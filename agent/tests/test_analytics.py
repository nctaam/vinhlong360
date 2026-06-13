"""
Tests for analytics.py — query tracking and knowledge gap detection.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import analytics


class TestAnalyticsLoadSave:
    """Test analytics data persistence."""

    def test_default_data_structure(self):
        data = analytics._default_data()
        assert "queries" in data
        assert "entity_hits" in data
        assert "tool_usage" in data
        assert "unanswered" in data
        assert "daily_stats" in data
        assert "sessions" in data

    def test_load_nonexistent(self, tmp_path):
        """Loading from nonexistent file returns default."""
        with patch.object(analytics, 'ANALYTICS_FILE', tmp_path / "nope.json"):
            data = analytics._load()
            assert data == analytics._default_data()

    def test_load_empty_file(self, tmp_path):
        """Loading empty file returns default."""
        f = tmp_path / "empty.json"
        f.write_text("")
        with patch.object(analytics, 'ANALYTICS_FILE', f):
            data = analytics._load()
            assert data == analytics._default_data()

    def test_load_corrupt_file(self, tmp_path):
        """Loading corrupt JSON returns default."""
        f = tmp_path / "corrupt.json"
        f.write_text("{invalid json!!!")
        with patch.object(analytics, 'ANALYTICS_FILE', f):
            data = analytics._load()
            assert data == analytics._default_data()

    def test_save_and_load(self, tmp_path):
        """Data survives save/load cycle."""
        f = tmp_path / "test.json"
        with patch.object(analytics, 'ANALYTICS_FILE', f):
            data = analytics._default_data()
            data["sessions"] = 42
            analytics._save(data)
            loaded = analytics._load()
            assert loaded["sessions"] == 42


class TestTrackQuery:
    """Test query tracking."""

    def test_track_query(self, tmp_path):
        f = tmp_path / "analytics.json"
        with patch.object(analytics, 'ANALYTICS_FILE', f):
            analytics.track_query("Cam sành là gì?", tools_used=["search"], reply="Cam sành là loại trái cây nổi tiếng")
            data = analytics._load()
            assert len(data["queries"]) == 1
            assert data["queries"][0]["text"] == "Cam sành là gì?"
            assert data["queries"][0]["has_answer"] is True

    def test_track_multiple_queries(self, tmp_path):
        f = tmp_path / "analytics.json"
        with patch.object(analytics, 'ANALYTICS_FILE', f):
            analytics.track_query("Q1", tools_used=[], reply="A long reply that has enough content for marking as answered")
            analytics.track_query("Q2", tools_used=[], reply="short")
            data = analytics._load()
            assert len(data["queries"]) == 2


class TestEntityHits:
    """Test entity hit counting."""

    def test_track_entity_hit(self, tmp_path):
        f = tmp_path / "analytics.json"
        with patch.object(analytics, 'ANALYTICS_FILE', f):
            analytics.track_entity_hit("cam-sanh-vinh-long")
            analytics.track_entity_hit("cam-sanh-vinh-long")
            analytics.track_entity_hit("bun-mam")
            data = analytics._load()
            assert data["entity_hits"]["cam-sanh-vinh-long"] == 2
            assert data["entity_hits"]["bun-mam"] == 1
