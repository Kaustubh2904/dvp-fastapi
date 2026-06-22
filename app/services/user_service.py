from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.user_repository import user_repository


class UserService:
    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        return await user_repository.get(db, user_id)

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        return await user_repository.get_by_email(db, email)

    @staticmethod
    async def deactivate_user(db: AsyncSession, user_id: int) -> Optional[User]:
        user = await user_repository.get(db, user_id)
        if user:
            user.is_active = False
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user


user_service = UserService()