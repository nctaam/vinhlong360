-- Threads-style Repost + Quote: đăng lại bài người khác (kèm/không kèm bình luận).
-- repost_of = id bài gốc; repost_snapshot = ảnh-chụp bài gốc lúc đăng-lại (id/author/content/
-- created_at) → render embedded không cần JOIN, vẫn ổn nếu bài gốc bị xoá.
-- Áp prod: ALTER posts (đã thuộc vl360 → OK, không cần ALTER OWNER).

ALTER TABLE posts ADD COLUMN IF NOT EXISTS repost_of UUID;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS repost_snapshot JSONB;
