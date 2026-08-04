"""Source guards for scheduler erasure boundaries."""

from __future__ import annotations

from pathlib import Path


SCHEDULER = Path(__file__).resolve().parents[1] / "scheduler.py"


def test_scheduler_contains_no_account_delete_sql():
    source = SCHEDULER.read_text(encoding="utf-8")
    assert "DELETE FROM users" not in source
    assert "UPDATE users SET erasure_due_at" not in source


def test_scheduler_delegates_lifecycle_to_orchestrators():
    source = SCHEDULER.read_text(encoding="utf-8")
    assert "erase_due_accounts" in source
    assert "retry_pending_quarantines" in source
    assert "ERASURE_AUDIT_ONLY" in source
    assert "ACCOUNT_ERASURE_DEADLINE_DAYS" in source


def test_account_cleanup_no_longer_owns_user_erasure_interval():
    source = SCHEDULER.read_text(encoding="utf-8")
    cleanup = source.split("def task_session_cleanup", 1)[1].split(
        "def _hard_delete_stale_posts", 1
    )[0]
    assert "deleted_at" not in cleanup
    assert "INTERVAL '30 days'" not in cleanup
