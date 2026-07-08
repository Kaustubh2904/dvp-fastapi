from typing import Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.storage import storage_service
from app.repositories.document_repository import document_repository
from app.models.document import Document, DocumentType, VerificationStatus
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.services.audit_service import audit_log_service
from app.services.subscription_service import subscription_service


class DocumentService:
    @staticmethod
    async def upload_document(
        db: AsyncSession,
        employee_id: int,
        document_type: DocumentType,
        file: UploadFile,
        actor_id: Optional[int] = None,
    ) -> Document:
        from app.repositories.employee_repository import employee_repository
        emp = await employee_repository.get(db, employee_id)
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        await subscription_service.ensure_mutation_allowed(db, emp.company_id)
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        await subscription_service.ensure_document_upload_capacity(db, emp.company_id, storage_bytes=file_size)
        query = select(Document).where(
            and_(Document.employee_id == employee_id, Document.document_type == document_type)
        )
        result = await db.execute(query)
        existing_doc = result.scalar_one_or_none()

        folder = f"employee_{employee_id}"
        file_url = await storage_service.upload_file(file, folder=folder)

        if existing_doc:
            old_url = existing_doc.file_url
            try:
                await storage_service.delete_file(old_url)
            except Exception:
                pass

            existing_doc.file_name = file.filename
            existing_doc.file_url = file_url
            existing_doc.verification_status = VerificationStatus.PENDING
            existing_doc.remarks = "Re-uploaded document replacement."
            db.add(existing_doc)
            await db.commit()
            await db.refresh(existing_doc)

            doc = existing_doc
            action_type = "REPLACE_DOCUMENT"
        else:
            doc_in = DocumentCreate(
                employee_id=employee_id,
                document_type=document_type,
                file_name=file.filename,
                file_url=file_url,
            )
            doc = await document_repository.create(db, obj_in=doc_in)
            action_type = "UPLOAD_DOCUMENT"

        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id,
            action=action_type,
            entity_type="Document",
            entity_id=doc.id,
            new_value={"type": document_type.value, "file_name": file.filename},
        )

        await subscription_service.increment_monthly_uploads(db, emp.company_id, storage_bytes=file_size)

        return doc

    @staticmethod
    async def verify_document(
        db: AsyncSession, document_id: int, remarks: Optional[str] = None, actor_id: Optional[int] = None
    ) -> Document:
        doc = await document_repository.get(db, document_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        from app.repositories.employee_repository import employee_repository
        emp = await employee_repository.get(db, doc.employee_id)
        if emp:
            await subscription_service.ensure_mutation_allowed(db, emp.company_id)

        old_val = {"status": doc.verification_status.value}

        doc.verification_status = VerificationStatus.VERIFIED
        doc.remarks = remarks or "Verified successfully."
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id,
            action="VERIFY_DOCUMENT",
            entity_type="Document",
            entity_id=document_id,
            old_value=old_val,
            new_value={"status": VerificationStatus.VERIFIED.value, "remarks": doc.remarks},
        )
        return doc

    @staticmethod
    async def reject_document(
        db: AsyncSession, document_id: int, remarks: str, actor_id: Optional[int] = None
    ) -> Document:
        if not remarks or not remarks.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remarks are required when rejecting a document.",
            )

        doc = await document_repository.get(db, document_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        from app.repositories.employee_repository import employee_repository
        emp = await employee_repository.get(db, doc.employee_id)
        if emp:
            await subscription_service.ensure_mutation_allowed(db, emp.company_id)

        old_val = {"status": doc.verification_status.value}

        doc.verification_status = VerificationStatus.REJECTED
        doc.remarks = remarks
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id,
            action="REJECT_DOCUMENT",
            entity_type="Document",
            entity_id=document_id,
            old_value=old_val,
            new_value={"status": VerificationStatus.REJECTED.value, "remarks": remarks},
        )
        return doc

    @staticmethod
    async def fetch_from_digilocker(
        db: AsyncSession, employee_id: int, document_type: DocumentType, actor_id: Optional[int] = None
    ) -> Document:
        from app.repositories.employee_repository import employee_repository
        emp = await employee_repository.get(db, employee_id)
        if emp:
            await subscription_service.ensure_mutation_allowed(db, emp.company_id)
            await subscription_service.ensure_document_upload_capacity(db, emp.company_id, storage_bytes=0)
        mock_file_name = f"digilocker_{document_type.value.lower()}.pdf"
        mock_file_url = f"/static/uploads/employee_{employee_id}/{mock_file_name}"

        doc_in = DocumentCreate(
            employee_id=employee_id,
            document_type=document_type,
            file_name=mock_file_name,
            file_url=mock_file_url,
        )

        doc = await document_repository.create(db, obj_in=doc_in)
        doc.verification_status = VerificationStatus.VERIFIED
        doc.remarks = "Automatically fetched and verified via DigiLocker Sandbox Mock."
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id,
            action="FETCH_DIGILOCKER",
            entity_type="Document",
            entity_id=doc.id,
            new_value={"type": document_type.value, "source": "DigiLocker Mock"},
        )

        return doc


document_service = DocumentService()