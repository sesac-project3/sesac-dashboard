from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.response import ApiResponse
from app.common.s3 import get_shortform_video_url
from app.common.security import get_current_user_id
from app.core.database import get_db
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
    return ShortformSchema(
        id=row.id,
        stockCode=stock.code,
        stockName=stock.name,
        sentiment=row.sentiment,
        videoUrl=row.video_url,
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
    (ISSUE-E1 STT + ISSUE-E2 피드 데이터 결합). video_url을 직접 안 넘기면 S3에 미리
    올려둔 `{종목명}_positive|negative.mp4` 배경 영상을 자동으로 찾아 채운다(ISSUE-E3).
    S3에도 없으면 빈 문자열로 저장되고 프론트가 자막 카드로 폴백한다(PRD §6).
    """
    stock = db.scalar(select(Stock).where(Stock.code == stock_code))
    if stock is None:
        raise HTTPException(status_code=404, detail=f"stock_code={stock_code} 없음")

    if not video_url:
        video_url = get_shortform_video_url(stock.name, sentiment) or ""

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

    db.commit()
    return ApiResponse.ok(LikeToggleResponse(liked=liked, likeCount=row.like_count))
