"""OpenFDA drug label integration.

Queries the FDA drug label API for warnings, adverse reactions, and contraindications.
Caches results for 7 days.
"""

import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external_api_cache import ExternalApiCache

OPENFDA_BASE_URL = "https://api.fda.gov"


class DrugLabel(BaseModel):
    brand_name: str | None = None
    generic_name: str | None = None
    warnings: list[str]
    adverse_reactions: list[str]
    contraindications: list[str]
    indications: list[str]


def _extract_sentences(sections: list[str] | None, max_chars: int = 2000) -> list[str]:
    """Split raw FDA label text into sentence-like chunks, truncated."""
    if not sections:
        return []
    combined = " ".join(sections)[:max_chars]
    sentences = [s.strip() for s in combined.replace("\n", " ").split(".") if len(s.strip()) > 10]
    return sentences[:10]


async def get_drug_label(
    db: AsyncSession,
    drug_name: str | None = None,
    rxcui: str | None = None,
) -> DrugLabel | None:
    """Query OpenFDA for a drug label.

    Tries drug_name first, falls back to rxcui if provided.
    Returns None gracefully when no match is found.
    """
    if not drug_name and not rxcui:
        return None

    search_term = drug_name or rxcui
    cache_key = f"openfda:label:{search_term.lower().strip()}"

    result = await db.execute(
        select(ExternalApiCache).where(ExternalApiCache.cache_key == cache_key)
    )
    cache_entry = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if cache_entry and cache_entry.expires_at > now:
        data = cache_entry.response_data
    else:
        query = urllib.parse.quote(f'openfda.brand_name:"{search_term}" OR openfda.generic_name:"{search_term}"')
        url = f"{OPENFDA_BASE_URL}/drug/label.json?search={query}&limit=1"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            if response.status_code == 404:
                # No match — cache the empty result to avoid hammering the API
                data = {"results": []}
            elif response.status_code != 200:
                return None
            else:
                data = response.json()

        if cache_entry:
            cache_entry.response_data = data
            cache_entry.expires_at = now + timedelta(days=7)
        else:
            cache_entry = ExternalApiCache(
                cache_key=cache_key,
                service="openfda",
                response_data=data,
                expires_at=now + timedelta(days=7),
                created_at=now,
            )
            db.add(cache_entry)

        await db.flush()

    results = data.get("results", [])
    if not results:
        return None

    label = results[0]
    openfda = label.get("openfda", {})

    return DrugLabel(
        brand_name=(openfda.get("brand_name") or [None])[0],
        generic_name=(openfda.get("generic_name") or [None])[0],
        warnings=_extract_sentences(label.get("warnings") or label.get("warnings_and_cautions")),
        adverse_reactions=_extract_sentences(label.get("adverse_reactions")),
        contraindications=_extract_sentences(label.get("contraindications")),
        indications=_extract_sentences(label.get("indications_and_usage")),
    )
