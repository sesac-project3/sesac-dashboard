from datetime import date, datetime, timedelta, timezone
import time
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException, ErrorCode
from app.core.kis import kis_token_client
from app.domain.stocks.models import Stock, StockDailyCandle
from app.domain.stocks.schemas import CandleBackfillResponse, CandleBackfillResult


def backfill_daily_candles(db: Session) -> CandleBackfillResponse:
    end_date = datetime.now(ZoneInfo("Asia/Seoul")).date() - timedelta(days=1)
    stocks = db.scalars(select(Stock).order_by(Stock.code)).all()
    results: list[CandleBackfillResult] = []

    for stock in stocks:
        last_date = db.scalar(
            select(func.max(StockDailyCandle.trade_date)).where(
                StockDailyCandle.stock_id == stock.id,
            )
        )
        start_date = (last_date + timedelta(days=1)) if last_date else end_date - timedelta(days=365)
        rows = _fetch_range(stock.code, start_date, end_date) if start_date <= end_date else []
        candles = [_to_candle(stock.id, row) for row in rows if row.get("stck_bsop_date")]
        existing_dates = set(db.scalars(
            select(StockDailyCandle.trade_date).where(
                StockDailyCandle.stock_id == stock.id,
                StockDailyCandle.trade_date.between(start_date, end_date),
            )
        ).all())
        inserted_count = sum(c["trade_date"] not in existing_dates for c in candles)
        if candles:
            stmt = insert(StockDailyCandle).values(candles)
            stmt = stmt.on_conflict_do_update(
                constraint="stock_daily_candles_stock_id_trade_date_key",
                set_={
                    "open_price": stmt.excluded.open_price,
                    "high_price": stmt.excluded.high_price,
                    "low_price": stmt.excluded.low_price,
                    "close_price": stmt.excluded.close_price,
                    "volume": stmt.excluded.volume,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            db.execute(stmt)
            db.commit()

        results.append(CandleBackfillResult(
            stockCode=stock.code,
            stockName=stock.name,
            requestedStartDate=start_date,
            requestedEndDate=end_date,
            receivedCount=len(candles),
            insertedCount=inserted_count,
            updatedCount=len(candles) - inserted_count,
        ))

    return CandleBackfillResponse(
        stockCount=len(results),
        totalReceivedCount=sum(r.receivedCount for r in results),
        totalInsertedCount=sum(r.insertedCount for r in results),
        totalUpdatedCount=sum(r.updatedCount for r in results),
        results=results,
    )


def _fetch_range(stock_code: str, start_date: date, end_date: date) -> list[dict[str, str]]:
    rows_by_date: dict[str, dict[str, str]] = {}
    cursor = end_date
    while cursor >= start_date:
        request_start = max(start_date, cursor - timedelta(days=90))
        rows = _request_with_backoff(
            stock_code,
            request_start.strftime("%Y%m%d"),
            cursor.strftime("%Y%m%d"),
        )
        for row in rows:
            trade_date = row.get("stck_bsop_date")
            if trade_date:
                rows_by_date[trade_date] = row
        cursor = request_start - timedelta(days=1)
    return [rows_by_date[key] for key in sorted(rows_by_date)]


def _request_with_backoff(stock_code: str, start_date: str, end_date: str) -> list[dict[str, str]]:
    for attempt in range(3):
        if attempt:
            time.sleep(2 ** attempt)
        else:
            time.sleep(0.5)
        try:
            return kis_token_client.daily_candles(stock_code, start_date, end_date)
        except BusinessException as exc:
            if exc.error_code != ErrorCode.SERVICE_UNAVAILABLE or attempt == 2:
                raise
    raise RuntimeError("unreachable")


def _to_candle(stock_id: int, row: dict[str, str]) -> dict[str, object]:
    return {
        "stock_id": stock_id,
        "trade_date": datetime.strptime(row["stck_bsop_date"], "%Y%m%d").date(),
        "open_price": float(row["stck_oprc"]),
        "high_price": float(row["stck_hgpr"]),
        "low_price": float(row["stck_lwpr"]),
        "close_price": float(row["stck_clpr"]),
        "volume": int(row["acml_vol"] or 0),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
