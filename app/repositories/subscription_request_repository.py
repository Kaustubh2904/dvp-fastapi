from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base_repository import BaseRepository
from app.models.subscription_request import SubscriptionRequest, SubscriptionRequestStatus


class SubscriptionRequestRepository(BaseRepository[SubscriptionRequest]):
    def __init__(self):
        super().__init__(SubscriptionRequest)

    async def get_by_company(self, db: AsyncSession, company_id: int, skip: int = 0, limit: int = 100) -> list[SubscriptionRequest]:
        query = (
            select(self.model)
            .where(self.model.company_id == company_id)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_pending(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> list[SubscriptionRequest]:
        query = (
            select(self.model)
            .where(self.model.status == SubscriptionRequestStatus.PENDING_APPROVAL)
            .order_by(self.model.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())


subscription_request_repository = SubscriptionRequestRepository()