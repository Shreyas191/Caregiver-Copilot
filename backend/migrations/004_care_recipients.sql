-- ============================================================
-- care_recipients: the person being cared for.
-- This is the ownership root for all clinical data.
-- ============================================================

CREATE TABLE care_recipients (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  caregiver_id             UUID NOT NULL REFERENCES caregivers(id) ON DELETE RESTRICT,

  -- Identity
  display_name             TEXT NOT NULL,
  date_of_birth            DATE NOT NULL,
  sex_at_birth             sex_at_birth NOT NULL,

  -- Clinical baseline
  -- conditions shape: [{"name": "Type 2 diabetes", "icd10": "E11.9", "diagnosed_date": "2018-03-12"}]
  conditions               JSONB NOT NULL DEFAULT '[]'::jsonb,

  -- allergies shape: [{"substance": "penicillin", "reaction": "rash", "severity": "moderate"}]
  allergies                JSONB NOT NULL DEFAULT '[]'::jsonb,

  -- Free text describing usual cognitive/physical state
  baseline_notes           TEXT,

  -- Provider info
  primary_provider_name    TEXT,
  primary_provider_email   TEXT,
  primary_provider_phone   TEXT,
  emergency_contact_name   TEXT,
  emergency_contact_phone  TEXT,

  -- Consent: caregiver as steward, not owner
  consent_basis            consent_basis NOT NULL,
  consent_documented_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  consent_revoked_at       TIMESTAMPTZ,

  -- Audit
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Invariants
  CONSTRAINT dob_realistic CHECK (
    date_of_birth > '1900-01-01' AND date_of_birth <= CURRENT_DATE
  ),
  CONSTRAINT consent_revocation_after_documented CHECK (
    consent_revoked_at IS NULL OR consent_revoked_at >= consent_documented_at
  ),
  CONSTRAINT conditions_is_array CHECK (jsonb_typeof(conditions) = 'array'),
  CONSTRAINT allergies_is_array CHECK (jsonb_typeof(allergies) = 'array')
);

-- Most queries scope to active care recipients owned by a caregiver
CREATE INDEX idx_care_recipients_caregiver
  ON care_recipients(caregiver_id)
  WHERE consent_revoked_at IS NULL;

-- Active care recipient lookup
CREATE INDEX idx_care_recipients_active
  ON care_recipients(id)
  WHERE consent_revoked_at IS NULL;
