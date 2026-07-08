from datetime import datetime, timezone
import enum
from sqlalchemy import Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class BillingStatus(str, enum.Enum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    SCHEDULED_CHANGE = "SCHEDULED_CHANGE"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=True)
    gst_number: Mapped[str] = mapped_column(String(50), nullable=True)

    # Subscription & Limits
    subscription_plan: Mapped[str] = mapped_column(String(100), default="FREE")
    subscription_start: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    subscription_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    employee_limit: Mapped[int] = mapped_column(Integer, default=10)
    current_employee_count: Mapped[int] = mapped_column(Integer, default=0)

    billing_status: Mapped[BillingStatus] = mapped_column(
        Enum(BillingStatus), default=BillingStatus.PENDING_APPROVAL, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_quota_reset_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )