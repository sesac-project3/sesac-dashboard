import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.common.response import ApiResponse
from app.core.config import settings
from app.domain.stt.schemas import TranscribeResponse
from app.domain.stt.service import (
    ensure_uploads_dir,
    summarize_transcript_with_llm,
    transcribe_media_file,
)

router = APIRouter(prefix="/stt", tags=["stt"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ApiResponse[TranscribeResponse])
async def transcribe(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="file name is required")

    content = await file.read()
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_size_bytes:
        raise HTTPException(status_code=413, detail="file is too large")

    uploads_dir = ensure_uploads_dir()
    upload_path = uploads_dir / Path(file.filename).name
    upload_path.write_bytes(content)

    try:
        transcript = await run_in_threadpool(transcribe_media_file, upload_path)
    except RuntimeError as exc:
        logger.exception("STT 전사 실패: %s", file.filename)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        upload_path.unlink(missing_ok=True)  # ponytail: 업로드 파일은 전사만 하고 바로 정리

    summary = await summarize_transcript_with_llm(transcript)
    summary = (summary + ["", "", ""])[:3]

    return ApiResponse.ok(
        TranscribeResponse(
            fileName=file.filename,
            transcript=transcript,
            aiInsightSummary1=summary[0],
            aiInsightSummary2=summary[1],
            aiInsightSummary3=summary[2],
        )
    )
