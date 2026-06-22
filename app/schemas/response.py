from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str = "INTERNAL_ERROR"
    message: str = "An error occurred"
    detail: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int = 0
    limit: int = 100