from datetime import datetime, timedelta, timezone
import random
import secrets
from typing import Optional
from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import settings
from app.core.security.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.database.redis import redis_set, redis_get, redis_delete
from app.repositories.user_repository import user_repository, otp_repository, password_reset_token_repository
from app.models.user import User, UserRole
from app.models.otp import OTPRecord
from app.models.password_reset import PasswordResetToken
from app.schemas.auth import Token, ResetPasswordRequest
from app.services.audit_service import audit_log_service
from app.services.notification_service import notification_service


class AuthService:
    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> User:
        user = await user_repository.get_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
            )
        return user

    @staticmethod
    async def generate_tokens(user: User) -> Token:
        access_payload = {"role": user.role.value, "company_id": user.company_id}
        access = create_access_token(user.id, additional_data=access_payload)
        refresh = create_refresh_token(user.id)
        return Token(access_token=access, refresh_token=refresh)

    @staticmethod
    async def refresh_tokens(db: AsyncSession, refresh_token: str) -> Token:
        payload = decode_token(refresh_token)
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user = await user_repository.get(db, int(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or deactivated",
            )

        return await AuthService.generate_tokens(user)

    @staticmethod
    async def register_saas_company(db: AsyncSession, obj_in: "CompanyRegistrationRequest") -> Token:
        from app.schemas.auth import CompanyRegistrationRequest
        from app.models.company import Company, BillingStatus
        from app.schemas.company import CompanyCreate
        from app.repositories.company_repository import company_repository
        from app.services.subscription_service import subscription_service
        
        # Check if email is used
        user = await user_repository.get_by_email(db, obj_in.email)
        if user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered",
            )
            
        plan = obj_in.plan_name.upper()
        if plan not in {"FREE", "BASIC", "PRO", "PREMIUM", "CUSTOM"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid plan name. Choose FREE, BASIC, PRO, PREMIUM, or CUSTOM.",
            )
            
        # 1. Create Company
        company_in = CompanyCreate(
            company_name=obj_in.company_name,
            email=obj_in.company_email,
            phone=obj_in.phone,
            subscription_plan=plan,
            employee_limit=10,
            billing_status=BillingStatus.PENDING_APPROVAL,
            is_active=True
        )
        # Using the repository will add it to the session and flush
        company = await company_repository.create(db, obj_in=company_in)
        
        # 2. Create Admin User
        admin_user = User(
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            email=obj_in.email,
            password_hash=hash_password(obj_in.password),
            role=UserRole.ADMIN,
            company_id=company.id,
            is_active=True,
            is_verified=True
        )
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)

        await subscription_service.initialize_company_subscription(
            db=db,
            company=company,
            admin_user=admin_user,
            plan_code=plan,
            actor_id=admin_user.id,
        )
        
        # Log audit
        await audit_log_service.log_action(
            db=db,
            actor_id=admin_user.id,
            action="COMPANY_SAAS_REGISTRATION",
            entity_type="Company",
            entity_id=company.id,
        )
        
        # Return login tokens
        return await AuthService.generate_tokens(admin_user)

    @staticmethod
    async def generate_otp(db: AsyncSession, email: str, background_tasks: Optional[BackgroundTasks] = None) -> str:
        code = f"{random.randint(100000, 999999)}"
        expires_delta = timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
        expires_at = datetime.now(timezone.utc) + expires_delta

        # Save to Database for audit/fallback
        otp_rec = OTPRecord(email=email, code=code, expires_at=expires_at)
        await otp_repository.create(db, obj_in=otp_rec)

        # Try saving to Redis
        redis_key = f"otp:{email}"
        await redis_set(redis_key, code, int(expires_delta.total_seconds()))

        # Trigger notification
        from app.tasks.queue import enqueue_task
        from app.tasks.worker import send_otp_email_job
        if background_tasks:
            await enqueue_task(background_tasks, send_otp_email_job, email=email, code=code)
        else:
            await notification_service.send_otp_email(email, code)

        return code

    @staticmethod
    async def verify_otp(db: AsyncSession, email: str, code: str) -> bool:
        # Try checking Redis
        cached_code = await redis_get(f"otp:{email}")

        if cached_code:
            if cached_code == code:
                await redis_delete(f"otp:{email}")
                # Mark as used in PostgreSQL
                db_otp = await otp_repository.get_active_otp(db, email)
                if db_otp:
                    db_otp.used = True
                    await db.commit()
                return True
            else:
                return False

        # Fallback: Check PostgreSQL database directly
        db_otp = await otp_repository.get_active_otp(db, email)
        if not db_otp:
            return False

        db_otp.attempts += 1
        await db.commit()

        if db_otp.attempts > settings.OTP_ATTEMPT_LIMIT:
            db_otp.used = True
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP limit exceeded. Please request a new code.",
            )

        if db_otp.code == code:
            db_otp.used = True
            await db.commit()
            return True

        return False

    @staticmethod
    async def forgot_password(db: AsyncSession, email: str, background_tasks: Optional[BackgroundTasks] = None) -> str:
        user = await user_repository.get_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with this email does not exist",
            )

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)

        reset_rec = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
        await password_reset_token_repository.create(db, obj_in=reset_rec)

        # Dispatch notification email
        from app.tasks.queue import enqueue_task
        from app.tasks.worker import send_reset_password_email_job
        if background_tasks:
            await enqueue_task(background_tasks, send_reset_password_email_job, email=email, token=token)
        else:
            await notification_service.send_reset_password_email(email, token)
        return token

    @staticmethod
    async def reset_password(db: AsyncSession, obj_in: ResetPasswordRequest) -> bool:
        reset_token = await password_reset_token_repository.get_active_token(db, obj_in.token)
        if not reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        user = await user_repository.get(db, reset_token.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user.password_hash = hash_password(obj_in.new_password)
        reset_token.used = True

        db.add(user)
        db.add(reset_token)
        await db.commit()

        await audit_log_service.log_action(
            db=db,
            actor_id=user.id,
            action="RESET_PASSWORD",
            entity_type="User",
            entity_id=user.id,
        )
        return True


auth_service = AuthService()