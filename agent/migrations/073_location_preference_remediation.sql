-- Migration 073: quarantine legacy location data and enforce provenance-safe tuples.

ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS location_reconfirm_required BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS location_provenance_version VARCHAR(32);

ALTER TABLE user_preferences
    ALTER COLUMN revision TYPE BIGINT;

ALTER TABLE user_preferences
    ADD CONSTRAINT ck_user_preferences_revision_json_safe
    CHECK (revision >= 0 AND revision <= 9007199254740991);

CREATE OR REPLACE FUNCTION vl360_region_text_is_safe(value TEXT)
RETURNS BOOLEAN
LANGUAGE SQL
IMMUTABLE
PARALLEL SAFE
AS $$
    SELECT value IS NULL OR (
        value !~ '(^|[^0-9])([0-9]{1,3}\.){3}[0-9]{1,3}([^0-9]|$)'
        AND value !~* '(^|[^0-9a-f])([0-9a-f]{1,4}:){2,7}[0-9a-f]{0,4}([^0-9a-f]|$)'
        AND value !~* '(^|[^0-9a-f:])::([0-9a-f]{1,4}:){0,6}[0-9a-f]{1,4}([^0-9a-f:]|$)'
        AND value !~* '(^|[^0-9a-f:])([0-9a-f]{1,4}:){1,7}:([^0-9a-f:]|$)'
        AND value !~* '(^|[^0-9a-f:])[0-9a-f]{1,4}::([0-9a-f]{1,4}:){0,5}[0-9a-f]{1,4}([^0-9a-f:]|$)'
        AND value !~ '^[[:space:]]*::[[:space:]]*$'
        AND value !~* '[-+]?[0-9]{1,3}(\.[0-9]+)?[[:space:]]*[,;/][[:space:]]*[-+]?[0-9]{1,3}(\.[0-9]+)?'
        AND value !~* '[0-9]{1,3}[[:space:]]*[°º][[:space:]]*[0-9]{1,2}'
        AND value !~* '[-+]?[0-9]{1,3}(\.[0-9]+)?[[:space:]]*[NSEW]'
    );
$$;

CREATE OR REPLACE FUNCTION vl360_resolver_region_is_normalized(
    resolver_region_id TEXT,
    resolver_region_label TEXT
)
RETURNS BOOLEAN
LANGUAGE SQL
IMMUTABLE
PARALLEL SAFE
AS $$
    SELECT
        resolver_region_id IS NOT NULL
        AND char_length(resolver_region_id) BETWEEN 1 AND 128
        AND resolver_region_id = regexp_replace(
            resolver_region_id,
            '^[[:space:]]+|[[:space:]]+$',
            '',
            'g'
        )
        AND resolver_region_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'
        AND (
            resolver_region_label IS NULL
            OR (
                char_length(resolver_region_label) BETWEEN 1 AND 160
                AND resolver_region_label = regexp_replace(
                    resolver_region_label,
                    '^[[:space:]]+|[[:space:]]+$',
                    '',
                    'g'
                )
            )
        );
$$;

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
       OR NOT vl360_region_text_is_safe(region_label)
       OR NOT COALESCE((
            (
                location_source = 'manual'
                AND location_provenance_version IS NULL
                AND (
                    (region_id = 'province-vl' AND region_label = 'Vĩnh Long' AND region_scope = 'province' AND location_accuracy = 'province')
                    OR (region_id = 'province-bt' AND region_label = 'Bến Tre' AND region_scope = 'province' AND location_accuracy = 'province')
                    OR (region_id = 'province-tv' AND region_label = 'Trà Vinh' AND region_scope = 'province' AND location_accuracy = 'province')
                    OR (region_id IS NULL AND region_label IS NULL AND region_scope = 'all' AND location_accuracy = 'unknown')
                )
            )
            OR (
                location_source = 'default'
                AND region_id IS NULL
                AND region_label IS NULL
                AND region_scope = 'unknown'
                AND location_accuracy = 'unknown'
                AND location_provenance_version IS NULL
            )
            OR (
                location_source IN ('gps', 'ip')
                AND vl360_resolver_region_is_normalized(region_id, region_label)
                AND region_scope IN ('ward', 'district', 'province')
                AND location_accuracy IN ('ward', 'district', 'province', 'unknown')
                AND location_enabled = TRUE
                AND location_consent_state = 'granted'
                AND location_provenance_version = 'resolver-v2'
            )
       ), FALSE)
       OR (
            location_reconfirm_required = TRUE
            AND NOT (
                location_source = 'default'
                AND region_id IS NULL
                AND region_label IS NULL
                AND region_scope = 'unknown'
                AND location_accuracy = 'unknown'
                AND location_enabled = FALSE
                AND location_consent_state = 'off'
                AND location_provenance_version IS NULL
            )
       );
    GET DIAGNOSTICS quarantined_count = ROW_COUNT;
    RAISE NOTICE 'NP-1.1 quarantined % legacy location preference rows', quarantined_count;
END $$;

ALTER TABLE user_preferences
    ADD CONSTRAINT ck_user_preferences_region_text_safe_v2
    CHECK (
        vl360_region_text_is_safe(region_id)
        AND vl360_region_text_is_safe(region_label)
    );

ALTER TABLE user_preferences
    ADD CONSTRAINT ck_user_preferences_region_tuple_v2
    CHECK (COALESCE((
        (
            location_source = 'manual'
            AND location_provenance_version IS NULL
            AND (
                (region_id = 'province-vl' AND region_label = 'Vĩnh Long' AND region_scope = 'province' AND location_accuracy = 'province')
                OR (region_id = 'province-bt' AND region_label = 'Bến Tre' AND region_scope = 'province' AND location_accuracy = 'province')
                OR (region_id = 'province-tv' AND region_label = 'Trà Vinh' AND region_scope = 'province' AND location_accuracy = 'province')
                OR (region_id IS NULL AND region_label IS NULL AND region_scope = 'all' AND location_accuracy = 'unknown')
            )
        )
        OR (
            location_source = 'default'
            AND region_id IS NULL
            AND region_label IS NULL
            AND region_scope = 'unknown'
            AND location_accuracy = 'unknown'
            AND location_provenance_version IS NULL
        )
        OR (
            location_source IN ('gps', 'ip')
            AND vl360_resolver_region_is_normalized(region_id, region_label)
            AND region_scope IN ('ward', 'district', 'province')
            AND location_accuracy IN ('ward', 'district', 'province', 'unknown')
            AND location_enabled = TRUE
            AND location_consent_state = 'granted'
            AND location_provenance_version = 'resolver-v2'
        )
    ), FALSE));

ALTER TABLE user_preferences
    ADD CONSTRAINT ck_user_preferences_reconfirm_state_v1
    CHECK (
        location_reconfirm_required = FALSE
        OR (
            location_source = 'default'
            AND region_id IS NULL
            AND region_label IS NULL
            AND region_scope = 'unknown'
            AND location_accuracy = 'unknown'
            AND location_enabled = FALSE
            AND location_consent_state = 'off'
            AND location_provenance_version IS NULL
        )
    );

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 73, '073_location_preference_remediation.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
