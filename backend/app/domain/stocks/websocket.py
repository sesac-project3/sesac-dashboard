from fastapi import WebSocket, WebSocketDisconnect

from app.common.security import decode_access_token
from app.domain.stocks.candle_store import (
    MARKET_INTERVALS,
    get_candle_snapshot,
    get_quote_snapshot,
)
from app.domain.stocks.market_subscription import (
    market_websocket_manager,
)


async def handle_market_websocket(websocket: WebSocket, token: str | None) -> None:
    await websocket.accept()
    if not token:
        await websocket.close(code=1008, reason="authentication required")
        return
    try:
        decode_access_token(token)
    except Exception:
        await websocket.close(code=1008, reason="invalid token")
        return
    await market_websocket_manager.connect(websocket)

    try:
        await websocket.send_json({"type": "connected"})
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")
            stock_code = str(message.get("stockCode", "")).strip()
            if message_type in {"subscribe", "unsubscribe"} and stock_code:
                if message_type == "subscribe":
                    await market_websocket_manager.subscribe(websocket, stock_code)
                    snapshots = [
                        await get_candle_snapshot(stock_code, interval)
                        for interval in MARKET_INTERVALS
                    ]
                    quote_snapshot = await get_quote_snapshot(stock_code)
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
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "type and stockCode are required",
                })
    except (WebSocketDisconnect, ValueError):
        await market_websocket_manager.disconnect(websocket)
