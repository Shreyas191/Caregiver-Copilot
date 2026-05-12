"""CC-041: Embed and index document chunks into Qdrant."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.chunking import Chunk

logger = logging.getLogger(__name__)

_COLLECTION = "document_chunks"


async def index_document(
    document_id: uuid.UUID,
    care_recipient_id: uuid.UUID,
    chunks: list[Chunk],
    document_name: str,
    document_type: str,
    db: AsyncSession,
) -> int:
    """Embed chunks and upsert into the document_chunks Qdrant collection.

    Returns the number of chunks indexed.
    Updates the document status to 'indexed' on success, 'failed' on error.
    """
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.models import PointStruct, SparseVector

    from app.agent.embeddings import Embedder
    from app.core.config import get_settings
    from sqlalchemy import text

    settings = get_settings()

    if not chunks:
        logger.warning("index_document called with 0 chunks for document %s", document_id)
        return 0

    texts = [c.text for c in chunks]
    embedder = Embedder()

    try:
        vectors = await embedder.embed_texts(texts)
    except Exception as e:
        logger.error("Embedding failed for document %s: %s", document_id, e)
        await _set_status(db, document_id, "failed", str(e))
        raise

    client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

    points: list[PointStruct] = []
    for chunk, vec in zip(chunks, vectors):
        payload: dict[str, Any] = {
            "document_id": str(document_id),
            "care_recipient_id": str(care_recipient_id),
            "document_name": document_name,
            "document_type": document_type,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,
            "section": chunk.section,
            "text": chunk.text,
        }

        sparse = {int(k): float(v) for k, v in vec.sparse.items()}

        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector={
                "dense": vec.dense,
                "sparse": SparseVector(
                    indices=list(sparse.keys()),
                    values=list(sparse.values()),
                ),
            },
            payload=payload,
        ))

    try:
        await client.upsert(collection_name=_COLLECTION, points=points)
        await client.close()
    except Exception as e:
        logger.error("Qdrant upsert failed for document %s: %s", document_id, e)
        await _set_status(db, document_id, "failed", str(e))
        raise

    await _set_status(db, document_id, "indexed")
    logger.info("Indexed %d chunks for document %s", len(chunks), document_id)
    return len(chunks)


async def _set_status(
    db: AsyncSession,
    document_id: uuid.UUID,
    status: str,
    error_msg: str | None = None,
) -> None:
    from sqlalchemy import text

    if error_msg:
        await db.execute(
            text("UPDATE documents SET status = :s, processing_error = :e WHERE id = :id"),
            {"s": status, "e": error_msg[:500], "id": document_id},
        )
    else:
        await db.execute(
            text("UPDATE documents SET status = :s WHERE id = :id"),
            {"s": status, "id": document_id},
        )
    await db.commit()
