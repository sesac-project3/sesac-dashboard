"""SCHEMA.md news 매핑."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class News(Base, TimestampMixin):
    # ponytail: 실제 배포된 테이블명은 data_source (팀원 크롤러가 이 이름으로 이미 115k+행 적재함).
    # SCHEMA.md/schema.sql 설계 당시 이름은 news였지만, 라이브 DB를 바꾸는 대신 ORM 쪽을 맞춘다.
    __tablename__ = "data_source"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"))
    source_type: Mapped[str] = mapped_column(String(20))  # '뉴스' | '토스_커뮤니티'
    headline: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
