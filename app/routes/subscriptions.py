from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.postgres import get_db
from app.core.dependencies.dependencies import require_subscription_portal_access, require_subscription_admin, require_admin, get_current_user
from app.models.user import User, UserRole
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    DashboardMetrics,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    SubscriptionRequestCreate,
    SubscriptionRequestReview,
)
from app.services.subscription_service import subscription_service
from app.repositories.subscription_repository import subscription_repository

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/plans", dependencies=[require_subscription_portal_access()])
async def list_plans(db: AsyncSession = Depends(get_db)):
    return await subscription_service.list_plans(db)


@router.post("/plans", dependencies=[require_subscription_admin()])
async def create_plan(
    obj_in: SubscriptionPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await subscription_service.create_plan(db, obj_in=obj_in, actor_id=current_user.id)


@router.put("/plans/{plan_id}", dependencies=[require_subscription_admin()])
async def update_plan(
    plan_id: int,
    obj_in: SubscriptionPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await subscription_service.update_plan(db, plan_id=plan_id, obj_in=obj_in, actor_id=current_user.id)


@router.get("/mine")
async def get_my_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await subscription_service.get_company_subscription_details(db, current_user.company_id)


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED, dependencies=[require_subscription_admin()])
async def create_subscription(
    obj_in: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await subscription_service.create_subscription(db, obj_in=obj_in, actor_id=current_user.id)


@router.put("/{subscription_id}", response_model=SubscriptionResponse, dependencies=[require_subscription_admin()])
async def update_subscription(
    subscription_id: int,
    obj_in: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await subscription_service.update_subscription(
        db, subscription_id=subscription_id, obj_in=obj_in, actor_id=current_user.id
    )


@router.post("/requests", dependencies=[require_admin()])
async def create_subscription_request(
    obj_in: SubscriptionRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await subscription_service.request_subscription_change(db, current_user=current_user, obj_in=obj_in)


@router.get("/requests", dependencies=[require_admin()])
async def list_subscription_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = None if current_user.role == UserRole.SUPERADMIN else current_user.company_id
    return await subscription_service.list_requests(db, company_id=company_id, skip=skip, limit=limit)


@router.get("/requests/{request_id}", dependencies=[require_admin()])
async def get_subscription_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = await subscription_service.get_request(db, request_id)
    if current_user.role != UserRole.SUPERADMIN and request.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return request


@router.post("/requests/{request_id}/review", dependencies=[require_subscription_admin()])
async def review_subscription_request(
    request_id: int,
    obj_in: SubscriptionRequestReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await subscription_service.review_subscription_request(db, request_id=request_id, reviewer=current_user, obj_in=obj_in)


@router.get("/dashboard", response_model=DashboardMetrics, dependencies=[require_subscription_portal_access()])
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
):
    return await subscription_service.get_dashboard_metrics(db)


@router.get("/expiring", dependencies=[require_subscription_portal_access()])
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


@router.post("/trigger-checks", dependencies=[require_subscription_portal_access()])
async def trigger_subscription_checks(db: AsyncSession = Depends(get_db)):
    notified = await subscription_service.check_expiring_companies(db)
    suspended = await subscription_service.suspend_expired_companies(db)
    return {
        "message": "Subscription validation check finished.",
        "notified_companies": notified,
        "suspended_companies": suspended,
    }