from typing import Optional, Any
from pydantic import BaseModel


class PaginationParams(BaseModel):
    skip: int = 0
    limit: int = 100


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None