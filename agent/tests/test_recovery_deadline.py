"""TDD contracts for exact-deadline recovery and quarantine locking."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from threading import Event, Lock, Thread

import pytest

import data_lifecycle
import quarantine


UTC = timezone.utc
NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
DUE = NOW + timedelta(days=30)
USER_ID = "00000000-0000-0000-0000-000000000001"


class RecoveryDatabase:
    _ph = "%s"

    def __init__(self, timeline=None):
        self.user = {
            "id": USER_ID,
            "is_active": False,
            "deleted_at": NOW - timedelta(minutes=1),
            "erasure_due_at": DUE,
            "erasure_attempt_count": 2,
            "erasure_last_attempt_at": NOW - timedelta(minutes=2),
            "erasure_last_error_code": "STORE_UNAVAILABLE",
        }
        self.events: list[tuple] = []
        self.statements: list[str] = []
        self.timeline = timeline if timeline is not None else self.events
        self._lock = Lock()

    def initialize(self):
        return None

    @contextmanager
    def _conn(self, **_kwargs):
        self._lock.acquire()
        self.events.append(("begin",))
        self.timeline.append(("db_begin",))
        try:
            yield self
        except Exception:
            self.events.append(("rollback",))
            self.timeline.append(("db_rollback",))
            raise
        else:
            self.events.append(("commit",))
            self.timeline.append(("db_commit",))
        finally:
            self._lock.release()

    def _fetchone(self, _conn, sql, params=None):
        normalized = " ".join(sql.split())
        self.statements.append(normalized)
        if normalized.startswith("SELECT"):
            return dict(self.user)
        if normalized.startswith("UPDATE users"):
            if "SET deleted_at = NULL" in normalized:
                self.user.update(
                    deleted_at=None,
                    erasure_due_at=None,
                    erasure_attempt_count=0,
                    erasure_last_attempt_at=None,
                    erasure_last_error_code=None,
                    is_active=True,
                )
            elif "erasure_last_attempt_at" in normalized:
                self.user["erasure_last_attempt_at"] = params[0]
                self.user["erasure_last_error_code"] = None
            return dict(self.user)
        raise AssertionError(f"unexpected query: {normalized}")

    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row is not None else None


class Gate:
    def __init__(self, events):
        self.events = events

    def block_owner(self, owner_key):
        self.events.append(("block", owner_key))

    def unblock_owner(self, owner_key):
        self.events.append(("unblock", owner_key))


def _registry(store, started=None, release=None):
    def purge(owner_key):
        if started:
            started.set()
        if release:
            release.wait(timeout=2)
        store.pop(owner_key, None)
        return 1

    return data_lifecycle.LifecycleRegistry(
        [
            data_lifecycle.DataStorePolicy(
                name="hot_memory",
                classification="personal",
                purge=purge,
                verify=lambda owner_key: owner_key not in store,
                description="hot",
                quarantine_on_request=True,
            )
        ]
    )


def test_recovery_before_deadline_clears_metadata_and_unblocks_after_commit(monkeypatch):
    events = []
    db = RecoveryDatabase(events)
    monkeypatch.setattr(quarantine, "db", db)
    monkeypatch.setattr(quarantine, "owner_write_gate", Gate(events))

    result = quarantine.recover_account(USER_ID, now=NOW)

    assert result.recovered is True
    assert result.user["is_active"] is True
    assert db.user["deleted_at"] is None
    assert db.user["erasure_due_at"] is None
    assert db.user["erasure_attempt_count"] == 0
    assert db.user["erasure_last_error_code"] is None
    assert db.statements[0].endswith("FOR UPDATE")
    assert events.index(("db_commit",)) < events.index(("unblock", f"user:{USER_ID}"))


@pytest.mark.parametrize("now", [DUE, DUE + timedelta(microseconds=1)])
def test_recovery_at_or_after_exact_deadline_fails_closed(monkeypatch, now):
    db = RecoveryDatabase()
    events = []
    monkeypatch.setattr(quarantine, "db", db)
    monkeypatch.setattr(quarantine, "owner_write_gate", Gate(events))

    result = quarantine.recover_account(USER_ID, now=now)

    assert result.recovered is False
    assert result.user is None
    assert db.user["deleted_at"] is not None
    assert db.user["is_active"] is False
    assert events == []


def test_recovery_without_due_date_fails_closed(monkeypatch):
    db = RecoveryDatabase()
    db.user["erasure_due_at"] = None
    events = []
    monkeypatch.setattr(quarantine, "db", db)
    monkeypatch.setattr(quarantine, "owner_write_gate", Gate(events))

    result = quarantine.recover_account(USER_ID, now=NOW)

    assert result.recovered is False
    assert db.user["deleted_at"] is not None
    assert events == []


def test_recovery_does_not_reconstruct_quarantined_hot_memory(monkeypatch):
    db = RecoveryDatabase()
    owner_key = f"user:{USER_ID}"
    store = {owner_key: "private"}
    events = []
    monkeypatch.setattr(quarantine, "db", db)
    monkeypatch.setattr(quarantine, "owner_write_gate", Gate(events))
    monkeypatch.setattr(quarantine, "lifecycle_registry", _registry(store))

    assert quarantine.quarantine_account(USER_ID, now=NOW).success is True
    assert owner_key not in store
    assert quarantine.recover_account(USER_ID, now=NOW).recovered is True
    assert owner_key not in store


def test_recovery_waits_for_quarantine_row_lock_before_unblocking(monkeypatch):
    owner_key = f"user:{USER_ID}"
    store = {owner_key: "private"}
    started = Event()
    release = Event()
    events = []
    db = RecoveryDatabase(events)
    monkeypatch.setattr(quarantine, "db", db)
    monkeypatch.setattr(quarantine, "owner_write_gate", Gate(events))
    monkeypatch.setattr(
        quarantine, "lifecycle_registry", _registry(store, started, release)
    )

    quarantine_thread = Thread(
        target=quarantine.quarantine_account, args=(USER_ID,), kwargs={"now": NOW}
    )
    quarantine_thread.start()
    assert started.wait(timeout=1)

    recovery_result = []
    recovery_thread = Thread(
        target=lambda: recovery_result.append(
            quarantine.recover_account(USER_ID, now=NOW)
        )
    )
    recovery_thread.start()
    assert recovery_thread.is_alive()

    release.set()
    quarantine_thread.join(timeout=2)
    recovery_thread.join(timeout=2)

    assert not quarantine_thread.is_alive()
    assert not recovery_thread.is_alive()
    assert recovery_result[0].recovered is True
    assert store == {}
    assert events.index(("db_commit",)) < events.index(("unblock", owner_key))
