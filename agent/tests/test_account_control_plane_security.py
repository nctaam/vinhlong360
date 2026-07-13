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

    @contextmanager
    def _conn(self):
        yield object()

    def _fetchone(self, _conn, sql, params=()):
        self.fetches.append((sql, params))
        if "FROM users" in sql:
            return self.users.get(str(params[0]))
        return None

    def _execute(self, _conn, sql, params=()):
        self.executes.append((sql, params))

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
