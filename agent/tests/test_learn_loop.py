"""
Tests for learn_loop.py — self-learning feedback loop.
"""

import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import learn_loop


class TestFeedbackRecording:
    """Test feedback recording and processing."""

    def test_record_positive_feedback(self, tmp_path):
        feedback_file = tmp_path / "feedback_history.json"
        feedback_file.write_text("[]")
        with patch.object(learn_loop, 'FEEDBACK_FILE', feedback_file):
            learn_loop.record_feedback(
                query="Cam sành ở đâu?",
                rating=1,
                entity_id="cam-sanh-vinh-long"
            )
            feedback = json.loads(feedback_file.read_text(encoding="utf-8"))
            assert len(feedback) >= 1
            assert feedback[-1]["rating"] == 1

    def test_record_negative_feedback(self, tmp_path):
        feedback_file = tmp_path / "feedback_history.json"
        feedback_file.write_text("[]")
        with patch.object(learn_loop, 'FEEDBACK_FILE', feedback_file):
            learn_loop.record_feedback(
                query="Sai rồi",
                rating=0,
                entity_id="bun-mam"
            )
            feedback = json.loads(feedback_file.read_text(encoding="utf-8"))
            assert feedback[-1]["rating"] == 0


class TestLearningStatus:
    """Test learning status reporting."""

    def test_status_returns_dict(self):
        status = learn_loop.learning_status()
        assert isinstance(status, dict)
        assert "knowledge_gaps" in status
        assert "feedback_total" in status
        assert "recent_learning" in status


class TestProcessFeedbackBatch:
    """Test batch feedback processing."""

    def test_no_feedback_no_crash(self, tmp_path):
        feedback_file = tmp_path / "feedback_history.json"
        feedback_file.write_text("[]")
        with patch.object(learn_loop, 'FEEDBACK_FILE', feedback_file):
            result = learn_loop.process_feedback_batch()
            assert isinstance(result, dict)
            assert result.get("total_feedback", 0) == 0


def test_persist_new_entities_preserves_concurrent_fields(tmp_path, monkeypatch):
    data_path = tmp_path / "data.json"
    original = {
        "entities": [{"id": "existing", "name": "Existing", "type": "dish",
                      "attributes": {"phone": "0900000000"}}],
        "relationships": [],
        "itineraries": [],
    }
    data_path.write_text(json.dumps(original), encoding="utf-8")
    stale = deepcopy(original)
    latest = deepcopy(original)
    latest["entities"][0]["attributes"]["phone"] = "0911111111"
    data_path.write_text(json.dumps(latest), encoding="utf-8")
    saved_to_db = []

    monkeypatch.setattr(learn_loop, "DATA_JSON", data_path)
    monkeypatch.setitem(
        sys.modules,
        "database",
        SimpleNamespace(db=SimpleNamespace(upsert_entity=lambda entity: saved_to_db.append(deepcopy(entity)))),
    )
    monkeypatch.setitem(sys.modules, "knowledge", SimpleNamespace(reload=lambda: None))

    added = learn_loop._persist_new_entities(
        stale,
        [{"id": "new-entity", "name": "New", "type": "dish", "attributes": {}}],
    )

    persisted = json.loads(data_path.read_text(encoding="utf-8"))
    assert added == 1
    assert persisted["entities"][0]["attributes"]["phone"] == "0911111111"
    assert {entity["id"] for entity in persisted["entities"]} == {"existing", "new-entity"}
    assert [entity["id"] for entity in saved_to_db] == ["new-entity"]


def test_persist_enrichments_skips_concurrently_changed_summary(tmp_path, monkeypatch):
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps({
        "entities": [{"id": "existing", "name": "Existing", "type": "dish", "summary": "fresh"}],
        "relationships": [],
        "itineraries": [],
    }), encoding="utf-8")
    monkeypatch.setattr(learn_loop, "DATA_JSON", data_path)

    applied = learn_loop._persist_enrichments({
        "existing": ("", "generated summary", "2026-07-12"),
    })

    persisted = json.loads(data_path.read_text(encoding="utf-8"))
    assert applied == 0
    assert persisted["entities"][0]["summary"] == "fresh"


def test_persist_new_entities_rechecks_names_and_near_duplicates(tmp_path, monkeypatch):
    data_path = tmp_path / "data.json"
    current = {
        "entities": [{"id": "existing", "name": "Quán Cây Dừa", "type": "dish", "attributes": {}}],
        "relationships": [],
        "itineraries": [],
    }
    data_path.write_text(json.dumps(current), encoding="utf-8")
    saved_to_db = []
    monkeypatch.setattr(learn_loop, "DATA_JSON", data_path)
    monkeypatch.setitem(
        sys.modules,
        "database",
        SimpleNamespace(db=SimpleNamespace(upsert_entity=lambda entity: saved_to_db.append(entity))),
    )
    monkeypatch.setitem(sys.modules, "knowledge", SimpleNamespace(reload=lambda: None))

    added = learn_loop._persist_new_entities(
        {"entities": [], "relationships": [], "itineraries": []},
        [
            {"id": "same-name", "name": "QUÁN CÂY DỪA", "type": "dish", "attributes": {}},
            {"id": "near-name", "name": "Quán Cây Dừa Vĩnh Long", "type": "dish", "attributes": {}},
        ],
    )

    persisted = json.loads(data_path.read_text(encoding="utf-8"))
    assert added == 0
    assert [entity["id"] for entity in persisted["entities"]] == ["existing"]
    assert saved_to_db == []
