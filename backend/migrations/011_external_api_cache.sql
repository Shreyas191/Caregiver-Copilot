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
