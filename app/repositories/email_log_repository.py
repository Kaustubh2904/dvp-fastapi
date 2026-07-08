from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base_repository import BaseRepository
from app.models.email_log import EmailLog


class EmailLogRepository(BaseRepository[EmailLog]):
    def __init__(self):
        super().__init__(EmailLog)


email_log_repository = EmailLogRepository()