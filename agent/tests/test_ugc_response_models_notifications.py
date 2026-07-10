# -*- coding: utf-8 -*-
"""W6.3 — response_model an toàn cho notifications.py (UGC PG-only).

Endpoint UGC trả 503 local (không PG) → KHÔNG gọi verify được. Thay bằng:
 1) shape-contract: dựng payload KHỚP return-statement (gồm field KHÔNG khai)
    → Model.model_validate KHÔNG raise + field không-khai VẪN CÒN (no-strip).
 2) 503-still-works: TestClient(router) gọi GET → 503 (SQLite) HOẶC 200,
    KHÔNG 500 → chứng minh response_model không phá path.
"""
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import notifications  # noqa: E402
from api_schemas import ApiModel  # noqa: E402
import api_schemas_notif as sn  # noqa: E402


# ── Router wiring: mỗi GET (trừ SSE stream) phải có response_model kế ApiModel ──

# path → model đã khai (SSE stream = StreamingResponse → BỎ QUA)
WIRED = {
    "/api/notifications": sn.NotificationsResponse,
    "/api/notifications/unread-count": sn.UnreadCountResponse,
    "/api/notification-preferences": sn.NotificationPreferencesResponse,
    "/api/follow/check/{target_type}/{target_id}": sn.FollowCheckResponse,
    "/api/following": sn.FollowingResponse,
    "/api/followers/count/{target_type}/{target_id}": sn.FollowerCountResponse,
    "/api/blocked-users": sn.BlockedUsersResponse,
    "/api/muted-users": sn.MutedUsersResponse,
    "/api/events/{entity_id}/rsvp": sn.RsvpStatusResponse,
}

SKIPPED_STREAM = "/api/notifications/stream"


def _get_routes():
    """path → (methods, response_model) cho mọi route GET của router."""
    out = {}
    for r in notifications.router.routes:
        if hasattr(r, "path") and "GET" in getattr(r, "methods", set()):
            out[r.path] = getattr(r, "response_model", None)
    return out


def test_all_get_endpoints_wired_except_stream():
    routes = _get_routes()
    for path, model in WIRED.items():
        rm = routes.get(path)
        assert rm is not None, f"{path} thiếu response_model"
        assert rm is model, f"{path} sai response_model: {rm}"
        assert issubclass(rm, ApiModel), f"{path} phải kế ApiModel (extra=allow)"


def test_stream_endpoint_has_no_response_model():
    # SSE StreamingResponse → response_model KHÔNG hợp → phải để trống.
    routes = _get_routes()
    assert SKIPPED_STREAM in routes, "stream endpoint phải tồn tại"
    assert routes[SKIPPED_STREAM] is None, "stream KHÔNG được gắn response_model"


def test_all_models_inherit_apimodel_allow():
    # Guard: base extra='allow' → không strip field FE.
    assert ApiModel.model_config.get("extra") == "allow"
    for model in WIRED.values():
        assert issubclass(model, ApiModel)


# ── Shape-contract: payload KHỚP return-statement, field không-khai vẫn còn ──

def _assert_no_strip(model, payload, extra_key, extra_val):
    """model_validate KHÔNG raise + field không-khai (extra) VẪN CÒN sau dump.

    Chèn extra_key vào payload (mô phỏng field return-statement KHÔNG khai
    trong model) → chứng minh extra='allow' mang qua nguyên.
    """
    full = {**payload, extra_key: extra_val}
    m = model.model_validate(full)
    dumped = m.model_dump()
    # tất cả field khai của payload đi qua
    for k in payload:
        assert k in dumped, f"{model.__name__}: field {k} bị strip"
    # field KHÔNG khai vẫn pass-through (extra='allow')
    assert dumped.get(extra_key) == extra_val, (
        f"{model.__name__}: field không-khai {extra_key} bị strip"
    )


def test_notifications_response_shape():
    # get_notifications → {"notifications": [grouped...], "unread_count": int}
    # item chứa field không khai (id/type/title/is_read...) phải pass-through.
    payload = {
        "notifications": [
            {"id": "n1", "type": "like", "title": "T", "body": None,
             "ref_type": "post", "ref_id": "p1", "is_read": False,
             "created_at": "2026-06-10T10:00:00", "group_count": 3},
        ],
        "unread_count": 5,
    }
    m = sn.NotificationsResponse.model_validate(payload)
    d = m.model_dump()
    assert d["unread_count"] == 5
    assert d["notifications"][0]["group_count"] == 3  # item field không-khai còn


def test_unread_count_response_shape():
    _assert_no_strip(sn.UnreadCountResponse,
                     {"unread_count": 7}, "surprise", "x")


def test_notification_preferences_response_shape():
    # 2 return path đều là dict 5 cờ bool.
    payload = {"pref_like": True, "pref_comment": False, "pref_mention": True,
               "pref_follow": True, "pref_system": False}
    m = sn.NotificationPreferencesResponse.model_validate(payload)
    d = m.model_dump()
    assert d["pref_like"] is True and d["pref_comment"] is False


def test_follow_check_response_shape():
    _assert_no_strip(sn.FollowCheckResponse,
                     {"following": True}, "extra", 1)
    # False path
    assert sn.FollowCheckResponse.model_validate({"following": False}).following is False


def test_following_response_shape():
    # get_following → {"following": [items], "total": int, "has_more": bool}
    payload = {
        "following": [
            {"target_type": "user", "target_id": "u1", "target_name": "Ai đó",
             "entity_type": None, "created_at": "2026-06-10T10:00:00"},
        ],
        "total": 1,
        "has_more": False,
    }
    m = sn.FollowingResponse.model_validate(payload)
    d = m.model_dump()
    assert d["total"] == 1 and d["has_more"] is False
    # item field không-khai còn nguyên
    assert d["following"][0]["target_name"] == "Ai đó"


def test_follower_count_response_shape():
    _assert_no_strip(sn.FollowerCountResponse,
                     {"count": 42}, "extra", "y")


def test_blocked_users_response_shape():
    payload = {
        "blocked": [
            {"id": "u1", "display_name": "N", "avatar_url": None,
             "username": "user1", "blocked_at": "2026-06-10T10:00:00"},
        ],
        "total": 1, "page": 1, "has_more": False,
    }
    m = sn.BlockedUsersResponse.model_validate(payload)
    d = m.model_dump()
    assert d["total"] == 1 and d["page"] == 1 and d["has_more"] is False
    assert d["blocked"][0]["username"] == "user1"


def test_muted_users_response_shape():
    payload = {
        "muted": [
            {"id": "u2", "display_name": "M", "avatar_url": None,
             "username": "user2", "muted_at": "2026-06-10T10:00:00"},
        ],
        "total": 1, "page": 1, "has_more": False,
    }
    m = sn.MutedUsersResponse.model_validate(payload)
    d = m.model_dump()
    assert d["total"] == 1 and d["muted"][0]["username"] == "user2"


def test_rsvp_status_response_shape():
    # toggle_rsvp → {"going": bool, "count": int}; get_rsvp → {"count": int, "going": bool}
    payload = {"count": 12, "going": True}
    m = sn.RsvpStatusResponse.model_validate(payload)
    d = m.model_dump()
    assert d["count"] == 12 and d["going"] is True


def test_empty_list_payloads_validate():
    # Trạng thái rỗng (list=[], count=0) — return-statement hợp lệ, không raise.
    assert sn.NotificationsResponse.model_validate(
        {"notifications": [], "unread_count": 0}).unread_count == 0
    assert sn.FollowingResponse.model_validate(
        {"following": [], "total": 0, "has_more": False}).total == 0
    assert sn.BlockedUsersResponse.model_validate(
        {"blocked": [], "total": 0, "page": 1, "has_more": False}).total == 0


# ── 503-still-works: response_model KHÔNG phá path 503 (SQLite, không PG) ──

def _client():
    app = FastAPI()
    app.include_router(notifications.router)
    return TestClient(app, raise_server_exceptions=False)


def test_get_endpoints_return_503_not_500_on_sqlite():
    from database import db
    if db._use_pg:
        # Có PG (dev cộng đồng) → endpoint sẽ 200/401, chỉ cần KHÔNG 500.
        pass
    c = _client()
    # 2 GET endpoint không cần path-param → gọi trực tiếp.
    for path in ("/api/notifications", "/api/notifications/unread-count"):
        r = c.get(path)
        assert r.status_code != 500, f"{path} → 500 (response_model phá path)"
        # SQLite: router dep require_pg → 503 trước handler.
        if not db._use_pg:
            assert r.status_code == 503, f"{path} → {r.status_code}, mong 503"


def test_public_get_follower_count_no_500_on_sqlite():
    from database import db
    c = _client()
    # /followers/count không require_user nhưng vẫn dưới router require_pg dep.
    r = c.get("/api/followers/count/user/some-id")
    assert r.status_code != 500
    if not db._use_pg:
        assert r.status_code == 503
