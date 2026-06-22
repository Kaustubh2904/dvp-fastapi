from typing import Optional
from pydantic import BaseModel


class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    company_id: int


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DepartmentResponse(DepartmentBase):
    id: int
    company_id: int

    class Config:
        from_attributes = True