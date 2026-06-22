from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.base_repository import BaseRepository
from app.models.company import Company


class CompanyRepository(BaseRepository[Company]):
    def __init__(self):
        super().__init__(Company)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[Company]:
        query = select(self.model).where(self.model.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_employee_count(self, db: AsyncSession, company_id: int, count_change: int) -> Optional[Company]:
        company = await self.get(db, company_id)
        if company:
            company.current_employee_count = max(0, company.current_employee_count + count_change)
            db.add(company)
            await db.commit()
            await db.refresh(company)
        return company


company_repository = CompanyRepository()