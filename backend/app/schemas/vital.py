import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import VitalSource, VitalType


class VitalResponse(BaseModel):
    id: uuid.UUID
    care_recipient_id: uuid.UUID
    type: VitalType
    value_numeric: float | None
    value_systolic: int | None
    value_diastolic: int | None
    value_text: str | None
    unit: str
    recorded_at: datetime
    source: VitalSource
    notes: str | None
    episode_id: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
