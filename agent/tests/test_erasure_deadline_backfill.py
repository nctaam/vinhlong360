"""Dry-run and backup-gated legacy deadline backfill contracts."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import scripts.backfill_erasure_deadlines as backfill


UTC = timezone.utc
NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
USER_ID = "00000000-0000-0000-0000-000000000001"


class FakeDatabase:
    _ph = "%s"
    _use_pg = True

    def __init__(self):
        self.writes = []
        self.rows = [
            {
                "id": USER_ID,
                "deleted_at": NOW - timedelta(days=40),
                "erasure_due_at": None,
            }
        ]

    @contextmanager
    def _conn(self, **_kwargs):
        yield self

    def _fetchall(self, _conn, _sql, _params):
        return list(self.rows)

    def _execute(self, _conn, sql, params):
        self.writes.append((sql, params))
        return None

    @staticmethod
    def _row_to_dict(row):
        return dict(row)


class BrokenDatabase(FakeDatabase):
    @contextmanager
    def _conn(self, **_kwargs):
        raise RuntimeError("database password=secret@example.com")
        yield self


def test_report_derives_deadlines_without_writing(monkeypatch):
    db = FakeDatabase()
    monkeypatch.setattr(backfill, "db", db)

    report = backfill.build_backfill_report(now=NOW, db_obj=db)

    expected = NOW - timedelta(days=10)
    assert report["legacy_missing_deadline_count"] == 1
    assert report["earliest_due_at"] == expected.isoformat()
    assert report["latest_due_at"] == expected.isoformat()
    assert db.writes == []


def test_report_db_failure_is_bounded_and_subject_free():
    report = backfill.build_backfill_report(now=NOW, db_obj=BrokenDatabase())

    assert report == {
        "legacy_missing_deadline_count": 0,
        "earliest_due_at": None,
        "latest_due_at": None,
        "error_code": "DB_CONSTRAINT",
    }


def test_apply_requires_backup_evidence_and_is_not_default(monkeypatch):
    db = FakeDatabase()
    monkeypatch.setattr(backfill, "db", db)

    assert backfill.main(["--apply"]) != 0
    assert db.writes == []


def test_apply_updates_only_missing_deadlines_with_backup(monkeypatch, tmp_path):
    db = FakeDatabase()
    backup = tmp_path / "backup-manifest.json"
    backup.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(backfill, "db", db)
    monkeypatch.setattr(backfill, "_utc_now", lambda: NOW, raising=False)

    assert backfill.main(["--apply", "--backup-evidence", str(backup)]) == 0
    assert len(db.writes) == 1
    assert "erasure_due_at" in db.writes[0][0]
