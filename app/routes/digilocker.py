import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.postgres import get_db
from app.core.dependencies.dependencies import get_current_user, require_employee
from app.core.exceptions import BadRequestException, ForbiddenException
from app.models.user import User, UserRole
from app.schemas.digilocker import (
    DigiLockerAuthorizeResponse,
    DigiLockerDocumentsResponse,
    DigiLockerStatusResponse,
    DigiLockerTokenRefreshResponse,
    DigiLockerUnlinkResponse,
)
from app.services.digilocker_service import digilocker_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/digilocker", tags=["DigiLocker"])


def _require_employee_role(current_user: User) -> None:
    """Ensure the current user is an EMPLOYEE role user."""
    if current_user.role != UserRole.EMPLOYEE:
        raise ForbiddenException(detail="Only Employee users can access DigiLocker integration.")


@router.get("/authorize", response_model=DigiLockerAuthorizeResponse, dependencies=[require_employee()])
async def authorize(
    current_user: User = Depends(get_current_user),
):
    """Generate the DigiLocker OAuth 2.0 authorization URL for the current employee."""
    _require_employee_role(current_user)
    result = await digilocker_service.generate_authorization_url(employee_id=current_user.id)
    return result


@router.get("/callback")
async def callback(
    code: str = Query(..., description="Authorization code from DigiLocker"),
    state: str = Query(..., description="OAuth state parameter for CSRF protection"),
    db: AsyncSession = Depends(get_db),
):
    """Handle the OAuth callback from DigiLocker after user authorization."""
    result = await digilocker_service.handle_callback(db=db, code=code, state=state)
    return result


@router.get("/status", response_model=DigiLockerStatusResponse, dependencies=[require_employee()])
async def get_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current DigiLocker link status for the authenticated employee."""
    _require_employee_role(current_user)
    return await digilocker_service.get_link_status(db=db, employee_id=current_user.id)


@router.get("/documents", response_model=DigiLockerDocumentsResponse, dependencies=[require_employee()])
async def fetch_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch the list of issued documents from the employee's linked DigiLocker account."""
    _require_employee_role(current_user)
    return await digilocker_service.fetch_documents(db=db, employee_id=current_user.id)


@router.post("/refresh-token", response_model=DigiLockerTokenRefreshResponse, dependencies=[require_employee()])
async def refresh_token(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Refresh the DigiLocker access token using the stored refresh token."""
    _require_employee_role(current_user)
    return await digilocker_service.refresh_token(db=db, employee_id=current_user.id)


@router.post("/unlink", response_model=DigiLockerUnlinkResponse, dependencies=[require_employee()])
async def unlink(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unlink the DigiLocker account from the employee's profile."""
    _require_employee_role(current_user)
    return await digilocker_service.unlink_account(
        db=db, employee_id=current_user.id, actor_id=current_user.id
    )
