from pydantic import BaseModel


class WatchlistStock(BaseModel):
    code: str
    name: str
    market: str


class WatchlistToggleResponse(BaseModel):
    inWatchlist: bool
