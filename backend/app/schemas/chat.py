import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import MessageRole


class ChatMessageRequest(BaseModel):
    content: str
    thread_id: uuid.UUID | None = None


class ThreadResponse(BaseModel):
    id: uuid.UUID
    caregiver_id: uuid.UUID
    care_recipient_id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    care_recipient_id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
