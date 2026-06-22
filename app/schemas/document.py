from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.document import DocumentType, VerificationStatus


class DocumentBase(BaseModel):
    document_type: DocumentType
    file_name: str
    file_url: str
    verification_status: Optional[VerificationStatus] = VerificationStatus.NOT_SUBMITTED
    remarks: Optional[str] = None


class DocumentCreate(BaseModel):
    employee_id: int
    document_type: DocumentType
    file_name: str
    file_url: str


class DocumentUpdate(BaseModel):
    verification_status: Optional[VerificationStatus] = None
    remarks: Optional[str] = None


class DocumentResponse(DocumentBase):
    id: int
    employee_id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True