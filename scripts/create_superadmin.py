"""
One-time script to create the initial superadmin user.
Run: python scripts/create_superadmin.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config.settings import settings
from app.models.user import User, UserRole
from app.core.security.security import hash_password
from app.models.base import Base


async def create_superadmin():
    if not settings.SUPERADMIN_EMAIL or not settings.SUPERADMIN_PASSWORD:
        raise RuntimeError(
            "SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD must be set in the environment before seeding the first superadmin."
        )

    engine = create_async_engine(
        settings.get_database_url,
        echo=False,
        future=True,
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if superadmin already exists
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.role == UserRole.SUPERADMIN)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Superadmin already exists: {existing.email}")
            return

        # Create superadmin
        superadmin = User(
            email=settings.SUPERADMIN_EMAIL,
            password_hash=hash_password(settings.SUPERADMIN_PASSWORD),
            role=UserRole.SUPERADMIN,
            company_id=None,
            is_active=True,
            is_verified=True,
        )
        session.add(superadmin)
        await session.commit()
        print("Superadmin created successfully!")
        print(f"Email: {settings.SUPERADMIN_EMAIL}")
        print("Password was read from the environment. Please rotate it after first login.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_superadmin())