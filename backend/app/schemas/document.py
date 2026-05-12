"""Document Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    care_recipient_id: uuid.UUID
    document_type: str
    status: str
    original_filename: str
    file_size_bytes: int
    download_url: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}
