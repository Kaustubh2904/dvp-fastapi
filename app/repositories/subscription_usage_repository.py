from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base_repository import BaseRepository
from app.models.subscription_usage import SubscriptionUsage


class SubscriptionUsageRepository(BaseRepository[SubscriptionUsage]):
    def __init__(self):
        super().__init__(SubscriptionUsage)

    @staticmethod
    def month_key_for(dt: Optional[datetime] = None) -> str:
        dt = dt or datetime.utcnow()
        return f"{dt.year:04d}-{dt.month:02d}"

    async def get_for_company_month(self, db: AsyncSession, company_id: int, month_key: Optional[str] = None) -> Optional[SubscriptionUsage]:
        month_key = month_key or self.month_key_for()
        query = select(self.model).where(
            self.model.company_id == company_id,
            self.model.month_key == month_key,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()


subscription_usage_repository = SubscriptionUsageRepository()