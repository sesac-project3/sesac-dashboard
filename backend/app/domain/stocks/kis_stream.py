import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

import websockets

from app.core.kis import kis_token_client
from app.domain.stocks.websocket import MarketWebSocketManager

logger = logging.getLogger(__name__)

KIS_WEBSOCKET_PATH = "/tryitout"
KIS_TRADE_TR_ID = "H0STCNT0"
KST = ZoneInfo("Asia/Seoul")


@dataclass
class LiveDailyCandle:
    trade_date: date
    open_price: int
    high_price: int
    low_price: int
    close_price: int
    volume: int

    def update(self, price: int, volume: int) -> None:
        self.high_price = max(self.high_price, price)
        self.low_price = min(self.low_price, price)
        self.close_price = price
        self.volume = volume

    def as_message(self, stock_code: str) -> dict[str, object]:
        return {
            "type": "candle_update",
            "stockCode": stock_code,
            "interval": "DAILY",
            "candle": {
                "timestamp": self.trade_date.isoformat(),
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
        self._candles: dict[str, LiveDailyCandle] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, stock_code: str) -> None:
        async with self._lock:
            self._subscribed_codes.add(stock_code)
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
            trade_date = date.fromisoformat(str(candle["timestamp"]))
            if trade_date != datetime.now(KST).date():
                return
            self._candles[stock_code] = LiveDailyCandle(
                trade_date=trade_date,
                open_price=int(candle["openPrice"]),
                high_price=int(candle["highPrice"]),
                low_price=int(candle["lowPrice"]),
                close_price=int(candle["closePrice"]),
                volume=int(candle["volume"]),
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

    async def _run(self) -> None:
        try:
            async with websockets.connect(
                f"{kis_token_client.websocket_url().rstrip('/')}{KIS_WEBSOCKET_PATH}",
                open_timeout=10,
                close_timeout=5,
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
        except Exception:
            logger.exception("KIS market WebSocket stopped")
        finally:
            self._connection = None
            async with self._lock:
                should_retry = bool(self._subscribed_codes)
            if should_retry:
                await asyncio.sleep(2)
                self._task = asyncio.create_task(self._run())

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
        volume = _to_int(values[13])
        if price <= 0:
            return
        today = datetime.now(KST).date()
        candle = self._candles.get(stock_code)
        if candle is None or candle.trade_date != today:
            candle = LiveDailyCandle(today, price, price, price, price, volume)
            self._candles[stock_code] = candle
        else:
            candle.update(price, volume)
        await self._manager.publish_candle(stock_code, candle.as_message(stock_code))


def _to_int(value: str) -> int:
    try:
        return int(value.replace(",", ""))
    except (TypeError, ValueError):
        return 0
