-- Hashtag #chủ-đề trên bài viết → feed theo chủ-đề.
-- Áp prod: psql "$DATABASE_URL" -f agent/migrations/010_post_hashtags.sql  (additive)

ALTER TABLE posts ADD COLUMN IF NOT EXISTS hashtags JSONB DEFAULT '[]';
CREATE INDEX IF NOT EXISTS idx_posts_hashtags ON posts USING GIN (hashtags);
