from collections import OrderedDict
from datetime import date
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException, ErrorCode
from app.domain.stocks.models import Stock, StockDailyCandle
from app.domain.stocks.schemas import Candle, CandleResponse

ChartInterval = Literal["DAILY", "WEEKLY", "MONTHLY"]
_READ_COUNTS = {"DAILY": 40, "WEEKLY": 230, "MONTHLY": 400}
_DISPLAY_COUNTS = {"DAILY": 30, "WEEKLY": 28, "MONTHLY": 12}


def get_candles(db: Session, stock_code: str, interval: ChartInterval) -> CandleResponse:
    stock = db.scalar(select(Stock).where(Stock.code == stock_code))
    if stock is None:
        raise BusinessException(ErrorCode.ENTITY_NOT_FOUND)

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
        source="DB",
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
