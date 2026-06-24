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
            email="superadmin@dvp.com",
            password_hash=hash_password("SuperAdmin@123"),
            role=UserRole.SUPERADMIN,
            company_id=None,
            is_active=True,
            is_verified=True,
        )
        session.add(superadmin)
        await session.commit()
        print("Superadmin created successfully!")
        print(f"Email: superadmin@dvp.com")
        print(f"Password: SuperAdmin@123")
        print("Please change the password after first login.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_superadmin())