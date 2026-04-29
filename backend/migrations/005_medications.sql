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
