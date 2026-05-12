"""Hybrid (dense + sparse) retrieval over Qdrant collections.

Uses Reciprocal Rank Fusion (RRF) to combine dense cosine scores with
BM25-style sparse scores. Mandatory care_recipient_id filter enforced
for document_chunks and episode_chunks collections.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
    NamedVector,
    NamedSparseVector,
    SparseVector,
)

from app.agent.embeddings import Embedder
from app.core.config import get_settings

# Collections where filtering by care_recipient_id is mandatory
_CARE_RECIPIENT_REQUIRED = {"document_chunks", "episode_chunks"}


class RetrievedChunk(BaseModel):
    id: str
    text: str
    score: float
    payload: dict[str, Any]


def _build_filter(filter_dict: dict[str, Any]) -> Filter | None:
    if not filter_dict:
        return None
    conditions = [
        FieldCondition(key=k, match=MatchValue(value=v))
        for k, v in filter_dict.items()
    ]
    return Filter(must=conditions)


def _rrf(dense_results: list, sparse_results: list, k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion over two ranked lists of (id, score) tuples."""
    scores: dict[str, float] = {}
    for rank, (doc_id, _) in enumerate(dense_results):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    for rank, (doc_id, _) in enumerate(sparse_results):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


async def hybrid_search(
    collection: str,
    query: str,
    filter: dict[str, Any],
    top_k: int = 5,
) -> list[RetrievedChunk]:
    """Perform hybrid dense + sparse search over a Qdrant collection.

    Raises ValueError if the collection requires a care_recipient_id filter
    and one is not provided.
    """
    if collection in _CARE_RECIPIENT_REQUIRED and "care_recipient_id" not in filter:
        raise ValueError(
            f"Collection '{collection}' requires a 'care_recipient_id' filter. "
            "Omitting it would allow cross-user data leakage."
        )

    settings = get_settings()
    client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
    )
    embedder = Embedder()

    try:
        vector = await embedder.embed_query(query)
        qdrant_filter = _build_filter(filter)

        # Dense search
        dense_hits = await client.search(
            collection_name=collection,
            query_vector=NamedVector(name="dense", vector=vector.dense),
            query_filter=qdrant_filter,
            limit=top_k * 2,
            with_payload=True,
        )

        # Sparse search
        sparse_vec = SparseVector(
            indices=list(vector.sparse.keys()),
            values=list(vector.sparse.values()),
        )
        try:
            sparse_hits = await client.search(
                collection_name=collection,
                query_vector=NamedSparseVector(name="sparse", vector=sparse_vec),
                query_filter=qdrant_filter,
                limit=top_k * 2,
                with_payload=True,
            )
        except Exception:
            # Sparse vector index may not be populated; fall back to dense only
            sparse_hits = []

        # Build (id, score) lists for RRF
        dense_ranked = [(str(h.id), h.score) for h in dense_hits]
        sparse_ranked = [(str(h.id), h.score) for h in sparse_hits]

        fused = _rrf(dense_ranked, sparse_ranked)[:top_k]

        # Map id -> hit for payload lookup
        all_hits = {str(h.id): h for h in dense_hits}
        all_hits.update({str(h.id): h for h in sparse_hits})

        chunks: list[RetrievedChunk] = []
        for doc_id, rrf_score in fused:
            hit = all_hits.get(doc_id)
            if hit is None:
                continue
            payload = dict(hit.payload or {})
            text = payload.pop("text", "")
            chunks.append(
                RetrievedChunk(
                    id=doc_id,
                    text=text,
                    score=rrf_score,
                    payload=payload,
                )
            )

        return chunks

    finally:
        await client.close()
        await embedder.aclose()
