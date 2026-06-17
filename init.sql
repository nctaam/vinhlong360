-- ============================================================
-- vinhlong360.vn — PostgreSQL Schema
-- Phase 0: Knowledge Graph + Auth + Sessions
-- Phase 1: Posts, Reviews, Comments, Likes, Bookmarks
-- Phase 2: Follows, Notifications, Reports, Moderation
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

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
    confidence  REAL DEFAULT 0.7,
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
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_placeid ON entities("placeId");
CREATE INDEX IF NOT EXISTS idx_entities_confidence ON entities(confidence);
CREATE INDEX IF NOT EXISTS idx_entities_name_trgm ON entities USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_entities_summary_trgm ON entities USING gin(summary gin_trgm_ops);

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
    bio           TEXT DEFAULT '',
    role          TEXT DEFAULT 'user' CHECK (role IN ('user', 'moderator', 'admin')),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone ON users(phone);

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
    post_type         TEXT DEFAULT 'post' CHECK (post_type IN ('post', 'review')),
    rating            SMALLINT CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
    moderation_status TEXT DEFAULT 'pending' CHECK (moderation_status IN ('pending', 'approved', 'rejected', 'flagged')),
    like_count        INTEGER DEFAULT 0,
    comment_count     INTEGER DEFAULT 0,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_entity ON posts(entity_id);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(moderation_status);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_type ON posts(post_type);

CREATE TABLE IF NOT EXISTS comments (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id           UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id         UUID REFERENCES comments(id) ON DELETE CASCADE,
    content           TEXT NOT NULL,
    moderation_status TEXT DEFAULT 'approved',
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
    target_type TEXT NOT NULL CHECK (target_type IN ('post', 'comment', 'user')),
    target_id   TEXT NOT NULL,
    reason      TEXT NOT NULL,
    status      TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'dismissed')),
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

CREATE OR REPLACE TRIGGER trg_entity_ratings
    AFTER INSERT OR UPDATE OR DELETE ON posts
    FOR EACH ROW
    WHEN (NEW IS NULL OR NEW.post_type = 'review')
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
