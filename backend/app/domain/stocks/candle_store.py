import asyncio
import json
from collections.abc import Awaitable, Callable

from redis.asyncio import Redis

from app.core.config import settings

MARKET_CANDLE_CHANNEL_PREFIX = "market:candle:"
MARKET_CANDLE_CHANNEL_PATTERN = f"{MARKET_CANDLE_CHANNEL_PREFIX}*"
MARKET_INDEX_CHANNEL_PREFIX = "market:index:"
MARKET_INDEX_CHANNEL_PATTERN = f"{MARKET_INDEX_CHANNEL_PREFIX}*"
MARKET_CANDLE_SNAPSHOT_PREFIX = "market:candle:state:"
MARKET_INDEX_SNAPSHOT_PREFIX = "market:index:state:"
MARKET_QUOTE_SNAPSHOT_PREFIX = "market:quote:state:"
MARKET_CANDLE_SNAPSHOT_TTL_SECONDS = 2 * 24 * 60 * 60
MARKET_MINUTE_CANDLE_PREFIX = "market:minute-candles:"
MARKET_INTERVALS = ("DAILY", "WEEKLY", "MONTHLY", "MINUTE_15")


async def publish_candle(stock_code: str, message: dict[str, object]) -> None:
    payload = json.dumps(message, ensure_ascii=False)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        interval = str(message.get("interval", "MINUTE_1"))
        await redis.set(
            f"{MARKET_CANDLE_SNAPSHOT_PREFIX}{stock_code}:{interval}",
            payload,
            ex=MARKET_CANDLE_SNAPSHOT_TTL_SECONDS,
        )
        await redis.publish(f"{MARKET_CANDLE_CHANNEL_PREFIX}{stock_code}", payload)
    finally:
        await redis.aclose()


async def publish_quote(stock_code: str, message: dict[str, object]) -> None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        payload = json.dumps(message, ensure_ascii=False)
        await redis.set(
            f"{MARKET_QUOTE_SNAPSHOT_PREFIX}{stock_code}",
            payload,
            ex=MARKET_CANDLE_SNAPSHOT_TTL_SECONDS,
        )
        await redis.publish(
            f"{MARKET_CANDLE_CHANNEL_PREFIX}{stock_code}",
            payload,
        )
    finally:
        await redis.aclose()


async def get_quote_snapshot(stock_code: str) -> dict[str, object] | None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        payload = await redis.get(f"{MARKET_QUOTE_SNAPSHOT_PREFIX}{stock_code}")
        return json.loads(payload) if payload else None
    finally:
        await redis.aclose()


async def publish_index(index_code: str, message: dict[str, object]) -> None:
    payload = json.dumps(message, ensure_ascii=False)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.set(
            f"{MARKET_INDEX_SNAPSHOT_PREFIX}{index_code}",
            payload,
            ex=MARKET_CANDLE_SNAPSHOT_TTL_SECONDS,
        )
        await redis.publish(f"{MARKET_INDEX_CHANNEL_PREFIX}{index_code}", payload)
    finally:
        await redis.aclose()


async def get_index_snapshot(index_code: str) -> dict[str, object] | None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        payload = await redis.get(f"{MARKET_INDEX_SNAPSHOT_PREFIX}{index_code}")
        return json.loads(payload) if payload else None
    finally:
        await redis.aclose()


async def store_minute_candle(stock_code: str, message: dict[str, object]) -> None:
    candle = message.get("candle", {})
    timestamp = candle.get("timestamp") if isinstance(candle, dict) else None
    if not isinstance(timestamp, str):
        return
    key = f"{MARKET_MINUTE_CANDLE_PREFIX}{stock_code}:{timestamp[:10].replace('-', '')}"
    payload = json.dumps(message, ensure_ascii=False)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.hset(key, timestamp, payload)
        await redis.expire(key, MARKET_CANDLE_SNAPSHOT_TTL_SECONDS)
        await redis.set(
            f"{MARKET_CANDLE_SNAPSHOT_PREFIX}{stock_code}:MINUTE_1",
            payload,
            ex=MARKET_CANDLE_SNAPSHOT_TTL_SECONDS,
        )
    finally:
        await redis.aclose()


async def get_candle_snapshot(
    stock_code: str,
    interval: str = "MINUTE_1",
) -> dict[str, object] | None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        payload = await redis.get(f"{MARKET_CANDLE_SNAPSHOT_PREFIX}{stock_code}:{interval}")
        return json.loads(payload) if payload else None
    finally:
        await redis.aclose()


async def get_minute_candle_messages(
    stock_code: str,
    traded_date: str,
) -> list[dict[str, object]]:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        values = await redis.hvals(f"{MARKET_MINUTE_CANDLE_PREFIX}{stock_code}:{traded_date}")
        messages = [json.loads(value) for value in values]
        return sorted(
            messages,
            key=lambda message: str(message.get("candle", {}).get("timestamp", "")),
        )
    finally:
        await redis.aclose()


async def subscribe_candle_events(
    stop_event: asyncio.Event,
    broadcast: Callable[[str, dict[str, object]], Awaitable[None]],
    broadcast_index: Callable[[str, dict[str, object]], Awaitable[None]] | None = None,
) -> None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.psubscribe(MARKET_CANDLE_CHANNEL_PATTERN, MARKET_INDEX_CHANNEL_PATTERN)
    try:
        while not stop_event.is_set():
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not message:
                continue
            channel = str(message["channel"])
            payload = json.loads(message["data"])
            if channel.startswith(MARKET_INDEX_CHANNEL_PREFIX):
                if broadcast_index is not None:
                    await broadcast_index(channel.removeprefix(MARKET_INDEX_CHANNEL_PREFIX), payload)
            else:
                await broadcast(channel.removeprefix(MARKET_CANDLE_CHANNEL_PREFIX), payload)
    finally:
        await pubsub.punsubscribe(MARKET_CANDLE_CHANNEL_PATTERN, MARKET_INDEX_CHANNEL_PATTERN)
        await pubsub.aclose()
        await redis.aclose()
