from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.base_repository import BaseRepository
from app.models.user import User, UserRole
from app.models.otp import OTPRecord
from app.models.password_reset import PasswordResetToken


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        query = select(self.model).where(self.model.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()


class OTPRepository(BaseRepository[OTPRecord]):
    def __init__(self):
        super().__init__(OTPRecord)

    async def get_active_otp(self, db: AsyncSession, email: str) -> Optional[OTPRecord]:
        from datetime import datetime, timezone
        from sqlalchemy import and_
        now = datetime.now(timezone.utc)
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.email == email,
                    self.model.used == False,
                    self.model.expires_at > now,
                )
            )
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    def __init__(self):
        super().__init__(PasswordResetToken)

    async def get_active_token(self, db: AsyncSession, token: str) -> Optional[PasswordResetToken]:
        from datetime import datetime, timezone
        from sqlalchemy import and_
        now = datetime.now(timezone.utc)
        query = select(self.model).where(
            and_(
                self.model.token == token,
                self.model.used == False,
                self.model.expires_at > now,
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()


user_repository = UserRepository()
otp_repository = OTPRepository()
password_reset_token_repository = PasswordResetTokenRepository()