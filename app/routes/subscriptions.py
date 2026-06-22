from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.postgres import get_db
from app.core.dependencies.dependencies import require_superadmin, get_current_user
from app.models.user import User
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse, DashboardMetrics
from app.services.subscription_service import subscription_service
from app.repositories.subscription_repository import subscription_repository

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED, dependencies=[require_superadmin()])
async def create_subscription(
    obj_in: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await subscription_service.create_subscription(db, obj_in=obj_in, actor_id=current_user.id)


@router.put("/{subscription_id}", response_model=SubscriptionResponse, dependencies=[require_superadmin()])
async def update_subscription(
    subscription_id: int,
    obj_in: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await subscription_service.update_subscription(
        db, subscription_id=subscription_id, obj_in=obj_in, actor_id=current_user.id
    )


@router.get("/dashboard", response_model=DashboardMetrics, dependencies=[require_superadmin()])
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
):
    return await subscription_service.get_dashboard_metrics(db)


@router.get("/expiring", dependencies=[require_superadmin()])
async def view_expiring_subscriptions(
    days: int = Query(7, ge=1),
    db: AsyncSession = Depends(get_db),
):
    exp = await subscription_repository.get_expiring(db, within_days=days)
    return [
        {
            "subscription_id": item.id,
            "company_id": item.company_id,
            "plan_name": item.plan_name,
            "end_date": item.end_date,
            "employee_limit": item.employee_limit,
            "billing_status": item.billing_status.value,
        }
        for item in exp
    ]


@router.post("/trigger-checks", dependencies=[require_superadmin()])
async def trigger_subscription_checks(db: AsyncSession = Depends(get_db)):
    notified = await subscription_service.check_expiring_companies(db)
    suspended = await subscription_service.suspend_expired_companies(db)
    return {
        "message": "Subscription validation check finished.",
        "notified_companies": notified,
        "suspended_companies": suspended,
    }