"""ISSUE-E1: invest/ai/stt/service.py를 이 프로젝트 구조에 맞게 이식.
faster-whisper로 전사하고, OPENAI_API_KEY가 있으면 3줄 요약까지 만든다
(없으면 문장 분리로 대체 — LLM 요약 실패가 전사 자체를 막으면 안 됨).
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

STT_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = STT_DIR / "uploads"


def ensure_uploads_dir() -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOADS_DIR


def _split_text_into_chunks(text: str, max_bullets: int = 3) -> list[str]:
    if not text:
        return []
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    sentences = [
        s.strip(" -*•\t")
        for s in re.split(r"(?<=[.!?])\s+|(?<=[다요])\.\s*", normalized)
        if s.strip()
    ]
    return sentences[:max_bullets] if sentences else [normalized]


@lru_cache(maxsize=1)
def get_openai_client():
    if not settings.openai_api_key:
        return None
    from openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key)


async def summarize_transcript_with_llm(transcript: str) -> list[str]:
    """3줄 요약. LLM 호출이 실패하거나 키가 없으면 문장 분리로 대체(둘 다 절대 예외를 던지지 않음)."""
    fallback = _split_text_into_chunks(transcript, max_bullets=3)
    if not transcript or transcript.startswith("[EMPTY]"):
        return fallback

    client = get_openai_client()
    if client is None:
        logger.warning("OPENAI_API_KEY 미설정 — 문장 분리 요약으로 대체")
        return fallback

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You summarize STT transcripts for a stock and investing app. "
                    "Be concise, factual, and output only Korean bullet points.",
                },
                {
                    "role": "user",
                    "content": (
                        "다음 STT 전사 결과를 한국어 3줄로 요약해줘. 각 줄은 '- '로 시작.\n\n"
                        f"{transcript}"
                    ),
                },
            ],
            max_tokens=260,
        )
        text = response.choices[0].message.content or ""
        bullets = [
            re.sub(r"^[-*•]\s*", "", line).strip()
            for line in text.strip().split("\n")
            if line.strip()
        ]
        return bullets[:3] if bullets else fallback
    except Exception:
        logger.exception("LLM 요약 실패 — 문장 분리로 대체")
        return fallback


@lru_cache(maxsize=1)
def get_whisper_model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            f"faster-whisper import 실패 ({sys.executable}): {exc}. "
            "pip install -r requirements.txt 확인"
        ) from exc

    return WhisperModel(
        settings.whisper_model_size,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


def transcribe_media_file(source_path: Path) -> str:
    model = get_whisper_model()
    segments, _ = model.transcribe(
        str(source_path),
        language=settings.whisper_language,
        vad_filter=True,
    )
    transcript = " ".join(seg.text.strip() for seg in segments if seg.text).strip()
    return transcript or "[EMPTY] no speech recognized"
