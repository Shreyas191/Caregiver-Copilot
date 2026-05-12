"""Document upload and retrieval routes (CC-037)."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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
