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
