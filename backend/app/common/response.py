"""공통 응답 포맷. invest/backend의 global/response/ApiResponse.java 구조를 그대로 옮김."""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    status: int
    code: str
    message: str
    data: T | None = None
    timestamp: datetime

    @classmethod
    def ok(cls, data: T | None = None, message: str = "요청이 성공했습니다.", status: int = 200):
        return cls(
            success=True,
            status=status,
            code=f"COMMON-{status}",
            message=message,
            data=data,
            timestamp=datetime.now(),
        )

    @classmethod
    def fail(cls, code: str, message: str, status: int):
        return cls(
            success=False,
            status=status,
            code=code,
            message=message,
            data=None,
            timestamp=datetime.now(),
        )
