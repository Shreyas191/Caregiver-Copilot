from sqlalchemy.ext.asyncio import AsyncSession
from app.models.caregiver import Caregiver
from app.repositories.base import BaseRepository

class CaregiverRepository(BaseRepository[Caregiver]):
    def __init__(self, db: AsyncSession):
        super().__init__(Caregiver, db)
