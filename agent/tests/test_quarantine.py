"""TDD contracts for immediate account quarantine and bounded retries."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from threading import Lock

import data_lifecycle
import quarantine
from owner_write_gate import owner_key_for_user


UTC = timezone.utc
NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
USER_ID = "00000000-0000-0000-0000-000000000001"
OTHER_ID = "00000000-0000-0000-0000-000000000002"
LATE_ID = "00000000-0000-0000-0000-000000000003"
ACTIVE_ID = "00000000-0000-0000-0000-000000000004"


def _deleted(user_id: str, *, due_at: datetime | None = None) -> dict:
    return {
        "id": user_id,
        "is_active": False,
        "deleted_at": NOW - timedelta(minutes=1),
        "erasure_due_at": due_at or NOW + timedelta(days=30),
        "erasure_attempt_count": 0,
        "erasure_last_attempt_at": None,
        "erasure_last_error_code": None,
    }


class FakeDatabase:
    _ph = "%s"

    def __init__(self, users: dict[str, dict]):
        self.users = users
        self.statements: list[str] = []
        self.events: list[tuple] = []
        self._lock = Lock()

    def initialize(self):
        return None

    @contextmanager
    def _conn(self, **_kwargs):
        self._lock.acquire()
        self.events.append(("begin",))
        try:
            yield self
        except Exception:
            self.events.append(("rollback",))
            raise
        else:
            self.events.append(("commit",))
        finally:
            self._lock.release()

    def _fetchone(self, _conn, sql, params=None):
        normalized = " ".join(sql.split())
        self.statements.append(normalized)
        if normalized.startswith("SELECT") and "FROM users" in normalized:
            user_id = str(params[0])
            row = self.users.get(user_id)
            return dict(row) if row else None
        if normalized.startswith("UPDATE users"):
            user_id = str(params[-1])
            row = self.users[user_id]
            if "erasure_last_error_code = NULL" in normalized:
                row["erasure_last_attempt_at"] = params[0]
                row["erasure_last_error_code"] = None
            elif "erasure_last_error_code" in normalized:
                row["erasure_last_attempt_at"] = params[0]
                row["erasure_last_error_code"] = params[1]
                row["erasure_attempt_count"] += 1
            elif "deleted_at = NULL" in normalized:
                row.update(
                    deleted_at=None,
                    erasure_due_at=None,
                    erasure_attempt_count=0,
                    erasure_last_attempt_at=None,
                    erasure_last_error_code=None,
                    is_active=True,
                )
            return dict(row)
        raise AssertionError(f"unexpected query: {normalized}")

    def _fetchall(self, _conn, sql, params=None):
        normalized = " ".join(sql.split())
        self.statements.append(normalized)
        assert "FROM users" in normalized
        now, limit = params
        rows = [
            row
            for row in self.users.values()
            if row["deleted_at"] is not None
            and row["erasure_due_at"] is not None
            and row["erasure_due_at"] > now
            and (
                row["erasure_last_attempt_at"] is None
                or row["erasure_last_error_code"] is not None
            )
        ]
        return [
            {"id": row["id"]}
            for row in sorted(rows, key=lambda item: item["id"])[: int(limit)]
        ]

    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row is not None else None


class FakeGate:
    def __init__(self):
        self.blocked: list[str] = []
        self.unblocked: list[str] = []

    def block_owner(self, owner_key: str):
        self.blocked.append(owner_key)

    def unblock_owner(self, owner_key: str):
        self.unblocked.append(owner_key)


def _policies(calls, *, failing_owner: str | None = None):
    names = (
        "hot_memory",
        "exact_cache",
        "semantic_cache",
        "semantic_leases",
        "pending_feedback_receipts",
    )
    policies = []
    for name in names:
        def purge(owner_key, *, _name=name):
            calls.append((_name, owner_key))
            if failing_owner == owner_key and _name == "semantic_cache":
                raise RuntimeError("raw adapter detail must not escape")
            return 1

        policies.append(
            data_lifecycle.DataStorePolicy(
                name=name,
                classification="pseudonymous",
                purge=purge,
                verify=lambda _owner: True,
                description=name,
                quarantine_on_request=True,
            )
        )
    return data_lifecycle.LifecycleRegistry(policies)


def test_quarantine_purges_only_immediate_registry_and_records_success(monkeypatch):
    db = FakeDatabase({USER_ID: _deleted(USER_ID)})
    calls = []
    gate = FakeGate()
    monkeypatch.setattr(quarantine, "db", db)
    monkeypatch.setattr(quarantine, "lifecycle_registry", _policies(calls))
    monkeypatch.setattr(quarantine, "owner_write_gate", gate)

    result = quarantine.quarantine_account(USER_ID, now=NOW)

    assert result.success is True
    assert result.error_code is None
    assert result.attempted_store_names == (
        "hot_memory",
        "exact_cache",
        "semantic_cache",
        "semantic_leases",
        "pending_feedback_receipts",
    )
    assert [name for name, owner in calls] == list(result.attempted_store_names)
    assert all(owner == owner_key_for_user(USER_ID) for _, owner in calls)
    assert gate.blocked == [owner_key_for_user(USER_ID)]
    assert db.users[USER_ID]["erasure_last_attempt_at"] == NOW
    assert db.users[USER_ID]["erasure_last_error_code"] is None
    assert any(statement.endswith("FOR UPDATE") for statement in db.statements)
    assert db.events[-1] == ("commit",)


def test_quarantine_failure_keeps_account_disabled_and_records_bounded_error(monkeypatch):
    db = FakeDatabase({USER_ID: _deleted(USER_ID)})
    calls = []
    gate = FakeGate()
    monkeypatch.setattr(quarantine, "db", db)
    monkeypatch.setattr(
        quarantine,
        "lifecycle_registry",
        _policies(calls, failing_owner=owner_key_for_user(USER_ID)),
    )
    monkeypatch.setattr(quarantine, "owner_write_gate", gate)

    result = quarantine.quarantine_account(USER_ID, now=NOW)

    assert result.success is False
    assert result.error_code == "STORE_UNAVAILABLE"
    assert db.users[USER_ID]["is_active"] is False
    assert db.users[USER_ID]["erasure_attempt_count"] == 1
    assert db.users[USER_ID]["erasure_last_error_code"] == "STORE_UNAVAILABLE"
    assert "raw adapter detail" not in repr(result)
    assert len(calls) == 5


def test_retry_selects_only_pending_predeadline_users_and_isolates_failures(monkeypatch):
    db = FakeDatabase(
        {
            USER_ID: _deleted(USER_ID),
            OTHER_ID: _deleted(OTHER_ID),
            LATE_ID: _deleted(LATE_ID, due_at=NOW),
            ACTIVE_ID: {
                **_deleted(ACTIVE_ID),
                "deleted_at": None,
                "is_active": True,
            },
        }
    )
    calls = []
    gate = FakeGate()
    monkeypatch.setattr(quarantine, "db", db)
    monkeypatch.setattr(
        quarantine,
        "lifecycle_registry",
        _policies(calls, failing_owner=owner_key_for_user(OTHER_ID)),
    )
    monkeypatch.setattr(quarantine, "owner_write_gate", gate)
    db.users[USER_ID]["erasure_last_attempt_at"] = NOW - timedelta(minutes=1)
    db.users[USER_ID]["erasure_last_error_code"] = "STORE_UNAVAILABLE"

    batch = quarantine.retry_pending_quarantines(now=NOW, limit=50)

    assert batch.selected_count == 2
    assert batch.completed_count == 1
    assert batch.failed_count == 1
    assert db.users[USER_ID]["erasure_last_error_code"] is None
    assert db.users[OTHER_ID]["erasure_last_error_code"] == "STORE_UNAVAILABLE"
    assert db.users[LATE_ID]["erasure_attempt_count"] == 0
    assert db.users[ACTIVE_ID]["erasure_attempt_count"] == 0


def test_retry_audit_only_does_not_purge_or_update_attempt_metadata(monkeypatch):
    db = FakeDatabase({USER_ID: _deleted(USER_ID)})
    calls = []
    monkeypatch.setattr(quarantine, "db", db)
    monkeypatch.setattr(quarantine, "lifecycle_registry", _policies(calls))

    before = dict(db.users[USER_ID])
    batch = quarantine.retry_pending_quarantines(now=NOW, audit_only=True)

    assert batch.audit_only is True
    assert batch.selected_count == 1
    assert batch.completed_count == 0
    assert calls == []
    assert db.users[USER_ID] == before
