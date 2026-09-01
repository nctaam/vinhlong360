from __future__ import annotations

import io
import json
import threading

import pytest


class FakeStorage:
    backend = "fake"

    def __init__(self):
        self.objects: set[str] = set()
        self.fail_after_upload_once = False

    def upload_image_set(self, data, folder="entities", slug="img"):
        del data
        urls = {size: f"/media/{folder}/{slug}-{size}.webp" for size in ("sm", "md", "lg")}
        self.objects.update(urls.values())
        if self.fail_after_upload_once:
            self.fail_after_upload_once = False
            raise RuntimeError("injected_upload_failure")
        return urls

    def delete(self, key):
        self.objects.discard(key)


def test_run_saga_compensates_completed_steps_and_is_idempotent(monkeypatch, isolated_sqlite_db):
    from control_plane.saga import SagaStep, run_saga
    import control_plane.saga as saga

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    saga._SAGA_RECEIPTS.clear()

    state: list[str] = []
    steps = [
        SagaStep("first", lambda: state.append("run-1") or {"key": "one"}, lambda r: state.append("undo-1")),
        SagaStep("second", lambda: (_ for _ in ()).throw(RuntimeError("boom")), lambda r: state.append("undo-2")),
    ]

    first = run_saga(steps, idempotency_key="saga-1")
    second = run_saga(steps, idempotency_key="saga-1")

    assert first.status == "failed_compensated"
    assert second == first
    assert state == ["run-1", "undo-1"]


def test_run_saga_replays_durable_receipt_after_process_cache_loss(monkeypatch, isolated_sqlite_db):
    from control_plane.saga import SagaStep, run_saga
    import control_plane.saga as saga

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    saga._SAGA_RECEIPTS.clear()
    calls = []
    steps = [SagaStep("one", lambda: calls.append("run") or {"ok": True}, lambda _: None)]
    first = run_saga(steps, idempotency_key="durable-generic-1")
    saga._SAGA_RECEIPTS.clear()
    second = run_saga(steps, idempotency_key="durable-generic-1")
    assert first.status == "committed"
    assert second == first
    assert calls == ["run"]


def test_run_saga_conflicts_when_same_key_has_different_steps(monkeypatch, isolated_sqlite_db):
    from control_plane.saga import SagaStep, run_saga
    import control_plane.saga as saga

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    saga._SAGA_RECEIPTS.clear()
    calls = []
    first = run_saga([SagaStep("one", lambda: calls.append("one"), lambda _: None)],
                     idempotency_key="generic-conflict")
    second = run_saga([SagaStep("two", lambda: calls.append("two"), lambda _: None)],
                      idempotency_key="generic-conflict")
    assert first.status == "committed"
    assert second.status == "idempotency_conflict"
    assert calls == ["one"]


def test_claim_decision_uses_nullable_reviewer_for_api_key_actor(monkeypatch):
    from entities import admin_api
    import control_plane.saga as saga

    captured = []

    class FakeDatabase:
        _ph = "%s"
        _use_pg = True

        def _fetchone(self, conn, sql, params):
            if sql.startswith("SELECT"):
                return {"id": "claim-uuid", "status": "pending", "claimant_id": "person-1",
                        "entity_id": "entity-1", "reviewer_id": None, "reviewed_at": None,
                        "rejection_reason": ""}
            return {"id": "claim-uuid"}

        @staticmethod
        def _row_to_dict(row):
            return dict(row)

        @staticmethod
        def _execute(conn, sql, params):
            assert params[0] is None
            return type("Result", (), {"rowcount": 1})()

        def record_entity_mutation_audit(self, **event):
            captured.append(event)

    fake_db = FakeDatabase()
    monkeypatch.setattr(admin_api, "db", fake_db)
    monkeypatch.setattr(saga, "db", fake_db)
    result = admin_api._apply_claim_decision(
        "conn", "claim-uuid", "approved", "api-key-admin", "claim_approved",
        reviewer_id=None,
    )
    assert result["ok"] is True
    assert captured[0]["actor_id"] == "api-key-admin"
    assert captured[0]["after"]["reviewer_id"] is None


def test_image_approval_invalidation_failure_keeps_committed_media(monkeypatch, isolated_sqlite_db):
    import image_suggestions
    import control_plane.saga as saga

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    monkeypatch.setattr(image_suggestions, "db", isolated_sqlite_db)
    image_suggestions._table_ready = False
    isolated_sqlite_db.upsert_entity({"id": "e-post", "name": "Entity", "type": "attraction", "images": []})
    sid = image_suggestions.create_batch([{"entity_id": "e-post", "candidate_url": "https://example.test/a.jpg"}])["ids"][0]
    storage = FakeStorage()
    monkeypatch.setattr(saga, "storage", storage)
    monkeypatch.setattr(saga, "fetch_image_data", lambda suggestion: b"bytes")
    monkeypatch.setattr(saga, "invalidate_entity", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("cache_down")))

    result = saga.approve_image_suggestion(sid, "admin-1", idempotency_key="k-post")
    assert result.status == "committed"
    assert result.post_commit_effects[0]["status"] == "failed"
    assert storage.objects
    assert image_suggestions.get_suggestion(sid)["status"] == "approved"


@pytest.mark.anyio
async def test_direct_upload_compensates_when_entity_commit_fails(monkeypatch, isolated_sqlite_db):
    from entities import admin_api
    import storage as storage_module
    from starlette.datastructures import UploadFile

    class UploadStorage(FakeStorage):
        @staticmethod
        def sniff_image_type(data):
            return "image/jpeg" if data else None

    upload_storage = UploadStorage()
    monkeypatch.setattr(admin_api, "db", isolated_sqlite_db)
    monkeypatch.setattr(admin_api, "_reject_non_ai_media", lambda: None)
    monkeypatch.setattr(admin_api, "_sync_kb", lambda: None)
    isolated_sqlite_db.upsert_entity({"id": "e-direct", "name": "Entity", "type": "attraction", "images": []})
    monkeypatch.setattr(isolated_sqlite_db, "upsert_entity", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("db_failure")))
    monkeypatch.setattr(storage_module, "storage", upload_storage)
    file = UploadFile(filename="image.jpg", file=io.BytesIO(b"jpeg-bytes"))
    with pytest.raises(RuntimeError, match="db_failure"):
        await admin_api.upload_entity_image("e-direct", file)
    assert upload_storage.objects == set()


@pytest.mark.anyio
async def test_direct_upload_compensates_partial_provider_failure(monkeypatch, isolated_sqlite_db):
    from entities import admin_api
    import storage as storage_module
    from starlette.datastructures import UploadFile

    class PartialUploadStorage(FakeStorage):
        @staticmethod
        def sniff_image_type(data):
            return "image/jpeg" if data else None

        def upload_image_set(self, data, folder="entities", slug="img"):
            urls = super().upload_image_set(data, folder, slug)
            failure = RuntimeError("partial_provider_failure")
            failure.urls = urls
            raise failure

    upload_storage = PartialUploadStorage()
    monkeypatch.setattr(admin_api, "db", isolated_sqlite_db)
    monkeypatch.setattr(admin_api, "_reject_non_ai_media", lambda: None)
    monkeypatch.setattr(storage_module, "storage", upload_storage)
    isolated_sqlite_db.upsert_entity({"id": "e-partial", "name": "Entity", "type": "attraction", "images": []})
    file = UploadFile(filename="image.jpg", file=io.BytesIO(b"jpeg-bytes"))

    with pytest.raises(Exception, match="Không thể upload"):
        await admin_api.upload_entity_image("e-partial", file)
    assert upload_storage.objects == set()


@pytest.mark.anyio
async def test_direct_upload_preserves_media_when_invalidation_fails_after_commit(monkeypatch, isolated_sqlite_db):
    from entities import admin_api
    import storage as storage_module
    import database as database_module
    from starlette.datastructures import UploadFile

    class UploadStorage(FakeStorage):
        @staticmethod
        def sniff_image_type(data):
            return "image/jpeg" if data else None

    upload_storage = UploadStorage()
    monkeypatch.setattr(admin_api, "db", isolated_sqlite_db)
    monkeypatch.setattr(admin_api, "_reject_non_ai_media", lambda: None)
    monkeypatch.setattr(admin_api, "_sync_kb", lambda: None)
    isolated_sqlite_db.upsert_entity({"id": "e-direct-post", "name": "Entity", "type": "attraction", "images": []})
    monkeypatch.setattr(storage_module, "storage", upload_storage)
    monkeypatch.setattr(database_module, "invalidate_entity", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("cache_down")))
    file = UploadFile(filename="image.jpg", file=io.BytesIO(b"jpeg-bytes"))
    result = await admin_api.upload_entity_image("e-direct-post", file)
    assert result["status"] == "uploaded_degraded"
    assert upload_storage.objects
    assert isolated_sqlite_db.get_entity("e-direct-post")["images"]


def test_bulk_place_records_per_item_upsert_failure(monkeypatch):
    from entities import admin_api

    class FakeDatabase:
        def get_entities_batch(self, ids):
            return {eid: {"id": eid, "name": eid, "type": "attraction", "images": []} for eid in ids}

        def upsert_entity(self, entity, **kwargs):
            if entity["id"] == "boom":
                raise RuntimeError("write_failure")

    monkeypatch.setattr(admin_api, "db", FakeDatabase())
    assigned, errors, outcomes = admin_api._bulk_assign_entities(["ok", "boom"], None, None)
    assert assigned == ["ok"]
    assert errors == [{"id": "boom", "error": "Không thể cập nhật entity"}]
    assert outcomes[-1]["ok"] is False


@pytest.mark.anyio
async def test_bulk_relationship_blank_id_has_explicit_failed_outcome(monkeypatch):
    from entities import admin_api

    body = admin_api.RelationshipBulkCreate(
        from_id="source-1",
        pairs=[admin_api.RelationshipBulkPair(to_id="   ", type="near")],
    )
    result = await admin_api.add_relationships_bulk(body)
    assert result["added"] == 0
    assert result["outcomes"] == [{"to_id": "", "type": "near", "ok": False, "error": "ID đích trống"}]


@pytest.mark.anyio
async def test_bulk_place_invalid_id_has_explicit_failed_outcome(monkeypatch):
    from entities import admin_api

    class FakeDatabase:
        def get_entities_batch(self, ids):
            return {eid: {"id": eid, "name": eid, "type": "attraction", "images": []} for eid in ids}

        def upsert_entity(self, entity, **kwargs):
            return None

    monkeypatch.setattr(admin_api, "db", FakeDatabase())
    result = await admin_api.bulk_assign_place(
        admin_api.BulkAssignPlaceRequest(entity_ids=["ok", "   "], place_id=None)
    )
    assert result["assigned"] == 1
    assert result["outcomes"][-1]["ok"] is False


@pytest.mark.anyio
async def test_bulk_delete_records_per_item_exception(monkeypatch):
    from entities import admin_api

    class FakeDatabase:
        def delete_entity(self, entity_id, **kwargs):
            if entity_id == "boom":
                raise RuntimeError("delete_failure")
            return entity_id == "ok"

    monkeypatch.setattr(admin_api, "db", FakeDatabase())
    result = await admin_api.bulk_delete(admin_api.BulkDeleteRequest(entity_ids=["ok", "boom"]))
    assert result["count"] == 1
    assert result["outcomes"][-1] == {"id": "boom", "ok": False, "error": "Không thể xóa entity"}


def test_image_upload_failure_compensates_object_and_retry_is_idempotent(monkeypatch, isolated_sqlite_db):
    import image_suggestions
    import control_plane.saga as saga

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    monkeypatch.setattr(image_suggestions, "db", isolated_sqlite_db)
    image_suggestions._table_ready = False
    isolated_sqlite_db.upsert_entity({"id": "e-1", "name": "Entity", "type": "attraction", "images": []})
    sid = image_suggestions.create_batch([{"entity_id": "e-1", "candidate_url": "https://example.test/a.jpg"}])["ids"][0]
    storage = FakeStorage()
    storage.fail_after_upload_once = True
    monkeypatch.setattr(saga, "storage", storage)
    monkeypatch.setattr(saga, "fetch_image_data", lambda suggestion: b"bytes")

    first = saga.approve_image_suggestion(sid, "admin-1", idempotency_key="k-1")
    assert first.status == "failed_compensated"
    assert storage.objects == set()
    saga._SAGA_RECEIPTS.clear()
    second = saga.approve_image_suggestion(sid, "admin-1", idempotency_key="k-1")
    assert second == first


def test_entity_audit_envelope_captures_actor_reason_correlation_revision_and_snapshots(monkeypatch, isolated_sqlite_db):
    import control_plane.saga as saga

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    isolated_sqlite_db.upsert_entity({"id": "e-2", "name": "Before", "type": "attraction", "images": []})
    saga.record_entity_mutation(
        "e-2", actor_id="admin-1", reason="correction", correlation_id="corr-1",
        before={"name": "Before"}, after={"name": "After"}, revision=2,
    )
    events = isolated_sqlite_db.get_entity_audit("e-2")
    event = next(e for e in events if e["correlation_id"] == "corr-1")
    assert event["actor_id"] == "admin-1"
    assert event["reason"] == "correction"
    assert event["correlation_id"] == "corr-1"
    assert event["revision"] == 2
    assert json.loads(event["before_json"])["name"] == "Before"
    assert json.loads(event["after_json"])["name"] == "After"


def test_image_approval_commits_entity_credit_status_and_audit(monkeypatch, isolated_sqlite_db):
    import image_suggestions
    import control_plane.saga as saga

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    monkeypatch.setattr(image_suggestions, "db", isolated_sqlite_db)
    image_suggestions._table_ready = False
    isolated_sqlite_db.upsert_entity({"id": "e-3", "name": "Entity", "type": "attraction", "images": []})
    sid = image_suggestions.create_batch([{"entity_id": "e-3", "candidate_url": "https://example.test/a.jpg", "license": "CC0"}])["ids"][0]
    storage = FakeStorage()
    monkeypatch.setattr(saga, "storage", storage)
    monkeypatch.setattr(saga, "fetch_image_data", lambda suggestion: b"bytes")

    result = saga.approve_image_suggestion(sid, "admin-1", idempotency_key="k-3")
    assert result.status == "committed"
    assert image_suggestions.get_suggestion(sid)["status"] == "approved"
    entity = isolated_sqlite_db.get_entity("e-3")
    assert entity["images"]
    assert entity["attributes"]["image_credits"][0]["license"] == "CC0"
    assert isolated_sqlite_db.get_entity_audit("e-3")[0]["reason"] == "image_approval"


def test_image_approval_merges_concurrent_suggestions_without_lost_images(monkeypatch, isolated_sqlite_db):
    import image_suggestions
    import control_plane.saga as saga

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    monkeypatch.setattr(image_suggestions, "db", isolated_sqlite_db)
    image_suggestions._table_ready = False
    isolated_sqlite_db.upsert_entity({"id": "e-race", "name": "Entity", "type": "attraction", "images": []})
    ids = image_suggestions.create_batch([
        {"entity_id": "e-race", "candidate_url": "https://example.test/a.jpg"},
        {"entity_id": "e-race", "candidate_url": "https://example.test/b.jpg"},
    ]) ["ids"]

    class ConcurrentStorage(FakeStorage):
        def __init__(self):
            super().__init__()
            self.ready = threading.Barrier(2)

        def upload_image_set(self, data, folder="entities", slug="img"):
            self.ready.wait(timeout=5)
            return super().upload_image_set(data, folder, slug)

    storage = ConcurrentStorage()
    monkeypatch.setattr(saga, "storage", storage)
    monkeypatch.setattr(saga, "fetch_image_data", lambda suggestion: b"bytes")
    results = []

    def approve(sid):
        results.append(saga.approve_image_suggestion(sid, "admin-1", idempotency_key=f"race-{sid}"))

    threads = [threading.Thread(target=approve, args=(sid,)) for sid in ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert all(result.status == "committed" for result in results)
    assert len(isolated_sqlite_db.get_entity("e-race")["images"]) == 2
    assert len(isolated_sqlite_db.get_entity("e-race")["attributes"]["image_credits"]) == 2


def test_claim_decision_writes_before_after_audit_in_its_transaction(monkeypatch):
    from entities import admin_api
    import control_plane.saga as saga

    captured = []

    class FakeDatabase:
        _ph = "?"
        _use_pg = False

        def _fetchone(self, conn, sql, params):
            return {
                "id": "claim-1", "status": "pending", "claimant_id": "person-1",
                "entity_id": "entity-1", "reviewer_id": None,
                "reviewed_at": None, "rejection_reason": "",
            }

        @staticmethod
        def _row_to_dict(row):
            return dict(row)

        @staticmethod
        def _execute(conn, sql, params):
            assert "WHERE id" in sql
            return object()

        def record_entity_mutation_audit(self, **event):
            assert event["conn"] == "same-transaction"
            captured.append(event)

    fake_db = FakeDatabase()
    monkeypatch.setattr(admin_api, "db", fake_db)
    monkeypatch.setattr(saga, "db", fake_db)

    result = admin_api._apply_claim_decision(
        "same-transaction", "claim-1", "approved", "admin-1", "correction",
    )

    assert result["ok"] is True
    assert captured[0]["actor_id"] == "admin-1"
    assert captured[0]["reason"] == "correction"
    assert captured[0]["before"]["status"] == "pending"
    assert captured[0]["after"]["status"] == "approved"


def test_provisional_decision_records_entity_audit(monkeypatch):
    from entities import admin_api
    import control_plane.saga as saga

    captured = []

    class FakeDB:
        def get_entity(self, entity_id):
            return {"id": entity_id, "name": "P", "status": "provisional", "verified": False}

        def record_entity_mutation_audit(self, **event):
            captured.append(event)

    fake_db = FakeDB()
    monkeypatch.setattr(admin_api, "db", fake_db)
    monkeypatch.setattr(saga, "db", fake_db)
    admin_api._record_provisional_decision(
        "p-1", "admin-1", "approve", {"status": "provisional", "verified": False},
        {"status": "verified", "verified": True},
    )
    assert captured[0]["actor_id"] == "admin-1"
    assert captured[0]["reason"] == "provisional_approve"
    assert captured[0]["before"]["status"] == "provisional"
    assert captured[0]["after"]["status"] == "verified"


def test_entity_upsert_revision_is_stable_for_noop_and_bumps_for_change(isolated_sqlite_db):
    isolated_sqlite_db.upsert_entity({"id": "e-rev", "name": "Before", "type": "attraction", "images": []})
    assert isolated_sqlite_db.get_entity("e-rev")["revision"] == 1
    isolated_sqlite_db.upsert_entity({"id": "e-rev", "name": "Before", "type": "attraction", "images": []})
    assert isolated_sqlite_db.get_entity("e-rev")["revision"] == 1
    isolated_sqlite_db.upsert_entity({"id": "e-rev", "name": "After", "type": "attraction", "images": []})
    assert isolated_sqlite_db.get_entity("e-rev")["revision"] == 2


def test_replayed_claim_without_receipt_is_in_progress(monkeypatch, isolated_sqlite_db):
    import control_plane.saga as saga
    import image_suggestions

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    monkeypatch.setattr(image_suggestions, "db", isolated_sqlite_db)
    image_suggestions._table_ready = False
    isolated_sqlite_db.upsert_entity({"id": "e-claim", "name": "Entity", "type": "attraction", "images": []})
    sid = image_suggestions.create_batch([{"entity_id": "e-claim", "candidate_url": "https://example.test/a.jpg"}])["ids"][0]
    first_claim, first_replay = saga._claim_command("durable-k", sid, "admin-1")
    second_claim, second_replay = saga._claim_command("durable-k", sid, "admin-1")
    assert first_claim.claimed and first_replay is None
    assert second_claim.replayed
    assert second_replay.status == "in_progress"


def test_durable_suggestion_claim_rejects_other_key(monkeypatch, isolated_sqlite_db):
    import control_plane.saga as saga
    import image_suggestions

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    monkeypatch.setattr(image_suggestions, "db", isolated_sqlite_db)
    image_suggestions._table_ready = False
    isolated_sqlite_db.upsert_entity({"id": "e-cas", "name": "Entity", "type": "attraction", "images": []})
    sid = image_suggestions.create_batch([{"entity_id": "e-cas", "candidate_url": "https://example.test/a.jpg"}])["ids"][0]
    assert saga._claim_suggestion(sid, "admin-1", "key-1")[0] is True
    claimed, error = saga._claim_suggestion(sid, "admin-2", "key-2")
    assert claimed is False
    assert error == "in_progress"


def test_image_approval_db_failure_compensates_uploaded_objects(monkeypatch, isolated_sqlite_db):
    import control_plane.saga as saga
    import image_suggestions

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    monkeypatch.setattr(image_suggestions, "db", isolated_sqlite_db)
    image_suggestions._table_ready = False
    isolated_sqlite_db.upsert_entity({"id": "e-fail", "name": "Entity", "type": "attraction", "images": []})
    sid = image_suggestions.create_batch([{"entity_id": "e-fail", "candidate_url": "https://example.test/a.jpg"}])["ids"][0]
    storage = FakeStorage()
    monkeypatch.setattr(saga, "storage", storage)
    monkeypatch.setattr(saga, "fetch_image_data", lambda suggestion: b"bytes")
    monkeypatch.setattr(saga, "bump_generation", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("commit_failure")))

    result = saga.approve_image_suggestion(sid, "admin-1", idempotency_key="k-fail")
    assert result.status == "failed_compensated"
    assert storage.objects == set()
    assert image_suggestions.get_suggestion(sid)["status"] == "pending"
    assert isolated_sqlite_db.get_entity("e-fail")["images"] == []


def test_cached_approval_receipt_is_not_replayed_for_a_different_request(monkeypatch, isolated_sqlite_db):
    import control_plane.saga as saga

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    saga._SAGA_RECEIPTS.clear()
    saga._SAGA_RECEIPT_HASHES.clear()
    saga._SAGA_RECEIPTS["same-key"] = saga.SagaReceipt("committed", "same-key")
    saga._SAGA_RECEIPT_HASHES["same-key"] = "hash-for-another-suggestion"
    assert saga.peek_approval_receipt("same-key", "s-1", "admin-1") is None


def test_sqlite_idempotency_claim_has_one_winner_across_workers(monkeypatch, isolated_sqlite_db):
    import control_plane.saga as saga
    import image_suggestions

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    monkeypatch.setattr(image_suggestions, "db", isolated_sqlite_db)
    image_suggestions._table_ready = False
    isolated_sqlite_db.upsert_entity({"id": "e-atomic", "name": "Entity", "type": "attraction", "images": []})
    sid = image_suggestions.create_batch([{"entity_id": "e-atomic", "candidate_url": "https://example.test/a.jpg"}])["ids"][0]
    outcomes = []

    def worker():
        outcomes.append(saga._claim_command("atomic-key", sid, "admin-1")[0])

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert sum(result.claimed for result in outcomes) == 1
    assert sum(result.replayed for result in outcomes) == 1


def test_database_commit_failure_is_marked_unknown_not_ordinary_rollback(isolated_sqlite_db, monkeypatch):
    from database import TransactionOutcomeUnknown

    monkeypatch.setattr(isolated_sqlite_db, "_finalize_connection", staticmethod(lambda conn, commit: (_ for _ in ()).throw(RuntimeError("commit_ack_lost"))))
    with pytest.raises(TransactionOutcomeUnknown) as exc_info:
        with isolated_sqlite_db._conn() as conn:
            conn.execute("SELECT 1")
    assert exc_info.value.commit_outcome_unknown is True


def test_receipt_write_failure_is_visible_and_replays_across_workers(monkeypatch, isolated_sqlite_db):
    from control_plane.saga import SagaStep, run_saga
    import control_plane.saga as saga

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    saga._SAGA_RECEIPTS.clear()
    calls = []
    original = saga.record_idempotency_receipt
    monkeypatch.setattr(saga, "record_idempotency_receipt", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("ledger_down")))
    first = run_saga([SagaStep("one", lambda: calls.append("run") or {"ok": True}, lambda _: None)], idempotency_key="receipt-fail")
    assert first.durability_error == "RuntimeError"
    saga._SAGA_RECEIPTS.clear()
    monkeypatch.setattr(saga, "record_idempotency_receipt", original)
    second = run_saga([SagaStep("one", lambda: calls.append("duplicate") or {"ok": True}, lambda _: None)], idempotency_key="receipt-fail")
    assert second == first
    assert calls == ["run"]


def test_provider_empty_cover_is_compensated_and_stays_pending(monkeypatch, isolated_sqlite_db):
    import image_suggestions
    import control_plane.saga as saga

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    monkeypatch.setattr(image_suggestions, "db", isolated_sqlite_db)
    image_suggestions._table_ready = False
    isolated_sqlite_db.upsert_entity({"id": "e-empty", "name": "Entity", "type": "attraction", "images": []})
    sid = image_suggestions.create_batch([{"entity_id": "e-empty", "candidate_url": "https://example.test/a.jpg"}])["ids"][0]

    class EmptyStorage(FakeStorage):
        def upload_image_set(self, data, folder="entities", slug="img"):
            del data, folder, slug
            return {}

    monkeypatch.setattr(saga, "storage", EmptyStorage())
    monkeypatch.setattr(saga, "fetch_image_data", lambda suggestion: b"bytes")
    result = saga.approve_image_suggestion(sid, "admin-1", idempotency_key="empty-cover")
    assert result.status == "failed_compensated"
    assert image_suggestions.get_suggestion(sid)["status"] == "pending"


def test_provider_non_mapping_upload_is_compensated_releases_claim_and_replays(
    monkeypatch, isolated_sqlite_db
):
    import image_suggestions
    import control_plane.saga as saga

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    monkeypatch.setattr(image_suggestions, "db", isolated_sqlite_db)
    image_suggestions._table_ready = False
    isolated_sqlite_db.upsert_entity({"id": "e-malformed", "name": "Entity", "type": "attraction", "images": []})
    sid = image_suggestions.create_batch(
        [{"entity_id": "e-malformed", "candidate_url": "https://example.test/a.jpg"}]
    )["ids"][0]

    class ListStorage(FakeStorage):
        def upload_image_set(self, data, folder="entities", slug="img"):
            urls = super().upload_image_set(data, folder, slug)
            return list(urls.values())

    upload_storage = ListStorage()
    monkeypatch.setattr(saga, "storage", upload_storage)
    monkeypatch.setattr(saga, "fetch_image_data", lambda suggestion: b"bytes")

    first = saga.approve_image_suggestion(sid, "admin-1", idempotency_key="malformed-upload")

    assert first.status == "failed_compensated"
    assert first.error == "RuntimeError"
    assert first.orphan_cleanup_pending is False
    assert upload_storage.objects == set()
    suggestion = image_suggestions.get_suggestion(sid)
    assert suggestion["status"] == "pending"
    assert suggestion.get("approved_by") in (None, "")
    assert saga.approve_image_suggestion(sid, "admin-1", idempotency_key="malformed-upload") == first


@pytest.mark.parametrize(
    "provider_response",
    [
        {"md": {"url": "/media/entities/object-md.webp"}, "lg": "/media/entities/object-lg.webp"},
        {"md": "/media/entities/object-md.webp", "credit": {"author": "bad"}},
    ],
)
def test_provider_malformed_cover_or_credit_is_rejected_before_entity_mutation(
    monkeypatch, isolated_sqlite_db, provider_response
):
    import image_suggestions
    import control_plane.saga as saga

    monkeypatch.setattr(saga, "db", isolated_sqlite_db)
    monkeypatch.setattr(image_suggestions, "db", isolated_sqlite_db)
    image_suggestions._table_ready = False
    isolated_sqlite_db.upsert_entity({"id": "e-malformed-fields", "name": "Entity", "type": "attraction", "images": []})
    sid = image_suggestions.create_batch(
        [{"entity_id": "e-malformed-fields", "candidate_url": "https://example.test/a.jpg"}]
    )["ids"][0]

    class MalformedFieldStorage(FakeStorage):
        def upload_image_set(self, data, folder="entities", slug="img"):
            del data, folder, slug
            return provider_response

    monkeypatch.setattr(saga, "storage", MalformedFieldStorage())
    monkeypatch.setattr(saga, "fetch_image_data", lambda suggestion: b"bytes")

    result = saga.approve_image_suggestion(sid, "admin-1", idempotency_key=f"malformed-field-{sid}")

    assert result.status == "failed_compensated"
    assert isolated_sqlite_db.get_entity("e-malformed-fields")["images"] == []
    suggestion = image_suggestions.get_suggestion(sid)
    assert suggestion["status"] == "pending"
    assert suggestion.get("approved_by") in (None, "")


def test_store_receipt_pg_fallback_casts_meta_to_jsonb(monkeypatch):
    import control_plane.saga as saga
    from control_plane.concurrency import ClaimResult

    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakePG:
        _use_pg = True
        _ph = "%s"

        def _conn(self):
            return _Connection()

        def _execute(self, conn, sql, params):
            self.sql = sql
            self.params = params

    fake_db = FakePG()
    monkeypatch.setattr(saga, "db", fake_db)
    monkeypatch.setattr(saga, "record_idempotency_receipt", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("ledger_down")))
    claim = ClaimResult("receipt-pg", claimed=True, request_hash="hash")
    receipt = saga.SagaReceipt("committed", "receipt-pg")

    stored = saga._store_receipt("receipt-pg", receipt, claim)

    assert stored.durability_error == "RuntimeError"
    assert "meta=%s::jsonb" in fake_db.sql
    assert fake_db.params[1] == "receipt-pg"


def test_update_description_and_cascade_relationship_delete_are_audited(isolated_sqlite_db):
    isolated_sqlite_db.upsert_entity({"id": "audit-a", "name": "A", "type": "attraction", "images": []})
    isolated_sqlite_db.upsert_entity({"id": "audit-b", "name": "B", "type": "attraction", "images": []})
    isolated_sqlite_db.add_relationship("audit-a", "audit-b", "related_to", actor_id="admin-1")
    assert isolated_sqlite_db.update_description("audit-a", "new", actor_id="admin-1", reason="correction")
    assert isolated_sqlite_db.get_entity("audit-a")["revision"] == 2
    isolated_sqlite_db.delete_entity("audit-a", actor_id="admin-1", reason="correction")
    events = isolated_sqlite_db.get_entity_audit()
    assert any(e["reason"] == "correction" and e["before_json"] and e["after_json"] for e in events)
    assert any(e["reason"] == "relationship_cascade_delete" and e["before_json"] for e in events)
