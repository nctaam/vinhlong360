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
        ("moderator", "moderator"),
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
