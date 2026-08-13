import json
import logging
from datetime import datetime, timedelta, timezone
from threading import Lock
from zoneinfo import ZoneInfo

import httpx

from app.common.exceptions import BusinessException, ErrorCode
from app.core.config import settings
from app.core.kis_endpoints import (
    CURRENT_PRICE_PATH,
    DAILY_CANDLE_PATH,
    MARKET_INVESTOR_TREND_PATH,
    MINUTE_CANDLE_PATH,
)
from app.core.redis import redis_client

logger = logging.getLogger(__name__)


class KisTokenClient:
    """KIS REST access_token / WebSocket approval_key 발급과 캐시를 담당한다.

    두 값은 발급/만료 정책이 달라(access_token은 KIS 응답이 실제 만료시각을 알려주고,
    approval_key는 KIS 문서상 24시간 고정) 완전히 독립적으로 캐싱·재발급한다.

    프로세스 메모리 캐시가 1차 캐시고, 그 뒤에 환경별 2차 저장소를 하나 더 둔다:
      - 개발 환경(APP_ENV=development, 기본값): 로컬 Redis는 개발자별 docker 컨테이너라
        인증값 공유 용도로 안 쓴다. 대신 .env(KIS_ACCESS_TOKEN 등)를 읽기 전용으로 참고하고,
        새로 발급하면 로그로 값을 출력해 개발자가 직접 .env에 복사해 넣게 한다.
      - 배포 환경(APP_ENV=production): Redis(kis:access_token 등)에 값+만료시각을 저장하고
        읽어써서, 여러 워커/재배포 사이에서 프로세스가 새로 떠도 재발급하지 않는다.
        동시에 여러 워커가 캐시 미스를 만나 동시에 재발급을 시도하지 않도록 Redis lock으로
        발급 구간을 감싼다.
    """

    _TOKEN_PATH = "/oauth2/tokenP"
    _APPROVAL_PATH = "/oauth2/Approval"

    # KIS 토큰 발급은 "1분당 1회"로 막혀 있다. 한 번 발급 실패하면 이 쿨다운 동안은
    # 재시도 자체를 하지 않는다 — 안 그러면 한 번의 /home-dashboard 요청 안에서만도
    # 지수 2번+종목 5번, 총 7번을 순서대로 재시도하며 그때마다 새로 실패해서 오히려
    # 레이트리밋 창이 계속 늘어나는(먼저 실패한 요청이 남은 대기시간을 계속 갱신하는)
    # 문제가 있었다.
    _TOKEN_FAILURE_COOLDOWN = timedelta(seconds=55)

    # WebSocket 접속키는 KIS 발급 응답에 만료시각이 안 실려 온다 — 문서상 정책인 24시간에서
    # 1시간 여유를 두고 만료 직전 재발급을 피한다(access_token과 동일한 여유 두는 방식).
    _WS_APPROVAL_KEY_TTL = timedelta(hours=23)

    _REDIS_ACCESS_TOKEN_KEY = "kis:access_token"
    _REDIS_ACCESS_TOKEN_EXPIRES_KEY = "kis:access_token:expires_at"
    _REDIS_APPROVAL_KEY_KEY = "kis:ws:approval_key"
    _REDIS_APPROVAL_KEY_EXPIRES_KEY = "kis:ws:approval_key:expires_at"
    _REDIS_LOCK_TIMEOUT_SECONDS = 10  # 발급 API 왕복 시간 감안한 락 최대 보유시간

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._expires_at: datetime | None = None
        self._approval_key: str | None = None
        self._approval_expires_at: datetime | None = None
        self._token_failed_until: datetime | None = None
        self._lock = Lock()

    def access_token(self) -> str:
        now = datetime.now(timezone.utc)
        if self._access_token and self._expires_at and now < self._expires_at:
            return self._access_token

        with self._lock:
            now = datetime.now(timezone.utc)
            if self._access_token and self._expires_at and now < self._expires_at:
                return self._access_token
            if self._load_cached_access_token(now):
                return self._access_token  # type: ignore[return-value]
            if self._token_failed_until and now < self._token_failed_until:
                raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE)
            if not settings.is_production:
                logger.info("[KIS] Access token expired or missing.")
            try:
                if settings.is_production:
                    token = self._with_redis_lock(
                        "kis:lock:access_token", lambda: self._issue_and_store_access_token()
                    )
                else:
                    token = self._issue_and_store_access_token()
            except BusinessException:
                self._token_failed_until = now + self._TOKEN_FAILURE_COOLDOWN
                raise
            self._token_failed_until = None
            return token

    def approval_key(self) -> str:
        now = datetime.now(timezone.utc)
        if self._approval_key and self._approval_expires_at and now < self._approval_expires_at:
            return self._approval_key

        with self._lock:
            now = datetime.now(timezone.utc)
            if self._approval_key and self._approval_expires_at and now < self._approval_expires_at:
                return self._approval_key
            if self._load_cached_approval_key(now):
                return self._approval_key  # type: ignore[return-value]
            if not settings.is_production:
                logger.info("[KIS] WebSocket approval key expired or missing.")
            if settings.is_production:
                return self._with_redis_lock(
                    "kis:lock:ws_approval_key", lambda: self._issue_and_store_approval_key()
                )
            return self._issue_and_store_approval_key()

    # --- 2차 저장소 읽기 (dev=.env / prod=Redis) — 락 재확인 시에도 재사용하므로
    # 항상 "지금 시각" 기준으로 새로 판단한다 ---

    def _load_cached_access_token(self, now: datetime) -> bool:
        if settings.is_production:
            value = redis_client.get(self._REDIS_ACCESS_TOKEN_KEY) or ""
            expiry_raw = redis_client.get(self._REDIS_ACCESS_TOKEN_EXPIRES_KEY) or ""
        else:
            value = settings.kis_access_token.strip()
            expiry_raw = settings.kis_access_token_expires_at.strip()
        expires_at = self._parse_iso(expiry_raw) if value and expiry_raw else None
        if not value or expires_at is None or now >= expires_at:
            return False
        self._access_token, self._expires_at = value, expires_at
        return True

    def _load_cached_approval_key(self, now: datetime) -> bool:
        if settings.is_production:
            value = redis_client.get(self._REDIS_APPROVAL_KEY_KEY) or ""
            expiry_raw = redis_client.get(self._REDIS_APPROVAL_KEY_EXPIRES_KEY) or ""
        else:
            value = settings.kis_ws_approval_key.strip()
            expiry_raw = settings.kis_ws_approval_key_expires_at.strip()
        expires_at = self._parse_iso(expiry_raw) if value and expiry_raw else None
        if not value or expires_at is None or now >= expires_at:
            return False
        self._approval_key, self._approval_expires_at = value, expires_at
        return True

    # --- 발급 + 저장 ---

    def _issue_and_store_access_token(self) -> str:
        # Redis 락 안에서 다시 호출될 수 있으니(다른 워커가 락을 쥔 사이 이미 발급해뒀을
        # 경우) 매번 최신 캐시를 재확인하고 나서야 실제 KIS API를 부른다.
        now = datetime.now(timezone.utc)
        if self._load_cached_access_token(now):
            return self._access_token  # type: ignore[return-value]

        token = self._issue_token(now)
        if settings.is_production:
            self._write_redis_pair(
                self._REDIS_ACCESS_TOKEN_KEY, self._REDIS_ACCESS_TOKEN_EXPIRES_KEY,
                self._access_token, self._expires_at,  # type: ignore[arg-type]
            )
        else:
            logger.info(
                "[KIS] New access token issued.\n"
                "KIS_ACCESS_TOKEN=%s\nKIS_ACCESS_TOKEN_EXPIRES_AT=%s\n"
                "Please update your local .env.",
                self._access_token, self._expires_at.isoformat(),  # type: ignore[union-attr]
            )
        return token

    def _issue_and_store_approval_key(self) -> str:
        now = datetime.now(timezone.utc)
        if self._load_cached_approval_key(now):
            return self._approval_key  # type: ignore[return-value]

        key = self._issue_approval_key(now)
        if settings.is_production:
            self._write_redis_pair(
                self._REDIS_APPROVAL_KEY_KEY, self._REDIS_APPROVAL_KEY_EXPIRES_KEY,
                self._approval_key, self._approval_expires_at,  # type: ignore[arg-type]
            )
        else:
            logger.info(
                "[KIS] New WebSocket approval key issued.\n"
                "KIS_WS_APPROVAL_KEY=%s\nKIS_WS_APPROVAL_KEY_EXPIRES_AT=%s\n"
                "Please update your local .env.",
                self._approval_key, self._approval_expires_at.isoformat(),  # type: ignore[union-attr]
            )
        return key

    def _write_redis_pair(self, value_key: str, expiry_key: str, value: str, expires_at: datetime) -> None:
        ttl = max(1, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
        redis_client.set(value_key, value, ex=ttl)
        redis_client.set(expiry_key, expires_at.isoformat(), ex=ttl)

    def _with_redis_lock(self, lock_key: str, fn):
        lock = redis_client.lock(
            lock_key, timeout=self._REDIS_LOCK_TIMEOUT_SECONDS, blocking_timeout=self._REDIS_LOCK_TIMEOUT_SECONDS
        )
        if not lock.acquire(blocking=True):
            # 락을 못 잡아도(드묾) 직접 발급을 시도한다 — 최악의 경우 레이트리밋 에러로
            # 수렴하고 위쪽 _token_failed_until 쿨다운이 재시도 폭주를 막아준다.
            return fn()
        try:
            return fn()
        finally:
            try:
                lock.release()
            except Exception:
                pass

    @staticmethod
    def _parse_iso(value: str) -> datetime | None:
        """.env/Redis에 우리가 직접 써둔(또는 개발자가 복사해 붙인) ISO 8601 만료시각을
        파싱한다. KIS API 응답 자체의 시각 포맷은 `_parse_expiry`가 따로 처리한다."""
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

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

    def minute_candles(
        self,
        stock_code: str,
        input_date: str,
        input_time: str,
    ) -> list[dict[str, str]]:
        response = httpx.get(
            f"{settings.kis_base_url.rstrip('/')}{MINUTE_CANDLE_PATH}",
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": stock_code,
                "FID_INPUT_DATE_1": input_date,
                "FID_INPUT_HOUR_1": input_time,
                "FID_PW_DATA_INCU_YN": "Y",
                "FID_FAKE_TICK_INCU_YN": "",
            },
            headers={
                "authorization": f"Bearer {self.access_token()}",
                "appkey": settings.kis_app_key,
                "appsecret": settings.kis_app_secret,
                "tr_id": "FHKST03010230",
                "custtype": "P",
            },
            timeout=20.0,
        )
        try:
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.error(
                "KIS minute candle request failed: %s, body=%s",
                _http_error_summary(response, exc),
                _response_error_body(response),
            )
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE) from exc

        if body.get("rt_cd") not in (None, "0"):
            logger.error(
                "KIS minute candle API returned an error: rt_cd=%s, msg_cd=%s, msg=%s",
                body.get("rt_cd"),
                body.get("msg_cd"),
                body.get("msg1"),
            )
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE)
        return body.get("output2", [])

    def current_price(self, stock_code: str) -> dict[str, str]:
        response = httpx.get(
            f"{settings.kis_base_url.rstrip('/')}{CURRENT_PRICE_PATH}",
            params={
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": stock_code,
            },
            headers={
                "authorization": f"Bearer {self.access_token()}",
                "appkey": settings.kis_app_key,
                "appsecret": settings.kis_app_secret,
                "tr_id": "FHKST01010100",
                "custtype": "P",
            },
            timeout=20.0,
        )
        try:
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.error(
                "KIS current price request failed: %s, body=%s",
                _http_error_summary(response, exc),
                _response_error_body(response),
            )
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE) from exc

        if body.get("rt_cd") not in (None, "0"):
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE)
        return body.get("output", {})

    def market_investor_trend(self, index_code: str, market_flag: str) -> dict[str, str]:
        """
        KIS 국내주식 시장별 투자자매매동향(일별) API (/uapi/domestic-stock/v1/quotations/
        inquire-investor-daily-by-market) 호출. 업종지수(코스피/코스닥) 현재가와 개인/외국인/
        기관 순매수 대금을 하루치 한 행으로 함께 준다.
        - index_code: "0001"(코스피), "1001"(코스닥)
        - market_flag: "KSP"(코스피), "KSQ"(코스닥)
        반환 주요 필드: bstp_nmix_prpr(지수), bstp_nmix_prdy_vrss(전일대비),
        bstp_nmix_prdy_ctrt(등락률%), prdy_vrss_sign, frgn_ntby_tr_pbmn/prsn_ntby_tr_pbmn/
        orgn_ntby_tr_pbmn(외국인/개인/기관 순매수 대금, 백만원 단위).
        """
        today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")
        response = httpx.get(
            f"{settings.kis_base_url.rstrip('/')}{MARKET_INVESTOR_TREND_PATH}",
            params={
                "fid_cond_mrkt_div_code": "U",
                "fid_input_iscd": index_code,
                "fid_input_date_1": today,
                "fid_input_iscd_1": market_flag,
                "fid_input_date_2": today,
                "fid_input_iscd_2": index_code,
            },
            headers={
                "authorization": f"Bearer {self.access_token()}",
                "appkey": settings.kis_app_key,
                "appsecret": settings.kis_app_secret,
                "tr_id": "FHPTJ04040000",
                "custtype": "P",
            },
            timeout=20.0,
        )
        try:
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.error(
                "KIS market investor trend request failed: %s, body=%s",
                _http_error_summary(response, exc),
                _response_error_body(response),
            )
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE) from exc

        if body.get("rt_cd") not in (None, "0"):
            raise BusinessException(ErrorCode.SERVICE_UNAVAILABLE)
        output = body.get("output", [])
        return output[0] if output else {}

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
        self._approval_expires_at = now + self._WS_APPROVAL_KEY_TTL
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
