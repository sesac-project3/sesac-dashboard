from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class Stock(Base, TimestampMixin):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)


class StockDailyCandle(Base, TimestampMixin):
    __tablename__ = "stock_daily_candles"
    __table_args__ = (UniqueConstraint("stock_id", "trade_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    high_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    low_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    close_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)


class StockMinuteCandle(Base, TimestampMixin):
    __tablename__ = "stock_minute_candles"
    __table_args__ = (UniqueConstraint("stock_id", "traded_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    traded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    high_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    low_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    close_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)


class SentimentAnalysis(Base, TimestampMixin):
    __tablename__ = "sentiment_analysis"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)

