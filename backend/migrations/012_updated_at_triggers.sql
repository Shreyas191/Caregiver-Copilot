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
