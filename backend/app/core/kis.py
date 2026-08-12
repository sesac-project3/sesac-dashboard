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

    def fetch_income_statement(self, stock_code: str, division: str = "0") -> list[dict]:
        """
        KIS 국내주식 손익계산서 API (/uapi/domestic-stock/v1/finance/income-statement) 호출.
        파라미터:
        - fid_div_cls_code: "0" (연간), "1" (분기)
        - fid_cond_mrkt_div_code: "J" (주식)
        - fid_input_iscd: stock_code (예: "000660")
        - tr_id: "FHKST66430200"
        반환: 결산년도(stac_yymm/fiscal_year), 매출액(revenue), 영업이익(operating_profit), 영업이익률(operating_margin)
        """
        if not settings.kis_app_key or not settings.kis_app_secret:
            return []

        url = f"{settings.kis_base_url.rstrip('/')}/uapi/domestic-stock/v1/finance/income-statement"
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token()}",
            "appkey": settings.kis_app_key,
            "appsecret": settings.kis_app_secret,
            "tr_id": "FHKST66430200",
            "custtype": "P",
            "User-Agent": settings.kis_user_agent,
        }
        params = {
            "fid_div_cls_code": division,
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock_code,
        }

        try:
            response = httpx.get(url, headers=headers, params=params, timeout=10.0)
            response.raise_for_status()
            body = response.json()
            output = body.get("output", [])
            if not isinstance(output, list):
                output = [output] if output else []

            results = []
            for item in output:
                stac_yymm = str(item.get("stac_yymm", ""))
                year = int(stac_yymm[:4]) if len(stac_yymm) >= 4 and stac_yymm[:4].isdigit() else 0
                if not year:
                    continue

                # KIS 손익계산서는 백만원 단위로 반환 -> 원 단위 변환 (* 1,000,000)
                revenue = float(item.get("sale_account", 0) or 0) * 1_000_000
                operating_profit = float(item.get("op_prfi", 0) or 0) * 1_000_000
                operating_margin = (operating_profit / revenue * 100) if revenue != 0 else 0.0

                results.append({
                    "stac_yymm": stac_yymm,
                    "fiscal_year": year,
                    "revenue": revenue,
                    "operating_profit": operating_profit,
                    "operating_margin": round(operating_margin, 2),
                })
            return results
        except (httpx.HTTPError, ValueError):
            return []

    def fetch_financial_ratio(self, stock_code: str) -> list[dict]:
        """
        KIS 국내주식 재무비율 API (/uapi/domestic-stock/v1/finance/financial-ratio) 호출.
        """
        return self.fetch_income_statement(stock_code, division="0")


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

