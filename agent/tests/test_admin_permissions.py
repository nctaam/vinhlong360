"""Contract tests for the shared AdminCP role/scope resolver."""

import asyncio
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_moderator_receives_only_moderation_scope():
    from admin_permissions import admin_scopes_for_user

    assert admin_scopes_for_user({"role": "moderator"}) == ["moderation.manager"]


def test_admin_receives_all_operational_scopes():
    from admin_permissions import admin_scopes_for_user

    assert admin_scopes_for_user({"role": "admin"}) == [
        "content.editor",
        "moderation.manager",
        "ops.deploy",
        "security.admin",
        "settings.admin",
    ]


def test_superadmin_receives_wildcard():
    from admin_permissions import admin_scopes_for_user

    assert admin_scopes_for_user({"role": "superadmin"}) == ["*"]


def test_custom_scopes_are_normalized_and_deduplicated():
    from admin_permissions import admin_scopes_for_user, has_admin_entry_scope

    user = {
        "role": "user",
        "admin_scopes": "content.editor, moderation.manager, content.editor",
        "permissions": ["security.admin", ""],
    }

    assert admin_scopes_for_user(user) == [
        "content.editor",
        "moderation.manager",
        "security.admin",
    ]
    assert has_admin_entry_scope(user) is True


def test_regular_user_has_no_admin_entry_scope():
    from admin_permissions import admin_scopes_for_user, has_admin_entry_scope

    user = {"role": "user"}

    assert admin_scopes_for_user(user) == []
    assert has_admin_entry_scope(user) is False


def test_safe_user_exposes_normalized_admin_scopes():
    from auth import _safe_user

    payload = _safe_user({
        "id": "moderator-1",
        "phone": "0900000000",
        "role": "moderator",
    })

    assert payload["admin_scopes"] == ["moderation.manager"]


def test_safe_user_keeps_regular_user_scope_empty():
    from auth import _safe_user

    payload = _safe_user({
        "id": "user-1",
        "phone": "0900000001",
        "role": "user",
    })

    assert payload["admin_scopes"] == []


@pytest.mark.parametrize(
    ("scopes", "expected"),
    [
        (["moderation.manager"], {"moderation": 7, "reports": 11}),
        (
            ["content.editor"],
            {"images": 3, "unclassified": 5, "provisional": 13},
        ),
        (["ops.deploy"], {}),
        (["settings.admin"], {}),
        (["security.admin"], {}),
        (
            ["*"],
            {
                "moderation": 7,
                "images": 3,
                "unclassified": 5,
                "provisional": 13,
                "reports": 11,
            },
        ),
    ],
)
def test_badge_counts_only_exposes_workstream_queues(scopes, expected):
    from admin_permissions import filter_admin_badge_counts

    counts = {
        "moderation": 7,
        "images": 3,
        "unclassified": 5,
        "provisional": 13,
        "reports": 11,
    }

    assert filter_admin_badge_counts(counts, scopes) == expected


def test_badge_counts_filters_cached_payload_for_request_scope(monkeypatch):
    import admin

    counts = {
        "moderation": 7,
        "images": 3,
        "unclassified": 5,
        "provisional": 13,
        "reports": 11,
    }
    monkeypatch.setitem(admin._badge_cache, "data", counts)
    monkeypatch.setitem(admin._badge_cache, "ts", time.time())
    request = SimpleNamespace(
        state=SimpleNamespace(admin_scopes=["moderation.manager"]),
    )

    assert asyncio.run(admin.badge_counts(request)) == {
        "moderation": 7,
        "reports": 11,
    }


def test_dashboard_alerts_only_exposes_actor_workstream():
    from admin_permissions import filter_admin_dashboard_alerts

    alerts = [
        {"type": "flagged", "count": 2},
        {"type": "appeals", "count": 3},
        {"type": "images", "count": 5},
        {"type": "unclassified", "count": 7},
    ]

    assert filter_admin_dashboard_alerts(alerts, ["moderation.manager"]) == [
        {"type": "flagged", "count": 2},
        {"type": "appeals", "count": 3},
    ]
    assert filter_admin_dashboard_alerts(alerts, ["content.editor"]) == [
        {"type": "images", "count": 5},
        {"type": "unclassified", "count": 7},
    ]
    assert filter_admin_dashboard_alerts(alerts, ["ops.deploy"]) == []
    assert filter_admin_dashboard_alerts(alerts, ["*"]) == alerts


def test_dashboard_alerts_filters_payload_for_request_scope(monkeypatch):
    import admin

    alerts = [
        {"type": "reports", "count": 2},
        {"type": "provisional", "count": 3},
    ]

    async def fake_to_thread(_query):
        return {"alerts": alerts}

    monkeypatch.setattr(admin.asyncio, "to_thread", fake_to_thread)
    request = SimpleNamespace(
        state=SimpleNamespace(admin_scopes=["moderation.manager"]),
    )

    assert asyncio.run(admin.dashboard_alerts(request)) == {
        "alerts": [{"type": "reports", "count": 2}],
    }


def test_dashboard_alerts_filters_scope_before_top_five(monkeypatch):
    import admin

    monkeypatch.setattr(admin.db, "_use_pg", False)
    monkeypatch.setattr(admin, "_count_open_info_reports", lambda: 0)

    def add_images(alerts):
        alerts.append({"type": "images", "count": 1, "priority": 6})

    def add_unclassified(alerts):
        alerts.append({"type": "unclassified", "count": 1, "priority": 7})

    def add_provisional(alerts):
        alerts.append({"type": "provisional", "count": 1, "priority": 8})

    def add_moderation(alerts):
        alerts.extend(
            {"type": "appeals", "count": 1, "priority": priority}
            for priority in range(1, 6)
        )

    monkeypatch.setattr(admin, "_dashboard_alerts_images", add_images)
    monkeypatch.setattr(admin, "_dashboard_alerts_unclassified", add_unclassified)
    monkeypatch.setattr(admin, "_dashboard_alerts_provisional", add_provisional)
    monkeypatch.setattr(admin, "_dashboard_alerts_appeals", add_moderation)
    request = SimpleNamespace(
        state=SimpleNamespace(admin_scopes=["content.editor"]),
    )

    result = asyncio.run(admin.dashboard_alerts(request))

    assert [alert["type"] for alert in result["alerts"]] == [
        "images",
        "unclassified",
        "provisional",
    ]


def test_moderator_is_denied_unrelated_or_unknown_admin_reads(monkeypatch):
    import admin
    from fastapi import HTTPException
    from starlette.requests import Request

    monkeypatch.setattr(admin, "_require_admin_rate_limit", lambda _request: "127.0.0.1")
    monkeypatch.setattr(admin, "verify_admin_key", lambda _request: False)

    async def current_user(_request):
        return {"id": "moderator-3", "role": "moderator"}

    async def no_side_effects(*_args, **_kwargs):
        return None

    monkeypatch.setattr(admin, "get_current_user", current_user)
    monkeypatch.setattr(admin, "_require_admin_mutation_side_effects", no_side_effects)

    for path in ("/admin/stats", "/admin/entity-schema", "/admin/unknown-read"):
        request = Request({
            "type": "http",
            "method": "GET",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
        })
        with pytest.raises(HTTPException) as exc:
            asyncio.run(admin.require_admin(request))
        assert exc.value.status_code == 403
