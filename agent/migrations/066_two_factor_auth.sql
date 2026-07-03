-- agent/migrations/066_two_factor_auth.sql
-- Migration 066: xác thực 2 bước (TOTP) — Wave 4 W4.1/W4.2/W4.3.
-- user_2fa: secret MÃ HOÁ (Fernet, KHÔNG hash — cần giải mã để verify) + cờ enabled.
-- user_2fa_recovery_codes: mã khôi phục HASH (SHA-256), dùng-một-lần qua used_at.
-- pending_2fa: thử thách nửa-đăng-nhập (mirror otp_sessions) — token_hash, hết hạn 5 phút.
-- Additive.

CREATE TABLE IF NOT EXISTS user_2fa (
    user_id      UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    secret_enc   TEXT NOT NULL,              -- Fernet-encrypted TOTP secret
    enabled      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at  TIMESTAMPTZ
);
ALTER TABLE user_2fa OWNER TO vl360;

CREATE TABLE IF NOT EXISTS user_2fa_recovery_codes (
    id         BIGSERIAL PRIMARY KEY,
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash  TEXT NOT NULL,
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE user_2fa_recovery_codes OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_recovery_codes_user ON user_2fa_recovery_codes(user_id);

CREATE TABLE IF NOT EXISTS pending_2fa (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT UNIQUE NOT NULL,
    ip         TEXT,
    user_agent TEXT,
    attempts   INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE pending_2fa OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_pending_2fa_token ON pending_2fa(token_hash);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 66, '066_two_factor_auth.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
