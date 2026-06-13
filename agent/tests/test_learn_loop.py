"""
Tests for learn_loop.py — self-learning feedback loop.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

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
