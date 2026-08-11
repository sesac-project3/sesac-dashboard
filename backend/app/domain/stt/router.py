from fastapi import APIRouter

from app.common.response import ApiResponse

router = APIRouter(prefix="/stt", tags=["stt"])


@router.post("/transcribe", response_model=ApiResponse[None])
def transcribe():
    # ISSUE-E1: z-invest(invest)/ai/stt를 그대로 이식할 자리.
    return ApiResponse.ok(data=None, message="STT는 아직 이식 전입니다 (ISSUE-E1).")
