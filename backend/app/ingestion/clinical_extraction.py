"""CC-040: Clinical data extraction using the generator LLM."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).parent.parent / "agent" / "prompts"

_PROMPT_FILES: dict[str, str] = {
    "lab_report": "extraction_lab.md",
    "discharge_summary": "extraction_discharge.md",
    "after_visit_summary": "extraction_visit.md",
}


class ClinicalExtraction(BaseModel):
    document_type: str
    raw: dict[str, Any]
    summary: str | None = None


def _load_prompt(document_type: str) -> str:
    filename = _PROMPT_FILES.get(document_type, "extraction_visit.md")
    return (_PROMPT_DIR / filename).read_text(encoding="utf-8")


def _strip_fences(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text.strip(), flags=re.MULTILINE)
    return text.strip()


async def extract_clinical_data(
    text: str,
    document_type: str = "after_visit_summary",
) -> ClinicalExtraction:
    """Extract structured clinical fields from document text.

    Uses the configured generator LLM with a type-specific prompt.
    Falls back to a minimal extraction on parse failure.
    """
    from app.providers.factory import get_generator_provider
    from app.providers.types import Message
    from app.core.config import get_settings

    settings = get_settings()
    prompt = _load_prompt(document_type)
    full_prompt = f"{prompt}\n\n{text[:8000]}"  # cap to avoid context overflow

    provider = get_generator_provider()
    try:
        response = await provider.chat(
            messages=[Message(role="user", content=full_prompt)],
            model=settings.generator_model_name,
        )
        raw_content = response.content or ""
        cleaned = _strip_fences(raw_content)
        parsed = json.loads(cleaned)
        return ClinicalExtraction(
            document_type=document_type,
            raw=parsed,
            summary=parsed.get("summary"),
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Clinical extraction parse failed for %s: %s", document_type, e)
        return ClinicalExtraction(
            document_type=document_type,
            raw={"error": "parse_failed", "raw_response": raw_content[:500]},
            summary=None,
        )
    finally:
        await provider.aclose()
