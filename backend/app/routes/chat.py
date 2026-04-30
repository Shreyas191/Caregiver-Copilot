import json
import logging
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.v0_loop import run_agent
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.enums import MessageRole
from app.schemas.chat import ChatMessageRequest, MessageResponse, ThreadResponse
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/{care_recipient_id}/messages")
async def send_message(
    care_recipient_id: uuid.UUID,
    payload: ChatMessageRequest,
    request: Request,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Accept a user message and stream an assistant reply as SSE."""
    claims = getattr(request.state, "clerk_claims", {})
    service = ChatService(db)

    caregiver = await service.get_or_create_caregiver(clerk_user_id, claims)
    thread = await service.get_or_create_thread(
        care_recipient_id=care_recipient_id,
        caregiver_id=caregiver.id,
        thread_id=payload.thread_id,
        first_message=payload.content,
    )

    # Save the user message
    await service.save_message(
        thread_id=thread.id,
        caregiver_id=caregiver.id,
        care_recipient_id=care_recipient_id,
        role=MessageRole.user,
        content=payload.content,
    )

    # Run the agent loop
    try:
        agent_result = await run_agent(
            care_recipient_id=care_recipient_id,
            user_message=payload.content,
            db=db,
        )
        reply_content = agent_result.content
        tool_calls_log = agent_result.tool_calls_log
        model_used = agent_result.model_used
        tokens_input = agent_result.tokens_input
        tokens_output = agent_result.tokens_output
        latency_ms = agent_result.latency_ms
    except Exception as e:
        logger.exception("Agent loop failed: %s", e)
        reply_content = (
            "I'm sorry, I encountered an error processing your request. "
            "Please try again or contact the care recipient's healthcare provider directly."
        )
        tool_calls_log = []
        model_used = None
        tokens_input = None
        tokens_output = None
        latency_ms = None

    # Save the assistant message with full audit trail
    await service.save_message(
        thread_id=thread.id,
        caregiver_id=caregiver.id,
        care_recipient_id=care_recipient_id,
        role=MessageRole.assistant,
        content=reply_content,
        tool_calls=tool_calls_log,
        model_used=model_used,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        latency_ms=latency_ms,
    )

    await db.commit()

    # Stream the reply as SSE
    async def event_stream():
        yield f"data: {json.dumps({'thread_id': str(thread.id)})}\n\n"

        # Stream word-by-word for a natural feel
        words = reply_content.split(" ")
        for i, word in enumerate(words):
            token = word if i == 0 else " " + word
            yield f"data: {json.dumps({'token': token})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{care_recipient_id}/threads", response_model=list[ThreadResponse])
async def list_threads(
    care_recipient_id: uuid.UUID,
    request: Request,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[ThreadResponse]:
    """List all conversation threads for a care recipient."""
    claims = getattr(request.state, "clerk_claims", {})
    service = ChatService(db)
    caregiver = await service.get_or_create_caregiver(clerk_user_id, claims)
    return await service.list_threads(care_recipient_id, caregiver.id)


@router.get("/threads/{thread_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    thread_id: uuid.UUID,
    request: Request,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    """Fetch all messages in a thread."""
    claims = getattr(request.state, "clerk_claims", {})
    service = ChatService(db)
    caregiver = await service.get_or_create_caregiver(clerk_user_id, claims)
    messages = await service.list_messages(thread_id, caregiver.id)
    if not messages:
        return []
    return messages
