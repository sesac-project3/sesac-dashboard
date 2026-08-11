import json
from datetime import datetime, timedelta, timezone
from threading import Lock

import httpx

from app.common.exceptions import BusinessException, ErrorCode
from app.core.config import settings


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
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE) from exc

        if not body.get("access_token"):
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE)

        self._access_token = body["access_token"]
        expires_in = int(body.get("expires_in", 86400))
        self._expires_at = now + timedelta(seconds=max(60, expires_in - 60))
        return self._access_token

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
