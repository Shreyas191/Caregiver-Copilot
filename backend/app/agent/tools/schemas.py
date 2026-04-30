"""Pydantic output schemas returned by context-reading tools."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    ConsentBasis,
    EpisodeStatus,
    SexAtBirth,
    UrgencyLevel,
    VitalSource,
    VitalType,
)


class ConditionItem(BaseModel):
    name: str
    icd10_code: str | None = None
    diagnosed_date: str | None = None


class AllergyItem(BaseModel):
    substance: str
    reaction: str | None = None
    severity: str | None = None


class CareRecipientContext(BaseModel):
    id: uuid.UUID
    display_name: str
    date_of_birth: date
    sex_at_birth: SexAtBirth
    conditions: list[ConditionItem] = Field(default_factory=list)
    allergies: list[AllergyItem] = Field(default_factory=list)
    baseline_notes: str | None = None
    primary_provider_name: str | None = None
    primary_provider_email: str | None = None
    primary_provider_phone: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    consent_basis: ConsentBasis


class ActiveMedication(BaseModel):
    id: uuid.UUID
    display_name: str
    rxnorm_code: str | None = None
    rxnorm_name: str | None = None
    dose: str | None = None
    frequency: str | None = None
    route: str | None = None
    started_at: date
    prescribed_for: str | None = None
    prescriber: str | None = None


class VitalReading(BaseModel):
    id: uuid.UUID
    type: VitalType
    value_numeric: float | None = None
    value_systolic: int | None = None
    value_diastolic: int | None = None
    value_text: str | None = None
    unit: str
    recorded_at: datetime
    source: VitalSource
    notes: str | None = None


class EpisodeSummary(BaseModel):
    id: uuid.UUID
    started_at: datetime
    caregiver_description: str
    symptoms: list[dict[str, Any]] = Field(default_factory=list)
    agent_assessment: str | None = None
    urgency_level: UrgencyLevel
    recommended_actions: list[dict[str, Any]] = Field(default_factory=list)
    status: EpisodeStatus
    resolved_at: datetime | None = None
    created_at: datetime
