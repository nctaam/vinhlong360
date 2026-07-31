"""Shared AdminCP role and scope resolution.

This module stays independent from FastAPI so authentication and AdminCP
authorization expose the same normalized permission contract.
"""

from typing import Any


ADMIN_ROLE_SCOPES: dict[str, set[str]] = {
    "moderator": {"moderation.manager"},
    "admin": {
        "content.editor",
        "moderation.manager",
        "ops.deploy",
        "settings.admin",
        "security.admin",
    },
    "superadmin": {"*"},
}

ADMIN_ENTRY_SCOPES = frozenset({
    "content.editor",
    "moderation.manager",
    "ops.deploy",
    "settings.admin",
    "security.admin",
})

ADMIN_BADGE_KEYS_BY_SCOPE: dict[str, frozenset[str]] = {
    "content.editor": frozenset({"images", "unclassified", "provisional"}),
    "moderation.manager": frozenset({"moderation", "reports"}),
}

ADMIN_ALERT_TYPES_BY_SCOPE: dict[str, frozenset[str]] = {
    "content.editor": frozenset({"images", "unclassified", "provisional"}),
    "moderation.manager": frozenset({"flagged", "moderation", "reports", "appeals"}),
}


def coerce_scope_list(value: Any) -> set[str]:
    """Normalize optional comma-separated or iterable custom scopes."""
    if isinstance(value, str):
        return {part.strip() for part in value.split(",") if part.strip()}
    if isinstance(value, (list, tuple, set)):
        return {str(part).strip() for part in value if str(part).strip()}
    return set()


def admin_scopes_for_user(user: dict | None) -> list[str]:
    """Return the canonical, stable scope list for an administrative actor."""
    if user is None:
        return ["*"]

    scopes = set(ADMIN_ROLE_SCOPES.get(str(user.get("role") or "user"), set()))
    for field in ("admin_scopes", "scopes", "permissions"):
        scopes.update(coerce_scope_list(user.get(field)))

    if "*" in scopes:
        return ["*"]
    return sorted(scopes)


def has_admin_entry_scope(user: dict | None) -> bool:
    """Return whether an actor may enter at least one AdminCP workstream."""
    scopes = set(admin_scopes_for_user(user))
    return "*" in scopes or bool(scopes & ADMIN_ENTRY_SCOPES)


def filter_admin_badge_counts(counts: dict[str, Any], scopes: Any) -> dict[str, Any]:
    """Expose only queue counts owned by the actor's AdminCP workstreams."""
    granted = coerce_scope_list(scopes)
    if "*" in granted:
        return dict(counts)

    allowed_keys: set[str] = set()
    for scope in granted:
        allowed_keys.update(ADMIN_BADGE_KEYS_BY_SCOPE.get(scope, ()))
    return {key: value for key, value in counts.items() if key in allowed_keys}


def filter_admin_dashboard_alerts(alerts: list[dict], scopes: Any) -> list[dict]:
    """Expose only dashboard alerts owned by the actor's workstreams."""
    granted = coerce_scope_list(scopes)
    if "*" in granted:
        return list(alerts)

    allowed_types: set[str] = set()
    for scope in granted:
        allowed_types.update(ADMIN_ALERT_TYPES_BY_SCOPE.get(scope, ()))
    return [alert for alert in alerts if alert.get("type") in allowed_types]
