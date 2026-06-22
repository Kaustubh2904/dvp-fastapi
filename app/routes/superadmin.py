from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database.postgres import get_db
from app.core.dependencies.dependencies import require_superadmin, get_current_user
from app.models.user import User, UserRole
from app.schemas.auth import UserResponse, UserCreate, UserUpdate
from app.repositories.user_repository import user_repository
from app.core.security.security import hash_password

router = APIRouter(prefix="/superadmin", tags=["Super Admin"], dependencies=[require_superadmin()])


@router.get("/users", response_model=list[UserResponse])
async def list_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: AsyncSession = Depends(get_db),
):
    return await user_repository.get_multi(db, skip=skip, limit=limit)


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    obj_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await user_repository.get_by_email(db, obj_in.email)
    if existing:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=obj_in.email,
        password_hash=hash_password(obj_in.password),
        role=obj_in.role,
        company_id=obj_in.company_id,
        is_active=obj_in.is_active,
        is_verified=obj_in.is_verified,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    obj_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    user = await user_repository.get(db, user_id)
    if not user:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updated = await user_repository.update(db, db_obj=user, obj_in=obj_in)
    return updated


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await user_repository.get(db, user_id)
    if not user:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await user_repository.remove(db, id=user_id)
    return None