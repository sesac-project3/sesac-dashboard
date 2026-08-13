from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.response import ApiResponse
from app.common.security import get_current_user_id
from app.core.database import get_db
from app.domain.stocks.models import Stock
from app.domain.watchlists.models import Watchlist
from app.domain.watchlists.schemas import WatchlistStock, WatchlistToggleResponse

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.get("", response_model=ApiResponse[list[WatchlistStock]])
def list_watchlist(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Stock).join(Watchlist, Watchlist.stock_id == Stock.id).where(Watchlist.user_id == user_id)
    ).scalars().all()
    return ApiResponse.ok([WatchlistStock(code=s.code, name=s.name, market=s.market) for s in rows])


@router.post("/{stock_code}/toggle", response_model=ApiResponse[WatchlistToggleResponse])
def toggle_watchlist(
    stock_code: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    stock = db.scalar(select(Stock).where(Stock.code == stock_code))
    if stock is None:
        raise HTTPException(status_code=404, detail=f"stock_code={stock_code} 없음")

    existing = db.scalar(
        select(Watchlist).where(Watchlist.user_id == user_id, Watchlist.stock_id == stock.id)
    )
    if existing is None:
        db.add(Watchlist(user_id=user_id, stock_id=stock.id))
        in_watchlist = True
    else:
        db.delete(existing)
        in_watchlist = False

    db.commit()
    return ApiResponse.ok(WatchlistToggleResponse(inWatchlist=in_watchlist))
