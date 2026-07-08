from datetime import datetime, timezone, timedelta
from typing import Optional, Any

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import settings
from app.models.company import Company, BillingStatus
from app.models.employee import Employee
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription_request import SubscriptionRequest, SubscriptionRequestStatus, SubscriptionRequestType
from app.models.subscription_usage import SubscriptionUsage
from app.models.user import User, UserRole
from app.repositories.company_repository import company_repository
from app.repositories.subscription_plan_repository import subscription_plan_repository
from app.repositories.subscription_repository import subscription_repository
from app.repositories.subscription_request_repository import subscription_request_repository
from app.repositories.subscription_usage_repository import subscription_usage_repository
from app.schemas.subscription import (
    DashboardMetrics,
    SubscriptionCreate,
    SubscriptionPlanCreate,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdate,
    SubscriptionRequestCreate,
    SubscriptionRequestReview,
    SubscriptionRequestResponse,
    UsageSummary,
    SubscriptionUpdate,
)
from app.services.audit_service import audit_log_service
from app.services.email_service import email_service
from app.services.notification_service import notification_service


class SubscriptionService:
    ACTIVE_STATUSES = {BillingStatus.TRIAL, BillingStatus.ACTIVE, BillingStatus.SCHEDULED_CHANGE}

    @staticmethod
    def _month_key(dt: Optional[datetime] = None) -> str:
        dt = dt or datetime.now(timezone.utc)
        return f"{dt.year:04d}-{dt.month:02d}"

    @staticmethod
    def _cycle_end(start_date: datetime, billing_cycle_days: int) -> datetime:
        return start_date + timedelta(days=billing_cycle_days)

    async def get_plan_by_code(self, db: AsyncSession, code: str) -> SubscriptionPlan:
        plan = await subscription_plan_repository.get_by_code(db, code.upper())
        if not plan or not plan.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription plan not found")
        return plan

    async def list_plans(self, db: AsyncSession) -> list[SubscriptionPlanResponse]:
        plans = await subscription_plan_repository.get_active(db)
        return [SubscriptionPlanResponse.model_validate(plan) for plan in plans]

    async def create_plan(self, db: AsyncSession, obj_in: SubscriptionPlanCreate, actor_id: Optional[int] = None) -> SubscriptionPlanResponse:
        existing = await subscription_plan_repository.get_by_code(db, obj_in.code.upper())
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan code already exists")
        plan = await subscription_plan_repository.create(
            db,
            obj_in={**obj_in.model_dump(), "code": obj_in.code.upper()},
        )
        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id,
            action="CREATE_SUBSCRIPTION_PLAN",
            entity_type="SubscriptionPlan",
            entity_id=plan.id,
            new_value=obj_in.model_dump(mode="json"),
        )
        return SubscriptionPlanResponse.model_validate(plan)

    async def update_plan(self, db: AsyncSession, plan_id: int, obj_in: SubscriptionPlanUpdate, actor_id: Optional[int] = None) -> SubscriptionPlanResponse:
        plan = await subscription_plan_repository.get(db, plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        old_value = {"code": plan.code, "price_cents": plan.price_cents, "is_active": plan.is_active}
        updated = await subscription_plan_repository.update(db, db_obj=plan, obj_in=obj_in)
        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id,
            action="UPDATE_SUBSCRIPTION_PLAN",
            entity_type="SubscriptionPlan",
            entity_id=plan_id,
            old_value=old_value,
            new_value=obj_in.model_dump(exclude_unset=True, mode="json"),
        )
        return SubscriptionPlanResponse.model_validate(updated)

    async def _get_company_admins(self, db: AsyncSession, company_id: int) -> list[User]:
        query = select(User).where(User.company_id == company_id, User.role.in_([UserRole.ADMIN, UserRole.HR]), User.is_active == True)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def _get_superadmins(self, db: AsyncSession) -> list[User]:
        query = select(User).where(User.role == UserRole.SUPERADMIN, User.is_active == True)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def _notify_company_admins(self, db: AsyncSession, company_id: int, title: str, message: str) -> None:
        for admin in await self._get_company_admins(db, company_id):
            await notification_service.create_in_app_notification(db, user_id=admin.id, title=title, message=message)

    async def _notify_superadmins(self, db: AsyncSession, title: str, message: str) -> None:
        for user in await self._get_superadmins(db):
            await notification_service.create_in_app_notification(db, user_id=user.id, title=title, message=message)

    async def _queue_email(self, db: AsyncSession, recipient_email: str, subject: str, template_name: str, body: str, background_tasks: Optional[BackgroundTasks] = None) -> None:
        await email_service.queue_email(
            db=db,
            recipient_email=recipient_email,
            subject=subject,
            template_name=template_name,
            context={"title": subject, "body": body},
            background_tasks=background_tasks,
        )

    async def _get_usage(self, db: AsyncSession, company_id: int) -> SubscriptionUsage:
        month_key = self._month_key()
        usage = await subscription_usage_repository.get_for_company_month(db, company_id, month_key)
        if usage:
            return usage
        company = await company_repository.get(db, company_id)
        usage = await subscription_usage_repository.create(
            db,
            obj_in={
                "company_id": company_id,
                "month_key": month_key,
                "employee_count": company.current_employee_count if company else 0,
                "monthly_document_uploads": 0,
                "storage_used_bytes": 0,
                "last_reset_at": datetime.now(timezone.utc),
            },
        )
        return usage

    async def get_current_subscription(self, db: AsyncSession, company_id: int) -> Optional[Subscription]:
        return await subscription_repository.get_active_by_company(db, company_id)

    async def initialize_company_subscription(
        self,
        db: AsyncSession,
        company: Company,
        admin_user: User,
        plan_code: str,
        actor_id: Optional[int] = None,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> Subscription:
        plan = await self.get_plan_by_code(db, plan_code)
        now = datetime.now(timezone.utc)
        is_free_trial = plan.code == "FREE"
        if is_free_trial and company.trial_used:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trial has already been consumed for this company")

        status_value = BillingStatus.TRIAL if is_free_trial else BillingStatus.ACTIVE
        end_date = self._cycle_end(now, plan.trial_days if is_free_trial else plan.billing_cycle_days)
        subscription = await subscription_repository.create(
            db,
            obj_in={
                "company_id": company.id,
                "plan_name": plan.code,
                "employee_limit": plan.max_employees,
                "start_date": now,
                "end_date": end_date,
                "billing_status": status_value,
                "is_active": True,
                "trial_used": is_free_trial,
            },
        )

        company.subscription_plan = plan.code
        company.subscription_start = now
        company.subscription_end = end_date
        company.employee_limit = plan.max_employees
        company.billing_status = status_value
        company.is_active = True
        company.trial_used = company.trial_used or is_free_trial
        company.last_quota_reset_at = now
        db.add(company)
        await db.commit()

        await self._get_usage(db, company.id)

        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id or admin_user.id,
            action="INITIAL_SUBSCRIPTION_CREATED",
            entity_type="Subscription",
            entity_id=subscription.id,
            new_value={"plan": plan.code, "status": status_value.value, "company_id": company.id},
        )

        title = "Subscription Activated"
        message = f"Your company subscription has been initialized with the {plan.name} plan."
        await self._notify_company_admins(db, company.id, title, message)
        await self._notify_superadmins(db, title, f"Company {company.company_name} activated the {plan.code} plan.")
        await self._queue_email(db, admin_user.email, title, "subscription_activation", message, background_tasks)
        return subscription

    async def create_subscription(
        self, db: AsyncSession, obj_in: SubscriptionCreate, actor_id: Optional[int] = None
    ) -> Subscription:
        company = await company_repository.get(db, obj_in.company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        plan = await self.get_plan_by_code(db, obj_in.plan_name)
        subscription = await subscription_repository.create(
            db,
            obj_in={
                "company_id": company.id,
                "plan_name": plan.code,
                "employee_limit": obj_in.employee_limit or plan.max_employees,
                "start_date": obj_in.start_date or datetime.now(timezone.utc),
                "end_date": obj_in.end_date,
                "billing_status": obj_in.billing_status or BillingStatus.ACTIVE,
                "is_active": obj_in.is_active if obj_in.is_active is not None else True,
                "trial_used": plan.code == "FREE",
            },
        )
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

    async def update_subscription(
        self, db: AsyncSession, subscription_id: int, obj_in: SubscriptionUpdate, actor_id: Optional[int] = None
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
            if obj_in.trial_used is not None:
                company.trial_used = obj_in.trial_used
            if obj_in.scheduled_plan_name is not None:
                company.subscription_plan = obj_in.scheduled_plan_name
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

    async def request_subscription_change(
        self,
        db: AsyncSession,
        current_user: User,
        obj_in: SubscriptionRequestCreate,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> SubscriptionRequest:
        company = await company_repository.get(db, current_user.company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        target_plan = await self.get_plan_by_code(db, obj_in.requested_plan_code)
        current_sub = await self.get_current_subscription(db, company.id) or await subscription_repository.get_by_company(db, company.id)
        current_plan_code = current_sub.plan_name if current_sub else company.subscription_plan
        request_type = SubscriptionRequestType(obj_in.request_type.upper()) if obj_in.request_type.upper() in SubscriptionRequestType.__members__ else SubscriptionRequestType.UPGRADE

        prorated_value = 0
        if current_sub and target_plan.price_cents > 0 and current_sub.end_date > datetime.now(timezone.utc):
            remaining_days = max((current_sub.end_date - datetime.now(timezone.utc)).days, 0)
            cycle_days = max((current_sub.end_date - current_sub.start_date).days, 1)
            prorated_value = int((target_plan.price_cents * remaining_days) / cycle_days)

        request = await subscription_request_repository.create(
            db,
            obj_in={
                "company_id": company.id,
                "requested_by_id": current_user.id,
                "request_type": request_type,
                "current_plan_code": current_plan_code,
                "requested_plan_code": target_plan.code,
                "status": SubscriptionRequestStatus.PENDING_APPROVAL,
                "immediate_effect": obj_in.immediate_effect,
                "prorated_value_cents": prorated_value,
                "notes": obj_in.notes,
            },
        )

        await audit_log_service.log_action(
            db=db,
            actor_id=current_user.id,
            action="SUBSCRIPTION_REQUEST_CREATED",
            entity_type="SubscriptionRequest",
            entity_id=request.id,
            new_value={"requested_plan_code": target_plan.code, "request_type": request_type.value, "company_id": company.id},
        )

        await self._notify_superadmins(
            db,
            "Subscription request pending",
            f"Company {company.company_name} requested a {request_type.value.lower()} to {target_plan.name}.",
        )
        await self._notify_company_admins(
            db,
            company.id,
            "Subscription request submitted",
            f"Your {request_type.value.lower()} request for {target_plan.name} is pending review.",
        )
        if current_user.email:
            await self._queue_email(
                db,
                current_user.email,
                "Subscription request submitted",
                "subscription_request",
                f"Your request for {target_plan.name} has been submitted for review.",
                background_tasks,
            )

        return request

    async def review_subscription_request(
        self,
        db: AsyncSession,
        request_id: int,
        reviewer: User,
        obj_in: SubscriptionRequestReview,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> SubscriptionRequest:
        request = await subscription_request_repository.get(db, request_id)
        if not request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription request not found")
        if request.status != SubscriptionRequestStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request is already processed")

        company = await company_repository.get(db, request.company_id)
        plan = await self.get_plan_by_code(db, request.requested_plan_code)
        decision = obj_in.decision.upper()
        if decision == "REJECT":
            request.status = SubscriptionRequestStatus.REJECTED
            request.reviewed_by_id = reviewer.id
            request.review_notes = obj_in.review_notes
            db.add(request)
            await db.commit()
            await audit_log_service.log_action(
                db=db,
                actor_id=reviewer.id,
                action="SUBSCRIPTION_REQUEST_REJECTED",
                entity_type="SubscriptionRequest",
                entity_id=request.id,
                new_value={"company_id": company.id, "requested_plan_code": plan.code},
            )
            await self._notify_company_admins(db, company.id, "Subscription request rejected", obj_in.review_notes or "Your request was rejected.")
            return request

        force_immediate = obj_in.force_immediate or request.immediate_effect
        current_sub = await self.get_current_subscription(db, company.id)
        applied_now = True
        if request.request_type == SubscriptionRequestType.DOWNGRADE and not force_immediate and current_sub:
            current_sub.billing_status = BillingStatus.SCHEDULED_CHANGE
            current_sub.scheduled_plan_name = plan.code
            current_sub.scheduled_effective_at = current_sub.end_date
            company.billing_status = BillingStatus.SCHEDULED_CHANGE
            company.subscription_plan = current_sub.plan_name
            db.add(current_sub)
            db.add(company)
            applied_now = False
            action_name = "SUBSCRIPTION_DOWNGRADE_SCHEDULED"
        else:
            await self._apply_subscription_plan(db, company, plan, reviewer, current_sub=current_sub)
            action_name = "SUBSCRIPTION_REQUEST_APPROVED"

        request.status = SubscriptionRequestStatus.APPROVED
        request.reviewed_by_id = reviewer.id
        request.review_notes = obj_in.review_notes
        db.add(request)
        await db.commit()

        await audit_log_service.log_action(
            db=db,
            actor_id=reviewer.id,
            action=action_name,
            entity_type="SubscriptionRequest",
            entity_id=request.id,
            new_value={"company_id": company.id, "plan_code": plan.code, "applied_now": applied_now},
        )

        await self._notify_company_admins(
            db,
            company.id,
            "Subscription request approved",
            f"Your request for {plan.name} has been approved{' and scheduled for the next billing cycle' if not applied_now else ''}.",
        )
        await self._notify_superadmins(db, "Subscription request processed", f"Company {company.company_name} request {request.id} approved.")
        return request

    async def _apply_subscription_plan(
        self,
        db: AsyncSession,
        company: Company,
        plan: SubscriptionPlan,
        actor: User,
        current_sub: Optional[Subscription] = None,
    ) -> Subscription:
        now = datetime.now(timezone.utc)
        is_trial = plan.code == "FREE"
        if is_trial and company.trial_used:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Company has already used the free trial")

        end_date = self._cycle_end(now, plan.trial_days if is_trial else plan.billing_cycle_days)
        if current_sub:
            old_value = {"plan": current_sub.plan_name, "status": current_sub.billing_status.value}
            current_sub.plan_name = plan.code
            current_sub.employee_limit = plan.max_employees
            current_sub.start_date = now
            current_sub.end_date = end_date
            current_sub.billing_status = BillingStatus.TRIAL if is_trial else BillingStatus.ACTIVE
            current_sub.is_active = True
            current_sub.trial_used = is_trial
            current_sub.scheduled_plan_name = None
            current_sub.scheduled_effective_at = None
            db.add(current_sub)
            subscription = current_sub
        else:
            subscription = await subscription_repository.create(
                db,
                obj_in={
                    "company_id": company.id,
                    "plan_name": plan.code,
                    "employee_limit": plan.max_employees,
                    "start_date": now,
                    "end_date": end_date,
                    "billing_status": BillingStatus.TRIAL if is_trial else BillingStatus.ACTIVE,
                    "is_active": True,
                    "trial_used": is_trial,
                },
            )
            old_value = None

        company.subscription_plan = plan.code
        company.subscription_start = now
        company.subscription_end = end_date
        company.employee_limit = plan.max_employees
        company.billing_status = BillingStatus.TRIAL if is_trial else BillingStatus.ACTIVE
        company.is_active = True
        company.trial_used = company.trial_used or is_trial
        company.last_quota_reset_at = now
        db.add(company)
        await db.commit()

        await self._get_usage(db, company.id)
        await audit_log_service.log_action(
            db=db,
            actor_id=actor.id,
            action="SUBSCRIPTION_PLAN_APPLIED",
            entity_type="Subscription",
            entity_id=subscription.id,
            old_value=old_value,
            new_value={"plan": plan.code, "company_id": company.id, "status": company.billing_status.value},
        )
        await self._notify_company_admins(db, company.id, "Subscription updated", f"Your subscription has been set to {plan.name}.")
        return subscription

    async def request_renewal(self, db: AsyncSession, current_user: User, background_tasks: Optional[BackgroundTasks] = None) -> SubscriptionRequest:
        current_sub = await self.get_current_subscription(db, current_user.company_id) or await subscription_repository.get_by_company(db, current_user.company_id)
        if not current_sub:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No subscription found for company")
        return await self.request_subscription_change(
            db,
            current_user=current_user,
            obj_in=SubscriptionRequestCreate(requested_plan_code=current_sub.plan_name, request_type="RENEWAL", immediate_effect=True),
            background_tasks=background_tasks,
        )

    async def ensure_mutation_allowed(self, db: AsyncSession, company_id: int, feature: str = "mutation") -> Company:
        company = await company_repository.get(db, company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        if company.billing_status not in self.ACTIVE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your subscription is read-only. Renew or request a subscription change to continue this action.",
            )
        return company

    async def ensure_feature_available(self, db: AsyncSession, company_id: int, feature: str) -> None:
        company = await company_repository.get(db, company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        if feature in {"read_only", "dashboard", "notifications", "documents_view", "employees_view", "support_ticket"}:
            return
        if company.billing_status not in self.ACTIVE_STATUSES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This feature requires an active subscription")

        sub = await self.get_current_subscription(db, company_id)
        if not sub:
            return
        plan = await self.get_plan_by_code(db, sub.plan_name)
        feature_map = {
            "chat": plan.chat_access,
            "api": plan.api_access,
            "analytics": plan.analytics_access,
            "white_label": plan.white_label_support,
        }
        if feature in feature_map and not feature_map[feature]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{feature.replace('_', ' ').title()} is not available on this plan")

    async def ensure_employee_capacity(self, db: AsyncSession, company_id: int, increment: int = 1) -> None:
        company = await self.ensure_mutation_allowed(db, company_id)
        if company.current_employee_count + increment > company.employee_limit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Company employee limit reached. Upgrade subscription plan.")

    async def increment_monthly_uploads(self, db: AsyncSession, company_id: int, storage_bytes: int = 0) -> SubscriptionUsage:
        await self.ensure_document_upload_capacity(db, company_id, storage_bytes=storage_bytes)
        usage = await self._get_usage(db, company_id)
        usage.monthly_document_uploads += 1
        usage.storage_used_bytes += storage_bytes
        db.add(usage)
        await db.commit()
        return usage

    async def ensure_document_upload_capacity(self, db: AsyncSession, company_id: int, storage_bytes: int = 0) -> None:
        usage = await self._get_usage(db, company_id)
        sub = await self.get_current_subscription(db, company_id) or await subscription_repository.get_by_company(db, company_id)
        if sub:
            plan = await self.get_plan_by_code(db, sub.plan_name)
            if usage.monthly_document_uploads + 1 > plan.monthly_document_uploads:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Monthly document upload limit reached")
            if usage.storage_used_bytes + storage_bytes > plan.storage_mb * 1024 * 1024:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Storage limit reached")

    async def sync_employee_usage(self, db: AsyncSession, company_id: int) -> SubscriptionUsage:
        usage = await self._get_usage(db, company_id)
        company = await company_repository.get(db, company_id)
        usage.employee_count = company.current_employee_count if company else usage.employee_count
        db.add(usage)
        await db.commit()
        return usage

    async def get_usage_summary(self, db: AsyncSession, company_id: int) -> UsageSummary:
        usage = await self._get_usage(db, company_id)
        return UsageSummary(
            company_id=company_id,
            month_key=usage.month_key,
            employee_count=usage.employee_count,
            monthly_document_uploads=usage.monthly_document_uploads,
            storage_used_bytes=usage.storage_used_bytes,
            last_reset_at=usage.last_reset_at,
        )

    async def check_expiring_companies(self, db: AsyncSession) -> list[int]:
        soon = await subscription_repository.get_expiring(db, within_days=settings.DEFAULT_EXPIRY_REMINDER_DAYS)
        notified_companies = []
        for sub in soon:
            company = await company_repository.get(db, sub.company_id)
            if not company:
                continue
            days_left = max((sub.end_date.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days, 0)
            title = "Subscription Expiry Notice"
            message = f"Your subscription for plan '{sub.plan_name}' is expiring in {days_left} days. Please renew to avoid service disruption."
            await self._notify_company_admins(db, company.id, title, message)
            await self._notify_superadmins(db, title, f"Company {company.company_name} subscription expires in {days_left} days.")
            notified_companies.append(sub.company_id)
        return notified_companies

    async def suspend_expired_companies(self, db: AsyncSession) -> list[int]:
        expired = await subscription_repository.get_expired(db)
        affected = []
        for sub in expired:
            company = await company_repository.get(db, sub.company_id)
            if not company:
                continue
            sub.billing_status = BillingStatus.EXPIRED if sub.billing_status != BillingStatus.SUSPENDED else BillingStatus.SUSPENDED
            sub.is_active = False
            company.billing_status = BillingStatus.EXPIRED if sub.billing_status == BillingStatus.EXPIRED else BillingStatus.SUSPENDED
            company.is_active = False
            db.add(sub)
            db.add(company)
            affected.append(company.id)
            await self._notify_company_admins(db, company.id, "Subscription expired", "Your subscription has expired. You still have read-only access and can request renewal.")
            await self._notify_superadmins(db, "Subscription expired", f"Company {company.company_name} has expired.")
        await db.commit()
        return affected

    async def process_scheduled_changes(self, db: AsyncSession) -> list[int]:
        now = datetime.now(timezone.utc)
        query = select(Subscription).where(
            Subscription.billing_status == BillingStatus.SCHEDULED_CHANGE,
            Subscription.scheduled_effective_at != None,  # noqa: E711
            Subscription.scheduled_effective_at <= now,
        )
        result = await db.execute(query)
        due = result.scalars().all()
        processed = []
        superadmins = await self._get_superadmins(db)
        system_actor = superadmins[0] if superadmins else None
        for sub in due:
            company = await company_repository.get(db, sub.company_id)
            if not company or not sub.scheduled_plan_name:
                continue
            plan = await self.get_plan_by_code(db, sub.scheduled_plan_name)
            if system_actor is None:
                system_actor = User(
                    email="system@dvp.local",
                    first_name="System",
                    last_name="",
                    password_hash="",
                    role=UserRole.SUPERADMIN,
                    company_id=None,
                    is_active=True,
                    is_verified=True,
                )
            await self._apply_subscription_plan(db, company, plan, actor=system_actor, current_sub=sub)
            sub.scheduled_plan_name = None
            sub.scheduled_effective_at = None
            sub.billing_status = BillingStatus.ACTIVE
            processed.append(company.id)
        await db.commit()
        return processed

    async def reset_monthly_usage(self, db: AsyncSession) -> list[int]:
        month_key = self._month_key()
        companies = await company_repository.get_multi(db, skip=0, limit=10000)
        reset = []
        for company in companies:
            usage = await subscription_usage_repository.get_for_company_month(db, company.id, month_key)
            if not usage:
                usage = await subscription_usage_repository.create(
                    db,
                    obj_in={
                        "company_id": company.id,
                        "month_key": month_key,
                        "employee_count": company.current_employee_count,
                        "monthly_document_uploads": 0,
                        "storage_used_bytes": 0,
                        "last_reset_at": datetime.now(timezone.utc),
                    },
                )
            else:
                usage.monthly_document_uploads = 0
                usage.employee_count = company.current_employee_count
                usage.last_reset_at = datetime.now(timezone.utc)
                db.add(usage)
            company.last_quota_reset_at = datetime.now(timezone.utc)
            db.add(company)
            reset.append(company.id)
        await db.commit()
        return reset

    async def get_dashboard_metrics(self, db: AsyncSession) -> DashboardMetrics:
        total_comp = await db.execute(select(func.count(Company.id)))
        total_comp_count = total_comp.scalar() or 0

        active_comp = await db.execute(select(func.count(Company.id)).where(Company.billing_status.in_([BillingStatus.TRIAL, BillingStatus.ACTIVE, BillingStatus.SCHEDULED_CHANGE])))
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

    async def list_requests(self, db: AsyncSession, company_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> list[SubscriptionRequestResponse]:
        if company_id:
            items = await subscription_request_repository.get_by_company(db, company_id, skip=skip, limit=limit)
        else:
            items = await subscription_request_repository.get_pending(db, skip=skip, limit=limit)
        return [SubscriptionRequestResponse.model_validate(item) for item in items]

    async def get_request(self, db: AsyncSession, request_id: int) -> SubscriptionRequestResponse:
        request = await subscription_request_repository.get(db, request_id)
        if not request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription request not found")
        return SubscriptionRequestResponse.model_validate(request)

    async def get_company_subscription_details(self, db: AsyncSession, company_id: int) -> dict[str, Any]:
        company = await company_repository.get(db, company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        sub = await self.get_current_subscription(db, company_id)
        usage = await self.get_usage_summary(db, company_id)
        plan = await self.get_plan_by_code(db, sub.plan_name if sub else company.subscription_plan)
        return {
            "company_id": company.id,
            "company_name": company.company_name,
            "subscription_status": company.billing_status.value,
            "subscription_plan": company.subscription_plan,
            "subscription_start": company.subscription_start,
            "subscription_end": company.subscription_end,
            "trial_used": company.trial_used,
            "plan": SubscriptionPlanResponse.model_validate(plan),
            "usage": usage.model_dump(),
        }
subscription_service = SubscriptionService()