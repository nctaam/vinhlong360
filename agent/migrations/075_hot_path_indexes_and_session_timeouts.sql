-- agent/migrations/075_hot_path_indexes_and_session_timeouts.sql
-- Migration 075: trả NỢ 4.
--   (A) Index còn thiếu trên các cột được lọc/join ở đường nóng feed + comment +
--       like, và trên các cột khoá-ngoại mà migration 074 vừa gắn ON DELETE
--       CASCADE (xoá 1 user phải rà từng bảng con — không index = quét toàn bảng).
--   (B) Trần thời gian cho phiên của role ứng dụng: một câu lệnh chạy mãi giữ
--       connection và kéo sập pool.
-- Additive, IF NOT EXISTS, chạy lại được (replay-safe).
--
-- ── VÌ SAO KHÔNG "CREATE INDEX CONCURRENTLY" ──────────────────────────────
-- scripts/apply_migrations.py chạy TOÀN BỘ chuỗi migration trong MỘT transaction:
-- `with psycopg2.connect(database_url) as conn:` (psycopg2 mặc định autocommit=False,
-- BEGIN ngầm ở câu lệnh đầu) rồi `conn.commit()` một lần ở cuối; ngoài ra
-- `apply_sql_file` nạp NGUYÊN file bằng một `cur.execute()`, tức multi-statement
-- simple query — cũng là một khối ngầm. PostgreSQL từ chối CREATE INDEX
-- CONCURRENTLY trong transaction block (SQLSTATE 25001) ⇒ dùng CONCURRENTLY ở đây
-- sẽ làm HỎNG cả chuỗi, chứ không phải "an toàn hơn". Nó còn phá tính nguyên tử
-- migration+schema_version mà runner đang bảo đảm.
-- CREATE INDEX thường lấy khoá SHARE: CHẶN GHI (INSERT/UPDATE/DELETE), KHÔNG chặn
-- đọc, trên đúng bảng đang tạo index. Sáu bảng dưới đây đều nhỏ ở quy mô hiện tại
-- nên cửa sổ chặn ghi tính bằng mili-giây. Khi nào bảng lớn tới mức cửa sổ đó không
-- chấp nhận được thì phải đổi CÁCH CHẠY (autocommit, ngoài runner) chứ không chỉ
-- đổi câu SQL — xem phần cảnh báo vận hành trong báo cáo NỢ 4.

-- Migration nặng chạy sau khi phần (B) có hiệu lực sẽ thừa kế statement_timeout của
-- role; dòng này là mẫu bắt buộc cho mọi migration build index/backfill về sau.
SET LOCAL statement_timeout = 0;

-- ══════════════════════════════════════════════════════════════════════════
-- (A) INDEX ĐƯỜNG NÓNG
-- ══════════════════════════════════════════════════════════════════════════

-- likes(post_id) — NỢ 4(a), đã xác nhận thiếu thật.
-- likes chỉ có: PRIMARY KEY (user_id, post_id) [init.sql], idx_likes_user_id
-- [020], idx_likes_user_recent(user_id, created_at DESC) [033]. Cả ba đều DẪN ĐẦU
-- bằng user_id ⇒ mọi truy vấn lọc theo post_id không có đường vào.
-- Ba chỗ trả giá:
--   1. trigger update_like_count() (init.sql) chạy
--      SELECT COUNT(*) FROM likes WHERE post_id = pid
--      sau MỖI lượt thích/bỏ thích — đây là chỗ đau nhất vì nó nằm trên đường ghi.
--   2. GET /posts/{id}/likers (agent/social.py) đếm rồi liệt kê
--      WHERE l.post_id = %s::uuid ORDER BY l.created_at DESC.
--   3. ràng buộc posts→likes ON DELETE CASCADE khi dọn bài quá hạn lưu.
-- Ghép created_at DESC để (2) lấy luôn thứ tự từ index.
CREATE INDEX IF NOT EXISTS idx_likes_post_created
    ON likes(post_id, created_at DESC);

-- bookmarks(post_id) — cùng hình dạng khiếm khuyết với likes: PRIMARY KEY
-- (user_id, post_id) + idx_bookmarks_user_id [020], không có đường vào theo
-- post_id. Phục vụ ràng buộc posts→bookmarks ON DELETE CASCADE.
CREATE INDEX IF NOT EXISTS idx_bookmarks_post
    ON bookmarks(post_id);

-- blocks(blocked_id) — CHIỀU NGƯỢC của khoá chính, dùng trên MỌI request đã đăng nhập.
-- agent/social.py::_block_sql chèn vào feed / danh sách comment / likers / chi tiết bài:
--     SELECT blocked_id FROM blocks WHERE blocker_id = %s::uuid      -- PK lo được
--     UNION
--     SELECT blocker_id FROM blocks WHERE blocked_id = %s::uuid      -- KHÔNG có index
-- PRIMARY KEY (blocker_id, blocked_id) chỉ phục vụ vế trên. Vế dưới hiện phải quét.
-- Đồng thời đóng luôn khe quét của users→blocks ON DELETE CASCADE (migration 074).
CREATE INDEX IF NOT EXISTS idx_blocks_blocked
    ON blocks(blocked_id);

-- comments(parent_id) — khoá ngoại TỰ THAM CHIẾU comments(id) ON DELETE CASCADE
-- (init.sql) chưa hề có index. Dọn định kỳ xoá cứng comment theo lô
-- (agent/scheduler.py::_hard_delete_stale_posts) ⇒ mỗi hàng bị xoá kéo theo một
-- lần rà comments tìm reply con: O(n²) trên chính bảng đó.
-- Cố ý dùng index THƯỜNG, không partial `WHERE parent_id IS NOT NULL`: kế hoạch của
-- trigger toàn vẹn tham chiếu là generic plan, không nên phụ thuộc vào việc bộ chứng
-- minh vị từ có suy ra được NOT NULL hay không.
CREATE INDEX IF NOT EXISTS idx_comments_parent
    ON comments(parent_id);

-- posts(pinned_comment_id) — khoá ngoại posts→comments (migration 032) KHÔNG có
-- ON DELETE, tức NO ACTION: xoá một comment buộc PostgreSQL rà bảng posts để chắc
-- không còn ai ghim nó. Không index ⇒ mỗi comment bị xoá cứng = một lần quét posts.
CREATE INDEX IF NOT EXISTS idx_posts_pinned_comment
    ON posts(pinned_comment_id);

-- user_mutes(muted_id) — UNIQUE(user_id, muted_id) [048] dẫn đầu bằng user_id nên
-- chỉ phục vụ chiều "tôi tắt tiếng ai". Chiều "ai tắt tiếng người này" là đường của
-- users→user_mutes ON DELETE CASCADE mà 074 vừa gắn.
CREATE INDEX IF NOT EXISTS idx_user_mutes_muted
    ON user_mutes(muted_id);

-- ══════════════════════════════════════════════════════════════════════════
-- (B) TRẦN THỜI GIAN PHIÊN CHO ROLE ỨNG DỤNG
-- ══════════════════════════════════════════════════════════════════════════
-- Đặt ở TẦNG ROLE, không ở DSN và không ở code, vì:
--   * agent/database.py mở PG bằng HAI đường — psycopg2.connect(dsn, connect_timeout=5)
--     và ThreadedConnectionPool(..., connect_timeout=5) — cả hai đều KHÔNG truyền
--     options; vá ở code phải sửa cả hai và vẫn bỏ sót mọi script khác
--     (apply_migrations, check_migration_gate, scheduler, psql tay).
--   * PG_USE_POOL mặc định false ⇒ mỗi request mở connection MỚI, nên mặc định ở
--     tầng role có hiệu lực ngay khi migration commit, không cần restart agent.
--   * Nhét vào DSN nghĩa là sửa .env trên prod: không nằm trong git, không review được.
-- CỐ Ý KHÔNG đặt lock_timeout ở tầng role: nó sẽ làm các migration DDL về sau thất
-- bại ngẫu nhiên khi có traffic, đổi một sự cố hiệu năng lấy một sự cố triển khai.
DO $migration$
DECLARE
    app_role CONSTANT TEXT := 'vl360';
    may_alter BOOLEAN;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = app_role) THEN
        RAISE WARNING 'migration 075: khong co role %, bo qua phan tran thoi gian', app_role;
        RETURN;
    END IF;

    -- Role thường được phép đặt mặc định phiên CHO CHÍNH NÓ; đặt cho role khác cần
    -- SUPERUSER hoặc CREATEROLE. Thiếu quyền thì cảnh báo chứ không làm hỏng chuỗi
    -- migration vì đây là tham số vận hành, không phải toàn vẹn dữ liệu.
    may_alter := current_user = app_role
        OR EXISTS (
            SELECT 1 FROM pg_catalog.pg_roles
            WHERE rolname = current_user AND (rolsuper OR rolcreaterole)
        );

    IF NOT may_alter THEN
        RAISE WARNING
            'migration 075: role % khong du quyen dat session default cho %; dat tay bang ALTER ROLE ... SET statement_timeout',
            current_user, app_role;
        RETURN;
    END IF;

    -- 30s: truy vấn feed/comment/like lành mạnh nằm ở mili-giây, báo cáo AdminCP
    -- nặng nhất vẫn dưới ngưỡng này; đủ chặt để cắt câu lệnh chạy mãi.
    EXECUTE format('ALTER ROLE %I SET statement_timeout = %L', app_role, '30s');
    -- Transaction bỏ quên còn độc hơn: nó giữ connection VÀ chặn vacuum.
    EXECUTE format(
        'ALTER ROLE %I SET idle_in_transaction_session_timeout = %L', app_role, '60s'
    );
END
$migration$;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 75, '075_hot_path_indexes_and_session_timeouts.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE
        WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration
        ELSE schema_version.migration
    END,
    updated_at = NOW();
