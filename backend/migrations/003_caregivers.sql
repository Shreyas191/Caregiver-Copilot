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
