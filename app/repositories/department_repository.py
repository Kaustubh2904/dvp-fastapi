from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.base_repository import BaseRepository
from app.models.department import Department


class DepartmentRepository(BaseRepository[Department]):
    def __init__(self):
        super().__init__(Department)

    async def get_by_company(self, db: AsyncSession, company_id: int, skip: int = 0, limit: int = 100) -> list[Department]:
        query = select(self.model).where(self.model.company_id == company_id).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())


department_repository = DepartmentRepository()