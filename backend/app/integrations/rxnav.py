import httpx
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import urllib.parse

from app.models.external_api_cache import ExternalApiCache
from app.schemas.medication import MedicationSuggestion

RXNAV_BASE_URL = "https://rxnav.nlm.nih.gov/REST"

async def search_medications(db: AsyncSession, query: str, max_results: int = 10) -> list[MedicationSuggestion]:
    """
    Search medications using NIH RxNav approximateTerm API.
    Uses external_api_cache to avoid hitting rate limits.
    """
    if not query or len(query) < 2:
        return []

    # Check cache
    cache_key = f"rxnav:approximate:{query.lower().strip()}"
    
    result = await db.execute(
        select(ExternalApiCache).where(ExternalApiCache.cache_key == cache_key)
    )
    cache_entry = result.scalar_one_or_none()
    
    now = datetime.now(timezone.utc)
    
    if cache_entry and cache_entry.expires_at > now:
        # Cache hit
        data = cache_entry.response_data
    else:
        # Cache miss or expired
        url = f"{RXNAV_BASE_URL}/approximateTerm.json?term={urllib.parse.quote(query)}&maxEntries={max_results}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code != 200:
                # Fallback to empty list on error
                return []
            
            data = response.json()
            
        # Save to cache
        if cache_entry:
            cache_entry.response_data = data
            cache_entry.expires_at = now + timedelta(hours=24)
        else:
            cache_entry = ExternalApiCache(
                cache_key=cache_key,
                service="rxnav",
                response_data=data,
                expires_at=now + timedelta(hours=24),
                created_at=now
            )
            db.add(cache_entry)
            
        await db.flush()

    # Parse RxNav response
    suggestions = []
    seen_rxcui = set()
    
    approx_group = data.get("approximateGroup", {})
    candidates = approx_group.get("candidate", [])
    
    for c in candidates:
        rxcui = c.get("rxcui")
        if rxcui in seen_rxcui:
            continue
            
        score = float(c.get("score", 0.0))
        name = c.get("name")
        
        # Some sources might not have a name attached in the approximate payload,
        # but typically RXNORM or USP will. If missing, fallback to capitalized query.
        if not name:
            name = query.capitalize()
            
        suggestions.append(MedicationSuggestion(rxcui=rxcui, name=name, score=score))
        seen_rxcui.add(rxcui)
        
        if len(suggestions) >= max_results:
            break
        
    return suggestions
