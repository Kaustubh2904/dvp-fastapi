from datetime import datetime, timezone
from sqlalchemy import Integer, DateTime, ForeignKey, String, BigInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SubscriptionUsage(Base):
    __tablename__ = "subscription_usage"
    __table_args__ = (
        UniqueConstraint("company_id", "month_key", name="uq_subscription_usage_company_month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    month_key: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    employee_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_document_uploads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    last_reset_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )