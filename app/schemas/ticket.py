from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TicketReply(BaseModel):
    responder_id: int
    responder_email: str
    responder_role: str
    message: str
    created_at: datetime


class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=3, max_length=4000)
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketReplyCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class TicketResponse(BaseModel):
    ticket_id: str
    subject: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    raised_by_id: int
    raised_by_email: str
    assigned_to_id: Optional[int] = None
    replies: list[TicketReply] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime