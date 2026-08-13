from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.response import ApiResponse
from app.common.s3 import get_shortform_video_url
from app.common.security import get_current_user_id, get_optional_user_id
from app.core.database import get_db
from app.domain.shortforms.generation_service import generate_all_shortforms
from app.domain.shortforms.like_cache import get_liked_ids, mark_liked, mark_unliked
from app.domain.shortforms.models import Shortform as ShortformModel
from app.domain.shortforms.models import ShortformLike
from app.domain.shortforms.schemas import BackgroundVideoResponse, LikeToggleResponse, ShortformGenerateRequest
from app.domain.shortforms.schemas import Shortform as ShortformSchema
from app.domain.shortforms.service import generate_video_for_report
from fastapi import BackgroundTasks
from app.common.s3 import get_s3_client, PRESIGNED_URL_EXPIRE_SECONDS
from app.domain.stocks.models import Stock
from app.domain.stt.service import (
    ensure_uploads_dir,
    summarize_transcript_with_llm,
    transcribe_media_file,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shortforms", tags=["shortforms"])


def _to_schema(row: ShortformModel, stock: Stock, liked: bool = False) -> ShortformSchema:
    # 1. 만약 DB의 row.s3_url이 "shortforms/"로 시작하는 S3 Key 형식이라면 presigned URL 발급
    video_url = None
    if row.s3_url:
        if row.s3_url.startswith("shortforms/"):
            from app.core.config import settings
            try:
                s3_client = get_s3_client()
                video_url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": settings.aws_s3_bucket, "Key": row.s3_url},
                    ExpiresIn=PRESIGNED_URL_EXPIRE_SECONDS,
                )
            except Exception as exc:
                logger.warning(f"S3 Key({row.s3_url}) presigned URL 생성 실패: {exc}")
                video_url = row.s3_url
        else:
            video_url = row.s3_url

    # 2. 없으면 기존 종목명+감성 매핑 presigned URL로 폴백
    if not video_url:
        sentiment_ko = "긍정" if row.sentiment == "POS" else "부정"
        video_url = get_shortform_video_url(stock.name, sentiment_ko)

    # 3. aiInsight를 script와 sentiment를 바탕으로 동적으로 복원
    sentiment_ko = "긍정" if row.sentiment == "POS" else "부정"
    ai_insight_list = [
        f"{stock.name}의 변동성은 {sentiment_ko} 흐름입니다.",
        f"주요 이슈: {row.script[:35]}...",
        f"이에 따른 투자자 심리는 {sentiment_ko} 여론을 형성 중입니다."
    ]
    ai_insight = "\n".join(ai_insight_list)

    return ShortformSchema(
        id=row.id,
        stockCode=stock.code,
        stockName=stock.name,
        sentiment=row.sentiment,  # "POS" | "NEG"
        videoUrl=video_url or "",
        subtitleText=row.script,
        aiInsight=ai_insight,
        likeCount=row.like_count,
        viewCount=row.view_count,
        liked=liked,
    )


@router.get("/background-video", response_model=ApiResponse[BackgroundVideoResponse])
def get_background_video(stock_code: str, sentiment: Literal["POS", "NEG"], db: Session = Depends(get_db)):
    """ISSUE-E3: `{종목명}_positive.mp4` / `{종목명}_negative.mp4` 네이밍으로 S3에
    올려둔 배경 영상을 조회만 한다 (숏폼 생성과 별개로 바로 테스트하고 싶을 때용)."""
    stock = db.scalar(select(Stock).where(Stock.code == stock_code))
    if stock is None:
        raise HTTPException(status_code=404, detail=f"stock_code={stock_code} 없음")

    sentiment_ko = "긍정" if sentiment == "POS" else "부정"
    video_url = get_shortform_video_url(stock.name, sentiment_ko)
    return ApiResponse.ok(BackgroundVideoResponse(videoUrl=video_url))


@router.get("", response_model=ApiResponse[list[ShortformSchema]])
def list_shortforms(
    user_id: int | None = Depends(get_optional_user_id),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(ShortformModel, Stock)
        .join(Stock, Stock.code == ShortformModel.ticker)
        .order_by(ShortformModel.created_at.desc())
    ).all()
    # 비로그인이면 좋아요 여부를 표시할 사용자가 없으니 전부 False(기존과 동일 동작).
    liked_ids = get_liked_ids(db, user_id) if user_id is not None else set()
    return ApiResponse.ok([_to_schema(sf, stock, liked=sf.id in liked_ids) for sf, stock in rows])


@router.get("/liked-ids", response_model=ApiResponse[list[int]])
def liked_shortform_ids(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """이 목록 API는 프론트가 클라이언트 사이드에서 따로 부른다 — /shortforms 자체는
    Next.js 서버 컴포넌트가 revalidate 캐시로 부르는데(모든 사용자가 공유하는 캐시라
    요청자의 로그인 토큰을 실어 보낼 수가 없다), liked는 사용자별로 달라서 그 경로로는
    절대 정확할 수 없다. 그래서 좋아요 여부만 따로, 브라우저에서 토큰을 실어 이 엔드포인트로
    가져와 화면에 합친다."""
    return ApiResponse.ok(sorted(get_liked_ids(db, user_id)))


@router.post("", response_model=ApiResponse[ShortformSchema])
async def create_shortform(
    stock_code: str = Form(...),
    sentiment: Literal["POS", "NEG"] = Form(...),
    video_url: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """뉴스 영상/음성을 업로드하면 whisper로 자막을 뽑고 3줄 요약까지 붙여 숏폼을 만든다
    (ISSUE-E1 STT + ISSUE-E2 피드 데이터 결합). video_url은 보통 비워서 보내면 되고,
    S3의 `{종목명}_positive|negative.mp4` 배경 영상은 조회할 때마다 매번 새로 찾는다
    (ISSUE-E3) — presigned URL은 만료되므로 생성 시점에 한 번 구해서 저장해두지 않는다.
    video_url을 굳이 채워 보내면 S3에 해당 영상이 없을 때만 폴백으로 쓰인다.
    """
    stock = db.scalar(select(Stock).where(Stock.code == stock_code))
    if stock is None:
        raise HTTPException(status_code=404, detail=f"stock_code={stock_code} 없음")

    if not file.filename:
        raise HTTPException(status_code=400, detail="file name is required")
    content = await file.read()
    uploads_dir = ensure_uploads_dir()
    upload_path = uploads_dir / Path(file.filename).name
    upload_path.write_bytes(content)

    try:
        transcript = await run_in_threadpool(transcribe_media_file, upload_path)
    finally:
        upload_path.unlink(missing_ok=True)

    row = ShortformModel(
        ticker=stock.code,
        sentiment=sentiment,
        s3_url=video_url,
        script=transcript,
        view_count=0,
        like_count=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return ApiResponse.ok(_to_schema(row, stock))


@router.post("/generate", response_model=ApiResponse[None])
def generate_shortform(
    body: ShortformGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """지정한 AI 리포트 ID와 감성을 바탕으로 숏폼 영상을 백그라운드에서 자동 생성한다.
    비디오 합성 작업은 무겁기 때문에 BackgroundTasks로 처리 후 즉시 응답을 보낸다.
    """
    background_tasks.add_task(generate_video_for_report, db, body.reportId, body.sentiment)
    return ApiResponse.ok(message="영상 생성이 백그라운드에서 시작되었습니다. 잠시 후 피드에서 확인하실 수 있습니다.")



@router.post("/{shortform_id}/like", response_model=ApiResponse[LikeToggleResponse])
def toggle_like(
    shortform_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    row = db.get(ShortformModel, shortform_id)
    if row is None:
        raise HTTPException(status_code=404, detail="shortform not found")

    existing = db.scalar(
        select(ShortformLike).where(
            ShortformLike.shortform_id == shortform_id, ShortformLike.user_id == user_id
        )
    )
    if existing is None:
        db.add(ShortformLike(shortform_id=shortform_id, user_id=user_id))
        row.like_count += 1
        liked = True
    else:
        db.delete(existing)
        row.like_count = max(0, row.like_count - 1)
        liked = False

    try:
        db.commit()
    except IntegrityError:
        # 같은 좋아요에 대한 요청이 여러 탭/기기에서 동시에 들어와 UNIQUE 제약에 걸린
        # 경우 — 이미 다른 요청이 좋아요를 완료했다는 뜻이라 에러가 아니라 "좋아요됨"으로
        # 취급한다. 프론트는 같은 버튼의 요청을 순서대로만 보내지만(레이스 방지), 다른
        # 탭/기기의 요청까지는 그걸로 못 막는다.
        db.rollback()
        row = db.get(ShortformModel, shortform_id)
        liked = True

    # write-through: DB 커밋에 성공한 뒤에만 캐시를 갱신한다 — 커밋이 실패해서 위 except로
    # 빠졌을 때도 결과가 liked=True로 확정됐으니 캐시도 그에 맞춰 갱신.
    (mark_liked if liked else mark_unliked)(user_id, shortform_id)

    return ApiResponse.ok(LikeToggleResponse(liked=liked, likeCount=row.like_count))
