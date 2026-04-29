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
