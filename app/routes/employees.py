from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.postgres import get_db
from app.core.dependencies.dependencies import require_admin, require_employee, verify_tenant_access, get_current_user
from app.models.user import User, UserRole
from app.schemas.employee import EmployeeCreate, EmployeeRegister, EmployeeUpdate, EmployeeResponse
from app.services.employee_service import employee_service
from app.repositories.employee_repository import employee_repository
from app.services.subscription_service import subscription_service

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
    await subscription_service.ensure_employee_capacity(db, company_id, increment=1)

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
    await subscription_service.ensure_mutation_allowed(db, company_id)

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
    await subscription_service.ensure_mutation_allowed(db, current_user.company_id)

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
    if current_user.role == UserRole.EMPLOYEE:
        # Prevent employees from reading admin-only notes
        employee.notes = None
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
        obj_in.department_id = None
        obj_in.notes = None

    employee = await employee_repository.get(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    await verify_tenant_access(employee.company_id, current_user=current_user)
    updated = await employee_repository.update(db, db_obj=employee, obj_in=obj_in)
    
    # Strip notes from response if the requester is an employee
    if current_user.role == UserRole.EMPLOYEE:
        updated.notes = None
    return updated


@router.post(
    "/{employee_id}/upload-letters",
    response_model=EmployeeResponse,
    dependencies=[require_admin()],
)
async def upload_offer_joining_letters(
    employee_id: int,
    offer_letter: UploadFile = File(..., description="Offer Letter PDF"),
    joining_letter: UploadFile = File(..., description="Joining Letter PDF"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Admin/HR uploads the company-specific Offer Letter and Joining Letter
    for a particular employee. Both files are required.
    """
    employee = await employee_repository.get(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    await verify_tenant_access(employee.company_id, current_user=current_user)

    from app.core.security.storage import storage_service

    folder = f"employee_{employee_id}/letters"
    offer_url = await storage_service.upload_file(offer_letter, folder=folder)
    joining_url = await storage_service.upload_file(joining_letter, folder=folder)

    employee.offer_letter_url = offer_url
    employee.joining_letter_url = joining_url
    db.add(employee)
    await db.commit()
    await db.refresh(employee)

    from app.services.audit_service import audit_log_service
    await audit_log_service.log_action(
        db=db,
        actor_id=current_user.id,
        action="UPLOAD_OFFER_JOINING_LETTERS",
        entity_type="Employee",
        entity_id=employee_id,
        new_value={"offer_letter_url": offer_url, "joining_letter_url": joining_url},
    )

    return employee


@router.post(
    "/{employee_id}/send-letters",
    dependencies=[require_admin()],
)
async def send_offer_joining_letters(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Admin/HR triggers sending the uploaded Offer and Joining Letters to the
    employee's email. Requires that both letters have been uploaded and all
    employee documents are verified.
    """
    employee = await employee_repository.get(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    await verify_tenant_access(employee.company_id, current_user=current_user)

    if not employee.offer_letter_url or not employee.joining_letter_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offer Letter and Joining Letter must be uploaded before sending.",
        )

    if employee.letters_sent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Letters have already been sent to this employee.",
        )

    # Verify all documents are verified
    from app.repositories.document_repository import document_repository
    from app.models.document import VerificationStatus
    all_docs = await document_repository.get_by_employee(db, employee_id)
    if not all_docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee has no uploaded documents. All documents must be verified before sending letters.",
        )
    unverified = [d for d in all_docs if d.verification_status != VerificationStatus.VERIFIED]
    if unverified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{len(unverified)} document(s) are not yet verified. All documents must be verified before sending letters.",
        )

    # Send the email
    from app.services.notification_service import notification_service
    await notification_service.send_offer_and_joining_letters(
        email=employee.email,
        first_name=employee.first_name,
    )

    employee.letters_sent = True
    db.add(employee)
    await db.commit()

    from app.services.audit_service import audit_log_service
    await audit_log_service.log_action(
        db=db,
        actor_id=current_user.id,
        action="SEND_OFFER_JOINING_LETTERS",
        entity_type="Employee",
        entity_id=employee_id,
    )

    return {"detail": f"Offer and Joining Letters sent successfully to {employee.email}."}