-- ============================================================
-- Enums: fixed clinical and system vocabularies.
-- Adding a value requires a new migration (correct: changing
-- the set of valid urgency levels is a clinical decision).
-- ============================================================

-- Demographics
CREATE TYPE sex_at_birth AS ENUM (
  'male',
  'female',
  'intersex',
  'unknown'
);

-- Consent: how does this caregiver have authority over this care recipient's data
CREATE TYPE consent_basis AS ENUM (
  'power_of_attorney',
  'healthcare_proxy',
  'parental_responsibility',
  'informal_arrangement',
  'self'
);

-- Vital types
CREATE TYPE vital_type AS ENUM (
  'blood_pressure',
  'heart_rate',
  'glucose',
  'weight',
  'temperature',
  'oxygen_saturation',
  'respiratory_rate',
  'pain_score'
);

-- Source of a vital reading
CREATE TYPE vital_source AS ENUM (
  'manual',
  'device',
  'from_visit',
  'from_document'
);

-- Urgency rubric: emergency > urgent > same_day > routine
CREATE TYPE urgency_level AS ENUM (
  'routine',
  'same_day',
  'urgent',
  'emergency'
);

-- Episode lifecycle
CREATE TYPE episode_status AS ENUM (
  'open',
  'monitoring',
  'resolved',
  'escalated'
);

-- Document classification
CREATE TYPE document_type AS ENUM (
  'lab_report',
  'discharge_summary',
  'after_visit_summary',
  'imaging_report',
  'prescription',
  'insurance_card',
  'other'
);

-- Document processing status
CREATE TYPE document_status AS ENUM (
  'uploaded',
  'processing',
  'indexed',
  'failed'
);

-- Conversation message role
CREATE TYPE message_role AS ENUM (
  'user',
  'assistant',
  'tool',
  'system'
);

-- Router intent classification
CREATE TYPE message_intent AS ENUM (
  'casual_chat',
  'vital_logging',
  'symptom_report',
  'medication_question',
  'document_question',
  'escalation',
  'unknown'
);

-- Verifier severity rating
CREATE TYPE verifier_severity AS ENUM (
  'none',
  'low',
  'medium',
  'high'
);

-- Provider message lifecycle
CREATE TYPE provider_message_status AS ENUM (
  'draft',
  'sent',
  'archived'
);
