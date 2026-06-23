-- "Đã đi / Muốn đi": đánh dấu địa điểm theo người dùng (bản đồ cá nhân).
-- Áp prod: psql "$DATABASE_URL" -f agent/migrations/009_user_visits.sql  (additive, an toàn)

CREATE TABLE IF NOT EXISTS user_visits (
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_id  TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('want', 'visited')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_user_visits_user ON user_visits(user_id, status);
