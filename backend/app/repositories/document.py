from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document
from app.repositories.base import BaseRepository

class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: AsyncSession):
        super().__init__(Document, db)
