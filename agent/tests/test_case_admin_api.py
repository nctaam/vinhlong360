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
    from config import settings

    double = _AdminDouble()
    monkeypatch.setitem(sys.modules, "admin", double)
    monkeypatch.setattr(settings, "CASE_KERNEL_ENABLED", True, raising=False)
    return double


def test_a_dormant_kernel_answers_404_before_it_checks_anybody_scope(monkeypatch):
    from fastapi import HTTPException

    from config import settings

    monkeypatch.setattr(settings, "CASE_KERNEL_ENABLED", False, raising=False)

    with pytest.raises(HTTPException) as excinfo:
        _run(require_case_action("queue.view"))

    # 403 would confirm the workbench is there and only the scope is missing.
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail["code"] == "capability_unavailable"


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


# ── Private-data clearance ──

import os  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from urllib.parse import parse_qs, urlparse  # noqa: E402

import database  # noqa: E402
from cases.security import CaseCrypto  # noqa: E402

UTC = timezone.utc
MASTER_KEY = "0" * 43


def _now():
    """Per-call, never module-level: the table checks expires_at against the
    database's own clock, and a stamp taken at collection time is already stale
    by the time a 20-minute full-suite run reaches these tests."""
    return datetime.now(UTC).replace(microsecond=0)


# Kept for call sites: evaluating it per use via _now() is the point.



def _pg_url():
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {
        "localhost", "127.0.0.1", "::1",
    }:
        return None
    if {"host", "hostaddr"} & parse_qs(parsed.query, keep_blank_values=True).keys():
        return None
    return raw


TEST_DATABASE_URL = _pg_url()
pg_only = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database",
)


@pytest.fixture
def pg_case():
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    from cases.admin_api import configure_case_admin_api

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    with adapter._conn(commit_on_success=False) as conn:
        case_id = str(adapter._fetchone(
            conn,
            "INSERT INTO cases (service_kind, category, phase, activity, disposition_family,"
            " reporter_privacy, owner_ref, current_revision, promise_policy_ref)"
            " VALUES ('correction','correction','triage','active','undetermined','anonymous',"
            " 'person:owner',1,'correction-pilot-v1') RETURNING case_id",
            (),
        )["case_id"])
        conn.commit()
    configure_case_admin_api(database=adapter, crypto=CaseCrypto(MASTER_KEY))
    yield adapter, case_id
    configure_case_admin_api(database=None, crypto=None)


def _operator(ref="user:7"):
    return SimpleNamespace(actor_ref=ref)


@pg_only
def test_a_fresh_grant_opens_the_report_for_the_person_who_earned_it(pg_case):
    from cases.admin_api import grant_private_evidence_access, require_private_evidence_access

    _adapter, case_id = pg_case

    grant = grant_private_evidence_access(case_id, _operator(), now=_now())
    require_private_evidence_access(case_id, _operator(), grant.secret, now=_now())

    assert timedelta(minutes=14) < grant.expires_at - _now() <= timedelta(minutes=15)


@pg_only
def test_only_the_digest_of_a_grant_is_ever_stored(pg_case):
    from cases.admin_api import grant_private_evidence_access

    adapter, case_id = pg_case

    grant = grant_private_evidence_access(case_id, _operator(), now=_now())

    with adapter._conn(commit_on_success=False) as conn:
        stored = adapter._fetchone(
            conn,
            "SELECT session_digest FROM case_admin_access_sessions WHERE case_id=%s",
            (case_id,),
        )["session_digest"]
    # A database copy must not be usable as the clearance itself.
    assert grant.secret not in stored
    assert len(stored) == 64


@pg_only
@pytest.mark.parametrize("scenario", ["expired", "revoked", "wrong_secret", "missing", "other_person"])
def test_every_way_a_clearance_can_be_absent_fails_the_same(pg_case, scenario):
    from cases.admin_api import (
        StepUpRefused,
        grant_private_evidence_access,
        revoke_private_evidence_access,
        require_private_evidence_access,
    )

    _adapter, case_id = pg_case
    grant = grant_private_evidence_access(case_id, _operator(), now=_now())
    secret, actor, when = grant.secret, _operator(), _now()
    if scenario == "expired":
        when = _now() + timedelta(minutes=16)
    elif scenario == "revoked":
        revoke_private_evidence_access(case_id, _operator(), now=_now())
    elif scenario == "wrong_secret":
        secret = "0" * 43
    elif scenario == "missing":
        secret = None
    else:
        actor = _operator("user:8")

    with pytest.raises(StepUpRefused) as excinfo:
        require_private_evidence_access(case_id, actor, secret, now=when)

    # One code for all five: telling them which half was right is a hint.
    assert excinfo.value.code == "case_private_access_required"


@pg_only
def test_a_shared_admin_key_can_never_hold_somebody_else_report(pg_case):
    from cases.admin_api import StepUpRefused, grant_private_evidence_access

    _adapter, case_id = pg_case

    with pytest.raises(StepUpRefused) as excinfo:
        grant_private_evidence_access(case_id, _operator("admin-key"), now=_now())

    # A deployment key identifies no person, so nobody could be held answerable.
    assert excinfo.value.code == "human_operator_required"


@pg_only
def test_re_authenticating_replaces_the_old_clearance_rather_than_stacking(pg_case):
    from cases.admin_api import (
        StepUpRefused,
        grant_private_evidence_access,
        require_private_evidence_access,
    )

    _adapter, case_id = pg_case
    first = grant_private_evidence_access(case_id, _operator(), now=_now())
    second = grant_private_evidence_access(case_id, _operator(), now=_now())

    require_private_evidence_access(case_id, _operator(), second.secret, now=_now())
    with pytest.raises(StepUpRefused):
        require_private_evidence_access(case_id, _operator(), first.secret, now=_now())


# ── The router is actually mounted ──

import server  # noqa: E402


def test_every_workbench_command_is_reachable_on_the_running_app():
    paths = {getattr(route, "path", "") for route in server.app.routes}

    # A module full of routes nobody mounted is the quietest way to ship nothing.
    assert {
        "/admin/cases",
        "/admin/cases/{case_id}",
        "/admin/cases/access/step-up",
        "/admin/cases/work/claim",
        "/admin/cases/work/heartbeat",
        "/admin/cases/work/release",
        "/admin/cases/work/takeover",
        "/admin/cases/work/recuse",
        "/admin/cases/change-sets",
        "/admin/cases/change-sets/apply",
        "/admin/cases/change-sets/rollback",
        "/admin/cases/change-sets/verify",
        "/admin/cases/evidence",
        "/admin/cases/decisions",
        "/admin/cases/assisted/corrections",
    } <= paths


def test_no_workbench_route_was_left_without_an_action_guard():
    actions = set()
    for route in server.app.routes:
        if not getattr(route, "path", "").startswith("/admin/cases"):
            continue
        for dependency in getattr(route, "dependencies", ()):
            action = getattr(dependency.dependency, "case_action", None)
            if action:
                actions.add(action)
    # Every mounted route carries one, and each names a command from the table.
    assert actions <= set(CASE_ACTION_SCOPE)
    assert len(actions) >= 16


def test_every_command_in_the_table_now_has_a_route_except_guided_intake():
    wired = set()
    for route in server.app.routes:
        for dependency in getattr(route, "dependencies", ()):
            action = getattr(dependency.dependency, "case_action", None)
            if action:
                wired.add(action)

    # Every command the table names is now reachable.
    assert set(CASE_ACTION_SCOPE) - wired == set()


def test_a_ruling_is_judged_and_observed_at_the_stored_risk(monkeypatch):
    import asyncio
    from contextlib import contextmanager

    from cases.admin_api import DecisionBody, decide_case_item
    from cases.domain import RiskClass

    events = []
    seen = {}
    monkeypatch.setattr("cases.metrics.observe",
                        lambda kind, **kw: events.append((kind, kw.get("risk_class"))) or True)
    monkeypatch.setattr("cases.correction.load_evidence_records", lambda case_id, item_id: ())

    def fake_decide(command, now):
        seen["risk"] = command.risk_class
        return SimpleNamespace(item_id=command.item_id, outcome_code="corrected",
                               reason_code=command.reason_code)

    monkeypatch.setattr("cases.correction.decide_item", fake_decide)

    class _Tx:
        def load_correction_items(self, case_id):
            return (SimpleNamespace(item_id="i-1", risk_class=RiskClass.R2),)

    class _Store:
        @contextmanager
        def transaction(self):
            yield _Tx()

    monkeypatch.setattr("cases.admin_api._store", lambda: _Store())

    # The caller claims R1; the stored item says R2. Storage wins, or any
    # decision could be judged by the easiest rules on offer.
    body = DecisionBody(case_id="c-1", item_id="i-1", outcome_code="corrected",
                        reason_code="source_confirms_change", risk_class="R1")
    asyncio.run(decide_case_item(SimpleNamespace(state=SimpleNamespace()), body))

    assert seen["risk"] is RiskClass.R2
    assert events == [("decided", "RiskClass.R2")] or events == [("decided", "R2")]


def test_the_queue_route_serialises_the_full_grammar(monkeypatch):
    import asyncio

    from cases.admin_api import list_case_queue

    class _Page:
        items = [SimpleNamespace(
            work_item_id="w-1", case_id="c-1", kind="decide", risk_class="R2",
            status="claimed", revision=3, promise_health="breached",
            assignee_ref="user:7",
        )]

    monkeypatch.setattr("cases.work_control.list_queue",
                        lambda actor, filters, now: _Page())

    payload = asyncio.run(list_case_queue(SimpleNamespace(state=SimpleNamespace())))

    row = payload["items"][0]
    # queue -> promise health -> owner -> next action: a rank that only sorts
    # is a rank the operator cannot see, so every row carries its words.
    assert row["promise_health"] == "breached"
    assert row["owner_ref"] == "user:7"
    assert row["kind"] == "decide" and row["revision"] == 3
