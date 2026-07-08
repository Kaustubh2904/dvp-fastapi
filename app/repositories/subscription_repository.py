from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.base_repository import BaseRepository
from app.models.subscription import Subscription
from app.models.company import BillingStatus


class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self):
        super().__init__(Subscription)

    async def get_by_company(self, db: AsyncSession, company_id: int) -> Optional[Subscription]:
        query = select(self.model).where(self.model.company_id == company_id).order_by(self.model.created_at.desc()).limit(1)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_by_company(self, db: AsyncSession, company_id: int) -> Optional[Subscription]:
        query = (
            select(self.model)
            .where(
                self.model.company_id == company_id,
                self.model.is_active == True,
                self.model.billing_status.in_([
                    BillingStatus.TRIAL,
                    BillingStatus.ACTIVE,
                    BillingStatus.SCHEDULED_CHANGE,
                ]),
            )
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_expiring(self, db: AsyncSession, within_days: int = 7) -> list[Subscription]:
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=within_days)
        query = select(self.model).where(
            and_(
                self.model.is_active == True,
                self.model.end_date >= now,
                self.model.end_date <= future
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_expired(self, db: AsyncSession) -> list[Subscription]:
        now = datetime.now(timezone.utc)
        query = select(self.model).where(
            and_(
                self.model.is_active == True,
                self.model.end_date < now,
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())


subscription_repository = SubscriptionRepository()