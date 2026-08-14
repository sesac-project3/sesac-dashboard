"""SCHEMA.md의 shortforms / shortform_likes 매핑."""

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.domain.news.models import News  # noqa: F401 — shortforms.news_id FK가 참조하는 테이블 등록용


class Shortform(Base, TimestampMixin):
    __tablename__ = "shortforms"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ticker: Mapped[str] = mapped_column(String(10))
    s3_url: Mapped[str] = mapped_column(Text)
    script: Mapped[str] = mapped_column(Text)
    sentiment: Mapped[str] = mapped_column(String(10))  # 'POS' | 'NEG'
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)


class ShortformLike(Base, TimestampMixin):
    __tablename__ = "shortform_likes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shortform_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("shortforms.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
