-- agent/migrations/067_trusted_devices.sql
-- Migration 067: thiết bị tin cậy — Wave 4 W4.5. token opaque (hash lưu, raw gửi cookie),
-- bỏ qua 2FA khi cookie khớp hàng chưa hết hạn. Tự hết hạn qua expires_at.
-- Additive.

CREATE TABLE IF NOT EXISTS trusted_devices (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash   TEXT UNIQUE NOT NULL,
    device_name  TEXT,
    ip           TEXT,
    user_agent   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ NOT NULL
);
ALTER TABLE trusted_devices OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_trusted_devices_token ON trusted_devices(token_hash);
CREATE INDEX IF NOT EXISTS idx_trusted_devices_user ON trusted_devices(user_id);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 67, '067_trusted_devices.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
