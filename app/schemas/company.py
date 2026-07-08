from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.company import BillingStatus


class CompanyBase(BaseModel):
    company_name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    subscription_plan: Optional[str] = "FREE"
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    employee_limit: Optional[int] = 10
    billing_status: Optional[BillingStatus] = BillingStatus.PENDING_APPROVAL
    is_active: Optional[bool] = True
    trial_used: Optional[bool] = False
    last_quota_reset_at: Optional[datetime] = None


class CompanyCreate(CompanyBase):
    subscription_end: datetime


class CompanyUpdate(BaseModel):
    company_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    employee_limit: Optional[int] = None
    billing_status: Optional[BillingStatus] = None
    is_active: Optional[bool] = None
    trial_used: Optional[bool] = None
    last_quota_reset_at: Optional[datetime] = None


class CompanyResponse(CompanyBase):
    id: int
    current_employee_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyStatistics(BaseModel):
    company_id: int
    company_name: str
    employee_limit: int
    current_employee_count: int
    remaining_slots: int
    total_departments: int
    billing_status: BillingStatus
    is_active: bool