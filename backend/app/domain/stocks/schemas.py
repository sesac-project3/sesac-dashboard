from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

Market = Literal["KOSPI", "KOSDAQ"]
IndexType = Literal["KOSPI", "KOSDAQ", "USD_KRW"]


class Stock(BaseModel):
    id: int
    code: str
    name: str
    market: Market


class MarketIndex(BaseModel):
    indexType: IndexType
    value: float
    recordedAt: datetime


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
