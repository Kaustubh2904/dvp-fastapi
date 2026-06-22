from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.employee import EmployeeStatus


class EmployeeBase(BaseModel):
    employee_code: Optional[str] = None
    first_name: str
    last_name: str
    phone: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    profile_photo: Optional[str] = None
    joining_date: Optional[date] = None


class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    department_id: Optional[int] = None


class EmployeeUpdate(BaseModel):
    employee_code: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    profile_photo: Optional[str] = None
    joining_date: Optional[date] = None
    department_id: Optional[int] = None
    status: Optional[EmployeeStatus] = None


class EmployeeRegister(BaseModel):
    """
    Schema for the self-registration / profile completion step by the employee.
    """
    employee_code: str
    phone: str
    gender: str
    date_of_birth: date
    address: str
    joining_date: Optional[date] = None


class EmployeeResponse(EmployeeBase):
    id: int
    company_id: int
    department_id: Optional[int] = None
    email: EmailStr
    registration_completed: bool
    status: EmployeeStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True