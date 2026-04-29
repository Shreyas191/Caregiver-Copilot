from sqlalchemy.ext.asyncio import AsyncSession
from app.models.vital import Vital
from app.repositories.base import BaseRepository

class VitalRepository(BaseRepository[Vital]):
    def __init__(self, db: AsyncSession):
        super().__init__(Vital, db)
