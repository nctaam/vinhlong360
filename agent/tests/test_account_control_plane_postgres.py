import asyncio
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import unquote, urlparse

import psycopg2
import psycopg2.extras
import pytest
from fastapi import HTTPException, Request, Response

import admin
import auth
import database as database_module
import ratelimit


THREAD_TIMEOUT = 10
WAIT_TIMEOUT = 5


def _test_database_url() -> str | None:
    url = os.environ.get("ACCOUNT_CONTROL_PLANE_TEST_DATABASE_URL")
    if not url:
        return None

    parsed = urlparse(url)
    database_name = unquote(parsed.path.lstrip("/"))
    explicitly_allowed = os.environ.get(
        "ACCOUNT_CONTROL_PLANE_ALLOW_PG_TESTS", ""
    ).lower() in {"1", "true", "yes", "on"}
    if parsed.scheme not in {"postgres", "postgresql"} or not database_name:
        raise pytest.UsageError(
            "ACCOUNT_CONTROL_PLANE_TEST_DATABASE_URL must be a PostgreSQL URL"
        )
    if "test" not in database_name.lower() and not explicitly_allowed:
        raise pytest.UsageError(
            "PostgreSQL account-control tests require a database name containing "
            "'test' or ACCOUNT_CONTROL_PLANE_ALLOW_PG_TESTS=true"
        )
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} and not explicitly_allowed:
        raise pytest.UsageError(
            "Non-loopback PostgreSQL account-control tests require "
            "ACCOUNT_CONTROL_PLANE_ALLOW_PG_TESTS=true"
        )
    return url


TEST_DATABASE_URL = _test_database_url()
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set ACCOUNT_CONTROL_PLANE_TEST_DATABASE_URL to a disposable PostgreSQL DB",
)


SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS otp_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone TEXT NOT NULL,
    code TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    user_agent TEXT,
    ip_address TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pending_2fa (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT UNIQUE NOT NULL,
    ip TEXT,
    user_agent TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


@pytest.fixture(scope="session", autouse=True)
def _postgres_schema():
    assert TEST_DATABASE_URL is not None
    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(SCHEMA_SQL)
    try:
        yield
    finally:
        with psycopg2.connect(TEST_DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "TRUNCATE pending_2fa, user_sessions, otp_sessions, users CASCADE"
                )


@pytest.fixture
def pg_db(monkeypatch):
    assert TEST_DATABASE_URL is not None
    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    monkeypatch.setattr(auth, "db", adapter)
    monkeypatch.setattr(admin, "db", adapter)

    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "TRUNCATE pending_2fa, user_sessions, otp_sessions, users CASCADE"
            )
    try:
        yield adapter
    finally:
        with psycopg2.connect(TEST_DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "TRUNCATE pending_2fa, user_sessions, otp_sessions, users CASCADE"
                )


def _seed_user(pg_db, password_hash="old-hash") -> tuple[str, str]:
    user_id = str(uuid.uuid4())
    phone = f"test-{uuid.uuid4().hex}"
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO users (id, phone, password_hash, role, is_active)
            VALUES (%s::uuid, %s, %s, 'user', TRUE)
            """,
            (user_id, phone, password_hash),
        )
    return user_id, phone


def _seed_reset_otp(pg_db, phone: str, code="otp-hash") -> None:
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO otp_sessions (phone, code, expires_at)
            VALUES (%s, %s, %s)
            """,
            (phone, code, datetime.now(timezone.utc) + timedelta(minutes=5)),
        )


def _seed_session(pg_db, user_id: str) -> None:
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO user_sessions (user_id, token, expires_at)
            VALUES (%s::uuid, %s, %s)
            """,
            (
                user_id,
                f"session-{uuid.uuid4().hex}",
                datetime.now(timezone.utc) + timedelta(hours=1),
            ),
        )


def _seed_pending(pg_db, user_id: str) -> None:
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO pending_2fa (user_id, token_hash, expires_at)
            VALUES (%s::uuid, %s, %s)
            """,
            (
                user_id,
                f"pending-{uuid.uuid4().hex}",
                datetime.now(timezone.utc) + timedelta(minutes=5),
            ),
        )


def _account_state(pg_db, user_id: str) -> dict:
    with pg_db._conn() as conn:
        user = pg_db._fetchone(
            conn,
            "SELECT password_hash, is_active FROM users WHERE id = %s::uuid",
            (user_id,),
        )
        sessions = pg_db._fetchone(
            conn,
            "SELECT COUNT(*) AS count FROM user_sessions WHERE user_id = %s::uuid",
            (user_id,),
        )
        pending = pg_db._fetchone(
            conn,
            "SELECT COUNT(*) AS count FROM pending_2fa WHERE user_id = %s::uuid",
            (user_id,),
        )
    return {
        "password_hash": user["password_hash"],
        "is_active": user["is_active"],
        "sessions": sessions["count"],
        "pending": pending["count"],
    }


def _otp_verified(pg_db, phone: str) -> bool:
    with pg_db._conn() as conn:
        row = pg_db._fetchone(
            conn,
            "SELECT verified FROM otp_sessions WHERE phone = %s",
            (phone,),
        )
    return row["verified"]


def _normalized(sql: str) -> str:
    return " ".join(sql.split())


def _http_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/auth/2fa/verify",
            "query_string": b"",
            "headers": [(b"host", b"localhost"), (b"user-agent", b"pytest")],
            "client": ("127.0.0.1", 12345),
            "server": ("localhost", 80),
            "scheme": "http",
        }
    )


def _admin_request() -> SimpleNamespace:
    actor = {"id": str(uuid.uuid4()), "role": "admin"}
    return SimpleNamespace(state=SimpleNamespace(admin_user=actor))


def _assert_reset_first_rejects_stale_creation(pg_db, monkeypatch, kind: str) -> None:
    user_id, phone = _seed_user(pg_db)
    _seed_reset_otp(pg_db, phone)
    _seed_session(pg_db, user_id)
    _seed_pending(pg_db, user_id)
    monkeypatch.setattr(auth, "_hash_password", lambda _password: "reset-hash")

    reset_updated = threading.Event()
    allow_reset_commit = threading.Event()
    stale_lock_attempted = threading.Event()
    original_execute = pg_db._execute
    original_fetchone = pg_db._fetchone

    def execute_with_reset_barrier(conn, sql, params=None):
        result = original_execute(conn, sql, params)
        statement = _normalized(sql)
        if statement.startswith("UPDATE users SET password_hash") and "RETURNING" not in statement:
            reset_updated.set()
            if not allow_reset_commit.wait(WAIT_TIMEOUT):
                raise AssertionError("timed out waiting to release reset transaction")
        return result

    def fetchone_with_stale_signal(conn, sql, params=None):
        statement = _normalized(sql)
        if statement.startswith("SELECT id, password_hash, is_active, deleted_at"):
            stale_lock_attempted.set()
        return original_fetchone(conn, sql, params)

    monkeypatch.setattr(pg_db, "_execute", execute_with_reset_barrier)
    monkeypatch.setattr(pg_db, "_fetchone", fetchone_with_stale_signal)

    with ThreadPoolExecutor(max_workers=2) as executor:
        reset = executor.submit(
            auth._reset_password_state, phone, "otp-hash", "NewPassword1"
        )
        assert reset_updated.wait(WAIT_TIMEOUT)
        if kind == "pending":
            stale = executor.submit(
                auth._create_pending_2fa,
                user_id,
                "127.0.0.1",
                "pytest",
                "old-hash",
            )
        else:
            stale = executor.submit(
                auth._create_session_atomic,
                user_id,
                f"stale-session-{uuid.uuid4().hex}",
                "pytest",
                "127.0.0.1",
                (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "old-hash",
            )
        assert stale_lock_attempted.wait(WAIT_TIMEOUT)
        assert not stale.done()
        allow_reset_commit.set()
        reset.result(timeout=THREAD_TIMEOUT)
        with pytest.raises(HTTPException) as exc:
            stale.result(timeout=THREAD_TIMEOUT)

    assert exc.value.status_code == 401
    assert _account_state(pg_db, user_id) == {
        "password_hash": "reset-hash",
        "is_active": True,
        "sessions": 0,
        "pending": 0,
    }


def test_reset_first_rejects_stale_pending_challenge_on_postgres(
    pg_db, monkeypatch
):
    _assert_reset_first_rejects_stale_creation(pg_db, monkeypatch, "pending")


def test_reset_first_rejects_stale_session_creation_on_postgres(
    pg_db, monkeypatch
):
    _assert_reset_first_rejects_stale_creation(pg_db, monkeypatch, "session")


def test_auth_first_session_and_challenge_are_revoked_by_reset_on_postgres(
    pg_db, monkeypatch
):
    user_id, phone = _seed_user(pg_db)
    _seed_reset_otp(pg_db, phone)
    monkeypatch.setattr(auth, "_hash_password", lambda _password: "reset-hash")

    pending_inserted = threading.Event()
    allow_auth_commit = threading.Event()
    reset_user_lock_attempted = threading.Event()
    original_execute = pg_db._execute
    original_fetchone = pg_db._fetchone

    def execute_with_auth_barrier(conn, sql, params=None):
        result = original_execute(conn, sql, params)
        if _normalized(sql).startswith("INSERT INTO pending_2fa"):
            pending_inserted.set()
            if not allow_auth_commit.wait(WAIT_TIMEOUT):
                raise AssertionError("timed out waiting to commit auth transaction")
        return result

    def fetchone_with_reset_signal(conn, sql, params=None):
        statement = _normalized(sql)
        if statement.startswith("SELECT u.* FROM users u WHERE u.phone"):
            reset_user_lock_attempted.set()
        return original_fetchone(conn, sql, params)

    monkeypatch.setattr(pg_db, "_execute", execute_with_auth_barrier)
    monkeypatch.setattr(pg_db, "_fetchone", fetchone_with_reset_signal)

    def create_old_snapshot_auth_state() -> None:
        auth._create_session_atomic(
            user_id,
            f"session-{uuid.uuid4().hex}",
            "pytest",
            "127.0.0.1",
            (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "old-hash",
        )
        auth._create_pending_2fa(
            user_id, "127.0.0.1", "pytest", "old-hash"
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        auth_state = executor.submit(create_old_snapshot_auth_state)
        assert pending_inserted.wait(WAIT_TIMEOUT)
        reset = executor.submit(
            auth._reset_password_state, phone, "otp-hash", "NewPassword1"
        )
        assert reset_user_lock_attempted.wait(WAIT_TIMEOUT)
        assert not reset.done()
        allow_auth_commit.set()
        auth_state.result(timeout=THREAD_TIMEOUT)
        reset.result(timeout=THREAD_TIMEOUT)

    assert _account_state(pg_db, user_id) == {
        "password_hash": "reset-hash",
        "is_active": True,
        "sessions": 0,
        "pending": 0,
    }


def test_consumed_challenge_cannot_create_session_after_reset_on_postgres(
    pg_db, monkeypatch
):
    user_id, phone = _seed_user(pg_db)
    _seed_reset_otp(pg_db, phone)
    challenge_id = auth._create_pending_2fa(
        user_id, "127.0.0.1", "pytest", "old-hash"
    )
    monkeypatch.setattr(auth, "_hash_password", lambda _password: "reset-hash")
    monkeypatch.setattr(auth, "_check_shared_auth_rate", lambda *_args: None)
    monkeypatch.setattr(auth, "_enforce_local_rate", lambda *_args: None)
    monkeypatch.setattr(auth, "_verify_2fa_code", lambda *_args: True)

    finish_entered = threading.Event()
    allow_finish = threading.Event()
    original_finish_login = auth._finish_login

    async def finish_after_reset(*args, **kwargs):
        finish_entered.set()
        released = await asyncio.to_thread(allow_finish.wait, WAIT_TIMEOUT)
        if not released:
            raise AssertionError("timed out waiting for reset before session creation")
        return await original_finish_login(*args, **kwargs)

    monkeypatch.setattr(auth, "_finish_login", finish_after_reset)
    body = auth._TwoFAVerify(challenge_id=challenge_id, code="123456")

    with ThreadPoolExecutor(max_workers=2) as executor:
        verification = executor.submit(
            asyncio.run, auth.twofa_verify(body, _http_request(), Response())
        )
        assert finish_entered.wait(WAIT_TIMEOUT)
        before_reset = _account_state(pg_db, user_id)
        assert before_reset["pending"] == 0
        assert before_reset["sessions"] == 0

        reset = executor.submit(
            auth._reset_password_state, phone, "otp-hash", "NewPassword1"
        )
        reset.result(timeout=THREAD_TIMEOUT)
        allow_finish.set()
        with pytest.raises(HTTPException) as exc:
            verification.result(timeout=THREAD_TIMEOUT)

    assert exc.value.status_code == 401
    assert _account_state(pg_db, user_id) == {
        "password_hash": "reset-hash",
        "is_active": True,
        "sessions": 0,
        "pending": 0,
    }


def test_reset_wins_against_legacy_rehash_cas_on_postgres(pg_db, monkeypatch):
    user_id, phone = _seed_user(pg_db)
    _seed_reset_otp(pg_db, phone)
    monkeypatch.setattr(auth, "_hash_password", lambda _password: "reset-hash")

    reset_updated = threading.Event()
    allow_reset_commit = threading.Event()
    rehash_attempted = threading.Event()
    original_execute = pg_db._execute
    original_fetchone = pg_db._fetchone

    def execute_with_reset_barrier(conn, sql, params=None):
        result = original_execute(conn, sql, params)
        statement = _normalized(sql)
        if statement.startswith("UPDATE users SET password_hash") and "RETURNING" not in statement:
            reset_updated.set()
            if not allow_reset_commit.wait(WAIT_TIMEOUT):
                raise AssertionError("timed out waiting to release reset transaction")
        return result

    def fetchone_with_rehash_signal(conn, sql, params=None):
        statement = _normalized(sql)
        if statement.startswith("UPDATE users SET password_hash") and "RETURNING" in statement:
            rehash_attempted.set()
        return original_fetchone(conn, sql, params)

    monkeypatch.setattr(pg_db, "_execute", execute_with_reset_barrier)
    monkeypatch.setattr(pg_db, "_fetchone", fetchone_with_rehash_signal)

    with ThreadPoolExecutor(max_workers=2) as executor:
        reset = executor.submit(
            auth._reset_password_state, phone, "otp-hash", "NewPassword1"
        )
        assert reset_updated.wait(WAIT_TIMEOUT)
        rehash = executor.submit(
            auth._rehash_legacy_password,
            user_id,
            "old-hash",
            "upgraded-legacy-hash",
        )
        assert rehash_attempted.wait(WAIT_TIMEOUT)
        assert not rehash.done()
        allow_reset_commit.set()
        reset.result(timeout=THREAD_TIMEOUT)
        assert rehash.result(timeout=THREAD_TIMEOUT) is False

    assert _account_state(pg_db, user_id)["password_hash"] == "reset-hash"


def test_reversed_bulk_bans_lock_in_sorted_order_without_deadlock_on_postgres(
    pg_db, monkeypatch
):
    first_id, _ = _seed_user(pg_db)
    second_id, _ = _seed_user(pg_db)
    _seed_session(pg_db, first_id)
    _seed_session(pg_db, second_id)
    monkeypatch.setattr(admin, "require_pg", lambda: None)
    monkeypatch.setattr(admin, "_log_mod_action", lambda *_args: None)
    monkeypatch.setattr(ratelimit, "check_rate", lambda *_args: None)

    first_lock_barrier = threading.Barrier(2)
    distinct_locks_held = threading.Barrier(2)
    first_attempts = {}
    attempts_lock = threading.Lock()
    original_fetchone = pg_db._fetchone

    def fetchone_with_lock_barriers(conn, sql, params=None):
        statement = _normalized(sql)
        is_bulk_lock = (
            statement.startswith("SELECT id, is_active, role FROM users")
            and "FOR UPDATE" in statement
        )
        if not is_bulk_lock:
            return original_fetchone(conn, sql, params)

        thread_id = threading.get_ident()
        with attempts_lock:
            is_first_lock = thread_id not in first_attempts
            if is_first_lock:
                first_attempts[thread_id] = str(params[0])
        if not is_first_lock:
            return original_fetchone(conn, sql, params)

        first_lock_barrier.wait(WAIT_TIMEOUT)
        row = original_fetchone(conn, sql, params)
        with attempts_lock:
            inputs_started_on_distinct_rows = len(set(first_attempts.values())) == 2
        if inputs_started_on_distinct_rows:
            distinct_locks_held.wait(WAIT_TIMEOUT)
        return row

    monkeypatch.setattr(pg_db, "_fetchone", fetchone_with_lock_barriers)
    body_forward = admin.BulkUserAction(user_ids=[first_id, second_id])
    body_reverse = admin.BulkUserAction(user_ids=[second_id, first_id])

    with ThreadPoolExecutor(max_workers=2) as executor:
        forward = executor.submit(
            asyncio.run,
            admin.bulk_ban_users(body_forward, _admin_request()),
        )
        reverse = executor.submit(
            asyncio.run,
            admin.bulk_ban_users(body_reverse, _admin_request()),
        )
        results = [
            forward.result(timeout=THREAD_TIMEOUT),
            reverse.result(timeout=THREAD_TIMEOUT),
        ]

    expected_first_lock = min(first_id, second_id)
    assert set(first_attempts.values()) == {expected_first_lock}
    assert all(result["banned_count"] == 2 for result in results)
    assert _account_state(pg_db, first_id)["is_active"] is False
    assert _account_state(pg_db, second_id)["is_active"] is False
    assert _account_state(pg_db, first_id)["sessions"] == 0
    assert _account_state(pg_db, second_id)["sessions"] == 0


def test_reset_rolls_back_real_partial_mutations_on_postgres(pg_db, monkeypatch):
    user_id, phone = _seed_user(pg_db)
    _seed_reset_otp(pg_db, phone)
    _seed_session(pg_db, user_id)
    _seed_pending(pg_db, user_id)
    monkeypatch.setattr(auth, "_hash_password", lambda _password: "reset-hash")
    original_execute = pg_db._execute
    pending_delete_executed = threading.Event()

    def execute_then_fail(conn, sql, params=None):
        result = original_execute(conn, sql, params)
        if _normalized(sql).startswith(
            "DELETE FROM pending_2fa WHERE user_id::text"
        ):
            pending_delete_executed.set()
            raise RuntimeError("injected failure after pending challenge deletion")
        return result

    monkeypatch.setattr(pg_db, "_execute", execute_then_fail)

    with pytest.raises(
        RuntimeError, match="injected failure after pending challenge deletion"
    ):
        auth._reset_password_state(phone, "otp-hash", "NewPassword1")

    assert pending_delete_executed.is_set()
    assert _account_state(pg_db, user_id) == {
        "password_hash": "old-hash",
        "is_active": True,
        "sessions": 1,
        "pending": 1,
    }
    assert _otp_verified(pg_db, phone) is False


def test_bulk_ban_rolls_back_real_partial_mutations_on_postgres(
    pg_db, monkeypatch
):
    first_id, _ = _seed_user(pg_db)
    second_id, _ = _seed_user(pg_db)
    _seed_session(pg_db, first_id)
    _seed_session(pg_db, second_id)
    monkeypatch.setattr(admin, "require_pg", lambda: None)
    monkeypatch.setattr(admin, "_log_mod_action", lambda *_args: None)
    monkeypatch.setattr(ratelimit, "check_rate", lambda *_args: None)
    original_execute = pg_db._execute
    session_delete_executed = threading.Event()

    def execute_then_fail(conn, sql, params=None):
        result = original_execute(conn, sql, params)
        if (
            _normalized(sql).startswith("DELETE FROM user_sessions WHERE user_id")
            and not session_delete_executed.is_set()
        ):
            session_delete_executed.set()
            raise RuntimeError("injected failure after session deletion")
        return result

    monkeypatch.setattr(pg_db, "_execute", execute_then_fail)
    body = admin.BulkUserAction(user_ids=[first_id, second_id])

    with pytest.raises(RuntimeError, match="injected failure after session deletion"):
        asyncio.run(admin.bulk_ban_users(body, _admin_request()))

    assert session_delete_executed.is_set()
    assert _account_state(pg_db, first_id)["is_active"] is True
    assert _account_state(pg_db, second_id)["is_active"] is True
    assert _account_state(pg_db, first_id)["sessions"] == 1
    assert _account_state(pg_db, second_id)["sessions"] == 1
