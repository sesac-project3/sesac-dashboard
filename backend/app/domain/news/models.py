"""SCHEMA.md news 매핑."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class News(Base, TimestampMixin):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"))
    source_type: Mapped[str] = mapped_column(String(20))  # '뉴스' | '토스_커뮤니티'
    headline: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
