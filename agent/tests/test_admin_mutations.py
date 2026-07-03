"""Runtime tests for admin mutation endpoints used daily.

These tests verify endpoints don't crash at runtime — the kind of bug
that source-inspection can't catch (module-vs-instance, SQL dialect, etc.).
"""
import os
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-mutations")
os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
os.environ.setdefault("BACKGROUND_INDEX_BUILD", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
import sys
import pathlib
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402
from server import app  # noqa: E402

client = TestClient(app)
H = {"X-Admin-Key": os.environ["ADMIN_API_KEY"]}
_USE_PG = os.environ.get("USE_POSTGRES") == "true"


# ── Entity CRUD ──────────────────────────────────────────────────────────

def _create_entity(suffix="1"):
    return client.post("/admin/entities", json={
        "id": f"test-mutation-{suffix}",
        "name": f"Test Entity {suffix}",
        "type": "attraction",
        "summary": "Runtime test entity",
    }, headers=H)


def test_create_entity():
    r = _create_entity("create")
    assert r.status_code in (201, 409)


def test_update_entity():
    _create_entity("update")
    r = client.put("/admin/entities/test-mutation-update", json={
        "name": "Test Entity Updated",
        "type": "attraction",
    }, headers=H)
    assert r.status_code == 200


def test_delete_entity():
    _create_entity("delete")
    r = client.delete("/admin/entities/test-mutation-delete", headers=H)
    assert r.status_code == 200


def test_create_entity_requires_auth():
    r = client.post("/admin/entities", json={"id": "x", "name": "x", "type": "attraction"})
    assert r.status_code == 401


# ── Entity bulk operations ───────────────────────────────────────────────

def test_bulk_place_endpoint_runs():
    r = client.post("/admin/entities/bulk-place", json={
        "entity_ids": [],
        "place_id": "nonexistent",
    }, headers=H)
    assert r.status_code in (200, 422)


def test_bulk_delete_empty():
    r = client.post("/admin/entities/bulk-delete", json={
        "entity_ids": [],
    }, headers=H)
    assert r.status_code in (200, 422)


# ── Itinerary CRUD ───────────────────────────────────────────────────────

def test_create_itinerary():
    r = client.post("/admin/itineraries", json={
        "name": "Test Itin Mutation",
        "title": "Test Itin Mutation",
        "stops": [],
    }, headers=H)
    assert r.status_code in (200, 201, 422)


def test_delete_itinerary_nonexistent():
    r = client.delete("/admin/itineraries/nonexistent-itin", headers=H)
    assert r.status_code in (200, 404)


# ── Relationships ────────────────────────────────────────────────────────

def test_relationship_create_validates():
    r = client.post("/admin/relationships", json={
        "from_id": "nonexistent-a",
        "to_id": "nonexistent-b",
        "type": "near",
    }, headers=H)
    assert r.status_code in (200, 201, 404, 422)


# ── Moderation ───────────────────────────────────────────────────────────

def test_moderation_batch_empty():
    r = client.post("/admin/moderation/batch", json={
        "post_ids": [],
        "action": "approve",
    }, headers=H)
    assert r.status_code in (200, 422)


@pytest.mark.skipif(not _USE_PG, reason="moderation needs PG (UGC table)")
def test_moderation_approve_nonexistent():
    r = client.post("/admin/moderation/nonexistent-post/approve", headers=H)
    assert r.status_code in (200, 404)


@pytest.mark.skipif(not _USE_PG, reason="moderation needs PG (UGC table)")
def test_moderation_reject_needs_reason():
    r = client.post("/admin/moderation/nonexistent-post/reject",
                    json={"reason": "test"}, headers=H)
    assert r.status_code in (200, 404)


# ── User management ─────────────────────────────────────────────────────

@pytest.mark.skipif(not _USE_PG, reason="user mgmt needs PG")
def test_ban_nonexistent_user():
    r = client.post("/admin/users/nonexistent-user/ban",
                    json={"reason": "test"}, headers=H)
    assert r.status_code in (200, 404)


@pytest.mark.skipif(not _USE_PG, reason="user mgmt needs PG")
def test_role_assignment_nonexistent():
    r = client.post("/admin/users/nonexistent-user/role",
                    json={"role": "moderator"}, headers=H)
    assert r.status_code in (200, 404)


# ── Reports ──────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _USE_PG, reason="reports needs PG")
def test_resolve_report_nonexistent():
    r = client.post("/admin/reports/nonexistent-report/resolve",
                    json={"resolution": "addressed"}, headers=H)
    assert r.status_code in (200, 404)


@pytest.mark.skipif(not _USE_PG, reason="reports needs PG")
def test_dismiss_report_nonexistent():
    r = client.post("/admin/reports/nonexistent-report/dismiss",
                    json={}, headers=H)
    assert r.status_code in (200, 404)


# ── Data quality ─────────────────────────────────────────────────────────

def test_data_quality_apply_dry_run():
    r = client.post("/admin/data-quality/apply", json={
        "candidate_ids": [],
        "dry_run": True,
    }, headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body.get("dry_run") is True


def test_data_quality_decision_endpoint_runs():
    r = client.post("/admin/data-quality/decision", json={
        "candidate_ids": ["nonexistent"],
        "decision": "approve",
    }, headers=H)
    assert r.status_code in (200, 403, 404, 422)


# ── Site settings ────────────────────────────────────────────────────────

@pytest.mark.skipif(not _USE_PG, reason="site-settings needs PG")
def test_site_settings_update():
    r = client.put("/admin/site-settings/site.name",
                   json={"value": "Test Site"}, headers=H)
    assert r.status_code == 200


@pytest.mark.skipif(not _USE_PG, reason="site-settings needs PG")
def test_site_settings_bulk():
    r = client.post("/admin/site-settings/bulk",
                    json={"settings": {"site.name": "Test Site Bulk"}}, headers=H)
    assert r.status_code == 200


# ── Provisional ──────────────────────────────────────────────────────────

def test_provisional_approve_nonexistent():
    r = client.post("/admin/provisional/nonexistent/approve", headers=H)
    assert r.status_code in (200, 404)


def test_provisional_reject_nonexistent():
    r = client.post("/admin/provisional/nonexistent/reject", headers=H)
    assert r.status_code in (200, 404)


# ── GET endpoints that previously 500'd or are high-traffic ──────────────

def test_dashboard_stats_endpoint():
    r = client.get("/admin/stats", headers=H)
    assert r.status_code == 200


def test_badge_counts_endpoint():
    r = client.get("/admin/badge-counts", headers=H)
    assert r.status_code == 200


def test_ops_summary_endpoint():
    r = client.get("/admin/ops-summary", headers=H)
    assert r.status_code == 200


def test_audit_log_endpoint():
    r = client.get("/admin/audit-log?limit=5", headers=H)
    assert r.status_code == 200


def test_media_endpoint():
    r = client.get("/admin/media?limit=5", headers=H)
    assert r.status_code == 200


def test_stale_queue_endpoint():
    r = client.get("/admin/stale-queue?limit=5", headers=H)
    assert r.status_code == 200


def test_entity_schema_endpoint():
    r = client.get("/admin/entity-schema", headers=H)
    assert r.status_code == 200


def test_entity_kinds_endpoint():
    r = client.get("/admin/entity-kinds", headers=H)
    assert r.status_code == 200


def test_data_quality_summary():
    r = client.get("/admin/data-quality/summary", headers=H)
    assert r.status_code == 200
