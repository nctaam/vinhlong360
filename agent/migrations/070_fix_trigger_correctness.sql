-- agent/migrations/070_fix_trigger_correctness.sql
-- Migration 070: vá 2 trigger đếm-sai (audit deep 2026-07-11) + recount data cũ.
-- Idempotent: CREATE OR REPLACE FUNCTION + DROP/CREATE TRIGGER + recount tất định.
--
-- BUG 1 — rating soft-delete: update_entity_ratings() tính AVG/COUNT KHÔNG lọc
--   deleted_at IS NULL. delete_post soft-delete (UPDATE deleted_at) chính là sự kiện
--   kích trigger → review vừa xoá VẪN nằm trong AVG/COUNT → sao entity không hồi phục.
--   Thêm điều kiện deleted_at IS NULL + luôn UPSERT (kể cả 0 review → reset về 0).
--
-- BUG 2 — comment_count đếm dư: update_comment_count() recount COUNT(*) KHÔNG lọc
--   deleted_at, chỉ fire AFTER INSERT OR DELETE; NHƯNG create_comment còn +1 tay
--   (chồng với recount) và delete_comment soft-delete (UPDATE — trigger cũ KHÔNG fire)
--   phải -N tay. Kết quả comment_count vừa dư vừa drift. Sửa: COUNT lọc deleted_at IS
--   NULL + fire thêm ON UPDATE (soft-delete recount) → trigger là nguồn-sự-thật duy nhất;
--   xoá 2 update tay ở social.py cùng migration này.

-- ── BUG 1: entity rating trigger ──────────────────────────────────────────
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
        SELECT COALESCE(AVG(rating), 0), COUNT(*)
        INTO v_avg, v_cnt
        FROM posts
        WHERE entity_id = eid AND post_type = 'review' AND rating IS NOT NULL
            AND moderation_status = 'approved' AND deleted_at IS NULL;
        -- Luôn UPSERT (kể cả v_cnt=0) → khi xoá review cuối cùng, avg/count reset về 0.
        INSERT INTO entity_ratings (entity_id, avg_rating, rating_count, updated_at)
        VALUES (eid, v_avg, v_cnt, NOW())
        ON CONFLICT (entity_id) DO UPDATE SET
            avg_rating   = EXCLUDED.avg_rating,
            rating_count = EXCLUDED.rating_count,
            updated_at   = NOW();
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- ── BUG 2: comment_count trigger (lọc deleted_at + fire on UPDATE) ─────────
CREATE OR REPLACE FUNCTION update_comment_count()
RETURNS TRIGGER AS $$
DECLARE
    pid UUID;
BEGIN
    IF TG_OP = 'DELETE' THEN pid := OLD.post_id;
    ELSE pid := NEW.post_id;
    END IF;
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

-- ── Recount data cũ (một lần, tất định — chạy lại ra cùng kết quả) ─────────
UPDATE posts p SET comment_count = (
    SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id AND c.deleted_at IS NULL
);

INSERT INTO entity_ratings (entity_id, avg_rating, rating_count, updated_at)
SELECT entity_id, COALESCE(AVG(rating), 0), COUNT(*), NOW()
FROM posts
WHERE post_type = 'review' AND rating IS NOT NULL
    AND moderation_status = 'approved' AND deleted_at IS NULL
GROUP BY entity_id
ON CONFLICT (entity_id) DO UPDATE SET
    avg_rating   = EXCLUDED.avg_rating,
    rating_count = EXCLUDED.rating_count,
    updated_at   = NOW();

-- Reset về 0 các entity còn hàng entity_ratings nhưng không còn review hợp lệ.
UPDATE entity_ratings er SET avg_rating = 0, rating_count = 0, updated_at = NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM posts p
    WHERE p.entity_id = er.entity_id AND p.post_type = 'review'
        AND p.rating IS NOT NULL AND p.moderation_status = 'approved'
        AND p.deleted_at IS NULL
);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 70, '070_fix_trigger_correctness.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
