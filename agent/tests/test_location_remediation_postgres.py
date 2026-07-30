"""Apply migration 073 to a disposable pre-073 PostgreSQL database."""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import psycopg2
import psycopg2.errors
import psycopg2.extras
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import database as database_module  # noqa: E402
import user_preferences  # noqa: E402
from scripts.apply_migrations import (  # noqa: E402
    DEFAULT_MIGRATIONS,
    apply_sql_file,
    migration_files,
    record_schema_version,
    run as apply_migrations,
)

LIBPQ_CONNECTION_TARGET_ENV_VARS = (
    "PGHOST",
    "PGHOSTADDR",
    "PGPORT",
    "PGDATABASE",
    "PGSERVICE",
    "PGSERVICEFILE",
)


def _validate_test_database_url(url: str) -> str:
    if any(os.environ.get(variable) for variable in LIBPQ_CONNECTION_TARGET_ENV_VARS):
        raise pytest.UsageError(
            "LOCATION_REMEDIATION_TEST_DATABASE_URL must not inherit libpq "
            "connection-target environment defaults"
        )
    parsed = urlparse(url)
    try:
        effective = psycopg2.extensions.parse_dsn(url)
    except psycopg2.ProgrammingError as exc:
        raise pytest.UsageError(
            "LOCATION_REMEDIATION_TEST_DATABASE_URL must be a valid PostgreSQL URL"
        ) from exc

    host = effective.get("host", "")
    hostaddr = effective.get("hostaddr", "")
    database_name = effective.get("dbname", "")
    loopback_hosts = {"127.0.0.1", "localhost", "::1"}
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or "service" in effective
        or "," in host
        or "," in hostaddr
        or host not in loopback_hosts
        or (hostaddr and hostaddr not in loopback_hosts)
        or "test" not in database_name.lower()
    ):
        raise pytest.UsageError(
            "LOCATION_REMEDIATION_TEST_DATABASE_URL must resolve to a single "
            "loopback PostgreSQL test database"
        )
    return url


def _test_database_url() -> str | None:
    url = os.environ.get("LOCATION_REMEDIATION_TEST_DATABASE_URL")
    return _validate_test_database_url(url) if url else None


def _connect_test_database():
    assert TEST_DATABASE_URL is not None
    return psycopg2.connect(_validate_test_database_url(TEST_DATABASE_URL))


TEST_DATABASE_URL = _test_database_url()
pg_only = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set LOCATION_REMEDIATION_TEST_DATABASE_URL to a disposable PostgreSQL DB",
)

LEGACY_CASES = {
    "raw-ip": ("203.0.113.9", "203.0.113.9", "manual"),
    "raw-coordinate": ("10.2500,105.9700", "10.2500, 105.9700", "manual"),
    "arbitrary-manual": ("district-untrusted", "Khu vực tự khai", "manual"),
    "legacy-gps": ("province-vl", "Vĩnh Long", "gps"),
    "legacy-ip": ("province-vl", "Vĩnh Long", "ip"),
}


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://user:password@localhost/my_test_db?host=prod.example.com",
        "postgresql://user:password@localhost/my_test_db?hostaddr=203.0.113.9",
        "postgresql://user:password@localhost/my_test_db?dbname=production",
        "postgresql://user:password@localhost/my_test_db?service=production",
        "postgresql://user:password@localhost/my_test_db?host=localhost%2Cprod.example.com",
    ],
    ids=["host-override", "hostaddr-override", "dbname-override", "service", "multi-host"],
)
def test_database_url_guard_rejects_libpq_effective_parameter_bypasses(
    monkeypatch, database_url
):
    monkeypatch.setenv("LOCATION_REMEDIATION_TEST_DATABASE_URL", database_url)

    with pytest.raises(pytest.UsageError, match="loopback PostgreSQL test database"):
        _test_database_url()


def test_database_url_guard_accepts_single_loopback_test_database(monkeypatch):
    database_url = "postgresql://user:password@127.0.0.1/np11_test"
    for variable in LIBPQ_CONNECTION_TARGET_ENV_VARS:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("LOCATION_REMEDIATION_TEST_DATABASE_URL", database_url)

    assert _test_database_url() == database_url


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("PGHOST", "prod.example.com"),
        ("PGHOSTADDR", "203.0.113.9"),
        ("PGPORT", "6543"),
        ("PGDATABASE", "production"),
        ("PGSERVICE", "production"),
        ("PGSERVICEFILE", "unsafe-service.conf"),
    ],
)
def test_database_url_guard_rejects_libpq_environment_target_defaults(
    monkeypatch, variable, value
):
    database_url = "postgresql://user:password@127.0.0.1/np11_test"
    for environment_variable in LIBPQ_CONNECTION_TARGET_ENV_VARS:
        monkeypatch.delenv(environment_variable, raising=False)
    monkeypatch.setenv("LOCATION_REMEDIATION_TEST_DATABASE_URL", database_url)
    monkeypatch.setenv(variable, value)

    with pytest.raises(pytest.UsageError, match="libpq connection-target environment"):
        _test_database_url()


@pytest.fixture
def pre73_database(tmp_path):
    assert TEST_DATABASE_URL is not None
    migrations_dir = tmp_path / "migrations-through-072"
    migrations_dir.mkdir()
    for migration in migration_files(DEFAULT_MIGRATIONS):
        if migration.version <= 72:
            shutil.copy2(migration.path, migrations_dir / migration.path.name)

    with _connect_test_database() as conn:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE")
            cursor.execute("CREATE SCHEMA public")

    apply_migrations(
        _validate_test_database_url(TEST_DATABASE_URL),
        migrations_dir=migrations_dir,
        init_baseline=True,
    )
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    return adapter


def apply_migration_073():
    assert TEST_DATABASE_URL is not None
    migration = DEFAULT_MIGRATIONS / "073_location_preference_remediation.sql"
    with _connect_test_database() as conn:
        with conn.cursor() as cursor:
            apply_sql_file(cursor, migration)
            record_schema_version(cursor, 73, migration.name)
        conn.commit()


def _insert_preference(
    cursor,
    *,
    user_id: str,
    region_id: str | None,
    region_label: str | None,
    region_scope: str,
    source: str,
    accuracy: str,
    consent: str = "off",
    enabled: bool = False,
    revision: int = 7,
) -> None:
    cursor.execute(
        """
        INSERT INTO user_preferences (
            user_id, region_id, region_label, region_scope, location_source,
            location_accuracy, location_consent_state, location_enabled,
            personalization_enabled, explicit_interests,
            recommendation_reset_at, consent_version, revision
        ) VALUES (
            %s::uuid, %s, %s, %s, %s, %s, %s, %s,
            TRUE, %s::jsonb, %s, 'privacy-v1', %s
        )
        """,
        (
            user_id,
            region_id,
            region_label,
            region_scope,
            source,
            accuracy,
            consent,
            enabled,
            json.dumps(["food", "culture"]),
            datetime(2026, 7, 1, 12, tzinfo=timezone.utc),
            revision,
        ),
    )


def _seed_pre73_rows() -> dict[str, str]:
    assert TEST_DATABASE_URL is not None
    users = {name: str(uuid4()) for name in (*LEGACY_CASES, "canonical-manual", "manual-all", "default-off")}
    with _connect_test_database() as conn:
        with conn.cursor() as cursor:
            for name, user_id in users.items():
                cursor.execute(
                    "INSERT INTO users (id, phone) VALUES (%s::uuid, %s)",
                    (user_id, f"np11-{name}-{uuid4().hex}"),
                )

            for name, (region_id, region_label, source) in LEGACY_CASES.items():
                scope = "district" if name == "arbitrary-manual" else "province"
                accuracy = "district" if name == "arbitrary-manual" else "province"
                _insert_preference(
                    cursor,
                    user_id=users[name],
                    region_id=region_id,
                    region_label=region_label,
                    region_scope=scope,
                    source=source,
                    accuracy=accuracy,
                    consent="granted" if source in {"gps", "ip"} else "off",
                    enabled=source in {"gps", "ip"},
                )

            _insert_preference(
                cursor,
                user_id=users["canonical-manual"],
                region_id="province-vl",
                region_label="Vĩnh Long",
                region_scope="province",
                source="manual",
                accuracy="province",
            )
            _insert_preference(
                cursor,
                user_id=users["manual-all"],
                region_id=None,
                region_label=None,
                region_scope="all",
                source="manual",
                accuracy="unknown",
            )
            _insert_preference(
                cursor,
                user_id=users["default-off"],
                region_id=None,
                region_label=None,
                region_scope="unknown",
                source="default",
                accuracy="unknown",
            )

            owner = users["raw-ip"]
            cursor.execute(
                """
                INSERT INTO user_preference_consents
                    (user_id, consent_type, state, version)
                VALUES (%s::uuid, 'personalization', 'granted', 'privacy-v1')
                """,
                (owner,),
            )
            cursor.execute(
                """
                INSERT INTO user_personalization_events
                    (user_id, event_type, context, interest_keys)
                VALUES (%s::uuid, 'entity_view', 'entity', '["food"]'::jsonb)
                """,
                (owner,),
            )
            cursor.execute(
                """
                INSERT INTO saved_entities (user_id, entity_id, kind, snapshot)
                VALUES (%s::uuid, 'workspace-np11', 'itinerary', '{"title":"Workspace NP-1.1"}'::jsonb)
                """,
                (owner,),
            )
    return users


def _preference_rows(users: dict[str, str]) -> dict[str, dict]:
    assert TEST_DATABASE_URL is not None
    names_by_user_id = {user_id: name for name, user_id in users.items()}
    with _connect_test_database() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM user_preferences")
            return {
                names_by_user_id[str(row["user_id"])]: dict(row)
                for row in cursor.fetchall()
            }


def _assert_constraint_violation(sql: str, params: tuple, constraint: str) -> None:
    assert TEST_DATABASE_URL is not None
    with pytest.raises(psycopg2.errors.CheckViolation) as exc_info:
        with _connect_test_database() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
    assert exc_info.value.diag.constraint_name == constraint


def _drop_location_constraints() -> None:
    with _connect_test_database() as conn:
        with conn.cursor() as cursor:
            for constraint in (
                "ck_user_preferences_region_text_safe_v2",
                "ck_user_preferences_region_tuple_v2",
                "ck_user_preferences_reconfirm_state_v1",
            ):
                cursor.execute(
                    f"ALTER TABLE user_preferences DROP CONSTRAINT {constraint}"
                )


def _restore_location_constraints() -> None:
    with _connect_test_database() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                ALTER TABLE user_preferences
                ADD CONSTRAINT ck_user_preferences_region_text_safe_v2
                CHECK (
                    vl360_region_text_is_safe(region_id)
                    AND vl360_region_text_is_safe(region_label)
                )
                """
            )
            cursor.execute(
                """
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
                        AND region_id IS NOT NULL
                        AND region_scope IN ('ward', 'district', 'province')
                        AND location_accuracy IN ('ward', 'district', 'province', 'unknown')
                        AND location_enabled = TRUE
                        AND location_consent_state = 'granted'
                        AND location_provenance_version = 'resolver-v2'
                    )
                ), FALSE))
                """
            )
            cursor.execute(
                """
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
                )
                """
            )
            cursor.execute(
                "SELECT conname FROM pg_constraint WHERE conrelid = 'user_preferences'::regclass"
            )
            constraints = {row[0] for row in cursor.fetchall()}
    assert {
        "ck_user_preferences_region_text_safe_v2",
        "ck_user_preferences_region_tuple_v2",
        "ck_user_preferences_reconfirm_state_v1",
    } <= constraints


@pg_only
def test_073_quarantines_legacy_location_without_erasing_personal_data(pre73_database):
    assert TEST_DATABASE_URL is not None
    users = _seed_pre73_rows()
    with _connect_test_database() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            tables_before = {row[0] for row in cursor.fetchall()}

    apply_migration_073()

    rows = _preference_rows(users)
    quarantined = {
        "region_id": None,
        "region_label": None,
        "region_scope": "unknown",
        "location_source": "default",
        "location_accuracy": "unknown",
        "location_consent_state": "off",
        "location_enabled": False,
        "location_provenance_version": None,
        "location_reconfirm_required": True,
    }
    for name in LEGACY_CASES:
        assert {key: rows[name][key] for key in quarantined} == quarantined
        assert rows[name]["revision"] == 8
        assert rows[name]["personalization_enabled"] is True
        assert rows[name]["explicit_interests"] == ["food", "culture"]
        assert rows[name]["recommendation_reset_at"] == datetime(
            2026, 7, 1, 12, tzinfo=timezone.utc
        )
        assert rows[name]["consent_version"] == "privacy-v1"

    assert {
        key: rows["canonical-manual"][key]
        for key in (
            "region_id", "region_label", "region_scope", "location_source",
            "location_accuracy", "location_reconfirm_required", "revision",
        )
    } == {
        "region_id": "province-vl",
        "region_label": "Vĩnh Long",
        "region_scope": "province",
        "location_source": "manual",
        "location_accuracy": "province",
        "location_reconfirm_required": False,
        "revision": 7,
    }
    assert {
        key: rows["manual-all"][key]
        for key in (
            "region_id", "region_label", "region_scope", "location_source",
            "location_accuracy", "location_reconfirm_required", "revision",
        )
    } == {
        "region_id": None,
        "region_label": None,
        "region_scope": "all",
        "location_source": "manual",
        "location_accuracy": "unknown",
        "location_reconfirm_required": False,
        "revision": 7,
    }
    assert rows["default-off"]["location_source"] == "default"
    assert rows["default-off"]["location_reconfirm_required"] is False
    assert rows["default-off"]["revision"] == 7

    with _connect_test_database() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM user_preference_consents WHERE user_id = %s::uuid) AS consents,
                    (SELECT COUNT(*) FROM user_personalization_events WHERE user_id = %s::uuid) AS events,
                    (SELECT COUNT(*) FROM saved_entities WHERE user_id = %s::uuid AND entity_id = 'workspace-np11') AS workspace
                """,
                (users["raw-ip"], users["raw-ip"], users["raw-ip"]),
            )
            assert dict(cursor.fetchone()) == {
                "consents": 1,
                "events": 1,
                "workspace": 1,
            }
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            assert {row["table_name"] for row in cursor.fetchall()} == tables_before


@pg_only
def test_073_installs_schema_function_and_enforces_write_guards(pre73_database):
    assert TEST_DATABASE_URL is not None
    users = _seed_pre73_rows()
    apply_migration_073()

    with _connect_test_database() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT column_name, data_type, character_maximum_length,
                       is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'user_preferences'
                  AND column_name IN (
                      'location_reconfirm_required',
                      'location_provenance_version',
                      'revision'
                  )
                """
            )
            columns = {row["column_name"]: dict(row) for row in cursor.fetchall()}
            assert columns["location_provenance_version"] == {
                "column_name": "location_provenance_version",
                "data_type": "character varying",
                "character_maximum_length": 32,
                "is_nullable": "YES",
                "column_default": None,
            }
            assert columns["location_reconfirm_required"] == {
                "column_name": "location_reconfirm_required",
                "data_type": "boolean",
                "character_maximum_length": None,
                "is_nullable": "NO",
                "column_default": "false",
            }
            assert columns["revision"]["data_type"] == "bigint"
            cursor.execute(
                """
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'user_preferences'::regclass
                """
            )
            constraints = {row["conname"] for row in cursor.fetchall()}
            assert {
                "ck_user_preferences_revision_json_safe",
                "ck_user_preferences_region_text_safe_v2",
                "ck_user_preferences_region_tuple_v2",
                "ck_user_preferences_reconfirm_state_v1",
            } <= constraints
            cursor.execute(
                """
                SELECT
                    vl360_region_text_is_safe('Vĩnh Long') AS safe_label,
                    vl360_region_text_is_safe('203.0.113.9') AS raw_ip,
                    vl360_region_text_is_safe('10.2500, 105.9700') AS coordinate,
                    vl360_region_text_is_safe('::1') AS loopback_ipv6,
                    vl360_region_text_is_safe('::dead:beef') AS compressed_ipv6,
                    vl360_region_text_is_safe('::') AS all_zero_ipv6,
                    vl360_region_text_is_safe('fe80::') AS trailing_compressed_ipv6,
                    vl360_region_text_is_safe('2001:db8::1') AS embedded_compressed_ipv6,
                    vl360_region_text_is_safe('0::1') AS zero_prefix_compressed_ipv6,
                    vl360_region_text_is_safe('a::b') AS hex_prefix_compressed_ipv6,
                    vl360_region_text_is_safe('f::1') AS short_prefix_compressed_ipv6,
                    vl360_region_text_is_safe(
                        '1::dead:beef'
                    ) AS one_prefix_multi_suffix_ipv6,
                    vl360_region_text_is_safe(
                        '2001:db8:85a3:0:0:8a2e:370:7334'
                    ) AS full_ipv6
                """
            )
            assert dict(cursor.fetchone()) == {
                "safe_label": True,
                "raw_ip": False,
                "coordinate": False,
                "loopback_ipv6": False,
                "compressed_ipv6": False,
                "all_zero_ipv6": False,
                "trailing_compressed_ipv6": False,
                "embedded_compressed_ipv6": False,
                "zero_prefix_compressed_ipv6": False,
                "hex_prefix_compressed_ipv6": False,
                "short_prefix_compressed_ipv6": False,
                "one_prefix_multi_suffix_ipv6": False,
                "full_ipv6": False,
            }

    _assert_constraint_violation(
        """
        UPDATE user_preferences
        SET region_id = 'district-untrusted', region_label = 'Khu vực tự khai',
            region_scope = 'district', location_accuracy = 'district'
        WHERE user_id = %s::uuid
        """,
        (users["canonical-manual"],),
        "ck_user_preferences_region_tuple_v2",
    )
    _assert_constraint_violation(
        """
        UPDATE user_preferences
        SET location_reconfirm_required = TRUE, location_enabled = TRUE
        WHERE user_id = %s::uuid
        """,
        (users["default-off"],),
        "ck_user_preferences_reconfirm_state_v1",
    )
    for raw_ip in (
        "203.0.113.9",
        "::",
        "::1",
        "::dead:beef",
        "fe80::",
        "2001:db8::1",
        "0::1",
        "a::b",
        "f::1",
        "1::dead:beef",
        "2001:db8:85a3:0:0:8a2e:370:7334",
    ):
        _assert_constraint_violation(
            """
            UPDATE user_preferences
            SET region_id = 'province-vl', region_label = %s,
                region_scope = 'province', location_source = 'gps',
                location_accuracy = 'province', location_consent_state = 'granted',
                location_enabled = TRUE, location_provenance_version = 'resolver-v2',
                location_reconfirm_required = FALSE
            WHERE user_id = %s::uuid
            """,
            (raw_ip, users["raw-ip"]),
            "ck_user_preferences_region_text_safe_v2",
        )
    _assert_constraint_violation(
        "UPDATE user_preferences SET revision = 9007199254740992 WHERE user_id = %s::uuid",
        (users["default-off"],),
        "ck_user_preferences_revision_json_safe",
    )

    with _connect_test_database() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE user_preferences
                SET region_id = 'province-vl', region_label = 'Vĩnh Long',
                    region_scope = 'province', location_source = 'gps',
                    location_accuracy = 'province', location_consent_state = 'granted',
                    location_enabled = TRUE, location_provenance_version = 'resolver-v2',
                    location_reconfirm_required = FALSE
                WHERE user_id = %s::uuid
                """,
                (users["raw-ip"],),
            )
            cursor.execute(
                "SELECT version FROM schema_version WHERE component = 'agent'"
            )
            assert cursor.fetchone()[0] == 73


@pg_only
def test_self_healing_worker_is_bounded_idempotent_and_preserves_non_location_state(
    pre73_database, monkeypatch
):
    monkeypatch.setattr(user_preferences, "db", pre73_database)
    assert TEST_DATABASE_URL is not None

    apply_migration_073()
    invalid_users = [str(uuid4()) for _ in range(105)]
    valid_users = {"canonical": str(uuid4()), "default": str(uuid4())}
    _drop_location_constraints()
    with _connect_test_database() as conn:
        with conn.cursor() as cursor:
            for index, user_id in enumerate([*invalid_users, *valid_users.values()]):
                cursor.execute(
                    "INSERT INTO users (id, phone) VALUES (%s::uuid, %s)",
                    (user_id, f"np11-worker-{index}-{uuid4().hex}"),
                )
            for user_id in invalid_users:
                _insert_preference(
                    cursor,
                    user_id=user_id,
                    region_id="203.0.113.9",
                    region_label="203.0.113.9",
                    region_scope="district",
                    source="manual",
                    accuracy="district",
                )
            _insert_preference(
                cursor,
                user_id=valid_users["canonical"],
                region_id="province-vl",
                region_label="Vĩnh Long",
                region_scope="province",
                source="manual",
                accuracy="province",
            )
            _insert_preference(
                cursor,
                user_id=valid_users["default"],
                region_id=None,
                region_label=None,
                region_scope="unknown",
                source="default",
                accuracy="unknown",
            )

    first = user_preferences.quarantine_invalid_preferences_batch(limit=100)
    assert sum(first.values()) == 100

    second = user_preferences.quarantine_invalid_preferences_batch(limit=100)
    assert sum(second.values()) == 5

    third = user_preferences.quarantine_invalid_preferences_batch(limit=100)
    assert sum(third.values()) == 0

    with _connect_test_database() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT region_id, region_label, region_scope, location_source,
                       location_accuracy, location_consent_state, location_enabled,
                       location_reconfirm_required, location_provenance_version,
                       explicit_interests, personalization_enabled, revision
                FROM user_preferences
                WHERE user_id = ANY(%s::uuid[])
                """,
                (invalid_users,),
            )
            healed = [dict(row) for row in cursor.fetchall()]
            assert len(healed) == 105
            for row in healed:
                assert row["region_id"] is None
                assert row["region_label"] is None
                assert row["region_scope"] == "unknown"
                assert row["location_source"] == "default"
                assert row["location_accuracy"] == "unknown"
                assert row["location_consent_state"] == "off"
                assert row["location_enabled"] is False
                assert row["location_reconfirm_required"] is True
                assert row["location_provenance_version"] is None
                assert row["explicit_interests"] == ["food", "culture"]
                assert row["personalization_enabled"] is True
                assert row["revision"] == 8

            cursor.execute(
                """
                SELECT region_id, region_scope, location_source, revision
                FROM user_preferences
                WHERE user_id = %s::uuid
                """,
                (valid_users["canonical"],),
            )
            assert dict(cursor.fetchone()) == {
                "region_id": "province-vl",
                "region_scope": "province",
                "location_source": "manual",
                "revision": 7,
            }

    _restore_location_constraints()


@pg_only
def test_self_healing_worker_aligns_candidate_and_reason_text_boundaries(
    pre73_database, monkeypatch
):
    monkeypatch.setattr(user_preferences, "db", pre73_database)
    assert TEST_DATABASE_URL is not None

    apply_migration_073()
    _drop_location_constraints()
    unsafe_labels = {
        "coordinate_pair": "10.2500 and 105.9700",
        "dms": '10° 15\' 30" N',
        "hemisphere": "10.2500N",
        "single_number": "105.9700",
        "sql_only": "a:b:c",
        "unicode_decimal": "١٠.٥",
        "unicode_pair": "١٠ and ١٠٥",
        "fullwidth_decimal": "１０.５",
        "unicode_signed": "-١٠.٥",
        "unicode_dms": '١٠° ١٥\' ٣٠" N',
    }
    for name in ("coordinate_pair", "dms", "hemisphere", "single_number"):
        assert user_preferences.contains_raw_location_value(unsafe_labels[name])
    for name in (
        "unicode_decimal",
        "unicode_pair",
        "fullwidth_decimal",
        "unicode_signed",
        "unicode_dms",
    ):
        assert user_preferences.contains_raw_location_value(unsafe_labels[name])
    assert not user_preferences.contains_raw_location_value(unsafe_labels["sql_only"])
    assert not user_preferences.contains_raw_location_value("999.9700")
    users = {
        name: str(uuid4())
        for name in (*unsafe_labels, "valid", "safe_out_of_range_number")
    }
    with _connect_test_database() as conn:
        with conn.cursor() as cursor:
            for index, (name, user_id) in enumerate(users.items()):
                cursor.execute(
                    "INSERT INTO users (id, phone) VALUES (%s::uuid, %s)",
                    (user_id, f"np11-parity-{index}-{uuid4().hex}"),
                )
                _insert_preference(
                    cursor,
                    user_id=user_id,
                    region_id="province-vl",
                    region_label=unsafe_labels.get(
                        name,
                        "999.9700"
                        if name == "safe_out_of_range_number"
                        else "Vĩnh Long",
                    ),
                    region_scope="province",
                    source="gps",
                    accuracy="province",
                    consent="granted",
                    enabled=True,
                )
                cursor.execute(
                    "UPDATE user_preferences SET location_provenance_version = 'resolver-v2' "
                    "WHERE user_id = %s::uuid",
                    (user_id,),
                )

    counts = user_preferences.quarantine_invalid_preferences_batch(limit=100)
    assert counts == {"raw_shape": len(unsafe_labels)}

    with _connect_test_database() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT user_id, region_id, region_label, location_source,
                       location_reconfirm_required, revision
                FROM user_preferences
                """
            )
            rows = {str(row["user_id"]): dict(row) for row in cursor.fetchall()}
    for name in unsafe_labels:
        row = rows[users[name]]
        assert row["region_id"] is None
        assert row["region_label"] is None
        assert row["location_source"] == "default"
        assert row["location_reconfirm_required"] is True
        assert row["revision"] == 8
    assert rows[users["valid"]]["region_label"] == "Vĩnh Long"
    assert rows[users["valid"]]["revision"] == 7
    assert (
        rows[users["safe_out_of_range_number"]]["region_label"] == "999.9700"
    )
    assert rows[users["safe_out_of_range_number"]]["revision"] == 7

    _restore_location_constraints()
