from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.base_repository import BaseRepository
from app.models.audit_log import AuditLog


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self):
        super().__init__(AuditLog)

    async def get_by_actor(self, db: AsyncSession, actor_id: int, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        query = select(self.model).where(self.model.actor_id == actor_id).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_entity(self, db: AsyncSession, entity_type: str, entity_id: int, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        query = select(self.model).where(
            self.model.entity_type == entity_type,
            self.model.entity_id == entity_id
        ).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_company(self, db: AsyncSession, company_id: int, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        from app.models.user import User
        query = (
            select(self.model)
            .join(User, self.model.actor_id == User.id)
            .where(User.company_id == company_id)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())


audit_log_repository = AuditLogRepository()