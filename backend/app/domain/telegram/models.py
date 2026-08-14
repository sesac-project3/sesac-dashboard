from datetime import date
from sqlalchemy import BigInteger, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin

class TelegramNotification(Base, TimestampMixin):
    __tablename__ = "telegram_notifications"
    __table_args__ = (
        # Unique constraint to prevent duplicate alerts for the same stock on the same day per user
        UniqueConstraint("user_id", "notification_type", "stock_id", "sent_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    notification_type: Mapped[str] = mapped_column(String(30), nullable=False)  # MORNING_BRIEFING / AFTERNOON_BRIEFING / PRICE_ALERT
    stock_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("stocks.id"), nullable=True)
    sent_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
