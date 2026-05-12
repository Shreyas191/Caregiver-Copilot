"""context_loader node (CC-030).

Preloads care recipient profile, active medications, recent vitals and episodes
into the AgentState before the generator runs.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import AgentState
from app.agent.tools import set_session
from app.agent.tools.context_tools import (
    get_active_medications,
    get_care_recipient_profile,
    get_recent_episodes,
    get_recent_vitals,
)


async def context_loader_node(state: AgentState, db: AsyncSession) -> dict[str, Any]:
    """Preload care recipient context into state."""
    care_recipient_id = state["care_recipient_id"]

    set_session(db)

    profile = await get_care_recipient_profile(care_recipient_id)
    meds = await get_active_medications(care_recipient_id)
    vitals = await get_recent_vitals(care_recipient_id, limit=10)
    episodes = await get_recent_episodes(care_recipient_id, limit=5)

    return {
        "retrieved_context": {
            "profile": profile.model_dump(mode="json"),
            "medications": [m.model_dump(mode="json") for m in meds],
            "vitals": [v.model_dump(mode="json") for v in vitals],
            "episodes": [e.model_dump(mode="json") for e in episodes],
        }
    }
