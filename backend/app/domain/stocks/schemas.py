from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

Market = Literal["KOSPI", "KOSDAQ"]
IndexType = Literal["KOSPI", "KOSDAQ", "USD_KRW"]
ChartInterval = Literal["DAILY", "WEEKLY", "MONTHLY", "MINUTE_15"]
CandleSource = Literal["DB", "DB_REDIS"]


class Stock(BaseModel):
    id: int
    code: str
    name: str
    market: Market


class MarketIndex(BaseModel):
    indexType: IndexType
    value: float
    recordedAt: datetime


class InvestorTrend(BaseModel):
    personal: float  # 개인 순매수 대금 (억원)
    foreign: float  # 외국인 순매수 대금 (억원)
    institution: float  # 기관 순매수 대금 (억원)


class MarketIndexDetail(BaseModel):
    indexType: Market
    title: str
    value: float
    change: float
    changePercent: float
    isUp: bool
    investors: InvestorTrend


class StockRankingItem(BaseModel):
    code: str
    name: str
    price: float
    change: float
    changePercent: float
    isUp: bool
    volume: int
    tradingValue: float  # 거래대금 (억원)


RankingType = Literal["상승률", "하락률", "거래대금", "거래량"]


class HomeDashboard(BaseModel):
    indices: list[MarketIndexDetail]
    rankings: dict[RankingType, list[StockRankingItem]]
    asOf: datetime


class MarketIssue(BaseModel):
    title: str
    text: str
    updatedAt: datetime


class Candle(BaseModel):
    timestamp: datetime | date
    openPrice: float
    highPrice: float
    lowPrice: float
    closePrice: float
    volume: int


class CandleResponse(BaseModel):
    stockCode: str
    stockName: str
    interval: ChartInterval
    source: CandleSource
    candles: list[Candle]


class CandleBackfillResult(BaseModel):
    stockCode: str
    stockName: str
    requestedStartDate: date
    requestedEndDate: date
    receivedCount: int
    insertedCount: int
    updatedCount: int


class CandleBackfillResponse(BaseModel):
    stockCount: int
    totalReceivedCount: int
    totalInsertedCount: int
    totalUpdatedCount: int
    results: list[CandleBackfillResult]


class MinuteCandleBackfillResult(BaseModel):
    stockCode: str
    stockName: str
    receivedMinuteCount: int
    upsertedMinuteCount: int


class MinuteCandleBackfillResponse(BaseModel):
    stockCount: int
    totalReceivedMinuteCount: int
    totalUpsertedMinuteCount: int
    results: list[MinuteCandleBackfillResult]


class DailySentimentItem(BaseModel):
    date: date
    day: str
    sentiment: str
    emoji: str


class WeeklySentimentResponse(BaseModel):
    stockId: int
    weeklySentiments: list[DailySentimentItem]

