"""The workbench guards: each route carries its own authority into the admin gate.

The guard reuses AdminCP authentication, rate limiting and audit, and replaces
only the scope decision. That override is the whole point: without it every
`/admin/cases` route would answer to whatever the prefix allows, and reading the
queue would be enough to change the live site.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases import admin_api  # noqa: E402
from cases.admin_api import CASE_ACTION_SCOPE, require_case_action  # noqa: E402


class _AdminDouble:
    def __init__(self) -> None:
        self.overrides: list[str | None] = []
        self.csrf_calls = 0

    async def require_admin(self, request, required_scope_override=None):
        self.overrides.append(required_scope_override)

    async def require_csrf(self, request):
        self.csrf_calls += 1


@pytest.fixture
def admin_double(monkeypatch):
    double = _AdminDouble()
    monkeypatch.setitem(sys.modules, "admin", double)
    return double


def _run(guard, request=None):
    asyncio.run(guard(request or SimpleNamespace()))


def test_a_guard_carries_its_own_scope_into_the_admin_gate(admin_double):
    _run(require_case_action("changeset.apply"))

    # Not None: a None override lets the path table decide, which for this prefix
    # would mean one gate for every command behind it.
    assert admin_double.overrides == ["publication.apply"]


def test_every_command_gets_the_scope_the_table_names(admin_double):
    for action, expected in CASE_ACTION_SCOPE.items():
        _run(require_case_action(action))

    assert admin_double.overrides == list(CASE_ACTION_SCOPE.values())


def test_a_guard_still_demands_the_csrf_token(admin_double):
    _run(require_case_action("item.decide"))

    # The workbench must not become the one admin surface without CSRF.
    assert admin_double.csrf_calls == 1


def test_a_mistyped_action_fails_when_the_route_is_declared():
    # At import time, where it is a visible error, rather than at request time
    # where it would look like somebody's permissions were wrong.
    with pytest.raises(KeyError):
        require_case_action("changeset.aply")


def test_each_guard_says_which_command_it_belongs_to():
    guard = require_case_action("work.takeover")

    assert guard.case_action == "work.takeover"
    assert guard.case_scope == "case.supervisor"
    assert "takeover" in guard.__name__


def test_the_module_does_not_export_a_bare_router_symbol():
    # A second module-level name `router` makes the static route registry read
    # the earlier route module as unmounted; this package learned that once.
    assert not hasattr(admin_api, "router")
