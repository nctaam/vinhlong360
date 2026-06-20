-- P1: saved entities (favorites) synced to user account.
-- Run against Postgres prod after backup. Safe to re-run.
CREATE TABLE IF NOT EXISTS saved_entities (
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_id  TEXT NOT NULL,
    snapshot   JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_saved_entities_user ON saved_entities(user_id, created_at DESC);
