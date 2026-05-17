"""CC-042: Background worker — polls for uploaded documents and processes them.

Run with:  python -m app.ingestion.worker
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.ingestion.chunking import chunk_clinical_document
from app.ingestion.clinical_extraction import extract_clinical_data
from app.ingestion.indexing import index_document
from app.ingestion.pdf_extraction import extract_text_from_bytes

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 30  # seconds


async def process_document(doc_row: dict, db: AsyncSession) -> None:
    """Full pipeline: extract → structure → chunk → index for one document."""
    doc_id = uuid.UUID(str(doc_row["id"]))
    care_recipient_id = uuid.UUID(str(doc_row["care_recipient_id"]))
    document_type = doc_row.get("type") or "other"
    document_name = doc_row.get("file_name") or str(doc_id)
    storage_path = doc_row.get("storage_path") or ""

    logger.info("Processing document %s (%s)", doc_id, document_name)

    # Mark as processing
    await db.execute(
        text("UPDATE documents SET status = 'processing' WHERE id = :id"),
        {"id": doc_id},
    )
    await db.commit()

    try:
        # 1. Fetch file bytes from Supabase Storage
        file_bytes = await _fetch_file(storage_path)

        # 2. Extract text from PDF
        extracted = extract_text_from_bytes(file_bytes, document_name)
        if extracted.is_empty:
            logger.warning("Document %s has no extractable text (possibly scanned)", doc_id)

        # 3. Clinical extraction
        clinical = await extract_clinical_data(extracted.full_text, document_type)

        # 4. Chunk
        chunks = chunk_clinical_document(extracted.full_text)
        if not chunks:
            logger.warning("No chunks produced for document %s", doc_id)
            await db.execute(
                text("UPDATE documents SET status = 'indexed' WHERE id = :id"),
                {"id": doc_id},
            )
            await db.commit()
            return

        # 5. Index into Qdrant
        n = await index_document(
            document_id=doc_id,
            care_recipient_id=care_recipient_id,
            chunks=chunks,
            document_name=document_name,
            document_type=document_type,
            db=db,
        )
        logger.info("Document %s: %d chunks indexed", doc_id, n)

        # 6. Store clinical summary back on document row
        if clinical.summary:
            await db.execute(
                text("UPDATE documents SET summary = :s WHERE id = :id"),
                {"s": clinical.summary, "id": doc_id},
            )
            await db.commit()

    except Exception as e:
        logger.exception("Failed to process document %s: %s", doc_id, e)
        await db.execute(
            text("UPDATE documents SET status = 'failed' WHERE id = :id"),
            {"id": doc_id},
        )
        await db.commit()


async def _fetch_file(storage_path: str) -> bytes:
    """Download file bytes from Supabase Storage."""
    import httpx
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase not configured — cannot fetch document bytes")

    bucket = settings.supabase_storage_bucket
    url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{storage_path}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {settings.supabase_service_role_key}"},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.content


async def run_once(db: AsyncSession) -> int:
    """Process all documents with status='uploaded'. Returns count processed."""
    result = await db.execute(
        text("""
            SELECT id, care_recipient_id, type, original_filename AS file_name, storage_path
            FROM documents
            WHERE status = 'uploaded'
            ORDER BY uploaded_at
            LIMIT 20
        """)
    )
    rows = [dict(r._mapping) for r in result]

    for row in rows:
        await process_document(row, db)

    return len(rows)


async def run_worker() -> None:
    """Main worker loop — polls every POLL_INTERVAL seconds."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Document processing worker started (poll interval: %ds)", _POLL_INTERVAL)

    while True:
        try:
            async with async_session_maker() as db:
                count = await run_once(db)
                if count:
                    logger.info("Processed %d document(s)", count)
        except Exception as e:
            logger.exception("Worker iteration failed: %s", e)

        await asyncio.sleep(_POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_worker())
