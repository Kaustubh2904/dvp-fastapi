from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base_repository import BaseRepository
from app.models.subscription_plan import SubscriptionPlan


class SubscriptionPlanRepository(BaseRepository[SubscriptionPlan]):
    def __init__(self):
        super().__init__(SubscriptionPlan)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[SubscriptionPlan]:
        query = select(self.model).where(self.model.code == code)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_active(self, db: AsyncSession) -> list[SubscriptionPlan]:
        query = select(self.model).where(self.model.is_active == True).order_by(self.model.price_cents.asc())
        result = await db.execute(query)
        return list(result.scalars().all())


subscription_plan_repository = SubscriptionPlanRepository()