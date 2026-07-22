from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DigiLockerAuthorizeResponse(BaseModel):
    """Response containing the OAuth authorization URL for DigiLocker."""
    authorization_url: str
    state: str


class DigiLockerCallbackRequest(BaseModel):
    """Request payload from the DigiLocker OAuth callback."""
    code: str
    state: str


class DigiLockerStatusResponse(BaseModel):
    """Response showing the current DigiLocker link status for an employee."""
    model_config = ConfigDict(from_attributes=True)

    is_linked: bool
    digilocker_id: Optional[str] = None
    status: Optional[str] = None
    linked_at: Optional[datetime] = None
    token_valid: bool = False


class DigiLockerDocumentItem(BaseModel):
    """A single document from the DigiLocker issued documents list."""
    name: str
    doc_type: str
    issuer: str
    uri: str
    date: Optional[str] = None


class DigiLockerDocumentsResponse(BaseModel):
    """Response containing the list of issued documents from DigiLocker."""
    documents: list[DigiLockerDocumentItem]
    total: int


class DigiLockerTokenRefreshResponse(BaseModel):
    """Response after refreshing the DigiLocker access token."""
    message: str
    token_valid: bool
    expires_at: Optional[datetime] = None


class DigiLockerUnlinkResponse(BaseModel):
    """Response after unlinking a DigiLocker account."""
    message: str
