"""LangGraph state machine for the Caregiver Co-Pilot agent (CC-030 through CC-034).

Graph topology:
    START
      └── router
            ├── casual_chat → casual_handler → END
            └── (other intents) → context_loader → generator → verifier
                                                                    ├── passed → END
                                                                    ├── failed + retries left → generator (retry)
                                                                    └── failed + max retries → escalation → END
"""

from __future__ import annotations

import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import AgentState
from app.models.enums import MessageIntent

MAX_REGENERATIONS = 2


def _route_after_router(state: AgentState) -> str:
    """Edge function: route casual chat to fast path, everything else to clinical path."""
    intent = state.get("intent", MessageIntent.symptom_report.value)
    if intent == MessageIntent.casual_chat.value:
        return "casual_handler"
    return "context_loader"


def _route_after_verifier(state: AgentState) -> str:
    """Edge function: route to persistence (pass), regeneration, or escalation."""
    verifier = state.get("verifier_result") or {}
    passed = verifier.get("passed", True)
    severity = verifier.get("severity", "none")
    regen_count = state.get("regeneration_count", 0)

    if passed:
        return END

    if severity in ("medium", "high") and regen_count < MAX_REGENERATIONS:
        return "generator"  # regenerate with verifier feedback

    return "escalation"


def _increment_regen(state: AgentState) -> dict[str, Any]:
    """Increment regeneration_count before re-entering generator."""
    return {"regeneration_count": state.get("regeneration_count", 0) + 1}


def build_graph(db: AsyncSession) -> Any:
    """Build and compile the LangGraph state machine.

    The db session is injected into all nodes that need DB access via closures.
    """
    from app.agent.nodes.router import router_node
    from app.agent.nodes.casual_handler import casual_handler_node
    from app.agent.nodes.context_loader import context_loader_node
    from app.agent.nodes.generator import generator_node
    from app.agent.nodes.verifier import verifier_node
    from app.agent.nodes.escalation import escalation_node
    from app.agent.tracing import trace_node

    # Wrap DB-dependent nodes to inject the session + tracing
    @trace_node("context_loader")
    async def _context_loader(state: AgentState) -> dict:
        return await context_loader_node(state, db)

    @trace_node("generator")
    async def _generator(state: AgentState) -> dict:
        updates = await generator_node(state, db)
        return updates

    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("casual_handler", casual_handler_node)
    graph.add_node("context_loader", _context_loader)
    graph.add_node("generator", _generator)
    graph.add_node("verifier", verifier_node)
    graph.add_node("escalation", escalation_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", _route_after_router)
    graph.add_edge("casual_handler", END)
    graph.add_edge("context_loader", "generator")
    graph.add_edge("generator", "verifier")
    graph.add_conditional_edges("verifier", _route_after_verifier)
    graph.add_edge("escalation", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


async def run_graph(
    care_recipient_id: uuid.UUID,
    user_message: str,
    db: AsyncSession,
    thread_id: uuid.UUID | None = None,
    clerk_user_id: str = "",
    history: list[dict[str, str]] | None = None,
    stream_id: str | None = None,
) -> dict[str, Any]:
    """Invoke the compiled LangGraph and return the final state.

    history: prior user/assistant turns for this thread, oldest first.
    The current user_message is appended as the final entry.
    stream_id: if set, generator/casual_handler nodes will push tokens into
    the registered queue so the SSE route can forward them in real-time.
    """
    compiled = build_graph(db)

    # Build message list: prior turns (up to last 10 exchanges) + current message
    prior = (history or [])[-20:]  # cap at 20 messages (~10 exchanges) to stay within context
    messages = prior + [{"role": "user", "content": user_message}]

    initial_state: AgentState = {
        "care_recipient_id": care_recipient_id,
        "thread_id": thread_id,
        "caregiver_clerk_id": clerk_user_id,
        "messages": messages,
        "intent": MessageIntent.symptom_report.value,
        "intent_confidence": 0.5,
        "retrieved_context": {},
        "tools_called": [],
        "final_response": None,
        "verifier_result": None,
        "regeneration_count": 0,
        "escalated": False,
        "stream_id": stream_id,
    }

    config = {"configurable": {"thread_id": str(thread_id or uuid.uuid4())}}
    final_state = await compiled.ainvoke(initial_state, config=config)
    return final_state
