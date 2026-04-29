from sqlalchemy.ext.asyncio import AsyncSession
from app.models.medication import Medication
from app.repositories.base import BaseRepository

class MedicationRepository(BaseRepository[Medication]):
    def __init__(self, db: AsyncSession):
        super().__init__(Medication, db)
