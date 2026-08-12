import asyncio
import json
from collections import defaultdict
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.common.security import decode_access_token
from app.core.config import settings

MARKET_CANDLE_CHANNEL_PREFIX = "market:candle:"
MARKET_CANDLE_CHANNEL_PATTERN = f"{MARKET_CANDLE_CHANNEL_PREFIX}*"
MARKET_CANDLE_SNAPSHOT_PREFIX = "market:candle:state:"
MARKET_CANDLE_SNAPSHOT_TTL_SECONDS = 2 * 24 * 60 * 60
MARKET_SUBSCRIBERS_PREFIX = "market:subscribers:"
MARKET_MINUTE_CANDLE_PREFIX = "market:minute-candles:"


class MarketWebSocketManager:
    def __init__(self) -> None:
        self._subscriptions: dict[WebSocket, set[str]] = defaultdict(set)
        self._connection_ids: dict[WebSocket, str] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, token: str | None) -> bool:
        await websocket.accept()
        if not token:
            await websocket.close(code=1008, reason="authentication required")
            return False
        try:
            decode_access_token(token)
        except Exception:
            await websocket.close(code=1008, reason="invalid token")
            return False
        async with self._lock:
            self._connection_ids[websocket] = uuid4().hex
            self._subscriptions[websocket]
        return True

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            stock_codes = self._subscriptions.pop(websocket, set())
            connection_id = self._connection_ids.pop(websocket, None)
        if connection_id is None:
            return
        for stock_code in stock_codes:
            await self._remove_subscriber(stock_code, connection_id)

    async def subscribe(self, websocket: WebSocket, stock_code: str) -> None:
        async with self._lock:
            if stock_code in self._subscriptions[websocket]:
                return
            self._subscriptions[websocket].add(stock_code)
            connection_id = self._connection_ids[websocket]
        is_first_subscriber = await self._add_subscriber(stock_code, connection_id)
        if is_first_subscriber:
            await _get_kis_market_stream().subscribe(stock_code)

    async def unsubscribe(self, websocket: WebSocket, stock_code: str) -> None:
        async with self._lock:
            if stock_code not in self._subscriptions[websocket]:
                return
            self._subscriptions[websocket].discard(stock_code)
            connection_id = self._connection_ids[websocket]
        await self._remove_subscriber(stock_code, connection_id)

    async def _add_subscriber(self, stock_code: str, connection_id: str) -> bool:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            added = await redis.sadd(
                f"{MARKET_SUBSCRIBERS_PREFIX}{stock_code}",
                connection_id,
            )
            return added == 1
        finally:
            await redis.aclose()

    async def _remove_subscriber(self, stock_code: str, connection_id: str) -> None:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            await redis.srem(f"{MARKET_SUBSCRIBERS_PREFIX}{stock_code}", connection_id)
            remaining = await redis.scard(f"{MARKET_SUBSCRIBERS_PREFIX}{stock_code}")
            if remaining == 0:
                await redis.delete(f"{MARKET_SUBSCRIBERS_PREFIX}{stock_code}")
                await _get_kis_market_stream().unsubscribe(stock_code)
        finally:
            await redis.aclose()

    async def broadcast(self, stock_code: str, message: dict[str, object]) -> None:
        async with self._lock:
            targets = [
                websocket
                for websocket, subscriptions in self._subscriptions.items()
                if stock_code in subscriptions
            ]
        await asyncio.gather(
            *(websocket.send_json(message) for websocket in targets),
            return_exceptions=True,
        )

    async def publish_candle(self, stock_code: str, message: dict[str, object]) -> None:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            payload = json.dumps(message, ensure_ascii=False)
            candle = message.get("candle", {})
            timestamp = candle.get("timestamp") if isinstance(candle, dict) else None
            if message.get("interval") == "MINUTE_1" and isinstance(timestamp, str):
                traded_date = timestamp[:10].replace("-", "")
                await redis.hset(
                    f"{MARKET_MINUTE_CANDLE_PREFIX}{stock_code}:{traded_date}",
                    timestamp,
                    payload,
                )
                await redis.expire(
                    f"{MARKET_MINUTE_CANDLE_PREFIX}{stock_code}:{traded_date}",
                    MARKET_CANDLE_SNAPSHOT_TTL_SECONDS,
                )
            await redis.set(
                f"{MARKET_CANDLE_SNAPSHOT_PREFIX}{stock_code}",
                payload,
                ex=MARKET_CANDLE_SNAPSHOT_TTL_SECONDS,
            )
            await redis.publish(
                f"{MARKET_CANDLE_CHANNEL_PREFIX}{stock_code}",
                payload,
            )
        finally:
            await redis.aclose()

    async def get_candle_snapshot(self, stock_code: str) -> dict[str, object] | None:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            payload = await redis.get(f"{MARKET_CANDLE_SNAPSHOT_PREFIX}{stock_code}")
            return json.loads(payload) if payload else None
        finally:
            await redis.aclose()

    async def get_minute_candle_messages(
        self,
        stock_code: str,
        traded_date: str,
    ) -> list[dict[str, object]]:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            values = await redis.hvals(
                f"{MARKET_MINUTE_CANDLE_PREFIX}{stock_code}:{traded_date}"
            )
            messages = [json.loads(value) for value in values]
            return sorted(
                messages,
                key=lambda message: str(message.get("candle", {}).get("timestamp", "")),
            )
        finally:
            await redis.aclose()

    async def active_stock_codes(self) -> list[str]:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            codes: list[str] = []
            async for key in redis.scan_iter(match=f"{MARKET_SUBSCRIBERS_PREFIX}*"):
                if await redis.scard(key):
                    codes.append(key.removeprefix(MARKET_SUBSCRIBERS_PREFIX))
            return codes
        finally:
            await redis.aclose()


market_websocket_manager = MarketWebSocketManager()
_kis_market_stream = None


def _get_kis_market_stream():
    global _kis_market_stream
    if _kis_market_stream is None:
        from app.domain.stocks.kis_stream import KisMarketStream

        _kis_market_stream = KisMarketStream(market_websocket_manager)
    return _kis_market_stream


async def subscribe_candle_events(stop_event: asyncio.Event) -> None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.psubscribe(MARKET_CANDLE_CHANNEL_PATTERN)
    try:
        while not stop_event.is_set():
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not message:
                continue
            channel = str(message["channel"])
            stock_code = channel.removeprefix(MARKET_CANDLE_CHANNEL_PREFIX)
            await market_websocket_manager.broadcast(stock_code, json.loads(message["data"]))
    finally:
        await pubsub.punsubscribe(MARKET_CANDLE_CHANNEL_PATTERN)
        await pubsub.aclose()
        await redis.aclose()


async def restore_kis_subscriptions() -> None:
    manager = market_websocket_manager
    stream = _get_kis_market_stream()
    for stock_code in await manager.active_stock_codes():
        snapshot = await manager.get_candle_snapshot(stock_code)
        if snapshot is not None:
            stream.restore_candle(stock_code, snapshot)
        await stream.subscribe(stock_code)


async def handle_market_websocket(websocket: WebSocket, token: str | None) -> None:
    if not await market_websocket_manager.connect(websocket, token):
        return

    try:
        await websocket.send_json({"type": "connected"})
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")
            stock_code = str(message.get("stockCode", "")).strip()
            if message_type in {"subscribe", "unsubscribe"} and stock_code:
                if message_type == "subscribe":
                    await market_websocket_manager.subscribe(websocket, stock_code)
                    snapshot = await market_websocket_manager.get_candle_snapshot(stock_code)
                else:
                    await market_websocket_manager.unsubscribe(websocket, stock_code)
                    snapshot = None
                await websocket.send_json({
                    "type": f"{message_type}d",
                    "stockCode": stock_code,
                })
                if snapshot is not None:
                    await websocket.send_json({
                        **snapshot,
                        "type": "candle_snapshot",
                    })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "type and stockCode are required",
                })
    except (WebSocketDisconnect, ValueError):
        await market_websocket_manager.disconnect(websocket)
