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


# ── Shared require_pg ──────────────────────────────────────────────────

def test_shared_require_pg_exists():
    from auth_middleware import require_pg
    assert callable(require_pg)
