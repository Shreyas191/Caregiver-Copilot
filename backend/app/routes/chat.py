import asyncio
import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import run_graph
from app.agent.nodes.generator import register_stream, unregister_stream
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

    await service.save_message(
        thread_id=thread.id,
        caregiver_id=caregiver.id,
        care_recipient_id=care_recipient_id,
        role=MessageRole.user,
        content=payload.content,
    )

    # Load prior messages for this thread to give the graph conversation history.
    # Exclude the message just saved (the current user turn) so it isn't duplicated.
    prior_messages = await service.list_messages(thread.id, caregiver.id)
    history = [
        {"role": m.role.value, "content": m.content}
        for m in prior_messages[:-1]  # all but the just-saved user message
        if m.role.value in ("user", "assistant") and m.content
    ]

    async def event_stream():
        # Send thread_id immediately so the UI registers the thread
        # and shows the typing indicator while the graph runs.
        yield f"data: {json.dumps({'thread_id': str(thread.id)})}\n\n"

        stream_id = str(uuid.uuid4())
        token_queue: asyncio.Queue[str | None] = asyncio.Queue()
        register_stream(stream_id, token_queue)

        final_state: dict = {}
        tool_calls_log: list = []
        latency_ms = None
        _start = time.monotonic()

        async def _run_graph() -> None:
            nonlocal final_state, tool_calls_log, latency_ms
            try:
                result = await run_graph(
                    care_recipient_id=care_recipient_id,
                    user_message=payload.content,
                    db=db,
                    thread_id=payload.thread_id,
                    clerk_user_id=clerk_user_id,
                    history=history,
                    stream_id=stream_id,
                )
                latency_ms = int((time.monotonic() - _start) * 1000)
                final_state = result
                tool_calls_log = result.get("tools_called") or []
            except Exception as e:
                logger.exception("Agent graph failed: %s", e)
            finally:
                # Always signal end of stream so the consumer loop below exits.
                await token_queue.put(None)
                unregister_stream(stream_id)

        graph_task = asyncio.create_task(_run_graph())

        # Forward tokens to the SSE stream as they arrive from the generator.
        tokens_streamed = 0
        try:
            while True:
                token = await asyncio.wait_for(token_queue.get(), timeout=120.0)
                if token is None:
                    break
                tokens_streamed += 1
                yield f"data: {json.dumps({'token': token})}\n\n"
        except asyncio.TimeoutError:
            logger.warning("Token queue timed out for thread %s", thread.id)
            graph_task.cancel()

        await graph_task

        reply_content = (
            final_state.get("final_response")
            or "I'm sorry, I encountered an error processing your request. "
               "Please try again or contact the care recipient's healthcare provider directly."
        )

        # Fallback: if the generator never streamed (e.g. max-iterations hit or escalation
        # path), push the final_response word-by-word so the frontend shows something.
        if tokens_streamed == 0:
            words = reply_content.split(" ")
            for i, word in enumerate(words):
                yield f"data: {json.dumps({'token': word if i == 0 else ' ' + word})}\n\n"

        await service.save_message(
            thread_id=thread.id,
            caregiver_id=caregiver.id,
            care_recipient_id=care_recipient_id,
            role=MessageRole.assistant,
            content=reply_content,
            tool_calls=tool_calls_log,
            model_used=None,
            tokens_input=None,
            tokens_output=None,
            latency_ms=latency_ms,
        )
        await db.commit()

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
