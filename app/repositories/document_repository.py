from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.base_repository import BaseRepository
from app.models.document import Document


class DocumentRepository(BaseRepository[Document]):
    def __init__(self):
        super().__init__(Document)

    async def get_by_employee(self, db: AsyncSession, employee_id: int) -> list[Document]:
        query = select(self.model).where(self.model.employee_id == employee_id)
        result = await db.execute(query)
        return list(result.scalars().all())


document_repository = DocumentRepository()