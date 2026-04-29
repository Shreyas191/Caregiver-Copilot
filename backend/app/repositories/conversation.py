from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import ConversationThread, ConversationMessage
from app.repositories.base import BaseRepository

class ConversationThreadRepository(BaseRepository[ConversationThread]):
    def __init__(self, db: AsyncSession):
        super().__init__(ConversationThread, db)

class ConversationMessageRepository(BaseRepository[ConversationMessage]):
    def __init__(self, db: AsyncSession):
        super().__init__(ConversationMessage, db)
