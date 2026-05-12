"""Tests for clinical tool definitions (CC-020/021/022)."""

import json
from app.agent.tools.clinical_tools import (
    get_clinical_tools,
    CHECK_DRUG_INTERACTIONS,
    LOOKUP_MEDICATION_SIDE_EFFECTS,
    CHECK_SYMPTOM_MEDICATION_LINK,
)


def test_get_clinical_tools_returns_four():
    tools = get_clinical_tools()
    assert len(tools) == 4  # interactions, side_effects, symptom_link, search_documents


def test_clinical_tool_names():
    tools = get_clinical_tools()
    names = {t.name for t in tools}
    assert "check_drug_interactions" in names
    assert "lookup_medication_side_effects" in names
    assert "check_symptom_medication_link" in names


def test_clinical_tool_schemas_are_valid():
    """All tool input schemas are valid JSON Schema objects."""
    for tool in get_clinical_tools():
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema


def test_lookup_side_effects_schema():
    props = LOOKUP_MEDICATION_SIDE_EFFECTS.input_schema["properties"]
    assert "drug_name" in props
    assert "drug_name" in LOOKUP_MEDICATION_SIDE_EFFECTS.input_schema["required"]


def test_symptom_link_schema():
    props = CHECK_SYMPTOM_MEDICATION_LINK.input_schema["properties"]
    assert "care_recipient_id" in props
    assert "symptom_text" in props
    required = CHECK_SYMPTOM_MEDICATION_LINK.input_schema["required"]
    assert "care_recipient_id" in required
    assert "symptom_text" in required
