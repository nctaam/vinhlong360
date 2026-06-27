-- Migration 023: Consent timestamp logging
-- BE-19: Log when user ticks consent during OTP flow (NĐ 147/2024 compliance)

CREATE TABLE IF NOT EXISTS consent_log (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version    TEXT NOT NULL DEFAULT '1.0',
    ip         TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consent_log_user ON consent_log(user_id);
