"""persistence node (CC-030).

Writes conversation messages (user + assistant) to the database after the agent loop.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agent.state import AgentState
from app.models.conversation import ConversationMessage, ConversationThread
from app.models.enums import MessageRole, MessageIntent


async def persistence_node(state: AgentState, db: AsyncSession) -> dict[str, Any]:
    """Persist the conversation turn to the database."""
    care_recipient_id = state["care_recipient_id"]
    thread_id = state.get("thread_id")
    messages = state.get("messages", [])
    final_response = state.get("final_response", "")
    tools_called = state.get("tools_called", [])
    intent = state.get("intent", MessageIntent.unknown.value)

    # Upsert thread
    if thread_id is None:
        thread = ConversationThread(
            care_recipient_id=care_recipient_id,
        )
        db.add(thread)
        await db.flush()
        thread_id = thread.id

    now = datetime.now(timezone.utc)

    # Persist user message
    user_content = messages[-1]["content"] if messages else ""
    user_msg = ConversationMessage(
        thread_id=thread_id,
        role=MessageRole.user,
        content=user_content,
        intent=MessageIntent(intent) if intent in [e.value for e in MessageIntent] else MessageIntent.unknown,
        created_at=now,
        tool_calls=[],
    )
    db.add(user_msg)

    # Persist assistant message
    assistant_msg = ConversationMessage(
        thread_id=thread_id,
        role=MessageRole.assistant,
        content=final_response,
        intent=MessageIntent(intent) if intent in [e.value for e in MessageIntent] else MessageIntent.unknown,
        created_at=now,
        tool_calls=tools_called,
        verifier_passed=state.get("verifier_result", {}).get("passed") if state.get("verifier_result") else None,
        verifier_severity=state.get("verifier_result", {}).get("severity") if state.get("verifier_result") else None,
    )
    db.add(assistant_msg)
    await db.flush()

    return {"thread_id": thread_id}
