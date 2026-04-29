from sqlalchemy.ext.asyncio import AsyncSession
from app.models.provider_message import ProviderMessage
from app.repositories.base import BaseRepository

class ProviderMessageRepository(BaseRepository[ProviderMessage]):
    def __init__(self, db: AsyncSession):
        super().__init__(ProviderMessage, db)
