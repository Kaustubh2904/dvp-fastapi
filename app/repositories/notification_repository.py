from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.base_repository import BaseRepository
from app.models.notification import Notification


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self):
        super().__init__(Notification)

    async def get_by_user(self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> list[Notification]:
        query = select(self.model).where(self.model.user_id == user_id).order_by(self.model.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def mark_all_read(self, db: AsyncSession, user_id: int) -> None:
        query = select(self.model).where(and_(self.model.user_id == user_id, self.model.is_read == False))
        result = await db.execute(query)
        unread = result.scalars().all()
        for item in unread:
            item.is_read = True
            db.add(item)
        await db.commit()


notification_repository = NotificationRepository()