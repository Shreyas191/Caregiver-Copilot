import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConsentBasis, SexAtBirth


class ConditionSchema(BaseModel):
    name: str = Field(..., description="The name of the condition")
    icd10_code: str | None = Field(default=None, description="Optional ICD-10 code")
    diagnosed_date: str | None = Field(default=None, description="When the condition was diagnosed (e.g., YYYY or YYYY-MM-DD)")


class AllergySchema(BaseModel):
    substance: str = Field(..., description="The substance the recipient is allergic to")
    reaction: str | None = Field(default=None, description="The reaction to the allergen")
    severity: str | None = Field(default=None, description="Severity of the allergy (e.g., mild, moderate, severe)")


class CareRecipientCreateRequest(BaseModel):
    display_name: str = Field(..., description="Full name of the care recipient")
    date_of_birth: date = Field(..., description="Date of birth")
    sex_at_birth: SexAtBirth = Field(..., description="Sex assigned at birth")
    
    conditions: list[ConditionSchema] = Field(default_factory=list, description="Known medical conditions")
    allergies: list[AllergySchema] = Field(default_factory=list, description="Known allergies")
    
    baseline_notes: str | None = Field(default=None, description="General baseline notes or context")
    
    primary_provider_name: str | None = Field(default=None, description="PCP name")
    primary_provider_email: str | None = Field(default=None, description="PCP email")
    primary_provider_phone: str | None = Field(default=None, description="PCP phone number")
    
    emergency_contact_name: str | None = Field(default=None, description="Emergency contact name")
    emergency_contact_phone: str | None = Field(default=None, description="Emergency contact phone")
    
    consent_basis: ConsentBasis = Field(..., description="Basis for proxy access")


class CareRecipientResponse(BaseModel):
    id: uuid.UUID
    caregiver_id: uuid.UUID
    display_name: str
    date_of_birth: date
    sex_at_birth: SexAtBirth
    conditions: list[ConditionSchema]
    allergies: list[AllergySchema]
    baseline_notes: str | None
    primary_provider_name: str | None
    primary_provider_email: str | None
    primary_provider_phone: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    consent_basis: ConsentBasis
    consent_documented_at: datetime
    consent_revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
