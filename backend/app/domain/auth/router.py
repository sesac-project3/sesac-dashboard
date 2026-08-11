from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.response import ApiResponse
from app.common.security import (
    create_access_token,
    create_refresh_token,
    get_current_user_id,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.core.config import settings
from app.core.database import get_db
from app.domain.auth.models import KakaoToken, User
from app.domain.auth.schemas import RefreshRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

KAKAO_AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_ME_URL = "https://kapi.kakao.com/v2/user/me"


@router.get("/kakao/login")
def kakao_login() -> RedirectResponse:
    """카카오 로그인 시작 — 프론트는 그냥 이 URL로 이동시키면 된다 (client_id는 서버에만 존재)."""
    params = {
        "client_id": settings.kakao_client_id,
        "redirect_uri": settings.kakao_redirect_uri,
        "response_type": "code",
    }
    return RedirectResponse(f"{KAKAO_AUTHORIZE_URL}?{urlencode(params)}")


@router.get("/kakao/callback")
def kakao_callback(code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    """카카오가 인가코드로 리다이렉트하는 지점. 코드 교환 → 프로필 조회 → users/kakao_tokens
    upsert → 우리 JWT 발급 → 프론트 /login/complete로 다시 리다이렉트한다.
    """
    token_data = {
        "grant_type": "authorization_code",
        "client_id": settings.kakao_client_id,
        "redirect_uri": settings.kakao_redirect_uri,
        "code": code,
    }
    if settings.kakao_client_secret:
        token_data["client_secret"] = settings.kakao_client_secret

    token_res = httpx.post(KAKAO_TOKEN_URL, data=token_data)
    token_res.raise_for_status()
    kakao_tokens = token_res.json()

    profile_res = httpx.get(
        KAKAO_USER_ME_URL,
        headers={"Authorization": f"Bearer {kakao_tokens['access_token']}"},
    )
    profile_res.raise_for_status()
    kakao_user_id = profile_res.json()["id"]

    kakao_token = db.scalar(select(KakaoToken).where(KakaoToken.kakao_user_id == kakao_user_id))

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=kakao_tokens["expires_in"])
    refresh_expires_at = now + timedelta(
        seconds=kakao_tokens.get("refresh_token_expires_in", 60 * 60 * 24 * 60)
    )

    if kakao_token is None:
        user = User()
        db.add(user)
        db.flush()  # user.id 확보

        kakao_token = KakaoToken(
            user_id=user.id,
            kakao_user_id=kakao_user_id,
            access_token=kakao_tokens["access_token"],
            refresh_token=kakao_tokens["refresh_token"],
            token_type=kakao_tokens.get("token_type", "bearer"),
            scope=kakao_tokens.get("scope"),
            expires_at=expires_at,
            refresh_token_expires_at=refresh_expires_at,
        )
        db.add(kakao_token)
    else:
        kakao_token.access_token = kakao_tokens["access_token"]
        kakao_token.refresh_token = kakao_tokens["refresh_token"]
        kakao_token.expires_at = expires_at
        kakao_token.refresh_token_expires_at = refresh_expires_at

    db.commit()

    access_token = create_access_token(kakao_token.user_id)
    refresh_token = create_refresh_token(kakao_token.user_id)

    query = urlencode({"access_token": access_token, "refresh_token": refresh_token})
    return RedirectResponse(f"{settings.frontend_base_url}/login/complete?{query}")


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
def refresh(body: RefreshRequest):
    access_token, refresh_token = rotate_refresh_token(body.refreshToken)
    return ApiResponse.ok(TokenResponse(accessToken=access_token, refreshToken=refresh_token))


@router.post("/logout", response_model=ApiResponse[None])
def logout(user_id: int = Depends(get_current_user_id)):
    revoke_refresh_token(user_id)
    return ApiResponse.ok(message="로그아웃 되었습니다.")
