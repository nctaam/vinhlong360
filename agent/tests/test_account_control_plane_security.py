import asyncio  # noqa: F401
import inspect  # noqa: F401
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


def test_bulk_ban_rejects_mixed_superior_batch_without_any_write(monkeypatch):
    actor = {"id": ADMIN_ID, "role": "admin"}

    async def legacy_auth_lookup(_request):
        return actor

    monkeypatch.setattr(admin, "get_current_user", legacy_auth_lookup)
    fake = _install_admin_db(
        monkeypatch,
        {
            USER_ID: {"id": USER_ID, "role": "user", "is_active": True},
            SUPER_ID: {"id": SUPER_ID, "role": "superadmin", "is_active": True},
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
    monkeypatch.setattr(admin, "_log_mod_action", lambda *_args: None)
    missing = "00000000-0000-0000-0000-000000000099"
    body = admin.BulkUserAction(user_ids=[PEER_ID, missing, USER_ID, PEER_ID])

    result = asyncio.run(
        admin.bulk_ban_users(body, _request(actor))
    )

    assert result["banned_ids"] == [PEER_ID, USER_ID]
    assert result["banned_count"] == 2
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
