import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MedicationSuggestion(BaseModel):
    rxcui: str = Field(..., description="RxNorm Concept Unique Identifier")
    name: str = Field(..., description="Display name of the medication")
    score: float = Field(..., description="Match score from RxNav")


class MedicationCreateRequest(BaseModel):
    display_name: str = Field(..., description="Name of the medication")
    rxnorm_code: str | None = Field(default=None, description="RxNorm CUI")
    rxnorm_name: str | None = Field(default=None, description="RxNorm standardized name")
    
    dose: str | None = Field(default=None, description="Dosage (e.g., 10mg)")
    frequency: str | None = Field(default=None, description="Frequency (e.g., twice daily)")
    route: str | None = Field(default="oral", description="Route of administration")
    
    started_at: date = Field(..., description="When the medication was started")
    stopped_at: date | None = Field(default=None, description="When the medication was stopped")
    stopped_reason: str | None = Field(default=None, description="Reason for stopping")
    
    prescribed_for: str | None = Field(default=None, description="Condition this is prescribed for")
    prescriber: str | None = Field(default=None, description="Name of the prescriber")


class MedicationUpdateRequest(BaseModel):
    dose: str | None = None
    frequency: str | None = None
    route: str | None = None
    stopped_at: date | None = None
    stopped_reason: str | None = None
    prescribed_for: str | None = None
    prescriber: str | None = None


class MedicationResponse(BaseModel):
    id: uuid.UUID
    care_recipient_id: uuid.UUID
    display_name: str
    rxnorm_code: str | None
    rxnorm_name: str | None
    dose: str | None
    frequency: str | None
    route: str | None
    started_at: date
    stopped_at: date | None
    stopped_reason: str | None
    prescribed_for: str | None
    prescriber: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
