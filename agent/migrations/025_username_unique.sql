-- Migration 025: Unique constraint on username (case-insensitive)
-- Prevents race condition where two users claim the same username simultaneously.
-- Replaces non-unique idx_users_username_lower from migration 024.

DROP INDEX IF EXISTS idx_users_username_lower;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique
    ON users(lower(username)) WHERE username IS NOT NULL;
