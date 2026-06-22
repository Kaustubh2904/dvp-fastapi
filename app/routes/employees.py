from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.postgres import get_db
from app.core.dependencies.dependencies import require_admin, require_employee, verify_tenant_access, get_current_user
from app.models.user import User, UserRole
from app.schemas.employee import EmployeeCreate, EmployeeRegister, EmployeeUpdate, EmployeeResponse
from app.services.employee_service import employee_service
from app.repositories.employee_repository import employee_repository

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED, dependencies=[require_admin()])
async def create_employee(
    obj_in: EmployeeCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = current_user.company_id
    if current_user.role == UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SUPERADMIN must create employees via tenant-specific configurations or pass company_id (not allowed in generic manual creation).",
        )

    return await employee_service.create_employee(
        db, company_id=company_id, obj_in=obj_in, actor_id=current_user.id, background_tasks=background_tasks
    )


@router.post("/bulk-upload", status_code=status.HTTP_200_OK, dependencies=[require_admin()])
async def bulk_upload_employees(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = current_user.company_id
    if not company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Global Admins/Superadmins cannot directly bulk upload employees without a tenant scope.",
        )

    file_content = await file.read()
    result = await employee_service.bulk_upload_employees(
        db,
        company_id=company_id,
        file_content=file_content,
        filename=file.filename,
        actor_id=current_user.id,
        background_tasks=background_tasks,
    )
    return result


@router.post("/register", response_model=EmployeeResponse, dependencies=[require_employee()])
async def register_employee_profile(
    obj_in: EmployeeRegister,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Employee role users can complete registration for themselves.",
        )

    return await employee_service.register_employee(db, employee_id=current_user.id, obj_in=obj_in)


@router.get("/{employee_id}", response_model=EmployeeResponse, dependencies=[require_employee()])
async def get_employee_details(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.EMPLOYEE and current_user.id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You can only view your own profile.",
        )

    employee = await employee_repository.get(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    await verify_tenant_access(employee.company_id, current_user=current_user)
    return employee


@router.put("/{employee_id}", response_model=EmployeeResponse, dependencies=[require_employee()])
async def update_employee_profile(
    employee_id: int,
    obj_in: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.EMPLOYEE:
        if current_user.id != employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: You can only update your own profile.",
            )
        obj_in.status = None

    employee = await employee_repository.get(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    await verify_tenant_access(employee.company_id, current_user=current_user)
    return await employee_repository.update(db, db_obj=employee, obj_in=obj_in)