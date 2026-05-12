-- Migration 014: Add Google OAuth token storage to caregivers
-- Stores the encrypted refresh token for Google Calendar access.

ALTER TABLE caregivers
    ADD COLUMN IF NOT EXISTS google_oauth_token TEXT;

-- DOWN migration:
-- ALTER TABLE caregivers DROP COLUMN IF EXISTS google_oauth_token;
