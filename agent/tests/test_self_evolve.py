"""
Tests for the eval-gated self-evolution harness:
  self_eval.py (fitness), kb_versioning.py (snapshot/rollback), self_evolve.py (gate).
"""

import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import self_eval
import kb_versioning
import self_evolve


class TestIsRegression:
    """Unit tests for the regression decision (no KB needed)."""

    def test_no_regression_when_equal(self):
        f = {"composite": 0.9, "recall_at_5": 1.0, "dup_ratio": 0.01}
        regressed, _ = self_eval.is_regression(f, dict(f))
        assert regressed is False

    def test_no_regression_on_improvement(self):
        before = {"composite": 0.8, "recall_at_5": 0.9, "dup_ratio": 0.02}
        after = {"composite": 0.9, "recall_at_5": 1.0, "dup_ratio": 0.01}
        regressed, _ = self_eval.is_regression(before, after)
        assert regressed is False

    def test_regression_on_composite_drop(self):
        before = {"composite": 0.9, "recall_at_5": 1.0, "dup_ratio": 0.01}
        after = {"composite": 0.85, "recall_at_5": 1.0, "dup_ratio": 0.01}
        regressed, reason = self_eval.is_regression(before, after)
        assert regressed is True
        assert "composite" in reason

    def test_regression_on_recall_hard_drop(self):
        before = {"composite": 0.9, "recall_at_5": 1.0, "dup_ratio": 0.01}
        # composite barely moves but recall craters → hard guardrail
        after = {"composite": 0.895, "recall_at_5": 0.9, "dup_ratio": 0.01}
        regressed, reason = self_eval.is_regression(before, after)
        assert regressed is True
        assert "recall" in reason

    def test_regression_on_duplicate_spike(self):
        before = {"composite": 0.9, "recall_at_5": 1.0, "dup_ratio": 0.01}
        after = {"composite": 0.9, "recall_at_5": 1.0, "dup_ratio": 0.05}
        regressed, reason = self_eval.is_regression(before, after)
        assert regressed is True
        assert "duplicate" in reason

    def test_small_composite_drop_within_epsilon(self):
        before = {"composite": 0.900, "recall_at_5": 1.0, "dup_ratio": 0.01}
        after = {"composite": 0.895, "recall_at_5": 1.0, "dup_ratio": 0.01}  # -0.005 < epsilon
        regressed, _ = self_eval.is_regression(before, after)
        assert regressed is False


class TestKbHealth:
    def test_health_structure(self):
        entities = {
            "a": {"id": "a", "name": "Cam sành", "type": "product", "summary": "x" * 30, "confidence": 0.9},
            "b": {"id": "b", "name": "Bún mắm", "type": "dish", "summary": "y" * 30, "confidence": 0.8},
            "p": {"id": "p", "name": "Xã A", "type": "place"},  # excluded
        }
        h = self_eval._kb_health(entities)
        assert h["entities"] == 2  # place excluded
        assert h["summary_coverage"] == 1.0
        assert 0.8 <= h["avg_confidence"] <= 0.9

    def test_duplicate_detection(self):
        entities = {
            "a": {"id": "a", "name": "Cam sành", "type": "product", "summary": "x" * 30},
            "b": {"id": "b", "name": "Cam Sành", "type": "product", "summary": "y" * 30},  # dup name
        }
        h = self_eval._kb_health(entities)
        assert h["dup_ratio"] > 0

    def test_provisional_counted(self):
        entities = {
            "a": {"id": "a", "name": "X", "type": "product", "summary": "x" * 30, "status": "provisional"},
            "b": {"id": "b", "name": "Y", "type": "product", "summary": "y" * 30},
        }
        h = self_eval._kb_health(entities)
        assert h["provisional_ratio"] == 0.5


class TestKbVersioning:
    def test_snapshot_rollback_roundtrip(self, tmp_path, monkeypatch):
        # Redirect snapshot dir + data.json to temp
        data_json = tmp_path / "data.json"
        snap_dir = tmp_path / "snaps"
        snap_dir.mkdir()
        original = {"entities": [{"id": "a", "name": "A"}], "relationships": [], "itineraries": []}
        data_json.write_text(json.dumps(original), encoding="utf-8")

        monkeypatch.setattr(kb_versioning, "DATA_JSON", data_json)
        monkeypatch.setattr(kb_versioning, "SNAP_DIR", snap_dir)
        monkeypatch.setattr(kb_versioning, "MANIFEST", snap_dir / "manifest.json")

        # Snapshot
        snap = kb_versioning.snapshot("test", snapshot_id="snap_test_1")
        assert snap is not None
        assert snap["entity_count"] == 1

        # Mutate data.json (simulate a bad self-change)
        bad = {"entities": [{"id": "a"}, {"id": "b"}, {"id": "c"}], "relationships": [], "itineraries": []}
        data_json.write_text(json.dumps(bad), encoding="utf-8")
        assert len(json.loads(data_json.read_text())["entities"]) == 3

        # Rollback
        result = kb_versioning.rollback("snap_test_1")
        assert result["restored"] is True
        restored = json.loads(data_json.read_text())
        assert len(restored["entities"]) == 1  # back to original

    def test_rollback_no_snapshots(self, tmp_path, monkeypatch):
        monkeypatch.setattr(kb_versioning, "SNAP_DIR", tmp_path / "empty")
        monkeypatch.setattr(kb_versioning, "MANIFEST", tmp_path / "empty" / "manifest.json")
        (tmp_path / "empty").mkdir()
        result = kb_versioning.rollback()
        assert result["restored"] is False


class TestGuardedEvolve:
    """Test the gate keeps good changes and rolls back regressions (mocked fitness)."""

    def test_keeps_good_change(self, monkeypatch, tmp_path):
        fitnesses = [
            {"composite": 0.90, "recall_at_5": 1.0, "dup_ratio": 0.01},  # before
            {"composite": 0.92, "recall_at_5": 1.0, "dup_ratio": 0.01},  # after (better)
        ]
        monkeypatch.setattr(self_evolve.self_eval, "compute_fitness", lambda *a, **k: fitnesses.pop(0))
        monkeypatch.setattr(self_evolve.kb_versioning, "snapshot", lambda **k: {"id": "s1"})
        monkeypatch.setattr(self_evolve.knowledge, "reload", lambda: None)
        monkeypatch.setattr(self_evolve, "AUDIT_LOG", tmp_path / "audit.jsonl")
        rolled = {"called": False}
        monkeypatch.setattr(self_evolve.kb_versioning, "rollback", lambda *a, **k: rolled.update(called=True))

        result = self_evolve.guarded_evolve("test", lambda: {"added": 3})
        assert result["decision"] == "kept"
        assert rolled["called"] is False

    def test_rolls_back_regression(self, monkeypatch, tmp_path):
        fitnesses = [
            {"composite": 0.90, "recall_at_5": 1.0, "dup_ratio": 0.01},  # before
            {"composite": 0.80, "recall_at_5": 1.0, "dup_ratio": 0.01},  # after (worse)
        ]
        monkeypatch.setattr(self_evolve.self_eval, "compute_fitness", lambda *a, **k: fitnesses.pop(0))
        monkeypatch.setattr(self_evolve.kb_versioning, "snapshot", lambda **k: {"id": "s1"})
        monkeypatch.setattr(self_evolve.knowledge, "reload", lambda: None)
        monkeypatch.setattr(self_evolve, "AUDIT_LOG", tmp_path / "audit.jsonl")
        rolled = {"called": False}
        monkeypatch.setattr(self_evolve.kb_versioning, "rollback",
                            lambda *a, **k: rolled.update(called=True) or {"restored": True})

        result = self_evolve.guarded_evolve("test", lambda: {"added": 99})
        assert result["decision"] == "rolled_back"
        assert rolled["called"] is True

    def test_rolls_back_on_apply_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(self_evolve.self_eval, "compute_fitness",
                            lambda *a, **k: {"composite": 0.9, "recall_at_5": 1.0, "dup_ratio": 0.01})
        monkeypatch.setattr(self_evolve.kb_versioning, "snapshot", lambda **k: {"id": "s1"})
        monkeypatch.setattr(self_evolve.knowledge, "reload", lambda: None)
        monkeypatch.setattr(self_evolve, "AUDIT_LOG", tmp_path / "audit.jsonl")
        rolled = {"called": False}
        monkeypatch.setattr(self_evolve.kb_versioning, "rollback",
                            lambda *a, **k: rolled.update(called=True) or {"restored": True})

        def boom():
            raise RuntimeError("apply failed")

        result = self_evolve.guarded_evolve("test", boom)
        assert result["decision"] == "rolled_back"
        assert "apply error" in result["reason"]
        assert rolled["called"] is True
