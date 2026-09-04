-- Durable, single-use OTP authority for reporters who have not created a case yet.
CREATE TABLE IF NOT EXISTS case_pre_contact_challenges (
    challenge_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_digest TEXT NOT NULL,
    challenge_digest TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    verified_at TIMESTAMPTZ,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_pre_contact_challenges_expiry_order CHECK (expires_at > created_at)
);
ALTER TABLE case_pre_contact_challenges OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_case_pre_contact_challenges_active
    ON case_pre_contact_challenges(contact_digest, created_at DESC)
    WHERE used_at IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS case_pre_contact_challenges_active_contact_key
    ON case_pre_contact_challenges(contact_digest)
    WHERE used_at IS NULL;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 86, '086_pre_case_contact_challenges.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version
                     THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
