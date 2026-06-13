"""Tests for data_quality candidate queue loading."""

import json

import data_quality


def _write_queue(path):
    payload = {
        "counts": {"auto_apply": 1, "needs_review": 0, "reject": 0},
        "auto_apply": [
            {
                "entity_id": "entity-1",
                "field": "source",
                "suggested_value": {"title": "Source", "url": "https://example.com"},
                "stream": "source",
                "apply_policy": "auto_apply",
            }
        ],
        "needs_review": [],
        "reject": [],
        "schema_errors": [],
    }
    path.mkdir(parents=True, exist_ok=True)
    (path / data_quality.QUEUE_FILE).write_text(json.dumps(payload), encoding="utf-8")


def test_load_candidate_queue_uses_cached_file_by_default(tmp_path, monkeypatch):
    _write_queue(tmp_path)

    def fail_merge(_output_dir):
        raise AssertionError("merge should not run when cache exists and refresh is false")

    monkeypatch.setattr(data_quality, "merge_candidate_outputs", fail_merge)
    queue = data_quality.load_candidate_queue(tmp_path)

    assert queue["auto_apply"][0]["candidate_id"]
    assert queue["auto_apply"][0]["kind"] == "source"
    assert queue["cache"]["exists"] is True


def test_load_candidate_queue_refresh_rebuilds(tmp_path, monkeypatch):
    _write_queue(tmp_path)

    def fake_merge(_output_dir):
        return {"auto_apply": [], "needs_review": [], "reject": [], "counts": {}}

    monkeypatch.setattr(data_quality, "merge_candidate_outputs", fake_merge)
    queue = data_quality.load_candidate_queue(tmp_path, refresh=True)

    assert queue["auto_apply"] == []
    assert queue["cache"]["exists"] is True


def test_apply_candidates_records_history_and_rollback(tmp_path, monkeypatch):
    data_path = tmp_path / "data.json"
    data_js_path = tmp_path / "data.js"
    backup_dir = tmp_path / "backups"
    burst_dir = tmp_path / "burst"
    data_path.write_text(
        json.dumps({"entities": [{"id": "entity-1", "name": "Entity 1", "type": "product"}], "relationships": [], "itineraries": []}),
        encoding="utf-8",
    )

    queue = {
        "auto_apply": [
            {
                "entity_id": "entity-1",
                "field": "source",
                "suggested_value": {"title": "Evidence", "url": "https://example.com/evidence"},
                "stream": "source",
                "apply_policy": "auto_apply",
                "url_verified": True,
                "evidence_urls": ["https://example.com/evidence"],
                "confidence": 0.96,
            }
        ],
        "needs_review": [],
        "reject": [],
    }

    monkeypatch.setattr(data_quality, "DATA_PATH", data_path)
    monkeypatch.setattr(data_quality, "DATA_JS_PATH", data_js_path)
    monkeypatch.setattr(data_quality, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(data_quality, "BURST_DIR", burst_dir)
    monkeypatch.setattr(data_quality, "load_candidate_queue", lambda refresh=True: queue)

    result = data_quality.apply_candidates(dry_run=False)

    assert result["applied_count"] == 1
    assert result["changes"][0]["before"] is None
    assert result["changes"][0]["after"]["url"] == "https://example.com/evidence"
    updated = json.loads(data_path.read_text(encoding="utf-8"))
    assert updated["entities"][0]["source"]["url"] == "https://example.com/evidence"

    history = data_quality.load_apply_history(output_dir=burst_dir)
    assert history["total"] == 1
    assert history["history"][0]["batch_id"] == result["batch_id"]

    rollback = data_quality.rollback_apply(result["batch_id"], output_dir=burst_dir)

    restored = json.loads(data_path.read_text(encoding="utf-8"))
    assert "source" not in restored["entities"][0]
    assert rollback["status"] == "rolled_back"
    history_after = data_quality.load_apply_history(output_dir=burst_dir)
    assert history_after["total"] == 2
    assert history_after["history"][0]["record_type"] == "rollback"
