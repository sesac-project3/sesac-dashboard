import json
import logging
from datetime import datetime, timedelta, timezone
from threading import Lock
from zoneinfo import ZoneInfo

import httpx

from app.common.exceptions import BusinessException, ErrorCode
from app.core.config import settings
from app.core.kis_endpoints import DAILY_CANDLE_PATH

logger = logging.getLogger(__name__)


class KisTokenClient:
    """KIS REST/WebSocket 인증키 발급과 메모리 캐시를 담당한다."""

    _TOKEN_PATH = "/oauth2/tokenP"
    _APPROVAL_PATH = "/oauth2/Approval"

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._expires_at: datetime | None = None
        self._approval_key: str | None = None
        self._approval_expires_at: datetime | None = None
        self._lock = Lock()

    def access_token(self) -> str:
        now = datetime.now(timezone.utc)
        if self._access_token and self._expires_at and now < self._expires_at:
            return self._access_token

        with self._lock:
            now = datetime.now(timezone.utc)
            if self._access_token and self._expires_at and now < self._expires_at:
                return self._access_token
            return self._issue_token(now)

    def approval_key(self) -> str:
        now = datetime.now(timezone.utc)
        if self._approval_key and self._approval_expires_at and now < self._approval_expires_at:
            return self._approval_key

        with self._lock:
            now = datetime.now(timezone.utc)
            if self._approval_key and self._approval_expires_at and now < self._approval_expires_at:
                return self._approval_key
            return self._issue_approval_key(now)

    def websocket_url(self) -> str:
        return settings.kis_websocket_url

    def daily_candles(self, stock_code: str, start_date: str, end_date: str) -> list[dict[str, str]]:
        response = httpx.get(
            f"{settings.kis_base_url.rstrip('/')}{DAILY_CANDLE_PATH}",
            params={
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": stock_code,
                "fid_input_date_1": start_date,
                "fid_input_date_2": end_date,
                "fid_period_div_code": "D",
                "fid_org_adj_prc": "1",
            },
            headers={
                "authorization": f"Bearer {self.access_token()}",
                "appkey": settings.kis_app_key,
                "appsecret": settings.kis_app_secret,
                "tr_id": "FHKST03010100",
                "custtype": "P",
            },
            timeout=20.0,
        )
        try:
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.error(
                "KIS daily candle request failed: %s, body=%s",
                _http_error_summary(response, exc),
                _response_error_body(response),
            )
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE) from exc

        if body.get("rt_cd") not in (None, "0"):
            logger.error(
                "KIS daily candle API returned an error: rt_cd=%s, msg_cd=%s, msg=%s",
                body.get("rt_cd"),
                body.get("msg_cd"),
                body.get("msg1"),
            )
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE)
        return body.get("output2", [])

    def _issue_token(self, now: datetime) -> str:
        if not settings.kis_app_key or not settings.kis_app_secret:
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE)

        try:
            response = httpx.post(
                f"{settings.kis_base_url.rstrip('/')}{self._TOKEN_PATH}",
                content=json.dumps({
                    "grant_type": "client_credentials",
                    "appkey": settings.kis_app_key,
                    "appsecret": settings.kis_app_secret,
                }),
                headers=self._headers(),
                timeout=10.0,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.error(
                "KIS access token request failed: %s, body=%s",
                _http_error_summary(response, exc),
                _response_error_body(response),
            )
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE) from exc

        if not body.get("access_token"):
            logger.error(
                "KIS access token response did not contain a token: rt_cd=%s, msg_cd=%s, msg=%s",
                body.get("rt_cd"),
                body.get("msg_cd"),
                body.get("msg1"),
            )
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE)

        self._access_token = body["access_token"]
        self._expires_at = self._parse_expiry(body.get("access_token_token_expired"), now)
        if self._expires_at is None:
            expires_in = int(body.get("expires_in", 86400))
            self._expires_at = now + timedelta(seconds=max(60, expires_in - 60))

        logger.info(
            "KIS access token issued successfully; expires_at=%s",
            self._expires_at.isoformat(),
        )
        return self._access_token

    @staticmethod
    def _parse_expiry(value: object, now: datetime) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None

        try:
            expiry = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=ZoneInfo("Asia/Seoul")
            ).astimezone(timezone.utc)
        except ValueError:
            return None

        # 만료 직전 재발급을 피하기 위해 1분 여유를 둔다.
        return max(now + timedelta(seconds=60), expiry - timedelta(minutes=1))

    def _issue_approval_key(self, now: datetime) -> str:
        if not settings.kis_app_key or not settings.kis_app_secret:
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE)

        try:
            response = httpx.post(
                f"{settings.kis_base_url.rstrip('/')}{self._APPROVAL_PATH}",
                content=json.dumps({
                    "grant_type": "client_credentials",
                    "appkey": settings.kis_app_key,
                    "secretkey": settings.kis_app_secret,
                }),
                headers=self._headers(),
                timeout=10.0,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE) from exc

        approval_key = body.get("approval_key")
        if not approval_key:
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE)

        self._approval_key = approval_key
        self._approval_expires_at = now + timedelta(hours=23)
        return approval_key

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "text/plain",
            "charset": "UTF-8",
            "User-Agent": settings.kis_user_agent,
        }


kis_token_client = KisTokenClient()


def _http_error_summary(response: httpx.Response, exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"status={response.status_code}"
    return type(exc).__name__


def _response_error_body(response: httpx.Response) -> str:
    return response.text[:500].replace("\n", " ")
