from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.repositories.subscription_repository import subscription_repository
from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate, DashboardMetrics
from app.repositories.company_repository import company_repository
from app.models.company import Company, BillingStatus
from app.models.employee import Employee
from app.services.notification_service import notification_service
from app.services.audit_service import audit_log_service


class SubscriptionService:
    @staticmethod
    async def create_subscription(
        db: AsyncSession, obj_in: SubscriptionCreate, actor_id: Optional[int] = None
    ) -> Subscription:
        company = await company_repository.get(db, obj_in.company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        subscription = await subscription_repository.create(db, obj_in=obj_in)

        company.subscription_plan = subscription.plan_name
        company.subscription_start = subscription.start_date
        company.subscription_end = subscription.end_date
        company.employee_limit = subscription.employee_limit
        company.billing_status = subscription.billing_status
        company.is_active = subscription.is_active
        db.add(company)
        await db.commit()

        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id,
            action="CREATE_SUBSCRIPTION",
            entity_type="Subscription",
            entity_id=subscription.id,
            new_value={"plan": subscription.plan_name, "company_id": subscription.company_id},
        )
        return subscription

    @staticmethod
    async def update_subscription(
        db: AsyncSession, subscription_id: int, obj_in: SubscriptionUpdate, actor_id: Optional[int] = None
    ) -> Subscription:
        sub = await subscription_repository.get(db, subscription_id)
        if not sub:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription record not found")

        old_val = {"plan": sub.plan_name, "billing_status": sub.billing_status.value}

        updated_sub = await subscription_repository.update(db, db_obj=sub, obj_in=obj_in)

        company = await company_repository.get(db, updated_sub.company_id)
        if company:
            if obj_in.plan_name is not None:
                company.subscription_plan = updated_sub.plan_name
            if obj_in.start_date is not None:
                company.subscription_start = updated_sub.start_date
            if obj_in.end_date is not None:
                company.subscription_end = updated_sub.end_date
            if obj_in.employee_limit is not None:
                company.employee_limit = updated_sub.employee_limit
            if obj_in.billing_status is not None:
                company.billing_status = updated_sub.billing_status
            if obj_in.is_active is not None:
                company.is_active = updated_sub.is_active
            db.add(company)
            await db.commit()

        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id,
            action="UPDATE_SUBSCRIPTION",
            entity_type="Subscription",
            entity_id=subscription_id,
            old_value=old_val,
            new_value=obj_in.model_dump(exclude_unset=True, mode="json"),
        )
        return updated_sub

    @staticmethod
    async def check_expiring_companies(db: AsyncSession) -> list[int]:
        expiring = await subscription_repository.get_expiring(db, within_days=7)
        notified_companies = []

        for sub in expiring:
            from app.models.user import User, UserRole
            admin_query = select(User).where(
                User.company_id == sub.company_id,
                User.role == UserRole.ADMIN
            )
            result = await db.execute(admin_query)
            admins = result.scalars().all()

            days_left = (sub.end_date.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days
            title = "Subscription Expiry Notice"
            message = f"Your subscription for plan '{sub.plan_name}' is expiring in {days_left} days. Please renew to avoid service disruption."

            for admin in admins:
                await notification_service.create_in_app_notification(db, user_id=admin.id, title=title, message=message)

            notified_companies.append(sub.company_id)

        return notified_companies

    @staticmethod
    async def suspend_expired_companies(db: AsyncSession) -> list[int]:
        now = datetime.now(timezone.utc)
        query = select(Subscription).where(
            Subscription.is_active == True,
            Subscription.end_date < now,
            Subscription.billing_status != BillingStatus.EXPIRED
        )
        result = await db.execute(query)
        expired = result.scalars().all()
        suspended_companies = []

        for sub in expired:
            sub.billing_status = BillingStatus.EXPIRED
            sub.is_active = False
            db.add(sub)

            company = await company_repository.get(db, sub.company_id)
            if company:
                company.billing_status = BillingStatus.SUSPENDED
                company.is_active = False
                db.add(company)

                from app.models.user import User, UserRole
                admin_query = select(User).where(
                    User.company_id == sub.company_id,
                    User.role == UserRole.ADMIN
                )
                admin_res = await db.execute(admin_query)
                admins = admin_res.scalars().all()

                title = "Account Suspended"
                message = "Your DVP account has been suspended due to an expired subscription. Please renew your plan."

                for admin in admins:
                    await notification_service.create_in_app_notification(db, user_id=admin.id, title=title, message=message)

                suspended_companies.append(sub.company_id)

        await db.commit()
        return suspended_companies

    @staticmethod
    async def get_dashboard_metrics(db: AsyncSession) -> DashboardMetrics:
        total_comp = await db.execute(select(func.count(Company.id)))
        total_comp_count = total_comp.scalar() or 0

        active_comp = await db.execute(select(func.count(Company.id)).where(Company.is_active == True))
        active_comp_count = active_comp.scalar() or 0

        expired_comp = await db.execute(select(func.count(Company.id)).where(Company.billing_status == BillingStatus.EXPIRED))
        expired_comp_count = expired_comp.scalar() or 0

        suspended_comp = await db.execute(select(func.count(Company.id)).where(Company.billing_status == BillingStatus.SUSPENDED))
        suspended_comp_count = suspended_comp.scalar() or 0

        total_emp = await db.execute(select(func.count(Employee.id)))
        total_emp_count = total_emp.scalar() or 0

        util = 0.0
        if total_comp_count > 0:
            sum_limit = await db.execute(select(func.sum(Company.employee_limit)))
            total_limit = sum_limit.scalar() or 0
            if total_limit > 0:
                util = round((total_emp_count / total_limit) * 100, 2)

        return DashboardMetrics(
            total_companies=total_comp_count,
            active_companies=active_comp_count,
            expired_companies=expired_comp_count,
            suspended_companies=suspended_comp_count,
            total_employees=total_emp_count,
            utilization_rate=util,
        )


subscription_service = SubscriptionService()