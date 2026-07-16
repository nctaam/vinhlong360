from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from contextlib import ExitStack, closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import pytest

from scripts import migrate_entity_status as migration
from scripts.postgres_target import canonical_json_bytes, sha256_bytes


pytestmark = pytest.mark.entity_status_postgres
TEST_URL = os.environ.get("ENTITY_STATUS_TEST_DATABASE_URL")
TEST_CONFIRM = os.environ.get("ENTITY_STATUS_TEST_CONFIRM")
NOW = datetime(2026, 7, 15, 12, 10, tzinfo=UTC)
RESTORE_LISTING = (
    "; disposable PostgreSQL integration listing\n"
    "1; 1259 100 TABLE public entities owner\n"
    "2; 1259 101 TABLE public entity_changes owner\n"
)
FUNCTION_ACL_LOCK_NAME = "vinhlong360:entity-identity:pg-control-system-acl-v1"


def _disposable_database_url() -> str:
    if TEST_CONFIRM != "disposable":
        pytest.skip(
            "set ENTITY_STATUS_TEST_CONFIRM=disposable for the disposable database"
        )
    if not TEST_URL:
        pytest.skip(
            "set ENTITY_STATUS_TEST_DATABASE_URL to a disposable PostgreSQL database"
        )
    try:
        parsed = urlsplit(TEST_URL)
    except ValueError:
        pytest.skip("ENTITY_STATUS_TEST_DATABASE_URL is not a valid PostgreSQL URL")
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or not parsed.netloc
        or not parsed.hostname
    ):
        pytest.skip(
            "ENTITY_STATUS_TEST_DATABASE_URL must be a PostgreSQL URL with a host"
        )
    try:
        parsed.port
    except ValueError:
        pytest.skip("ENTITY_STATUS_TEST_DATABASE_URL has an invalid port")
    return TEST_URL


def _role_url(base_url: str, role: str, password: str) -> str:
    try:
        parsed = urlsplit(base_url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise AssertionError("base URL must have a valid PostgreSQL host") from exc
    if parsed.scheme not in {"postgres", "postgresql"} or not hostname:
        raise AssertionError("base URL must be a PostgreSQL URL with a host")
    host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        host = f"{host}:{port}"
    netloc = f"{quote(role, safe='')}:{quote(password, safe='')}@{host}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, ""))


def _quote_role(role: str) -> str:
    if not re.fullmatch(r"entity_identity_[0-9a-f]{32}", role):
        raise AssertionError("fixture role must be a safe generated role")
    return f'"{role}"'


def _acquire_function_acl_lock(cursor) -> None:
    cursor.execute(
        "SELECT pg_catalog.pg_advisory_lock("
        "pg_catalog.hashtextextended(%s, 0))",
        (FUNCTION_ACL_LOCK_NAME,),
    )


def _read_function_acl(cursor):
    cursor.execute(
        "SELECT proacl FROM pg_catalog.pg_proc "
        "WHERE oid = 'pg_catalog.pg_control_system()'::regprocedure"
    )
    row = cursor.fetchone()
    if row is None:
        raise AssertionError("pg_control_system function ACL snapshot is missing")
    return row[0]


def _verify_function_acl(cursor, function_acl) -> bool:
    cursor.execute(
        "SELECT proacl IS NOT DISTINCT FROM %s::pg_catalog.aclitem[] "
        "FROM pg_catalog.pg_proc "
        "WHERE oid = 'pg_catalog.pg_control_system()'::pg_catalog.regprocedure",
        (function_acl,),
    )
    row = cursor.fetchone()
    return row is not None and row[0] is True


def _release_function_acl_lock(cursor) -> bool:
    cursor.execute(
        "SELECT pg_catalog.pg_advisory_unlock("
        "pg_catalog.hashtextextended(%s, 0))",
        (FUNCTION_ACL_LOCK_NAME,),
    )
    row = cursor.fetchone()
    return row is not None and row[0] is True


def _restore_function_acl(cursor, function_acl) -> None:
    cursor.execute(
        "UPDATE pg_catalog.pg_proc SET proacl = %s::pg_catalog.aclitem[] "
        "WHERE oid = 'pg_catalog.pg_control_system()'::pg_catalog.regprocedure",
        (function_acl,),
    )


def _cleanup_identity_roles(
    *,
    admin,
    sql,
    roles: tuple[str, ...],
    created_roles: set[str],
    connect_granted_roles: set[str],
    database_name: str | None,
    allowed_role: str,
    read_granted: bool,
    function_granted: bool,
    function_acl,
    public_execute_revoked: bool,
    function_acl_snapshot_acquired: bool,
    acl_lock_acquired: bool,
) -> None:
    errors: list[str] = []
    acl_restore_succeeded = not public_execute_revoked
    acl_readback_succeeded = False

    def attempt(label: str, action) -> None:
        try:
            action()
        except Exception as exc:
            errors.append(f"{label} ({type(exc).__name__})")

    def execute(query, params=None) -> None:
        with admin.cursor() as cursor:
            if params is None:
                cursor.execute(query)
            else:
                cursor.execute(query, params)

    if admin is None:
        if created_roles or public_execute_revoked or acl_lock_acquired:
            errors.append("administrator connection was not opened")
    else:
        admin_closed = False
        try:
            admin_closed = bool(admin.closed)
        except Exception as exc:
            errors.append(f"administrator connection state ({type(exc).__name__})")
        if admin_closed:
            errors.append("administrator connection was closed before cleanup")
        else:
            attempt("administrator rollback", admin.rollback)
            attempt("administrator autocommit", lambda: setattr(admin, "autocommit", True))
            for role in roles:
                attempt(
                    "terminate generated role sessions",
                    lambda role=role: execute(
                        "SELECT pg_terminate_backend(pid) "
                        "FROM pg_catalog.pg_stat_activity "
                        "WHERE usename = %s AND pid <> pg_backend_pid()",
                        (role,),
                    ),
                )
            if database_name is not None:
                for role in connect_granted_roles:
                    attempt(
                        "revoke database connect",
                        lambda role=role: execute(
                            sql.SQL("REVOKE CONNECT ON DATABASE {} FROM {}").format(
                                sql.Identifier(database_name), sql.Identifier(role)
                            )
                        ),
                    )
            if read_granted:
                attempt(
                    "revoke read role",
                    lambda: execute(
                        sql.SQL("REVOKE pg_read_all_data FROM {}").format(
                            sql.Identifier(allowed_role)
                        )
                    ),
                )
            if function_granted:
                attempt(
                    "revoke function execute",
                    lambda: execute(
                        sql.SQL(
                            "REVOKE EXECUTE ON FUNCTION "
                            "pg_catalog.pg_control_system() FROM {}"
                        ).format(sql.Identifier(allowed_role))
                    ),
                )
            if public_execute_revoked:
                def restore_function_acl() -> None:
                    with admin.cursor() as cursor:
                        _restore_function_acl(cursor, function_acl)
                    nonlocal acl_restore_succeeded
                    acl_restore_succeeded = True

                attempt(
                    "restore function ACL",
                    restore_function_acl,
                )
            if acl_lock_acquired:
                if not function_acl_snapshot_acquired:
                    errors.append("function ACL snapshot was not acquired")
                else:
                    def verify_function_acl() -> None:
                        with admin.cursor() as cursor:
                            if not _verify_function_acl(cursor, function_acl):
                                raise AssertionError(
                                    "function ACL readback did not match snapshot"
                                )
                        nonlocal acl_readback_succeeded
                        acl_readback_succeeded = True

                    attempt("verify function ACL", verify_function_acl)
            for role in created_roles:
                attempt(
                    "drop generated role",
                    lambda role=role: execute(
                        sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role))
                    ),
                )
            if acl_lock_acquired:
                if acl_restore_succeeded and acl_readback_succeeded:
                    def release_function_acl_lock() -> None:
                        with admin.cursor() as cursor:
                            if not _release_function_acl_lock(cursor):
                                raise AssertionError(
                                    "function ACL advisory lock release was not confirmed"
                                )

                    attempt("release function ACL lock", release_function_acl_lock)
                else:
                    errors.append("function ACL advisory lock left for connection close")
        attempt("close administrator connection", admin.close)

    if errors:
        raise AssertionError(
            "restricted PostgreSQL role cleanup failed: " + "; ".join(errors)
        )


def _quote_schema(schema: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", schema):
        raise AssertionError("fixture schema must be a safe generated identifier")
    return f'"{schema}"'


def test_role_url_replaces_credentials_and_discards_fragment() -> None:
    base_url = (
        "postgresql://old%20role:old%2Fpassword@[2001:db8::1]:5433/vl360"
        "?sslmode=require#ignored"
    )
    role = "entity_identity_" + ("a" * 32)
    password = "p@ss/w%rd"

    assert _role_url(base_url, role, password) == (
        "postgresql://entity_identity_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:"
        "p%40ss%2Fw%25rd@[2001:db8::1]:5433/vl360?sslmode=require"
    )


@pytest.mark.parametrize(
    "role",
    [
        "entity_identity_" + ("a" * 31),
        "entity_identity_" + ("g" * 32),
        "entity_identity_other",
    ],
)
def test_quote_role_rejects_non_generated_identifiers(role: str) -> None:
    with pytest.raises(AssertionError, match="safe generated role"):
        _quote_role(role)


def test_disposable_database_url_skips_missing_hostname(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "tests.test_migrate_entity_status_postgres.TEST_URL",
        "postgresql://fixture@:5432/vl360",
    )
    monkeypatch.setattr(
        "tests.test_migrate_entity_status_postgres.TEST_CONFIRM", "disposable"
    )

    with pytest.raises(pytest.skip.Exception, match="host"):
        _disposable_database_url()


def test_restore_function_acl_uses_raw_aclitem_array() -> None:
    class RecordingCursor:
        def __init__(self) -> None:
            self.calls: list[tuple[str, tuple[object, ...]]] = []

        def execute(self, query: str, params: tuple[object, ...]) -> None:
            self.calls.append((query, params))

    cursor = RecordingCursor()
    acl = ["=X/postgres", "postgres=X/postgres"]

    _restore_function_acl(cursor, acl)

    assert cursor.calls == [
        (
            "UPDATE pg_catalog.pg_proc SET proacl = %s::pg_catalog.aclitem[] "
            "WHERE oid = 'pg_catalog.pg_control_system()'::pg_catalog.regprocedure",
            (acl,),
        )
    ]


def test_function_acl_lock_is_acquired_before_snapshot() -> None:
    class RecordingCursor:
        def __init__(self) -> None:
            self.calls: list[tuple[str, tuple[object, ...] | None]] = []

        def execute(
            self, query: str, params: tuple[object, ...] | None = None
        ) -> None:
            self.calls.append((query, params))

        def fetchone(self) -> tuple[list[str]]:
            return (["=X/postgres"],)

    cursor = RecordingCursor()

    _acquire_function_acl_lock(cursor)
    acl = _read_function_acl(cursor)

    assert acl == ["=X/postgres"]
    assert cursor.calls == [
        (
            "SELECT pg_catalog.pg_advisory_lock("
            "pg_catalog.hashtextextended(%s, 0))",
            ("vinhlong360:entity-identity:pg-control-system-acl-v1",),
        ),
        (
            "SELECT proacl FROM pg_catalog.pg_proc "
            "WHERE oid = 'pg_catalog.pg_control_system()'::regprocedure",
            None,
        ),
    ]


def test_cleanup_verifies_acl_before_unlocking_and_closing() -> None:
    events: list[str] = []

    class FakeSqlValue(str):
        def format(self, *args) -> str:
            return str(self).format(*args)

    class FakeSql:
        @staticmethod
        def SQL(value: str) -> FakeSqlValue:
            return FakeSqlValue(value)

        @staticmethod
        def Identifier(value: str) -> str:
            return f'"{value}"'

    class FakeCursor:
        row: tuple[bool] | None = None

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def execute(self, query, params=None) -> None:
            normalized = " ".join(str(query).split())
            events.append(normalized)
            if "proacl IS NOT DISTINCT FROM" in normalized:
                self.row = (True,)
            elif "pg_advisory_unlock" in normalized:
                self.row = (True,)

        def fetchone(self) -> tuple[bool] | None:
            return self.row

    class FakeAdmin:
        closed = False

        def rollback(self) -> None:
            events.append("rollback")

        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def close(self) -> None:
            events.append("close")

    role = "entity_identity_" + ("a" * 32)
    _cleanup_identity_roles(
        admin=FakeAdmin(),
        sql=FakeSql,
        roles=(role,),
        created_roles={role},
        connect_granted_roles={role},
        database_name="vl360",
        allowed_role=role,
        read_granted=True,
        function_granted=True,
        function_acl=["=X/postgres"],
        public_execute_revoked=True,
        function_acl_snapshot_acquired=True,
        acl_lock_acquired=True,
    )

    terminate = next(i for i, event in enumerate(events) if "pg_terminate" in event)
    restore = next(i for i, event in enumerate(events) if event.startswith("UPDATE"))
    verify = next(
        i for i, event in enumerate(events) if "proacl IS NOT DISTINCT FROM" in event
    )
    drop = next(i for i, event in enumerate(events) if event.startswith("DROP ROLE"))
    unlock = next(i for i, event in enumerate(events) if "pg_advisory_unlock" in event)
    close = events.index("close")

    assert terminate < restore < verify < drop < unlock < close


def test_cleanup_reports_closed_admin_connection() -> None:
    class ClosedAdmin:
        closed = True
        close_called = False

        def close(self) -> None:
            self.close_called = True

    admin = ClosedAdmin()

    with pytest.raises(AssertionError, match="closed before cleanup"):
        _cleanup_identity_roles(
            admin=admin,
            sql=None,
            roles=(),
            created_roles=set(),
            connect_granted_roles=set(),
            database_name=None,
            allowed_role="entity_identity_" + ("a" * 32),
            read_granted=False,
            function_granted=False,
            function_acl=None,
            public_execute_revoked=False,
            function_acl_snapshot_acquired=False,
            acl_lock_acquired=False,
        )

    assert admin.close_called is True


def _restore_listing_sha() -> str:
    return hashlib.sha256(RESTORE_LISTING.encode("utf-8")).hexdigest()


def _backup_evidence(
    tmp_path: Path, target: str, identity: dict[str, object]
) -> migration.BackupEvidence:
    root = tmp_path / "backup"
    root.mkdir()
    artifact = root / "postgres.dump"
    artifact.write_bytes(b"PGDMP-disposable-test")
    artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest = {
        "schema": "vinhlong360-pg-backup-v1",
        "target": "pg",
        "target_fingerprint": target,
        "database_identity": dict(identity),
        "started_at": "2026-07-15T12:00:00Z",
        "completed_at": "2026-07-15T12:00:01Z",
        "max_age_seconds": migration.MAX_BACKUP_AGE_SECONDS,
        "tools": {
            "pg_dump": "pg_dump (PostgreSQL) 16.4",
            "pg_restore": "pg_restore (PostgreSQL) 16.4",
        },
        "artifact": {
            "path": artifact.name,
            "size": artifact.stat().st_size,
            "sha256": artifact_sha,
        },
        "validation": {
            "pg_restore_list": True,
            "required_tables": ["entities", "entity_changes"],
            "listing_sha256": _restore_listing_sha(),
        },
        "policy_revision": "published-v1",
    }
    return migration.BackupEvidence(
        manifest=manifest,
        manifest_sha256=sha256_bytes(canonical_json_bytes(manifest)),
        artifact_root=root,
    )


def _rows(cursor) -> list[dict[str, object]]:
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def _audit_rows(cursor, schema: str) -> list[tuple[object, ...]]:
    quoted_schema = _quote_schema(schema)
    cursor.execute(
        f"SELECT entity_id, field, old_value, new_value, actor "
        f"FROM {quoted_schema}.entity_changes "
        "ORDER BY entity_id, actor, old_value, new_value"
    )
    return cursor.fetchall()


def _begin_serializable(connection) -> None:
    connection.set_session(
        isolation_level="SERIALIZABLE",
        readonly=False,
        autocommit=False,
    )
    assert connection.autocommit is False


def _assert_serializable(cursor) -> None:
    cursor.execute("SHOW transaction_isolation")
    assert cursor.fetchone() == ("serializable",)
    cursor.execute("SHOW transaction_read_only")
    assert cursor.fetchone() == ("off",)


@pytest.fixture
def pg_schema():
    database_url = _disposable_database_url()
    psycopg2 = pytest.importorskip("psycopg2")
    schema = f"entity_status_{uuid.uuid4().hex}"
    quoted_schema = _quote_schema(schema)
    connection = psycopg2.connect(
        database_url,
        connect_timeout=5,
        options="-c statement_timeout=5000 -c lock_timeout=1000",
    )
    created = False
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE SCHEMA {quoted_schema}")
            created = True
            cursor.execute(f"SET search_path TO {quoted_schema}")
            cursor.execute(
                "CREATE TABLE entities ("
                "id TEXT PRIMARY KEY, type TEXT NOT NULL, status TEXT, "
                "verified INTEGER, attributes JSONB, source JSONB)"
            )
            cursor.execute(
                "CREATE TABLE entity_changes ("
                "id BIGSERIAL PRIMARY KEY, entity_id TEXT NOT NULL, "
                "field TEXT NOT NULL, old_value TEXT, new_value TEXT, "
                "actor TEXT, created_at TIMESTAMPTZ DEFAULT NOW())"
            )
            cursor.executemany(
                "INSERT INTO entities "
                "(id, type, status, verified, attributes, source) "
                "VALUES (%s, %s, NULL, 1, %s::jsonb, %s::jsonb)",
                [
                    (
                        entity_id,
                        "dish",
                        "{}",
                        json.dumps([{"url": source_url}]),
                    )
                    for entity_id, source_url in (
                        ("a", "https://example.org/a"),
                        ("b", "https://example.org/b"),
                    )
                ],
            )
            cursor.execute("RESET search_path")
        connection.autocommit = False
        yield connection, schema
    finally:
        try:
            connection.rollback()
            connection.autocommit = True
            if created:
                with connection.cursor() as cursor:
                    cursor.execute(f"DROP SCHEMA IF EXISTS {quoted_schema} CASCADE")
        finally:
            connection.close()


@pytest.fixture
def pg_identity_roles():
    database_url = _disposable_database_url()
    psycopg2 = pytest.importorskip("psycopg2")
    sql = pytest.importorskip("psycopg2.sql")
    role_specs = [
        (f"entity_identity_{uuid.uuid4().hex}", uuid.uuid4().hex),
        (f"entity_identity_{uuid.uuid4().hex}", uuid.uuid4().hex),
    ]
    allowed_role, allowed_password = role_specs[0]
    denied_role, denied_password = role_specs[1]
    roles = (allowed_role, denied_role)
    created_roles: set[str] = set()
    connect_granted_roles: set[str] = set()
    admin = None
    database_name = None
    function_acl = None
    function_acl_snapshot_acquired = False
    read_granted = False
    function_granted = False
    public_execute_revoked = False
    acl_lock_acquired = False
    try:
        admin = psycopg2.connect(
            database_url,
            connect_timeout=5,
            options="-c statement_timeout=5000 -c lock_timeout=1000",
        )
        admin.autocommit = True
        valid_until = datetime.now(UTC) + timedelta(minutes=15)
        with admin.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            database_name = cursor.fetchone()[0]
            _acquire_function_acl_lock(cursor)
            acl_lock_acquired = True
            function_acl = _read_function_acl(cursor)
            function_acl_snapshot_acquired = True
            cursor.execute(
                "REVOKE EXECUTE ON FUNCTION pg_catalog.pg_control_system() FROM PUBLIC"
            )
            public_execute_revoked = True
            for role, password in role_specs:
                cursor.execute(
                    f"CREATE ROLE {_quote_role(role)} LOGIN PASSWORD %s "
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT "
                    "NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2 VALID UNTIL %s",
                    (password, valid_until),
                )
                created_roles.add(role)
                cursor.execute(
                    f"ALTER ROLE {_quote_role(role)} "
                    "SET default_transaction_read_only = 'on'"
                )
                cursor.execute(
                    f"ALTER ROLE {_quote_role(role)} SET statement_timeout = '5000ms'"
                )
            cursor.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {} ").format(
                    sql.Identifier(database_name), sql.Identifier(allowed_role)
                )
            )
            connect_granted_roles.add(allowed_role)
            cursor.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {} ").format(
                    sql.Identifier(database_name), sql.Identifier(denied_role)
                )
            )
            connect_granted_roles.add(denied_role)
            cursor.execute(
                sql.SQL("GRANT pg_read_all_data TO {} ").format(
                    sql.Identifier(allowed_role)
                )
            )
            read_granted = True
            cursor.execute(
                sql.SQL(
                    "GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO {}"
                ).format(sql.Identifier(allowed_role))
            )
            function_granted = True
        yield {
            "allowed_role": allowed_role,
            "allowed_url": _role_url(database_url, allowed_role, allowed_password),
            "denied_role": denied_role,
            "denied_url": _role_url(database_url, denied_role, denied_password),
        }
    finally:
        _cleanup_identity_roles(
            admin=admin,
            sql=sql,
            roles=roles,
            created_roles=created_roles,
            connect_granted_roles=connect_granted_roles,
            database_name=database_name,
            allowed_role=allowed_role,
            read_granted=read_granted,
            function_granted=function_granted,
            function_acl=function_acl,
            public_execute_revoked=public_execute_revoked,
            function_acl_snapshot_acquired=function_acl_snapshot_acquired,
            acl_lock_acquired=acl_lock_acquired,
        )


def test_postgres_apply_recovery_and_rollback_audits(
    pg_schema, tmp_path: Path
) -> None:
    connection, schema = pg_schema
    quoted_schema = _quote_schema(schema)

    _begin_serializable(connection)
    with connection.cursor() as cursor:
        _assert_serializable(cursor)
        store = migration.PostgresPublicationStore(cursor, schema=schema)
        cursor.execute(f"SELECT * FROM {quoted_schema}.entities ORDER BY id")
        rows = _rows(cursor)
        identity = store.target_identity()
        plan = migration.build_plan(
            rows=rows,
            identity=identity,
            schema_columns=store.schema_columns(),
            created_at="2026-07-15T12:00:00Z",
            tool_source_revision="postgres-integration-test",
        )
        plan_sha = sha256_bytes(canonical_json_bytes(plan))
        backup = _backup_evidence(tmp_path, plan["target_fingerprint"], identity)
        applied = migration.apply_plan(
            store,
            plan,
            plan_sha256=plan_sha,
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=NOW,
            restore_validator=lambda _artifact: _restore_listing_sha(),
            clock=lambda: NOW,
        )
    connection.commit()

    assert applied["result"] == "applied"
    assert applied["updated_ids"] == ["a", "b"]

    _begin_serializable(connection)
    with connection.cursor() as cursor:
        _assert_serializable(cursor)
        store = migration.PostgresPublicationStore(cursor, schema=schema)
        assert store.status_counts() == {"published": 2, "null": 0}
        apply_actor = migration.audit_actor("apply", plan_sha)
        assert _audit_rows(cursor, schema) == [
            ("a", "status", "null", "published", apply_actor),
            ("b", "status", "null", "published", apply_actor),
        ]
        repeated = migration.apply_plan(
            store,
            plan,
            plan_sha256=plan_sha,
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=NOW,
            restore_validator=lambda _artifact: _restore_listing_sha(),
            clock=lambda: NOW,
        )
    connection.commit()

    assert repeated["result"] == "already-applied"
    assert repeated["recovery_ready"] is True
    assert repeated["recovery_contract"] == "apply-audit-exact-v1"
    assert repeated["updated_ids"] == ["a", "b"]

    rollback_now = NOW + timedelta(minutes=10)
    repeated_sha = sha256_bytes(canonical_json_bytes(repeated))
    _begin_serializable(connection)
    with connection.cursor() as cursor:
        _assert_serializable(cursor)
        assert _audit_rows(cursor, schema) == [
            ("a", "status", "null", "published", apply_actor),
            ("b", "status", "null", "published", apply_actor),
        ]
        store = migration.PostgresPublicationStore(cursor, schema=schema)
        rolled_back = migration.rollback_apply(
            store,
            repeated,
            apply_report_sha256=repeated_sha,
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=rollback_now,
            restore_validator=lambda _artifact: _restore_listing_sha(),
            clock=lambda: rollback_now,
        )
    connection.commit()

    assert rolled_back["result"] == "rolled-back"
    assert rolled_back["restored_ids"] == ["a", "b"]

    _begin_serializable(connection)
    with connection.cursor() as cursor:
        _assert_serializable(cursor)
        store = migration.PostgresPublicationStore(cursor, schema=schema)
        assert store.status_counts() == {"published": 0, "null": 2}
        rollback_actor = migration.audit_actor("rollback", plan_sha)
        assert _audit_rows(cursor, schema) == [
            ("a", "status", "null", "published", apply_actor),
            ("a", "status", "published", "null", rollback_actor),
            ("b", "status", "null", "published", apply_actor),
            ("b", "status", "published", "null", rollback_actor),
        ]
        repeated_rollback = migration.rollback_apply(
            store,
            repeated,
            apply_report_sha256=repeated_sha,
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=rollback_now,
            restore_validator=lambda _artifact: _restore_listing_sha(),
            clock=lambda: rollback_now,
        )
    connection.commit()

    assert repeated_rollback["result"] == "already-rolled-back"
    assert repeated_rollback["recovery_ready"] is True
    assert repeated_rollback["recovery_contract"] == "rollback-audit-exact-v1"
    assert repeated_rollback["restored_ids"] == []

    with connection.cursor() as cursor:
        store = migration.PostgresPublicationStore(cursor, schema=schema)
        assert store.status_counts() == {"published": 0, "null": 2}
        assert _audit_rows(cursor, schema) == [
            ("a", "status", "null", "published", apply_actor),
            ("a", "status", "published", "null", rollback_actor),
            ("b", "status", "null", "published", apply_actor),
            ("b", "status", "published", "null", rollback_actor),
        ]


def test_postgres_advisory_lock_excludes_second_transaction(pg_schema) -> None:
    _fixture_connection, schema = pg_schema
    psycopg2 = pytest.importorskip("psycopg2")
    lock_name = f"{migration.LOCK_NAME}:{schema}"
    with ExitStack() as stack:
        first = stack.enter_context(
            closing(
                psycopg2.connect(
                    TEST_URL,
                    connect_timeout=5,
                    options="-c statement_timeout=5000 -c lock_timeout=1000",
                )
            )
        )
        second = stack.enter_context(
            closing(
                psycopg2.connect(
                    TEST_URL,
                    connect_timeout=5,
                    options="-c statement_timeout=5000 -c lock_timeout=1000",
                )
            )
        )
        try:
            with first.cursor() as first_cursor, second.cursor() as second_cursor:
                for cursor in (first_cursor, second_cursor):
                    cursor.execute("SET LOCAL statement_timeout = '5s'")
                    cursor.execute("SET LOCAL lock_timeout = '1s'")
                migration.PostgresPublicationStore(
                    first_cursor, schema=schema
                ).acquire_lock(lock_name)
                second_cursor.execute(
                    "SELECT pg_try_advisory_xact_lock(hashtext(%s))",
                    (lock_name,),
                )
                assert second_cursor.fetchone()[0] is False
                first.rollback()
                second_cursor.execute(
                    "SELECT pg_try_advisory_xact_lock(hashtext(%s))",
                    (lock_name,),
                )
                assert second_cursor.fetchone()[0] is True
        finally:
            first.rollback()
            second.rollback()


def test_postgres_identity_allowed_role_has_read_only_identity_access(
    pg_identity_roles,
) -> None:
    psycopg2 = pytest.importorskip("psycopg2")
    connection = psycopg2.connect(
        pg_identity_roles["allowed_url"],
        connect_timeout=5,
        options="-c statement_timeout=5000 -c lock_timeout=1000",
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW transaction_read_only")
            assert cursor.fetchone() == ("on",)
            cursor.execute(
                "SELECT pg_has_role(current_user, 'pg_read_all_data', 'USAGE')"
            )
            assert cursor.fetchone() == (True,)
            cursor.execute(
                "SELECT has_function_privilege("
                "current_user, 'pg_catalog.pg_control_system()', 'EXECUTE')"
            )
            assert cursor.fetchone() == (True,)
            identity = migration.read_target_identity(cursor)
    finally:
        connection.close()

    assert identity["identity_revision"] == "postgres-cluster-v2"
    assert type(identity["database_oid"]) is int
    assert identity["database_oid"] > 0
    assert re.fullmatch(r"[0-9]+", identity["system_identifier"])


def test_postgres_identity_denied_role_lacks_control_system_execute(
    pg_identity_roles,
) -> None:
    psycopg2 = pytest.importorskip("psycopg2")
    connection = psycopg2.connect(
        pg_identity_roles["denied_url"],
        connect_timeout=5,
        options="-c statement_timeout=5000 -c lock_timeout=1000",
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT has_function_privilege("
                "current_user, 'pg_catalog.pg_control_system()', 'EXECUTE')"
            )
            assert cursor.fetchone() == (False,)
            with pytest.raises(psycopg2.Error):
                migration.read_target_identity(cursor)
    finally:
        connection.close()
