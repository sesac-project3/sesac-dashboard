"""KIS REST/WebSocket 연결 확인용 수동 테스트.

실행:
    PYTHONPATH=backend python3 backend/tests/manual_kis_connection.py rest
    PYTHONPATH=backend python3 backend/tests/manual_kis_connection.py websocket
    PYTHONPATH=backend python3 backend/tests/manual_kis_connection.py all
"""

import argparse
import asyncio
import json

import httpx

from app.common.exceptions import BusinessException
from app.core.config import settings
from app.core.kis import kis_token_client


KOSPI_CODE = "0001"
INDEX_PATH = "/uapi/domestic-stock/v1/quotations/inquire-index-price"
INDEX_TR_ID = "FHPUP02100000"
INDEX_WS_TR_ID = "H0UPCNT0"
WEBSOCKET_PATH = "/tryitout"


def test_rest() -> None:
    if not settings.kis_app_key or not settings.kis_app_secret:
        raise RuntimeError("backend/.env의 KIS_APP_KEY와 KIS_APP_SECRET을 입력하세요.")

    access_token = kis_token_client.access_token()
    response = httpx.get(
        f"{settings.kis_base_url.rstrip('/')}{INDEX_PATH}",
        headers={
            "authorization": f"Bearer {access_token}",
            "appkey": settings.kis_app_key,
            "appsecret": settings.kis_app_secret,
            "tr_id": INDEX_TR_ID,
            "custtype": "P",
            "content-type": "application/json; charset=utf-8",
            "Accept": "text/plain",
            "charset": "UTF-8",
            "User-Agent": settings.kis_user_agent,
        },
        params={
            "FID_COND_MRKT_DIV_CODE": "U",
            "FID_INPUT_ISCD": KOSPI_CODE,
        },
        timeout=10.0,
    )
    response.raise_for_status()
    body = response.json()
    output = body.get("output", {})
    print(f"[REST] KOSPI 지수: {output.get('bstp_nmix_prpr')}")


async def test_websocket() -> None:
    if not settings.kis_app_key or not settings.kis_app_secret:
        raise RuntimeError("backend/.env의 KIS_APP_KEY와 KIS_APP_SECRET을 입력하세요.")

    try:
        import websockets
    except ImportError as exc:
        raise RuntimeError("websockets 패키지가 필요합니다. uvicorn[standard] 설치 후 다시 실행하세요.") from exc

    approval_key = kis_token_client.approval_key()
    async with websockets.connect(
        f"{kis_token_client.websocket_url().rstrip('/')}{WEBSOCKET_PATH}",
        open_timeout=10,
        close_timeout=5,
    ) as connection:
        await connection.send(json.dumps({
            "header": {
                "approval_key": approval_key,
                "custtype": "P",
                "tr_type": "1",
                "content-type": "utf-8",
            },
            "body": {"input": {"tr_id": INDEX_WS_TR_ID, "tr_key": KOSPI_CODE}},
        }))

        while True:
            try:
                raw = await asyncio.wait_for(connection.recv(), timeout=30)
            except asyncio.TimeoutError as exc:
                raise RuntimeError("웹소켓 연결 후 30초 동안 KOSPI 데이터가 오지 않았습니다.") from exc

            if isinstance(raw, bytes):
                raw = raw.decode()
            if not raw or raw[0] not in {"0", "1"}:
                print(f"[WebSocket 제어응답] {raw}")
                continue

            fields = raw.split("|")
            if len(fields) < 4 or fields[1] != INDEX_WS_TR_ID:
                continue

            values = fields[3].split("^")
            print(f"[WebSocket] KOSPI 지수: {values[2]}")
            return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=("rest", "websocket", "all"))
    args = parser.parse_args()

    try:
        if args.target in {"rest", "all"}:
            test_rest()
        if args.target in {"websocket", "all"}:
            asyncio.run(test_websocket())
    except RuntimeError as exc:
        print(f"테스트 실패: {exc}")
        raise SystemExit(1) from exc
    except BusinessException as exc:
        cause = exc.__cause__
        if isinstance(cause, httpx.HTTPStatusError):
            print(f"KIS 인증 실패: HTTP {cause.response.status_code}")
            print(cause.response.text)
        elif isinstance(cause, httpx.HTTPError):
            print(f"KIS 요청 실패: {cause}")
        else:
            print("KIS 인증에 실패했습니다. AppKey/AppSecret과 API 환경을 확인하세요.")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
