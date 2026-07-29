-- Migration 072: durable account-erasure deadline and bounded attempt state.
-- Intentionally does not backfill legacy soft-deleted rows; Task 7 reports those
-- rows for a separately approved, audit-only deadline backfill.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS erasure_due_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS erasure_attempt_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS erasure_last_attempt_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS erasure_last_error_code TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'users_erasure_attempt_count_nonnegative'
    ) THEN
        ALTER TABLE users
            ADD CONSTRAINT users_erasure_attempt_count_nonnegative
            CHECK (erasure_attempt_count >= 0);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'users_erasure_last_error_code_allowed'
    ) THEN
        ALTER TABLE users
            ADD CONSTRAINT users_erasure_last_error_code_allowed
            CHECK (
                erasure_last_error_code IS NULL
                OR erasure_last_error_code IN (
                    'STORE_UNAVAILABLE',
                    'RESIDUAL_DATA',
                    'DB_CONSTRAINT',
                    'VERIFY_FAILED'
                )
            );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_users_erasure_due
    ON users(erasure_due_at)
    WHERE deleted_at IS NOT NULL AND erasure_due_at IS NOT NULL;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 72, '072_account_erasure_state.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE
        WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration
        ELSE schema_version.migration
    END,
    updated_at = NOW();
