"""Tests for CC-030: LangGraph state machine structure."""

import uuid
from unittest.mock import AsyncMock, patch

from app.agent.graph import build_graph, _route_after_router, _route_after_verifier
from app.agent.state import AgentState
from app.models.enums import MessageIntent
from langgraph.graph import END


def _make_state(**kwargs) -> AgentState:
    base: AgentState = {
        "care_recipient_id": uuid.uuid4(),
        "thread_id": None,
        "caregiver_clerk_id": "test_user",
        "messages": [{"role": "user", "content": "test"}],
        "intent": MessageIntent.symptom_report.value,
        "intent_confidence": 0.9,
        "retrieved_context": {},
        "tools_called": [],
        "final_response": None,
        "verifier_result": None,
        "regeneration_count": 0,
        "escalated": False,
    }
    base.update(kwargs)
    return base


def test_route_after_router_casual():
    state = _make_state(intent=MessageIntent.casual_chat.value)
    assert _route_after_router(state) == "casual_handler"


def test_route_after_router_symptom():
    state = _make_state(intent=MessageIntent.symptom_report.value)
    assert _route_after_router(state) == "context_loader"


def test_route_after_router_vital_logging():
    state = _make_state(intent=MessageIntent.vital_logging.value)
    assert _route_after_router(state) == "context_loader"


def test_route_after_router_medication_question():
    state = _make_state(intent=MessageIntent.medication_question.value)
    assert _route_after_router(state) == "context_loader"


def test_route_after_verifier_passes():
    state = _make_state(verifier_result={"passed": True, "severity": "none", "issues": []})
    assert _route_after_verifier(state) == END


def test_route_after_verifier_low_severity_passes():
    state = _make_state(verifier_result={"passed": True, "severity": "low", "issues": []})
    assert _route_after_verifier(state) == END


def test_route_after_verifier_medium_triggers_regeneration():
    state = _make_state(
        verifier_result={"passed": False, "severity": "medium", "issues": [{"description": "hallucination"}]},
        regeneration_count=0,
    )
    assert _route_after_verifier(state) == "generator"


def test_route_after_verifier_max_regen_escalates():
    state = _make_state(
        verifier_result={"passed": False, "severity": "high", "issues": []},
        regeneration_count=2,  # at max
    )
    assert _route_after_verifier(state) == "escalation"


def test_route_after_verifier_no_result_passes():
    state = _make_state(verifier_result=None)
    assert _route_after_verifier(state) == END


def test_build_graph_has_expected_nodes():
    db = AsyncMock()
    graph = build_graph(db)
    node_names = set(graph.nodes)
    for expected in ["router", "casual_handler", "context_loader", "generator", "verifier", "escalation"]:
        assert expected in node_names, f"Missing node: {expected}"
