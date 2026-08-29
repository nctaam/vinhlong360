-- Migration 082: dạy vl360_region_text_is_safe nhận diện CHỮ SỐ UNICODE.
--
-- Bối cảnh (ROADMAP §48.4, đợt fix 20f234f0): các pattern [0-9] ASCII của hàm
-- 078 không khớp chữ số Ả-Rập-Ấn (U+0660-0669), Ả-Rập-Ấn mở rộng (U+06F0-06F9)
-- và fullwidth (U+FF10-FF19) — toạ độ thô viết bằng các chữ số đó lọt CHECK
-- constraint ở tầng SQL. Worker tự-chữa đã được vá cùng bảng translate
-- (agent/user_preferences.py); migration này đưa CHECK về cùng parity, rồi
-- quarantine các row tồn đọng đang vi phạm theo định nghĩa mới — đúng khuôn
-- quarantine của 078 (SET-list giữ nguyên từng ô).

CREATE OR REPLACE FUNCTION vl360_digit_fold(value TEXT)
RETURNS TEXT
LANGUAGE SQL
IMMUTABLE
PARALLEL SAFE
AS $$
    SELECT translate(
        value,
        '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹０１２３４５６７８９',
        '012345678901234567890123456789'
    );
$$;

-- Cùng thân với bản 078, chỉ khác: mọi pattern so trên bản đã gấp chữ số về
-- ASCII. CHECK constraint ck_user_preferences_region_text_safe_v2 tham chiếu
-- hàm theo tên nên tự dùng định nghĩa mới cho mọi ghi MỚI; row cũ xử ở DO dưới.
CREATE OR REPLACE FUNCTION vl360_region_text_is_safe(value TEXT)
RETURNS BOOLEAN
LANGUAGE SQL
IMMUTABLE
PARALLEL SAFE
AS $$
    SELECT value IS NULL OR (
        vl360_digit_fold(value) !~ '(^|[^0-9])([0-9]{1,3}\.){3}[0-9]{1,3}([^0-9]|$)'
        AND vl360_digit_fold(value) !~* '(^|[^0-9a-f])([0-9a-f]{1,4}:){2,7}[0-9a-f]{0,4}([^0-9a-f]|$)'
        AND vl360_digit_fold(value) !~* '(^|[^0-9a-f:])::([0-9a-f]{1,4}:){0,6}[0-9a-f]{1,4}([^0-9a-f:]|$)'
        AND vl360_digit_fold(value) !~* '(^|[^0-9a-f:])([0-9a-f]{1,4}:){1,7}:([^0-9a-f:]|$)'
        AND vl360_digit_fold(value) !~* '(^|[^0-9a-f:])[0-9a-f]{1,4}::([0-9a-f]{1,4}:){0,5}[0-9a-f]{1,4}([^0-9a-f:]|$)'
        AND vl360_digit_fold(value) !~ '^[[:space:]]*::[[:space:]]*$'
        AND vl360_digit_fold(value) !~* '[-+]?[0-9]{1,3}(\.[0-9]+)?[[:space:]]*[,;/][[:space:]]*[-+]?[0-9]{1,3}(\.[0-9]+)?'
        AND vl360_digit_fold(value) !~* '[0-9]{1,3}[[:space:]]*[°º][[:space:]]*[0-9]{1,2}'
        AND vl360_digit_fold(value) !~* '[-+]?[0-9]{1,3}(\.[0-9]+)?[[:space:]]*[NSEW]'
    );
$$;

-- Quarantine row tồn đọng nay vi phạm định nghĩa mới. Chỉ nhắm phần text-safety
-- (các lớp bất-hợp-lệ khác 078 đã càn rồi); SET-list y hệt 078 để ngữ nghĩa
-- quarantine không phân kỳ.
DO $$
DECLARE
    quarantined_count BIGINT;
BEGIN
    UPDATE user_preferences
    SET region_id = NULL,
        region_label = NULL,
        region_scope = 'unknown',
        location_source = 'default',
        location_accuracy = 'unknown',
        location_consent_state = 'off',
        location_enabled = FALSE,
        location_provenance_version = NULL,
        location_reconfirm_required = TRUE,
        revision = revision + 1,
        updated_at = NOW()
    WHERE NOT vl360_region_text_is_safe(region_id)
       OR NOT vl360_region_text_is_safe(region_label);
    GET DIAGNOSTICS quarantined_count = ROW_COUNT;
    RAISE NOTICE '082 quarantined % unicode-digit location rows', quarantined_count;
END $$;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 82, '082_unicode_digit_region_safety.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
