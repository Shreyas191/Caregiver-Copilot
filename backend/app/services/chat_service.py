"""Chat service: thread/message persistence and placeholder streaming."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.caregiver import Caregiver
from app.models.conversation import ConversationMessage, ConversationThread
from app.models.enums import MessageRole

_PLACEHOLDER = (
    "This is a placeholder response. The agent will be implemented in a later task. "
    "I've received your message and can see the care recipient's context. "
    "Once the agent is wired up, I'll be able to provide meaningful clinical assistance."
)


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_caregiver(self, clerk_user_id: str, claims: dict) -> Caregiver:
        result = await self.db.execute(
            select(Caregiver).where(Caregiver.clerk_user_id == clerk_user_id)
        )
        caregiver = result.scalar_one_or_none()
        if not caregiver:
            email = claims.get("email", f"{clerk_user_id}@placeholder.com")
            name = claims.get("name", "Caregiver")
            caregiver = Caregiver(
                clerk_user_id=clerk_user_id,
                display_name=name,
                email=email,
                timezone="America/New_York",
            )
            self.db.add(caregiver)
            await self.db.flush()
            await self.db.refresh(caregiver)
        return caregiver

    async def get_or_create_thread(
        self,
        care_recipient_id: uuid.UUID,
        caregiver_id: uuid.UUID,
        thread_id: uuid.UUID | None,
        first_message: str,
    ) -> ConversationThread:
        if thread_id:
            result = await self.db.execute(
                select(ConversationThread).where(
                    ConversationThread.id == thread_id,
                    ConversationThread.care_recipient_id == care_recipient_id,
                    ConversationThread.caregiver_id == caregiver_id,
                )
            )
            thread = result.scalar_one_or_none()
            if thread:
                return thread

        title = first_message[:60] + ("…" if len(first_message) > 60 else "")
        thread = ConversationThread(
            caregiver_id=caregiver_id,
            care_recipient_id=care_recipient_id,
            title=title,
        )
        self.db.add(thread)
        await self.db.flush()
        await self.db.refresh(thread)
        return thread

    async def save_message(
        self,
        thread_id: uuid.UUID,
        caregiver_id: uuid.UUID,
        care_recipient_id: uuid.UUID,
        role: MessageRole,
        content: str,
        tool_calls: list | None = None,
        model_used: str | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        latency_ms: int | None = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            thread_id=thread_id,
            caregiver_id=caregiver_id,
            care_recipient_id=care_recipient_id,
            role=role,
            content=content,
            tool_calls=tool_calls or [],
            model_used=model_used,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return msg

    async def list_threads(
        self, care_recipient_id: uuid.UUID, caregiver_id: uuid.UUID
    ) -> list[ConversationThread]:
        result = await self.db.execute(
            select(ConversationThread)
            .where(
                ConversationThread.care_recipient_id == care_recipient_id,
                ConversationThread.caregiver_id == caregiver_id,
            )
            .order_by(desc(ConversationThread.updated_at))
        )
        return list(result.scalars().all())

    async def list_messages(
        self, thread_id: uuid.UUID, caregiver_id: uuid.UUID
    ) -> list[ConversationMessage]:
        result = await self.db.execute(
            select(ConversationMessage)
            .where(
                ConversationMessage.thread_id == thread_id,
                ConversationMessage.caregiver_id == caregiver_id,
            )
            .order_by(ConversationMessage.created_at)
        )
        return list(result.scalars().all())


async def stream_placeholder_reply(text: str = _PLACEHOLDER) -> AsyncIterator[str]:
    """Yield SSE-formatted tokens word-by-word to simulate streaming."""
    words = text.split(" ")
    for i, word in enumerate(words):
        token = word if i == 0 else " " + word
        payload = json.dumps({"token": token})
        yield f"data: {payload}\n\n"
        await asyncio.sleep(0.03)
    yield "data: [DONE]\n\n"
