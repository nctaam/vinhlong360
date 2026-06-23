-- Tìm kiếm bài viết cộng đồng: trigram index trên lower(content) để tăng tốc
-- `lower(content) LIKE '%q%'` (case-insensitive substring). Additive, an toàn.
-- Áp prod: sudo -u postgres psql -d vinhlong360 -f agent/migrations/014_post_search.sql
--   (pg_trgm là contrib chuẩn; nếu thiếu, query vẫn ĐÚNG qua seq-scan — chỉ chậm hơn)

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_posts_content_trgm
    ON posts USING GIN (lower(content) gin_trgm_ops);
