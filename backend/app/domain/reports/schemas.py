from typing import Literal

from pydantic import BaseModel


class PeerComparisonRow(BaseModel):
    name: str
    per: float
    pbr: float
    roe: float


class StockReport(BaseModel):
    stockCode: str
    reportDate: str
    judgement: Literal["매수", "중립", "매도"] | None = None
    judgementReasons: list[str] | None = None
    revenueTrend: Literal["증가", "감소"] | None = None
    operatingProfitTrend: Literal["증가", "감소"] | None = None
    growthGrade: Literal["양호", "보통", "낮음"] | None = None
    riskScores: dict[str, float] | None = None
    peerComparison: list[PeerComparisonRow] | None = None
    week52High: float | None = None
    week52Low: float | None = None
    currentPrice: float | None = None
    valuationComment: str | None = None

