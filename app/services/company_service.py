from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.repositories.company_repository import company_repository
from app.models.company import Company, BillingStatus
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyStatistics
from app.services.audit_service import audit_log_service


class CompanyService:
    @staticmethod
    async def create_company(db: AsyncSession, obj_in: CompanyCreate, actor_id: Optional[int] = None) -> Company:
        existing = await company_repository.get_by_email(db, obj_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company with this email already exists",
            )

        company = await company_repository.create(db, obj_in=obj_in)

        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id,
            action="CREATE_COMPANY",
            entity_type="Company",
            entity_id=company.id,
            new_value=obj_in.model_dump(mode="json"),
        )
        return company

    @staticmethod
    async def update_company(
        db: AsyncSession, company_id: int, obj_in: CompanyUpdate, actor_id: Optional[int] = None
    ) -> Company:
        company = await company_repository.get(db, company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found",
            )

        old_val = {
            "company_name": company.company_name,
            "billing_status": company.billing_status.value if company.billing_status else None,
            "is_active": company.is_active,
            "employee_limit": company.employee_limit,
        }

        updated_company = await company_repository.update(db, db_obj=company, obj_in=obj_in)

        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id,
            action="UPDATE_COMPANY",
            entity_type="Company",
            entity_id=company_id,
            old_value=old_val,
            new_value=obj_in.model_dump(exclude_unset=True, mode="json"),
        )
        return updated_company

    @staticmethod
    async def get_company_statistics(db: AsyncSession, company_id: int) -> CompanyStatistics:
        company = await company_repository.get(db, company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found",
            )

        from app.models.department import Department
        dept_query = select(func.count(Department.id)).where(Department.company_id == company_id)
        dept_result = await db.execute(dept_query)
        total_departments = dept_result.scalar() or 0

        remaining_slots = max(0, company.employee_limit - company.current_employee_count)

        return CompanyStatistics(
            company_id=company.id,
            company_name=company.company_name,
            employee_limit=company.employee_limit,
            current_employee_count=company.current_employee_count,
            remaining_slots=remaining_slots,
            total_departments=total_departments,
            billing_status=company.billing_status,
            is_active=company.is_active,
        )


company_service = CompanyService()