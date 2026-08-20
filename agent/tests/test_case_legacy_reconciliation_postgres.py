"""The ledger against the file, on a real database: replay, algebra, freeze.

Cutover rests on this: the ledger explains every source line, replaying an
import changes nothing, and the freeze marker survives anything short of the
database itself being lost.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database  # noqa: E402
from cases.legacy_import import (  # noqa: E402
    FREEZE_SOURCE,
    correction_writes_frozen,
    freeze_correction_writes,
    reconcile_import,
    shadow_import,
)
from cases.store import PostgresCaseStore  # noqa: E402




# One loopback-only rule for every suite that opens the disposable database.
from _pg_test_database import TEST_DATABASE_URL, pg_only  # noqa: E402


@pytest.fixture
def pg_store(tmp_path):
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(conn, "DELETE FROM legacy_intake_records", ())
        conn.commit()
    return PostgresCaseStore(adapter)


def _line(**overrides) -> str:
    base = {"ts": "2026-01-01T00:00:00+00:00", "target_id": "p-quan-com",
            "target_type": "stale_field", "field": "phone",
            "detail": "0270 333 4444", "status": "open"}
    base.update(overrides)
    return json.dumps(base, ensure_ascii=False)


def _source(tmp_path: Path) -> Path:
    path = tmp_path / "reports.jsonl"
    path.write_text("\n".join([
        _line(),
        _line(target_type="post", field=None, detail="bài xúc phạm"),
        "broken line",
        _line(),  # duplicate of line 1
        _line(field="images", detail="ảnh sai"),
    ]) + "\n", encoding="utf-8")
    return path


@pg_only
def test_an_import_lands_one_ledger_row_per_line(pg_store, tmp_path):
    source = _source(tmp_path)

    with pg_store.transaction() as transaction:
        shadow_import(source, transaction, dry_run=False)
        summary = transaction.legacy_intake_summary(str(source))

    assert summary["rows"] == 5
    assert summary["corrections"] == 1
    assert summary["duplicates"] == 1
    assert summary["unexplained"] == 0


@pg_only
def test_replaying_the_same_file_changes_nothing(pg_store, tmp_path):
    source = _source(tmp_path)

    with pg_store.transaction() as transaction:
        shadow_import(source, transaction, dry_run=False)
    with pg_store.transaction() as transaction:
        shadow_import(source, transaction, dry_run=False)
        summary = transaction.legacy_intake_summary(str(source))

    # The (source_file, source_line) key makes the second run a no-op, which is
    # what lets an interrupted import simply be run again.
    assert summary["rows"] == 5


@pg_only
def test_reconciliation_passes_when_the_ledger_explains_every_line(pg_store, tmp_path):
    source = _source(tmp_path)

    import hashlib

    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with pg_store.transaction() as transaction:
        shadow_import(source, transaction, dry_run=False)
    with pg_store.transaction() as transaction:
        outcome = reconcile_import(source, transaction, expected_digest=digest)

    assert outcome["passed"] is True
    assert outcome["digest_verified"] is True
    assert all(value is True for value in outcome["checks"].values())


@pg_only
def test_reconciliation_fails_cutover_when_the_ledger_is_short(pg_store, tmp_path):
    source = _source(tmp_path)

    with pg_store.transaction() as transaction:
        shadow_import(source, transaction, dry_run=False)
    # Somebody edits the source after the import: the walk and ledger diverge.
    with source.open("a", encoding="utf-8") as handle:
        handle.write(_line(field="hours", detail="7h-21h") + "\n")

    with pg_store.transaction() as transaction:
        outcome = reconcile_import(source, transaction)

    assert outcome["passed"] is False
    assert outcome["checks"]["ledger_rows_match"] is False


@pg_only
def test_the_freeze_marker_is_durable_and_idempotent(pg_store):
    with pg_store.transaction() as transaction:
        assert correction_writes_frozen(transaction) is False
        freeze_correction_writes(transaction)
        freeze_correction_writes(transaction)  # twice is a no-op, not an error

    # A new transaction — the marker is in the database, not in any process.
    with pg_store.transaction() as transaction:
        assert correction_writes_frozen(transaction) is True
        assert transaction.legacy_intake_summary(FREEZE_SOURCE)["rows"] == 1


@pg_only
def test_a_cutover_without_a_stated_digest_does_not_claim_to_have_checked(
    pg_store, tmp_path,
):
    source = _source(tmp_path)
    with pg_store.transaction() as transaction:
        shadow_import(source, transaction, dry_run=False)

    with pg_store.transaction() as transaction:
        outcome = reconcile_import(source, transaction)

    # This check used to be hardcoded True. legacy_intake_records stores no
    # digest, so there was never anything to compare against — the cutover proof
    # reported success for a property nothing had verified.
    assert outcome["checks"]["source_digest_unchanged"] is None
    assert outcome["digest_verified"] is False
    assert outcome["passed"] is False


@pg_only
def test_a_file_edited_after_import_fails_the_cutover(pg_store, tmp_path):
    import hashlib

    source = _source(tmp_path)
    reviewed = hashlib.sha256(source.read_bytes()).hexdigest()
    with pg_store.transaction() as transaction:
        shadow_import(source, transaction, dry_run=False)

    # Somebody edits the file between the review and the cutover.
    with source.open("a", encoding="utf-8") as handle:
        handle.write(_line(field="hours", detail="7h-21h") + chr(10))

    with pg_store.transaction() as transaction:
        outcome = reconcile_import(source, transaction, expected_digest=reviewed)

    assert outcome["checks"]["source_digest_unchanged"] is False
    assert outcome["passed"] is False
