# Architecture Reference

> **Purpose:** This document is the authoritative reference for the project's database schema, RLS policies, triggers, and Qdrant collections. It is the source of truth for tickets CC-008 (schema migrations), CC-009 (RLS policies), and CC-024 (Qdrant collections). Other tickets reference it as needed.
>
> **How to use:** Each section below maps directly to one or more migration files. Copy the SQL into the corresponding `backend/migrations/<NNN>_<name>.sql` file exactly as shown. Do not modify column names, types, defaults, or constraints. Do not add columns that aren't specified here. Do not skip indexes.

---

## Table of Contents

- [1. Migration Order](#1-migration-order)
- [2. Migration 001 — Extensions](#2-migration-001--extensions)
- [3. Migration 002 — Enums](#3-migration-002--enums)
- [4. Migration 003 — Caregivers](#4-migration-003--caregivers)
- [5. Migration 004 — Care Recipients](#5-migration-004--care-recipients)
- [6. Migration 005 — Medications](#6-migration-005--medications)
- [7. Migration 006 — Vitals](#7-migration-006--vitals)
- [8. Migration 007 — Episodes](#8-migration-007--episodes)
- [9. Migration 008 — Documents](#9-migration-008--documents)
- [10. Migration 009 — Provider Messages](#10-migration-009--provider-messages)
- [11. Migration 010 — Conversation](#11-migration-010--conversation)
- [12. Migration 011 — External API Cache](#12-migration-011--external-api-cache)
- [13. Migration 012 — updated_at Triggers](#13-migration-012--updated_at-triggers)
- [14. Migration 013 — RLS Policies](#14-migration-013--rls-policies)
- [15. Qdrant Collections](#15-qdrant-collections)
- [16. Design Notes](#16-design-notes)

---

## 1. Migration Order

Migrations must be applied in this order. Each filename is exact.

| # | Filename | Creates |
|---|---|---|
| 1 | `001_extensions.sql` | Postgres extensions |
| 2 | `002_enums.sql` | All enum types |
| 3 | `003_caregivers.sql` | `caregivers` table |
| 4 | `004_care_recipients.sql` | `care_recipients` table |
| 5 | `005_medications.sql` | `medications` table + `active_medications` view |
| 6 | `006_vitals.sql` | `vitals` table (FK to episodes added later) |
| 7 | `007_episodes.sql` | `episodes` table + ALTER `vitals` to add FK |
| 8 | `008_documents.sql` | `documents` table |
| 9 | `009_provider_messages.sql` | `provider_messages` table |
| 10 | `010_conversation.sql` | `conversation_threads` + `conversation_messages` |
| 11 | `011_external_api_cache.sql` | `external_api_cache` table |
| 12 | `012_updated_at_triggers.sql` | `set_updated_at` function + triggers |
| 13 | `013_rls_policies.sql` | RLS helper function + all policies |

After CC-008 (migrations 002-012) and CC-009 (migration 013), later tickets may add migrations starting at `014_*`.

---

## 2. Migration 001 — Extensions

**File:** `backend/migrations/001_extensions.sql`
**Created in:** CC-003

```sql
-- Required Postgres extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- trigram fuzzy search for medication names
-- Note: pg_audit must be enabled via the Supabase dashboard for managed projects.
-- Document this requirement in docs/setup.md.
```

---

## 3. Migration 002 — Enums

**File:** `backend/migrations/002_enums.sql`
**Created in:** CC-008

```sql
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
```

---

## 4. Migration 003 — Caregivers

**File:** `backend/migrations/003_caregivers.sql`
**Created in:** CC-008

```sql
-- ============================================================
-- caregivers: the user account.
-- Minimal because Clerk owns identity; this is the local mirror.
-- ============================================================

CREATE TABLE caregivers (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clerk_user_id   TEXT NOT NULL UNIQUE,
  display_name    TEXT NOT NULL,
  email           TEXT NOT NULL,
  timezone        TEXT NOT NULL DEFAULT 'America/New_York',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT email_format CHECK (email ~* '^[^@]+@[^@]+\.[^@]+$')
);

-- Lookup by Clerk user ID is the hot path (every authenticated request)
CREATE INDEX idx_caregivers_clerk_user_id ON caregivers(clerk_user_id);
```

---

## 5. Migration 004 — Care Recipients

**File:** `backend/migrations/004_care_recipients.sql`
**Created in:** CC-008

```sql
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
```

**Design notes for this table:**

- `ON DELETE RESTRICT` on the caregiver FK prevents accidental cascade deletes. Use the consent revocation workflow to remove care recipients.
- JSONB with CHECK constraints (`jsonb_typeof = 'array'`) enforces structural correctness without requiring a strict column-per-condition schema.
- Partial indexes filtering on `consent_revoked_at IS NULL` are smaller and faster because most queries care only about active care recipients.

---

## 6. Migration 005 — Medications

**File:** `backend/migrations/005_medications.sql`
**Created in:** CC-008

```sql
-- ============================================================
-- medications: append-only via started_at / stopped_at.
-- Never deleted in normal operation: medication history is
-- clinically meaningful even after the medication is stopped.
-- ============================================================

CREATE TABLE medications (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  care_recipient_id   UUID NOT NULL REFERENCES care_recipients(id) ON DELETE CASCADE,

  -- Identification
  display_name        TEXT NOT NULL,
  rxnorm_code         TEXT,
  rxnorm_name         TEXT,

  -- Dosing
  dose                TEXT,
  frequency           TEXT,
  route               TEXT DEFAULT 'oral',

  -- Lifecycle
  started_at          DATE NOT NULL,
  stopped_at          DATE,
  stopped_reason      TEXT,

  -- Context
  prescribed_for      TEXT,
  prescriber          TEXT,

  -- Audit
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT stopped_after_started CHECK (
    stopped_at IS NULL OR stopped_at >= started_at
  ),
  CONSTRAINT rxnorm_consistency CHECK (
    (rxnorm_code IS NULL AND rxnorm_name IS NULL) OR
    (rxnorm_code IS NOT NULL AND rxnorm_name IS NOT NULL)
  )
);

-- Hot path: "what is this care recipient currently taking?"
CREATE INDEX idx_medications_active
  ON medications(care_recipient_id)
  WHERE stopped_at IS NULL;

-- For drug interaction lookups by RxNorm code
CREATE INDEX idx_medications_rxnorm
  ON medications(rxnorm_code)
  WHERE rxnorm_code IS NOT NULL;

-- Trigram index for medication name search/autocomplete
CREATE INDEX idx_medications_name_trgm
  ON medications USING gin(display_name gin_trgm_ops);

-- Convenience view for active medications (most reads)
CREATE VIEW active_medications AS
  SELECT * FROM medications WHERE stopped_at IS NULL;
```

---

## 7. Migration 006 — Vitals

**File:** `backend/migrations/006_vitals.sql`
**Created in:** CC-008

> **Note:** The FK from `vitals.episode_id → episodes.id` is added in migration 007 (after the `episodes` table exists). The `episode_id` column itself is created here.

```sql
-- ============================================================
-- vitals: discrete measurements over time.
-- Multiple value columns because BP needs systolic/diastolic,
-- "irregular" pulse is text, and most other vitals are a single
-- numeric value with a unit.
-- ============================================================

CREATE TABLE vitals (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  care_recipient_id   UUID NOT NULL REFERENCES care_recipients(id) ON DELETE CASCADE,

  type                vital_type NOT NULL,

  -- Values: at least one of these must be set
  value_numeric       NUMERIC(10, 2),
  value_systolic      INTEGER,
  value_diastolic     INTEGER,
  value_text          TEXT,
  unit                TEXT NOT NULL,

  -- Provenance
  recorded_at         TIMESTAMPTZ NOT NULL,
  source              vital_source NOT NULL DEFAULT 'manual',
  source_document_id  UUID,
  notes               TEXT,

  -- Linked context (FK constraint added in migration 007)
  episode_id          UUID,

  -- Audit
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Must have some value
  CONSTRAINT vital_has_value CHECK (
    value_numeric IS NOT NULL OR
    (value_systolic IS NOT NULL AND value_diastolic IS NOT NULL) OR
    value_text IS NOT NULL
  ),

  -- Blood pressure must have both systolic and diastolic
  CONSTRAINT bp_has_both_components CHECK (
    type != 'blood_pressure' OR
    (value_systolic IS NOT NULL AND value_diastolic IS NOT NULL)
  ),

  -- Realistic ranges
  CONSTRAINT bp_systolic_realistic CHECK (
    value_systolic IS NULL OR (value_systolic BETWEEN 40 AND 300)
  ),
  CONSTRAINT bp_diastolic_realistic CHECK (
    value_diastolic IS NULL OR (value_diastolic BETWEEN 20 AND 200)
  )
);

-- Hot path: time series for a specific vital type
CREATE INDEX idx_vitals_recipient_type_time
  ON vitals(care_recipient_id, type, recorded_at DESC);

-- Hot path: timeline view (all vitals chronologically)
CREATE INDEX idx_vitals_recipient_time
  ON vitals(care_recipient_id, recorded_at DESC);
```

---

## 8. Migration 007 — Episodes

**File:** `backend/migrations/007_episodes.sql`
**Created in:** CC-008

```sql
-- ============================================================
-- episodes: the core clinical event record.
-- Every concerning event becomes one row. Drives the timeline
-- view and is the primary unit of audit/replay.
-- ============================================================

CREATE TABLE episodes (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  care_recipient_id        UUID NOT NULL REFERENCES care_recipients(id) ON DELETE CASCADE,

  -- When and how it started
  started_at               TIMESTAMPTZ NOT NULL,
  caregiver_description    TEXT NOT NULL,

  -- Agent assessment
  -- symptoms shape: [{"symptom": "confusion", "severity": "moderate", "first_noticed": "this morning"}]
  symptoms                 JSONB NOT NULL DEFAULT '[]'::jsonb,

  agent_assessment         TEXT,
  urgency_level            urgency_level NOT NULL,

  -- recommended_actions shape: [{"action": "Recheck BP in 2 hours", "deadline": "2026-04-29T13:00:00Z"}]
  recommended_actions      JSONB NOT NULL DEFAULT '[]'::jsonb,

  -- citations shape: [{"type": "drug_interaction", "source": "RxNav", "claim": "..."}]
  citations                JSONB NOT NULL DEFAULT '[]'::jsonb,

  -- Status lifecycle
  status                   episode_status NOT NULL DEFAULT 'open',
  resolved_at              TIMESTAMPTZ,
  resolution_notes         TEXT,

  -- Audit
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT resolved_at_after_started CHECK (
    resolved_at IS NULL OR resolved_at >= started_at
  ),
  CONSTRAINT resolved_status_has_timestamp CHECK (
    (status = 'resolved') = (resolved_at IS NOT NULL)
  ),
  CONSTRAINT symptoms_is_array CHECK (jsonb_typeof(symptoms) = 'array'),
  CONSTRAINT recommended_actions_is_array CHECK (jsonb_typeof(recommended_actions) = 'array'),
  CONSTRAINT citations_is_array CHECK (jsonb_typeof(citations) = 'array')
);

-- Now add the FK from vitals back to episodes (forward reference resolved)
ALTER TABLE vitals
  ADD CONSTRAINT fk_vitals_episode
  FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE SET NULL;

-- Hot path: timeline view shows recent episodes
CREATE INDEX idx_episodes_recipient_time
  ON episodes(care_recipient_id, started_at DESC);

-- Open episodes need fast lookup for proactive follow-ups
CREATE INDEX idx_episodes_open
  ON episodes(care_recipient_id, started_at DESC)
  WHERE status IN ('open', 'monitoring');

-- Urgent episodes for admin alerts
CREATE INDEX idx_episodes_urgent
  ON episodes(care_recipient_id, started_at DESC)
  WHERE urgency_level IN ('urgent', 'emergency');
```

---

## 9. Migration 008 — Documents

**File:** `backend/migrations/008_documents.sql`
**Created in:** CC-008

```sql
-- ============================================================
-- documents: uploaded clinical documents (PDFs).
-- Lifecycle: uploaded → processing → indexed (or failed).
-- ============================================================

CREATE TABLE documents (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  care_recipient_id   UUID NOT NULL REFERENCES care_recipients(id) ON DELETE CASCADE,
  caregiver_id        UUID NOT NULL REFERENCES caregivers(id),

  type                document_type NOT NULL,
  status              document_status NOT NULL DEFAULT 'uploaded',

  -- Storage (Supabase Storage)
  original_filename   TEXT NOT NULL,
  storage_path        TEXT NOT NULL,
  file_size_bytes     BIGINT NOT NULL,
  mime_type           TEXT NOT NULL,

  -- Processing results
  document_date       DATE,
  page_count          INTEGER,
  extraction_method   TEXT,
  extracted_text      TEXT,

  -- extracted_data shape varies by document_type. Examples:
  -- lab_report:        {"lab_values": [{"name": "Glucose", "value": 145, "unit": "mg/dL", "ref_range": "70-100"}]}
  -- discharge_summary: {"assessment": "...", "plan": "...", "medications": [...]}
  extracted_data      JSONB DEFAULT '{}'::jsonb,

  -- Errors
  processing_error    TEXT,

  -- Audit
  uploaded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  indexed_at          TIMESTAMPTZ,

  CONSTRAINT file_size_positive CHECK (file_size_bytes > 0),
  CONSTRAINT indexed_implies_indexed_at CHECK (
    (status = 'indexed') = (indexed_at IS NOT NULL)
  )
);

-- Hot path: documents by recipient and type
CREATE INDEX idx_documents_recipient_type
  ON documents(care_recipient_id, type);

-- Worker poll: documents needing processing
CREATE INDEX idx_documents_status
  ON documents(status)
  WHERE status IN ('uploaded', 'processing');
```

---

## 10. Migration 009 — Provider Messages

**File:** `backend/migrations/009_provider_messages.sql`
**Created in:** CC-008

```sql
-- ============================================================
-- provider_messages: drafted communications to the PCP.
-- Always tied to an episode for traceability.
-- ============================================================

CREATE TABLE provider_messages (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  episode_id      UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,

  recipient_name  TEXT NOT NULL,
  recipient_email TEXT,
  recipient_phone TEXT,

  subject         TEXT NOT NULL,
  draft_content   TEXT NOT NULL,

  status          provider_message_status NOT NULL DEFAULT 'draft',
  sent_at         TIMESTAMPTZ,
  sent_via        TEXT,

  -- Audit
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT sent_status_has_timestamp CHECK (
    (status = 'sent') = (sent_at IS NOT NULL)
  )
);

CREATE INDEX idx_provider_messages_episode
  ON provider_messages(episode_id);
```

---

## 11. Migration 010 — Conversation

**File:** `backend/migrations/010_conversation.sql`
**Created in:** CC-008

```sql
-- ============================================================
-- conversation_threads: one thread per chat conversation.
-- Multiple threads can exist per care recipient.
-- ============================================================

CREATE TABLE conversation_threads (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  caregiver_id        UUID NOT NULL REFERENCES caregivers(id) ON DELETE CASCADE,
  care_recipient_id   UUID NOT NULL REFERENCES care_recipients(id) ON DELETE CASCADE,
  title               TEXT,

  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_threads_recipient_recent
  ON conversation_threads(care_recipient_id, updated_at DESC);

-- ============================================================
-- conversation_messages: every turn captured with full audit.
-- This is the primary observability table — one row per message
-- with intent, tool calls, retrieved context, verifier output,
-- and performance metrics.
-- ============================================================

CREATE TABLE conversation_messages (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id           UUID NOT NULL REFERENCES conversation_threads(id) ON DELETE CASCADE,
  caregiver_id        UUID NOT NULL REFERENCES caregivers(id),
  care_recipient_id   UUID NOT NULL REFERENCES care_recipients(id),

  role                message_role NOT NULL,
  content             TEXT NOT NULL,

  -- Routing classification (only on user messages)
  intent              message_intent,
  intent_confidence   NUMERIC(4, 3),

  -- tool_calls shape (assistant messages):
  -- [{"tool": "check_drug_interactions", "input": {...}, "output": {...}, "duration_ms": 234}]
  tool_calls          JSONB DEFAULT '[]'::jsonb,

  -- retrieved_context shape:
  -- [{"collection": "drug_label_chunks", "chunk_id": "...", "score": 0.87, "text": "..."}]
  retrieved_context   JSONB DEFAULT '[]'::jsonb,

  -- Verifier output (assistant messages that went through verification)
  verifier_passed     BOOLEAN,
  verifier_severity   verifier_severity,
  verifier_issues     JSONB DEFAULT '[]'::jsonb,
  regeneration_count  INTEGER NOT NULL DEFAULT 0,

  -- Linked clinical artifacts
  episode_id          UUID REFERENCES episodes(id) ON DELETE SET NULL,

  -- Performance
  model_used          TEXT,
  tokens_input        INTEGER,
  tokens_output       INTEGER,
  latency_ms          INTEGER,

  -- Audit
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT intent_only_on_user_messages CHECK (
    (role = 'user') OR (intent IS NULL AND intent_confidence IS NULL)
  ),
  CONSTRAINT confidence_range CHECK (
    intent_confidence IS NULL OR (intent_confidence >= 0 AND intent_confidence <= 1)
  ),
  CONSTRAINT regeneration_count_nonneg CHECK (regeneration_count >= 0),
  CONSTRAINT tool_calls_is_array CHECK (jsonb_typeof(tool_calls) = 'array'),
  CONSTRAINT retrieved_context_is_array CHECK (jsonb_typeof(retrieved_context) = 'array'),
  CONSTRAINT verifier_issues_is_array CHECK (jsonb_typeof(verifier_issues) = 'array')
);

-- Hot path: chat history for a thread
CREATE INDEX idx_messages_thread_time
  ON conversation_messages(thread_id, created_at);

-- Recent messages for a care recipient
CREATE INDEX idx_messages_recipient_time
  ON conversation_messages(care_recipient_id, created_at DESC);

-- Observability: find verifier failures
CREATE INDEX idx_messages_verifier_failures
  ON conversation_messages(created_at DESC)
  WHERE verifier_passed = false;
```

---

## 12. Migration 011 — External API Cache

**File:** `backend/migrations/011_external_api_cache.sql`
**Created in:** CC-008

```sql
-- ============================================================
-- external_api_cache: shared cache for RxNav, OpenFDA, etc.
-- System-wide (no per-caregiver scoping) because these
-- responses contain no PHI and benefit from cross-user caching.
-- ============================================================

CREATE TABLE external_api_cache (
  cache_key       TEXT PRIMARY KEY,
  service         TEXT NOT NULL,
  response_data   JSONB NOT NULL,
  expires_at      TIMESTAMPTZ NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- For periodic cache eviction
CREATE INDEX idx_cache_expires ON external_api_cache(expires_at);
```

---

## 13. Migration 012 — updated_at Triggers

**File:** `backend/migrations/012_updated_at_triggers.sql`
**Created in:** CC-008

```sql
-- ============================================================
-- set_updated_at: trigger function to maintain updated_at.
-- Applied to every table with an updated_at column.
-- ============================================================

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_caregivers_updated_at
  BEFORE UPDATE ON caregivers
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_care_recipients_updated_at
  BEFORE UPDATE ON care_recipients
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_medications_updated_at
  BEFORE UPDATE ON medications
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_episodes_updated_at
  BEFORE UPDATE ON episodes
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_provider_messages_updated_at
  BEFORE UPDATE ON provider_messages
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_conversation_threads_updated_at
  BEFORE UPDATE ON conversation_threads
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

> **Note:** `vitals`, `documents`, `conversation_messages`, and `external_api_cache` do not have `updated_at` columns and therefore do not get this trigger. They are append-only or have type-specific lifecycle columns instead.

---

## 14. Migration 013 — RLS Policies

**File:** `backend/migrations/013_rls_policies.sql`
**Created in:** CC-009

```sql
-- ============================================================
-- Row-Level Security: enforce caregiver → care_recipient
-- ownership at the database layer.
--
-- Pattern:
--   1. Helper function reads Clerk user ID from JWT.
--   2. Each table's policy filters via the ownership chain.
--
-- The RLS context is set per-session by the application via
-- SET LOCAL request.jwt.claims = '{"sub": "<clerk_id>"}'.
-- See backend/app/core/database.py.
-- ============================================================

-- Helper function: returns the current caregiver's UUID
CREATE OR REPLACE FUNCTION current_caregiver_id() RETURNS UUID AS $$
  SELECT id FROM caregivers
  WHERE clerk_user_id = (
    current_setting('request.jwt.claims', true)::json ->> 'sub'
  );
$$ LANGUAGE SQL STABLE;

-- ============================================================
-- Enable RLS on every clinical table
-- ============================================================
ALTER TABLE caregivers              ENABLE ROW LEVEL SECURITY;
ALTER TABLE care_recipients         ENABLE ROW LEVEL SECURITY;
ALTER TABLE medications             ENABLE ROW LEVEL SECURITY;
ALTER TABLE vitals                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodes                ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents               ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_messages       ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_threads    ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages   ENABLE ROW LEVEL SECURITY;

-- Note: external_api_cache does NOT have RLS enabled.
-- It contains no PHI and is read/written by all authenticated users.

-- ============================================================
-- caregivers: each caregiver sees only their own row
-- ============================================================
CREATE POLICY caregiver_self_access ON caregivers
  FOR ALL
  USING (
    clerk_user_id = (current_setting('request.jwt.claims', true)::json ->> 'sub')
  )
  WITH CHECK (
    clerk_user_id = (current_setting('request.jwt.claims', true)::json ->> 'sub')
  );

-- ============================================================
-- care_recipients: caregiver-owned and not consent-revoked
-- ============================================================
CREATE POLICY care_recipients_owned ON care_recipients
  FOR ALL
  USING (
    caregiver_id = current_caregiver_id()
    AND consent_revoked_at IS NULL
  )
  WITH CHECK (
    caregiver_id = current_caregiver_id()
  );

-- ============================================================
-- medications: filter via care_recipient ownership chain
-- ============================================================
CREATE POLICY medications_via_care_recipient ON medications
  FOR ALL
  USING (
    care_recipient_id IN (
      SELECT id FROM care_recipients
      WHERE caregiver_id = current_caregiver_id()
        AND consent_revoked_at IS NULL
    )
  )
  WITH CHECK (
    care_recipient_id IN (
      SELECT id FROM care_recipients
      WHERE caregiver_id = current_caregiver_id()
        AND consent_revoked_at IS NULL
    )
  );

-- ============================================================
-- vitals: same pattern
-- ============================================================
CREATE POLICY vitals_via_care_recipient ON vitals
  FOR ALL
  USING (
    care_recipient_id IN (
      SELECT id FROM care_recipients
      WHERE caregiver_id = current_caregiver_id()
        AND consent_revoked_at IS NULL
    )
  )
  WITH CHECK (
    care_recipient_id IN (
      SELECT id FROM care_recipients
      WHERE caregiver_id = current_caregiver_id()
        AND consent_revoked_at IS NULL
    )
  );

-- ============================================================
-- episodes: same pattern
-- ============================================================
CREATE POLICY episodes_via_care_recipient ON episodes
  FOR ALL
  USING (
    care_recipient_id IN (
      SELECT id FROM care_recipients
      WHERE caregiver_id = current_caregiver_id()
        AND consent_revoked_at IS NULL
    )
  )
  WITH CHECK (
    care_recipient_id IN (
      SELECT id FROM care_recipients
      WHERE caregiver_id = current_caregiver_id()
        AND consent_revoked_at IS NULL
    )
  );

-- ============================================================
-- documents: same pattern
-- ============================================================
CREATE POLICY documents_via_care_recipient ON documents
  FOR ALL
  USING (
    care_recipient_id IN (
      SELECT id FROM care_recipients
      WHERE caregiver_id = current_caregiver_id()
        AND consent_revoked_at IS NULL
    )
  )
  WITH CHECK (
    care_recipient_id IN (
      SELECT id FROM care_recipients
      WHERE caregiver_id = current_caregiver_id()
        AND consent_revoked_at IS NULL
    )
  );

-- ============================================================
-- provider_messages: filter via episode → care_recipient
-- ============================================================
CREATE POLICY provider_messages_via_episode ON provider_messages
  FOR ALL
  USING (
    episode_id IN (
      SELECT e.id FROM episodes e
      JOIN care_recipients cr ON cr.id = e.care_recipient_id
      WHERE cr.caregiver_id = current_caregiver_id()
        AND cr.consent_revoked_at IS NULL
    )
  )
  WITH CHECK (
    episode_id IN (
      SELECT e.id FROM episodes e
      JOIN care_recipients cr ON cr.id = e.care_recipient_id
      WHERE cr.caregiver_id = current_caregiver_id()
        AND cr.consent_revoked_at IS NULL
    )
  );

-- ============================================================
-- conversation_threads: filter via care_recipient ownership
-- ============================================================
CREATE POLICY conversation_threads_via_care_recipient ON conversation_threads
  FOR ALL
  USING (
    care_recipient_id IN (
      SELECT id FROM care_recipients
      WHERE caregiver_id = current_caregiver_id()
        AND consent_revoked_at IS NULL
    )
  )
  WITH CHECK (
    care_recipient_id IN (
      SELECT id FROM care_recipients
      WHERE caregiver_id = current_caregiver_id()
        AND consent_revoked_at IS NULL
    )
  );

-- ============================================================
-- conversation_messages: same pattern
-- ============================================================
CREATE POLICY conversation_messages_via_care_recipient ON conversation_messages
  FOR ALL
  USING (
    care_recipient_id IN (
      SELECT id FROM care_recipients
      WHERE caregiver_id = current_caregiver_id()
        AND consent_revoked_at IS NULL
    )
  )
  WITH CHECK (
    care_recipient_id IN (
      SELECT id FROM care_recipients
      WHERE caregiver_id = current_caregiver_id()
        AND consent_revoked_at IS NULL
    )
  );
```

### Verifying RLS works

After applying this migration, manually test with `psql`:

```sql
-- Create two caregivers and care recipients
INSERT INTO caregivers (clerk_user_id, display_name, email)
  VALUES ('user_a', 'User A', 'a@example.com'), ('user_b', 'User B', 'b@example.com');

-- (Insert one care_recipient for each caregiver)

-- Set context as user A
SET request.jwt.claims = '{"sub": "user_a"}';

-- Should return only A's care recipient
SELECT id, display_name FROM care_recipients;

-- Switch to user B
SET request.jwt.claims = '{"sub": "user_b"}';

-- Should return only B's care recipient
SELECT id, display_name FROM care_recipients;

-- Without context, should return zero rows
RESET request.jwt.claims;
SELECT id, display_name FROM care_recipients;
```

---

## 15. Qdrant Collections

**Created in:** CC-024

Three collections, all initialized via the script `backend/scripts/init_qdrant.py`. The script must be idempotent — re-running it must not duplicate or error.

### 15.1 `document_chunks`

Chunked text from uploaded clinical documents. Used for retrieval-augmented generation when the agent needs to reference past lab values, discharge instructions, etc.

```python
COLLECTION_NAME = "document_chunks"

# Vector configuration
vectors_config = {
    "dense": VectorParams(size=1024, distance=Distance.COSINE),
}
sparse_vectors_config = {
    "sparse": SparseVectorParams(),
}

# Payload schema (every point must have these fields):
# {
#   "care_recipient_id": str,    # MANDATORY filter on every query
#   "document_id": str,
#   "document_type": str,        # "lab_report" | "discharge_summary" | ...
#   "chunk_index": int,
#   "page_number": int,
#   "section": str,              # "assessment" | "plan" | "medications" | ...
#   "document_date": str,        # ISO date "YYYY-MM-DD"
# }

# Required payload index for fast filtering
client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="care_recipient_id",
    field_schema=PayloadSchemaType.KEYWORD,
)
```

### 15.2 `episode_chunks`

Episode descriptions and assessments. Used to retrieve semantically similar past events ("last time mom was confused, here's what happened").

```python
COLLECTION_NAME = "episode_chunks"

vectors_config = {
    "dense": VectorParams(size=1024, distance=Distance.COSINE),
}
sparse_vectors_config = {
    "sparse": SparseVectorParams(),
}

# Payload schema:
# {
#   "care_recipient_id": str,    # MANDATORY filter
#   "episode_id": str,
#   "started_at": str,           # ISO timestamp
#   "urgency_level": str,
# }

client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="care_recipient_id",
    field_schema=PayloadSchemaType.KEYWORD,
)
```

### 15.3 `drug_label_chunks`

Sections of OpenFDA drug labels for medications appearing in users' active medication lists. **System-wide collection** (no per-care-recipient filter) because drug label content contains no PHI.

```python
COLLECTION_NAME = "drug_label_chunks"

vectors_config = {
    "dense": VectorParams(size=1024, distance=Distance.COSINE),
}
# Note: dense-only for this collection. Drug label search benefits less
# from sparse retrieval because users query with structured medical terms.

# Payload schema:
# {
#   "rxnorm_code": str,
#   "drug_name": str,
#   "section": str,              # "warnings" | "side_effects" | "dosage" | "contraindications"
#   "source": str,               # "openfda"
# }

client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="rxnorm_code",
    field_schema=PayloadSchemaType.KEYWORD,
)
```

### 15.4 Mandatory query rules

The repository layer in `backend/app/agent/retrieval.py` (CC-025) **must** enforce:

1. Every query against `document_chunks` includes a `care_recipient_id` filter.
2. Every query against `episode_chunks` includes a `care_recipient_id` filter.
3. Queries that omit the required filter raise `ValueError` before reaching Qdrant.

This is a defense-in-depth measure to prevent cross-recipient data leaks even if RLS context is misconfigured elsewhere.

### 15.5 Qdrant deletion on consent revocation

When a care recipient's consent is revoked, the application must delete all Qdrant payloads with that `care_recipient_id` from `document_chunks` and `episode_chunks`. Postgres cascade deletes do not extend to Qdrant; this must be done explicitly in application code.

---

## 16. Design Notes

A few choices that aren't obvious from the SQL alone:

**Why JSONB for `conditions`, `allergies`, `symptoms`, etc.?**
These lists are unbounded and their internal shape may evolve. JSONB with `jsonb_typeof = 'array'` CHECK constraints enforces structural correctness at the type level while leaving the inner schema flexible. A future migration can tighten this with formal JSON Schema validation if needed.

**Why no soft-delete column on most tables?**
Care recipients use `consent_revoked_at` (semantic). Medications use `stopped_at` (semantic — drugs aren't "deleted," they're stopped). Most clinical tables use `ON DELETE CASCADE` from `care_recipients` so the consent revocation workflow handles cleanup. Adding generic soft-delete would be redundant.

**Why partial indexes everywhere?**
Most queries care only about active records (active care recipients, active medications, open episodes). Partial indexes are smaller and faster than full indexes for these access patterns. The cost is one extra index per "active vs. all" query distinction, which is well worth it.

**Why are `tool_calls` and `retrieved_context` JSONB rather than separate tables?**
They are tightly bound to the conversation message that produced them — no other entity references them, and they are read together. Splitting them out would add joins to every chat history query without semantic benefit. JSONB with shape conventions is the right choice.

**Why `RESTRICT` on `caregivers → care_recipients` but `CASCADE` everywhere else?**
Deleting a caregiver should never silently delete a care recipient's clinical history. The correct workflow is to revoke consent on each care recipient, run the deletion job, and only then delete the caregiver. Cascade from caregiver to care recipient would bypass this safeguard. From care recipient downward, cascade is correct because the care recipient is the ownership root of clinical data.

**Why does `conversation_messages` have no `updated_at`?**
Messages are append-only. A user message, once sent, is immutable. An assistant message, once produced, is immutable — regenerations create new messages, they don't update old ones. Removing `updated_at` makes this invariant structural rather than enforced by convention.

**Why is `external_api_cache` outside RLS?**
Drug label data and drug-drug interaction data contain no PHI. Caching it system-wide (rather than per-caregiver) means one cache hit serves all users querying the same drug. RLS would prevent this benefit without adding security value.

---

*End of architecture reference. For higher-level design (system overview, data flows, agent pipeline), see the design document `caregiver_copilot_design.docx`.*
