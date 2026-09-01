from __future__ import annotations

import json


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


def test_run_saga_compensates_completed_steps_and_is_idempotent():
    from control_plane.saga import SagaStep, run_saga

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
