"""The operator workbench: one scope per command, and no prefix that grants them all.

`/admin/cases` is not a permission. Reading the queue, transcribing a phone call,
ruling on an item, changing the live site and taking work off a colleague are
five different authorities, and each route names the one it needs. A single gate
on the prefix would mean whoever can read the queue can also publish, which is
the failure this module is shaped to prevent.

Responses here are the safe workbench projection: identifiers, classification and
state. What a person actually reported is private, and reaching it needs both the
work to justify it and a short-lived grant that a separate step-up creates. The
queue never carries it at all.
"""
from __future__ import annotations

import sys
from pathlib import Path

if str(Path(__file__).resolve().parents[1]) not in sys.path:  # pragma: no cover - import shim
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from admin_permissions import admin_scopes_for_user  # noqa: E402

# Every command the workbench offers, against the single authority it needs.
# Kept as data so a route cannot be added without stating what it costs, and so
# the matrix is readable in one place rather than spread across decorators.
CASE_ACTION_SCOPE: dict[str, str] = {
    # Looking at work, and at one case's safe summary.
    "queue.view": "service.operator",
    "case.view": "service.operator",
    # Reaching what a person actually reported, for as long as the work lasts.
    "access.stepup": "service.operator",
    "access.revoke": "service.operator",
    # Holding and handing back work.
    "work.claim": "service.operator",
    "work.heartbeat": "service.operator",
    "work.release": "service.operator",
    "work.recuse": "service.operator",
    # Taking work off somebody else is a supervisor act, not a working one.
    "work.takeover": "case.supervisor",
    # Recording what was found, and ruling on it, are different jobs.
    "evidence.add": "service.operator",
    "item.decide": "correction.decide",
    "changeset.build": "correction.decide",
    # Changing what the public reads, and claiming they can see it.
    "changeset.apply": "publication.apply",
    "changeset.rollback": "publication.apply",
    "changeset.verify": "publication.verify",
    # Taking a correction down the phone on somebody's behalf.
    "assisted.create": "service.operator",
}


def action_scope(action: str) -> str:
    """The scope a command needs. Unknown commands raise rather than default.

    Defaulting would mean a new route silently inherits whatever the prefix
    allows, which is exactly the overgrant this table exists to stop.
    """
    return CASE_ACTION_SCOPE[action]


def may_perform(user: dict | None, action: str) -> bool:
    """Whether this administrative actor holds the authority for one command."""
    scopes = set(admin_scopes_for_user(user))
    return "*" in scopes or action_scope(action) in scopes


def require_case_action(action: str):
    """Build the dependency that guards one command.

    It reuses the AdminCP authentication, rate limiting and audit path, but
    overrides the scope with this command's own instead of letting the router's
    prefix decide. `action_scope` is called at build time so a typo fails when
    the route is declared, not when somebody is refused in production.
    """
    scope = action_scope(action)

    async def guard(request):
        import admin

        await admin.require_admin(request, required_scope_override=scope)
        await admin.require_csrf(request)

    guard.__name__ = f"require_{action.replace('.', '_')}"
    guard.case_action = action
    guard.case_scope = scope
    return guard
