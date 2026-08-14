"""공통 예외. invest/backend의 global/exception/ErrorCode.java 코드 체계를 그대로 옮김."""

from enum import Enum

from fastapi import Request
from fastapi.responses import JSONResponse

from app.common.response import ApiResponse


class ErrorCode(Enum):
    INVALID_INPUT_VALUE = (400, "COMMON-400", "잘못된 요청입니다.")
    ENTITY_NOT_FOUND = (404, "COMMON-404", "요청한 리소스를 찾을 수 없습니다.")
    CONFLICT = (409, "COMMON-409", "이미 처리된 요청이거나 충돌이 발생했습니다.")
    UNAUTHORIZED = (401, "AUTH-401", "인증이 필요합니다.")
    INVALID_TOKEN = (401, "AUTH-401-1", "유효하지 않은 토큰입니다.")
    ACCESS_DENIED = (403, "AUTH-403", "접근 권한이 없습니다.")
    INTERNAL_SERVER_ERROR = (500, "COMMON-500", "서버 내부 오류가 발생했습니다.")
    SERVICE_UNAVAILABLE = (503, "COMMON-503", "일시적으로 서비스를 사용할 수 없습니다.")

    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


class BusinessException(Exception):
    def __init__(self, error_code: ErrorCode):
        self.error_code = error_code


async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
    ec = exc.error_code
    body = ApiResponse.fail(code=ec.code, message=ec.message, status=ec.status)
    return JSONResponse(status_code=ec.status, content=body.model_dump(mode="json"))
