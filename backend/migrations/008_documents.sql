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
