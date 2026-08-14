from fastapi import APIRouter

from app.common.response import ApiResponse

router = APIRouter(prefix="/news", tags=["news"])


@router.get("", response_model=ApiResponse[list[dict]])
def list_news(stock_code: str | None = None):
    # SCHEMA.md news ⋈ sentiment_analysis 조인 예정 (F-03-4, F-05). 크롤러/배치 붙기 전 빈 목록.
    return ApiResponse.ok([])
