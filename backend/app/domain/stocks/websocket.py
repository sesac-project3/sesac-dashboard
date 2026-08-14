import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import WebSocket, WebSocketDisconnect

from app.common.security import decode_access_token

from app.domain.stocks.candle_store import (
    MARKET_INTERVALS,
    get_candle_snapshot,
    get_quote_snapshot,
)
from app.domain.stocks.market_subscription import market_websocket_manager
from app.core.kis import kis_token_client

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")


def _to_int(value: object) -> int:
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0


def _to_float(value: object) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


async def _get_quote_snapshot_from_rest(stock_code: str) -> dict[str, object] | None:
    try:
        current = await asyncio.to_thread(kis_token_client.current_price, stock_code)
    except Exception:
        logger.exception("KIS quote snapshot fallback failed: stock_code=%s", stock_code)
        return None

    price = _to_int(current.get("stck_prpr"))
    if price <= 0:
        return None
    sign = str(current.get("prdy_vrss_sign", "3"))
    change_price = abs(_to_int(current.get("prdy_vrss")))
    if sign in {"4", "5"}:
        change_price = -change_price
    change_rate = abs(_to_float(current.get("prdy_ctrt")))
    if sign in {"4", "5"}:
        change_rate = -change_rate
    return {
        "type": "quote_snapshot",
        "stockCode": stock_code,
        "currentPrice": price,
        "changePrice": change_price,
        "changeRate": change_rate,
        "changeDirection": "UP" if change_price > 0 else "DOWN" if change_price < 0 else "EVEN",
        "previousClosePrice": price - change_price,
        "updatedAt": datetime.now(KST).isoformat(),
    }


async def handle_market_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    user_id: int | None = None
    logger.info("Market WS accepted: client=%s", websocket.client)

    try:
        auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=5)
        if auth_message.get("type") != "auth":
            logger.warning("Market WS auth rejected: reason=authentication required client=%s", websocket.client)
            await websocket.close(code=1008, reason="authentication required")
            return
        token = str(auth_message.get("accessToken", ""))
        if not token:
            logger.warning("Market WS auth rejected: reason=missing token client=%s", websocket.client)
            await websocket.close(code=1008, reason="authentication required")
            return
        try:
            user_id = decode_access_token(token)
        except Exception:
            logger.warning("Market WS auth rejected: reason=invalid token client=%s", websocket.client)
            await websocket.close(code=1008, reason="invalid access token")
            return

        if not await market_websocket_manager.connect(websocket, user_id):
            logger.warning("Market WS connection rejected: user_id=%s reason=connection limit exceeded", user_id)
            await websocket.close(code=1008, reason="connection limit exceeded")
            return

        logger.info("Market WS authenticated: user_id=%s", user_id)
        await websocket.send_json({"type": "authenticated"})
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")
            stock_code = str(message.get("stockCode", "")).strip()
            if message_type in {"subscribe", "unsubscribe"} and stock_code:
                logger.info(
                    "Market WS subscription request: user_id=%s action=%s stock_code=%s",
                    user_id,
                    message_type,
                    stock_code,
                )
                if message_type == "subscribe":
                    await market_websocket_manager.subscribe(websocket, stock_code)
                    snapshots = [
                        await get_candle_snapshot(stock_code, interval)
                        for interval in MARKET_INTERVALS
                    ]
                    quote_snapshot = await get_quote_snapshot(stock_code)
                    if quote_snapshot is None:
                        logger.info("Quote snapshot missing; using KIS REST fallback: stock_code=%s", stock_code)
                        quote_snapshot = await _get_quote_snapshot_from_rest(stock_code)
                else:
                    await market_websocket_manager.unsubscribe(websocket, stock_code)
                    snapshots = []
                    quote_snapshot = None
                await websocket.send_json({
                    "type": f"{message_type}d",
                    "stockCode": stock_code,
                })
                for snapshot in snapshots:
                    if snapshot is None:
                        continue
                    await websocket.send_json({
                        **snapshot,
                        "type": "candle_snapshot",
                    })
                if quote_snapshot is not None:
                    await websocket.send_json({
                        **quote_snapshot,
                        "type": "quote_snapshot",
                    })
                logger.info(
                    "Market WS subscription response: user_id=%s action=%s stock_code=%s candles=%s quote=%s",
                    user_id,
                    message_type,
                    stock_code,
                    len(snapshots),
                    quote_snapshot is not None,
                )
            else:
                logger.warning("Market WS invalid message: user_id=%s type=%s", user_id, message_type)
                await websocket.send_json({
                    "type": "error",
                    "message": "type and stockCode are required",
                })
    except asyncio.TimeoutError:
        logger.warning("Market WS auth timeout: client=%s", websocket.client)
        await websocket.close(code=1008, reason="authentication timeout")
        await market_websocket_manager.disconnect(websocket)
    except WebSocketDisconnect as exc:
        logger.info("Market WS disconnected: user_id=%s code=%s", user_id, exc.code)
        await market_websocket_manager.disconnect(websocket)
    except ValueError:
        logger.warning("Market WS closed after invalid message: user_id=%s", user_id)
        await market_websocket_manager.disconnect(websocket)
