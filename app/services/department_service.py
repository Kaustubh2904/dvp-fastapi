from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.repositories.department_repository import department_repository
from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.repositories.company_repository import company_repository
from app.services.audit_service import audit_log_service


class DepartmentService:
    @staticmethod
    async def create_department(
        db: AsyncSession, obj_in: DepartmentCreate, actor_id: Optional[int] = None
    ) -> Department:
        company = await company_repository.get(db, obj_in.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company/Tenant not found",
            )

        dept = await department_repository.create(db, obj_in=obj_in)

        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id,
            action="CREATE_DEPARTMENT",
            entity_type="Department",
            entity_id=dept.id,
            new_value=obj_in.model_dump(mode="json"),
        )
        return dept

    @staticmethod
    async def update_department(
        db: AsyncSession, department_id: int, obj_in: DepartmentUpdate, actor_id: Optional[int] = None
    ) -> Department:
        dept = await department_repository.get(db, department_id)
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found",
            )

        old_val = {"name": dept.name, "description": dept.description}
        updated_dept = await department_repository.update(db, db_obj=dept, obj_in=obj_in)

        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id,
            action="UPDATE_DEPARTMENT",
            entity_type="Department",
            entity_id=department_id,
            old_value=old_val,
            new_value=obj_in.model_dump(exclude_unset=True, mode="json"),
        )
        return updated_dept

    @staticmethod
    async def delete_department(
        db: AsyncSession, department_id: int, actor_id: Optional[int] = None
    ) -> Optional[Department]:
        dept = await department_repository.get(db, department_id)
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found",
            )

        deleted_dept = await department_repository.remove(db, id=department_id)
        if deleted_dept:
            await audit_log_service.log_action(
                db=db,
                actor_id=actor_id,
                action="DELETE_DEPARTMENT",
                entity_type="Department",
                entity_id=department_id,
                old_value={"name": deleted_dept.name, "company_id": deleted_dept.company_id},
            )
        return deleted_dept


department_service = DepartmentService()