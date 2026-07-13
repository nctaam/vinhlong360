import ast
import asyncio  # noqa: F401
import inspect  # noqa: F401
import textwrap
from contextlib import contextmanager  # noqa: F401
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import admin
import auth  # noqa: F401


ADMIN_ID = "00000000-0000-0000-0000-000000000001"
PEER_ID = "00000000-0000-0000-0000-000000000002"
SUPER_ID = "00000000-0000-0000-0000-000000000003"
USER_ID = "00000000-0000-0000-0000-000000000004"


def _request(actor):
    return SimpleNamespace(state=SimpleNamespace(admin_user=actor))


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
        self.pending = []
        self.sessions = []
        self.fetches = []
        self.executes = []

    @contextmanager
    def _conn(self):
        yield object()

    def _fetchone(self, _conn, sql, params=()):
        self.fetches.append((sql, params))
        if "FROM users" in sql:
            return dict(self.user) if self.user else None
        return None

    def _execute(self, _conn, sql, params=()):
        self.executes.append((sql, params))
        if "INSERT INTO pending_2fa" in sql:
            self.pending.append(params)
        if "INSERT INTO user_sessions" in sql:
            self.sessions.append(params)

    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row else None


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


def test_legacy_rehash_updates_local_password_snapshot_before_auth_creation():
    tree = ast.parse(textwrap.dedent(inspect.getsource(auth.login_password)))
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)]
    user_copy = next(
        node
        for node in assignments
        if any(isinstance(target, ast.Name) and target.id == "user" for target in node.targets)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "dict"
    )
    snapshot_update = next(
        node
        for node in assignments
        if any(
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name)
            and target.value.id == "user"
            and isinstance(target.slice, ast.Constant)
            and target.slice.value == "password_hash"
            for target in node.targets
        )
        and isinstance(node.value, ast.Name)
        and node.value.id == "new_hash"
    )
    rehash_call = _threaded_helper_calls(auth.login_password, "_rehash")[0]
    challenge_call = _threaded_helper_calls(auth.login_password, "_create_pending_2fa")[0]
    finish_call = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_finish_login"
    )

    assert rehash_call.lineno < user_copy.lineno < snapshot_update.lineno
    assert snapshot_update.lineno < challenge_call.lineno
    assert snapshot_update.lineno < finish_call.lineno
