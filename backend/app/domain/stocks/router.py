from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException, ErrorCode
from app.common.response import ApiResponse
from app.core.database import get_db
from app.domain.stocks.chart_service import get_candles
from app.domain.stocks.home_dashboard_service import get_home_dashboard, get_market_issue
from app.domain.stocks.models import Stock as StockModel
from app.domain.stocks.schemas import (
    CandleBackfillResponse,
    CandleResponse,
    ChartInterval,
    HomeDashboard,
    MarketIndex,
    MarketIssue,
    MinuteCandleBackfillResponse,
    Stock,
    WeeklySentimentResponse,
)
from app.domain.stocks.service import (
    backfill_daily_candles,
    backfill_minute_candles,
    get_weekly_stock_sentiments,
)
from app.domain.stocks.websocket import handle_market_websocket

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/{stock_id_or_code}/sentiments/weekly", response_model=ApiResponse[WeeklySentimentResponse])
def weekly_sentiments(stock_id_or_code: str, db: Session = Depends(get_db)):
    return ApiResponse.ok(get_weekly_stock_sentiments(db, stock_id_or_code))


@router.get("", response_model=ApiResponse[list[Stock]])
def list_stocks(db: Session = Depends(get_db)):
    # ponytail: merge conflict 정리하면서 원래 있던 5종목 마스터 목록 엔드포인트가
    # 이 라우터 전체 교체로 빠져 있길래 복구 — 하드코딩 대신 실 DB 기준으로.
    rows = db.scalars(select(StockModel).order_by(StockModel.id)).all()
    return ApiResponse.ok([Stock.model_validate(row, from_attributes=True) for row in rows])


@router.websocket("/ws")
async def market_websocket(websocket: WebSocket):
    await handle_market_websocket(websocket)


@router.get("/home-dashboard", response_model=ApiResponse[HomeDashboard])
def home_dashboard(db: Session = Depends(get_db)):
    # /{stock_code}보다 먼저 등록해야 한다 — 안 그러면 "home-dashboard"가 종목코드로 잡힘.
    return ApiResponse.ok(get_home_dashboard(db))


@router.get("/market-issue", response_model=ApiResponse[MarketIssue | None])
def market_issue():
    # /home-dashboard는 5초마다 폴링되는데 이건 LLM 호출(캐시 미스 시)이 껴서 느리다 —
    # 그 폴링에 얹으면 대시보드 전체가 느려지니 별도 엔드포인트로 분리, 프론트가 드물게 부른다.
    # /{stock_code}보다 먼저 등록해야 한다 — 안 그러면 "market-issue"가 종목코드로 잡힘.
    return ApiResponse.ok(get_market_issue())


@router.get("/{stock_code}", response_model=ApiResponse[Stock])
def stock(stock_code: str, db: Session = Depends(get_db)):
    row = db.scalar(select(StockModel).where(StockModel.code == stock_code))
    if row is None:
        raise BusinessException(ErrorCode.ENTITY_NOT_FOUND)
    return ApiResponse.ok(Stock.model_validate(row, from_attributes=True))


@router.get("/{stock_code}/candles", response_model=ApiResponse[CandleResponse])
def candles(
    stock_code: str,
    interval: ChartInterval = "DAILY",
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(get_candles(db, stock_code, interval))

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


@router.post(
    "/admin/minute-candles/backfill",
    response_model=ApiResponse[MinuteCandleBackfillResponse],
)
def backfill_minute_candles_api(db: Session = Depends(get_db)):
    return ApiResponse.ok(
        backfill_minute_candles(db),
        message="최근 거래일 1분봉 백필이 완료되었습니다.",
    )
