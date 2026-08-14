"""OpenAI 클라이언트 lazy singleton. stt/shortforms 등 여러 도메인이 공유해서 쓴다."""

from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def get_openai_client():
    if not settings.openai_api_key:
        return None
    from openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key)
