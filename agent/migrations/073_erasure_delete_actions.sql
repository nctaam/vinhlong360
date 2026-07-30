-- Migration 073: register user FK actions and nullable audit/decision actors.
-- The VALUES inventory mirrors agent/structured_references.py. Special labels
-- such as completed_claim_scrub are enforced by the final erasure transaction.

ALTER TABLE IF EXISTS post_edit_history
    ALTER COLUMN editor_id DROP NOT NULL;
ALTER TABLE IF EXISTS admin_user_notes
    ALTER COLUMN admin_id DROP NOT NULL;
ALTER TABLE IF EXISTS entity_claims
    ALTER COLUMN claimant_id DROP NOT NULL,
    ALTER COLUMN business_name DROP NOT NULL,
    ALTER COLUMN contact_phone DROP NOT NULL;
ALTER TABLE IF EXISTS moderation_appeals
    ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE IF EXISTS moderation_log
    ALTER COLUMN target_id DROP NOT NULL;
ALTER TABLE IF EXISTS admin_audit_events
    ALTER COLUMN actor DROP NOT NULL;

DO $migration$
DECLARE
    schema_name TEXT := current_schema();
    policy RECORD;
    existing_constraint RECORD;
    constraint_name TEXT;
BEGIN
    IF to_regclass(format('%I.users', schema_name)) IS NULL THEN
        RAISE EXCEPTION 'users table is required before migration 073';
    END IF;

    FOR policy IN
        SELECT * FROM (VALUES
            ('admin_user_notes', 'admin_id', 'SET NULL', 'actor_reference'),
            ('admin_user_notes', 'user_id', 'CASCADE', NULL),
            ('announcements', 'created_by', 'SET NULL', 'actor_reference'),
            ('blocks', 'blocked_id', 'CASCADE', NULL),
            ('blocks', 'blocker_id', 'CASCADE', NULL),
            ('bookmarks', 'user_id', 'CASCADE', NULL),
            ('collections', 'created_by', 'SET NULL', 'actor_reference'),
            ('comment_likes', 'user_id', 'CASCADE', NULL),
            ('comments', 'user_id', 'CASCADE', NULL),
            ('consent_log', 'user_id', 'CASCADE', NULL),
            ('entity_claims', 'claimant_id', 'SET NULL', 'completed_claim_scrub'),
            ('entity_claims', 'reviewer_id', 'SET NULL', 'actor_reference'),
            ('event_rsvp', 'user_id', 'CASCADE', NULL),
            ('featured_entities', 'added_by', 'SET NULL', 'actor_reference'),
            ('feedback_receipts', 'user_id', 'CASCADE', NULL),
            ('follows', 'follower_id', 'CASCADE', NULL),
            ('likes', 'user_id', 'CASCADE', NULL),
            ('login_history', 'user_id', 'CASCADE', NULL),
            ('moderation_appeals', 'reviewer_id', 'SET NULL', 'actor_reference'),
            ('moderation_appeals', 'user_id', 'SET NULL', 'completed_appeal_scrub'),
            ('moderation_log', 'moderator_id', 'SET NULL', 'actor_reference'),
            ('notification_preferences', 'user_id', 'CASCADE', NULL),
            ('notifications', 'user_id', 'CASCADE', NULL),
            ('pending_2fa', 'user_id', 'CASCADE', NULL),
            ('post_edit_history', 'editor_id', 'SET NULL', 'actor_reference'),
            ('post_reactions', 'user_id', 'CASCADE', NULL),
            ('posts', 'featured_by', 'SET NULL', 'actor_reference'),
            ('posts', 'user_id', 'CASCADE', NULL),
            ('profile_views', 'viewed_id', 'CASCADE', NULL),
            ('profile_views', 'viewer_id', 'CASCADE', NULL),
            ('reports', 'reporter_id', 'CASCADE', NULL),
            ('review_responses', 'responder_id', 'CASCADE', NULL),
            ('saved_entities', 'user_id', 'CASCADE', NULL),
            ('trusted_devices', 'user_id', 'CASCADE', NULL),
            ('user_2fa', 'user_id', 'CASCADE', NULL),
            ('user_2fa_recovery_codes', 'user_id', 'CASCADE', NULL),
            ('user_achievements', 'user_id', 'CASCADE', NULL),
            ('user_collections', 'user_id', 'CASCADE', NULL),
            ('user_hidden_posts', 'user_id', 'CASCADE', NULL),
            ('user_mutes', 'muted_id', 'CASCADE', NULL),
            ('user_mutes', 'user_id', 'CASCADE', NULL),
            ('user_plans', 'user_id', 'CASCADE', NULL),
            ('user_privacy', 'user_id', 'CASCADE', NULL),
            ('user_sessions', 'user_id', 'CASCADE', NULL),
            ('user_visits', 'user_id', 'CASCADE', NULL)
        ) AS policies(table_name, column_name, delete_action, special_policy)
    LOOP
        IF to_regclass(format('%I.%I', schema_name, policy.table_name)) IS NULL THEN
            CONTINUE;
        END IF;

        FOR existing_constraint IN
            SELECT constraint_row.conname
            FROM pg_constraint AS constraint_row
            JOIN pg_attribute AS attribute
              ON attribute.attrelid = constraint_row.conrelid
             AND attribute.attnum = ANY(constraint_row.conkey)
            WHERE constraint_row.contype = 'f'
              AND constraint_row.conrelid =
                  to_regclass(format('%I.%I', schema_name, policy.table_name))
              AND constraint_row.confrelid =
                  to_regclass(format('%I.users', schema_name))
              AND attribute.attname = policy.column_name
        LOOP
            EXECUTE format(
                'ALTER TABLE %I.%I DROP CONSTRAINT %I',
                schema_name,
                policy.table_name,
                existing_constraint.conname
            );
        END LOOP;

        IF policy.delete_action = 'SET NULL' THEN
            EXECUTE format(
                'ALTER TABLE %I.%I ALTER COLUMN %I DROP NOT NULL',
                schema_name,
                policy.table_name,
                policy.column_name
            );
        END IF;

        constraint_name := format(
            'erasure_%s_%s_users_fk', policy.table_name, policy.column_name
        );
        IF policy.delete_action = 'CASCADE' THEN
            EXECUTE format(
                'ALTER TABLE %I.%I ADD CONSTRAINT %I '
                'FOREIGN KEY (%I) REFERENCES %I.users(id) ON DELETE CASCADE',
                schema_name,
                policy.table_name,
                constraint_name,
                policy.column_name,
                schema_name
            );
        ELSE
            EXECUTE format(
                'ALTER TABLE %I.%I ADD CONSTRAINT %I '
                'FOREIGN KEY (%I) REFERENCES %I.users(id) ON DELETE SET NULL',
                schema_name,
                policy.table_name,
                constraint_name,
                policy.column_name,
                schema_name
            );
        END IF;
    END LOOP;
END
$migration$;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 73, '073_erasure_delete_actions.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE
        WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration
        ELSE schema_version.migration
    END,
    updated_at = NOW();
