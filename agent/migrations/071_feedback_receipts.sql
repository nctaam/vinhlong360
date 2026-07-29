-- agent/migrations/071_feedback_receipts.sql
-- One-time owner-bound feedback receipts and deidentified daily rollups.

CREATE TABLE IF NOT EXISTS feedback_receipts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_digest TEXT NOT NULL,
    owner_kind TEXT NOT NULL CHECK (owner_kind IN ('authenticated', 'anonymous')),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    anonymous_owner_digest TEXT,
    owner_binding_digest TEXT NOT NULL,
    assistant_turn_digest TEXT NOT NULL,
    model_variant TEXT NOT NULL,
    tool_bucket TEXT NOT NULL,
    rating SMALLINT CHECK (rating IN (0, 1)),
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    CONSTRAINT idx_feedback_receipts_token_digest UNIQUE (token_digest),
    CONSTRAINT feedback_receipts_token_digest_shape CHECK (
        token_digest ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT feedback_receipts_owner_binding_shape CHECK (
        owner_binding_digest ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT feedback_receipts_turn_digest_shape CHECK (
        assistant_turn_digest ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT feedback_receipts_anonymous_digest_shape CHECK (
        anonymous_owner_digest IS NULL
        OR anonymous_owner_digest ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT feedback_receipts_model_variant_bounded CHECK (
        model_variant IN (
            'cx-gpt-5-4', 'cx-gpt-5-4-mini',
            'cx-gpt-5-5', 'cx-gpt-5-5-mini', 'other'
        )
    ),
    CONSTRAINT feedback_receipts_tool_bucket_bounded CHECK (
        tool_bucket IN ('none', 'search', 'weather', 'knowledge', 'mixed')
    ),
    CONSTRAINT feedback_receipts_expiry_order CHECK (expires_at > created_at),
    CONSTRAINT feedback_receipts_owner_state CHECK (
        (
            used_at IS NULL
            AND num_nonnulls(user_id, anonymous_owner_digest) = 1
            AND (
                (owner_kind = 'authenticated' AND user_id IS NOT NULL)
                OR (owner_kind = 'anonymous' AND anonymous_owner_digest IS NOT NULL)
            )
        )
        OR (
            used_at IS NOT NULL
            AND user_id IS NULL
            AND anonymous_owner_digest IS NULL
        )
    )
);

ALTER TABLE feedback_receipts OWNER TO vl360;

CREATE INDEX IF NOT EXISTS idx_feedback_receipts_expires
    ON feedback_receipts(expires_at, id);
CREATE INDEX IF NOT EXISTS idx_feedback_receipts_user
    ON feedback_receipts(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_feedback_receipts_anonymous
    ON feedback_receipts(anonymous_owner_digest)
    WHERE anonymous_owner_digest IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_feedback_receipts_owner_binding
    ON feedback_receipts(owner_binding_digest);

CREATE TABLE IF NOT EXISTS feedback_daily_rollups (
    day DATE NOT NULL,
    owner_kind TEXT NOT NULL CHECK (owner_kind IN ('authenticated', 'anonymous')),
    model_variant TEXT NOT NULL CHECK (
        model_variant IN (
            'cx-gpt-5-4', 'cx-gpt-5-4-mini',
            'cx-gpt-5-5', 'cx-gpt-5-5-mini', 'other'
        )
    ),
    tool_bucket TEXT NOT NULL CHECK (
        tool_bucket IN ('none', 'search', 'weather', 'knowledge', 'mixed')
    ),
    positive_count BIGINT NOT NULL DEFAULT 0 CHECK (positive_count >= 0),
    negative_count BIGINT NOT NULL DEFAULT 0 CHECK (negative_count >= 0),
    CONSTRAINT feedback_daily_rollups_dimensions_key
        UNIQUE (day, owner_kind, model_variant, tool_bucket)
);

ALTER TABLE feedback_daily_rollups OWNER TO vl360;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 71, '071_feedback_receipts.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
