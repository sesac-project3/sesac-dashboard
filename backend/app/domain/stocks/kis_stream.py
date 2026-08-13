import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import websockets
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.kis import kis_token_client
from app.domain.stocks.models import Stock, StockDailyCandle
from app.domain.stocks.service import persist_live_minute_candle
from app.domain.stocks.candle_store import publish_candle, publish_quote, store_minute_candle
from app.domain.stocks.market_subscription import MarketWebSocketManager

logger = logging.getLogger(__name__)

KIS_WEBSOCKET_PATH = "/tryitout"
KIS_TRADE_TR_ID = "H0STCNT0"
KST = ZoneInfo("Asia/Seoul")


@dataclass
class LiveMinuteCandle:
    traded_at: datetime
    open_price: int
    high_price: int
    low_price: int
    close_price: int
    volume: int

    def update(self, price: int, volume: int) -> None:
        self.high_price = max(self.high_price, price)
        self.low_price = min(self.low_price, price)
        self.close_price = price
        self.volume += volume

    def as_message(self, stock_code: str) -> dict[str, object]:
        return {
            "type": "candle_update",
            "stockCode": stock_code,
            "interval": "MINUTE_1",
            "candle": {
                "timestamp": self.traded_at.isoformat(),
                "openPrice": self.open_price,
                "highPrice": self.high_price,
                "lowPrice": self.low_price,
                "closePrice": self.close_price,
                "volume": self.volume,
            },
            "updatedAt": datetime.now(KST).isoformat(),
        }


@dataclass
class LiveAggregateCandle:
    interval: str
    traded_at: datetime
    open_price: int
    high_price: int
    low_price: int
    close_price: int
    volume: int
    display_at: datetime | None = None
    last_cumulative_volume: int | None = None

    def update(self, price: int, volume: int, cumulative_volume: int | None = None) -> None:
        self.high_price = max(self.high_price, price)
        self.low_price = min(self.low_price, price)
        self.close_price = price
        if cumulative_volume is None:
            self.volume += volume
        elif self.last_cumulative_volume is not None:
            self.volume += max(0, cumulative_volume - self.last_cumulative_volume)
        self.last_cumulative_volume = cumulative_volume

    def as_message(self, stock_code: str) -> dict[str, object]:
        display_at = self.display_at or self.traded_at
        timestamp = (
            display_at.date().isoformat()
            if self.interval in {"DAILY", "WEEKLY", "MONTHLY"}
            else display_at.isoformat()
        )
        return {
            "type": "candle_update",
            "stockCode": stock_code,
            "interval": self.interval,
            "candle": {
                "timestamp": timestamp,
                "openPrice": self.open_price,
                "highPrice": self.high_price,
                "lowPrice": self.low_price,
                "closePrice": self.close_price,
                "volume": self.volume,
            },
            "updatedAt": datetime.now(KST).isoformat(),
        }


class KisMarketStream:
    def __init__(self, manager: MarketWebSocketManager) -> None:
        self._manager = manager
        self._connection = None
        self._task: asyncio.Task[None] | None = None
        self._subscribed_codes: set[str] = set()
        self._candles: dict[str, LiveMinuteCandle] = {}
        self._aggregate_candles: dict[tuple[str, str], LiveAggregateCandle] = {}
        self._initialized_codes: set[str] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self, stock_code: str) -> None:
        async with self._lock:
            self._subscribed_codes.add(stock_code)
            needs_initialization = stock_code not in self._initialized_codes
        if needs_initialization:
            await self._initialize_candles(stock_code)
            self._initialized_codes.add(stock_code)

        async with self._lock:
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._run())
            connection = self._connection
            if connection is not None:
                await self._send_subscription(connection, stock_code, "1")

    def restore_candle(self, stock_code: str, message: dict[str, object]) -> None:
        candle = message.get("candle")
        if not isinstance(candle, dict):
            return
        try:
            traded_at = datetime.fromisoformat(str(candle["timestamp"]))
            if traded_at.astimezone(KST).date() != datetime.now(KST).date():
                return
            interval = str(message.get("interval", "MINUTE_1"))
            restored = LiveMinuteCandle(
                traded_at=traded_at,
                open_price=int(candle["openPrice"]),
                high_price=int(candle["highPrice"]),
                low_price=int(candle["lowPrice"]),
                close_price=int(candle["closePrice"]),
                volume=int(candle["volume"]),
            )
            if interval == "MINUTE_1":
                self._candles[stock_code] = restored
            elif interval in {"DAILY", "WEEKLY", "MONTHLY", "MINUTE_15"}:
                self._aggregate_candles[(stock_code, interval)] = LiveAggregateCandle(
                    interval=interval,
                    traded_at=_aggregate_bucket(traded_at, interval),
                    open_price=restored.open_price,
                    high_price=restored.high_price,
                    low_price=restored.low_price,
                    close_price=restored.close_price,
                    volume=restored.volume,
                    display_at=traded_at,
                )
        except (KeyError, TypeError, ValueError):
            logger.warning("Invalid KIS candle snapshot ignored: stock_code=%s", stock_code)

    async def unsubscribe(self, stock_code: str) -> None:
        async with self._lock:
            self._subscribed_codes.discard(stock_code)
            connection = self._connection
            has_subscriptions = bool(self._subscribed_codes)
        if connection is not None:
            await self._send_subscription(connection, stock_code, "2")
            if not has_subscriptions:
                await connection.close()
        candle = self._candles.pop(stock_code, None)
        for interval in ("DAILY", "WEEKLY", "MONTHLY", "MINUTE_15"):
            self._aggregate_candles.pop((stock_code, interval), None)
        self._initialized_codes.discard(stock_code)
        if candle is not None:
            await asyncio.to_thread(
                persist_live_minute_candle,
                stock_code,
                candle.as_message(stock_code),
            )

    async def _run(self) -> None:
        try:
            async with websockets.connect(
                f"{kis_token_client.websocket_url().rstrip('/')}{KIS_WEBSOCKET_PATH}",
                open_timeout=10,
                close_timeout=5,
                ping_interval=20,
                ping_timeout=20,
            ) as connection:
                self._connection = connection
                async with self._lock:
                    codes = list(self._subscribed_codes)
                if not codes:
                    await connection.close()
                    return
                for code in codes:
                    await self._send_subscription(connection, code, "1")
                async for raw in connection:
                    await self._handle_message(raw)
        except asyncio.CancelledError:
            raise
        except websockets.exceptions.ConnectionClosedError as exc:
            logger.warning("KIS market WebSocket closed unexpectedly: %s", exc)
        except Exception:
            logger.exception("KIS market WebSocket stopped")
        finally:
            await self._persist_active_minute_candles()
            self._connection = None
            async with self._lock:
                should_retry = bool(self._subscribed_codes)
            if should_retry:
                await asyncio.sleep(2)
                self._task = asyncio.create_task(self._run())

    async def _persist_active_minute_candles(self) -> None:
        candles = list(self._candles.items())
        for stock_code, candle in candles:
            try:
                await asyncio.to_thread(
                    persist_live_minute_candle,
                    stock_code,
                    candle.as_message(stock_code),
                )
            except Exception:
                logger.exception(
                    "Failed to persist active minute candle: stock_code=%s",
                    stock_code,
                )

    async def _send_subscription(self, connection, stock_code: str, tr_type: str) -> None:
        await connection.send(json.dumps({
            "header": {
                "approval_key": await asyncio.to_thread(kis_token_client.approval_key),
                "custtype": "P",
                "tr_type": tr_type,
                "content-type": "utf-8",
            },
            "body": {"input": {"tr_id": KIS_TRADE_TR_ID, "tr_key": stock_code}},
        }))

    async def _handle_message(self, raw: str | bytes) -> None:
        if isinstance(raw, bytes):
            raw = raw.decode()
        if not raw or raw[0] not in {"0", "1"}:
            return
        fields = raw.split("|")
        if len(fields) < 4 or fields[1] != KIS_TRADE_TR_ID:
            return
        values = fields[3].split("^")
        if len(values) < 14:
            return
        stock_code = values[0]
        price = _to_int(values[2])
        change_price = _signed_change(values[3], values[4])
        change_rate = _signed_change_rate(values[3], values[5])
        trade_volume = _to_int(values[12])
        cumulative_volume = _to_int(values[13])
        if price <= 0:
            return

        logger.info(
            "Publishing quote update: stock_code=%s current_price=%s change_price=%s change_rate=%s",
            stock_code,
            price,
            change_price,
            change_rate,
        )
        await publish_quote(stock_code, {
            "type": "quote_update",
            "stockCode": stock_code,
            "currentPrice": price,
            "changePrice": change_price,
            "changeRate": change_rate,
            "changeDirection": _change_direction(change_price),
            "previousClosePrice": price - change_price,
            "updatedAt": datetime.now(KST).isoformat(),
        })
        traded_at = _minute_bucket(datetime.now(KST))
        candle = self._candles.get(stock_code)
        if candle is not None and candle.traded_at != traded_at:
            await asyncio.to_thread(
                persist_live_minute_candle,
                stock_code,
                candle.as_message(stock_code),
            )
        if candle is None or candle.traded_at != traded_at:
            candle = LiveMinuteCandle(traded_at, price, price, price, price, trade_volume)
            self._candles[stock_code] = candle
        else:
            candle.update(price, trade_volume)
        minute_message = candle.as_message(stock_code)
        await store_minute_candle(stock_code, minute_message)
        for interval in ("DAILY", "WEEKLY", "MONTHLY", "MINUTE_15"):
            aggregate = self._aggregate_candles.get((stock_code, interval))
            bucket = _aggregate_bucket(traded_at, interval)
            if aggregate is None or aggregate.traded_at != bucket:
                aggregate = LiveAggregateCandle(
                    interval,
                    bucket,
                    price,
                    price,
                    price,
                    price,
                    cumulative_volume if interval in {"DAILY", "WEEKLY", "MONTHLY"} else trade_volume,
                    last_cumulative_volume=cumulative_volume,
                )
                self._aggregate_candles[(stock_code, interval)] = aggregate
            else:
                aggregate.update(price, trade_volume, cumulative_volume)
            await publish_candle(stock_code, aggregate.as_message(stock_code))

    async def _initialize_candles(self, stock_code: str) -> None:
        try:
            current = await asyncio.to_thread(kis_token_client.current_price, stock_code)
            seeds = await asyncio.to_thread(_load_candle_seeds, stock_code, current)
        except Exception:
            logger.exception("Failed to initialize live candles: stock_code=%s", stock_code)
            return

        for interval, candle in seeds.items():
            self._aggregate_candles[(stock_code, interval)] = candle
            await publish_candle(stock_code, candle.as_message(stock_code))


def _to_int(value: str) -> int:
    try:
        return int(value.replace(",", ""))
    except (TypeError, ValueError):
        return 0


def _to_float(value: str) -> float:
    try:
        return float(value.replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _signed_change(sign: str, value: str) -> int:
    change = abs(_to_int(value))
    return -change if sign in {"4", "5"} else change


def _signed_change_rate(sign: str, value: str) -> float:
    rate = abs(_to_float(value))
    return -rate if sign in {"4", "5"} else rate


def _change_direction(change_price: int) -> str:
    if change_price > 0:
        return "UP"
    if change_price < 0:
        return "DOWN"
    return "EVEN"


def _load_candle_seeds(
    stock_code: str,
    current: dict[str, str],
) -> dict[str, LiveAggregateCandle]:
    now = datetime.now(KST)
    today = now.date()
    current_price = _to_int(current.get("stck_prpr", ""))
    if current_price <= 0:
        return {}
    today_candle = {
        "open": _to_int(current.get("stck_oprc", "")) or current_price,
        "high": _to_int(current.get("stck_hgpr", "")) or current_price,
        "low": _to_int(current.get("stck_lwpr", "")) or current_price,
        "close": current_price,
        "volume": _to_int(current.get("acml_vol", "")),
    }

    with SessionLocal() as db:
        stock = db.scalar(select(Stock).where(Stock.code == stock_code))
        if stock is None:
            return {}
        rows = db.scalars(
            select(StockDailyCandle)
            .where(
                StockDailyCandle.stock_id == stock.id,
                StockDailyCandle.trade_date >= today.replace(day=1),
                StockDailyCandle.trade_date < today,
            )
            .order_by(StockDailyCandle.trade_date)
        ).all()

    seeds: dict[str, LiveAggregateCandle] = {
        "DAILY": LiveAggregateCandle(
            "DAILY", _aggregate_bucket(now, "DAILY"), today_candle["open"],
            today_candle["high"], today_candle["low"], today_candle["close"],
            today_candle["volume"],
            last_cumulative_volume=today_candle["volume"],
        )
    }
    for interval in ("WEEKLY", "MONTHLY"):
        period_rows = [row for row in rows if _same_period(row.trade_date, today, interval)]
        prices = [
            (float(row.open_price), float(row.high_price), float(row.low_price),
             float(row.close_price), row.volume)
            for row in period_rows
        ]
        if prices:
            open_price = int(prices[0][0])
            high_price = int(max(item[1] for item in prices))
            low_price = int(min(item[2] for item in prices))
            volume = sum(item[4] for item in prices)
        else:
            open_price, high_price, low_price, volume = (
                today_candle["open"], today_candle["high"],
                today_candle["low"], 0,
            )
        seeds[interval] = LiveAggregateCandle(
            interval,
            _aggregate_bucket(now, interval),
            open_price,
            max(high_price, today_candle["high"]),
            min(low_price, today_candle["low"]),
            today_candle["close"],
            volume + today_candle["volume"],
            display_at=(
                _date_at_midnight(min(row.trade_date for row in period_rows))
                if interval == "WEEKLY" and period_rows
                else _date_at_midnight(today)
            ),
            last_cumulative_volume=today_candle["volume"],
        )
    return seeds


def _same_period(value: date, today: date, interval: str) -> bool:
    if interval == "MONTHLY":
        return value.year == today.year and value.month == today.month
    return value.isocalendar()[:2] == today.isocalendar()[:2]


def _date_at_midnight(value: date) -> datetime:
    return datetime(value.year, value.month, value.day, tzinfo=KST)


def _minute_bucket(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def _aggregate_bucket(value: datetime, interval: str) -> datetime:
    value = value.astimezone(KST)
    if interval == "MINUTE_15":
        return value.replace(
            minute=value.minute // 15 * 15,
            second=0,
            microsecond=0,
        )
    if interval == "DAILY":
        return value.replace(hour=0, minute=0, second=0, microsecond=0)
    if interval == "MONTHLY":
        return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (value - timedelta(days=value.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
