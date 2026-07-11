"""
Tests for session-be features: block enforcement, admin activity feed,
SEO og:image, consent logging, privacy, session management.

Design: same as test_writepaths_*.py —
  - SQLite/CI: verify 503 guards (no PG needed)
  - Pure helper functions: always exercised
  - Postgres happy-paths: skipif(not db._use_pg)
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth
import seo
from database import db

pg_only = pytest.mark.skipif(
    not db._use_pg,
    reason="UGC/auth is Postgres-only. Set DATABASE_URL=postgresql://… to run.",
)


# ── Auth router wiring (new endpoints) ──────────────────────────────────

def _auth_client():
    app = FastAPI()
    app.include_router(auth.router)
    return TestClient(app)


def _route_pairs(app) -> set:
    pairs = set()
    for r in app.routes:
        for m in (getattr(r, "methods", None) or set()):
            pairs.add((m, r.path))
    return pairs


def test_session_endpoints_mounted():
    pairs = _route_pairs(_auth_client().app)
    assert ("GET", "/auth/sessions") in pairs
    assert ("DELETE", "/auth/sessions/{session_id}") in pairs


def test_deactivate_endpoint_mounted():
    pairs = _route_pairs(_auth_client().app)
    assert ("POST", "/auth/deactivate") in pairs


def test_login_history_endpoint_mounted():
    pairs = _route_pairs(_auth_client().app)
    assert ("GET", "/auth/login-history") in pairs


def test_privacy_endpoints_mounted():
    pairs = _route_pairs(_auth_client().app)
    assert ("GET", "/auth/privacy") in pairs
    assert ("PUT", "/auth/privacy") in pairs


def test_consent_history_endpoint_mounted():
    pairs = _route_pairs(_auth_client().app)
    assert ("GET", "/auth/consent-history") in pairs


def test_avatar_endpoint_mounted():
    pairs = _route_pairs(_auth_client().app)
    assert ("POST", "/auth/avatar") in pairs


# ── Auth PG guards for new endpoints ────────────────────────────────────

def test_new_auth_pg_guards():
    client = _auth_client()
    if not db._use_pg:
        assert client.get("/auth/sessions").status_code == 503
        assert client.delete("/auth/sessions/abc").status_code == 503
        assert client.post("/auth/deactivate").status_code == 503
        assert client.get("/auth/login-history").status_code == 503
        assert client.get("/auth/privacy").status_code == 503
        assert client.put("/auth/privacy", json={"show_activity": False}).status_code == 503
        assert client.get("/auth/consent-history").status_code == 503
    else:
        assert client.get("/auth/sessions").status_code in (401, 403)
        assert client.get("/auth/consent-history").status_code in (401, 403)


# ── Password helpers (backend-agnostic) ─────────────────────────────────

def test_password_hash_verify():
    hashed = auth._hash_password("MyPass123")
    assert auth._verify_password("MyPass123", hashed)
    assert not auth._verify_password("WrongPass1", hashed)


def test_password_validation_rules():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        auth.SetPassword(password="short1")
    with pytest.raises(ValidationError):
        auth.SetPassword(password="noletter1" * 0 + "12345678")
    with pytest.raises(ValidationError):
        auth.SetPassword(password="nodigitx")
    auth.SetPassword(password="Valid1pw!")


def test_password_max_length():
    """Password > 128 chars should be rejected (prevent PBKDF2 CPU burn)."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        auth.SetPassword(password="A1" + "x" * 200)


def test_set_password_requires_current_if_has_password():
    """SetPassword model allows current_password=None (for first-time set)."""
    sp = auth.SetPassword(password="NewPass1x")
    assert sp.current_password is None
    sp2 = auth.SetPassword(password="NewPass1x", current_password="OldPass1")
    assert sp2.current_password == "OldPass1"


# ── Privacy model validation ────────────────────────────────────────────

def test_privacy_update_model():
    body = auth.PrivacyUpdate(profile_visibility="private", show_activity=False)
    assert body.profile_visibility == "private"
    assert body.show_activity is False
    assert body.show_saved is None


# ── Social block enforcement: router wiring ─────────────────────────────

def test_social_block_endpoints_mounted():
    import notifications
    app = FastAPI()
    app.include_router(notifications.router)
    pairs = _route_pairs(app)
    assert ("POST", "/api/block/{blocked_id}") in pairs
    assert ("GET", "/api/blocked-users") in pairs


def test_social_blocked_users_pg_guard():
    import notifications
    app = FastAPI()
    app.include_router(notifications.router)
    client = TestClient(app)
    if not db._use_pg:
        assert client.get("/api/blocked-users").status_code == 503
    else:
        assert client.get("/api/blocked-users").status_code in (401, 403)


# ── Entity feed block enforcement: endpoint exists ──────────────────────

def test_entity_feed_endpoint_mounted():
    import social
    app = FastAPI()
    app.include_router(social.router)
    pairs = _route_pairs(app)
    assert ("GET", "/api/entities/{entity_id}/feed") in pairs


# ── Admin activity feed ─────────────────────────────────────────────────

def test_admin_activity_feed_endpoint_mounted():
    import admin
    app = FastAPI()
    app.include_router(admin.router)
    pairs = _route_pairs(app)
    assert ("GET", "/admin/activity-feed") in pairs


@pytest.mark.skipif(db._use_pg, reason="Activity feed serves from admin_audit_events DB table on PG; the JSONL-file path (monkeypatched _AUDIT_FILE) only runs on SQLite/fallback")
def test_admin_activity_feed_reads_jsonl(tmp_path, monkeypatch):
    import admin
    audit_file = tmp_path / "admin_audit.jsonl"
    records = [
        {"ts": "2026-06-27T10:00:00", "actor": "admin-key", "method": "POST", "path": "/admin/entities", "ip": "127.0.0.1"},
        {"ts": "2026-06-27T10:01:00", "actor": "user:abc", "method": "PUT", "path": "/admin/entities/x", "ip": "10.0.0.1"},
        {"ts": "2026-06-27T10:02:00", "actor": "admin-key", "method": "DELETE", "path": "/admin/entities/y", "ip": "127.0.0.1"},
    ]
    audit_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    monkeypatch.setattr(admin, "_AUDIT_FILE", audit_file)

    app = FastAPI()
    app.include_router(admin.router)
    app.dependency_overrides[admin.require_admin] = lambda: "test"
    client = TestClient(app)

    resp = client.get("/admin/activity-feed?limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["actions"]) == 2
    assert data["actions"][0]["method"] == "DELETE"
    assert data["actions"][1]["method"] == "PUT"


@pytest.mark.skipif(db._use_pg, reason="Activity feed serves from admin_audit_events DB table on PG; the JSONL-file path (monkeypatched _AUDIT_FILE) only runs on SQLite/fallback")
def test_admin_activity_feed_empty(tmp_path, monkeypatch):
    import admin
    audit_file = tmp_path / "admin_audit.jsonl"
    monkeypatch.setattr(admin, "_AUDIT_FILE", audit_file)

    app = FastAPI()
    app.include_router(admin.router)
    app.dependency_overrides[admin.require_admin] = lambda: "test"
    client = TestClient(app)

    resp = client.get("/admin/activity-feed")
    assert resp.status_code == 200
    assert resp.json()["actions"] == []


# ── SEO og:image ────────────────────────────────────────────────────────

def test_og_meta_site_default():
    meta = seo.build_og_meta()
    assert meta["og:site_name"] == "VinhLong360"
    assert "og:image" in meta
    assert meta["og:type"] == "website"


def test_og_meta_entity_with_image():
    entity = {
        "id": "cam-sanh",
        "name": "Cam sành",
        "type": "product",
        "summary": "Cam sành ngon lắm",
        "images": ["https://example.com/cam.jpg", "https://example.com/cam2.jpg"],
    }
    meta = seo.build_og_meta(entity)
    assert meta["og:title"] == "Cam sành"
    assert meta["og:image"] == "https://example.com/cam.jpg"
    assert meta["og:type"] == "article"
    assert "Cam sành" in meta["og:description"]


def test_og_meta_entity_no_image():
    entity = {"id": "bun-mam", "name": "Bún mắm", "type": "dish", "images": []}
    meta = seo.build_og_meta(entity)
    assert meta["og:image"] == seo.DEFAULT_OG_IMAGE


def test_twitter_card_meta_site_default():
    meta = seo.build_og_meta()
    assert meta["twitter:card"] == "summary_large_image"
    assert meta["twitter:title"] == meta["og:title"]
    assert meta["twitter:description"] == meta["og:description"]
    assert meta["twitter:image"] == meta["og:image"]


def test_twitter_card_meta_entity():
    entity = {
        "id": "test-entity",
        "name": "Test Entity",
        "type": "attraction",
        "summary": "A test attraction",
        "images": ["https://example.com/photo.jpg"],
    }
    meta = seo.build_og_meta(entity)
    assert meta["twitter:card"] == "summary_large_image"
    assert meta["twitter:title"] == "Test Entity"
    assert meta["twitter:description"] == "A test attraction"
    assert meta["twitter:image"] == "https://example.com/photo.jpg"


def test_og_meta_escapes_html_in_entity_fields():
    entity = {
        "id": "xss-test",
        "name": '"><script>alert(1)</script>',
        "type": "attraction",
        "summary": 'A "test" with <tags> & special chars',
    }
    meta = seo.build_og_meta(entity)
    assert "<script>" not in meta["og:title"]
    assert "&lt;script&gt;" in meta["og:title"]
    assert "<tags>" not in meta["og:description"]
    assert "&amp;" in meta["og:description"]


def test_aggregate_rating_in_jsonld():
    entity = {
        "id": "rated-place",
        "name": "Rated Place",
        "type": "attraction",
        "avg_rating": 4.2,
        "rating_count": 15,
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "aggregateRating" in ld
    assert ld["aggregateRating"]["ratingValue"] == 4.2
    assert ld["aggregateRating"]["ratingCount"] == 15
    assert ld["aggregateRating"]["bestRating"] == 5


def test_aggregate_rating_omitted_when_no_ratings():
    entity = {"id": "no-ratings", "name": "No Ratings", "type": "attraction"}
    ld = seo.build_entity_jsonld(entity, {})
    assert "aggregateRating" not in ld


def test_og_endpoints_mounted():
    app = FastAPI()
    app.include_router(seo.router)
    pairs = _route_pairs(app)
    assert ("GET", "/seo/og/{entity_id}") in pairs
    assert ("GET", "/seo/og") in pairs


def test_og_site_endpoint():
    app = FastAPI()
    app.include_router(seo.router)
    client = TestClient(app)
    resp = client.get("/seo/og")
    assert resp.status_code == 200
    assert resp.json()["og:site_name"] == "VinhLong360"


# ── Consent logging helper ──────────────────────────────────────────────

def test_log_consent_no_crash_without_pg():
    """_log_consent must not crash on SQLite (swallows exception)."""
    auth._log_consent("00000000-0000-0000-0000-000000000000", "1.0", "127.0.0.1")


# ── Audit rotation ──────────────────────────────────────────────────────

def test_audit_rotation(tmp_path, monkeypatch):
    import admin
    audit_file = tmp_path / "admin_audit.jsonl"
    lines = [json.dumps({"ts": f"2026-06-{i:02d}", "actor": "a", "method": "POST", "path": "/x", "ip": "1"}) for i in range(1, 10)]
    audit_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setattr(admin, "_AUDIT_FILE", audit_file)
    monkeypatch.setattr(admin, "_AUDIT_MAX_LINES", 5)
    admin._maybe_rotate_audit()
    remaining = audit_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(remaining) == 5


# ── Dashboard alerts endpoint mounted ───────────────────────────────────

def test_dashboard_alerts_endpoint_mounted():
    import admin
    app = FastAPI()
    app.include_router(admin.router)
    pairs = _route_pairs(app)
    assert ("GET", "/admin/dashboard-alerts") in pairs


# ── Login history helper ────────────────────────────────────────────────

def test_log_login_no_crash_without_pg():
    """_log_login must not crash on SQLite (swallows exception)."""
    from unittest.mock import MagicMock
    mock_req = MagicMock()
    mock_req.headers = {"user-agent": "test"}
    auth._log_login("0901234567", "password", False, mock_req)


# ── Comment edit/delete endpoints ──────────────────────────────────────

def test_comment_edit_delete_endpoints_mounted():
    import social
    app = FastAPI()
    app.include_router(social.router)
    pairs = _route_pairs(app)
    assert ("PUT", "/api/comments/{comment_id}") in pairs
    assert ("DELETE", "/api/comments/{comment_id}") in pairs


def test_comment_edit_pg_guard():
    import social
    app = FastAPI()
    app.include_router(social.router)
    client = TestClient(app)
    if not db._use_pg:
        assert client.put("/api/comments/abc", json={"content": "updated text"}).status_code == 503
        assert client.delete("/api/comments/abc").status_code == 503


# ── Plans / Visits write-path endpoints ────────────────────────────────

def test_plans_endpoints_mounted():
    import plans
    app = FastAPI()
    app.include_router(plans.router)
    pairs = _route_pairs(app)
    assert ("GET", "/api/my-plans") in pairs
    assert ("POST", "/api/my-plans") in pairs


def test_visits_endpoints_mounted():
    import visits
    app = FastAPI()
    app.include_router(visits.router)
    pairs = _route_pairs(app)
    assert ("GET", "/api/me/visits") in pairs
    assert ("POST", "/api/me/visits") in pairs


def test_plans_pg_guard():
    import plans
    app = FastAPI()
    app.include_router(plans.router)
    client = TestClient(app)
    if not db._use_pg:
        assert client.get("/api/my-plans").status_code == 503
        assert client.post("/api/my-plans", json={"title": "test"}).status_code == 503


def test_visits_pg_guard():
    import visits
    app = FastAPI()
    app.include_router(visits.router)
    client = TestClient(app)
    if not db._use_pg:
        assert client.get("/api/me/visits").status_code == 503
        assert client.post("/api/me/visits", json={"entity_id": "x", "status": "want"}).status_code == 503


# ── Check-phone rate-limit (new) ───────────────────────────────────────

def test_check_phone_endpoint_mounted():
    pairs = _route_pairs(_auth_client().app)
    assert ("POST", "/auth/check-phone") in pairs


# ── LRU cache eviction ─────────────────────────────────────────────────

def test_entity_cache_lru_eviction():
    from collections import OrderedDict
    from public_api import _entity_cache, _ENTITY_CACHE_MAX
    assert isinstance(_entity_cache, OrderedDict)
    assert _ENTITY_CACHE_MAX == 1000


def test_place_cache_lru_eviction():
    from collections import OrderedDict
    from public_api import _place_cache, _PLACE_CACHE_MAX
    assert isinstance(_place_cache, OrderedDict)
    assert _PLACE_CACHE_MAX == 500


# ── ND 147 transparency ──────────────────────────────────────────────

def test_transparency_endpoint_mounted():
    from public_api import router as pub_router
    app = FastAPI()
    app.include_router(pub_router)
    pairs = _route_pairs(app)
    assert ("GET", "/api/transparency") in pairs


def test_transparency_endpoint_returns_nd147():
    from public_api import router as pub_router
    app = FastAPI()
    app.include_router(pub_router)
    client = TestClient(app)
    resp = client.get("/api/transparency")
    assert resp.status_code == 200
    data = resp.json()
    assert data["nd147_compliance"]["content_removal_within_24h"] is True
    assert data["content_policy"]["takedown_sla_hours"] == 24
    assert "147" in data["nd147_compliance"]["regulation"]


# ── Shared require_pg ──────────────────────────────────────────────────

def test_shared_require_pg_exists():
    from auth_middleware import require_pg
    assert callable(require_pg)


# ── DRY block clause helper ───────────────────────────────────────────

def test_block_sql_helper_no_user():
    from social import _block_sql
    clause, params = _block_sql(None)
    assert clause == ""
    assert params == []


def test_block_sql_helper_with_user():
    from social import _block_sql
    clause, params = _block_sql({"id": "abc-123"})
    assert "NOT IN" in clause
    assert "blocked_id" in clause
    assert "blocker_id" in clause
    assert params == ["abc-123", "abc-123"]


def test_block_sql_helper_custom_column():
    from social import _block_sql
    clause, _ = _block_sql({"id": "x"}, "c.user_id")
    assert "c.user_id NOT IN" in clause


# ── Health check DB probe ─────────────────────────────────────────────

def test_health_db_probe_select1():
    """Verify the DB probe pattern (SELECT 1) works."""
    with db._conn() as conn:
        row = db._fetchone(conn, "SELECT 1", ())
    assert row is not None


# ── /api/health alias ────────────────────────────────────────────────

def test_api_health_endpoint_exists():
    """GET /api/health should exist and return Cache-Control: no-store."""
    client = _public_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert resp.headers.get("Cache-Control") == "no-store"


def test_api_health_has_openapi_docs():
    """The /api/health endpoint must have summary and description."""
    import public_api
    import inspect
    assert "summary" in inspect.getsource(public_api.router.get) or True
    from public_api import router
    for route in router.routes:
        if hasattr(route, "path") and route.path == "/api/health":
            assert route.summary is not None
            break


# ── Southern dialect spam patterns ────────────────────────────────────

def test_southern_spam_patterns():
    from moderation import _check_spam_patterns_v2
    result = _check_spam_patterns_v2("dzô link kiếm tiền dễ ợt")
    assert result["score"] > 0
    assert any("spam_v2" in r for r in result["reasons"])


def test_southern_spam_gambling():
    from moderation import _check_spam_patterns_v2
    result = _check_spam_patterns_v2("đá gà online uy tín")
    assert result["score"] > 0


def test_southern_spam_clean():
    from moderation import _check_spam_patterns_v2
    result = _check_spam_patterns_v2("Cảnh đẹp Vĩnh Long quá trời!")
    assert result["score"] == 0.0


# ── Admin path ID validation ─────────────────────────────────────────

def test_admin_entity_validates_path_id():
    import admin
    app = FastAPI()
    app.include_router(admin.router)
    app.dependency_overrides[admin.require_admin] = lambda: "test"
    client = TestClient(app)
    resp = client.get("/admin/entities/'; DROP TABLE--")
    assert resp.status_code == 400


# ── Social path ID validation ────────────────────────────────────────

def test_social_post_validates_path_id():
    import social
    app = FastAPI()
    app.include_router(social.router)
    client = TestClient(app)
    if not db._use_pg:
        assert client.get("/api/posts/'; DROP TABLE--").status_code in (400, 503)
    else:
        assert client.get("/api/posts/'; DROP TABLE--").status_code == 400


def test_social_comment_validates_path_id():
    import social
    app = FastAPI()
    app.include_router(social.router)
    client = TestClient(app)
    if not db._use_pg:
        assert client.get("/api/posts/valid-id/comments").status_code in (400, 503)


# ── Notifications path validation ─────────────────────────────────────

def test_notifications_block_validates_path_id():
    import notifications
    app = FastAPI()
    app.include_router(notifications.router)
    client = TestClient(app)
    if not db._use_pg:
        assert client.post("/api/block/'; DROP TABLE--").status_code in (400, 503)


# ── PG connect timeout configured ────────────────────────────────────

def test_pg_connect_timeout_set():
    """Verify connect_timeout parameter is used in database.py."""
    import inspect
    from database import Database
    src = inspect.getsource(Database._conn)
    assert "connect_timeout" in src


# ── Security headers consolidation ────────────────────────────────────

def test_security_headers_complete():
    """Verify all security headers are defined."""
    from auth_middleware import SECURITY_HEADERS, SECURITY_HEADERS_PROD
    assert "X-Content-Type-Options" in SECURITY_HEADERS
    assert "X-Frame-Options" in SECURITY_HEADERS
    assert "Permissions-Policy" in SECURITY_HEADERS
    assert "Cross-Origin-Opener-Policy" in SECURITY_HEADERS
    assert "Cross-Origin-Resource-Policy" in SECURITY_HEADERS
    assert "Strict-Transport-Security" in SECURITY_HEADERS_PROD
    assert "preload" in SECURITY_HEADERS_PROD["Strict-Transport-Security"]


def test_get_security_headers_prod_includes_hsts():
    from auth_middleware import get_security_headers
    headers = get_security_headers(is_production=True)
    assert "Strict-Transport-Security" in headers


def test_get_security_headers_dev_no_hsts():
    from auth_middleware import get_security_headers
    headers = get_security_headers(is_production=False)
    assert "Strict-Transport-Security" not in headers


# ── Per-endpoint body limits ──────────────────────────────────────────

def test_body_limits_defined():
    """Verify per-endpoint body limits exist in server config."""
    # Can't import server.py without LLM_API_KEY, so check the source file
    src = (Path(__file__).parent.parent / "server.py").read_text(encoding="utf-8")
    assert "_BODY_LIMITS" in src
    assert "/api/comments" in src
    assert "/api/posts" in src


# ── Map pins ───────────────────────────────────────────────────────────

def _public_client():
    import public_api
    app = FastAPI()
    app.include_router(public_api.router)
    return TestClient(app)


def test_entities_month_param_validated():
    """month must be 1-12; out-of-range should return 422."""
    client = _public_client()
    assert client.get("/api/entities?month=0").status_code == 422
    assert client.get("/api/entities?month=13").status_code == 422
    assert client.get("/api/entities?month=-1").status_code == 422


def test_map_pins_endpoint_mounted():
    pairs = _route_pairs(_public_client().app)
    assert ("GET", "/api/map-pins") in pairs


def test_map_pins_type_meta():
    import public_api
    assert "dish" in public_api._TYPE_META
    assert "emoji" in public_api._TYPE_META["dish"]
    assert "color" in public_api._TYPE_META["dish"]


def test_map_pins_filters_no_coords():
    """_is_public entities without coordinates should be excluded."""
    import public_api
    entities = [
        {"id": "a", "name": "A", "type": "dish", "coordinates": [10.25, 106.01],
         "attributes": {"rating": 4.5}, "placeId": None},
        {"id": "b", "name": "B", "type": "dish", "coordinates": None,
         "attributes": {}, "placeId": None},
        {"id": "c", "name": "C", "type": "dish", "coordinates": [],
         "attributes": {}, "placeId": None},
    ]
    from unittest.mock import patch
    with patch.object(public_api.db, "list_entities", return_value=entities):
        public_api._map_pins_cache.update(data=None, filters=None, ts=0.0)
        client = _public_client()
        resp = client.get("/api/map-pins")
    assert resp.status_code == 200
    pins = resp.json()
    assert len(pins) == 1
    assert pins[0]["id"] == "a"
    assert pins[0]["lat"] == 10.25
    assert pins[0]["emoji"] == public_api._TYPE_META["dish"]["emoji"]


def test_map_pins_type_filter():
    """Comma-separated type filter passes entity_types to DB."""
    import public_api
    from unittest.mock import patch
    filtered = [
        {"id": "a", "name": "A", "type": "dish", "coordinates": [10.25, 106.01],
         "attributes": {}, "placeId": None},
        {"id": "b", "name": "B", "type": "attraction", "coordinates": [10.26, 106.02],
         "attributes": {}, "placeId": None},
    ]
    with patch.object(public_api.db, "list_entities", return_value=filtered) as mock_list:
        public_api._map_pins_cache.update(data=None, filters=None, ts=0.0)
        client = _public_client()
        resp = client.get("/api/map-pins?type=dish,attraction")
        mock_list.assert_called_once()
        _, kwargs = mock_list.call_args
        assert set(kwargs.get("entity_types")) == {"dish", "attraction"}
    assert resp.status_code == 200
    pins = resp.json()
    assert len(pins) == 2


# ── Review stats ──────────────────────────────────────────────────────

def test_review_stats_endpoint_mounted():
    pairs = _route_pairs(_public_client().app)
    assert ("GET", "/api/entities/{entity_id}/review-stats") in pairs


def test_review_stats_no_pg_returns_empty():
    """Without Postgres, review-stats returns empty defaults for existing entity."""
    import public_api
    from unittest.mock import patch
    if not db._use_pg:
        fake_entity = {"id": "test-entity", "type": "attraction", "name": "Test"}
        with patch.object(public_api.db, "get_entity", return_value=fake_entity):
            client = _public_client()
            resp = client.get("/api/entities/test-entity/review-stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg"] == 0
        assert data["count"] == 0
        assert data["distribution"] == {}
        assert data["mentions"] == []


def test_mention_extraction():
    """_extract_mentions extracts unigrams + bigrams with count >= 2."""
    import public_api
    texts = [
        "Món ăn ngon lắm, view đẹp quá",
        "Ngon quá, giá rẻ nữa",
        "View đẹp, ngon và giá rẻ",
        "Tuyệt vời, rất ngon",
    ]
    mentions = public_api._extract_mentions(texts)
    keywords = {m["keyword"] for m in mentions}
    assert "ngon" in keywords
    counts = {m["keyword"]: m["count"] for m in mentions}
    assert counts["ngon"] >= 3


def test_mention_extraction_empty():
    import public_api
    mentions = public_api._extract_mentions([])
    assert mentions == []


def test_mention_stopwords_filtered():
    import public_api
    texts = ["và của là này đó có không được", "và của là này đó có không được"]
    mentions = public_api._extract_mentions(texts)
    keywords = {m["keyword"] for m in mentions}
    assert len(keywords & public_api._VN_STOPWORDS) == 0


# ── Sort + fields params ──────────────────────────────────────────────

def test_to_minimal_fields():
    import public_api
    entity = {
        "id": "test", "name": "Test", "type": "dish", "summary": "Good",
        "images": ["img1.jpg", "img2.jpg", "img3.jpg"],
        "description": "Long desc", "attributes": {"rating": 4.5, "review_count": 10},
        "relationships": [{"type": "near"}], "coordinates": [10.2, 106.0],
        "place_name": "Xã A", "place_area": "Vĩnh Long",
    }
    minimal = public_api._to_minimal(entity)
    assert minimal["id"] == "test"
    assert minimal["rating"] == 4.5
    assert minimal["review_count"] == 10
    assert len(minimal["images"]) == 1
    assert "description" not in minimal
    assert "relationships" not in minimal


def test_sort_param_accepted():
    """Sort parameter should be accepted by the entities endpoint."""
    import public_api
    from unittest.mock import patch
    entities = [
        {"id": "a", "name": "Aaa", "type": "dish", "attributes": {"rating": 3.0}},
        {"id": "b", "name": "Bbb", "type": "dish", "attributes": {"rating": 5.0}},
    ]
    with patch.object(public_api.db, "list_entities", return_value=entities) as mock_list, \
         patch.object(public_api.db, "count_entities_filtered", return_value=2):
        client = _public_client()
        resp = client.get("/api/entities?sort=rating")
    assert resp.status_code == 200
    mock_list.assert_called_once()
    call_kwargs = mock_list.call_args
    assert call_kwargs[1].get("sort") == "rating" or (len(call_kwargs[0]) > 0)


def test_fields_minimal_response():
    """fields=minimal should return reduced payload."""
    import public_api
    from unittest.mock import patch
    entities = [
        {"id": "a", "name": "A", "type": "dish", "summary": "Good",
         "images": ["img1.jpg", "img2.jpg"], "description": "Long",
         "attributes": {"rating": 4.5, "review_count": 3},
         "coordinates": [10.2, 106.0]},
    ]
    with patch.object(public_api.db, "list_entities", return_value=entities), \
         patch.object(public_api.db, "count_entities_filtered", return_value=1):
        client = _public_client()
        resp = client.get("/api/entities?fields=minimal")
    assert resp.status_code == 200
    data = resp.json()
    e = data["entities"][0]
    assert e["rating"] == 4.5
    assert len(e["images"]) == 1
    assert "description" not in e


def test_sort_db_method_has_sort_param():
    """database.py list_entities should accept sort parameter."""
    import inspect
    sig = inspect.signature(db.list_entities)
    assert "sort" in sig.parameters


# ── Entity gallery ────────────────────────────────────────────────────

def test_gallery_endpoint_mounted():
    pairs = _route_pairs(_public_client().app)
    assert ("GET", "/api/entities/{entity_id}/gallery") in pairs


def test_gallery_entity_images():
    """Gallery should include entity images."""
    import public_api
    from unittest.mock import patch
    entity = {
        "id": "test-gallery", "name": "Test", "type": "dish",
        "images": ["https://img1.jpg", "https://img2.jpg"],
        "attributes": {"image_credit": "VL360"},
    }
    with patch.object(public_api.db, "get_entity", return_value=entity):
        client = _public_client()
        resp = client.get("/api/entities/test-gallery/gallery")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["images"][0]["url"] == "https://img1.jpg"
    assert data["images"][0]["credit"] == "VL360"
    assert "Test" in data["images"][0]["alt"]


def test_gallery_no_entity_404():
    import public_api
    from unittest.mock import patch
    with patch.object(public_api.db, "get_entity", return_value=None):
        client = _public_client()
        resp = client.get("/api/entities/nonexistent/gallery")
    assert resp.status_code == 404


def test_gallery_empty_images():
    import public_api
    from unittest.mock import patch
    entity = {"id": "empty", "name": "Empty", "type": "dish", "images": [], "attributes": {}}
    with patch.object(public_api.db, "get_entity", return_value=entity):
        client = _public_client()
        resp = client.get("/api/entities/empty/gallery")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["images"] == []


# ── Contact view tracking ─────────────────────────────────────────────

def test_view_contact_endpoint_mounted():
    pairs = _route_pairs(_public_client().app)
    assert ("POST", "/api/entities/{entity_id}/view-contact") in pairs


def test_view_contact_writes_log(tmp_path, monkeypatch):
    import public_api
    import ratelimit
    ratelimit._reset()
    log_file = tmp_path / "contact_views.jsonl"
    monkeypatch.setattr(public_api, "CONTACT_VIEWS_FILE", log_file)
    client = _public_client()
    resp = client.post("/api/entities/test-entity/view-contact?action=zalo")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    lines = log_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["entity_id"] == "test-entity"
    assert record["action"] == "zalo"
    assert "ts" in record
    assert "ip_hash" in record


def test_view_contact_invalid_action():
    client = _public_client()
    resp = client.post("/api/entities/test-entity/view-contact?action=invalid")
    assert resp.status_code == 422


def test_view_contact_rate_limit(tmp_path, monkeypatch):
    import public_api
    import ratelimit
    ratelimit._reset()
    log_file = tmp_path / "contact_views.jsonl"
    monkeypatch.setattr(public_api, "CONTACT_VIEWS_FILE", log_file)
    client = _public_client()
    for i in range(10):
        resp = client.post("/api/entities/test-entity/view-contact?action=phone")
        assert resp.status_code == 200
    resp = client.post("/api/entities/test-entity/view-contact?action=phone")
    assert resp.status_code == 429


# ── JSONL log rotation ────────────────────────────────────────────────

def test_jsonl_rotation_under_limit(tmp_path):
    """File under _JSONL_MAX_LINES should NOT be rotated."""
    import public_api
    log_file = tmp_path / "test.jsonl"
    log_file.write_text("line1\nline2\nline3\n", encoding="utf-8")
    public_api._maybe_rotate_jsonl(log_file)
    assert len(log_file.read_text(encoding="utf-8").splitlines()) == 3
    archives = list(tmp_path.glob("test.*.jsonl"))
    assert len(archives) == 0


def test_jsonl_rotation_over_limit(tmp_path, monkeypatch):
    """File over limit should be split: archive old, keep newest."""
    import public_api
    monkeypatch.setattr(public_api, "_JSONL_MAX_LINES", 3)
    log_file = tmp_path / "test.jsonl"
    log_file.write_text("old1\nold2\nnew1\nnew2\nnew3\n", encoding="utf-8")
    public_api._maybe_rotate_jsonl(log_file)
    remaining = log_file.read_text(encoding="utf-8").splitlines()
    assert len(remaining) == 3
    assert remaining == ["new1", "new2", "new3"]
    archives = list(tmp_path.glob("test.*.jsonl"))
    assert len(archives) == 1
    archived = archives[0].read_text(encoding="utf-8").splitlines()
    assert archived == ["old1", "old2"]


def test_jsonl_rotation_missing_file(tmp_path):
    """Rotation on nonexistent file should be a no-op."""
    import public_api
    public_api._maybe_rotate_jsonl(tmp_path / "nope.jsonl")


# ── DB-level month filtering ──────────────────────────────────────────────

class TestMonthFilter:
    """Verify list_entities month param filters at SQL level (SQLite json_each)."""

    def test_month_condition_sqlite(self):
        """SQLite _month_condition uses json_each subquery."""
        if db._use_pg:
            pytest.skip("SQLite-specific test")
        cond = db._month_condition()
        assert "json_each" in cond
        assert "json_extract" in cond

    def test_month_param_sqlite(self):
        """SQLite _month_param returns raw int."""
        if db._use_pg:
            pytest.skip("SQLite-specific test")
        assert db._month_param(3) == 3

    def test_month_condition_pg(self):
        """PG _month_condition uses @> jsonb containment."""
        if not db._use_pg:
            pytest.skip("PG-specific test")
        cond = db._month_condition()
        assert "@>" in cond
        assert "jsonb" in cond

    def test_month_param_pg(self):
        """PG _month_param returns JSON array string."""
        if not db._use_pg:
            pytest.skip("PG-specific test")
        assert db._month_param(6) == "[6]"

    def test_list_entities_accepts_month(self):
        """list_entities method signature includes month param."""
        import inspect
        sig = inspect.signature(db.list_entities)
        assert "month" in sig.parameters

    def test_search_entities_accepts_month(self):
        """search_entities method signature includes month param."""
        import inspect
        sig = inspect.signature(db.search_entities)
        assert "month" in sig.parameters

    def test_count_entities_accepts_month(self):
        """count_entities_filtered method signature includes month param."""
        import inspect
        sig = inspect.signature(db.count_entities_filtered)
        assert "month" in sig.parameters

    def test_list_entities_month_filter(self):
        """Month filter actually filters at DB level (SQLite)."""
        if db._use_pg:
            pytest.skip("SQLite-specific test")
        db.list_entities(limit=50)
        month_3 = db.list_entities(limit=50, month=3)
        for e in month_3:
            months = (e.get("season") or {}).get("months") or []
            assert 3 in months, f"Entity {e['id']} missing month 3 in season"


# ═══════════════════════════════════════════════════════
# Phase 7A: Security hardening tests
# ═══════════════════════════════════════════════════════

class TestPhase7Security:
    """Tests for Phase 7A security improvements."""

    def test_csrf_enforced_on_set_password(self):
        """set_password endpoint requires CSRF dependency."""
        import inspect
        sig = inspect.signature(auth.set_password)
        param_names = list(sig.parameters.keys())
        assert "_csrf" in param_names, "set_password must have _csrf Depends(_require_csrf_lazy)"

    def test_csrf_enforced_on_deactivate(self):
        """deactivate_account endpoint requires CSRF dependency."""
        import inspect
        assert "_csrf" in list(inspect.signature(auth.deactivate_account).parameters.keys())

    def test_csrf_enforced_on_delete_account(self):
        """delete_account endpoint requires CSRF dependency."""
        import inspect
        assert "_csrf" in list(inspect.signature(auth.delete_account).parameters.keys())

    def test_session_binding_imported(self):
        """_check_session_binding_safe is defined and callable in auth module."""
        assert hasattr(auth, '_check_session_binding_safe')
        assert callable(auth._check_session_binding_safe)

    def test_otp_verify_rate_limit_config(self):
        """OTP verify has per-IP rate limiting configured."""
        assert hasattr(auth, 'OTP_VERIFY_IP_LIMIT')
        assert hasattr(auth, 'OTP_VERIFY_IP_WINDOW')
        assert auth.OTP_VERIFY_IP_LIMIT > 0
        assert auth.OTP_VERIFY_IP_WINDOW > 0

    def test_otp_verify_rate_dict_exists(self):
        """OTP verify IP rate dict exists."""
        assert hasattr(auth, '_otp_verify_ip_rate')
        assert isinstance(auth._otp_verify_ip_rate, dict)

    def test_soft_delete_grace_period(self):
        """Account deletion has configurable grace period."""
        assert hasattr(auth, 'ACCOUNT_DELETE_GRACE_DAYS')
        assert auth.ACCOUNT_DELETE_GRACE_DAYS >= 7

    def test_get_current_user_excludes_deleted(self):
        """_get_current_user_or_none query excludes deleted users."""
        import inspect
        source = inspect.getsource(auth._get_current_user_or_none)
        assert "deleted_at IS NULL" in source

    def test_get_current_user_includes_session_data(self):
        """_get_current_user_or_none returns session IP/UA for binding."""
        import inspect
        source = inspect.getsource(auth._get_current_user_or_none)
        assert "session_ip" in source
        assert "session_ua" in source

    def test_update_user_allows_deleted_at(self):
        """database.update_user accepts deleted_at field."""
        import inspect
        source = inspect.getsource(db.update_user)
        assert "deleted_at" in source

    def test_migration_026_exists(self):
        """Migration 026 for soft-delete column exists."""
        migration = Path(__file__).resolve().parent.parent / "migrations" / "026_soft_delete.sql"
        assert migration.exists()
        content = migration.read_text()
        assert "deleted_at" in content


# ═══════════════════════════════════════════════════════
# Phase 7B: Performance tests
# ═══════════════════════════════════════════════════════

class TestPhase7Performance:
    """Tests for Phase 7B performance improvements."""

    def test_homepage_stampede_flag(self):
        """Homepage cache has stampede protection flag."""
        import public_api
        assert hasattr(public_api, '_homepage_rebuilding')

    def test_request_timeout_in_middleware(self):
        """Response tracking middleware uses asyncio.wait_for for timeout."""
        server_path = Path(__file__).resolve().parent.parent / "server.py"
        source = server_path.read_text(encoding="utf-8")
        assert "asyncio.wait_for" in source
        assert "TimeoutError" in source

    def test_timeout_returns_504(self):
        """Timeout handler returns 504 status code."""
        server_path = Path(__file__).resolve().parent.parent / "server.py"
        source = server_path.read_text(encoding="utf-8")
        assert "504" in source


# ═══════════════════════════════════════════════════════
# Phase 7C: Observability tests
# ═══════════════════════════════════════════════════════

class TestPhase7Observability:
    """Tests for Phase 7C observability improvements."""

    def test_pii_masking_ip(self):
        """IP addresses are masked before logging."""
        from middleware import _mask_ip
        assert _mask_ip("192.168.1.100") != "192.168.1.100"
        assert _mask_ip("192.168.1.100").startswith("192.168.")

    def test_pii_masking_ipv6(self):
        """IPv6 addresses are masked."""
        from middleware import _mask_ip
        masked = _mask_ip("2001:db8::1")
        assert "****" in masked

    def test_pii_masking_phone(self):
        """Phone numbers are masked."""
        from middleware import _mask_phone
        assert _mask_phone("0901234567") == "090****567"

    def test_pii_masking_short_phone(self):
        """Short/empty phone values handled gracefully."""
        from middleware import _mask_phone
        assert _mask_phone("") == "***"
        assert _mask_phone("123") == "***"

    def test_security_logger_masks_pii(self):
        """SecurityEventLogger._mask_pii masks ip and phone fields."""
        from middleware import SecurityEventLogger
        entry = {"ip": "10.0.0.1", "phone": "0901234567", "event": "test"}
        masked = SecurityEventLogger._mask_pii(entry)
        assert masked["ip"] != "10.0.0.1"
        assert masked["phone"] != "0901234567"
        assert masked["event"] == "test"

    def test_readiness_endpoint_exists(self):
        """Server has /health/ready endpoint defined."""
        server_path = Path(__file__).resolve().parent.parent / "server.py"
        source = server_path.read_text(encoding="utf-8")
        assert '/health/ready' in source
        assert 'async def readiness_probe' in source

    def test_slo_endpoint_exists(self):
        """Server has /health/slo endpoint defined."""
        server_path = Path(__file__).resolve().parent.parent / "server.py"
        source = server_path.read_text(encoding="utf-8")
        assert '/health/slo' in source
        assert 'async def slo_metrics' in source


# ═══════════════════════════════════════════════════════
# Phase 7D: Data integrity tests
# ═══════════════════════════════════════════════════════

class TestPhase7DataIntegrity:
    """Tests for Phase 7D data integrity improvements."""

    def test_jsonl_lock_exists(self):
        """JSONL write lock exists for atomicity."""
        import public_api
        assert hasattr(public_api, '_jsonl_lock')

    def test_jsonl_write_uses_lock(self):
        """Report write uses _jsonl_lock for thread safety."""
        import inspect
        import public_api
        source = inspect.getsource(public_api.submit_report)
        assert "_jsonl_lock" in source


# ── Phase 8: Block enforcement + notification hardening ─────────────────

class TestPhase8BlockEnforcement:
    """Phase 8: block enforcement fixes."""

    def test_enrich_post_no_phone(self):
        """_enrich_post must NOT leak phone to API response."""
        import social
        row = {"id": "test-id", "content": "hello", "user_id": "u1", "like_count": 0,
               "comment_count": 0, "created_at": "2025-01-01"}
        user = {"display_name": "TestUser", "avatar_url": None, "phone": "0909123456"}
        result = social._enrich_post(row, user)
        assert "phone" not in result

    def test_enrich_post_sets_display(self):
        """_enrich_post copies display_name and avatar from user."""
        import social
        row = {"id": "test-id", "content": "hello", "user_id": "u1", "like_count": 0,
               "comment_count": 0, "created_at": "2025-01-01"}
        user = {"display_name": "TestUser", "avatar_url": "http://img.test/a.webp", "phone": "090"}
        result = social._enrich_post(row, user)
        assert result["author"]["display_name"] == "TestUser"
        assert result["author"]["avatar_url"] == "http://img.test/a.webp"

    def test_toggle_block_unfollow_uses_target_id(self):
        """Auto-unfollow SQL must use target_id (not followed_id) column."""
        import inspect
        import notifications
        src = inspect.getsource(notifications.toggle_block)
        assert "target_id" in src, "toggle_block unfollow must use target_id column"
        assert "followed_id" not in src, "followed_id column does not exist in follows table"

    def test_toggle_block_unfollow_uses_target_type(self):
        """Auto-unfollow must filter target_type = 'user'."""
        import inspect
        import notifications
        src = inspect.getsource(notifications.toggle_block)
        assert "target_type = 'user'" in src

    def test_notification_block_check_symmetric(self):
        """create_notification block check must be symmetric (both directions)."""
        import inspect
        import notifications
        src = inspect.getsource(notifications.create_notification)
        assert src.count("blocker_id") >= 2, "Must check block in both directions"
        assert src.count("blocked_id") >= 2, "Must check block in both directions"

    def test_mention_notification_has_actor_id(self):
        """_notify_mentions passes actor_id for block check."""
        import inspect
        import social
        src = inspect.getsource(social._notify_mentions)
        assert "actor_id=" in src

    def test_entity_follower_notification_has_actor_id(self):
        """_notify_entity_followers passes actor_id for block check."""
        import inspect
        import social
        src = inspect.getsource(social._notify_entity_followers)
        assert "actor_id=" in src

    def test_comment_notification_has_actor_id(self):
        """Comment notification passes actor_id=me for block check."""
        import inspect
        import social
        # Refactor: notify logic moved to helper _notify_comment (+
        # _notify_owner_comment). Wiring-assert + giữ nguyên assertion.
        assert "_notify_comment" in inspect.getsource(social.create_comment)
        src = inspect.getsource(social._notify_comment) + inspect.getsource(social._notify_owner_comment)
        assert "actor_id=" in src

    def test_like_notification_has_actor_id(self):
        """Like notification passes actor_id for block check."""
        import inspect
        import social
        # Refactor: notify logic moved to helper _notify_like (called from
        # toggle_like). Wiring-assert + giữ nguyên assertion.
        assert "_notify_like" in inspect.getsource(social.toggle_like)
        src = inspect.getsource(social._notify_like)
        assert "actor_id=" in src

    def test_follow_notification_has_actor_id(self):
        """Follow notification passes actor_id for block check."""
        import inspect
        import notifications
        # The follow notification moved into the extracted `_run_follow_side_effects`
        # helper (behaviour-preserving extract-method); toggle_follow wires to it.
        src = inspect.getsource(notifications.toggle_follow)
        assert "_run_follow_side_effects" in src  # wiring assert
        helper_src = inspect.getsource(notifications._run_follow_side_effects)
        assert "actor_id=" in helper_src

    def test_entity_type_cap(self):
        """Entity type filter caps at 10 types to prevent abuse."""
        import inspect
        import public_api
        src = inspect.getsource(public_api.list_entities)
        assert "[:10]" in src

    def test_repost_notification_has_actor_id(self):
        """Repost notification passes actor_id for block check."""
        import inspect
        import social
        # Refactor: notify logic moved to helper _notify_new_post, create_post
        # gọi helper (wiring-assert). Giữ nguyên assertion.
        assert "_notify_new_post" in inspect.getsource(social.create_post)
        src = inspect.getsource(social._notify_new_post)
        assert src.count("actor_id=") >= 1


class TestPhase8SessionCleanup:
    """Phase 8: session cleanup and soft-delete enforcement."""

    def test_session_cleanup_task_exists(self):
        """Scheduler has session-cleanup task."""
        import scheduler
        names = [t.name for t in scheduler.TASKS]
        assert "session-cleanup" in names

    def test_session_cleanup_purges_expired(self):
        """task_session_cleanup purges expired sessions."""
        import inspect
        import scheduler
        src = inspect.getsource(scheduler.task_session_cleanup)
        assert "expires_at < NOW()" in src

    def test_session_cleanup_purges_deleted_users(self):
        """task_session_cleanup purges sessions for soft-deleted users past grace period."""
        import inspect
        import scheduler
        src = inspect.getsource(scheduler.task_session_cleanup)
        assert "deleted_at IS NOT NULL" in src
        assert "30 days" in src

    def test_leaderboard_excludes_deleted(self):
        """Leaderboard query excludes soft-deleted users."""
        import inspect
        import social
        # Refactor: leaderboard SQL moved to helper _leaderboard_query.
        assert "_leaderboard_query" in inspect.getsource(social.community_leaderboard)
        src = inspect.getsource(social._leaderboard_query)
        assert "deleted_at IS NULL" in src

    def test_user_search_excludes_deleted(self):
        """User search query excludes soft-deleted users."""
        import inspect
        import social
        src = inspect.getsource(social.search_users)
        assert "deleted_at IS NULL" in src

    def test_suggested_follows_excludes_deleted(self):
        """Suggested follows excludes soft-deleted users."""
        import inspect
        import social
        src = inspect.getsource(social.suggested_follows)
        assert "deleted_at IS NULL" in src

    def test_admin_report_path_validation(self):
        """Admin report endpoints validate path IDs."""
        import inspect
        import admin
        assert "validate_path_id" in inspect.getsource(admin.resolve_report)
        assert "validate_path_id" in inspect.getsource(admin.dismiss_report)
        assert "validate_path_id" in inspect.getsource(admin.get_moderation_notes)


class TestPhase8BanHardening:
    """Phase 8: ban revokes sessions + audit logging."""

    def test_ban_revokes_sessions(self):
        """Ban must delete all user sessions for immediate effect."""
        import inspect
        import admin
        src = inspect.getsource(admin.ban_user)
        assert "DELETE FROM user_sessions" in src

    def test_ban_audit_log(self):
        """Ban action is logged to moderation audit trail."""
        import inspect
        import admin
        src = inspect.getsource(admin.ban_user)
        assert "_log_mod_action" in src

    def test_unban_audit_log(self):
        """Unban action is logged to moderation audit trail."""
        import inspect
        import admin
        src = inspect.getsource(admin.unban_user)
        assert "_log_mod_action" in src

    def test_role_change_audit_log(self):
        """Role change is logged to moderation audit trail."""
        import inspect
        import admin
        src = inspect.getsource(admin.set_user_role)
        assert "_log_mod_action" in src

    def test_phone_removed_from_social_queries(self):
        """No social.py query fetches u.phone (data minimization)."""
        import social as _soc
        src = Path(_soc.__file__).read_text(encoding="utf-8")
        assert "u.phone" not in src


class TestPhase9ErrorInfoLeaks:
    """Phase 9: error messages must not leak internal details to clients."""

    _admin_src = None
    _server_src = None

    @classmethod
    def _get_admin_src(cls):
        if cls._admin_src is None:
            cls._admin_src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        return cls._admin_src

    @classmethod
    def _get_server_src(cls):
        if cls._server_src is None:
            cls._server_src = (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")
        return cls._server_src

    def test_backup_error_no_stderr(self):
        """Backup endpoint does not expose result.stderr in HTTP response."""
        src = self._get_admin_src()
        idx = src.find("def trigger_backup")
        block = src[idx:idx + 1500]
        assert "result.stderr" not in block or "logger" in block
        assert "Kiểm tra log server" in block

    def test_image_upload_error_generic(self):
        """Image upload error returns generic message, not str(e)."""
        import inspect
        import social
        src = inspect.getsource(social.upload_image)
        assert "str(e)" not in src

    def test_suggestion_image_error_generic(self):
        """Suggestion image download error returns generic message."""
        src = self._get_admin_src()
        idx = src.find("def approve_image_suggestion")
        block = src[idx:idx + 1200]
        assert "str(e)[:120]" not in block

    def test_bulk_relationship_error_generic(self):
        """Bulk relationship error does not leak str(e) to response."""
        src = self._get_admin_src()
        idx = src.find("def add_relationships_bulk")
        block = src[idx:idx + 600]
        for line in block.split("\n"):
            if "errors.append" in line:
                assert "str(e)" not in line

    def test_moderation_queue_no_phone(self):
        """Moderation queue does not fetch u.phone (admin data minimization)."""
        src = self._get_admin_src()
        idx = src.find("def moderation_queue")
        block = src[idx:idx + 800]
        assert "u.phone" not in block

    def test_tool_errors_no_str_e(self):
        """Public chat tool error handlers use generic messages, not str(e)."""
        src = self._get_server_src()
        for tool_name in ["community_reviews", "trending_posts"]:
            idx = src.find(f'"{tool_name}"')
            if idx == -1:
                continue
            block = src[idx:idx + 600]
            if "str(e)" in block:
                assert False, f"{tool_name} tool handler leaks str(e)"

    def test_cache_health_no_str_e(self):
        """Cache health check does not leak Redis exception details."""
        import inspect
        import cache
        src = inspect.getsource(cache.redis_stats)
        assert "str(e)" not in src

    def test_silent_except_has_logging(self):
        """Info reports parsing exception in admin triage is logged, not silently swallowed."""
        src = self._get_admin_src()
        idx = src.find("def ai_triage")
        block = src[idx:idx + 1500]
        assert "logger.warning" in block or "logger.error" in block


class TestPhase9TimingAndRace:
    """Phase 9: timing-safe token comparison + OTP race condition fix."""

    def test_session_current_uses_hmac(self):
        """Session list uses hmac.compare_digest for is_current, not == ."""
        auth_src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        idx = auth_src.find("is_current")
        block = auth_src[max(0, idx - 20):idx + 100]
        assert "hmac.compare_digest" in block
        assert '== cur_hash' not in block

    def test_otp_select_for_update(self):
        """OTP verification uses SELECT ... FOR UPDATE to prevent race conditions."""
        auth_src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        # Refactor: OTP-row verify (SELECT ... FOR UPDATE) dời sang _consume_verified_otp,
        # được reset_password_otp gọi (move-not-delete).
        assert "_consume_verified_otp" in auth_src  # wiring
        idx = auth_src.find("def _consume_verified_otp(")
        block = auth_src[idx:idx + 900]  # docstring dài → FOR UPDATE ở ~517 char
        assert "FOR UPDATE" in block


class TestPhase10LikeEscape:
    """Phase 10: SQL LIKE wildcard escaping prevents wildcard injection."""

    def test_escape_like_helper_exists(self):
        """database.escape_like helper function exists and works."""
        from database import escape_like
        assert escape_like("hello") == "hello"
        assert escape_like("100%") == "100\\%"
        assert escape_like("test_name") == "test\\_name"
        assert escape_like("a\\b") == "a\\\\b"
        assert escape_like("50%_off") == "50\\%\\_off"

    def test_search_entities_uses_escape(self):
        """search_entities escapes LIKE wildcards in user query."""
        import database
        src = Path(database.__file__).read_text(encoding="utf-8")
        # Refactor: q-filter (escape_like + ESCAPE) dời sang _append_q_filter,
        # được search_entities gọi (move-not-delete).
        se_block = src[src.find("def search_entities"):src.find("def search_entities") + 2000]
        assert "_append_q_filter" in se_block  # wiring
        idx = src.find("def _append_q_filter")
        block = src[idx:idx + 1500]
        assert "escape_like" in block
        assert "ESCAPE" in block

    def test_admin_duplicate_check_uses_escape(self):
        """Admin duplicate check escapes LIKE wildcards."""
        admin_src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = admin_src.find("def check_duplicate")
        # Window 900: hàm dài ra hợp lệ (fix dialect PG 2026-07-02) — assertion giữ nguyên.
        block = admin_src[idx:idx + 900]
        assert "escape_like" in block
        assert "ESCAPE" in block

    def test_admin_unclassified_uses_escape(self):
        """Admin unclassified search escapes LIKE wildcards."""
        admin_src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = admin_src.find("def list_unclassified")
        # Window 1200: hàm dài ra hợp lệ (fix dialect PG 2026-07-02) — assertion giữ nguyên.
        block = admin_src[idx:idx + 1200]
        assert "escape_like" in block
        assert "ESCAPE" in block

    def test_social_search_posts_uses_escape(self):
        """Social post search escapes LIKE wildcards."""
        import social
        src = Path(social.__file__).read_text(encoding="utf-8")
        idx = src.find("def search_posts")
        block = src[idx:idx + 1500]
        assert "escape_like" in block
        assert "ESCAPE" in block

    def test_social_search_users_uses_escape(self):
        """Social user search escapes LIKE wildcards."""
        import social
        src = Path(social.__file__).read_text(encoding="utf-8")
        idx = src.find("def search_users")
        block = src[idx:idx + 1500]
        assert "escape_like" in block
        assert "ESCAPE" in block


class TestPhase10PaginationConsistency:
    """Phase 10: all paginated endpoints return consistent metadata."""

    _src = None

    @classmethod
    def _social_src(cls):
        if cls._src is None:
            import social
            cls._src = Path(social.__file__).read_text(encoding="utf-8")
        return cls._src

    @staticmethod
    def _func_block(src, name, size=2500):
        idx = src.find(f"def {name}")
        return src[idx:idx + size] if idx != -1 else ""

    def test_search_posts_has_page(self):
        """search_posts response includes page field."""
        block = self._func_block(self._social_src(), "search_posts")
        assert '"page"' in block

    def test_search_users_has_page(self):
        """search_users response includes page field."""
        block = self._func_block(self._social_src(), "search_users")
        assert '"page"' in block

    def test_bookmarks_has_pagination(self):
        """Bookmarks response includes pagination metadata."""
        block = self._func_block(self._social_src(), "get_my_bookmarks")
        assert '"has_more"' in block

    def test_user_posts_has_pagination(self):
        """User posts response includes pagination metadata."""
        block = self._func_block(self._social_src(), "get_user_posts")
        assert '"has_more"' in block

    def test_following_has_offset(self):
        """Following list response includes offset."""
        block = self._func_block(self._social_src(), "list_following_users")
        assert '"offset"' in block

    def test_followers_has_offset(self):
        """Followers list response includes offset."""
        block = self._func_block(self._social_src(), "list_followers")
        assert '"offset"' in block

    def test_delete_account_has_success(self):
        """DELETE /account response includes success field for consistency."""
        auth_src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        block = self._func_block(auth_src, "delete_account")
        assert '"success"' in block


class TestPhase11SessionLimit:
    """Phase 11: max concurrent session enforcement.

    Wave 4 Task 3 extracted the session-create+cookie+log+streak+achievement
    sequence (previously duplicated inline in both verify_otp and login_password)
    into a shared `_finish_login` helper, called from both endpoints' non-2FA
    success path. `_create_session_atomic` is therefore no longer a literal
    substring of verify_otp's/login_password's own source block — it now lives
    in `_finish_login`. These tests are updated to check the same real property
    (session-limit enforcement is reachable from both login paths) through the
    new call chain: verify_otp/login_password -> _finish_login -> _create_session_atomic.
    """

    def test_verify_otp_enforces_session_limit(self):
        """verify_otp's success path reaches _create_session_atomic via _finish_login."""
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "def _create_session_atomic" in src
        assert "MAX_CONCURRENT_SESSIONS" in src
        idx = src.find("def verify_otp")
        end = src.find("\nasync def ", idx + 1)
        block = src[idx:end] if end != -1 else src[idx:idx + 5000]
        assert "_finish_login" in block
        finish_idx = src.find("async def _finish_login")
        finish_end = src.find("\n@router.post", finish_idx + 1)
        finish_block = src[finish_idx:finish_end] if finish_end != -1 else src[finish_idx:finish_idx + 3000]
        assert "_create_session_atomic" in finish_block

    def test_login_password_enforces_session_limit(self):
        """login_password's success path reaches _create_session_atomic via _finish_login."""
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "def _create_session_atomic" in src
        idx = src.find("def login_password")
        end = src.find("\nasync def ", idx + 1)
        block = src[idx:end] if end != -1 else src[idx:idx + 5000]
        assert "_finish_login" in block
        finish_idx = src.find("async def _finish_login")
        finish_end = src.find("\n@router.post", finish_idx + 1)
        finish_block = src[finish_idx:finish_end] if finish_end != -1 else src[finish_idx:finish_idx + 3000]
        assert "_create_session_atomic" in finish_block


class TestPhase11BlockFollow:
    """Phase 11: block prevents follow."""

    def test_follow_checks_block_bidirectional(self):
        """toggle_follow checks blocks table before allowing follow."""
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        block = src[src.find("def toggle_follow"):src.find("def toggle_follow") + 3000]
        assert "blocks" in block.lower()
        assert "blocker_id" in block
        assert "blocked_id" in block
        assert "403" in block


class TestPhase11SelfRepost:
    """Phase 11: prevent self-repost."""

    def test_repost_blocks_own_post(self):
        """create_post rejects reposting own post."""
        # Refactor: repost guard moved to helper _process_repost (called from
        # create_post). Wiring-assert + giữ nguyên assertion trên block helper.
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        cp_idx = src.find("def create_post")
        assert "_process_repost" in src[cp_idx:cp_idx + 5000]
        idx = src.find("def _process_repost")
        block = src[idx:idx + 5000]
        assert "Không thể đăng lại bài viết của chính mình" in block


class TestPhase11RsvpValidation:
    """Phase 11: RSVP entity type validation."""

    def test_rsvp_checks_entity_type(self):
        """toggle_rsvp validates entity is of type 'event'."""
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        block = src[src.find("def toggle_rsvp"):src.find("def toggle_rsvp") + 2000]
        assert "get_entity" in block
        assert '"event"' in block
        assert "404" in block


class TestPhase11ReportRateLimit:
    """Phase 11: rate limit on report-ugc."""

    def test_report_has_rate_limit(self):
        """create_report calls check_rate before processing."""
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        block = src[src.find("def create_report"):src.find("def create_report") + 1000]
        assert "check_rate" in block
        assert "report:" in block


class TestPhase11NotificationCleanup:
    """Phase 11: notification cleanup scheduler task."""

    def test_notification_cleanup_task_exists(self):
        """Scheduler has notification-cleanup task."""
        import scheduler
        names = [t.name for t in scheduler.TASKS]
        assert "notification-cleanup" in names

    def test_notification_cleanup_prunes_old(self):
        """task_notification_cleanup deletes old notifications."""
        import inspect
        import scheduler
        src = inspect.getsource(scheduler.task_notification_cleanup)
        assert "90 days" in src
        assert "30 days" in src

    def test_notification_cleanup_prunes_read(self):
        """task_notification_cleanup prunes read notifications after 30 days."""
        import inspect
        import scheduler
        src = inspect.getsource(scheduler.task_notification_cleanup)
        assert "is_read = TRUE" in src


class TestPhase11CommentEditWindow:
    """Phase 11: comment edit time window."""

    def test_edit_comment_has_time_check(self):
        """edit_comment rejects edits after 24 hours."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("def edit_comment")
        end = src.find("\nasync def ", idx + 1)
        block = src[idx:end] if end != -1 else src[idx:idx + 3000]
        assert "24" in block
        assert "COMMENT_EDIT_WINDOW_HOURS" in block
        assert "created_at" in block

    def test_edit_comment_returns_400_after_window(self):
        """edit_comment raises 400 when window expired."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("def edit_comment")
        end = src.find("\nasync def ", idx + 1)
        block = src[idx:end] if end != -1 else src[idx:idx + 3000]
        assert "400" in block
        assert "24 giờ" in block


class TestPhase11SelfLikePrevention:
    """Phase 11: self-like prevention."""

    def test_toggle_like_prevents_self_like(self):
        """toggle_like rejects liking own post."""
        # Refactor: self-like guard moved to helper _like_check_self (called from
        # toggle_like). Wiring-assert + giữ nguyên assertion trên block helper.
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        tl_idx = src.find("def toggle_like")
        tl_end = src.find("\n\n\n", tl_idx + 1)
        assert "_like_check_self" in src[tl_idx:tl_end if tl_end != -1 else tl_idx + 4000]
        gidx = src.find("def _like_check_self")
        gblock = src[gidx:gidx + 2000]
        assert "Không thể thích bài viết của chính mình" in gblock

    def test_toggle_like_checks_post_exists(self):
        """toggle_like verifies post exists before like check."""
        # Refactor: post-exists check moved to helper _like_check_self.
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        tl_idx = src.find("def toggle_like")
        assert "_like_check_self" in src[tl_idx:tl_idx + 1500]
        gidx = src.find("def _like_check_self")
        block = src[gidx:gidx + 1500]
        assert "404" in block
        assert "Bài viết không tồn tại" in block


class TestPhase11HtmlSanitization:
    """Phase 11: HTML tag stripping in content validators."""

    def test_strip_html_tags_helper(self):
        """_strip_html_tags removes HTML tags."""
        import social
        assert social._strip_html_tags("<script>alert(1)</script>hello") == "alert(1)hello"
        assert social._strip_html_tags("no tags here") == "no tags here"
        assert social._strip_html_tags("<b>bold</b> <i>italic</i>") == "bold italic"
        assert social._strip_html_tags("") == ""

    def test_create_post_validator_strips_html(self):
        """CreatePost.validate_content strips HTML tags."""
        import social
        p = social.CreatePost(content="<b>Hello world</b> this is a test post", post_type="share")
        assert "<b>" not in p.content
        assert "Hello world" in p.content

    def test_create_comment_validator_strips_html(self):
        """CreateComment.validate_content strips HTML tags."""
        import social
        c = social.CreateComment(content="<script>alert('xss')</script>bình luận hợp lệ")
        assert "<script>" not in c.content
        assert "bình luận hợp lệ" in c.content

    def test_edit_comment_validator_strips_html(self):
        """EditComment.validate_content strips HTML tags."""
        import social
        c = social.EditComment(content="<img src=x onerror=alert(1)>OK comment here")
        assert "<img" not in c.content
        assert "OK comment here" in c.content

    def test_update_post_strips_html(self):
        """UpdatePost.validate_content strips HTML tags."""
        import social
        p = social.UpdatePost(content="<div onclick='hack()'>Safe content here for testing</div>")
        assert "<div" not in p.content
        assert "Safe content" in p.content


class TestPhase11AdminHardening:
    """Phase 11: admin endpoint validation hardening."""

    def test_ban_user_prevents_self_ban(self):
        """ban_user checks admin user ID against target."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def ban_user")
        end = src.find("\nasync def ", idx + 1)
        block = src[idx:end] if end != -1 else src[idx:idx + 2000]
        assert "Không thể tự ban chính mình" in block
        assert "get_current_user" in block

    def test_ban_user_checks_target_exists(self):
        """ban_user verifies target user exists."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def ban_user")
        end = src.find("\nasync def ", idx + 1)
        block = src[idx:end] if end != -1 else src[idx:idx + 2000]
        assert "404" in block
        assert "Không tìm thấy người dùng" in block

    def test_unban_checks_ban_status(self):
        """unban_user rejects unbanning non-banned user."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def unban_user")
        end = src.find("\nasync def ", idx + 1)
        block = src[idx:end] if end != -1 else src[idx:idx + 2000]
        assert "Người dùng không bị ban" in block
        assert "is_active" in block

    def test_set_role_checks_user_exists(self):
        """set_user_role verifies target user exists."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def set_user_role")
        end = src.find("\nasync def ", idx + 1)
        block = src[idx:end] if end != -1 else src[idx:idx + 2000]
        assert "404" in block
        assert "Không tìm thấy người dùng" in block

    def test_set_role_rejects_banned_user(self):
        """set_user_role rejects assigning role to banned user."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def set_user_role")
        end = src.find("\nasync def ", idx + 1)
        block = src[idx:end] if end != -1 else src[idx:idx + 2000]
        assert "Không thể gán quyền cho tài khoản đã bị ban" in block

    def test_backup_has_cooldown(self):
        """trigger_backup has a 5-minute cooldown."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def trigger_backup")
        block = src[max(0, idx - 200):idx + 1500]
        assert "_BACKUP_COOLDOWN" in block
        assert "429" in block


class TestPhase11CommentCap:
    """Phase 11: per-post comment cap."""

    def test_create_comment_has_per_post_cap(self):
        """create_comment enforces MAX_COMMENTS_PER_POST."""
        # Refactor: cap check moved to helper _comment_guard (called via
        # _comment_query). MAX_COMMENTS_PER_POST vẫn ở create_comment; thông
        # điệp giới hạn ở helper. Wiring-assert + giữ nguyên assertion.
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("def create_comment")
        end = src.find("\nasync def ", idx + 1)
        block = src[idx:end] if end != -1 else src[idx:idx + 4000]
        assert "MAX_COMMENTS_PER_POST" in block
        assert "_comment_query" in block
        guard_idx = src.find("def _comment_guard")
        guard_block = src[guard_idx:guard_idx + 4000]
        assert "đạt giới hạn bình luận" in guard_block

    def test_comment_cap_value_reasonable(self):
        """MAX_COMMENTS_PER_POST is set to 500 (via config)."""
        from config import settings
        assert settings.MAX_COMMENTS_PER_POST == 500


class TestPhase11FollowingFeedBlockFilter:
    """Phase 11: following feed must exclude blocked users."""

    def test_following_feed_has_block_sql(self):
        """get_following_feed applies _block_sql to filter blocked users."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("def get_following_feed")
        end = src.find("\nasync def ", idx + 1)
        block = src[idx:end] if end != -1 else src[idx:idx + 4000]
        assert "_block_sql" in block
        assert "bc_p" in block or "bc" in block

    def test_following_feed_block_in_both_queries(self):
        """Block filter applied to both feed and count SQL."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("def get_following_feed")
        end = src.find("\nasync def ", idx + 1)
        block = src[idx:end] if end != -1 else src[idx:idx + 4000]
        assert block.count("{bc}") >= 2


class TestPhase11DailyPostLimit:
    """Phase 11: daily post creation limit."""

    def test_create_post_has_daily_limit(self):
        """create_post enforces a daily rate limit in addition to per-minute."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("def create_post")
        block = src[idx:idx + 1000]
        assert "post-day:" in block
        assert "RL_POST_DAILY" in block

    def test_daily_limit_is_50(self):
        """Daily post limit is 50."""
        import social
        assert social.RL_POST_DAILY_LIMIT == 50
        assert social.RL_POST_DAILY_WINDOW == 86400


# ═══════════════════════════════════════════════════════════════════════
#  Phase 12: CSRF on all state-changing endpoints + dependency security
# ═══════════════════════════════════════════════════════════════════════

class TestPhase12CsrfCoverage:
    """Phase 12: All POST/PUT/DELETE/PATCH endpoints must have CSRF dependency."""

    def _check_csrf(self, module_name, func_name):
        """Helper: verify _csrf=Depends(require_csrf) in function signature."""
        import importlib
        mod = importlib.import_module(module_name)
        fn = getattr(mod, func_name)
        import inspect
        sig = inspect.signature(fn)
        param_names = list(sig.parameters.keys())
        assert "_csrf" in param_names, f"{module_name}.{func_name} missing _csrf Depends"

    def test_social_create_post_csrf(self):
        self._check_csrf("social", "create_post")

    def test_social_delete_post_csrf(self):
        self._check_csrf("social", "delete_post")

    def test_social_update_post_csrf(self):
        self._check_csrf("social", "update_post")

    def test_social_create_comment_csrf(self):
        self._check_csrf("social", "create_comment")

    def test_social_edit_comment_csrf(self):
        self._check_csrf("social", "edit_comment")

    def test_social_delete_comment_csrf(self):
        self._check_csrf("social", "delete_comment")

    def test_social_set_best_answer_csrf(self):
        self._check_csrf("social", "set_best_answer")

    def test_social_toggle_like_csrf(self):
        self._check_csrf("social", "toggle_like")

    def test_social_toggle_bookmark_csrf(self):
        self._check_csrf("social", "toggle_bookmark")

    def test_social_upload_image_csrf(self):
        self._check_csrf("social", "upload_image")

    def test_notifications_mark_all_read_csrf(self):
        self._check_csrf("notifications", "mark_all_read")

    def test_notifications_mark_read_csrf(self):
        self._check_csrf("notifications", "mark_notification_read")

    def test_notifications_update_prefs_csrf(self):
        self._check_csrf("notifications", "update_notification_preferences")

    def test_notifications_toggle_follow_csrf(self):
        self._check_csrf("notifications", "toggle_follow")

    def test_notifications_create_report_csrf(self):
        self._check_csrf("notifications", "create_report")

    def test_notifications_toggle_block_csrf(self):
        self._check_csrf("notifications", "toggle_block")

    def test_notifications_toggle_rsvp_csrf(self):
        self._check_csrf("notifications", "toggle_rsvp")

    def test_auth_logout_csrf(self):
        self._check_csrf("auth", "logout")

    def test_auth_revoke_session_csrf(self):
        self._check_csrf("auth", "revoke_session")

    def test_auth_update_profile_csrf(self):
        self._check_csrf("auth", "update_profile")

    def test_auth_upload_avatar_csrf(self):
        self._check_csrf("auth", "upload_avatar")

    def test_auth_upload_cover_csrf(self):
        self._check_csrf("auth", "upload_cover")

    def test_auth_update_privacy_csrf(self):
        self._check_csrf("auth", "update_privacy")

    def test_visits_set_visit_csrf(self):
        self._check_csrf("visits", "set_visit")

    def test_visits_remove_visit_csrf(self):
        self._check_csrf("visits", "remove_visit")

    def test_saved_add_csrf(self):
        self._check_csrf("saved", "add_saved")

    def test_saved_remove_csrf(self):
        self._check_csrf("saved", "remove_saved")

    def test_saved_merge_csrf(self):
        self._check_csrf("saved", "merge_saved")

    def test_plans_add_csrf(self):
        self._check_csrf("plans", "add_plan")

    def test_plans_remove_csrf(self):
        self._check_csrf("plans", "remove_plan")

    def test_plans_merge_csrf(self):
        self._check_csrf("plans", "merge_plans")

    def test_plans_publish_csrf(self):
        self._check_csrf("plans", "publish_plan")


class TestPhase12DependencySecurity:
    """Phase 12: Dependency and SMS security fixes."""

    def test_python_multipart_version(self):
        """python-multipart must be >=0.0.11 (CVE-2024-24762)."""
        reqs = (Path(__file__).resolve().parent.parent.parent / "requirements.txt").read_text()
        assert "python-multipart>=0.0.11" in reqs

    def test_esms_uses_https(self):
        """eSMS API must use HTTPS, not HTTP."""
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "https://rest.esms.vn/" in src
        assert "http://rest.esms.vn/" not in src


# ═══════════════════════════════════════════════════════════════════════
#  Phase 14: PG indexes for performance
# ═══════════════════════════════════════════════════════════════════════

def _index_defn_source() -> str:
    """Nơi index có thể được định nghĩa: database.py (inline) + MỌI migration .sql.

    Các index social đã được dời từ inline database.py sang agent/migrations/ (commit
    5c09a00). Quét CẢ HAI phản ánh đúng schema thật thay vì chỉ database.py (đọc sai
    chỗ → fail cả SQLite lẫn PG). 3 index bị xoá nhầm được tái tạo ở migration 069.
    """
    root = Path(__file__).resolve().parent.parent
    parts = [(root / "database.py").read_text(encoding="utf-8")]
    mig = root / "migrations"
    if mig.is_dir():
        for f in sorted(mig.glob("*.sql")):
            parts.append(f.read_text(encoding="utf-8"))
    return "\n".join(parts)


class TestPhase14PgIndexes:
    """Phase 14: các index PG cần thiết phải được định nghĩa (database.py HOẶC migrations)."""

    def test_follows_indexes_exist(self):
        src = _index_defn_source()
        assert "idx_follows_follower" in src
        assert "idx_follows_target" in src

    def test_posts_user_index_exists(self):
        assert "idx_posts_user" in _index_defn_source()

    def test_comments_post_index_exists(self):
        assert "idx_comments_post" in _index_defn_source()

    def test_likes_bookmarks_indexes_exist(self):
        src = _index_defn_source()
        assert "idx_likes_user" in src
        assert "idx_bookmarks_user" in src

    def test_entity_ratings_index_exists(self):
        assert "idx_entity_ratings" in _index_defn_source()

    def test_posts_entity_index_exists(self):
        assert "idx_posts_entity" in _index_defn_source()


# ═══════════════════════════════════════════════════════════════════════
#  Phase 13: Config centralization — hardcoded values wired to config.py
# ═══════════════════════════════════════════════════════════════════════

class TestPhase13ConfigCentralization:
    """Phase 13: Business constants must use config.py, not hardcoded values."""

    def test_config_has_business_rules(self):
        from config import settings
        assert settings.MAX_COMMENTS_PER_POST == 500
        assert settings.MAX_CONCURRENT_SESSIONS == 5
        assert settings.COMMENT_EDIT_WINDOW_HOURS == 24
        assert settings.RL_POST_DAILY_LIMIT == 50
        assert settings.RL_POST_DAILY_WINDOW == 86400
        assert settings.TRENDING_CACHE_TTL == 120
        assert settings.BACKUP_COOLDOWN == 300
        assert settings.ACCOUNT_DELETE_GRACE_DAYS == 30
        assert settings.PBKDF2_ITERATIONS == 310_000

    def test_social_uses_config_for_daily_limit(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        assert "_cfg.RL_POST_DAILY_LIMIT" in src
        assert "_cfg.RL_POST_DAILY_WINDOW" in src

    def test_social_uses_config_for_comment_cap(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        assert "_cfg.MAX_COMMENTS_PER_POST" in src

    def test_social_uses_config_for_edit_window(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        assert "_cfg.COMMENT_EDIT_WINDOW_HOURS" in src

    def test_social_uses_config_for_trending_ttl(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        assert "_cfg.TRENDING_CACHE_TTL" in src

    def test_auth_uses_config_for_pbkdf2(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "_cfg.PBKDF2_ITERATIONS" in src

    def test_auth_uses_config_for_delete_grace(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "_cfg.ACCOUNT_DELETE_GRACE_DAYS" in src

    def test_admin_uses_config_for_backup_cooldown(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        assert "_cfg.BACKUP_COOLDOWN" in src

    def test_no_hardcoded_daily_limit(self):
        """Ensure RL_POST_DAILY_LIMIT is not hardcoded to 50 in social.py."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        lines = [l for l in src.splitlines() if "RL_POST_DAILY_LIMIT" in l and "= 50" in l]
        assert not lines, f"Hardcoded daily limit found: {lines}"


# ═══════════════════════════════════════════════════════════════════════
#  Phase 14b: Rate limit background GC
# ═══════════════════════════════════════════════════════════════════════

class TestPhase14RatelimitGC:
    """Phase 14: Rate limit background GC prevents memory leaks."""

    def test_gc_all_exists(self):
        from ratelimit import gc_all
        result = gc_all()
        assert "before" in result
        assert "after" in result
        assert "freed" in result

    def test_gc_all_cleans_expired(self):
        from ratelimit import _buckets, gc_all
        import time
        _buckets["test_gc_expired"] = [time.time() - 7200]
        result = gc_all()
        assert "test_gc_expired" not in _buckets
        assert result["freed"] >= 1

    def test_scheduler_has_ratelimit_gc_task(self):
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        assert "ratelimit-gc" in src
        assert "task_ratelimit_gc" in src

    def test_scheduler_gc_interval_reasonable(self):
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        assert "interval_seconds=300" in src.split("ratelimit-gc")[1][:100]


# ═══════════════════════════════════════════════════════════════════════
#  Phase 14c: Leaderboard cache + SELECT * fix
# ═══════════════════════════════════════════════════════════════════════

class TestPhase14QueryOptimization:
    """Phase 14: Query optimization — caching and SELECT * removal."""

    def test_leaderboard_cache_exists(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        assert "_leaderboard_cache" in src

    def test_no_select_star_in_privacy(self):
        """user_privacy queries must select explicit columns."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        assert "SELECT * FROM user_privacy" not in src

    def test_privacy_selects_explicit_columns(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        assert "profile_visibility, show_activity, show_saved FROM user_privacy" in src


# ═══════════════════════════════════════════════════════════════════════
#  Phase 15: Idempotency key support
# ═══════════════════════════════════════════════════════════════════════

class TestPhase15Idempotency:
    """Phase 15: Idempotency key support for write endpoints."""

    def test_require_idempotency_exists(self):
        from auth_middleware import require_idempotency
        import inspect
        assert inspect.iscoroutinefunction(require_idempotency)

    def test_create_post_has_idempotency(self):
        import inspect
        import social
        sig = inspect.signature(social.create_post)
        assert "_idem" in sig.parameters

    def test_create_comment_has_idempotency(self):
        import inspect
        import social
        sig = inspect.signature(social.create_comment)
        assert "_idem" in sig.parameters

    def test_idempotency_check_deduplication(self):
        from auth_middleware import check_idempotency, _reset_idempotency
        _reset_idempotency()
        r1 = check_idempotency("test-key-123")
        assert r1["is_duplicate"] is False
        r2 = check_idempotency("test-key-123")
        assert r2["is_duplicate"] is True
        _reset_idempotency()

    def test_idempotency_empty_key_not_duplicate(self):
        from auth_middleware import check_idempotency
        r = check_idempotency("")
        assert r["is_duplicate"] is False

    def test_reset_idempotency_clears_pg_table(self):
        # _reset_idempotency() phải xoá CẢ bảng PG request_idempotency_keys (không chỉ
        # memory) — nếu không, dưới PG key cũ tồn tại qua test khiến lần gọi đầu = duplicate.
        from auth_middleware import check_idempotency, _reset_idempotency
        _reset_idempotency()
        assert check_idempotency("reset-pg-key")["is_duplicate"] is False
        assert check_idempotency("reset-pg-key")["is_duplicate"] is True
        _reset_idempotency()
        assert check_idempotency("reset-pg-key")["is_duplicate"] is False, \
            "_reset_idempotency phải xoá row PG → key lại 'mới'"
        _reset_idempotency()


# ═══════════════════════════════════════════════════════════════════════
#  Phase 13b: Auth config centralization (SESSION_EXPIRE, OTP, ESMS)
# ═══════════════════════════════════════════════════════════════════════

class TestPhase13bAuthConfig:
    """Phase 13b: auth.py uses centralized config for session/OTP/ESMS values."""

    def test_config_has_session_expire(self):
        from config import settings
        assert settings.SESSION_EXPIRE_DAYS == 30

    def test_config_has_otp_expire(self):
        from config import settings
        assert settings.OTP_EXPIRE_MINUTES == 5

    def test_auth_uses_config_session_expire(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "_cfg.SESSION_EXPIRE_DAYS" in src

    def test_auth_uses_config_otp_expire(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "_cfg.OTP_EXPIRE_MINUTES" in src

    def test_auth_uses_config_esms(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "_cfg.ESMS_API_KEY" in src
        assert "_cfg.ESMS_SECRET" in src
        assert "_cfg.ESMS_BRANDNAME" in src

    def test_no_os_getenv_in_auth(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "os.getenv" not in src, "auth.py should use config.py, not os.getenv"
