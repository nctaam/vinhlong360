"""
Tests for scheduler.py — task scheduling engine.
"""

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scheduler import ScheduledTask, TASKS, scheduler_status, sync_data_json_to_js


class TestScheduledTask:
    """Test individual scheduled task behavior."""

    def test_should_run_initially(self):
        task = ScheduledTask("test", lambda: None, interval_seconds=60)
        assert task.should_run() is True  # Never run before

    def test_can_delay_initial_run(self):
        task = ScheduledTask("test", lambda: None, interval_seconds=60, run_immediately=False)
        assert task.should_run() is False
        assert task.next_run_after > time.time()

    def test_should_not_run_after_recent(self):
        task = ScheduledTask("test", lambda: None, interval_seconds=3600)
        task.last_run = time.time()
        assert task.should_run() is False

    def test_disabled_never_runs(self):
        task = ScheduledTask("test", lambda: None, interval_seconds=0, enabled=False)
        assert task.should_run() is False

    def test_run_tracks_count(self):
        counter = {"n": 0}
        def inc():
            counter["n"] += 1
        task = ScheduledTask("test", inc, interval_seconds=60)
        task.run()
        assert task.run_count == 1
        assert counter["n"] == 1
        assert task.last_error is None

    def test_run_captures_error(self):
        def fail():
            raise ValueError("boom")
        task = ScheduledTask("test", fail, interval_seconds=60)
        task.run()  # Should not raise
        assert task.last_error == "boom"
        assert task.run_count == 0  # Failed runs don't count

    def test_run_timing(self):
        def slow():
            time.sleep(0.1)
        task = ScheduledTask("test", slow, interval_seconds=60)
        task.run()
        assert task.last_run > 0


class TestTaskRegistry:
    """Test the global TASKS list."""

    def test_all_tasks_have_names(self):
        for task in TASKS:
            assert task.name, f"Task missing name: {task}"

    def test_all_tasks_have_functions(self):
        for task in TASKS:
            assert callable(task.func), f"Task {task.name} func not callable"

    def test_all_tasks_have_intervals(self):
        for task in TASKS:
            assert task.interval > 0, f"Task {task.name} has invalid interval"

    def test_expected_tasks_present(self):
        names = {t.name for t in TASKS}
        expected = {"auto-learn", "relationships", "data-sync", "analytics-cleanup", "learning-loop"}
        assert expected.issubset(names), f"Missing tasks: {expected - names}"

    def test_learning_loop_interval(self):
        import scheduler
        loop_task = next(t for t in TASKS if t.name == "learning-loop")
        assert loop_task.interval == scheduler.LEARNING_LOOP_INTERVAL  # env-driven (default 1h)

    def test_env_int_parsing(self):
        import scheduler
        assert scheduler._env_int("NONEXISTENT_VAR_XYZ", 1234) == 1234

    def test_env_int_floor(self):
        """Values below the 5-minute floor fall back to default (safety)."""
        import os
        import scheduler
        os.environ["TEST_LEARN_IVL"] = "10"
        try:
            assert scheduler._env_int("TEST_LEARN_IVL", 999) == 999
        finally:
            del os.environ["TEST_LEARN_IVL"]

    def test_discovery_task_present_with_adaptive_bounds(self):
        import scheduler
        t = next(t for t in TASKS if t.name == "continuous-discovery")
        assert scheduler.DISCOVERY_MIN_INTERVAL <= t.interval <= scheduler.DISCOVERY_MAX_INTERVAL


class TestSchedulerStatus:
    """Test status reporting."""

    def test_status_structure(self):
        status = scheduler_status()
        assert "running" in status
        assert "enabled" in status
        assert "run_startup_tasks" in status
        assert "autonomous_tasks_enabled" in status
        assert "tasks" in status
        assert isinstance(status["tasks"], list)

    def test_status_task_info(self):
        status = scheduler_status()
        for task_info in status["tasks"]:
            assert "name" in task_info
            assert "enabled" in task_info
            assert "interval_hours" in task_info
            assert "next_run_after" in task_info
            assert "run_count" in task_info


class TestDataSync:
    """Test data.json → data.js sync."""

    def test_sync_creates_js(self, sample_data, tmp_path):
        json_path = tmp_path / "data.json"
        js_path = tmp_path / "data.js"
        json_path.write_text(json.dumps(sample_data, ensure_ascii=False), encoding="utf-8")

        with patch.object(sys.modules['scheduler'], 'PROJECT_DIR', tmp_path):
            # Create web/ directory structure
            web_dir = tmp_path / "web"
            web_dir.mkdir()
            web_json = web_dir / "data.json"
            web_json.write_text(json.dumps(sample_data, ensure_ascii=False), encoding="utf-8")
            result = sync_data_json_to_js()
            assert result is True
            web_js = web_dir / "data.js"
            assert web_js.exists()
            content = web_js.read_text(encoding="utf-8")
            assert "window.VL_DATA" in content
            assert "entities: places.concat(items)" in content

    def test_sync_no_file(self, tmp_path):
        with patch.object(sys.modules['scheduler'], 'PROJECT_DIR', tmp_path):
            result = sync_data_json_to_js()
            assert result is False
