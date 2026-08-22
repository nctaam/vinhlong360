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


def test_the_backfill_only_picks_entities_that_really_lack_coordinates():
    from learn_loop import _coord_backfill_candidates

    kb = {"entities": [
        {"id": "a", "type": "attraction", "name": "Có toạ độ", "coordinates": [10.2, 106.0]},
        {"id": "b", "type": "attraction", "name": "Thiếu toạ độ"},
        {"id": "c", "type": "place", "name": "Phường"},
        {"id": "d", "type": "attraction", "name": "Legacy", "coords": [9.9, 105.5]},
        {"id": "e", "type": "attraction"},
    ]}

    picked = [e["id"] for e in _coord_backfill_candidates(kb)]

    # Filtering on the dead `coords` key selected every non-place entity —
    # 1609 of which already had `coordinates` — so the 15-slot window went to
    # rows the write side would skip, and the ones truly missing never came up.
    assert picked == ["b"]


def test_freshly_learned_entities_are_offered_first():
    from learn_loop import _coord_backfill_candidates

    kb = {"entities": [
        {"id": "settled", "type": "attraction", "name": "Đã duyệt", "verified": 1},
        {"id": "fresh", "type": "attraction", "name": "Mới học", "verified": 0},
        {"id": "prov", "type": "attraction", "name": "Tạm", "status": "provisional"},
    ]}

    picked = [e["id"] for e in _coord_backfill_candidates(kb)]

    # `e.get("verified") is False` never matched the integer 0 the database and
    # the JSON actually store, so this ordering was dead code.
    assert picked[-1] == "settled"
    assert set(picked[:2]) == {"fresh", "prov"}


def test_the_backfill_writes_the_key_the_detail_page_reads():
    import inspect

    from learn_loop import _persist_backfilled_coords

    source = inspect.getsource(_persist_backfilled_coords)

    # web-nuxt/pages/dia-diem/[id].vue reads entity.coordinates. Writing the
    # legacy `coords` key meant a successful geocode still left the map empty.
    assert 'entity["coordinates"] = updates[entity["id"]]' in source
    assert 'entity["coords"] = updates' not in source
    # And data.json is an export: the public pages read the database, so the
    # work has to land there too, like the two sibling paths in this file.
    assert "db.upsert_entity(entity)" in source
