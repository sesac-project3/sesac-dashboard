from typing import Literal

from pydantic import BaseModel


class Shortform(BaseModel):
    id: int
    stockCode: str
    stockName: str
    sentiment: Literal["긍정", "부정"]
    videoUrl: str
    subtitleText: str
    aiInsight: str | None = None
    likeCount: int = 0
    viewCount: int = 0


class LikeToggleResponse(BaseModel):
    liked: bool
    likeCount: int
