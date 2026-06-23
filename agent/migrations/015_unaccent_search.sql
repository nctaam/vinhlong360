-- Tìm kiếm KHÔNG phân-biệt-dấu (người Việt gõ "ao ba om" → "Ao Bà Om").
-- f_unaccent: bọc unaccent ở dạng IMMUTABLE (chỉ-định dict tường-minh) để dùng
-- được trong functional index. GIN trigram trên f_unaccent(lower(...)) → vừa
-- không-dấu vừa nhanh. Additive, an toàn.
-- Áp prod: sudo -u postgres psql -d vinhlong360 -f agent/migrations/015_unaccent_search.sql

CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS
$$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$;

-- posts: nội dung bài viết
CREATE INDEX IF NOT EXISTS idx_posts_content_unaccent
    ON posts USING GIN (f_unaccent(lower(content)) gin_trgm_ops);

-- entities: tên + tóm tắt
CREATE INDEX IF NOT EXISTS idx_entities_name_unaccent
    ON entities USING GIN (f_unaccent(lower(name)) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_entities_summary_unaccent
    ON entities USING GIN (f_unaccent(lower(summary)) gin_trgm_ops);
