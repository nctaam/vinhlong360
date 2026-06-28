-- Migration 026: Soft-delete support for user accounts.
-- Instead of hard DELETE, set deleted_at + is_active=FALSE.
-- OTP login within grace period clears deleted_at and reactivates.

ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
