"""
Tests for scheduler.py — task scheduling engine.
"""

import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scheduler import (
    ScheduledTask,
    TASKS,
    scheduler_status,
    task_cleanup_feedback_receipts,
)


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
        expected = {
            "auto-learn",
            "relationships",
            "analytics-cleanup",
            "feedback-receipt-cleanup",
            "learning-loop",
        }
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


class TestFeedbackReceiptCleanup:
    def test_cleanup_is_bounded(self, monkeypatch):
        import feedback_policy

        calls = []
        monkeypatch.setattr(
            feedback_policy,
            "cleanup_expired_feedback_receipts",
            lambda *, limit: calls.append(limit) or 17,
        )

        assert task_cleanup_feedback_receipts() == 17
        assert calls == [500]

    def test_cleanup_failure_logs_stable_code(self, monkeypatch, caplog):
        import feedback_policy

        def fail_cleanup(*, limit):
            raise feedback_policy.FeedbackUnavailable("raw db secret@example.com")

        monkeypatch.setattr(
            feedback_policy,
            "cleanup_expired_feedback_receipts",
            fail_cleanup,
        )
        with caplog.at_level("ERROR", logger="scheduler"):
            assert task_cleanup_feedback_receipts() == 0

        output = "\n".join(record.getMessage() for record in caplog.records)
        assert "FEEDBACK_RECEIPT_CLEANUP_FAILED" in output
        assert "secret@example.com" not in output


# ── Task 8: the case notification dispatcher runs here, inert by default ──

def test_case_outbox_is_a_registered_task():
    import scheduler

    names = [task.name for task in scheduler.TASKS]
    assert "case-outbox" in names
    task = next(task for task in scheduler.TASKS if task.name == "case-outbox")
    assert task.interval == 60


def test_case_outbox_does_nothing_while_the_kernel_flag_is_off(monkeypatch):
    import scheduler
    from types import SimpleNamespace

    monkeypatch.setitem(
        sys.modules, "config",
        SimpleNamespace(settings=SimpleNamespace(CASE_KERNEL_ENABLED=False)),
    )

    # No database, no provider, no exception: a disabled capability is a no-op.
    assert scheduler.task_case_outbox() is None


def test_a_dispatcher_failure_cannot_escape_into_the_scheduler_loop(monkeypatch):
    import scheduler
    from types import SimpleNamespace

    monkeypatch.setitem(
        sys.modules, "config",
        SimpleNamespace(settings=SimpleNamespace(
            CASE_KERNEL_ENABLED=True, CASE_KERNEL_ENCRYPTION_KEY="not-a-valid-key"
        )),
    )

    # A bad key blows up inside the task; unrelated jobs must not be affected.
    assert scheduler.task_case_outbox() is None


def test_case_lifecycle_cleanup_is_a_no_op_while_the_kernel_sleeps(monkeypatch):
    import scheduler as scheduler_module
    from config import settings

    monkeypatch.setattr(settings, "CASE_KERNEL_ENABLED", False, raising=False)

    # No kernel, no shelves to walk — and above all, no database touched.
    assert scheduler_module.task_case_lifecycle_cleanup() == 0


def test_case_lifecycle_cleanup_is_scheduled_daily():
    import scheduler as scheduler_module

    task = next(t for t in scheduler_module.TASKS if t.name == "case-lifecycle-cleanup")

    assert task.interval == 24 * 3600


def test_the_promise_watch_stays_asleep_while_the_case_flags_are_off(monkeypatch):
    import scheduler
    from config import settings

    monkeypatch.setattr(settings, "CASE_KERNEL_ENABLED", False, raising=False)

    # Every case task is inert by default; this one is new and must be no
    # different, because it writes to cases and creates supervisor work.
    assert scheduler.task_case_promise_watch() == 0


def test_the_promise_watch_is_registered_and_runs_often_enough_to_matter():
    import scheduler

    task = next(t for t in scheduler.TASKS if t.name == "case-promise-watch")

    # A breach that nobody notices for a day is a promise nobody kept. Ten
    # minutes is the cadence the queue needs to sort late work to the top.
    assert task.interval <= 900
    assert task.func is scheduler.task_case_promise_watch
