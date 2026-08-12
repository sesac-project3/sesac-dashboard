from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import ApiResponse
from app.core.database import get_db
from app.domain.reports.schemas import StockReport
from app.domain.reports.service import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{code}", response_model=ApiResponse[StockReport | None])
def get_report(code: str, db: Session = Depends(get_db)):
    report = report_service.get_stock_report(db, code)
    if not report:
        return ApiResponse.ok(data=None, message="존재하지 않는 종목이거나 리포트 데이터가 없습니다.")
    return ApiResponse.ok(data=report)
