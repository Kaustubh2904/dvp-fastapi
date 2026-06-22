from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.company import BillingStatus


class SubscriptionBase(BaseModel):
    plan_name: str
    employee_limit: int
    start_date: Optional[datetime] = None
    end_date: datetime
    billing_status: Optional[BillingStatus] = BillingStatus.PENDING
    is_active: Optional[bool] = True


class SubscriptionCreate(SubscriptionBase):
    company_id: int


class SubscriptionUpdate(BaseModel):
    plan_name: Optional[str] = None
    employee_limit: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    billing_status: Optional[BillingStatus] = None
    is_active: Optional[bool] = None


class SubscriptionResponse(SubscriptionBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardMetrics(BaseModel):
    total_companies: int
    active_companies: int
    expired_companies: int
    suspended_companies: int
    total_employees: int
    utilization_rate: float