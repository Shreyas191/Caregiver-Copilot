from sqlalchemy.ext.asyncio import AsyncSession
from app.models.care_recipient import CareRecipient
from app.repositories.base import BaseRepository

class CareRecipientRepository(BaseRepository[CareRecipient]):
    def __init__(self, db: AsyncSession):
        super().__init__(CareRecipient, db)
