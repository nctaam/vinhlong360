"""Scheduler contracts for audit-only account erasure lifecycle runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from threading import Event, Thread

import scheduler


UTC = timezone.utc
NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
USER_ID = "00000000-0000-0000-0000-000000000001"


class Result:
    selected_count = 2
    completed_count = 0
    failed_count = 0
    overdue_count = 2

    def to_dict(self):
        return {
            "selected_count": self.selected_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "overdue_count": self.overdue_count,
            "audit_only": True,
            "error_code": None,
        }


def test_account_erasure_task_delegates_audit_only_and_updates_status(monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler, "_utc_now", lambda: NOW, raising=False)
    monkeypatch.setattr(
        scheduler,
        "_legacy_deadline_impact",
        lambda _now: {
            "legacy_missing_deadline_count": 3,
            "earliest_due_at": "2026-06-01T12:00:00+00:00",
            "latest_due_at": "2026-07-01T12:00:00+00:00",
        },
        raising=False,
    )

    def run_erasure(*, now, limit, audit_only):
        calls.append((now, limit, audit_only))
        return Result()

    monkeypatch.setattr(scheduler, "erase_due_accounts", run_erasure, raising=False)
    monkeypatch.setattr(scheduler.settings, "ERASURE_AUDIT_ONLY", True, raising=False)
    monkeypatch.setattr(
        scheduler.settings,
        "ERASURE_ACTIVATION_ENABLED",
        False,
        raising=False,
    )

    result = scheduler.task_account_erasure()

    assert calls == [(NOW, 50, True)]
    assert result["audit_only"] is True
    assert result["due_count"] == 2
    assert result["overdue_count"] == 2
    assert result["legacy_missing_deadline_count"] == 3
    assert USER_ID not in json.dumps(result, sort_keys=True)


def test_erasure_mutation_requires_separate_activation_setting(monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler, "_utc_now", lambda: NOW, raising=False)
    monkeypatch.setattr(
        scheduler,
        "_legacy_deadline_impact",
        lambda _now: {"legacy_missing_deadline_count": 0},
        raising=False,
    )
    monkeypatch.setattr(
        scheduler,
        "erase_due_accounts",
        lambda **kwargs: calls.append(kwargs) or Result(),
        raising=False,
    )
    monkeypatch.setattr(scheduler.settings, "ERASURE_AUDIT_ONLY", False, raising=False)
    monkeypatch.setattr(
        scheduler.settings,
        "ERASURE_ACTIVATION_ENABLED",
        False,
        raising=False,
    )

    scheduler.task_account_erasure()

    assert calls[0]["audit_only"] is True


def test_quarantine_retry_uses_same_safe_gate(monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler, "_utc_now", lambda: NOW, raising=False)
    monkeypatch.setattr(
        scheduler,
        "retry_pending_quarantines",
        lambda **kwargs: calls.append(kwargs) or {"audit_only": kwargs["audit_only"]},
        raising=False,
    )
    monkeypatch.setattr(scheduler.settings, "ERASURE_AUDIT_ONLY", True, raising=False)

    result = scheduler.task_quarantine_retry()

    assert calls == [{"now": NOW, "limit": 50, "audit_only": True}]
    assert result["audit_only"] is True


def test_lifecycle_tasks_are_five_minute_startup_catchup_tasks():
    tasks = {task.name: task for task in scheduler.TASKS}

    assert tasks["account-erasure"].interval == 300
    assert tasks["quarantine-retry"].interval == 300
    assert tasks["account-erasure"].next_run_after == 0
    assert tasks["quarantine-retry"].next_run_after == 0


def test_scheduler_status_exposes_subject_free_erasure_state():
    status = scheduler.scheduler_status()["erasure"]

    assert {
        "audit_only",
        "last_run_at",
        "last_result",
        "due_count",
        "overdue_count",
        "legacy_missing_deadline_count",
        "legacy_deadline_impact",
    } <= set(status)
    assert USER_ID not in json.dumps(status, sort_keys=True)


def test_lifecycle_tasks_are_single_flight(monkeypatch):
    started = Event()
    release = Event()
    calls = []

    def blocked(**_kwargs):
        calls.append("started")
        started.set()
        release.wait(timeout=2)
        return Result()

    monkeypatch.setattr(scheduler, "_utc_now", lambda: NOW, raising=False)
    monkeypatch.setattr(scheduler, "erase_due_accounts", blocked, raising=False)
    monkeypatch.setattr(scheduler, "_legacy_deadline_impact", lambda _now: {}, raising=False)
    monkeypatch.setattr(scheduler.settings, "ERASURE_AUDIT_ONLY", True, raising=False)

    first = Thread(target=scheduler.task_account_erasure)
    first.start()
    assert started.wait(timeout=1)
    second = scheduler.task_account_erasure()
    release.set()
    first.join(timeout=2)

    assert second["status"] == "already_running"
    assert calls == ["started"]
