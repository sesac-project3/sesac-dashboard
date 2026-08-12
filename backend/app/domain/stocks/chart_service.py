from collections import OrderedDict
from datetime import date, datetime
import json
from typing import Literal
from zoneinfo import ZoneInfo

from redis import Redis as SyncRedis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException, ErrorCode
from app.core.config import settings
from app.domain.stocks.models import Stock, StockDailyCandle, StockMinuteCandle
from app.domain.stocks.schemas import Candle, CandleResponse

ChartInterval = Literal["DAILY", "WEEKLY", "MONTHLY", "MINUTE_15"]
_READ_COUNTS = {"DAILY": 40, "WEEKLY": 230, "MONTHLY": 400, "MINUTE_15": 500}
_DISPLAY_COUNTS = {"DAILY": 30, "WEEKLY": 28, "MONTHLY": 12, "MINUTE_15": 30}
KST = ZoneInfo("Asia/Seoul")
MINUTE_CANDLE_PREFIX = "market:minute-candles:"


def get_candles(db: Session, stock_code: str, interval: ChartInterval) -> CandleResponse:
    stock = db.scalar(select(Stock).where(Stock.code == stock_code))
    if stock is None:
        raise BusinessException(ErrorCode.ENTITY_NOT_FOUND)

    if interval == "MINUTE_15":
        rows = db.scalars(
            select(StockMinuteCandle)
            .where(StockMinuteCandle.stock_id == stock.id)
            .order_by(StockMinuteCandle.traded_at.desc())
            .limit(_READ_COUNTS[interval])
        ).all()
        minute_rows = _merge_minute_candles(
            list(reversed(rows)),
            _get_live_minute_candles(stock.code),
        )
        candles = _aggregate_minute_candles(minute_rows)
    else:
        rows = db.scalars(
            select(StockDailyCandle)
            .where(StockDailyCandle.stock_id == stock.id)
            .order_by(StockDailyCandle.trade_date.desc())
            .limit(_READ_COUNTS[interval])
        ).all()
        candles = [_to_candle(row) for row in reversed(rows)]
        if interval != "DAILY":
            candles = _aggregate(candles, interval)

    return CandleResponse(
        stockCode=stock.code,
        stockName=stock.name,
        interval=interval,
        source="DB_REDIS" if interval == "MINUTE_15" else "DB",
        candles=candles[-_DISPLAY_COUNTS[interval]:],
    )


def _to_candle(row: StockDailyCandle) -> Candle:
    return Candle(
        timestamp=row.trade_date,
        openPrice=float(row.open_price),
        highPrice=float(row.high_price),
        lowPrice=float(row.low_price),
        closePrice=float(row.close_price),
        volume=row.volume,
    )


def _aggregate_minute_candles(rows: list[StockMinuteCandle]) -> list[Candle]:
    buckets: OrderedDict[datetime, Candle] = OrderedDict()
    for row in rows:
        traded_at = row.traded_at
        if traded_at.tzinfo is None:
            traded_at = traded_at.replace(tzinfo=KST)
        traded_at = traded_at.astimezone(KST)
        bucket = traded_at.replace(
            minute=traded_at.minute // 15 * 15,
            second=0,
            microsecond=0,
        )
        current = buckets.get(bucket)
        candle = Candle(
            timestamp=traded_at,
            openPrice=float(row.open_price),
            highPrice=float(row.high_price),
            lowPrice=float(row.low_price),
            closePrice=float(row.close_price),
            volume=row.volume,
        )
        if current is None:
            buckets[bucket] = candle.model_copy(update={"timestamp": bucket})
        else:
            buckets[bucket] = current.model_copy(update={
                "highPrice": max(current.highPrice, candle.highPrice),
                "lowPrice": min(current.lowPrice, candle.lowPrice),
                "closePrice": candle.closePrice,
                "volume": current.volume + candle.volume,
            })
    return list(buckets.values())


def _get_live_minute_candles(stock_code: str) -> list[StockMinuteCandle]:
    traded_date = datetime.now(KST).strftime("%Y%m%d")
    redis = SyncRedis.from_url(settings.redis_url, decode_responses=True)
    try:
        values = redis.hvals(f"{MINUTE_CANDLE_PREFIX}{stock_code}:{traded_date}")
    finally:
        redis.close()

    candles: list[StockMinuteCandle] = []
    for value in values:
        try:
            message = json.loads(value)
            candle = message["candle"]
            row = StockMinuteCandle(
                traded_at=datetime.fromisoformat(candle["timestamp"]),
                open_price=float(candle["openPrice"]),
                high_price=float(candle["highPrice"]),
                low_price=float(candle["lowPrice"]),
                close_price=float(candle["closePrice"]),
                volume=int(candle["volume"]),
            )
            candles.append(row)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return candles


def _merge_minute_candles(
    db_rows: list[StockMinuteCandle],
    live_rows: list[StockMinuteCandle],
) -> list[StockMinuteCandle]:
    merged: dict[datetime, StockMinuteCandle] = {}
    for row in db_rows + live_rows:
        traded_at = row.traded_at
        if traded_at.tzinfo is None:
            traded_at = traded_at.replace(tzinfo=KST)
        merged[traded_at.astimezone(KST).replace(second=0, microsecond=0)] = row
    return [merged[key] for key in sorted(merged)]


def _aggregate(candles: list[Candle], interval: ChartInterval) -> list[Candle]:
    buckets: OrderedDict[tuple[int, int], Candle] = OrderedDict()
    for candle in candles:
        key = _bucket_key(candle.timestamp, interval)
        previous = buckets.get(key)
        if previous is None:
            buckets[key] = candle.model_copy(
                update={
                    "timestamp": candle.timestamp
                    if interval == "WEEKLY"
                    else candle.timestamp.replace(day=1)
                }
            )
            continue
        buckets[key] = previous.model_copy(update={
            "timestamp": previous.timestamp,
            "highPrice": max(previous.highPrice, candle.highPrice),
            "lowPrice": min(previous.lowPrice, candle.lowPrice),
            "closePrice": candle.closePrice,
            "volume": previous.volume + candle.volume,
        })
    return list(buckets.values())


def _bucket_key(value: date, interval: ChartInterval) -> tuple[int, int]:
    if interval == "MONTHLY":
        return value.year, value.month
    iso = value.isocalendar()
    return iso.year, iso.week
