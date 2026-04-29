-- ============================================================
-- conversation_threads: one thread per chat conversation.
-- Multiple threads can exist per care recipient.
-- ============================================================

CREATE TABLE conversation_threads (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  caregiver_id        UUID NOT NULL REFERENCES caregivers(id) ON DELETE CASCADE,
  care_recipient_id   UUID NOT NULL REFERENCES care_recipients(id) ON DELETE CASCADE,
  title               TEXT,

  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_threads_recipient_recent
  ON conversation_threads(care_recipient_id, updated_at DESC);

-- ============================================================
-- conversation_messages: every turn captured with full audit.
-- This is the primary observability table — one row per message
-- with intent, tool calls, retrieved context, verifier output,
-- and performance metrics.
-- ============================================================

CREATE TABLE conversation_messages (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id           UUID NOT NULL REFERENCES conversation_threads(id) ON DELETE CASCADE,
  caregiver_id        UUID NOT NULL REFERENCES caregivers(id),
  care_recipient_id   UUID NOT NULL REFERENCES care_recipients(id),

  role                message_role NOT NULL,
  content             TEXT NOT NULL,

  -- Routing classification (only on user messages)
  intent              message_intent,
  intent_confidence   NUMERIC(4, 3),

  -- tool_calls shape (assistant messages):
  -- [{"tool": "check_drug_interactions", "input": {...}, "output": {...}, "duration_ms": 234}]
  tool_calls          JSONB DEFAULT '[]'::jsonb,

  -- retrieved_context shape:
  -- [{"collection": "drug_label_chunks", "chunk_id": "...", "score": 0.87, "text": "..."}]
  retrieved_context   JSONB DEFAULT '[]'::jsonb,

  -- Verifier output (assistant messages that went through verification)
  verifier_passed     BOOLEAN,
  verifier_severity   verifier_severity,
  verifier_issues     JSONB DEFAULT '[]'::jsonb,
  regeneration_count  INTEGER NOT NULL DEFAULT 0,

  -- Linked clinical artifacts
  episode_id          UUID REFERENCES episodes(id) ON DELETE SET NULL,

  -- Performance
  model_used          TEXT,
  tokens_input        INTEGER,
  tokens_output       INTEGER,
  latency_ms          INTEGER,

  -- Audit
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT intent_only_on_user_messages CHECK (
    (role = 'user') OR (intent IS NULL AND intent_confidence IS NULL)
  ),
  CONSTRAINT confidence_range CHECK (
    intent_confidence IS NULL OR (intent_confidence >= 0 AND intent_confidence <= 1)
  ),
  CONSTRAINT regeneration_count_nonneg CHECK (regeneration_count >= 0),
  CONSTRAINT tool_calls_is_array CHECK (jsonb_typeof(tool_calls) = 'array'),
  CONSTRAINT retrieved_context_is_array CHECK (jsonb_typeof(retrieved_context) = 'array'),
  CONSTRAINT verifier_issues_is_array CHECK (jsonb_typeof(verifier_issues) = 'array')
);

-- Hot path: chat history for a thread
CREATE INDEX idx_messages_thread_time
  ON conversation_messages(thread_id, created_at);

-- Recent messages for a care recipient
CREATE INDEX idx_messages_recipient_time
  ON conversation_messages(care_recipient_id, created_at DESC);

-- Observability: find verifier failures
CREATE INDEX idx_messages_verifier_failures
  ON conversation_messages(created_at DESC)
  WHERE verifier_passed = false;
