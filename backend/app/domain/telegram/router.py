from fastapi import APIRouter

from app.common.response import ApiResponse

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.get("/status", response_model=ApiResponse[None])
def status():
    # F-04 보류 확정 (PRODUCT.md ISSUE-E4). telegram_link_codes/telegram_notifications
    # 스키마는 재개 대비로 유지, 라우터는 자리만.
    return ApiResponse.ok(data=None, message="텔레그램 연동은 이번 스프린트에서 보류 상태입니다.")
