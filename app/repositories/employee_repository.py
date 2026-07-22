from datetime import datetime
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


    async def update_digilocker_credentials(
        self,
        db: AsyncSession,
        employee_id: int,
        *,
        digilocker_id: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expiry: Optional[datetime] = None,
        status: Optional[str] = None,
        linked_at: Optional[datetime] = None,
    ) -> Optional[Employee]:
        """Update DigiLocker credential fields for an employee."""
        employee = await self.get(db, employee_id)
        if not employee:
            return None
        if digilocker_id is not None:
            employee.digilocker_id = digilocker_id
        if access_token is not None:
            employee.digilocker_access_token = access_token
        if refresh_token is not None:
            employee.digilocker_refresh_token = refresh_token
        if token_expiry is not None:
            employee.digilocker_token_expiry = token_expiry
        if status is not None:
            employee.digilocker_status = status
        if linked_at is not None:
            employee.digilocker_linked_at = linked_at
        db.add(employee)
        await db.commit()
        await db.refresh(employee)
        return employee

    async def clear_digilocker_credentials(self, db: AsyncSession, employee_id: int) -> Optional[Employee]:
        """Clear all DigiLocker fields for an employee (unlink)."""
        employee = await self.get(db, employee_id)
        if not employee:
            return None
        employee.digilocker_id = None
        employee.digilocker_access_token = None
        employee.digilocker_refresh_token = None
        employee.digilocker_token_expiry = None
        employee.digilocker_status = None
        employee.digilocker_linked_at = None
        db.add(employee)
        await db.commit()
        await db.refresh(employee)
        return employee

    async def get_digilocker_status(self, db: AsyncSession, employee_id: int) -> Optional[dict]:
        """Return only DigiLocker-related fields for an employee."""
        employee = await self.get(db, employee_id)
        if not employee:
            return None
        return {
            "digilocker_id": employee.digilocker_id,
            "digilocker_status": employee.digilocker_status,
            "digilocker_linked_at": employee.digilocker_linked_at,
            "digilocker_token_expiry": employee.digilocker_token_expiry,
        }


employee_repository = EmployeeRepository()