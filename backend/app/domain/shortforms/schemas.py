from typing import Literal

from pydantic import BaseModel


class Shortform(BaseModel):
    id: int
    stockCode: str
    stockName: str
    sentiment: Literal["POS", "NEG"]
    videoUrl: str
    subtitleText: str
    aiInsight: str | None = None
    likeCount: int = 0
    viewCount: int = 0
    liked: bool = False


class LikeToggleResponse(BaseModel):
    liked: bool
    likeCount: int


class BackgroundVideoResponse(BaseModel):
    videoUrl: str | None


class ShortformGenerateRequest(BaseModel):
    reportId: int
    sentiment: Literal["POS", "NEG"]

