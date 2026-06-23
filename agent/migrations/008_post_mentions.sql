-- @-mention: lưu danh sách người-dùng/địa-điểm được nhắc trong bài viết.
-- mentions = [{"type":"user"|"entity","id":"...","label":"..."}]
-- Áp prod: psql "$DATABASE_URL" -f agent/migrations/008_post_mentions.sql  (additive, an toàn)

ALTER TABLE posts ADD COLUMN IF NOT EXISTS mentions JSONB DEFAULT '[]';
ALTER TABLE comments ADD COLUMN IF NOT EXISTS mentions JSONB DEFAULT '[]';
