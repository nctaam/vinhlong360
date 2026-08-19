"""One scope per action, never one scope for the prefix.

A single `/admin/cases` gate would mean anyone allowed to read the queue is also
allowed to publish to the live site. Each command names the scope it needs, and
this file is the table of who may do what — kept as data so a new route cannot
quietly inherit somebody else's authority.

The separations that matter: transcribing is not deciding, deciding is not
publishing, publishing is not supervising, and supervising does not lift the
risk guards it was given to work around.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from admin_permissions import (  # noqa: E402
    ADMIN_ENTRY_SCOPES,
    CASE_ACTION_SCOPES,
    admin_scopes_for_user,
)
from cases.admin_api import CASE_ACTION_SCOPE, action_scope, may_perform  # noqa: E402


def _user(*scopes) -> dict:
    return {"role": "moderator", "admin_scopes": list(scopes)}


# ── The table itself ──

def test_every_action_names_its_own_scope():
    # A missing entry would fall back to the router's gate, which is the
    # prefix-wide overgrant this design exists to prevent.
    assert set(CASE_ACTION_SCOPE) == {
        "queue.view", "case.view", "access.stepup", "access.revoke",
        "work.claim", "work.heartbeat", "work.release", "work.takeover", "work.recuse",
        "evidence.add", "item.decide",
        "changeset.build", "changeset.apply", "changeset.verify", "changeset.rollback",
        "assisted.create",
    }
    assert set(CASE_ACTION_SCOPE.values()) <= CASE_ACTION_SCOPES


def test_an_unknown_action_is_refused_rather_than_defaulted():
    with pytest.raises(KeyError):
        action_scope("changeset.publish_everything")


# ── Who may do what ──

def test_an_operator_may_transcribe_and_view_but_may_not_decide():
    operator = _user("service.operator")

    assert may_perform(operator, "queue.view")
    assert may_perform(operator, "case.view")
    assert may_perform(operator, "assisted.create")
    assert may_perform(operator, "evidence.add")
    # Taking down what somebody reported is not the same as ruling on it.
    assert not may_perform(operator, "item.decide")
    assert not may_perform(operator, "changeset.apply")


def test_a_decision_maker_may_rule_but_may_not_publish():
    decider = _user("correction.decide")

    assert may_perform(decider, "item.decide")
    assert may_perform(decider, "changeset.build")
    # Deciding a correction is owed is not permission to change the live site.
    assert not may_perform(decider, "changeset.apply")
    assert not may_perform(decider, "changeset.rollback")


def test_a_publisher_may_publish_but_may_not_decide_or_supervise():
    publisher = _user("publication.apply", "publication.verify")

    assert may_perform(publisher, "changeset.apply")
    assert may_perform(publisher, "changeset.rollback")
    assert may_perform(publisher, "changeset.verify")
    assert not may_perform(publisher, "item.decide")
    # Taking work off a colleague is a supervisor act, not a publishing one.
    assert not may_perform(publisher, "work.takeover")


def test_only_a_supervisor_may_take_work_from_somebody_else():
    assert may_perform(_user("case.supervisor"), "work.takeover")
    for scope in ("service.operator", "correction.decide", "publication.apply"):
        assert not may_perform(_user(scope), "work.takeover")


def test_verification_is_its_own_authority_not_a_free_rider_on_applying():
    # Applying writes the row; verifying is the separate claim that a reader can
    # see it. One person holding both is a choice, not a default.
    assert action_scope("changeset.apply") != action_scope("changeset.verify")
    assert not may_perform(_user("publication.apply"), "changeset.verify")


def test_a_superadmin_passes_every_gate():
    assert all(may_perform(None, action) for action in CASE_ACTION_SCOPE)


def test_holding_no_case_scope_gets_nothing():
    stranger = _user("content.editor")

    assert not any(may_perform(stranger, action) for action in CASE_ACTION_SCOPE)


# ── The scopes exist in the shared permission model ──

def test_every_case_scope_is_a_real_admin_scope():
    # A guard naming a scope nobody can be granted would fail closed forever and
    # look like a permissions bug rather than a typo.
    assert CASE_ACTION_SCOPES <= ADMIN_ENTRY_SCOPES
    assert set(CASE_ACTION_SCOPE.values()) <= set(admin_scopes_for_user(
        {"role": "admin"}
    ))
