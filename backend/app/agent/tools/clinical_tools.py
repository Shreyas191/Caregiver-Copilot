"""Clinical reasoning tools: drug interactions, side effects, symptom-med links, urgency.

All tools rely on the same ContextVar session pattern as context_tools.
"""

import uuid
from typing import Any

from pydantic import BaseModel

from app.agent.tools.context_tools import _get_session, get_active_medications
from app.agent.tools.types import Tool


# ------------------------------------------------------------------
# CC-020: Drug interaction checker
# ------------------------------------------------------------------


class InteractionResult(BaseModel):
    drug1: str
    drug2: str
    severity: str
    description: str


async def check_drug_interactions(
    care_recipient_id: uuid.UUID,
) -> list[InteractionResult]:
    """Check for drug-drug interactions among the care recipient's active medications.

    Loads active meds, filters for those with an RxCUI, queries RxNav, and returns
    any known interactions with severity and description.
    """
    from app.integrations.rxnav import get_interactions

    db = _get_session()
    meds = await get_active_medications(care_recipient_id)

    rxcuis = [m.rxnorm_code for m in meds if m.rxnorm_code]
    if len(rxcuis) < 2:
        return []

    interactions = await get_interactions(db, rxcuis)

    return [
        InteractionResult(
            drug1=i.drug1_name or i.rxcui1,
            drug2=i.drug2_name or i.rxcui2,
            severity=i.severity,
            description=i.description,
        )
        for i in interactions
    ]


CHECK_DRUG_INTERACTIONS = Tool(
    name="check_drug_interactions",
    description=(
        "Check for known drug-drug interactions among the care recipient's active "
        "medications using the NIH RxNav API. Returns interactions with severity "
        "(high, moderate, low) and a brief description."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "care_recipient_id": {
                "type": "string",
                "format": "uuid",
                "description": "UUID of the care recipient",
            }
        },
        "required": ["care_recipient_id"],
    },
    function=check_drug_interactions,
)


# ------------------------------------------------------------------
# CC-021: Medication side effects lookup
# ------------------------------------------------------------------


class SideEffectResult(BaseModel):
    drug_name: str
    warnings: list[str]
    adverse_reactions: list[str]
    contraindications: list[str]
    found: bool


async def lookup_medication_side_effects(drug_name: str) -> SideEffectResult:
    """Look up side effects and warnings for a medication from the OpenFDA drug label database."""
    from app.integrations.openfda import get_drug_label

    db = _get_session()
    label = await get_drug_label(db, drug_name=drug_name)

    if label is None:
        return SideEffectResult(
            drug_name=drug_name,
            warnings=[],
            adverse_reactions=[],
            contraindications=[],
            found=False,
        )

    return SideEffectResult(
        drug_name=drug_name,
        warnings=label.warnings[:5] if label.warnings else [],
        adverse_reactions=label.adverse_reactions[:5] if label.adverse_reactions else [],
        contraindications=label.contraindications[:3] if label.contraindications else [],
        found=True,
    )


LOOKUP_MEDICATION_SIDE_EFFECTS = Tool(
    name="lookup_medication_side_effects",
    description=(
        "Look up FDA-labelled warnings, adverse reactions, and contraindications "
        "for a specific medication name using OpenFDA drug label data."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "drug_name": {
                "type": "string",
                "description": "Medication name to look up (e.g. 'lisinopril', 'metformin')",
            }
        },
        "required": ["drug_name"],
    },
    function=lookup_medication_side_effects,
)


# ------------------------------------------------------------------
# CC-022: Symptom-medication link checker (depends on Qdrant + embeddings)
# ------------------------------------------------------------------


class SymptomMedLink(BaseModel):
    medication_name: str
    symptom: str
    plausible: bool
    reasoning: str
    citation: str


async def check_symptom_medication_link(
    care_recipient_id: uuid.UUID,
    symptom_text: str,
) -> list[SymptomMedLink]:
    """Cross-reference reported symptoms against medication side effect profiles.

    For each active medication, retrieves relevant chunks from the drug_label_chunks
    Qdrant collection and scores the symptom-medication link using the generator model.
    """
    from app.agent.retrieval import hybrid_search
    from app.integrations.openfda import get_drug_label
    from app.providers.factory import get_generator_provider
    from app.core.config import get_settings

    meds = await get_active_medications(care_recipient_id)
    if not meds:
        return []

    db = _get_session()
    settings = get_settings()
    provider = get_generator_provider()
    results: list[SymptomMedLink] = []

    try:
        for med in meds:
            # Try Qdrant first for indexed drug label chunks
            try:
                filter_dict: dict[str, Any] = {}
                if med.rxnorm_code:
                    filter_dict = {"rxnorm_code": med.rxnorm_code}

                chunks = await hybrid_search(
                    collection="drug_label_chunks",
                    query=symptom_text,
                    filter=filter_dict,
                    top_k=3,
                )
                context_text = "\n\n".join(c.text for c in chunks)
            except Exception:
                # Fall back to OpenFDA if Qdrant isn't populated yet
                label = await get_drug_label(db, drug_name=med.display_name)
                if label:
                    parts = (label.adverse_reactions or []) + (label.warnings or [])
                    context_text = " ".join(parts[:3])
                else:
                    context_text = ""

            if not context_text:
                continue

            from app.providers.types import Message

            prompt = (
                f"Drug label information for {med.display_name}:\n{context_text}\n\n"
                f"Reported symptom: {symptom_text}\n\n"
                f"Is there a plausible link between this symptom and this medication "
                f"based on the label? Reply with JSON: "
                f'{{ "plausible": true/false, "reasoning": "...", "citation": "..." }}'
            )

            response = await provider.chat(
                messages=[Message(role="user", content=prompt)],
                model=settings.generator_model_name,
            )

            import json as _json

            try:
                raw = (response.content or "{}").strip()
                # Strip markdown code block if present
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                parsed = _json.loads(raw)
                results.append(
                    SymptomMedLink(
                        medication_name=med.display_name,
                        symptom=symptom_text,
                        plausible=bool(parsed.get("plausible", False)),
                        reasoning=parsed.get("reasoning", ""),
                        citation=parsed.get("citation", f"{med.display_name} drug label"),
                    )
                )
            except (_json.JSONDecodeError, KeyError):
                pass
    finally:
        await provider.aclose()

    return [r for r in results if r.plausible]


CHECK_SYMPTOM_MEDICATION_LINK = Tool(
    name="check_symptom_medication_link",
    description=(
        "Cross-reference a reported symptom against the side effect profiles of the "
        "care recipient's active medications. Returns plausible links with citations "
        "from the drug label."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "care_recipient_id": {
                "type": "string",
                "format": "uuid",
                "description": "UUID of the care recipient",
            },
            "symptom_text": {
                "type": "string",
                "description": "The symptom or complaint to investigate (e.g. 'dizziness and fatigue')",
            },
        },
        "required": ["care_recipient_id", "symptom_text"],
    },
    function=check_symptom_medication_link,
)


# ------------------------------------------------------------------
# CC-043: search_documents tool
# ------------------------------------------------------------------


class DocumentChunk(BaseModel):
    document_name: str
    document_type: str
    section: str | None
    page_number: int | None
    text: str
    score: float


async def search_documents(
    care_recipient_id: uuid.UUID,
    query: str,
    top_k: int = 5,
) -> list[DocumentChunk]:
    """Search indexed documents for a care recipient using hybrid search."""
    from app.agent.retrieval import hybrid_search

    results = await hybrid_search(
        collection="document_chunks",
        query=query,
        filter={"care_recipient_id": str(care_recipient_id)},
        top_k=top_k,
    )

    chunks = []
    for r in results:
        payload = r.get("payload", {})
        chunks.append(DocumentChunk(
            document_name=payload.get("document_name", "Unknown"),
            document_type=payload.get("document_type", "other"),
            section=payload.get("section"),
            page_number=payload.get("page_number"),
            text=payload.get("text", ""),
            score=r.get("score", 0.0),
        ))
    return chunks


SEARCH_DOCUMENTS = Tool(
    name="search_documents",
    description=(
        "Search the care recipient's uploaded documents (lab reports, discharge summaries, "
        "visit notes) for relevant information. Returns text chunks with citations."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "care_recipient_id": {
                "type": "string",
                "format": "uuid",
                "description": "UUID of the care recipient",
            },
            "query": {
                "type": "string",
                "description": "What to search for (e.g. 'HbA1c results', 'discharge medications')",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default 5)",
                "default": 5,
            },
        },
        "required": ["care_recipient_id", "query"],
    },
    function=search_documents,
)


def get_clinical_tools() -> list[Tool]:
    """Return all clinical reasoning tools."""
    return [
        CHECK_DRUG_INTERACTIONS,
        LOOKUP_MEDICATION_SIDE_EFFECTS,
        CHECK_SYMPTOM_MEDICATION_LINK,
        SEARCH_DOCUMENTS,
    ]
