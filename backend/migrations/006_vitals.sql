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
