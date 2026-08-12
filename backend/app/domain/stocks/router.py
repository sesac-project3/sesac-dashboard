from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import ApiResponse
from app.core.database import get_db
from app.domain.stocks.schemas import CandleBackfillResponse, MarketIndex, Stock
from app.domain.stocks.service import backfill_daily_candles

router = APIRouter(prefix="/stocks", tags=["stocks"])

@router.get("/market/indices", response_model=ApiResponse[list[MarketIndex]])
def market_indices():
    # ponytail: KIS/환율 연동 전까지의 목업. ISSUE-A4에서 실 데이터로 교체.
    now = datetime.now(timezone.utc)
    mock = [
        MarketIndex(indexType="KOSPI", value=2650.12, recordedAt=now),
        MarketIndex(indexType="KOSDAQ", value=845.30, recordedAt=now),
        MarketIndex(indexType="USD_KRW", value=1380.5, recordedAt=now),
    ]
    return ApiResponse.ok(mock)


@router.post("/admin/candles/backfill", response_model=ApiResponse[CandleBackfillResponse])
def backfill_candles(db: Session = Depends(get_db)):
    return ApiResponse.ok(backfill_daily_candles(db), message="최근 1년 일봉 백필이 완료되었습니다.")
