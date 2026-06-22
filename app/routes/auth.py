from fastapi import APIRouter, Depends, status, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.postgres import get_db
from app.core.dependencies.dependencies import get_current_user, require_employee
from app.schemas.auth import (
    LoginRequest, Token, TokenRefreshRequest, OTPGenerateRequest, OTPLoginRequest,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest, UserResponse
)
from app.services.auth_service import auth_service
from app.repositories.user_repository import user_repository
from app.models.user import User
from app.core.security.security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(obj_in: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate(db, email=obj_in.email, password=obj_in.password)
    return await auth_service.generate_tokens(user)


@router.post("/refresh", response_model=Token)
async def refresh_token(obj_in: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.refresh_tokens(db, refresh_token=obj_in.refresh_token)


@router.post("/otp/generate", status_code=status.HTTP_200_OK)
async def generate_otp(
    obj_in: OTPGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    user = await user_repository.get_by_email(db, obj_in.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email is not registered"
        )

    await auth_service.generate_otp(db, email=obj_in.email, background_tasks=background_tasks)
    return {"message": "OTP generated and sent to email."}


@router.post("/otp/login", response_model=Token)
async def otp_login(obj_in: OTPLoginRequest, db: AsyncSession = Depends(get_db)):
    user = await user_repository.get_by_email(db, obj_in.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email is not registered"
        )

    is_valid = await auth_service.verify_otp(db, email=obj_in.email, code=obj_in.code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP"
        )

    return await auth_service.generate_tokens(user)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    obj_in: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    await auth_service.forgot_password(db, email=obj_in.email, background_tasks=background_tasks)
    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(obj_in: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.reset_password(db, obj_in=obj_in)
    return {"message": "Password reset completed successfully."}


@router.post("/change-password", status_code=status.HTTP_200_OK, dependencies=[require_employee()])
async def change_password(
    obj_in: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(obj_in.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password"
        )

    current_user.password_hash = hash_password(obj_in.new_password)
    db.add(current_user)
    await db.commit()
    return {"message": "Password changed successfully."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user