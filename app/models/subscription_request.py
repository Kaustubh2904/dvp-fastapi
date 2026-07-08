from datetime import datetime, timezone
import enum
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SubscriptionRequestStatus(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class SubscriptionRequestType(str, enum.Enum):
    UPGRADE = "UPGRADE"
    DOWNGRADE = "DOWNGRADE"
    RENEWAL = "RENEWAL"
    TRIAL_CONVERSION = "TRIAL_CONVERSION"


class SubscriptionRequest(Base):
    __tablename__ = "subscription_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    requested_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    reviewed_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    request_type: Mapped[SubscriptionRequestType] = mapped_column(Enum(SubscriptionRequestType), nullable=False)
    current_plan_code: Mapped[str] = mapped_column(String(50), nullable=True)
    requested_plan_code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[SubscriptionRequestStatus] = mapped_column(
        Enum(SubscriptionRequestStatus), default=SubscriptionRequestStatus.PENDING_APPROVAL, nullable=False
    )
    immediate_effect: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    prorated_value_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str] = mapped_column(String(1000), nullable=True)
    review_notes: Mapped[str] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )