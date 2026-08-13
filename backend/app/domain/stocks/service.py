from datetime import date, datetime, timedelta, timezone
import time
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException, ErrorCode
from app.core.kis import kis_token_client
from app.core.database import SessionLocal
from app.domain.stocks.models import SentimentAnalysis, Stock, StockDailyCandle, StockMinuteCandle
from app.domain.stocks.schemas import (
    CandleBackfillResponse,
    CandleBackfillResult,
    DailySentimentItem,
    MinuteCandleBackfillResponse,
    MinuteCandleBackfillResult,
    WeeklySentimentResponse,
)

KST = ZoneInfo("Asia/Seoul")
MARKET_OPEN = "090000"
MARKET_CLOSE = "153000"
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]
EMOJI_MAP = {
    "긍정": "☀️",
    "중립": "🌤️",
    "부정": "🌧️",
}


def get_weekly_stock_sentiments(db: Session, identifier: str) -> WeeklySentimentResponse:
    """어제 날짜(yesterday) 이하 기준 최근 7일치 주식 감정 날씨 데이터 조회 (stock_id 또는 stock_code)."""
    stock_id: int = 1
    if identifier.isdigit() and len(identifier) < 6:
        stock_id = int(identifier)
    else:
        stock = db.scalar(select(Stock).where(Stock.code == identifier))
        if stock:
            stock_id = stock.id

    yesterday = datetime.now(KST).date() - timedelta(days=1)
    rows = db.scalars(
        select(SentimentAnalysis)
        .where(
            SentimentAnalysis.stock_id == stock_id,
            SentimentAnalysis.date <= yesterday,
        )
        .order_by(SentimentAnalysis.date.desc())
        .limit(7)
    ).all()

    # 과거 -> 최근 순서로 정렬
    rows_sorted = list(reversed(rows))
    items = [
        DailySentimentItem(
            date=row.date,
            day=WEEKDAYS[row.date.weekday()],
            sentiment=row.sentiment,
            emoji=EMOJI_MAP.get(row.sentiment, "🌤️"),
        )
        for row in rows_sorted
    ]

    return WeeklySentimentResponse(stockId=stock_id, weeklySentiments=items)




def persist_live_minute_candle(stock_code: str, message: dict[str, object]) -> None:
    candle = message.get("candle")
    if not isinstance(candle, dict):
        return
    timestamp = candle.get("timestamp")
    if not isinstance(timestamp, str):
        return

    with SessionLocal() as db:
        stock = db.scalar(select(Stock).where(Stock.code == stock_code))
        if stock is None:
            return
        traded_at = datetime.fromisoformat(timestamp).astimezone(timezone.utc)
        now = datetime.now(timezone.utc)
        values = {
            "stock_id": stock.id,
            "traded_at": traded_at,
            "open_price": float(candle["openPrice"]),
            "high_price": float(candle["highPrice"]),
            "low_price": float(candle["lowPrice"]),
            "close_price": float(candle["closePrice"]),
            "volume": int(candle["volume"]),
            "created_at": now,
            "updated_at": now,
        }
        stmt = insert(StockMinuteCandle).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="stock_minute_candles_stock_id_traded_at_key",
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


def backfill_minute_candles(db: Session) -> MinuteCandleBackfillResponse:
    now = datetime.now(KST)
    stocks = db.scalars(select(Stock).order_by(Stock.code)).all()
    results: list[MinuteCandleBackfillResult] = []

    for stock in stocks:
        minute_rows = _fetch_latest_minute_range(stock.code, now)
        candles = [_to_minute_candle(stock.id, row) for row in minute_rows]
        if candles:
            stmt = insert(StockMinuteCandle).values(candles)
            stmt = stmt.on_conflict_do_update(
                constraint="stock_minute_candles_stock_id_traded_at_key",
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

        results.append(MinuteCandleBackfillResult(
            stockCode=stock.code,
            stockName=stock.name,
            receivedMinuteCount=len(minute_rows),
            upsertedMinuteCount=len(candles),
        ))

    return MinuteCandleBackfillResponse(
        stockCount=len(results),
        totalReceivedMinuteCount=sum(r.receivedMinuteCount for r in results),
        totalUpsertedMinuteCount=sum(r.upsertedMinuteCount for r in results),
        results=results,
    )


def _fetch_latest_minute_range(stock_code: str, now: datetime) -> list[dict[str, str]]:
    input_time = min(now.strftime("%H%M%S"), MARKET_CLOSE)
    for days_ago in range(8):
        target_date = now.date() - timedelta(days=days_ago)
        rows = _fetch_minute_range(
            stock_code,
            target_date.strftime("%Y%m%d"),
            input_time if days_ago == 0 else MARKET_CLOSE,
        )
        if rows:
            return rows
    return []


def _fetch_minute_range(
    stock_code: str,
    input_date: str,
    input_time: str,
) -> list[dict[str, str]]:
    rows_by_timestamp: dict[tuple[str, str], dict[str, str]] = {}
    cursor = input_time

    for _ in range(5):
        rows = _minute_request_with_backoff(stock_code, input_date, cursor)
        if not rows:
            break

        for row in rows:
            key = (row.get("stck_bsop_date", ""), row.get("stck_cntg_hour", ""))
            if all(key) and key[0] == input_date:
                rows_by_timestamp[key] = row

        oldest = min(
            (row for row in rows if row.get("stck_bsop_date") and row.get("stck_cntg_hour")),
            key=lambda row: (row["stck_bsop_date"], row["stck_cntg_hour"]),
            default=None,
        )
        if oldest is None or oldest["stck_cntg_hour"] <= MARKET_OPEN:
            break

        oldest_at = datetime.strptime(
            f"{oldest['stck_bsop_date']} {oldest['stck_cntg_hour']}",
            "%Y%m%d %H%M%S",
        )
        cursor = (oldest_at - timedelta(seconds=1)).strftime("%H%M%S")

    return [rows_by_timestamp[key] for key in sorted(rows_by_timestamp)]


def _minute_request_with_backoff(
    stock_code: str,
    input_date: str,
    input_time: str,
) -> list[dict[str, str]]:
    for attempt in range(3):
        if attempt:
            time.sleep(2 ** attempt)
        else:
            time.sleep(0.5)
        try:
            return kis_token_client.minute_candles(stock_code, input_date, input_time)
        except BusinessException as exc:
            if exc.error_code != ErrorCode.SERVICE_UNAVAILABLE or attempt == 2:
                raise
    raise RuntimeError("unreachable")


def _to_minute_candle(stock_id: int, row: dict[str, str]) -> dict[str, object]:
    traded_at = datetime.strptime(
        f"{row['stck_bsop_date']} {row['stck_cntg_hour']}",
        "%Y%m%d %H%M%S",
    ).replace(tzinfo=KST).astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    return {
        "stock_id": stock_id,
        "traded_at": traded_at,
        "open_price": float(row["stck_oprc"]),
        "high_price": float(row["stck_hgpr"]),
        "low_price": float(row["stck_lwpr"]),
        "close_price": float(row["stck_prpr"]),
        "volume": int(row.get("cntg_vol") or 0),
        "created_at": now,
        "updated_at": now,
    }


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
