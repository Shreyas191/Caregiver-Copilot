"""Tests for CC-020: drug interaction checker and RxNav integration."""

import pytest
import uuid
from unittest.mock import AsyncMock, patch
from datetime import date

from app.agent.tools.clinical_tools import check_drug_interactions, CHECK_DRUG_INTERACTIONS
from app.agent.tools.context_tools import set_session
from app.agent.tools.schemas import ActiveMedication
from app.tests.conftest import make_test_session


@pytest.mark.asyncio
async def test_check_drug_interactions_no_rxcuis():
    """Returns empty list when no medications have RxCUIs."""
    async with make_test_session() as session:
        set_session(session)
        with patch(
            "app.agent.tools.clinical_tools.get_active_medications",
            new=AsyncMock(return_value=[
                ActiveMedication(
                    id=uuid.uuid4(), display_name="Some Drug",
                    rxnorm_code=None, started_at=date.today(),
                ),
            ]),
        ):
            result = await check_drug_interactions(uuid.uuid4())
            assert result == []


@pytest.mark.asyncio
async def test_check_drug_interactions_single_med_returns_empty():
    """Returns empty when only one med has an RxCUI (need >=2 for interactions)."""
    async with make_test_session() as session:
        set_session(session)
        with patch(
            "app.agent.tools.clinical_tools.get_active_medications",
            new=AsyncMock(return_value=[
                ActiveMedication(
                    id=uuid.uuid4(), display_name="Lisinopril",
                    rxnorm_code="29046", started_at=date.today(),
                ),
            ]),
        ):
            result = await check_drug_interactions(uuid.uuid4())
            assert result == []


@pytest.mark.asyncio
async def test_check_drug_interactions_returns_mapped_results():
    """Maps Interaction objects to InteractionResult correctly."""
    async with make_test_session() as session:
        set_session(session)

        meds = [
            ActiveMedication(id=uuid.uuid4(), display_name="Warfarin",
                             rxnorm_code="11289", started_at=date.today()),
            ActiveMedication(id=uuid.uuid4(), display_name="Aspirin",
                             rxnorm_code="1191", started_at=date.today()),
        ]

        from app.integrations.rxnav import Interaction
        fake = Interaction(
            rxcui1="11289", drug1_name="Warfarin",
            rxcui2="1191", drug2_name="Aspirin",
            severity="high", description="Increased bleeding risk",
        )

        with patch("app.agent.tools.clinical_tools.get_active_medications",
                   new=AsyncMock(return_value=meds)):
            with patch("app.integrations.rxnav.get_interactions",
                       new=AsyncMock(return_value=[fake])):
                result = await check_drug_interactions(uuid.uuid4())

        assert len(result) == 1
        assert result[0].drug1 == "Warfarin"
        assert result[0].drug2 == "Aspirin"
        assert result[0].severity == "high"
        assert "bleeding" in result[0].description


def test_check_drug_interactions_tool_schema():
    """Tool definition has correct name and required fields."""
    assert CHECK_DRUG_INTERACTIONS.name == "check_drug_interactions"
    props = CHECK_DRUG_INTERACTIONS.input_schema["properties"]
    assert "care_recipient_id" in props
    assert "care_recipient_id" in CHECK_DRUG_INTERACTIONS.input_schema["required"]
