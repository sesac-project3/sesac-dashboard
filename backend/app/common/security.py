"""JWT 발급/검증. refresh token은 DB가 아니라 Redis에 저장하고 거기서 가져와 대조한다
(PRODUCT.md ISSUE-001). Redis가 유효성의 단일 진실 공급원이라 로그아웃 시 키 삭제만으로
즉시 무효화된다.
"""

import time
import uuid

import jwt
from fastapi import Header

from app.common.exceptions import BusinessException, ErrorCode
from app.core.config import settings
from app.core.redis import redis_client

ALGORITHM = "HS256"


def _refresh_key(user_id: int) -> str:
    return f"refresh:{user_id}"


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": int(time.time()) + settings.jwt_access_expire_minutes * 60,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    ttl_seconds = settings.jwt_refresh_expire_days * 24 * 60 * 60
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": int(time.time()) + ttl_seconds,
        # jti: 초 단위로 같은 payload가 나올 수 있어서(같은 유저, 같은 만료초) 넣지 않으면
        # 회전 전/후 토큰이 완전히 같은 문자열이 되어 재사용 탐지가 무력화된다.
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)
    redis_client.set(_refresh_key(user_id), token, ex=ttl_seconds)
    return token


def rotate_refresh_token(refresh_token: str) -> tuple[str, str]:
    """refresh token을 검증하고 access/refresh 토큰을 새로 발급한다 (rotation).

    검증은 서명/만료뿐 아니라 Redis에 저장된 값과 일치하는지까지 확인한다 —
    로그아웃되었거나 이미 회전되어 폐기된 토큰의 재사용을 막기 위함.
    """
    try:
        payload = jwt.decode(refresh_token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise BusinessException(ErrorCode.INVALID_TOKEN)

    if payload.get("type") != "refresh":
        raise BusinessException(ErrorCode.INVALID_TOKEN)

    user_id = int(payload["sub"])
    if redis_client.get(_refresh_key(user_id)) != refresh_token:
        raise BusinessException(ErrorCode.INVALID_TOKEN)

    return create_access_token(user_id), create_refresh_token(user_id)


def revoke_refresh_token(user_id: int) -> None:
    redis_client.delete(_refresh_key(user_id))


def decode_access_token(access_token: str) -> int:
    try:
        payload = jwt.decode(access_token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise BusinessException(ErrorCode.INVALID_TOKEN)
    if payload.get("type") != "access":
        raise BusinessException(ErrorCode.INVALID_TOKEN)
    return int(payload["sub"])


def get_current_user_id(authorization: str = Header(default="")) -> int:
    """보호된 라우트에서 `Depends(get_current_user_id)`로 사용."""
    if not authorization.startswith("Bearer "):
        raise BusinessException(ErrorCode.UNAUTHORIZED)
    return decode_access_token(authorization.removeprefix("Bearer "))
