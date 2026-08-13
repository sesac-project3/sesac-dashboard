"""사용자별 '좋아요한 숏폼 id' 집합을 Redis에 캐싱한다.

GET /shortforms를 부를 때마다 shortform_likes를 매번 조인해서 읽는 대신, Redis SET
(user:{id}:liked_shortforms)을 먼저 보고 없을 때만(캐시 미스) DB에서 한 번 채워 넣는다.
toggle_like에서 등록/해제할 때 같은 키를 갱신해서(write-through) 캐시가 항상 최신을
따라가게 한다 — Postgres가 항상 진실의 원천이고, Redis는 그 위의 읽기 캐시일 뿐이다.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.redis import redis_client

TTL_SECONDS = 60 * 60  # 1시간 — 어차피 write-through로 항상 최신 유지, 여유만 둠
_EMPTY_SENTINEL = "0"  # shortform.id는 1부터 시작 — 빈 집합도 "캐시는 있음"을 표시하려고 씀


def _key(user_id: int) -> str:
    return f"user:{user_id}:liked_shortforms"


def get_liked_ids(db: Session, user_id: int) -> set[int]:
    key = _key(user_id)
    if redis_client.exists(key):
        return {int(v) for v in redis_client.smembers(key) if v != _EMPTY_SENTINEL}

    from app.domain.shortforms.models import ShortformLike  # 순환 임포트 방지

    ids = list(db.scalars(select(ShortformLike.shortform_id).where(ShortformLike.user_id == user_id)))
    redis_client.sadd(key, *(ids or [_EMPTY_SENTINEL]))
    redis_client.expire(key, TTL_SECONDS)
    return set(ids)


def mark_liked(user_id: int, shortform_id: int) -> None:
    key = _key(user_id)
    redis_client.srem(key, _EMPTY_SENTINEL)
    redis_client.sadd(key, shortform_id)
    redis_client.expire(key, TTL_SECONDS)


def mark_unliked(user_id: int, shortform_id: int) -> None:
    key = _key(user_id)
    redis_client.srem(key, shortform_id)
    if not redis_client.exists(key):
        # SREM으로 마지막 원소까지 지우면 Redis가 빈 SET을 자동으로 지워버린다 —
        # 그러면 다음 조회 때 "캐시 없음"으로 보여 불필요하게 DB를 다시 읽으니
        # sentinel로 "빈 채로 캐시는 있음" 상태를 유지해준다.
        redis_client.sadd(key, _EMPTY_SENTINEL)
        redis_client.expire(key, TTL_SECONDS)
