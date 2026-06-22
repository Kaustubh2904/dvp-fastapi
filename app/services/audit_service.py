from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_repository import audit_log_repository
from app.schemas.common import MessageResponse


class AuditLogService:
    @staticmethod
    async def log_action(
        db: AsyncSession,
        actor_id: Optional[int],
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        old_value: Optional[dict[str, Any]] = None,
        new_value: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ):
        from pydantic import BaseModel

        class AuditLogCreate(BaseModel):
            actor_id: Optional[int] = None
            action: str
            entity_type: str
            entity_id: Optional[int] = None
            old_value: Optional[dict[str, Any]] = None
            new_value: Optional[dict[str, Any]] = None
            ip_address: Optional[str] = None

        audit_data = AuditLogCreate(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
        )
        return await audit_log_repository.create(db, obj_in=audit_data)


audit_log_service = AuditLogService()