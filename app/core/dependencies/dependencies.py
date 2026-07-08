from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database.postgres import get_db
from app.core.security.security import decode_token
from app.models.user import User, UserRole

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise credentials_exception

    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    token_type = payload.get("type")

    if not user_id or token_type != "access":
        raise credentials_exception

    query = select(User).where(User.id == int(user_id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account"
        )

    return user


class RoleChecker:
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user


# Helper factory dependencies
def require_role(roles: list[UserRole]):
    return Depends(RoleChecker(roles))


# Specific role dependencies for convenience
def require_superadmin():
    return Depends(RoleChecker([UserRole.SUPERADMIN]))


def require_portal_access():
    return Depends(RoleChecker([UserRole.SUPERADMIN, UserRole.MARKETING, UserRole.TECHNICAL_TEAM]))


def require_subscription_portal_access():
    return Depends(RoleChecker([UserRole.SUPERADMIN, UserRole.MARKETING]))


def require_subscription_admin():
    return Depends(RoleChecker([UserRole.SUPERADMIN]))


def require_ticket_portal_access():
    return Depends(RoleChecker([UserRole.SUPERADMIN, UserRole.TECHNICAL_TEAM]))


def require_admin():
    return Depends(RoleChecker([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.HR]))


def require_employee():
    return Depends(RoleChecker([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.EMPLOYEE]))


async def verify_tenant_access(
    company_id: int,
    current_user: User = Depends(get_current_user),
) -> int:
    """
    Enforces tenant isolation by verifying that the user belongs to the requested company_id
    unless they are a SUPERADMIN.
    """
    if current_user.role == UserRole.SUPERADMIN:
        return company_id

    if current_user.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not belong to this tenant/company",
        )

    return company_id