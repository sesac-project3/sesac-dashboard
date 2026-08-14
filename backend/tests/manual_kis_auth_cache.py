"""KIS access_token/approval_key의 dev(.env)/prod(Redis+lock) 캐시 분기 확인용 수동 테스트.

실제 KIS 네트워크는 안 부른다 — `_issue_token`/`_issue_approval_key`를 호출 횟수를 세는
가짜로 바꿔치기해서, "몇 번 실제로 발급을 시도했는지"만으로 캐시가 제대로 재사용되는지
검증한다. 로컬 docker-compose의 Redis가 떠 있어야 한다(REDIS_URL).

실행:
    PYTHONPATH=backend python3 backend/tests/manual_kis_auth_cache.py
"""

import threading
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.kis import KisTokenClient
from app.core.redis import redis_client


def _fake_issuer(prefix: str, call_count: list[int], ttl: timedelta):
    """실제 KIS API를 부르는 대신 카운터만 올리고 값을 즉시 채워 넣는다."""

    def _issue(self, now: datetime) -> str:
        call_count[0] += 1
        value = f"{prefix}-{call_count[0]}"
        expires_at = now + ttl
        if prefix == "token":
            self._access_token, self._expires_at = value, expires_at
        else:
            self._approval_key, self._approval_expires_at = value, expires_at
        return value

    return _issue


def test_dev_env_reuse() -> None:
    """dev: 프로세스가 새로 떠도(=새 인스턴스) .env에 남겨둔 값이 유효하면 재발급 안 함."""
    settings.app_env = "development"
    settings.kis_access_token = ""
    settings.kis_access_token_expires_at = ""

    calls = [0]
    KisTokenClient._issue_token = _fake_issuer("token", calls, timedelta(hours=1))
    try:
        client = KisTokenClient()
        token1 = client.access_token()
        assert calls[0] == 1, "첫 호출은 발급해야 함"

        token2 = client.access_token()
        assert token2 == token1 and calls[0] == 1, "같은 인스턴스면 메모리 캐시 재사용"

        # "서버 재시작" 시뮬레이션: 개발자가 로그에서 복사해 .env에 넣어둔 상태
        settings.kis_access_token = client._access_token
        settings.kis_access_token_expires_at = client._expires_at.isoformat()
        fresh = KisTokenClient()
        token3 = fresh.access_token()
        assert token3 == token1 and calls[0] == 1, ".env에 유효한 값 있으면 새 인스턴스도 재발급 안 함"

        # .env 값이 만료됐으면 재발급
        settings.kis_access_token_expires_at = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        fresh2 = KisTokenClient()
        fresh2.access_token()
        assert calls[0] == 2, "만료된 .env 값은 재발급해야 함"
    finally:
        KisTokenClient._issue_token = _ORIGINAL_ISSUE_TOKEN
        settings.kis_access_token = ""
        settings.kis_access_token_expires_at = ""

    print("[OK] test_dev_env_reuse")


def test_prod_redis_reuse() -> None:
    """prod: Redis에 유효한 값이 있으면 다른 프로세스(=새 인스턴스)도 재발급 안 함."""
    settings.app_env = "production"
    redis_client.delete(
        KisTokenClient._REDIS_ACCESS_TOKEN_KEY, KisTokenClient._REDIS_ACCESS_TOKEN_EXPIRES_KEY
    )

    calls = [0]
    KisTokenClient._issue_token = _fake_issuer("token", calls, timedelta(hours=1))
    try:
        client = KisTokenClient()
        token1 = client.access_token()
        assert calls[0] == 1

        stored_ttl = redis_client.ttl(KisTokenClient._REDIS_ACCESS_TOKEN_KEY)
        assert 0 < stored_ttl <= 3600, f"Redis TTL이 만료시각 기준으로 안 잡힘: {stored_ttl}"

        # 완전히 새 인스턴스(다른 프로세스/워커 상정) — 메모리 캐시는 비어있고 Redis만 공유
        other_process = KisTokenClient()
        token2 = other_process.access_token()
        assert token2 == token1 and calls[0] == 1, "Redis에 유효한 값 있으면 다른 프로세스도 재발급 안 함"
    finally:
        KisTokenClient._issue_token = _ORIGINAL_ISSUE_TOKEN
        redis_client.delete(
            KisTokenClient._REDIS_ACCESS_TOKEN_KEY, KisTokenClient._REDIS_ACCESS_TOKEN_EXPIRES_KEY
        )

    print("[OK] test_prod_redis_reuse")


def test_prod_concurrent_lock() -> None:
    """prod: 여러 '프로세스'가 동시에 캐시 미스를 만나도 실제 발급은 한 번만."""
    settings.app_env = "production"
    redis_client.delete(
        KisTokenClient._REDIS_ACCESS_TOKEN_KEY, KisTokenClient._REDIS_ACCESS_TOKEN_EXPIRES_KEY
    )

    calls = [0]

    def _slow_issue(self, now: datetime) -> str:
        import time

        time.sleep(0.2)  # 실제 KIS 왕복 시간을 흉내내 락 경합 창을 벌려줌
        calls[0] += 1
        self._access_token = f"token-{calls[0]}"
        self._expires_at = now + timedelta(hours=1)
        return self._access_token

    KisTokenClient._issue_token = _slow_issue
    try:
        results: list[str] = []

        def _worker():
            results.append(KisTokenClient().access_token())

        threads = [threading.Thread(target=_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert calls[0] == 1, f"동시 요청인데 {calls[0]}번 발급됨 — 락이 안 먹음"
        assert len(set(results)) == 1, "모든 워커가 같은 토큰을 받아야 함"
    finally:
        KisTokenClient._issue_token = _ORIGINAL_ISSUE_TOKEN
        redis_client.delete(
            KisTokenClient._REDIS_ACCESS_TOKEN_KEY, KisTokenClient._REDIS_ACCESS_TOKEN_EXPIRES_KEY
        )

    print("[OK] test_prod_concurrent_lock")


def test_approval_key_independent_from_access_token() -> None:
    """access_token과 approval_key는 서로 다른 캐시 슬롯 — 하나만 있어도 다른 하나는 재발급."""
    settings.app_env = "development"
    settings.kis_access_token = ""
    settings.kis_access_token_expires_at = ""
    settings.kis_ws_approval_key = ""
    settings.kis_ws_approval_key_expires_at = ""

    token_calls = [0]
    key_calls = [0]
    KisTokenClient._issue_token = _fake_issuer("token", token_calls, timedelta(hours=1))
    KisTokenClient._issue_approval_key = _fake_issuer("key", key_calls, timedelta(hours=23))
    try:
        client = KisTokenClient()
        client.access_token()
        assert token_calls[0] == 1 and key_calls[0] == 0, "approval_key를 부르기 전엔 발급되면 안 됨"
        client.approval_key()
        assert token_calls[0] == 1 and key_calls[0] == 1, "access_token 캐시가 approval_key엔 영향 없어야 함"
    finally:
        KisTokenClient._issue_token = _ORIGINAL_ISSUE_TOKEN
        KisTokenClient._issue_approval_key = _ORIGINAL_ISSUE_APPROVAL_KEY
        settings.kis_access_token = ""
        settings.kis_access_token_expires_at = ""
        settings.kis_ws_approval_key = ""
        settings.kis_ws_approval_key_expires_at = ""

    print("[OK] test_approval_key_independent_from_access_token")


_ORIGINAL_ISSUE_TOKEN = KisTokenClient._issue_token
_ORIGINAL_ISSUE_APPROVAL_KEY = KisTokenClient._issue_approval_key


def main() -> None:
    original_env = settings.app_env
    try:
        test_dev_env_reuse()
        test_prod_redis_reuse()
        test_prod_concurrent_lock()
        test_approval_key_independent_from_access_token()
    finally:
        settings.app_env = original_env
    print("모든 검증 통과.")


if __name__ == "__main__":
    main()
