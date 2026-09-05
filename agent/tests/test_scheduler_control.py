"""Deterministic scheduler lease tests (SQLite only; not production proof)."""

from datetime import datetime, timedelta, timezone

import pytest

from scheduler_control import (
    LeaseNotOwned,
    claim_task_slot,
    finish_task_slot,
)
import database as database_module
import scheduler


NOW = datetime(2026, 9, 5, 8, 0, tzinfo=timezone.utc)


def test_only_one_owner_claims_a_task_slot(isolated_sqlite_db):
    first = claim_task_slot(
        isolated_sqlite_db,
        task_name="admin-digest",
        slot_key="2026-09-05T08:00Z",
        owner_id="worker-a",
        now=NOW,
        lease_seconds=60,
    )
    second = claim_task_slot(
        isolated_sqlite_db,
        task_name="admin-digest",
        slot_key="2026-09-05T08:00Z",
        owner_id="worker-b",
        now=NOW,
        lease_seconds=60,
    )
    assert first.acquired is True
    assert second.acquired is False
    assert second.lease_id == first.lease_id


def test_expired_lease_can_be_taken_over_but_stale_owner_cannot_finish(isolated_sqlite_db):
    first = claim_task_slot(
        isolated_sqlite_db,
        task_name="cleanup",
        slot_key="slot-1",
        owner_id="worker-a",
        now=NOW,
        lease_seconds=60,
    )
    takeover = claim_task_slot(
        isolated_sqlite_db,
        task_name="cleanup",
        slot_key="slot-1",
        owner_id="worker-b",
        now=NOW + timedelta(seconds=61),
        lease_seconds=60,
    )
    assert takeover.acquired is True
    assert takeover.lease_id != first.lease_id
    with pytest.raises(LeaseNotOwned):
        finish_task_slot(
            isolated_sqlite_db,
            lease_id=first.lease_id,
            outcome="success",
            finished_at=NOW + timedelta(seconds=62),
            receipt={"owner": "worker-a"},
        )


def test_finished_slot_is_not_run_twice(isolated_sqlite_db):
    claim = claim_task_slot(
        isolated_sqlite_db,
        task_name="digest",
        slot_key="slot-1",
        owner_id="worker-a",
        now=NOW,
        lease_seconds=60,
    )
    finish_task_slot(
        isolated_sqlite_db,
        lease_id=claim.lease_id,
        outcome="success",
        finished_at=NOW + timedelta(seconds=2),
        receipt={"count": 1},
    )
    replay = claim_task_slot(
        isolated_sqlite_db,
        task_name="digest",
        slot_key="slot-1",
        owner_id="worker-b",
        now=NOW + timedelta(seconds=120),
        lease_seconds=60,
    )
    assert replay.acquired is False


def test_scheduled_task_writes_success_receipt(isolated_sqlite_db, monkeypatch):
    monkeypatch.setattr(database_module, "db", isolated_sqlite_db)
    monkeypatch.setattr(scheduler, "_SCHEDULER_OWNER_ID", "worker-test")
    task = scheduler.ScheduledTask("receipt-test", lambda: {"ok": True}, interval_seconds=60, timeout=1)

    task.run()

    with isolated_sqlite_db._conn() as conn:
        row = isolated_sqlite_db._fetchone(
            conn,
            "SELECT status, outcome, receipt_json FROM scheduler_task_slots WHERE task_name = ?",
            ("receipt-test",),
        )
    record = isolated_sqlite_db._row_to_dict(row)
    assert record["status"] == "finished"
    assert record["outcome"] == "success"
    assert '"status": "success"' in record["receipt_json"]
