from fastapi import APIRouter

from app.common.response import ApiResponse

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/sentiment/{code}", response_model=ApiResponse[None])
def sentiment(code: str):
    # F-05 P2. SCHEMA.md 설계상 별도 테이블 없이 news(source_type='토스_커뮤니티') +
    # sentiment_analysis 조인으로 계산 — 여유 있을 때 ISSUE-D4에서 구현.
    return ApiResponse.ok(data=None, message="커뮤니티 민심 분석은 여유 시 구현 예정입니다 (P2).")
