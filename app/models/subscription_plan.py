from datetime import datetime, timezone
from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    max_admins: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_employees: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    monthly_document_uploads: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    storage_mb: Mapped[int] = mapped_column(Integer, default=1024, nullable=False)
    chat_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    api_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    analytics_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ticket_priority: Mapped[str] = mapped_column(String(20), default="LOW", nullable=False)
    white_label_support: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    audit_log_retention_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    billing_cycle_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    trial_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )