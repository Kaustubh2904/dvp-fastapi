from datetime import datetime, timezone
import enum
from sqlalchemy import Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class DocumentType(str, enum.Enum):
    AADHAR = "AADHAR"
    PAN = "PAN"
    PASSPORT = "PASSPORT"
    RESUME = "RESUME"
    DEGREE = "DEGREE"
    OTHER = "OTHER"


class VerificationStatus(str, enum.Enum):
    NOT_SUBMITTED = "NOT_SUBMITTED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), default=VerificationStatus.PENDING, nullable=False
    )
    remarks: Mapped[str] = mapped_column(String(500), nullable=True)

    # Relationships
    employee = relationship("Employee", backref="documents", lazy="joined")