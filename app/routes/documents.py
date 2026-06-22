from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database.postgres import get_db
from app.core.dependencies.dependencies import require_admin, require_employee, verify_tenant_access, get_current_user
from app.models.user import User, UserRole
from app.models.document import DocumentType, VerificationStatus
from app.schemas.document import DocumentResponse, DocumentUpdate
from app.services.document_service import document_service
from app.repositories.document_repository import document_repository
from app.repositories.employee_repository import employee_repository

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse, dependencies=[require_employee()])
async def upload_document(
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Employee users can upload documents to their profile.",
        )

    return await document_service.upload_document(
        db, employee_id=current_user.id, document_type=document_type, file=file, actor_id=current_user.id
    )


@router.post("/{document_id}/verify", response_model=DocumentResponse, dependencies=[require_admin()])
async def verify_document(
    document_id: int,
    remarks: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = await document_repository.get(db, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    emp = await employee_repository.get(db, doc.employee_id)
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked employee profile not found")

    await verify_tenant_access(emp.company_id, current_user=current_user)
    return await document_service.verify_document(db, document_id=document_id, remarks=remarks, actor_id=current_user.id)


@router.post("/{document_id}/reject", response_model=DocumentResponse, dependencies=[require_admin()])
async def reject_document(
    document_id: int,
    remarks: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = await document_repository.get(db, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    emp = await employee_repository.get(db, doc.employee_id)
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked employee profile not found")

    await verify_tenant_access(emp.company_id, current_user=current_user)
    return await document_service.reject_document(db, document_id=document_id, remarks=remarks, actor_id=current_user.id)


@router.post("/digilocker-fetch", response_model=DocumentResponse, dependencies=[require_employee()])
async def fetch_digilocker_document(
    document_type: DocumentType = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Employee users can link their DigiLocker.",
        )

    return await document_service.fetch_from_digilocker(
        db, employee_id=current_user.id, document_type=document_type, actor_id=current_user.id
    )


@router.get("/employee/{employee_id}", response_model=list[DocumentResponse], dependencies=[require_employee()])
async def list_employee_documents(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.EMPLOYEE and current_user.id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You can only view your own documents.",
        )

    emp = await employee_repository.get(db, employee_id)
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    await verify_tenant_access(emp.company_id, current_user=current_user)
    return await document_repository.get_by_employee(db, employee_id=employee_id)