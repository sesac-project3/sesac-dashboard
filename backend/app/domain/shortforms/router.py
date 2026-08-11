from fastapi import APIRouter

from app.common.response import ApiResponse
from app.domain.shortforms.schemas import Shortform

router = APIRouter(prefix="/shortforms", tags=["shortforms"])


@router.get("", response_model=ApiResponse[list[Shortform]])
def list_shortforms():
    # ISSUE-E1~E3(STT 이식 + 영상 합성)에서 실 데이터로 교체.
    return ApiResponse.ok([])
