-- Community state machine CAS/lease fields (Task 7).
ALTER TABLE posts ADD COLUMN IF NOT EXISTS revision BIGINT NOT NULL DEFAULT 1;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS claimed_by TEXT;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS claim_expires_at TIMESTAMPTZ;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS publish_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS last_error_code TEXT;
ALTER TABLE moderation_appeals ADD COLUMN IF NOT EXISTS revision BIGINT NOT NULL DEFAULT 1;
ALTER TABLE moderation_appeals ADD COLUMN IF NOT EXISTS claimed_by TEXT;
ALTER TABLE moderation_appeals ADD COLUMN IF NOT EXISTS claim_expires_at TIMESTAMPTZ;
ALTER TABLE moderation_appeals ADD COLUMN IF NOT EXISTS last_error_code TEXT;

CREATE INDEX IF NOT EXISTS idx_posts_due_state_cas
    ON posts(scheduled_at, revision)
    WHERE scheduled_at IS NOT NULL AND is_draft = FALSE
      AND moderation_status IN ('pending', 'flagged', 'publish_failed');

DO $$
DECLARE
    old_constraint TEXT;
BEGIN
    FOR old_constraint IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'posts'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%moderation_status%'
    LOOP
        EXECUTE format('ALTER TABLE posts DROP CONSTRAINT IF EXISTS %I', old_constraint);
    END LOOP;
    ALTER TABLE posts
        ADD CONSTRAINT posts_moderation_status_check
        CHECK (moderation_status IN ('pending', 'approved', 'rejected', 'flagged', 'publish_failed'));
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'posts_revision_positive') THEN
        ALTER TABLE posts ADD CONSTRAINT posts_revision_positive CHECK (revision >= 1);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'moderation_appeals_revision_positive') THEN
        ALTER TABLE moderation_appeals ADD CONSTRAINT moderation_appeals_revision_positive CHECK (revision >= 1);
    END IF;
END $$;

INSERT INTO schema_version (component, version, migration, updated_at)
VALUES ('agent', 84, '084_community_state_cas.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version
                     THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
