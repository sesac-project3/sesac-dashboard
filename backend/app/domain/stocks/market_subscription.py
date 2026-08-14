import asyncio
import logging
from collections import defaultdict
from uuid import uuid4

from fastapi import WebSocket
from redis.asyncio import Redis

from app.core.config import settings
from app.domain.stocks.candle_store import (
    MARKET_INTERVALS,
    get_candle_snapshot,
    subscribe_candle_events as subscribe_market_events_from_store,
)

MARKET_SUBSCRIBERS_PREFIX = "market:subscribers:"
MARKET_INDEX_SUBSCRIBERS_PREFIX = "market:index-subscribers:"
MAX_CONNECTIONS_PER_USER = 5
logger = logging.getLogger(__name__)


class MarketWebSocketManager:
    def __init__(self) -> None:
        self._subscriptions: dict[WebSocket, set[str]] = defaultdict(set)
        self._index_subscriptions: dict[WebSocket, set[str]] = defaultdict(set)
        self._connection_ids: dict[WebSocket, str] = {}
        self._user_connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int) -> bool:
        async with self._lock:
            if len(self._user_connections[user_id]) >= MAX_CONNECTIONS_PER_USER:
                logger.warning("Market WS connection limit: user_id=%s limit=%s", user_id, MAX_CONNECTIONS_PER_USER)
                return False
            self._connection_ids[websocket] = uuid4().hex
            self._subscriptions[websocket]
            self._user_connections[user_id].add(websocket)
            websocket.state.user_id = user_id
            logger.info(
                "Market WS registered: user_id=%s active_connections=%s",
                user_id,
                len(self._user_connections[user_id]),
            )
            return True

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            stock_codes = self._subscriptions.pop(websocket, set())
            index_codes = self._index_subscriptions.pop(websocket, set())
            connection_id = self._connection_ids.pop(websocket, None)
            user_id = getattr(websocket.state, "user_id", None)
            if user_id is not None:
                connections = self._user_connections[user_id]
                connections.discard(websocket)
                if not connections:
                    self._user_connections.pop(user_id, None)
        if connection_id is None:
            return
        logger.info(
            "Market WS unregistered: user_id=%s subscriptions=%s",
            user_id,
            sorted(stock_codes),
        )
        for stock_code in stock_codes:
            await self._remove_subscriber(stock_code, connection_id)
        for index_code in index_codes:
            await self._remove_index_subscriber(index_code, connection_id)

    async def subscribe(self, websocket: WebSocket, stock_code: str) -> None:
        async with self._lock:
            if stock_code in self._subscriptions[websocket]:
                return
            self._subscriptions[websocket].add(stock_code)
            connection_id = self._connection_ids[websocket]
        if await self._add_subscriber(stock_code, connection_id):
            await get_kis_market_stream().subscribe(stock_code)
        logger.info("Market WS subscribed: user_id=%s stock_code=%s", websocket.state.user_id, stock_code)

    async def unsubscribe(self, websocket: WebSocket, stock_code: str) -> None:
        async with self._lock:
            if stock_code not in self._subscriptions[websocket]:
                return
            self._subscriptions[websocket].discard(stock_code)
            connection_id = self._connection_ids[websocket]
        await self._remove_subscriber(stock_code, connection_id)
        logger.info("Market WS unsubscribed: user_id=%s stock_code=%s", websocket.state.user_id, stock_code)

    async def subscribe_index(self, websocket: WebSocket, index_code: str) -> None:
        async with self._lock:
            if index_code in self._index_subscriptions[websocket]:
                return
            self._index_subscriptions[websocket].add(index_code)
            connection_id = self._connection_ids[websocket]
        if await self._add_index_subscriber(index_code, connection_id):
            await get_kis_market_stream().subscribe_index(index_code)
        logger.info("Market WS index subscribed: user_id=%s index_code=%s", websocket.state.user_id, index_code)

    async def unsubscribe_index(self, websocket: WebSocket, index_code: str) -> None:
        async with self._lock:
            if index_code not in self._index_subscriptions[websocket]:
                return
            self._index_subscriptions[websocket].discard(index_code)
            connection_id = self._connection_ids[websocket]
        await self._remove_index_subscriber(index_code, connection_id)
        logger.info("Market WS index unsubscribed: user_id=%s index_code=%s", websocket.state.user_id, index_code)

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
                await get_kis_market_stream().unsubscribe(stock_code)
        finally:
            await redis.aclose()

    async def _add_index_subscriber(self, index_code: str, connection_id: str) -> bool:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            return await redis.sadd(
                f"{MARKET_INDEX_SUBSCRIBERS_PREFIX}{index_code}", connection_id
            ) == 1
        finally:
            await redis.aclose()

    async def _remove_index_subscriber(self, index_code: str, connection_id: str) -> None:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            await redis.srem(f"{MARKET_INDEX_SUBSCRIBERS_PREFIX}{index_code}", connection_id)
            remaining = await redis.scard(f"{MARKET_INDEX_SUBSCRIBERS_PREFIX}{index_code}")
            if remaining == 0:
                await redis.delete(f"{MARKET_INDEX_SUBSCRIBERS_PREFIX}{index_code}")
                await get_kis_market_stream().unsubscribe_index(index_code)
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

    async def broadcast_index(self, index_code: str, message: dict[str, object]) -> None:
        async with self._lock:
            targets = [
                websocket
                for websocket, subscriptions in self._index_subscriptions.items()
                if index_code in subscriptions
            ]
        await asyncio.gather(
            *(websocket.send_json(message) for websocket in targets),
            return_exceptions=True,
        )

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

    async def active_index_codes(self) -> list[str]:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            codes: list[str] = []
            async for key in redis.scan_iter(match=f"{MARKET_INDEX_SUBSCRIBERS_PREFIX}*"):
                if await redis.scard(key):
                    codes.append(key.removeprefix(MARKET_INDEX_SUBSCRIBERS_PREFIX))
            return codes
        finally:
            await redis.aclose()


market_websocket_manager = MarketWebSocketManager()
_kis_market_stream = None


def get_kis_market_stream():
    global _kis_market_stream
    if _kis_market_stream is None:
        from app.domain.stocks.kis_stream import KisMarketStream

        _kis_market_stream = KisMarketStream(market_websocket_manager)
    return _kis_market_stream


async def subscribe_candle_events(stop_event: asyncio.Event) -> None:
    await subscribe_market_events_from_store(
        stop_event,
        market_websocket_manager.broadcast,
        market_websocket_manager.broadcast_index,
    )


async def restore_kis_subscriptions() -> None:
    stream = get_kis_market_stream()
    for stock_code in await market_websocket_manager.active_stock_codes():
        for interval in (*MARKET_INTERVALS, "MINUTE_1"):
            snapshot = await get_candle_snapshot(stock_code, interval)
            if snapshot is not None:
                stream.restore_candle(stock_code, snapshot)
        await stream.subscribe(stock_code)
    for index_code in await market_websocket_manager.active_index_codes():
        await stream.subscribe_index(index_code)
