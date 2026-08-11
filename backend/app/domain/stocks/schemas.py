from datetime import datetime
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
