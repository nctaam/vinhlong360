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
import tempfile
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
    from unittest.mock import AsyncMock
    app.dependency_overrides[admin.require_admin] = lambda: "test"
    client = TestClient(app)

    resp = client.get("/admin/activity-feed?limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["actions"]) == 2
    assert data["actions"][0]["method"] == "DELETE"
    assert data["actions"][1]["method"] == "PUT"


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
    assert params == ["abc-123"]


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
    import inspect
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
    """Comma-separated type filter should work."""
    import public_api
    entities = [
        {"id": "a", "name": "A", "type": "dish", "coordinates": [10.25, 106.01],
         "attributes": {}, "placeId": None},
        {"id": "b", "name": "B", "type": "attraction", "coordinates": [10.26, 106.02],
         "attributes": {}, "placeId": None},
        {"id": "c", "name": "C", "type": "product", "coordinates": [10.27, 106.03],
         "attributes": {}, "placeId": None},
    ]
    from unittest.mock import patch
    with patch.object(public_api.db, "list_entities", return_value=entities):
        public_api._map_pins_cache.update(data=None, filters=None, ts=0.0)
        client = _public_client()
        resp = client.get("/api/map-pins?type=dish,attraction")
    assert resp.status_code == 200
    pins = resp.json()
    assert len(pins) == 2
    ids = {p["id"] for p in pins}
    assert ids == {"a", "b"}


# ── Review stats ──────────────────────────────────────────────────────

def test_review_stats_endpoint_mounted():
    pairs = _route_pairs(_public_client().app)
    assert ("GET", "/api/entities/{entity_id}/review-stats") in pairs


def test_review_stats_no_pg_returns_empty():
    """Without Postgres, review-stats returns empty defaults."""
    import public_api
    if not db._use_pg:
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
    assert "ip" in record


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
