"""SCHEMA.md의 watchlists 매핑 (F-04 관심종목)."""

from sqlalchemy import BigInteger, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class Watchlist(Base, TimestampMixin):
    __tablename__ = "watchlists"
    __table_args__ = (UniqueConstraint("user_id", "stock_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"))
