"""SCHEMA.md의 users / kakao_tokens를 그대로 매핑. 나머지 13개 테이블의 ORM 모델은
해당 기능(ISSUE-A2, C1 등)을 실제로 구현할 때 그 도메인 폴더에 추가한다.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    device_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)

    # Telegram notification preferences
    notify_morning: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    notify_evening: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    notify_alert: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)



class KakaoToken(Base, TimestampMixin):
    __tablename__ = "kakao_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True)
    kakao_user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    access_token: Mapped[str] = mapped_column(String)
    refresh_token: Mapped[str] = mapped_column(String)
    token_type: Mapped[str] = mapped_column(String, default="bearer")
    scope: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    refresh_token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
