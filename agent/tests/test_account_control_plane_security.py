import ast
import asyncio  # noqa: F401
import inspect  # noqa: F401
import textwrap
from contextlib import contextmanager  # noqa: F401
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request, Response

import admin
import auth  # noqa: F401


ADMIN_ID = "00000000-0000-0000-0000-000000000001"
PEER_ID = "00000000-0000-0000-0000-000000000002"
SUPER_ID = "00000000-0000-0000-0000-000000000003"
USER_ID = "00000000-0000-0000-0000-000000000004"


def _request(actor):
    return SimpleNamespace(state=SimpleNamespace(admin_user=actor))


def _http_request(*, trusted=False):
    headers = [(b"host", b"localhost"), (b"user-agent", b"pytest")]
    if trusted:
        headers.append((b"cookie", b"vl360_trusted=device-token"))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/auth/login",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("localhost", 80),
            "scheme": "http",
        }
    )


class _AdminDB:
    _ph = "%s"

    def __init__(self, users):
        self.users = {uid: dict(row) for uid, row in users.items()}
        self.fetches = []
        self.executes = []
        self.calls = []

    @contextmanager
    def _conn(self):
        yield object()

    def _fetchone(self, _conn, sql, params=()):
        self.fetches.append((sql, params))
        self.calls.append(("fetch", sql, params))
        if "FROM users" in sql:
            return self.users.get(str(params[0]))
        return None

    def _execute(self, _conn, sql, params=()):
        self.executes.append((sql, params))
        self.calls.append(("execute", sql, params))

    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row else None


class _AuthDB:
    _ph = "%s"

    def __init__(self, user):
        self.user = dict(user)
        self.login_user = dict(user)
        self.trusted_device_id = None
        self.pending = []
        self.sessions = []
        self.fetches = []
        self.executes = []
        self.calls = []

    @contextmanager
    def _conn(self):
        yield object()

    def _fetchone(self, _conn, sql, params=()):
        self.fetches.append((sql, params))
        self.calls.append(("fetch", sql, params))
        if "UPDATE users SET password_hash" in sql and "RETURNING password_hash" in sql:
            new_hash, user_id, original_hash = params
            if (
                self.user
                and str(self.user["id"]) == str(user_id)
                and self.user.get("password_hash") == original_hash
            ):
                self.user["password_hash"] = new_hash
                return {"password_hash": new_hash}
            return None
        if "FROM trusted_devices" in sql:
            if self.trusted_device_id:
                return {"id": self.trusted_device_id}
            return None
        if "FROM users" in sql:
            return dict(self.user) if self.user else None
        return None

    def _execute(self, _conn, sql, params=()):
        self.executes.append((sql, params))
        self.calls.append(("execute", sql, params))
        if "INSERT INTO pending_2fa" in sql:
            self.pending.append(params)
        if "INSERT INTO user_sessions" in sql:
            self.sessions.append(params)

    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row else None

    def get_user_by_phone(self, _phone):
        return dict(self.login_user) if self.login_user else None


def _invoke_auth_snapshot_creation(kind, expected_password_hash):
    if kind == "pending":
        return auth._create_pending_2fa(
            USER_ID, "127.0.0.1", "pytest", expected_password_hash
        )
    return auth._create_session_atomic(
        USER_ID,
        "token-hash",
        "pytest",
        "127.0.0.1",
        "2099-01-01T00:00:00+00:00",
        expected_password_hash,
    )


def _threaded_helper_calls(fn, helper_name):
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "to_thread"
        and node.args
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == helper_name
    ]


def _is_user_password_snapshot(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "user"
        and node.func.attr == "get"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "password_hash"
    )


def _disable_login_rate_limits(monkeypatch):
    monkeypatch.setattr(auth, "_check_shared_auth_rate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth, "_enforce_local_rate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth, "_login_ip_rate", {})
    monkeypatch.setattr(auth, "_login_phone_fails", {})
    monkeypatch.setattr(auth, "_otp_verify_ip_rate", {})
    monkeypatch.setattr(auth, "_otp_verify_phone_rate", {})


async def _run_trusted_login_path(path, response):
    request = _http_request(trusted=True)
    if path == "otp":
        body = auth.OTPVerify(phone="0901234567", code="123456")
        return await auth.verify_otp(body, request, response)
    body = auth.PasswordLogin(phone="0901234567", password="password123")
    return await auth.login_password(body, request, response)


def _install_admin_db(monkeypatch, users):
    fake = _AdminDB(users)
    monkeypatch.setattr(admin, "db", fake)
    monkeypatch.setattr(admin, "require_pg", lambda: None)
    return fake


@pytest.mark.parametrize(
    ("actor_role", "target_role"),
    [
        ("moderator", "user"),
        ("admin", "moderator"),
        ("admin", "user"),
        ("superadmin", "admin"),
        ("superadmin", "moderator"),
        ("superadmin", "user"),
    ],
)
def test_actor_can_manage_only_lower_roles(actor_role, target_role):
    admin._assert_actor_can_manage_target({"role": actor_role}, target_role)


@pytest.mark.parametrize(
    ("actor_role", "target_role"),
    [
        ("user", "user"),
        ("user", "moderator"),
        ("user", "admin"),
        ("user", "superadmin"),
        ("moderator", "moderator"),
        ("moderator", "admin"),
        ("moderator", "superadmin"),
        ("admin", "admin"),
        ("admin", "superadmin"),
        ("superadmin", "superadmin"),
        ("unknown", "user"),
        ("admin", "unknown"),
        ("", "user"),
    ],
)
def test_actor_cannot_manage_equal_higher_or_unknown_roles(actor_role, target_role):
    with pytest.raises(HTTPException) as exc:
        admin._assert_actor_can_manage_target({"role": actor_role}, target_role)
    assert exc.value.status_code == 403


def test_admin_key_can_manage_superadmin():
    admin._assert_actor_can_manage_target(None, "superadmin")


@pytest.mark.parametrize("target_role", ["admin", "superadmin"])
def test_single_ban_denies_peer_or_superior_without_side_effects(monkeypatch, target_role):
    fake = _install_admin_db(
        monkeypatch,
        {SUPER_ID: {"id": SUPER_ID, "role": target_role, "is_active": True}},
    )
    logs = []
    monkeypatch.setattr(admin, "_log_mod_action", lambda *args: logs.append(args))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(admin.ban_user(SUPER_ID, _request({"id": ADMIN_ID, "role": "admin"})))

    assert exc.value.status_code == 403
    assert fake.executes == []
    assert logs == []
    assert any("FOR UPDATE" in sql for sql, _ in fake.fetches)


@pytest.mark.parametrize(
    ("actor", "target_role"),
    [
        ({"id": ADMIN_ID, "role": "superadmin"}, "admin"),
        (None, "superadmin"),
    ],
)
def test_single_ban_allows_superior_or_admin_key(monkeypatch, actor, target_role):
    fake = _install_admin_db(
        monkeypatch,
        {SUPER_ID: {"id": SUPER_ID, "role": target_role, "is_active": True}},
    )
    logs = []
    monkeypatch.setattr(admin, "_log_mod_action", lambda *args: logs.append(args))

    result = asyncio.run(admin.ban_user(SUPER_ID, _request(actor)))

    assert result == {"success": True}
    assert any("UPDATE users SET is_active = FALSE" in sql for sql, _ in fake.executes)
    assert any("DELETE FROM user_sessions" in sql for sql, _ in fake.executes)
    assert len(logs) == 1


def test_single_ban_uses_request_scoped_actor_without_auth_lookup(monkeypatch):
    _install_admin_db(
        monkeypatch,
        {SUPER_ID: {"id": SUPER_ID, "role": "admin", "is_active": True}},
    )

    async def unexpected_auth_lookup(_request):
        raise AssertionError("ban_user must use request.state.admin_user")

    monkeypatch.setattr(admin, "get_current_user", unexpected_auth_lookup)
    monkeypatch.setattr(admin, "_log_mod_action", lambda *_args: None)

    result = asyncio.run(
        admin.ban_user(SUPER_ID, _request({"id": ADMIN_ID, "role": "superadmin"}))
    )

    assert result == {"success": True}


@pytest.mark.parametrize("target_role", ["admin", "superadmin"])
def test_bulk_ban_rejects_mixed_peer_or_superior_batch_without_any_write(
    monkeypatch, target_role
):
    actor = {"id": ADMIN_ID, "role": "admin"}

    async def legacy_auth_lookup(_request):
        return actor

    monkeypatch.setattr(admin, "get_current_user", legacy_auth_lookup)
    fake = _install_admin_db(
        monkeypatch,
        {
            USER_ID: {"id": USER_ID, "role": "user", "is_active": True},
            SUPER_ID: {"id": SUPER_ID, "role": target_role, "is_active": True},
        },
    )
    assert_manage = admin._assert_actor_can_manage_target

    def track_validation(admin_user, target_role):
        fake.calls.append(("validate", admin_user, target_role))
        return assert_manage(admin_user, target_role)

    monkeypatch.setattr(admin, "_assert_actor_can_manage_target", track_validation)
    logs = []
    monkeypatch.setattr(admin, "_log_mod_action", lambda *args: logs.append(args))

    body = admin.BulkUserAction(user_ids=[USER_ID, SUPER_ID], reason="security")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            admin.bulk_ban_users(
                body,
                _request(actor),
            )
        )

    assert exc.value.status_code == 403
    assert fake.executes == []
    assert logs == []
    assert [call[0] for call in fake.calls] == [
        "fetch",
        "fetch",
        "validate",
        "validate",
    ]


def test_bulk_ban_deduplicates_skips_missing_and_preserves_response_order(monkeypatch):
    actor = {"id": ADMIN_ID, "role": "admin"}

    async def legacy_auth_lookup(_request):
        return actor

    monkeypatch.setattr(admin, "get_current_user", legacy_auth_lookup)
    fake = _install_admin_db(
        monkeypatch,
        {
            USER_ID: {"id": USER_ID, "role": "user", "is_active": True},
            PEER_ID: {"id": PEER_ID, "role": "moderator", "is_active": True},
        },
    )
    assert_manage = admin._assert_actor_can_manage_target

    def track_validation(admin_user, target_role):
        fake.calls.append(("validate", admin_user, target_role))
        return assert_manage(admin_user, target_role)

    monkeypatch.setattr(admin, "_assert_actor_can_manage_target", track_validation)
    logs = []
    monkeypatch.setattr(admin, "_log_mod_action", lambda *args: logs.append(args))
    missing = "00000000-0000-0000-0000-000000000099"
    body = admin.BulkUserAction(user_ids=[PEER_ID, missing, USER_ID, PEER_ID])

    result = asyncio.run(
        admin.bulk_ban_users(body, _request(actor))
    )

    assert result["banned_ids"] == [PEER_ID, USER_ID]
    assert result["banned_count"] == 2
    assert logs == [
        ("user", PEER_ID, "ban", None),
        ("user", USER_ID, "ban", None),
    ]
    assert len(fake.fetches) == 3
    locked_ids = [str(params[0]) for sql, params in fake.fetches if "FOR UPDATE" in sql]
    assert locked_ids == sorted({PEER_ID, missing, USER_ID})
    first_write = next(i for i, call in enumerate(fake.calls) if call[0] == "execute")
    assert [call[0] for call in fake.calls[:first_write]] == [
        "fetch",
        "fetch",
        "fetch",
        "validate",
        "validate",
    ]


def test_bulk_ban_uses_request_scoped_actor_without_auth_lookup(monkeypatch):
    _install_admin_db(
        monkeypatch,
        {USER_ID: {"id": USER_ID, "role": "user", "is_active": True}},
    )

    async def unexpected_auth_lookup(_request):
        raise AssertionError("bulk_ban_users must use request.state.admin_user")

    monkeypatch.setattr(admin, "get_current_user", unexpected_auth_lookup)
    monkeypatch.setattr(admin, "_log_mod_action", lambda *_args: None)

    result = asyncio.run(
        admin.bulk_ban_users(
            admin.BulkUserAction(user_ids=[USER_ID]),
            _request({"id": ADMIN_ID, "role": "admin"}),
        )
    )

    assert result["banned_ids"] == [USER_ID]


def test_pending_challenge_rejects_stale_password_snapshot(monkeypatch):
    fake = _AuthDB(
        {"id": USER_ID, "password_hash": "new-hash", "is_active": True, "deleted_at": None}
    )
    monkeypatch.setattr(auth, "db", fake)

    with pytest.raises(HTTPException) as exc:
        auth._create_pending_2fa(USER_ID, "127.0.0.1", "pytest", "old-hash")

    assert exc.value.status_code == 401
    assert fake.pending == []
    assert any("FOR UPDATE" in sql for sql, _ in fake.fetches)


def test_session_creation_rejects_stale_password_snapshot(monkeypatch):
    fake = _AuthDB(
        {"id": USER_ID, "password_hash": "new-hash", "is_active": True, "deleted_at": None}
    )
    monkeypatch.setattr(auth, "db", fake)

    with pytest.raises(HTTPException) as exc:
        auth._create_session_atomic(
            USER_ID,
            "token-hash",
            "pytest",
            "127.0.0.1",
            "2099-01-01T00:00:00+00:00",
            "old-hash",
        )

    assert exc.value.status_code == 401
    assert fake.sessions == []


@pytest.mark.parametrize("kind", ["pending", "session"])
def test_auth_state_matching_password_snapshot_allows_creation(monkeypatch, kind):
    fake = _AuthDB(
        {"id": USER_ID, "password_hash": "same-hash", "is_active": True, "deleted_at": None}
    )
    monkeypatch.setattr(auth, "db", fake)

    _invoke_auth_snapshot_creation(kind, "same-hash")

    inserted = fake.pending if kind == "pending" else fake.sessions
    assert len(inserted) == 1
    assert any("FOR UPDATE" in sql for sql, _ in fake.fetches)


@pytest.mark.parametrize("kind", ["pending", "session"])
def test_auth_state_none_snapshot_allows_none_password_account(monkeypatch, kind):
    fake = _AuthDB(
        {"id": USER_ID, "password_hash": None, "is_active": True, "deleted_at": None}
    )
    monkeypatch.setattr(auth, "db", fake)

    _invoke_auth_snapshot_creation(kind, None)

    inserted = fake.pending if kind == "pending" else fake.sessions
    assert len(inserted) == 1


@pytest.mark.parametrize("kind", ["pending", "session"])
@pytest.mark.parametrize(
    ("expected_password_hash", "current_password_hash"),
    [(None, "current-hash"), ("expected-hash", None)],
)
def test_auth_state_null_direction_mismatch_rejects_creation(
    monkeypatch, kind, expected_password_hash, current_password_hash
):
    fake = _AuthDB(
        {
            "id": USER_ID,
            "password_hash": current_password_hash,
            "is_active": True,
            "deleted_at": None,
        }
    )
    monkeypatch.setattr(auth, "db", fake)

    with pytest.raises(HTTPException) as exc:
        _invoke_auth_snapshot_creation(kind, expected_password_hash)

    assert exc.value.status_code == 401
    assert fake.pending == []
    assert fake.sessions == []


@pytest.mark.parametrize("kind", ["pending", "session"])
@pytest.mark.parametrize("state", ["inactive", "deleted", "missing"])
def test_auth_state_invalid_account_rejects_creation(monkeypatch, kind, state):
    user = {
        "id": USER_ID,
        "password_hash": "same-hash",
        "is_active": state != "inactive",
        "deleted_at": "2099-01-01T00:00:00+00:00" if state == "deleted" else None,
    }
    fake = _AuthDB(user)
    if state == "missing":
        fake.user = None
    monkeypatch.setattr(auth, "db", fake)

    with pytest.raises(HTTPException) as exc:
        _invoke_auth_snapshot_creation(kind, "same-hash")

    assert exc.value.status_code == 401
    assert fake.pending == []
    assert fake.sessions == []


def test_auth_state_non_null_snapshot_uses_constant_time_compare(monkeypatch):
    compared = []

    def compare(expected, current):
        compared.append((expected, current))
        return True

    monkeypatch.setattr(auth.hmac, "compare_digest", compare)

    assert auth._password_snapshot_matches("expected-hash", "current-hash") is True
    assert compared == [("expected-hash", "current-hash")]


@pytest.mark.parametrize(
    ("fn", "helper_name"),
    [
        (auth.verify_otp, "_create_pending_2fa"),
        (auth.login_password, "_create_pending_2fa"),
        (auth._finish_login, "_create_session_atomic"),
    ],
)
def test_login_paths_forward_password_snapshot(fn, helper_name):
    calls = _threaded_helper_calls(fn, helper_name)

    assert len(calls) == 1
    assert _is_user_password_snapshot(calls[0].args[-1])


def test_finish_login_auth_state_check_precedes_login_side_effects():
    tree = ast.parse(textwrap.dedent(inspect.getsource(auth._finish_login)))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    session_call = _threaded_helper_calls(auth._finish_login, "_create_session_atomic")[0]
    side_effect_names = {
        "_check_suspicious_login",
        "_log_login",
        "_update_login_streak",
        "_set_session_cookie",
    }
    side_effect_lines = [
        node.lineno
        for node in calls
        if (
            isinstance(node.func, ast.Name)
            and node.func.id in side_effect_names
        )
        or (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "to_thread"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in side_effect_names
        )
    ]

    assert side_effect_lines
    assert session_call.lineno < min(side_effect_lines)


def test_finish_login_stale_snapshot_has_no_side_effects(monkeypatch):
    fake = _AuthDB(
        {"id": USER_ID, "password_hash": "new-hash", "is_active": True, "deleted_at": None}
    )
    monkeypatch.setattr(auth, "db", fake)
    calls = []
    monkeypatch.setattr(auth, "_check_suspicious_login", lambda *_args: calls.append("alert"))
    monkeypatch.setattr(auth, "_log_login", lambda *_args: calls.append("history"))
    monkeypatch.setattr(auth, "_update_login_streak", lambda *_args: calls.append("streak"))
    monkeypatch.setattr(auth, "_set_session_cookie", lambda *_args: calls.append("cookie"))
    monkeypatch.setattr(auth.asyncio, "create_task", lambda *_args: calls.append("achievement"))
    response = Response()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            auth._finish_login(
                {"id": USER_ID, "password_hash": "old-hash", "is_active": True},
                "0901234567",
                "password",
                _http_request(),
                response,
            )
        )

    assert exc.value.status_code == 401
    assert fake.sessions == []
    assert response.headers.get("set-cookie") is None
    assert response.body == b""
    assert calls == []


def test_legacy_rehash_cas_rejects_concurrent_reset_without_auth_creation(monkeypatch):
    fake = _AuthDB(
        {"id": USER_ID, "password_hash": "reset-hash", "is_active": True, "deleted_at": None}
    )
    fake.login_user = {
        "id": USER_ID,
        "phone": "0901234567",
        "password_hash": "legacy-hash",
        "is_active": True,
        "deleted_at": None,
    }
    monkeypatch.setattr(auth, "db", fake)
    _disable_login_rate_limits(monkeypatch)
    monkeypatch.setattr(
        auth,
        "_verify_password",
        lambda *_args, **_kwargs: (True, True),
    )
    monkeypatch.setattr(auth, "_hash_password", lambda _password: "upgraded-hash")
    reached = []
    monkeypatch.setattr(auth, "_2fa_is_enabled", lambda *_args: reached.append("2fa"))

    async def finish(*_args):
        reached.append("finish")

    monkeypatch.setattr(auth, "_finish_login", finish)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            auth.login_password(
                auth.PasswordLogin(phone="0901234567", password="password123"),
                _http_request(),
                Response(),
            )
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == auth._STALE_AUTH_DETAIL
    assert fake.user["password_hash"] == "reset-hash"
    assert fake.pending == []
    assert fake.sessions == []
    assert reached == []
    cas_sql, cas_params = next(
        (sql, params)
        for sql, params in fake.fetches
        if "UPDATE users SET password_hash" in sql
    )
    assert "password_hash = %s" in cas_sql
    assert "RETURNING password_hash" in cas_sql
    assert cas_params == ("upgraded-hash", USER_ID, "legacy-hash")


def test_legacy_rehash_cas_success_updates_local_snapshot(monkeypatch):
    fake = _AuthDB(
        {"id": USER_ID, "password_hash": "legacy-hash", "is_active": True, "deleted_at": None}
    )
    fake.login_user.update({"phone": "0901234567"})
    monkeypatch.setattr(auth, "db", fake)
    _disable_login_rate_limits(monkeypatch)
    monkeypatch.setattr(
        auth,
        "_verify_password",
        lambda *_args, **_kwargs: (True, True),
    )
    monkeypatch.setattr(auth, "_hash_password", lambda _password: "upgraded-hash")
    monkeypatch.setattr(auth, "_2fa_is_enabled", lambda *_args: False)
    snapshots = []

    async def finish(user, *_args):
        snapshots.append(user["password_hash"])
        return {"success": True}

    monkeypatch.setattr(auth, "_finish_login", finish)

    result = asyncio.run(
        auth.login_password(
            auth.PasswordLogin(phone="0901234567", password="password123"),
            _http_request(),
            Response(),
        )
    )

    assert result == {"success": True}
    assert fake.user["password_hash"] == "upgraded-hash"
    assert snapshots == ["upgraded-hash"]


@pytest.mark.parametrize("path", ["otp", "password"])
def test_trusted_device_touch_occurs_after_successful_finish_login(monkeypatch, path):
    user = {
        "id": USER_ID,
        "phone": "0901234567",
        "password_hash": "current-hash",
        "is_active": True,
        "deleted_at": None,
    }
    fake = _AuthDB(user)
    fake.trusted_device_id = "device-id"
    monkeypatch.setattr(auth, "db", fake)
    _disable_login_rate_limits(monkeypatch)
    monkeypatch.setattr(auth, "_consume_verified_otp", lambda *_args: None)
    monkeypatch.setattr(auth, "_get_or_create_user", lambda *_args: dict(user))
    monkeypatch.setattr(
        auth,
        "_verify_password",
        lambda *_args, **_kwargs: (True, False),
    )
    monkeypatch.setattr(auth, "_2fa_is_enabled", lambda *_args: True)
    events = []
    execute = fake._execute

    def track_execute(conn, sql, params=()):
        if "UPDATE trusted_devices SET last_used_at" in sql:
            events.append("touch")
        return execute(conn, sql, params)

    fake._execute = track_execute

    async def finish(*_args):
        events.append("finish")
        return {"success": True}

    monkeypatch.setattr(auth, "_finish_login", finish)

    result = asyncio.run(_run_trusted_login_path(path, Response()))

    assert result == {"success": True}
    assert events == ["finish", "touch"]


@pytest.mark.parametrize("path", ["otp", "password"])
def test_trusted_device_stale_finish_login_does_not_touch(monkeypatch, path):
    user = {
        "id": USER_ID,
        "phone": "0901234567",
        "password_hash": "current-hash",
        "is_active": True,
        "deleted_at": None,
    }
    fake = _AuthDB(user)
    fake.trusted_device_id = "device-id"
    monkeypatch.setattr(auth, "db", fake)
    _disable_login_rate_limits(monkeypatch)
    monkeypatch.setattr(auth, "_consume_verified_otp", lambda *_args: None)
    monkeypatch.setattr(auth, "_get_or_create_user", lambda *_args: dict(user))
    monkeypatch.setattr(
        auth,
        "_verify_password",
        lambda *_args, **_kwargs: (True, False),
    )
    monkeypatch.setattr(auth, "_2fa_is_enabled", lambda *_args: True)
    events = []
    execute = fake._execute

    def track_execute(conn, sql, params=()):
        if "UPDATE trusted_devices SET last_used_at" in sql:
            events.append("touch")
        return execute(conn, sql, params)

    fake._execute = track_execute

    async def stale_finish(*_args):
        events.append("finish")
        raise HTTPException(401, "stale")

    monkeypatch.setattr(auth, "_finish_login", stale_finish)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(_run_trusted_login_path(path, Response()))

    assert exc.value.status_code == 401
    assert events == ["finish"]
