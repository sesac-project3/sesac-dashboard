import os
import time
import logging
import httpx
from datetime import date
from sqlalchemy import text, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.common.openai_client import get_openai_client
from app.common.s3 import get_s3_client
from app.domain.shortforms.models import Shortform as ShortformModel
from app.domain.stocks.models import Stock

logger = logging.getLogger(__name__)

def generate_video_for_report(db: Session, report_id: int, sentiment: str) -> ShortformModel | None:
    """
    지정한 AI 리포트 ID(report_id)와 감성(sentiment: 'POS' | 'NEG')을 기반으로
    LLM 대본 생성 -> DALL-E 3 이미지 생성 -> TTS 음성 생성 -> MoviePy 합성 -> S3 업로드를 수행하여 숏폼을 저장한다.
    """
    # 1. AI 리포트 및 종목 정보 가져오기
    report = db.execute(
        text("""
            SELECT r.id, r.stock_id, r.report_date, r.judgement, r.judgement_reasons, 
                   s.code as stock_code, s.name as stock_name
            FROM stock_reports r
            JOIN stocks s ON r.stock_id = s.id
            WHERE r.id = :report_id
        """),
        {"report_id": report_id}
    ).fetchone()

    if not report:
        logger.error(f"AI 리포트 ID={report_id} 를 찾을 수 없습니다.")
        return None

    stock_code = report.stock_code
    stock_name = report.stock_name
    report_date = report.report_date
    judgement_reasons = report.judgement_reasons or []

    # 2. OpenAI 클라이언트 로드
    client = get_openai_client()
    if not client:
        logger.error("OpenAI API 키가 설정되지 않아 영상 생성을 진행할 수 없습니다.")
        return None

    temp_image_path = f"temp_{report_id}_{sentiment}.png"
    temp_audio_path = f"temp_{report_id}_{sentiment}.mp3"
    temp_video_path = f"temp_{report_id}_{sentiment}.mp4"

    try:
        # 3. LLM을 사용하여 숏폼 나레이션 대본 및 DALL-E 이미지 프롬프트 추출
        sentiment_ko = "긍정" if sentiment == "POS" else "부정"
        reasons_text = "\n".join(f"- {r}" for r in judgement_reasons)
        system_prompt = (
            "너는 주식 분석 리포트를 20초 분량의 숏폼 나레이션 대본과 이미지 생성용 프롬프트로 변환하는 전문가야.\n"
            "출력은 반드시 JSON 형식을 따라야 하며 다른 텍스트는 절대 포함하지 마.\n"
            "출력 규격:\n"
            "{\n"
            "  \"script\": \"(나레이션으로 읽을 한글 텍스트 대본, 약 100~150자 내외로 주식 호재/악재 상황을 긴박하게 전달)\",\n"
            "  \"image_prompt\": \"(DALL-E 3에 입력할 영문 이미지 생성 프롬프트. 해당 주식 종목과 지정된 감성을 은유적이고 시네마틱하게 표현하는 예술적 프롬프트, 9:16 비율에 최적화된 배경 묘사)\"\n"
            "}"
        )
        user_prompt = (
            f"종목명: {stock_name}\n"
            f"리포트 날짜: {report_date}\n"
            f"주요 이슈/근거:\n{reasons_text}\n"
            f"영상 타겟 여론/감성: {sentiment_ko}\n\n"
            f"이 정보와 지정된 감성('{sentiment_ko}')에 딱 맞추어 JSON을 작성해줘."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=500
        )

        import json
        llm_data = json.loads(response.choices[0].message.content)
        script_text = llm_data.get("script", f"오늘 {stock_name}의 시장 상황은 {sentiment_ko} 분위기를 보이고 있습니다.")
        image_prompt = llm_data.get("image_prompt", f"A clean aesthetic representation of {stock_name} stock market with {sentiment_ko} mood, vertical 9:16 framing")

        logger.info(f"생성된 대본: {script_text}")
        logger.info(f"생성된 이미지 프롬프트: {image_prompt}")

        # 4. 이미지 생성 및 폴백
        try:
            logger.info("gpt-image-2 이미지를 생성 중입니다...")
            dalle_res = client.images.generate(
                model="gpt-image-2",
                prompt=image_prompt,
                size="1024x1792",  # 9:16 비율
                n=1
            )
            if dalle_res.data[0].b64_json:
                import base64
                img_data = base64.b64decode(dalle_res.data[0].b64_json)
                with open(temp_image_path, "wb") as f:
                    f.write(img_data)
                logger.info("gpt-image-2 이미지 (base64) 저장 완료.")
            else:
                image_url = dalle_res.data[0].url
                with httpx.Client() as http_client:
                    img_data = http_client.get(image_url).content
                    with open(temp_image_path, "wb") as f:
                        f.write(img_data)
                logger.info("gpt-image-2 이미지 다운로드 완료.")
        except Exception as gpt_img_exc:
            logger.warning(f"gpt-image-2 생성 실패 ({gpt_img_exc}). DALL-E 3로 폴백 시도합니다...")
            try:
                logger.info("DALL-E 3 이미지를 생성 중입니다...")
                dalle_res = client.images.generate(
                    model="dall-e-3",
                    prompt=image_prompt,
                    size="1024x1792",
                    quality="standard",
                    n=1
                )
                image_url = dalle_res.data[0].url
                with httpx.Client() as http_client:
                    img_data = http_client.get(image_url).content
                    with open(temp_image_path, "wb") as f:
                        f.write(img_data)
                logger.info("DALL-E 3 이미지 다운로드 완료.")
            except Exception as dalle_exc:
                logger.warning(f"DALL-E 3 생성 실패 ({dalle_exc}). DALL-E 2로 폴백 시도합니다...")
                try:
                    dalle_res = client.images.generate(
                        model="dall-e-2",
                        prompt=image_prompt,
                        size="1024x1024",
                        n=1
                    )
                    image_url = dalle_res.data[0].url
                    with httpx.Client() as http_client:
                        img_data = http_client.get(image_url).content
                        with open(temp_image_path, "wb") as f:
                            f.write(img_data)
                    logger.info("DALL-E 2 이미지 다운로드 완료.")
                except Exception as dalle2_exc:
                    logger.warning(f"DALL-E 2 생성 실패 ({dalle2_exc}). Unsplash 주식 차트 이미지로 폴백을 시도합니다...")
                    try:
                        # POS: 초록/상승 차트 이미지, NEG: 어두운/하락 차트 이미지
                        url = (
                            "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=1024&h=1792&fit=crop"
                            if sentiment == "POS" else
                            "https://images.unsplash.com/photo-1618044733300-9472054094ee?w=1024&h=1792&fit=crop"
                        )
                        with httpx.Client() as http_client:
                            img_data = http_client.get(url).content
                            with open(temp_image_path, "wb") as f:
                                f.write(img_data)
                        logger.info("Unsplash 폴백 이미지 다운로드 완료.")
                    except Exception as unsplash_exc:
                        logger.warning(f"Unsplash 다운로드 실패 ({unsplash_exc}). 로컬 단색 이미지로 폴백합니다.")
                        from PIL import Image
                        # POS: Rose/Coral color, NEG: Slate/Dark color
                        bg_color = (225, 29, 72) if sentiment == "POS" else (30, 41, 59)
                        img = Image.new("RGB", (1024, 1792), color=bg_color)
                        img.save(temp_image_path)
                        logger.info("로컬 단색 폴백 이미지 생성 완료.")

        # 5. OpenAI TTS 나레이션 음성 파일 생성
        logger.info("OpenAI TTS 음성을 생성 중입니다...")
        tts_res = client.audio.speech.create(
            model="tts-1",
            voice="alloy",  # 숏폼에 잘 어울리는 alloy 목소리 적용
            input=script_text
        )
        tts_res.stream_to_file(temp_audio_path)
        logger.info("TTS 음성 다운로드 완료.")

        # 6. MoviePy 미디어 합성
        logger.info("MoviePy를 활용해 영상을 렌더링하고 있습니다...")
        
        # 메모리 절약 및 인코딩 안정성을 위해 이미지를 576x1024로 리사이즈
        try:
            from PIL import Image
            with Image.open(temp_image_path) as img:
                resampling = getattr(Image, "Resampling", None)
                filter_method = resampling.LANCZOS if resampling else Image.BICUBIC
                img_resized = img.resize((576, 1024), filter_method)
                img_resized.save(temp_image_path)
            logger.info("이미지를 576x1024 비율로 리사이즈 완료 (메모리 최적화).")
        except Exception as resize_exc:
            logger.warning(f"이미지 리사이즈 실패 ({resize_exc}). 원본 크기로 계속 진행합니다.")

        from moviepy.editor import ImageClip, AudioFileClip

        audio_clip = AudioFileClip(temp_audio_path)
        duration = audio_clip.duration

        # 9:16 비율의 이미지 클립 생성 및 시간 설정
        image_clip = ImageClip(temp_image_path).set_duration(duration)
        video_clip = image_clip.set_audio(audio_clip)

        # H.264 코덱의 MP4로 비디오 렌더링 실행
        video_clip.write_videofile(
            temp_video_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=f"temp_audio_{report_id}_{sentiment}.m4a",
            remove_temp=True,
            logger=None
        )
        
        # MoviePy 리소스 릴리즈
        audio_clip.close()
        image_clip.close()
        video_clip.close()
        logger.info("비디오 합성 완료.")

        # 7. S3에 비디오 업로드
        if not settings.aws_s3_bucket:
            logger.error("AWS_S3_BUCKET이 설정되지 않아 S3 업로드를 건너뜁니다.")
            return None

        s3_key = f"shortforms/{stock_code}_{sentiment}_{report_date}.mp4"
        s3_client = get_s3_client()
        
        logger.info(f"S3 업로드 시작: key={s3_key}")
        s3_client.upload_file(
            temp_video_path, 
            settings.aws_s3_bucket, 
            s3_key,
            ExtraArgs={"ContentType": "video/mp4"}
        )
        logger.info("S3 업로드 완료.")

        # 8. 데이터베이스 저장 (Upsert)
        # 동일한 report_id와 sentiment를 가진 기존 숏폼 존재 여부 확인
        row = None
        if report_id is not None:
            row = db.scalar(
                select(ShortformModel).where(
                    ShortformModel.report_id == report_id,
                    ShortformModel.sentiment == sentiment
                )
            )

        if row:
            row.s3_url = s3_key  # 조회할 때 presigned URL로 변환될 S3 Key 보관
            row.script = script_text
        else:
            row = ShortformModel(
                ticker=stock_code,
                sentiment=sentiment,
                s3_url=s3_key,
                script=script_text,
                report_id=report_id,
                view_count=0,
                like_count=0
            )
            db.add(row)

        db.commit()
        db.refresh(row)
        logger.info(f"숏폼 DB 저장 완료: ID={row.id}")
        return row

    except Exception as e:
        logger.exception("숏폼 영상 자동 제작 프로세스 도중 에러가 발생했습니다.")
        return None
    finally:
        # 9. 임시 로컬 미디어 파일 정리 제거
        for temp_file in (temp_image_path, temp_audio_path, temp_video_path):
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as cleanup_err:
                    logger.warning(f"임시 파일 삭제 실패 ({temp_file}): {cleanup_err}")
