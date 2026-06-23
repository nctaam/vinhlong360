-- Q&A: đánh dấu "câu trả lời hay nhất" cho bài hỏi (post_type='question').
-- Áp prod: psql + ALTER TABLE posts OWNER... (posts đã thuộc vl360, chỉ ALTER cột → OK)

ALTER TABLE posts ADD COLUMN IF NOT EXISTS best_answer_id UUID;
