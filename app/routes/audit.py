from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database.postgres import get_db
from app.core.dependencies.dependencies import require_superadmin, require_admin, verify_tenant_access, get_current_user
from app.models.user import User, UserRole
from app.schemas.audit import AuditLogResponse
from app.repositories.audit_repository import audit_log_repository

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("/all", response_model=List[AuditLogResponse], dependencies=[require_superadmin()])
async def get_all_audit_logs(
    actor_id: Optional[int] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """
    Superadmin endpoint to search/list all audit logs globally across the platform.
    """
    query = select(audit_log_repository.model)
    
    if actor_id is not None:
        query = query.where(audit_log_repository.model.actor_id == actor_id)
    if entity_type is not None:
        query = query.where(audit_log_repository.model.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(audit_log_repository.model.entity_id == entity_id)

    query = query.order_by(audit_log_repository.model.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/company/{company_id}", response_model=List[AuditLogResponse])
async def get_company_audit_logs(
    company_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves audit logs for a company. Restricted to Company Admin and HR of the company, or Superadmin.
    """
    # Verify the user has access to this tenant (Superadmin bypasses this check)
    await verify_tenant_access(company_id, current_user=current_user)

    if current_user.role not in {UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.HR}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Only Admin, HR, or Superadmin can access company audit logs."
        )

    return await audit_log_repository.get_by_company(db, company_id=company_id, skip=skip, limit=limit)
