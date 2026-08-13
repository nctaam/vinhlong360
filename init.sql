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
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    revision    INTEGER NOT NULL DEFAULT 1
);
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'entities_revision_positive'
          AND conrelid = 'entities'::regclass
    ) THEN
        ALTER TABLE entities
            ADD CONSTRAINT entities_revision_positive CHECK (revision >= 1);
    END IF;
END $$;

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
    deleted_at    TIMESTAMPTZ,
    erasure_due_at TIMESTAMPTZ,
    erasure_attempt_count INTEGER NOT NULL DEFAULT 0
        CHECK (erasure_attempt_count >= 0),
    erasure_last_attempt_at TIMESTAMPTZ,
    erasure_last_error_code TEXT
        CHECK (erasure_last_error_code IS NULL OR erasure_last_error_code IN (
            'STORE_UNAVAILABLE', 'RESIDUAL_DATA', 'DB_CONSTRAINT', 'VERIFY_FAILED'
        )),
    consent_at    TIMESTAMPTZ,
    consent_version TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique
  ON users (lower(username)) WHERE username IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_erasure_due
  ON users(erasure_due_at)
  WHERE deleted_at IS NOT NULL AND erasure_due_at IS NOT NULL;

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
    v_avg NUMERIC;
    v_cnt INTEGER;
BEGIN
    IF TG_OP = 'DELETE' THEN eid := OLD.entity_id;
    ELSE eid := NEW.entity_id;
    END IF;

    IF eid IS NOT NULL THEN
        -- deleted_at IS NULL: review soft-delete không còn tính vào sao (xem migration 070).
        SELECT COALESCE(AVG(rating), 0), COUNT(*)
        INTO v_avg, v_cnt
        FROM posts
        WHERE entity_id = eid AND post_type = 'review' AND rating IS NOT NULL
            AND moderation_status = 'approved' AND deleted_at IS NULL;
        -- Luôn UPSERT (kể cả v_cnt=0) → xoá review cuối cùng thì reset avg/count về 0.
        INSERT INTO entity_ratings (entity_id, avg_rating, rating_count, updated_at)
        VALUES (eid, v_avg, v_cnt, NOW())
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
    -- deleted_at IS NULL + fire ON UPDATE (soft-delete): trigger là nguồn-sự-thật duy
    -- nhất cho comment_count; social.py KHÔNG tăng/giảm tay nữa (xem migration 070).
    UPDATE posts SET comment_count = (
        SELECT COUNT(*) FROM comments WHERE post_id = pid AND deleted_at IS NULL
    ) WHERE id = pid;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_comment_count ON comments;
CREATE TRIGGER trg_comment_count
    AFTER INSERT OR DELETE OR UPDATE ON comments
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
    CONSTRAINT feedback_receipts_token_digest_shape CHECK (token_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT feedback_receipts_owner_binding_shape CHECK (owner_binding_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT feedback_receipts_turn_digest_shape CHECK (assistant_turn_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT feedback_receipts_anonymous_digest_shape CHECK (
        anonymous_owner_digest IS NULL OR anonymous_owner_digest ~ '^[0-9a-f]{64}$'
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

-- Correction Case Kernel fresh-schema parity (migration 080).
-- Additive Correction Case Kernel schema (PostgreSQL only).
-- No legacy rows are rewritten by this migration.

ALTER TABLE entities
    ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'entities_revision_positive'
          AND conrelid = 'entities'::regclass
    ) THEN
        ALTER TABLE entities
            ADD CONSTRAINT entities_revision_positive CHECK (revision >= 1);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS cases (
    case_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_kind TEXT NOT NULL CHECK (service_kind IN ('correction', 'claim', 'account_recovery', 'safety_report')),
    category TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN ('intake', 'triage', 'investigation', 'decision', 'fulfillment', 'closed')),
    activity TEXT NOT NULL CHECK (activity IN ('active', 'waiting_on_requester', 'waiting_on_external')),
    disposition_family TEXT NOT NULL CHECK (disposition_family IN ('undetermined', 'action_taken', 'no_action', 'transferred', 'withdrawn', 'duplicate')),
    domain_outcome TEXT,
    severity TEXT,
    reporter_privacy TEXT NOT NULL,
    owner_ref TEXT NOT NULL,
    current_revision INTEGER NOT NULL DEFAULT 1 CHECK (current_revision >= 1),
    promise_policy_ref TEXT NOT NULL,
    review_of_case_id UUID REFERENCES cases(case_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    CONSTRAINT cases_closed_phase_order CHECK ((phase = 'closed') = (closed_at IS NOT NULL))
);
ALTER TABLE cases OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_interactions (
    interaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    channel TEXT NOT NULL CHECK (channel IN ('web', 'phone', 'zalo_human', 'zalo_ai_handoff', 'email_transcribed')),
    actor_ref TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound', 'internal')),
    consent_ref TEXT,
    identity_assurance TEXT,
    payload_enc TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE case_interactions OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_party_authorities (
    party_authority_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    party_ref TEXT NOT NULL,
    authority_kind TEXT NOT NULL,
    scope TEXT NOT NULL,
    assurance_level TEXT NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CONSTRAINT case_party_authorities_expiry_order CHECK (expires_at IS NULL OR expires_at > granted_at)
);
ALTER TABLE case_party_authorities OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_work_items (
    work_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    required_role TEXT NOT NULL,
    risk_class TEXT NOT NULL CHECK (risk_class IN ('R0', 'R1', 'R2', 'R3')),
    status TEXT NOT NULL CHECK (status IN ('ready', 'claimed', 'waiting', 'completed', 'cancelled')),
    assignee_ref TEXT,
    lease_expires_at TIMESTAMPTZ,
    ready_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    next_review_at TIMESTAMPTZ,
    priority SMALLINT NOT NULL DEFAULT 0,
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
    CONSTRAINT case_work_items_active_lease CHECK (status <> 'claimed' OR (assignee_ref IS NOT NULL AND lease_expires_at IS NOT NULL))
);
ALTER TABLE case_work_items OWNER TO vl360;
CREATE UNIQUE INDEX IF NOT EXISTS uq_case_work_items_active_lease
    ON case_work_items(case_id, kind)
    WHERE status = 'claimed';
CREATE INDEX IF NOT EXISTS idx_case_work_items_queue_priority
    ON case_work_items(priority DESC, ready_at, work_item_id)
    WHERE status = 'ready';

CREATE TABLE IF NOT EXISTS case_decisions (
    decision_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    item_id UUID,
    outcome_code TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    decision_maker_ref TEXT NOT NULL,
    reviewer_ref TEXT,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    policy_revision TEXT NOT NULL
);
ALTER TABLE case_decisions OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_promise_clocks (
    clock_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('receipt', 'triage', 'update', 'resolution')),
    started_at TIMESTAMPTZ NOT NULL,
    due_at TIMESTAMPTZ NOT NULL,
    health TEXT NOT NULL CHECK (health IN ('on_track', 'at_risk', 'breached', 'recovery')),
    policy_revision TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT case_promise_clocks_due_order CHECK (due_at >= started_at),
    CONSTRAINT case_promise_clocks_kind_unique UNIQUE (case_id, kind)
);
ALTER TABLE case_promise_clocks OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_case_promise_clocks_due
    ON case_promise_clocks(due_at, case_id)
    WHERE health IN ('at_risk', 'breached');

CREATE TABLE IF NOT EXISTS case_receipts (
    receipt_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    public_reference TEXT NOT NULL UNIQUE,
    capability_digest TEXT NOT NULL UNIQUE,
    capability_key_version TEXT NOT NULL,
    notification_consent_ref TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_receipts_capability_digest_shape CHECK (capability_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT case_receipts_expiry_order CHECK (expires_at > created_at)
);
ALTER TABLE case_receipts OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_access_sessions (
    access_session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    receipt_id UUID NOT NULL REFERENCES case_receipts(receipt_id) ON DELETE CASCADE,
    session_digest TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_access_sessions_expiry_order CHECK (expires_at > created_at)
);
ALTER TABLE case_access_sessions OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_case_access_sessions_expiry
    ON case_access_sessions(expires_at, access_session_id)
    WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS case_admin_access_sessions (
    admin_access_session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    actor_ref TEXT NOT NULL,
    scope TEXT NOT NULL,
    session_digest TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_admin_access_sessions_expiry_order CHECK (expires_at > created_at)
);
ALTER TABLE case_admin_access_sessions OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_transitions (
    transition_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    from_phase TEXT,
    to_phase TEXT NOT NULL,
    from_revision INTEGER,
    to_revision INTEGER NOT NULL,
    actor_ref TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    policy_revision TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_transitions_revision_order CHECK (to_revision >= 1 AND (from_revision IS NULL OR to_revision = from_revision + 1))
);
ALTER TABLE case_transitions OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_audit_events (
    audit_event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    actor_ref TEXT NOT NULL,
    actor_scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    channel TEXT,
    reason_code TEXT NOT NULL,
    policy_revision TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    before_snapshot JSONB,
    after_snapshot JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE case_audit_events OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_outbox (
    outbox_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(case_id) ON DELETE CASCADE,
    idempotency_key TEXT NOT NULL,
    topic TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'sent', 'failed')),
    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_outbox_idempotency_unique UNIQUE (idempotency_key)
);
ALTER TABLE case_outbox OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_case_outbox_retry
    ON case_outbox(available_at, outbox_id)
    WHERE status IN ('pending', 'failed');

CREATE TABLE IF NOT EXISTS case_idempotency (
    idempotency_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    idempotency_key TEXT NOT NULL,
    actor_ref TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    response_enc TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_idempotency_key_actor_unique UNIQUE (idempotency_key, actor_ref),
    CONSTRAINT case_idempotency_expiry_order CHECK (expires_at > created_at)
);
ALTER TABLE case_idempotency OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_contact_challenges (
    challenge_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    contact_digest TEXT NOT NULL,
    challenge_digest TEXT NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('phone', 'email')),
    expires_at TIMESTAMPTZ NOT NULL,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_contact_challenges_expiry_order CHECK (expires_at > created_at)
);
ALTER TABLE case_contact_challenges OWNER TO vl360;

CREATE TABLE IF NOT EXISTS correction_items (
    item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    entity_id TEXT REFERENCES entities(id),
    field_path TEXT NOT NULL,
    reported_value_enc TEXT,
    proposed_value_enc TEXT,
    base_entity_revision INTEGER NOT NULL CHECK (base_entity_revision >= 1),
    risk_class TEXT NOT NULL CHECK (risk_class IN ('R0', 'R1', 'R2', 'R3')),
    evidence_level TEXT NOT NULL CHECK (evidence_level IN ('E0', 'E1', 'E2', 'E3', 'E4')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE correction_items OWNER TO vl360;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'case_decisions_item_id_fkey'
          AND conrelid = 'case_decisions'::regclass
    ) THEN
        ALTER TABLE case_decisions
            ADD CONSTRAINT case_decisions_item_id_fkey
            FOREIGN KEY (item_id) REFERENCES correction_items(item_id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS correction_evidence (
    evidence_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    item_id UUID REFERENCES correction_items(item_id) ON DELETE CASCADE,
    evidence_level TEXT NOT NULL CHECK (evidence_level IN ('E0', 'E1', 'E2', 'E3', 'E4')),
    source_ref TEXT,
    descriptor JSONB NOT NULL DEFAULT '{}'::jsonb,
    content_enc TEXT,
    created_by_ref TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE correction_evidence OWNER TO vl360;

CREATE TABLE IF NOT EXISTS correction_change_sets (
    change_set_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    item_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    base_entity_revision INTEGER NOT NULL,
    before_patch JSONB NOT NULL,
    after_patch JSONB NOT NULL,
    inverse_patch JSONB NOT NULL,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    policy_revision TEXT NOT NULL,
    risk_class TEXT NOT NULL CHECK (risk_class IN ('R0', 'R1', 'R2', 'R3')),
    decision_maker_ref TEXT NOT NULL,
    reviewer_ref TEXT,
    apply_status TEXT NOT NULL DEFAULT 'pending' CHECK (apply_status IN ('pending', 'applied', 'rolled_back', 'rejected')),
    public_projection_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT correction_change_sets_base_revision_positive CHECK (base_entity_revision >= 1)
);
ALTER TABLE correction_change_sets OWNER TO vl360;

CREATE TABLE IF NOT EXISTS legacy_intake_records (
    legacy_intake_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_file TEXT NOT NULL,
    source_line INTEGER NOT NULL CHECK (source_line >= 1),
    raw_record_digest TEXT NOT NULL CHECK (raw_record_digest ~ '^[0-9a-f]{64}$'),
    imported_case_id UUID REFERENCES cases(case_id),
    legacy_status TEXT,
    missing_data_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    mapping_decision TEXT NOT NULL,
    import_result TEXT NOT NULL,
    reconciliation_result TEXT,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT legacy_intake_locator_unique UNIQUE (source_file, source_line)
);
ALTER TABLE legacy_intake_records OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_legacy_intake_reconcile
    ON legacy_intake_records(import_result, imported_at);

CREATE TABLE IF NOT EXISTS case_capacity_events (
    capacity_event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(case_id) ON DELETE SET NULL,
    channel TEXT NOT NULL,
    risk_class TEXT CHECK (risk_class IN ('R0', 'R1', 'R2', 'R3')),
    event_kind TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_seconds INTEGER CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
ALTER TABLE case_capacity_events OWNER TO vl360;

CREATE OR REPLACE FUNCTION reject_case_ledger_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'immutable_case_ledger';
END;
$$;
DROP TRIGGER IF EXISTS case_transitions_immutable ON case_transitions;
CREATE TRIGGER case_transitions_immutable BEFORE UPDATE OR DELETE ON case_transitions
FOR EACH ROW EXECUTE FUNCTION reject_case_ledger_mutation();
DROP TRIGGER IF EXISTS case_audit_events_immutable ON case_audit_events;
CREATE TRIGGER case_audit_events_immutable BEFORE UPDATE OR DELETE ON case_audit_events
FOR EACH ROW EXECUTE FUNCTION reject_case_ledger_mutation();


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
