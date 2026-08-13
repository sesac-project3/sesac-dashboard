from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.response import ApiResponse
from app.common.security import get_current_user_id
from app.core.database import get_db
from app.domain.stocks.home_dashboard_service import fetch_stock_ranking_items
from app.domain.stocks.models import Stock
from app.domain.watchlists.models import Watchlist
from app.domain.watchlists.schemas import WatchlistStock, WatchlistToggleResponse

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.get("", response_model=ApiResponse[list[WatchlistStock]])
def list_watchlist(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Stock).join(Watchlist, Watchlist.stock_id == Stock.id).where(Watchlist.user_id == user_id)
    ).scalars().all()
    if not rows:
        return ApiResponse.ok([])

    # 홈 대시보드 랭킹과 같은 KIS 현재가 조회 함수를 재사용(중복 구현 방지). 5종목
    # 전체를 조회한 뒤 관심종목만 골라낸다 — 종목 수가 5개뿐이라 이 정도는 괜찮지만,
    # 종목 수가 늘어나면 코드 목록을 받는 버전으로 분리해야 한다.
    watched_codes = {s.code for s in rows}
    price_by_code = {item.code: item for item in fetch_stock_ranking_items(db) if item.code in watched_codes}

    result = []
    for s in rows:
        item = price_by_code.get(s.code)
        result.append(
            WatchlistStock(
                code=s.code,
                name=s.name,
                market=s.market,
                price=item.price if item else None,
                change=item.change if item else None,
                changePercent=item.changePercent if item else None,
                isUp=item.isUp if item else None,
            )
        )
    return ApiResponse.ok(result)


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
