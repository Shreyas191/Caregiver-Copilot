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
