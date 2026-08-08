-- Migration 071: privacy-safe identity/location preferences and bounded personalization signals.
-- Additive only. Raw GPS, IP, IP hash, raw queries, and arbitrary metadata are intentionally absent.

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id                       UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    region_id                    TEXT,
    region_label                 VARCHAR(160),
    region_scope                 TEXT NOT NULL DEFAULT 'unknown'
                                 CHECK (region_scope IN ('ward', 'district', 'province', 'all', 'unknown')),
    location_source              TEXT NOT NULL DEFAULT 'default'
                                 CHECK (location_source IN ('manual', 'gps', 'ip', 'default')),
    location_accuracy            TEXT NOT NULL DEFAULT 'unknown'
                                 CHECK (location_accuracy IN ('ward', 'district', 'province', 'unknown')),
    location_consent_state       TEXT NOT NULL DEFAULT 'unknown'
                                 CHECK (location_consent_state IN ('unknown', 'granted', 'denied', 'off', 'expired')),
    location_enabled             BOOLEAN NOT NULL DEFAULT FALSE,
    personalization_enabled      BOOLEAN NOT NULL DEFAULT FALSE,
    explicit_interests           JSONB NOT NULL DEFAULT '[]'::JSONB
                                 CHECK (jsonb_typeof(explicit_interests) = 'array'
                                        AND jsonb_array_length(explicit_interests) <= 12),
    recommendation_reset_at      TIMESTAMPTZ,
    consent_version              VARCHAR(64),
    revision                     INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_preference_consents (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type TEXT NOT NULL CHECK (consent_type IN ('location', 'personalization')),
    state        TEXT NOT NULL CHECK (state IN ('granted', 'denied', 'off', 'expired')),
    version      VARCHAR(64) NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_preference_consents_user_created_at
    ON user_preference_consents(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS user_personalization_events (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type    VARCHAR(64) NOT NULL,
    context       VARCHAR(64) NOT NULL,
    entity_id     TEXT,
    entity_type   VARCHAR(64),
    area_id       TEXT,
    interest_keys JSONB NOT NULL DEFAULT '[]'::JSONB
                  CHECK (jsonb_typeof(interest_keys) = 'array'
                         AND jsonb_array_length(interest_keys) <= 12),
    occurred_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at    TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '90 days')
);

CREATE INDEX IF NOT EXISTS idx_user_personalization_events_user_occurred_at
    ON user_personalization_events(user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_personalization_events_expires_at
    ON user_personalization_events(expires_at);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 76, '076_identity_location_preferences.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
