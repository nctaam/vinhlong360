-- ============================================================
-- vinhlong360.vn — PostgreSQL Schema
-- Phase 0: Knowledge Graph + Auth + Sessions
-- Phase 1: Posts, Reviews, Comments, Likes, Bookmarks
-- Phase 2: Follows, Notifications, Reports, Moderation
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";
-- f_unaccent: unaccent dạng IMMUTABLE → dùng được trong functional index (migration 015)
CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS
$$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$;

-- ──────────────────────────────────────────────────────────
-- PHASE 0: Knowledge Graph (migrated from SQLite)
-- ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS entities (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    summary     TEXT DEFAULT '',
    description TEXT DEFAULT '',
    "placeId"   TEXT,
    confidence  REAL DEFAULT 1.0,
    season      JSONB,
    attributes  JSONB DEFAULT '{}',
    source      JSONB DEFAULT '{}',
    images      JSONB DEFAULT '[]',
    coordinates JSONB,
    area        TEXT,
    level       TEXT,
    "parentId"  TEXT,
    "legacyArea" TEXT,
    "updatedAt" TEXT,
    status      TEXT,
    verified    INTEGER DEFAULT 1,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_placeid ON entities("placeId");
CREATE INDEX IF NOT EXISTS idx_entities_public_type_area_updated
    ON entities(type, area, "updatedAt" DESC, id)
    WHERE type <> 'place'
      AND (status IS NULL OR status <> 'provisional')
      AND (verified IS NULL OR verified <> 0);
CREATE INDEX IF NOT EXISTS idx_entities_public_area_updated
    ON entities(area, "updatedAt" DESC, id)
    WHERE type <> 'place'
      AND (status IS NULL OR status <> 'provisional')
      AND (verified IS NULL OR verified <> 0);
CREATE INDEX IF NOT EXISTS idx_entities_public_place_updated
    ON entities("placeId", "updatedAt" DESC, id)
    WHERE type <> 'place'
      AND "placeId" IS NOT NULL
      AND (status IS NULL OR status <> 'provisional')
      AND (verified IS NULL OR verified <> 0);
CREATE INDEX IF NOT EXISTS idx_entities_public_coordinates
    ON entities(type, area)
    WHERE type <> 'place'
      AND coordinates IS NOT NULL
      AND (status IS NULL OR status <> 'provisional')
      AND (verified IS NULL OR verified <> 0);
CREATE INDEX IF NOT EXISTS idx_entities_public_events_updated
    ON entities("updatedAt" DESC, id)
    WHERE type = 'event'
      AND (status IS NULL OR status <> 'provisional')
      AND (verified IS NULL OR verified <> 0);
CREATE INDEX IF NOT EXISTS idx_entities_season_gin
    ON entities USING gin(season jsonb_path_ops)
    WHERE season IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_entities_name_trgm ON entities USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_entities_summary_trgm ON entities USING gin(summary gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_entities_name_unaccent ON entities USING gin(f_unaccent(lower(name)) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_entities_summary_unaccent ON entities USING gin(f_unaccent(lower(summary)) gin_trgm_ops);

CREATE TABLE IF NOT EXISTS relationships (
    from_id TEXT NOT NULL,
    to_id   TEXT NOT NULL,
    type    TEXT NOT NULL,
    PRIMARY KEY (from_id, to_id, type)
);

CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_id);
CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_id);

CREATE TABLE IF NOT EXISTS itineraries (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    area       TEXT,
    areas      JSONB DEFAULT '[]',
    duration   TEXT,
    summary    TEXT DEFAULT '',
    stops      JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedback (
    id         SERIAL PRIMARY KEY,
    user_id    TEXT,
    query      TEXT,
    rating     INTEGER,
    entity_id  TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id);

CREATE TABLE IF NOT EXISTS query_log (
    id            SERIAL PRIMARY KEY,
    query         TEXT,
    tools         JSONB,
    reply_length  INTEGER,
    score         REAL,
    session_id    TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_log_session ON query_log(session_id);
CREATE INDEX IF NOT EXISTS idx_query_log_created ON query_log(created_at);

-- ──────────────────────────────────────────────────────────
-- PHASE 0: Users + OTP Authentication
-- ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone         TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    display_name  TEXT,
    avatar_url    TEXT,
    username      TEXT,
    bio           TEXT DEFAULT '',
    role          TEXT DEFAULT 'user' CHECK (role IN ('user', 'moderator', 'admin', 'superadmin')),
    is_active     BOOLEAN DEFAULT TRUE,
    consent_at    TIMESTAMPTZ,
    consent_version TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique
  ON users (lower(username)) WHERE username IS NOT NULL;

CREATE TABLE IF NOT EXISTS otp_sessions (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone      TEXT NOT NULL,
    code       TEXT NOT NULL,
    attempts   INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    verified   BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_otp_phone ON otp_sessions(phone, verified);

CREATE TABLE IF NOT EXISTS user_sessions (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT UNIQUE NOT NULL,
    user_agent TEXT,
    ip_address TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);

-- ──────────────────────────────────────────────────────────
-- PHASE 1: Social — Posts, Reviews, Comments, Likes
-- ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS posts (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_id         TEXT REFERENCES entities(id) ON DELETE SET NULL,
    content           TEXT NOT NULL,
    images            JSONB DEFAULT '[]',
    post_type         TEXT DEFAULT 'share' CHECK (post_type IN ('share', 'review', 'recommend', 'question')),
    rating            SMALLINT CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
    moderation_status TEXT DEFAULT 'pending' CHECK (moderation_status IN ('pending', 'approved', 'rejected', 'flagged')),
    like_count        INTEGER DEFAULT 0,
    comment_count     INTEGER DEFAULT 0,
    mentions          JSONB DEFAULT '[]',
    hashtags          JSONB DEFAULT '[]',
    -- deleted_at thuộc baseline vì index idx_posts_review_entity_recent_public bên dưới
    -- tham chiếu nó NGAY trong file này (migration 051 ALTER IF NOT EXISTS = no-op khi replay).
    deleted_at        TIMESTAMPTZ DEFAULT NULL,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_entity ON posts(entity_id);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(moderation_status);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_type ON posts(post_type);
CREATE INDEX IF NOT EXISTS idx_posts_content_trgm ON posts USING GIN (lower(content) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_posts_content_unaccent ON posts USING GIN (f_unaccent(lower(content)) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_posts_review_entity_recent_public
    ON posts(entity_id, created_at DESC)
    WHERE post_type = 'review'
      AND moderation_status = 'approved'
      AND deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS comments (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id           UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id         UUID REFERENCES comments(id) ON DELETE CASCADE,
    content           TEXT NOT NULL,
    moderation_status TEXT DEFAULT 'approved',
    mentions          JSONB DEFAULT '[]',
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);

CREATE TABLE IF NOT EXISTS likes (
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id    UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, post_id)
);

CREATE TABLE IF NOT EXISTS bookmarks (
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id    UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, post_id)
);

CREATE TABLE IF NOT EXISTS entity_ratings (
    entity_id    TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
    avg_rating   REAL DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Saved entities (favorites) synced to user account (P1). entity_id is TEXT
-- (entity ids are slugs). `snapshot` keeps a lightweight copy (name/type/image)
-- so a new device can render saved cards without N detail fetches.
CREATE TABLE IF NOT EXISTS saved_entities (
    id         UUID DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_id  TEXT NOT NULL,
    kind       TEXT DEFAULT 'entity' CHECK (kind IN ('entity', 'itinerary')),
    snapshot   JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_saved_entities_user ON saved_entities(user_id, created_at DESC);

-- ──────────────────────────────────────────────────────────
-- PHASE 2: Community — Follows, Notifications, Reports
-- ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS follows (
    follower_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type  TEXT NOT NULL CHECK (target_type IN ('user', 'entity')),
    target_id    TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (follower_id, target_type, target_id)
);

CREATE INDEX IF NOT EXISTS idx_follows_target ON follows(target_type, target_id);

CREATE TABLE IF NOT EXISTS notifications (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type       TEXT NOT NULL,
    title      TEXT NOT NULL,
    body       TEXT,
    ref_type   TEXT,
    ref_id     TEXT,
    is_read    BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read, created_at DESC);

CREATE TABLE IF NOT EXISTS reports (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL CHECK (target_type IN ('post', 'comment', 'user', 'entity', 'facility')),
    target_id   TEXT NOT NULL,
    reason      TEXT NOT NULL,
    status      TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'dismissed', 'resolved')),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS blocks (
    blocker_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (blocker_id, blocked_id)
);

CREATE TABLE IF NOT EXISTS moderation_log (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_type TEXT NOT NULL,
    target_id   TEXT NOT NULL,
    action      TEXT NOT NULL,
    reason      TEXT,
    moderator_id UUID REFERENCES users(id),
    auto        BOOLEAN DEFAULT FALSE,
    scores      JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ──────────────────────────────────────────────────────────
-- Functions & Triggers
-- ──────────────────────────────────────────────────────────

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_users_updated
    BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trg_posts_updated
    BEFORE UPDATE ON posts FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Update entity_ratings aggregate on review insert/delete
CREATE OR REPLACE FUNCTION update_entity_ratings()
RETURNS TRIGGER AS $$
DECLARE
    eid TEXT;
BEGIN
    IF TG_OP = 'DELETE' THEN eid := OLD.entity_id;
    ELSE eid := NEW.entity_id;
    END IF;

    IF eid IS NOT NULL THEN
        INSERT INTO entity_ratings (entity_id, avg_rating, rating_count, updated_at)
        SELECT entity_id, AVG(rating), COUNT(*), NOW()
        FROM posts
        WHERE entity_id = eid AND post_type = 'review' AND rating IS NOT NULL
            AND moderation_status = 'approved'
        GROUP BY entity_id
        ON CONFLICT (entity_id)
        DO UPDATE SET
            avg_rating   = EXCLUDED.avg_rating,
            rating_count = EXCLUDED.rating_count,
            updated_at   = NOW();
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Tách 2 trigger: PG cấm WHEN tham chiếu NEW trên trigger có DELETE
-- (DELETE chỉ có OLD). Hàm update_entity_ratings xử lý cả hai qua TG_OP.
CREATE OR REPLACE TRIGGER trg_entity_ratings
    AFTER INSERT OR UPDATE ON posts
    FOR EACH ROW
    WHEN (NEW.post_type = 'review')
    EXECUTE FUNCTION update_entity_ratings();

CREATE OR REPLACE TRIGGER trg_entity_ratings_del
    AFTER DELETE ON posts
    FOR EACH ROW
    WHEN (OLD.post_type = 'review')
    EXECUTE FUNCTION update_entity_ratings();

-- Update post like_count
CREATE OR REPLACE FUNCTION update_like_count()
RETURNS TRIGGER AS $$
DECLARE
    pid UUID;
BEGIN
    IF TG_OP = 'DELETE' THEN pid := OLD.post_id;
    ELSE pid := NEW.post_id;
    END IF;
    UPDATE posts SET like_count = (SELECT COUNT(*) FROM likes WHERE post_id = pid) WHERE id = pid;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_like_count
    AFTER INSERT OR DELETE ON likes
    FOR EACH ROW EXECUTE FUNCTION update_like_count();

-- Update post comment_count
CREATE OR REPLACE FUNCTION update_comment_count()
RETURNS TRIGGER AS $$
DECLARE
    pid UUID;
BEGIN
    IF TG_OP = 'DELETE' THEN pid := OLD.post_id;
    ELSE pid := NEW.post_id;
    END IF;
    UPDATE posts SET comment_count = (SELECT COUNT(*) FROM comments WHERE post_id = pid) WHERE id = pid;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_comment_count
    AFTER INSERT OR DELETE ON comments
    FOR EACH ROW EXECUTE FUNCTION update_comment_count();

-- Cleanup expired OTP sessions (run via pg_cron or app-level)
-- DELETE FROM otp_sessions WHERE expires_at < NOW() - INTERVAL '1 hour';
-- DELETE FROM user_sessions WHERE expires_at < NOW();

-- ──────────────────────────────────────────────────────────
-- PHASE CMS: Site Settings (admin-configurable website elements)
-- ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS site_settings (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL,
    category    TEXT NOT NULL,
    label       TEXT NOT NULL DEFAULT '',
    description TEXT DEFAULT '',
    input_type  TEXT DEFAULT 'text',
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_site_settings_cat ON site_settings(category);

-- Lịch trình cá nhân đồng-bộ tài-khoản (builder) — cross-device
CREATE TABLE IF NOT EXISTS user_plans (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL DEFAULT 'Lịch trình',
    stops       JSONB NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_plans_user ON user_plans(user_id, created_at DESC);

-- "Đã đi / Muốn đi" — bản đồ cá nhân
CREATE TABLE IF NOT EXISTS user_visits (
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_id  TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('want', 'visited')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_user_visits_user ON user_visits(user_id, status);

-- Append-only admin audit store used by AdminCP RBAC/audit workflows.
CREATE TABLE IF NOT EXISTS admin_audit_events (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor        TEXT NOT NULL,
    actor_role   TEXT,
    actor_scopes TEXT[] DEFAULT ARRAY[]::TEXT[],
    method       TEXT NOT NULL,
    path         TEXT NOT NULL,
    request_id   TEXT,
    ip           TEXT,
    reason       TEXT,
    before_json  JSONB,
    after_json   JSONB,
    meta         JSONB DEFAULT '{}'::JSONB
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_events_created_at
    ON admin_audit_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_events_actor
    ON admin_audit_events(actor, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_events_path
    ON admin_audit_events(path, created_at DESC);

-- Shared rate-limit and idempotency stores for multi-worker deploys.
CREATE TABLE IF NOT EXISTS shared_rate_limits (
    key        TEXT PRIMARY KEY,
    hits       DOUBLE PRECISION[] NOT NULL DEFAULT ARRAY[]::DOUBLE PRECISION[],
    expires_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_shared_rate_limits_expires_at
    ON shared_rate_limits(expires_at);

CREATE TABLE IF NOT EXISTS request_idempotency_keys (
    key           TEXT PRIMARY KEY,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at    TIMESTAMPTZ NOT NULL,
    meta          JSONB NOT NULL DEFAULT '{}'::JSONB
);
CREATE INDEX IF NOT EXISTS idx_request_idempotency_keys_expires_at
    ON request_idempotency_keys(expires_at);

CREATE TABLE IF NOT EXISTS quality_metric_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_key TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metric_unit TEXT DEFAULT 'count',
    source TEXT DEFAULT 'quality_budget',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_quality_metric_snapshots_key_time
    ON quality_metric_snapshots(metric_key, created_at DESC);

-- Migration baseline marker. A fresh database must still run
-- scripts/apply_migrations.py to reach the latest release schema.
CREATE TABLE IF NOT EXISTS schema_version (
  component  TEXT PRIMARY KEY,
  version    INTEGER NOT NULL,
  migration  TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 1, 'init.sql', NOW())
ON CONFLICT (component) DO UPDATE SET
  version = GREATEST(schema_version.version, EXCLUDED.version),
  migration = CASE
    WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration
    ELSE schema_version.migration
  END,
  updated_at = NOW();
