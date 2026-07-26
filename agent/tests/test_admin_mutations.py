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

_KNOWLEDGE_STATE_NAMES = (
    "_entities",
    "_relationships",
    "_itineraries",
    "_data_source",
    "_adjacency",
    "_adj_src",
)


@pytest.fixture
def knowledge_state_snapshot():
    import knowledge

    snapshot = {name: getattr(knowledge, name) for name in _KNOWLEDGE_STATE_NAMES}
    yield snapshot
    for name, original in snapshot.items():
        assert getattr(knowledge, name) is original
    entities = knowledge._entities or {}
    assert "test-isolation-sentinel" not in entities
    assert "test-mutation-knowledge-lifecycle" not in entities


@pytest.fixture(autouse=True)
def isolate_admin_database(isolated_sqlite_db, monkeypatch, knowledge_state_snapshot):
    import admin
    import database
    import knowledge

    monkeypatch.setattr(database, "db", isolated_sqlite_db)
    monkeypatch.setattr(admin, "db", isolated_sqlite_db)
    try:
        # Keep reload from treating an emptied test DB as a fresh install and seeding real data.
        isolated_sqlite_db.upsert_entity({
            "id": "test-isolation-sentinel",
            "name": "Test isolation sentinel",
            "type": "attraction",
        })
        yield
    finally:
        for name, original in knowledge_state_snapshot.items():
            setattr(knowledge, name, original)


def test_admin_mutations_use_temporary_sqlite(isolated_sqlite_db):
    assert pathlib.Path(isolated_sqlite_db.db_path).name == "isolated.db"
    assert pathlib.Path(isolated_sqlite_db.db_path).resolve() != (
        pathlib.Path(__file__).resolve().parents[1] / "data" / "vinhlong360.db"
    ).resolve()


def test_admin_mutation_knowledge_state_is_fixture_scoped():
    response = _create_entity("knowledge-lifecycle")
    assert response.status_code == 201

    import knowledge

    assert "test-isolation-sentinel" in knowledge._entities
    assert "test-mutation-knowledge-lifecycle" in knowledge._entities


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


def _assert_ai_only_response(response):
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ai_only_media"


def test_create_entity_rejects_non_ai_images_without_mutation(isolated_sqlite_db):
    response = client.post("/admin/entities", json={
        "id": "test-mutation-non-ai-create",
        "name": "Non AI create",
        "type": "attraction",
        "images": ["https://cdn.example/photo.jpg"],
    }, headers=H)

    _assert_ai_only_response(response)
    assert isolated_sqlite_db.get_entity("test-mutation-non-ai-create") is None


def test_update_entity_rejects_non_ai_images_without_mutation(isolated_sqlite_db):
    isolated_sqlite_db.upsert_entity({
        "id": "test-mutation-non-ai-update",
        "name": "Before",
        "type": "attraction",
        "images": ["/legacy/existing.jpg"],
    })

    response = client.put("/admin/entities/test-mutation-non-ai-update", json={
        "name": "After",
        "images": ["/uploads/new-photo.jpg"],
    }, headers=H)

    _assert_ai_only_response(response)
    saved = isolated_sqlite_db.get_entity("test-mutation-non-ai-update")
    assert saved["name"] == "Before"
    assert saved["images"] == ["/legacy/existing.jpg"]


def test_entity_image_url_rejects_non_ai_before_network_or_database_mutation(
    isolated_sqlite_db,
    monkeypatch,
):
    import admin

    isolated_sqlite_db.upsert_entity({
        "id": "test-mutation-image-url",
        "name": "Image URL",
        "type": "attraction",
        "images": [],
    })
    network_calls: list[str] = []
    monkeypatch.setattr(admin, "_validate_public_image_url", network_calls.append)

    response = client.post(
        "/admin/entities/test-mutation-image-url/images",
        json={"url": "https://cdn.example/photo.jpg"},
        headers=H,
    )

    _assert_ai_only_response(response)
    assert network_calls == []
    assert isolated_sqlite_db.get_entity("test-mutation-image-url")["images"] == []


def test_entity_image_upload_rejects_non_ai_before_storage_or_database_mutation(
    isolated_sqlite_db,
    monkeypatch,
):
    import storage

    isolated_sqlite_db.upsert_entity({
        "id": "test-mutation-image-upload",
        "name": "Image upload",
        "type": "attraction",
        "images": [],
    })
    storage_calls: list[str] = []
    monkeypatch.setattr(storage.storage, "sniff_image_type", lambda _data: "image/jpeg")
    monkeypatch.setattr(
        storage.storage,
        "upload_image_set",
        lambda *_args: storage_calls.append("upload") or {
            "md": "/img/entities/uploaded.webp",
        },
    )

    response = client.post(
        "/admin/entities/test-mutation-image-upload/images/upload",
        files={"file": ("photo.jpg", b"not-really-an-image", "image/jpeg")},
        headers=H,
    )

    _assert_ai_only_response(response)
    assert storage_calls == []
    assert isolated_sqlite_db.get_entity("test-mutation-image-upload")["images"] == []


def test_suggestion_approval_rejects_non_ai_before_network_storage_or_mutation(
    isolated_sqlite_db,
    monkeypatch,
):
    import admin
    import storage

    isolated_sqlite_db.upsert_entity({
        "id": "test-mutation-suggestion",
        "name": "Suggestion",
        "type": "attraction",
        "images": [],
    })
    side_effects: list[str] = []
    monkeypatch.setattr(admin._imgq, "get_suggestion", lambda _id: {
        "id": "suggestion-1",
        "entity_id": "test-mutation-suggestion",
        "candidate_url": "https://cdn.example/photo.jpg",
        "status": "pending",
    })
    monkeypatch.setattr(admin._imgq, "mark_status", lambda *_args, **_kwargs: side_effects.append("status"))
    monkeypatch.setattr(
        admin._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: side_effects.append("network"),
    )

    async def fetched(*_args, **_kwargs):
        side_effects.append("fetch")
        return b"image"

    monkeypatch.setattr(admin, "_approve_fetch_image_data", fetched)
    monkeypatch.setattr(
        storage.storage,
        "upload_image_set",
        lambda *_args: side_effects.append("storage") or {
            "md": "/img/entities/suggestion.webp",
        },
    )

    response = client.post(
        "/admin/image-suggestions/suggestion-1/approve",
        headers=H,
    )

    _assert_ai_only_response(response)
    assert side_effects == []
    assert isolated_sqlite_db.get_entity("test-mutation-suggestion")["images"] == []


def test_media_policy_keeps_pydantic_shape_errors_as_422():
    create_response = client.post("/admin/entities", json={
        "id": "test-mutation-shape",
        "name": "Shape",
        "type": "attraction",
        "images": "not-a-list",
    }, headers=H)
    url_response = client.post(
        "/admin/entities/test-mutation-shape/images",
        json={"url": ["not-a-string"]},
        headers=H,
    )

    assert create_response.status_code == 422
    assert url_response.status_code == 422


def test_admin_update_does_not_erase_publication_fields(isolated_sqlite_db):
    isolated_sqlite_db.upsert_entity({
        "id": "test-mutation-status",
        "name": "Published entity",
        "type": "attraction",
        "status": "published",
        "verified": True,
    })
    response = client.put(
        "/admin/entities/test-mutation-status",
        json={"name": "Renamed", "type": "attraction"},
        headers=H,
    )
    assert response.status_code == 200
    saved = isolated_sqlite_db.get_entity("test-mutation-status")
    assert saved["status"] == "published"
    assert saved["verified"] in (True, 1)


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
    r = client.post("/admin/provisional/nonexistent/approve",
                    json={"review_token": "0" * 64}, headers=H)
    assert r.status_code == 404


def test_provisional_approve_requires_review_token_body():
    r = client.post("/admin/provisional/nonexistent/approve", headers=H)
    assert r.status_code == 422


@pytest.mark.parametrize("review_token", ["0" * 63, "0" * 65, "A" * 64, "g" * 64])
def test_provisional_approve_validates_review_token(review_token):
    r = client.post("/admin/provisional/nonexistent/approve",
                    json={"review_token": review_token}, headers=H)
    assert r.status_code == 422


def test_provisional_stale_review_returns_conflict(monkeypatch):
    import kb_curation

    monkeypatch.setattr(
        kb_curation,
        "promote",
        lambda entity_id, review_token: {"ok": False, "error": "stale_review"},
    )
    r = client.post("/admin/provisional/nonexistent/approve",
                    json={"review_token": "0" * 64}, headers=H)
    assert r.status_code == 409


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


def test_admin_media_keeps_legacy_raw_images_inspectable_and_removable(
    isolated_sqlite_db,
):
    import admin

    entity_id = "test-admin-raw-media"
    isolated_sqlite_db.upsert_entity({
        "id": entity_id,
        "name": "Admin raw media",
        "type": "attraction",
        "images": [
            "https://cdn.example/user-upload.webp",
            "/img/entities/test-admin-raw-media.webp",
        ],
    })
    admin._media_cache.update(ts=0.0, data=None)

    gallery = client.get("/admin/media?limit=200", headers=H)

    assert gallery.status_code == 200
    raw_item = next(
        item for item in gallery.json()["items"]
        if item["url"] == "https://cdn.example/user-upload.webp"
    )
    assert raw_item["entity_id"] == entity_id
    assert raw_item["usage_count"] == 1

    removed = client.delete(f"/admin/entities/{entity_id}/images/0", headers=H)

    assert removed.status_code == 200
    assert removed.json()["images"] == ["/img/entities/test-admin-raw-media.webp"]
    assert isolated_sqlite_db.get_entity(entity_id)["images"] == [
        "/img/entities/test-admin-raw-media.webp",
    ]


def test_admin_media_skips_malformed_persisted_image_elements(isolated_sqlite_db):
    import admin

    isolated_sqlite_db.upsert_entity({
        "id": "test-admin-malformed-media",
        "name": "Admin malformed media",
        "type": "attraction",
        "images": [
            None,
            42,
            ["nested"],
            {"unexpected": "shape"},
            {"url": 42},
            {"url": ["nested"]},
            "https://cdn.example/valid-raw.webp",
        ],
    })
    admin._media_cache.update(ts=0.0, data=None)

    response = client.get("/admin/media?limit=200", headers=H)

    assert response.status_code == 200
    assert [item["url"] for item in response.json()["items"]] == [
        "https://cdn.example/valid-raw.webp",
    ]


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
