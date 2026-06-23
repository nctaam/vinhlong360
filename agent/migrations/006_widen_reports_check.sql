-- P0-14: nới CHECK của bảng reports cho khớp code.
-- ReportRequest cho phép target_type='entity'; admin resolve_report set status='resolved'.
-- Trước đây CHECK chỉ (post,comment,user) + (pending,reviewed,dismissed) → INSERT/UPDATE
-- các giá trị trên sẽ vi phạm CHECK → 500. Nới CHECK = AN TOÀN (không row cũ nào vi phạm).
-- Áp trên prod: psql "$DATABASE_URL" -f agent/migrations/006_widen_reports_check.sql

ALTER TABLE reports DROP CONSTRAINT IF EXISTS reports_target_type_check;
ALTER TABLE reports ADD CONSTRAINT reports_target_type_check
    CHECK (target_type IN ('post', 'comment', 'user', 'entity', 'facility'));

ALTER TABLE reports DROP CONSTRAINT IF EXISTS reports_status_check;
ALTER TABLE reports ADD CONSTRAINT reports_status_check
    CHECK (status IN ('pending', 'reviewed', 'dismissed', 'resolved'));
