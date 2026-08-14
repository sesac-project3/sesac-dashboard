from pydantic import BaseModel


class WatchlistStock(BaseModel):
    code: str
    name: str
    market: str
    price: float | None = None
    change: float | None = None
    changePercent: float | None = None
    isUp: bool | None = None


class WatchlistToggleResponse(BaseModel):
    inWatchlist: bool
