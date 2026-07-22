from datetime import datetime, date, timezone
import enum
from typing import Optional
from sqlalchemy import Integer, String, Boolean, DateTime, Date, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class DigiLockerStatus(str, enum.Enum):
    LINKED = "LINKED"
    UNLINKED = "UNLINKED"
    EXPIRED = "EXPIRED"


class EmployeeStatus(str, enum.Enum):
    PENDING_INVITE = "PENDING_INVITE"
    INVITED = "INVITED"
    REGISTERED = "REGISTERED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    employee_code: Mapped[str] = mapped_column(String(50), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    gender: Mapped[str] = mapped_column(String(20), nullable=True)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=True)
    profile_photo: Mapped[str] = mapped_column(String(500), nullable=True)
    joining_date: Mapped[date] = mapped_column(Date, nullable=True)

    registration_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[EmployeeStatus] = mapped_column(
        Enum(EmployeeStatus), default=EmployeeStatus.PENDING_INVITE, nullable=False
    )
    notes: Mapped[str] = mapped_column(String(2000), nullable=True)
    offer_letter_url: Mapped[str] = mapped_column(String(500), nullable=True)
    joining_letter_url: Mapped[str] = mapped_column(String(500), nullable=True)
    letters_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # DigiLocker integration fields (encrypted at rest)
    digilocker_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    digilocker_access_token: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    digilocker_refresh_token: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    digilocker_token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    digilocker_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    digilocker_linked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="employee", lazy="select")
    company = relationship("Company", backref="employees", lazy="joined")
    department = relationship("Department", backref="employees", lazy="joined")