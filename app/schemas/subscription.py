from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field
from app.models.company import BillingStatus


class SubscriptionBase(BaseModel):
    plan_name: str
    employee_limit: int
    start_date: Optional[datetime] = None
    end_date: datetime
    billing_status: Optional[BillingStatus] = BillingStatus.PENDING_APPROVAL
    is_active: Optional[bool] = True
    trial_used: Optional[bool] = False
    scheduled_plan_name: Optional[str] = None
    scheduled_effective_at: Optional[datetime] = None


class SubscriptionCreate(SubscriptionBase):
    company_id: int


class SubscriptionUpdate(BaseModel):
    plan_name: Optional[str] = None
    employee_limit: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    billing_status: Optional[BillingStatus] = None
    is_active: Optional[bool] = None
    trial_used: Optional[bool] = None
    scheduled_plan_name: Optional[str] = None
    scheduled_effective_at: Optional[datetime] = None


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


class PlanFeatureSet(BaseModel):
    max_admins: int = 1
    max_employees: int = 10
    monthly_document_uploads: int = 100
    storage_mb: int = 1024
    chat_access: bool = False
    api_access: bool = False
    analytics_access: bool = False
    ticket_priority: str = "LOW"
    white_label_support: bool = False
    audit_log_retention_days: int = 90
    billing_cycle_days: int = 30
    trial_days: int = 14
    price_cents: int = 0
    is_active: bool = True
    is_custom: bool = False


class SubscriptionPlanCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str
    description: Optional[str] = None
    max_admins: int = 1
    max_employees: int = 10
    monthly_document_uploads: int = 100
    storage_mb: int = 1024
    chat_access: bool = False
    api_access: bool = False
    analytics_access: bool = False
    ticket_priority: str = "LOW"
    white_label_support: bool = False
    audit_log_retention_days: int = 90
    billing_cycle_days: int = 30
    trial_days: int = 14
    price_cents: int = 0
    is_active: bool = True
    is_custom: bool = False


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    max_admins: Optional[int] = None
    max_employees: Optional[int] = None
    monthly_document_uploads: Optional[int] = None
    storage_mb: Optional[int] = None
    chat_access: Optional[bool] = None
    api_access: Optional[bool] = None
    analytics_access: Optional[bool] = None
    ticket_priority: Optional[str] = None
    white_label_support: Optional[bool] = None
    audit_log_retention_days: Optional[int] = None
    billing_cycle_days: Optional[int] = None
    trial_days: Optional[int] = None
    price_cents: Optional[int] = None
    is_active: Optional[bool] = None
    is_custom: Optional[bool] = None


class SubscriptionPlanResponse(SubscriptionPlanCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionRequestCreate(BaseModel):
    requested_plan_code: str
    request_type: str = "UPGRADE"
    notes: Optional[str] = None
    immediate_effect: bool = False


class SubscriptionRequestReview(BaseModel):
    decision: str
    review_notes: Optional[str] = None
    force_immediate: bool = False


class SubscriptionRequestResponse(BaseModel):
    id: int
    company_id: int
    requested_by_id: int
    reviewed_by_id: Optional[int] = None
    request_type: str
    current_plan_code: Optional[str] = None
    requested_plan_code: str
    status: str
    immediate_effect: bool
    prorated_value_cents: int = 0
    notes: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UsageSummary(BaseModel):
    company_id: int
    month_key: str
    employee_count: int
    monthly_document_uploads: int
    storage_used_bytes: int
    last_reset_at: Optional[datetime] = None
