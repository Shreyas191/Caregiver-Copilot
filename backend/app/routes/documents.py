"""Document upload and retrieval routes (CC-037)."""

import asyncio
import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, async_session_maker
from app.core.security import get_current_user_id
from app.models.caregiver import Caregiver
from app.models.document import Document
from app.models.enums import DocumentType
from app.schemas.document import DocumentResponse
from app.services.document_service import (
    create_document,
    get_download_url,
    upload_to_supabase,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/care-recipients", tags=["documents"])

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}


@router.post("/{care_recipient_id}/documents", response_model=DocumentResponse)
async def upload_document(
    care_recipient_id: uuid.UUID,
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Upload a document (PDF or image) for a care recipient."""
    # Validate file type
    if file.content_type not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Only PDF and images are accepted.",
        )

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10 MB limit.")

    # Resolve document type enum
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        doc_type = DocumentType.other

    # Lookup caregiver
    result = await db.execute(
        select(Caregiver).where(Caregiver.clerk_user_id == clerk_user_id)
    )
    caregiver = result.scalar_one_or_none()
    if caregiver is None:
        raise HTTPException(status_code=404, detail="Caregiver not found")

    document_id = uuid.uuid4()
    filename = file.filename or f"{document_id}.pdf"

    storage_path = await upload_to_supabase(
        file_content=content,
        filename=filename,
        mime_type=file.content_type,
        care_recipient_id=care_recipient_id,
        document_id=document_id,
    )

    doc = await create_document(
        db=db,
        care_recipient_id=care_recipient_id,
        caregiver_id=caregiver.id,
        filename=filename,
        mime_type=file.content_type,
        file_size=len(content),
        storage_path=storage_path,
        document_type=doc_type,
    )

    await db.commit()

    # Kick off ingestion immediately in the background (don't wait for the polling worker)
    doc_row = {
        "id": doc.id,
        "care_recipient_id": doc.care_recipient_id,
        "type": doc.type.value,
        "file_name": doc.original_filename,
        "storage_path": doc.storage_path,
    }
    asyncio.create_task(_ingest_in_background(doc_row))

    return DocumentResponse(
        id=doc.id,
        care_recipient_id=doc.care_recipient_id,
        document_type=doc.type.value,
        status=doc.status.value,
        original_filename=doc.original_filename,
        file_size_bytes=doc.file_size_bytes,
        download_url=get_download_url(doc.storage_path),
        uploaded_at=doc.uploaded_at,
    )


async def _ingest_in_background(doc_row: dict) -> None:
    """Run the full ingestion pipeline for a single document in a fresh DB session."""
    from app.ingestion.worker import process_document

    try:
        async with async_session_maker() as db:
            await process_document(doc_row, db)
    except Exception:
        logger.exception("Background ingestion failed for document %s", doc_row.get("id"))


@router.get("/{care_recipient_id}/documents/{document_id}/download")
async def download_document(
    care_recipient_id: uuid.UUID,
    document_id: uuid.UUID,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a short-lived signed URL and return it as JSON."""
    row = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.care_recipient_id == care_recipient_id,
        )
    )
    doc = row.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    settings = get_settings()
    if not settings.supabase_url or doc.storage_path.startswith("local/"):
        raise HTTPException(status_code=404, detail="File not available")

    bucket = settings.supabase_storage_bucket
    sign_url = f"{settings.supabase_url}/storage/v1/object/sign/{bucket}/{doc.storage_path}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            sign_url,
            json={"expiresIn": 3600},
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not generate download link")

    signed_path = resp.json().get("signedURL") or resp.json().get("signedUrl", "")
    if not signed_path:
        raise HTTPException(status_code=502, detail="Empty signed URL from Supabase")

    # Supabase returns a relative path like /object/sign/...?token=...
    # The storage REST API lives under /storage/v1, so we must prepend that.
    if signed_path.startswith("http"):
        full_url = signed_path
    elif signed_path.startswith("/object/"):
        full_url = f"{settings.supabase_url}/storage/v1{signed_path}"
    else:
        full_url = f"{settings.supabase_url}{signed_path}"
    return {"url": full_url}


@router.get("/{care_recipient_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    care_recipient_id: uuid.UUID,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """List all documents for a care recipient."""
    rows = (
        await db.execute(
            select(Document)
            .where(Document.care_recipient_id == care_recipient_id)
            .order_by(Document.uploaded_at.desc())
        )
    ).scalars().all()

    return [
        DocumentResponse(
            id=doc.id,
            care_recipient_id=doc.care_recipient_id,
            document_type=doc.type.value,
            status=doc.status.value,
            original_filename=doc.original_filename,
            file_size_bytes=doc.file_size_bytes,
            download_url=get_download_url(doc.storage_path),
            uploaded_at=doc.uploaded_at,
        )
        for doc in rows
    ]
