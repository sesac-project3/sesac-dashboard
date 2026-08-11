from fastapi import APIRouter

from app.common.response import ApiResponse
from app.domain.reports.schemas import StockReport

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{code}", response_model=ApiResponse[StockReport | None])
def get_report(code: str):
    # ISSUE-C1~C4, D1~D3에서 실제 배치 생성 리포트로 교체. 그 전까진 데이터 없음으로 응답.
    return ApiResponse.ok(data=None, message="리포트가 아직 생성되지 않았습니다.")
