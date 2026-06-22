from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database.postgres import get_db
from app.core.dependencies.dependencies import require_superadmin, require_admin, verify_tenant_access, get_current_user
from app.models.user import User, UserRole
from app.models.employee import Employee
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse, CompanyStatistics
from app.services.company_service import company_service
from app.repositories.company_repository import company_repository

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.post("", response_model=CompanyResponse, dependencies=[require_superadmin()])
async def create_company(
    obj_in: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await company_service.create_company(db, obj_in=obj_in, actor_id=current_user.id)


@router.get("", response_model=list[CompanyResponse], dependencies=[require_superadmin()])
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: AsyncSession = Depends(get_db),
):
    return await company_repository.get_multi(db, skip=skip, limit=limit)


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int = Depends(verify_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    company = await company_repository.get(db, company_id)
    return company


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    obj_in: CompanyUpdate,
    company_id: int = Depends(verify_tenant_access),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.ADMIN:
        obj_in.subscription_plan = None
        obj_in.employee_limit = None
        obj_in.billing_status = None
        obj_in.is_active = None

    return await company_service.update_company(db, company_id=company_id, obj_in=obj_in, actor_id=current_user.id)


@router.get("/{company_id}/statistics", response_model=CompanyStatistics, dependencies=[require_admin()])
async def get_company_statistics(
    company_id: int = Depends(verify_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.get_company_statistics(db, company_id=company_id)


@router.get("/{company_id}/employees", dependencies=[require_admin()])
async def list_company_employees(
    company_id: int = Depends(verify_tenant_access),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: AsyncSession = Depends(get_db),
):
    query = select(Employee).where(Employee.company_id == company_id).offset(skip).limit(limit)
    result = await db.execute(query)
    employees = result.scalars().all()

    return [
        {
            "id": emp.id,
            "employee_code": emp.employee_code,
            "first_name": emp.first_name,
            "last_name": emp.last_name,
            "email": emp.email,
            "phone": emp.phone,
            "gender": emp.gender,
            "status": emp.status.value,
            "registration_completed": emp.registration_completed,
            "joining_date": emp.joining_date,
            "department_id": emp.department_id,
        }
        for emp in employees
    ]