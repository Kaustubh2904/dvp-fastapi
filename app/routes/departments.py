from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.postgres import get_db
from app.core.dependencies.dependencies import require_admin, verify_tenant_access, get_current_user, require_employee
from app.models.user import User, UserRole
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from app.services.department_service import department_service
from app.repositories.department_repository import department_repository
from app.repositories.employee_repository import employee_repository

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED, dependencies=[require_admin()])
async def create_department(
    obj_in: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await verify_tenant_access(obj_in.company_id, current_user=current_user)
    return await department_service.create_department(db, obj_in=obj_in, actor_id=current_user.id)


@router.get("/company/{company_id}", response_model=list[DepartmentResponse])
async def list_company_departments(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await verify_tenant_access(company_id, current_user=current_user)
    return await department_repository.get_by_company(db, company_id=company_id)


@router.get("/{department_id}", response_model=DepartmentResponse, dependencies=[require_employee()])
async def get_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dept = await department_repository.get(db, department_id)
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    await verify_tenant_access(dept.company_id, current_user=current_user)
    return dept


@router.put("/{department_id}", response_model=DepartmentResponse, dependencies=[require_admin()])
async def update_department(
    department_id: int,
    obj_in: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dept = await department_repository.get(db, department_id)
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    await verify_tenant_access(dept.company_id, current_user=current_user)
    return await department_service.update_department(
        db, department_id=department_id, obj_in=obj_in, actor_id=current_user.id
    )


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[require_admin()])
async def delete_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dept = await department_repository.get(db, department_id)
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    await verify_tenant_access(dept.company_id, current_user=current_user)
    await department_service.delete_department(db, department_id=department_id, actor_id=current_user.id)
    return None


@router.post("/{department_id}/employees/{employee_id}", response_model=DepartmentResponse, dependencies=[require_admin()])
async def assign_employee_to_department(
    department_id: int,
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign an employee to a specific department."""
    dept = await department_repository.get(db, department_id)
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    await verify_tenant_access(dept.company_id, current_user=current_user)

    employee = await employee_repository.get(db, employee_id)
    if not employee or employee.company_id != dept.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Employee not found or does not belong to this company"
        )

    await employee_repository.update(db, db_obj=employee, obj_in={"department_id": department_id})
    return dept


@router.delete("/{department_id}/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[require_admin()])
async def remove_employee_from_department(
    department_id: int,
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an employee from a specific department."""
    dept = await department_repository.get(db, department_id)
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    await verify_tenant_access(dept.company_id, current_user=current_user)

    employee = await employee_repository.get(db, employee_id)
    if not employee or employee.company_id != dept.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Employee not found or does not belong to this company"
        )
        
    if employee.department_id != department_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee does not belong to this department"
        )

    await employee_repository.update(db, db_obj=employee, obj_in={"department_id": None})
    return None