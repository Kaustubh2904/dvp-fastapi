from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.base_repository import BaseRepository
from app.models.employee import Employee


class EmployeeRepository(BaseRepository[Employee]):
    def __init__(self):
        super().__init__(Employee)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[Employee]:
        query = select(self.model).where(self.model.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_company(self, db: AsyncSession, company_id: int, skip: int = 0, limit: int = 100) -> list[Employee]:
        query = select(self.model).where(self.model.company_id == company_id).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())


employee_repository = EmployeeRepository()