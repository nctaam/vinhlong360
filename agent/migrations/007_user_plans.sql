-- Lịch trình cá nhân đồng-bộ tài-khoản (builder /tao-lich-trinh) — cross-device như favorites.
-- Áp prod: psql "$DATABASE_URL" -f agent/migrations/007_user_plans.sql  (additive, an toàn)

CREATE TABLE IF NOT EXISTS user_plans (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL DEFAULT 'Lịch trình',
    stops       JSONB NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_plans_user ON user_plans(user_id, created_at DESC);
