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
from app.common.security import get_current_user_id
from app.core.database import get_db
from app.domain.shortforms.generation_service import generate_all_shortforms
from app.domain.shortforms.models import Shortform as ShortformModel
from app.domain.shortforms.models import ShortformLike
from app.domain.shortforms.schemas import BackgroundVideoResponse, LikeToggleResponse
from app.domain.shortforms.schemas import Shortform as ShortformSchema
from app.domain.stocks.models import Stock
from app.domain.stt.service import (
    ensure_uploads_dir,
    summarize_transcript_with_llm,
    transcribe_media_file,
)

router = APIRouter(prefix="/shortforms", tags=["shortforms"])


def _to_schema(row: ShortformModel, stock: Stock) -> ShortformSchema:
    # S3 presigned URL은 1시간 뒤 만료된다 — 생성 시점 값을 DB에 저장해두고 그대로 돌려주면
    # 언젠간 반드시 깨진다. 그래서 조회마다 S3에서 새로 발급하고, S3에 없을 때만
    # row.video_url(수동으로 넣어둔 외부 URL 등)을 폴백으로 쓴다.
    video_url = get_shortform_video_url(stock.name, row.sentiment) or row.video_url

    return ShortformSchema(
        id=row.id,
        stockCode=stock.code,
        stockName=stock.name,
        sentiment=row.sentiment,
        videoUrl=video_url,
        subtitleText=row.subtitle_text,
        aiInsight=row.ai_insight,
        likeCount=row.like_count,
        viewCount=row.view_count,
    )


@router.get("/background-video", response_model=ApiResponse[BackgroundVideoResponse])
def get_background_video(stock_code: str, sentiment: Literal["긍정", "부정"], db: Session = Depends(get_db)):
    """ISSUE-E3: `{종목명}_positive.mp4` / `{종목명}_negative.mp4` 네이밍으로 S3에
    올려둔 배경 영상을 조회만 한다 (숏폼 생성과 별개로 바로 테스트하고 싶을 때용)."""
    stock = db.scalar(select(Stock).where(Stock.code == stock_code))
    if stock is None:
        raise HTTPException(status_code=404, detail=f"stock_code={stock_code} 없음")

    video_url = get_shortform_video_url(stock.name, sentiment)
    return ApiResponse.ok(BackgroundVideoResponse(videoUrl=video_url))


@router.get("", response_model=ApiResponse[list[ShortformSchema]])
def list_shortforms(db: Session = Depends(get_db)):
    rows = db.execute(
        select(ShortformModel, Stock)
        .join(Stock, Stock.id == ShortformModel.stock_id)
        .order_by(ShortformModel.published_date.desc())
    ).all()
    return ApiResponse.ok([_to_schema(sf, stock) for sf, stock in rows])


@router.post("", response_model=ApiResponse[ShortformSchema])
async def create_shortform(
    stock_code: str = Form(...),
    sentiment: Literal["긍정", "부정"] = Form(...),
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

    summary_bullets = await summarize_transcript_with_llm(transcript)
    ai_insight = "\n".join(b for b in summary_bullets if b)

    row = ShortformModel(
        stock_id=stock.id,
        sentiment=sentiment,
        video_url=video_url,
        subtitle_text=transcript,
        ai_insight=ai_insight,
        view_count=0,
        like_count=0,
        published_date=date.today(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return ApiResponse.ok(_to_schema(row, stock))


@router.post("/generate", response_model=ApiResponse[list[ShortformSchema]])
def generate_shortforms(db: Session = Depends(get_db)):
    """종목(id순) × [긍정, 부정] 조합마다 S3 영상 + sentiment_analysis(없으면 그 자리에서
    뉴스로 LLM 분류해 채움) + /reports 데이터를 엮어 자막·AI Insight를 생성/갱신한다.
    수동 트리거 배치 엔드포인트 (crontab 등에서 주기 호출하는 걸 상정)."""
    rows = generate_all_shortforms(db)
    stock_by_id = {s.id: s for s in db.scalars(select(Stock)).all()}
    return ApiResponse.ok([_to_schema(row, stock_by_id[row.stock_id]) for row in rows])


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

    return ApiResponse.ok(LikeToggleResponse(liked=liked, likeCount=row.like_count))
