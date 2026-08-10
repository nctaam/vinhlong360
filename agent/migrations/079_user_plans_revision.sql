-- Migration authority: schema_version 79 (079_user_plans_revision.sql).
ALTER TABLE user_plans
    ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE user_plans
SET revision = 1
WHERE revision IS NULL OR revision < 1;

CREATE INDEX IF NOT EXISTS idx_user_plans_user_updated
    ON user_plans(user_id, updated_at DESC);
