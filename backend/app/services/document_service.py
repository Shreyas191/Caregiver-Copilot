"""Document upload service (CC-037).

Handles storing uploaded files to Supabase Storage and creating document records.
"""

import uuid
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings
from app.models.document import Document
from app.models.enums import DocumentStatus, DocumentType
from sqlalchemy.ext.asyncio import AsyncSession


async def upload_to_supabase(
    file_content: bytes,
    filename: str,
    mime_type: str,
    care_recipient_id: uuid.UUID,
    document_id: uuid.UUID,
) -> str:
    """Upload a file to Supabase Storage and return the storage path."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        # Fall back to local path when Supabase is not configured
        return f"local/{care_recipient_id}/{document_id}/{filename}"

    bucket = settings.supabase_storage_bucket
    storage_path = f"{care_recipient_id}/{document_id}/{filename}"
    url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{storage_path}"

    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": mime_type,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, content=file_content, headers=headers)
        if response.status_code not in (200, 201):
            raise RuntimeError(f"Supabase upload failed: {response.status_code} {response.text}")

    return storage_path


async def create_document(
    db: AsyncSession,
    care_recipient_id: uuid.UUID,
    caregiver_id: uuid.UUID,
    filename: str,
    mime_type: str,
    file_size: int,
    storage_path: str,
    document_type: DocumentType = DocumentType.other,
) -> Document:
    doc = Document(
        care_recipient_id=care_recipient_id,
        caregiver_id=caregiver_id,
        type=document_type,
        status=DocumentStatus.uploaded,
        original_filename=filename,
        storage_path=storage_path,
        file_size_bytes=file_size,
        mime_type=mime_type,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


def get_download_url(storage_path: str) -> str:
    """Generate a public or signed URL for the stored document."""
    settings = get_settings()
    if not settings.supabase_url or storage_path.startswith("local/"):
        return f"/api/v1/documents/local/{storage_path}"

    bucket = settings.supabase_storage_bucket
    return f"{settings.supabase_url}/storage/v1/object/public/{bucket}/{storage_path}"
