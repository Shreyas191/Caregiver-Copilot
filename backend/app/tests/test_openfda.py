"""Tests for CC-021: OpenFDA drug label integration."""

import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone

from app.integrations.openfda import get_drug_label, DrugLabel, _extract_sentences
from app.tests.conftest import make_test_session


def test_extract_sentences_basic():
    """Splits text into sentence fragments."""
    text = "This drug may cause dizziness. Do not drive. Avoid alcohol."
    result = _extract_sentences([text])
    assert len(result) >= 2
    assert any("dizziness" in s for s in result)


def test_extract_sentences_empty():
    assert _extract_sentences(None) == []
    assert _extract_sentences([]) == []


def test_extract_sentences_truncates():
    """Respects max_chars limit."""
    long_text = "word. " * 500
    result = _extract_sentences([long_text], max_chars=100)
    assert len(result) <= 10


@pytest.mark.asyncio
async def test_get_drug_label_returns_none_on_no_match():
    """Returns None when OpenFDA finds no results."""
    async with make_test_session() as session:
        with patch("app.integrations.openfda.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=MagicMock(
                status_code=404,
            ))
            mock_client_cls.return_value = mock_client

            result = await get_drug_label(session, drug_name="nonexistentxyz123")
            assert result is None


@pytest.mark.asyncio
async def test_get_drug_label_returns_none_without_args():
    """Returns None when neither drug_name nor rxcui provided."""
    async with make_test_session() as session:
        result = await get_drug_label(session)
        assert result is None


@pytest.mark.asyncio
async def test_get_drug_label_parses_response():
    """Parses a mock OpenFDA response into a DrugLabel."""
    async with make_test_session() as session:
        mock_data = {
            "results": [{
                "openfda": {
                    "brand_name": ["Prinivil"],
                    "generic_name": ["Lisinopril"],
                },
                "warnings": ["May cause dry cough. Monitor renal function."],
                "adverse_reactions": ["Dizziness and lightheadedness are common. Headache may occur in some patients. Fatigue has been reported."],
                "contraindications": ["History of angioedema related to previous ACE inhibitor therapy."],
                "indications_and_usage": ["Treatment of hypertension."],
            }]
        }

        # Use a unique drug name to avoid hitting a real DB cache entry
        with patch("app.integrations.openfda.httpx.AsyncClient") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json = MagicMock(return_value=mock_data)

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await get_drug_label(session, drug_name="prinivil_test_unique")

        assert result is not None
        assert isinstance(result, DrugLabel)
        assert result.brand_name == "Prinivil"
        assert result.generic_name == "Lisinopril"
        assert len(result.warnings) > 0
        assert len(result.adverse_reactions) > 0
