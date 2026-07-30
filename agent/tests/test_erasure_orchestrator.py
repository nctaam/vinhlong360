"""TDD contracts for verified hard erasure and batch isolation."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import data_lifecycle
import erasure
from data_lifecycle import PurgeResult, VerificationResult


UTC = timezone.utc
NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
USER_ID = "00000000-0000-0000-0000-000000000001"
OTHER_ID = "00000000-0000-0000-0000-000000000002"


def _due(user_id: str) -> dict:
    return {
        "id": user_id,
        "is_active": False,
        "deleted_at": NOW - timedelta(days=30),
        "erasure_due_at": NOW - timedelta(seconds=1),
        "erasure_attempt_count": 0,
        "erasure_last_attempt_at": None,
        "erasure_last_error_code": None,
    }


class Cursor:
    def __init__(self, owner):
        self.owner = owner
        self.statements: list[tuple[str, tuple | None]] = []
        self.rowcount = 0
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        self.statements.append((normalized, params))
        self.rowcount = 0
        self._rows = []
        if "FROM users" in normalized and "COUNT" in normalized:
            self._rows = [(0,)]

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None


class Connection:
    def __init__(self, owner):
        self.owner = owner
        self.cursor_obj = Cursor(owner)

    def cursor(self, **_kwargs):
        return self.cursor_obj


class FakeDatabase:
    _ph = "%s"
    _use_pg = True

    def __init__(self, users: dict[str, dict]):
        self.users = users
        self.statements: list[str] = []
        self.events: list[tuple] = []
        self.fail_delete_once = False
        self.connections: list[Connection] = []

    def initialize(self):
        return None

    @contextmanager
    def _conn(self, **_kwargs):
        conn = Connection(self)
        self.connections.append(conn)
        self.events.append(("begin",))
        try:
            yield conn
        except Exception:
            self.events.append(("rollback",))
            raise
        else:
            self.events.append(("commit",))

    def _fetchone(self, conn, sql, params=None):
        normalized = " ".join(sql.split())
        self.statements.append(normalized)
        if normalized.startswith("SELECT") and "FROM users" in normalized:
            user_id = str(params[0])
            row = self.users.get(user_id)
            return dict(row) if row else None
        if normalized.startswith("UPDATE users"):
            user_id = str(params[-1])
            row = self.users[user_id]
            row["erasure_last_attempt_at"] = params[0]
            if "erasure_last_error_code = NULL" in normalized or "erasure_last_error_code" not in normalized:
                row["erasure_last_error_code"] = None
            else:
                row["erasure_last_error_code"] = params[1]
                row["erasure_attempt_count"] += 1
            return dict(row)
        raise AssertionError(f"unexpected fetchone: {normalized}")

    def _fetchall(self, _conn, sql, params=None):
        normalized = " ".join(sql.split())
        self.statements.append(normalized)
        now, limit = params
        rows = [
            row
            for row in self.users.values()
            if row["deleted_at"] is not None
            and row["erasure_due_at"] <= now
        ]
        return [
            {"id": row["id"], "erasure_due_at": row["erasure_due_at"]}
            for row in rows[: int(limit)]
        ]

    def _row_to_dict(self, row):
        return dict(row) if row is not None else None

    def delete_erased_user(self, conn, user_id, now):
        self.statements.append(
            "DELETE FROM users WHERE id::text = %s AND deleted_at IS NOT NULL "
            "AND erasure_due_at IS NOT NULL AND erasure_due_at <= %s"
        )
        if self.fail_delete_once:
            self.fail_delete_once = False
            raise RuntimeError("final transaction unavailable")
        row = self.users.get(str(user_id))
        if not row or row["deleted_at"] is None or row["erasure_due_at"] > now:
            return None
        return self.users.pop(str(user_id))


class Metric:
    def __init__(self):
        self.calls = []

    def inc(self, labels=None, amount=1):
        self.calls.append((labels, amount))


def _registry(calls, *, failing_owner=None, residual_owner=None):
    policies = []
    for name, classification in (("cold_memory", "personal"), ("memory_graph", "pseudonymous")):
        def purge(owner_key, *, _name=name):
            calls.append(("purge", _name, owner_key))
            if owner_key == failing_owner:
                return PurgeResult(_name, complete=False, error_code="STORE_UNAVAILABLE")
            return PurgeResult(_name, removed_count=1)

        def verify(owner_key, *, _name=name):
            calls.append(("verify", _name, owner_key))
            if owner_key == residual_owner:
                return VerificationResult(_name, absent=False, residual_count=1)
            return VerificationResult(_name, absent=True)

        policies.append(
            data_lifecycle.DataStorePolicy(
                name=name,
                classification=classification,
                purge=purge,
                verify=verify,
                description=name,
            )
        )
    policies.append(
        data_lifecycle.DataStorePolicy(
            name="deidentified_daily_rollups",
            classification="aggregate",
            purge=None,
            verify=None,
            description="aggregate",
            subject_linked=False,
            retained_fields=("date", "request_count"),
        )
    )
    return data_lifecycle.LifecycleRegistry(policies)


def _patch_common(monkeypatch, db, registry, calls):
    monkeypatch.setattr(erasure, "db", db)
    monkeypatch.setattr(erasure, "lifecycle_registry", registry)
    monkeypatch.setattr(
        erasure,
        "validate_lifecycle_registry",
        lambda _policies: (),
        raising=False,
    )
    monkeypatch.setattr(erasure, "validate_user_fk_actions", lambda _conn: ())
    monkeypatch.setattr(
        erasure,
        "scrub_user_references",
        lambda *_args, **_kwargs: calls.append(("scrub",)) or None,
    )
    for name in (
        "erasure_due_total",
        "erasure_completed_total",
        "erasure_failed_total",
        "erasure_overdue_total",
    ):
        monkeypatch.setattr(erasure.metrics, name, Metric())


def test_due_batch_isolates_failure_and_deletes_successful_user(monkeypatch):
    db = FakeDatabase({USER_ID: _due(USER_ID), OTHER_ID: _due(OTHER_ID)})
    calls = []
    registry = _registry(calls, failing_owner=f"user:{OTHER_ID}")
    _patch_common(monkeypatch, db, registry, calls)

    result = erasure.erase_due_accounts(now=NOW, limit=50)

    assert result.selected_count == 2
    assert result.completed_count == 1
    assert result.failed_count == 1
    assert USER_ID not in db.users
    assert db.users[OTHER_ID]["deleted_at"] is not None
    assert db.users[OTHER_ID]["erasure_last_error_code"] == "STORE_UNAVAILABLE"
    assert any(item[0] == "scrub" for item in calls)
    assert erasure.metrics.erasure_due_total.calls == [(None, 2)]
    assert erasure.metrics.erasure_overdue_total.calls == [(None, 2)]
    assert erasure.metrics.erasure_completed_total.calls == [(None, 1)]
    assert erasure.metrics.erasure_failed_total.calls == [
        ({"code": "STORE_UNAVAILABLE"}, 1)
    ]


def test_due_batch_isolates_unexpected_controller_exception(monkeypatch):
    db = FakeDatabase({USER_ID: _due(USER_ID), OTHER_ID: _due(OTHER_ID)})
    calls = []
    _patch_common(monkeypatch, db, _registry(calls), calls)
    attempted = []

    def erase_one(user_id, *, now, run_id=None):
        attempted.append(user_id)
        if user_id == USER_ID:
            raise RuntimeError("sensitive controller failure")
        return erasure.ErasureResult(
            status="completed",
            verified=True,
            run_id="safe-run",
        )

    monkeypatch.setattr(erasure, "erase_account", erase_one)

    result = erasure.erase_due_accounts(now=NOW, limit=50)

    assert attempted == [USER_ID, OTHER_ID]
    assert result.selected_count == 2
    assert result.completed_count == 1
    assert result.failed_count == 1
    assert "sensitive controller failure" not in repr(result)


def test_residual_store_blocks_final_delete_and_records_residual_code(monkeypatch):
    db = FakeDatabase({USER_ID: _due(USER_ID)})
    calls = []
    _patch_common(
        monkeypatch,
        db,
        _registry(calls, residual_owner=f"user:{USER_ID}"),
        calls,
    )

    result = erasure.erase_account(USER_ID, now=NOW)

    assert result.status == "failed"
    assert result.error_code == "RESIDUAL_DATA"
    assert result.verified is False
    assert USER_ID in db.users
    assert not any(item[0] == "scrub" for item in calls)


def test_invalid_lifecycle_registry_blocks_hard_erasure(monkeypatch):
    db = FakeDatabase({USER_ID: _due(USER_ID)})
    calls = []
    _patch_common(monkeypatch, db, _registry(calls), calls)
    monkeypatch.setattr(
        erasure,
        "validate_lifecycle_registry",
        lambda _policies: ("MISSING_ADAPTER:cold_memory",),
    )

    result = erasure.erase_account(USER_ID, now=NOW)

    assert result.status == "failed"
    assert result.error_code == "STORE_UNAVAILABLE"
    assert USER_ID in db.users
    assert db.users[USER_ID]["erasure_attempt_count"] == 1
    assert db.users[USER_ID]["erasure_last_error_code"] == "STORE_UNAVAILABLE"
    assert calls == []


def test_final_transaction_failure_repurges_idempotently_on_retry(monkeypatch):
    db = FakeDatabase({USER_ID: _due(USER_ID)})
    db.fail_delete_once = True
    calls = []
    _patch_common(monkeypatch, db, _registry(calls), calls)

    first = erasure.erase_account(USER_ID, now=NOW, run_id="stable-run")
    second = erasure.erase_account(USER_ID, now=NOW, run_id="stable-run")

    assert first.status == "failed"
    assert first.error_code == "DB_CONSTRAINT"
    assert second.verified is True
    assert first.run_id == second.run_id
    assert USER_ID not in db.users
    assert sum(1 for item in calls if item[0] == "purge") == 4
    assert USER_ID not in repr(first)


def test_retry_after_committed_delete_is_already_verified(monkeypatch):
    db = FakeDatabase({USER_ID: _due(USER_ID)})
    calls = []
    _patch_common(monkeypatch, db, _registry(calls), calls)

    first = erasure.erase_account(USER_ID, now=NOW, run_id="first-run")
    second = erasure.erase_account(USER_ID, now=NOW, run_id="retry-run")

    assert first.verified is True
    assert second.status == "already_erased"
    assert second.verified is True
    assert second.error_code is None


def test_audit_only_batch_is_read_only_and_results_are_subject_free(monkeypatch):
    db = FakeDatabase({USER_ID: _due(USER_ID)})
    calls = []
    _patch_common(monkeypatch, db, _registry(calls), calls)

    result = erasure.erase_due_accounts(now=NOW, limit=50, audit_only=True)

    assert result.audit_only is True
    assert result.selected_count == 1
    assert result.completed_count == 0
    assert calls == []
    assert USER_ID in db.users
    assert USER_ID not in repr(result)


def test_final_delete_uses_due_predicate_and_runs_fk_validation(monkeypatch):
    db = FakeDatabase({USER_ID: _due(USER_ID)})
    calls = []
    _patch_common(monkeypatch, db, _registry(calls), calls)

    result = erasure.erase_account(USER_ID, now=NOW)

    assert result.verified is True
    delete_sql = next(sql for sql in db.statements if sql.startswith("DELETE FROM users"))
    assert "deleted_at IS NOT NULL" in delete_sql
    assert "erasure_due_at <=" in delete_sql


def test_observability_hashes_subject_shaped_run_id(monkeypatch, caplog):
    db = FakeDatabase({USER_ID: _due(USER_ID)})
    calls = []
    _patch_common(
        monkeypatch,
        db,
        _registry(calls, failing_owner=f"user:{USER_ID}"),
        calls,
    )

    result = erasure.erase_account(
        USER_ID,
        now=NOW,
        run_id=USER_ID,
    )

    encoded = json.dumps(result.to_dict(), sort_keys=True)
    assert USER_ID not in encoded
    assert f"user:{USER_ID}" not in encoded
    assert USER_ID not in caplog.text
    assert f"user:{USER_ID}" not in caplog.text
    assert erasure.metrics.erasure_failed_total.calls == [
        ({"code": "STORE_UNAVAILABLE"}, 1)
    ]
