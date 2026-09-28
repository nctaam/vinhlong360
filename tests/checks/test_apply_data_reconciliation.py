import hashlib
import json
import os
import sqlite3
from pathlib import Path

import pytest

import scripts.checks.apply_data_reconciliation as apply_module
from scripts.checks.apply_data_reconciliation import (
    ApplyError,
    apply_plan,
    canonical_plan_sha256,
    main,
    recover_interrupted_apply,
)
from scripts.checks.reconciliation_journal import load_journal
from scripts.checks.reconciliation_lock import ReconciliationLock


def _fixture(tmp_path: Path):
    db = tmp_path / "fixture.db"
    payload = {
        "entities": [
            {"id": "a", "type": "place", "name": "A", "season": None, "attributes": {}, "source": None, "images": [], "coordinates": None},
            {"id": "b", "type": "place", "name": "B", "season": None, "attributes": {}, "source": None, "images": [], "coordinates": None},
        ],
        "relationships": [{"from": "a", "to": "b", "type": "near"}],
        "itineraries": [],
    }
    with sqlite3.connect(db) as conn:
        conn.executescript(
            "CREATE TABLE entities (id TEXT PRIMARY KEY, type TEXT, name TEXT, season TEXT, attributes TEXT, source TEXT, images TEXT, coordinates TEXT);"
            "CREATE TABLE relationships (from_id TEXT, to_id TEXT, type TEXT);"
            "CREATE TABLE itineraries (id TEXT);"
        )
        conn.execute("INSERT INTO entities VALUES ('a','place','A',NULL,'{}',NULL,'[]',NULL)")
        conn.execute("INSERT INTO entities VALUES ('b','place','B',NULL,'{}',NULL,'[]',NULL)")
        conn.execute("INSERT INTO relationships VALUES ('a','b','near')")
    json_path = tmp_path / "data.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    sqlite_backup = tmp_path / "fixture.db.bak"
    sqlite_backup.write_bytes(db.read_bytes())
    json_backup = tmp_path / "data.json.bak"
    json_backup.write_bytes(json_path.read_bytes())
    return db, json_path, sqlite_backup, json_backup


def _plan(db: Path, json_path: Path, *, deferred=None):
    plan = {
        "schemaVersion": 1,
        "mode": "dry-run",
        "status": "approved",
        "reviewedPlanMarker": "reviewed-by-owner",
        "inputs": {
            "sqlite": {"sha256": hashlib.sha256(db.read_bytes()).hexdigest()},
            "json": {"sha256": hashlib.sha256(json_path.read_bytes()).hexdigest()},
        },
        "mutations": [
            {"mutationId": "m1", "store": "sqlite", "recordType": "relationship", "recordId": "a->b", "operation": "update", "field": "type", "before": "near", "after": "related_to", "metadata": {"rowid": 1}},
            {"mutationId": "m2", "store": "json", "recordType": "relationship", "recordId": "a->b", "operation": "update", "field": "relationship", "before": {"from": "a", "to": "b", "type": "near"}, "after": {"from": "a", "to": "b", "type": "related_to"}, "metadata": {"index": 0}},
        ],
        "deferred": deferred or [],
    }
    return plan


def test_requires_confirmation_and_reviewed_approval(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    with pytest.raises(ApplyError, match="confirm-phase-b"):
        apply_plan(plan, db, data, db_bak, data_bak, plan_sha256=canonical_plan_sha256(plan))
    plan["reviewedPlanMarker"] = None
    with pytest.raises(ApplyError, match="reviewed"):
        apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))


def test_rejects_stale_hash_missing_backup_and_unaccepted_deferred(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data, deferred=[{"itemId": "owner-review"}])
    with pytest.raises(ApplyError, match="deferred"):
        apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))
    with pytest.raises(ApplyError, match="plan hash"):
        apply_plan(_plan(db, data), db, data, db_bak, data_bak, confirm=True, plan_sha256="0" * 64)
    db_bak.unlink()
    with pytest.raises(ApplyError, match="backup"):
        apply_plan(_plan(db, data), db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(_plan(db, data)))


def test_successful_fixture_apply_is_atomic_and_parity_clean(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    result = apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))
    assert result["status"] == "applied"
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT type FROM relationships").fetchone()[0] == "related_to"
    assert json.loads(data.read_text(encoding="utf-8"))["relationships"][0]["type"] == "related_to"
    assert result["parity"]["status"] == "clean"


def test_entity_delete_and_nested_remove_apply_to_both_fixture_stores(tmp_path):
    db = tmp_path / "media.db"
    payload = {
        "entities": [
            {"id": "prov-1", "type": "place", "name": "Provider", "season": None,
             "attributes": {"image_author": "unknown", "keep": "yes"}, "source": None,
             "images": [], "coordinates": None},
            {"id": "unrelated", "type": "place", "name": "Unrelated", "season": None,
             "attributes": {"image_author": "remove-me"}, "source": None, "images": [], "coordinates": None},
        ],
        "relationships": [], "itineraries": [],
    }
    with sqlite3.connect(db) as conn:
        conn.executescript(
            "CREATE TABLE entities (id TEXT PRIMARY KEY, type TEXT, name TEXT, season TEXT, attributes TEXT, source TEXT, images TEXT, coordinates TEXT);"
            "CREATE TABLE relationships (from_id TEXT, to_id TEXT, type TEXT);"
            "CREATE TABLE itineraries (id TEXT);"
        )
        conn.execute("INSERT INTO entities VALUES ('prov-1','place','Provider',NULL,?,?,?,?)", (json.dumps({"image_author": "unknown", "keep": "yes"}), None, "[]", None))
        conn.execute("INSERT INTO entities VALUES ('unrelated','place','Unrelated',NULL,?,?,?,?)", (json.dumps({"image_author": "remove-me"}), None, "[]", None))
    data = tmp_path / "media.json"
    data.write_text(json.dumps(payload), encoding="utf-8")
    db_bak = tmp_path / "media.db.bak"; db_bak.write_bytes(db.read_bytes())
    data_bak = tmp_path / "media.json.bak"; data_bak.write_bytes(data.read_bytes())
    plan = {
        "schemaVersion": 1, "mode": "dry-run", "status": "approved", "reviewedPlanMarker": "reviewed",
        "inputs": {"sqlite": {"sha256": hashlib.sha256(db.read_bytes()).hexdigest()},
                   "json": {"sha256": hashlib.sha256(data.read_bytes()).hexdigest()}},
        "mutations": [
            {"mutationId": "s-delete", "store": "sqlite", "recordType": "entity", "recordId": "prov-1",
             "operation": "delete", "field": "entity", "before": payload["entities"][0]},
            {"mutationId": "s-remove", "store": "sqlite", "recordType": "entity", "recordId": "unrelated",
             "operation": "remove", "field": "attributes.image_author", "before": None, "after": None},
            {"mutationId": "j-delete", "store": "json", "recordType": "entity", "recordId": "prov-1",
             "operation": "delete", "field": "entity", "before": payload["entities"][0], "metadata": {"index": 0}},
            {"mutationId": "j-remove", "store": "json", "recordType": "entity", "recordId": "unrelated",
             "operation": "remove", "field": "attributes.image_author", "before": None, "after": None, "metadata": {"index": 1}},
        ], "deferred": [],
    }
    # Remove the nested key from the surviving entity in both stores.
    plan["mutations"][1]["before"] = "remove-me"
    plan["mutations"][3]["before"] = "remove-me"
    result = apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))
    assert result["parity"]["status"] == "clean"
    assert result["verification"]["status"] == "clean"
    expected_survivor = dict(payload["entities"][1], attributes={})
    assert json.loads(data.read_text(encoding="utf-8"))["entities"] == [expected_survivor]
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT id FROM entities").fetchall() == [("unrelated",)]


def test_targeted_media_verification_preserves_unrelated_global_drift(tmp_path):
    db, data, _, _ = _fixture(tmp_path)
    payload = json.loads(data.read_text(encoding="utf-8"))
    payload["entities"][1]["attributes"] = {"unrelated_drift": True}
    data.write_text(json.dumps(payload), encoding="utf-8")
    plan = {"verification": {"mode": "targeted-media-v1", "targets": {"a": payload["entities"][0]}}}
    result = apply_module.verify_plan_result(plan, db, data)
    assert result == {"mode": "targeted-media-v1", "status": "clean", "globalParity": "known-drift-preserved"}


def test_json_manifest_indexes_are_scoped_by_record_type():
    payload = {
        "entities": [{"id": "a", "attributes": {"image_author": "remove-me"}}],
        "relationships": [{"from": "a", "to": "a", "type": "near"}],
    }
    mutations = [
        {
            "mutationId": "entity-remove",
            "store": "json",
            "recordType": "entity",
            "recordId": "a",
            "operation": "remove",
            "field": "attributes.image_author",
            "before": "remove-me",
            "after": None,
            "metadata": {"index": 0},
        },
        {
            "mutationId": "relationship-update",
            "store": "json",
            "recordType": "relationship",
            "recordId": "a->a",
            "operation": "update",
            "field": "relationship",
            "before": {"from": "a", "to": "a", "type": "near"},
            "after": {"from": "a", "to": "a", "type": "related_to"},
            "metadata": {"index": 0},
        },
    ]
    _, json_mutations, _ = apply_module._validated_mutations({"mutations": mutations})
    apply_module._apply_json_mutations(payload, json_mutations)
    assert payload["entities"][0]["attributes"] == {}
    assert payload["relationships"][0]["type"] == "related_to"


def test_generated_graph_insert_schema_applies_and_preserves_relationship_parity(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    payload = json.loads(data.read_text(encoding="utf-8"))
    payload["relationships"].append({"from": "a", "to": "b", "type": "related_to"})
    data.write_text(json.dumps(payload), encoding="utf-8")
    data_bak.write_bytes(data.read_bytes())
    plan = _plan(db, data)
    plan["mutations"] = [
        {
            "mutationId": "graph-1",
            "store": "sqlite",
            "recordType": "relationship",
            "recordId": "prov-1->b",
            "operation": "insert",
            "field": "relationship",
            "before": None,
            "after": {"from_id": "a", "to_id": "b", "type": "related_to"},
        },
    ]
    result = apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))
    assert result["parity"]["status"] == "clean"
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT from_id, to_id, type FROM relationships WHERE from_id = 'a' AND to_id = 'b' AND type = 'related_to'"
        ).fetchone() == ("a", "b", "related_to")


def test_graph_insert_rejects_existing_relationship_triple(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    plan["mutations"] = [{
        "mutationId": "graph-duplicate",
        "store": "sqlite",
        "recordType": "relationship",
        "recordId": "a->b",
        "operation": "insert",
        "field": "relationship",
        "before": None,
        "after": {"from_id": "a", "to_id": "b", "type": "near"},
    }]
    with pytest.raises(ApplyError, match="duplicate"):
        apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))


def test_sqlite_rolls_back_when_mutation_fails_and_json_is_unchanged(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    plan["mutations"].append({"mutationId": "bad", "store": "sqlite", "recordType": "relationship", "recordId": "a->b", "operation": "update", "field": "missing", "before": None, "after": "x"})
    with pytest.raises(ApplyError):
        apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT type FROM relationships").fetchone()[0] == "near"
    assert json.loads(data.read_text(encoding="utf-8"))["relationships"][0]["type"] == "near"


def test_live_paths_require_extra_explicit_flag(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    with pytest.raises(ApplyError, match="live"):
        apply_plan(plan, Path("agent/data/vinhlong360.db"), Path("web/data.json"), db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))


def test_rejects_sqlite_before_value_mismatch(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    plan["mutations"][0]["before"] = "not-near"
    with pytest.raises(ApplyError, match="before"):
        apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))


def test_rejects_json_before_value_mismatch(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    plan["mutations"][1]["before"]["type"] = "not-near"
    with pytest.raises(ApplyError, match="before"):
        apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))


def test_multiple_json_deletes_are_applied_descending_without_index_shift(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO relationships VALUES ('b','a','near')")
        conn.execute("INSERT INTO relationships VALUES ('a','a','near')")
    payload = json.loads(data.read_text(encoding="utf-8"))
    payload["relationships"].extend([
        {"from": "b", "to": "a", "type": "near"},
        {"from": "a", "to": "a", "type": "near"},
    ])
    data.write_text(json.dumps(payload), encoding="utf-8")
    db_bak.write_bytes(db.read_bytes())
    data_bak.write_bytes(data.read_bytes())
    plan = _plan(db, data)
    plan["mutations"] = [
        {"mutationId": "s1", "store": "sqlite", "recordType": "relationship", "recordId": "b->a", "operation": "delete", "field": "relationship", "before": {"from": "b", "to": "a", "type": "near"}, "after": None, "metadata": {"rowid": 2}},
        {"mutationId": "s2", "store": "sqlite", "recordType": "relationship", "recordId": "a->a", "operation": "delete", "field": "relationship", "before": {"from": "a", "to": "a", "type": "near"}, "after": None, "metadata": {"rowid": 3}},
        {"mutationId": "j1", "store": "json", "recordType": "relationship", "recordId": "b->a", "operation": "delete", "field": "relationship", "before": payload["relationships"][1], "after": None, "metadata": {"index": 1}},
        {"mutationId": "j2", "store": "json", "recordType": "relationship", "recordId": "a->a", "operation": "delete", "field": "relationship", "before": payload["relationships"][2], "after": None, "metadata": {"index": 2}},
    ]
    result = apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))
    assert result["parity"]["status"] == "clean"
    assert len(json.loads(data.read_text(encoding="utf-8"))["relationships"]) == 1


def test_rejects_conflicting_json_indexes(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    duplicate = dict(plan["mutations"][1])
    duplicate["mutationId"] = "j2"
    plan["mutations"].append(duplicate)
    with pytest.raises(ApplyError, match="index"):
        apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))


def test_rejects_backup_aliases(tmp_path):
    db, data, _, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    with pytest.raises(ApplyError, match="backup"):
        apply_plan(plan, db, data, db, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))
    hardlink = tmp_path / "db-hardlink.bak"
    os.link(db, hardlink)
    with pytest.raises(ApplyError, match="backup"):
        apply_plan(plan, db, data, hardlink, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))


def test_post_validation_failure_restores_json_atomically_and_rolls_back_sqlite(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    original = data.read_bytes()
    plan = _plan(db, data)
    plan["mutations"][1]["after"]["from"] = "missing"
    with pytest.raises(ApplyError, match="parity"):
        apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))
    assert data.read_bytes() == original
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT type FROM relationships").fetchone()[0] == "near"


def test_malformed_plan_is_apply_error_not_traceback(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    with pytest.raises(ApplyError):
        apply_plan({"status": "approved"}, db, data, db_bak, data_bak, confirm=True, plan_sha256="0" * 64)


def test_parity_rejects_duplicate_and_invalid_json_relationships(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    plan["mutations"][1]["after"] = {"from": "missing", "to": "b", "type": "related_to"}
    with pytest.raises(ApplyError, match="parity"):
        apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))


def test_duplicate_json_relationships_are_not_clean(tmp_path):
    db, data, _, _ = _fixture(tmp_path)
    payload = json.loads(data.read_text(encoding="utf-8"))
    payload["relationships"].append(dict(payload["relationships"][0]))
    data.write_text(json.dumps(payload), encoding="utf-8")
    assert apply_module._parity(db, data)["status"] == "drift"


def test_malformed_or_duplicate_entity_rows_are_not_clean(tmp_path):
    db, data, _, _ = _fixture(tmp_path)
    payload = json.loads(data.read_text(encoding="utf-8"))
    payload["entities"].append({"id": "a"})
    data.write_text(json.dumps(payload), encoding="utf-8")
    assert apply_module._parity(db, data)["status"] == "drift"


@pytest.mark.parametrize("field,value", [("relationships", [42]), ("entities", [{"name": "missing-id"}])])
def test_incomplete_json_rows_are_not_reported_clean(tmp_path, field, value):
    db, data, _, _ = _fixture(tmp_path)
    payload = json.loads(data.read_text(encoding="utf-8"))
    payload[field] = value
    data.write_text(json.dumps(payload), encoding="utf-8")
    assert apply_module._parity(db, data)["status"] == "drift"


def test_non_list_json_collections_are_not_reported_clean(tmp_path):
    db, data, _, _ = _fixture(tmp_path)
    payload = json.loads(data.read_text(encoding="utf-8"))
    payload["relationships"] = {"from": "a", "to": "b", "type": "near"}
    data.write_text(json.dumps(payload), encoding="utf-8")
    assert apply_module._parity(db, data)["status"] == "drift"


def test_malformed_collections_cannot_clean_when_sqlite_collections_are_empty(tmp_path):
    db, data, _, _ = _fixture(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM relationships")
        conn.execute("DELETE FROM entities")
    payload = json.loads(data.read_text(encoding="utf-8"))
    payload["relationships"] = {"from": "a", "to": "b", "type": "near"}
    payload["entities"] = {"id": "a"}
    data.write_text(json.dumps(payload), encoding="utf-8")
    assert apply_module._parity(db, data)["status"] == "drift"


def test_commit_failure_restores_json_atomically_and_rolls_back_sqlite(tmp_path, monkeypatch):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    original = data.read_bytes()
    plan = _plan(db, data)
    real_connect = apply_module.sqlite3.connect
    calls = {"count": 0}

    class CommitFailConnection:
        def __init__(self, connection):
            self._connection = connection

        def execute(self, *args, **kwargs):
            return self._connection.execute(*args, **kwargs)

        def commit(self):
            raise sqlite3.OperationalError("simulated commit failure")

        def rollback(self):
            return self._connection.rollback()

        def close(self):
            return self._connection.close()

    def connect(path, *args, **kwargs):
        calls["count"] += 1
        connection = real_connect(path, *args, **kwargs)
        return CommitFailConnection(connection) if calls["count"] == 2 else connection

    monkeypatch.setattr(apply_module.sqlite3, "connect", connect)
    with pytest.raises(ApplyError, match="simulated commit failure"):
        apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))
    assert data.read_bytes() == original
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT type FROM relationships").fetchone()[0] == "near"


def test_external_json_edit_before_publication_fails_closed_and_preserves_external_bytes(tmp_path, monkeypatch):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    original_publish = apply_module._publish_json

    def edit_before_publication(source, target, expected_bytes, expected_identity):
        data.write_bytes(b'{"external":"edit"}\n')
        return original_publish(source, target, expected_bytes, expected_identity)

    monkeypatch.setattr(apply_module, "_publish_json", edit_before_publication)
    with pytest.raises(ApplyError, match="changed"):
        apply_plan(plan, db, data, db_bak, data_bak, confirm=True, plan_sha256=canonical_plan_sha256(plan))
    assert data.read_bytes() == b'{"external":"edit"}\n'
    journal = db.with_name(f"{db.name}.reconciliation.journal.json")
    assert journal.exists()
    with pytest.raises(ApplyError, match="JSON target ownership cannot be verified"):
        recover_interrupted_apply(journal, db.with_name(f"{db.name}.reconciliation.lock"))
    assert data.read_bytes() == b'{"external":"edit"}\n'
    assert journal.exists()


def test_cli_malformed_plan_returns_controlled_refusal(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan_path = tmp_path / "malformed-plan.json"
    plan_path.write_text("{not-json", encoding="utf-8")
    assert main([
        "--plan", str(plan_path), "--sqlite", str(db), "--json", str(data),
        "--sqlite-backup", str(db_bak), "--json-backup", str(data_bak),
        "--plan-sha256", "0" * 64, "--confirm-phase-b",
    ]) == 2


def test_existing_journal_and_lock_contention_block_fixture_apply(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    lock = tmp_path / "apply.lock"
    journal = tmp_path / "apply.journal.json"
    journal.write_text("stale", encoding="utf-8")
    with pytest.raises(ApplyError, match="existing reconciliation journal"):
        apply_plan(plan, db, data, db_bak, data_bak, lock_path=lock, journal_path=journal, confirm=True, plan_sha256=canonical_plan_sha256(plan))
    journal.unlink()
    with ReconciliationLock(lock, {"operationId": "owner"}), pytest.raises(ApplyError, match="held"):
        apply_plan(plan, db, data, db_bak, data_bak, lock_path=lock, journal_path=journal, confirm=True, plan_sha256=canonical_plan_sha256(plan))


def test_committed_phase_journal_recovers_exact_fixture_snapshot(tmp_path, monkeypatch):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    lock = tmp_path / "apply.lock"
    journal = tmp_path / "apply.journal.json"
    original_publish = apply_module._publish_json

    def fail_publish(*args, **kwargs):
        raise ApplyError("injected after SQLite commit")

    monkeypatch.setattr(apply_module, "_publish_json", fail_publish)
    with pytest.raises(ApplyError, match="injected"):
        apply_plan(plan, db, data, db_bak, data_bak, lock_path=lock, journal_path=journal, confirm=True, plan_sha256=canonical_plan_sha256(plan))
    assert load_journal(journal)["phase"] == "sqlite_committed"
    monkeypatch.setattr(apply_module, "_publish_json", original_publish)
    result = recover_interrupted_apply(journal, lock)
    assert result["status"] == "recovered"
    assert db.read_bytes() == db_bak.read_bytes()
    assert data.read_bytes() == data_bak.read_bytes()
    assert not journal.exists()


def test_json_published_failure_leaves_recoverable_journal(tmp_path, monkeypatch):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    lock = tmp_path / "apply.lock"
    journal = tmp_path / "apply.journal.json"
    original_parity = apply_module._parity
    calls = 0

    def fail_after_publication(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ApplyError("injected after JSON publication")
        return original_parity(*args, **kwargs)

    monkeypatch.setattr(apply_module, "_parity", fail_after_publication)
    with pytest.raises(ApplyError, match="after JSON publication"):
        apply_plan(plan, db, data, db_bak, data_bak, lock_path=lock, journal_path=journal, confirm=True, plan_sha256=canonical_plan_sha256(plan))
    assert load_journal(journal)["phase"] == "json_published"
    recover_interrupted_apply(journal, lock)
    assert db.read_bytes() == db_bak.read_bytes()
    assert data.read_bytes() == data_bak.read_bytes()
    assert not journal.exists()


def test_recovery_refuses_external_json_edit_after_publication_boundary(tmp_path, monkeypatch):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    lock = tmp_path / "apply.lock"
    journal = tmp_path / "apply.journal.json"
    original_publish = apply_module._publish_json

    def publish_then_external_edit(source, target, expected_bytes, expected_identity):
        original_publish(source, target, expected_bytes, expected_identity)
        target.write_bytes(b'{"external":"after-publication"}\n')
        raise ApplyError("simulated failure after publication boundary")

    monkeypatch.setattr(apply_module, "_publish_json", publish_then_external_edit)
    with pytest.raises(ApplyError, match="after publication boundary"):
        apply_plan(
            plan,
            db,
            data,
            db_bak,
            data_bak,
            lock_path=lock,
            journal_path=journal,
            confirm=True,
            plan_sha256=canonical_plan_sha256(plan),
        )

    external_bytes = b'{"external":"after-publication"}\n'
    assert data.read_bytes() == external_bytes
    with pytest.raises(ApplyError, match="JSON target ownership cannot be verified"):
        recover_interrupted_apply(journal, lock)
    assert data.read_bytes() == external_bytes
    assert journal.exists()


def test_maintenance_window_does_not_bypass_live_refusal(tmp_path):
    db, data, db_bak, data_bak = _fixture(tmp_path)
    plan = _plan(db, data)
    with pytest.raises(ApplyError, match="live"):
        apply_plan(
            plan,
            Path("agent/data/vinhlong360.db"),
            Path("web/data.json"),
            db_bak,
            data_bak,
            lock_path=tmp_path / "apply.lock",
            journal_path=tmp_path / "apply.journal.json",
            maintenance_mode=True,
            confirm=True,
            plan_sha256=canonical_plan_sha256(plan),
        )
