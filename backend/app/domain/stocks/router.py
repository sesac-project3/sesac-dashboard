from datetime import datetime, timezone

from fastapi import APIRouter

from app.common.response import ApiResponse
from app.domain.stocks.schemas import MarketIndex, Stock

router = APIRouter(prefix="/stocks", tags=["stocks"])

# seed.sql과 동일한 5종목. 실 시세는 ISSUE-A1(KIS 연동) 붙기 전까지 이 하드코딩으로 대체.
_STOCKS = [
    Stock(id=1, code="005930", name="삼성전자", market="KOSPI"),
    Stock(id=2, code="000660", name="SK하이닉스", market="KOSPI"),
    Stock(id=3, code="005380", name="현대자동차", market="KOSPI"),
    Stock(id=4, code="373220", name="LG에너지솔루션", market="KOSPI"),
    Stock(id=5, code="042660", name="한화오션", market="KOSPI"),
]


@router.get("", response_model=ApiResponse[list[Stock]])
def list_stocks():
    return ApiResponse.ok(_STOCKS)


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
