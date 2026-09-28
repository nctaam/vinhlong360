import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

import scripts.checks.reconciliation_journal as journal_module
from scripts.checks.reconciliation_journal import (
    JournalRecoveryError,
    JournalValidationError,
    load_journal,
    recover_journal,
    write_journal,
)
from scripts.checks.reconciliation_lock import ReconciliationLock


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path):
    db = tmp_path / "fixture.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE values_table (value TEXT)")
        conn.execute("INSERT INTO values_table VALUES ('before')")
    data = tmp_path / "data.json"
    data.write_text(json.dumps({"value": "before"}), encoding="utf-8")
    db_backup = tmp_path / "fixture.db.bak"
    data_backup = tmp_path / "data.json.bak"
    db_backup.write_bytes(db.read_bytes())
    data_backup.write_bytes(data.read_bytes())
    state = {
        "schemaVersion": 1,
        "operationId": "op-1",
        "phase": "prepared",
        "planSha256": "a" * 64,
        "sqlite": {
            "path": str(db),
            "beforeSha256": _sha(db),
            "backupPath": str(db_backup),
            "backupSha256": _sha(db_backup),
            "beforeIdentity": {"device": "d", "inode": "i", "size": db.stat().st_size},
        },
        "json": {
            "path": str(data),
            "beforeSha256": _sha(data),
            "backupPath": str(data_backup),
            "backupSha256": _sha(data_backup),
            "stagedPath": str(tmp_path / "data.json.staged"),
            "stagedSha256": "b" * 64,
            "beforeIdentity": {"device": "d", "inode": "j", "size": data.stat().st_size},
        },
    }
    return db, data, db_backup, data_backup, state


def test_write_load_and_monotonic_phase(tmp_path: Path):
    db, data, db_backup, data_backup, state = _fixture(tmp_path)
    journal = tmp_path / "reconciliation.journal.json"
    write_journal(journal, state)
    assert load_journal(journal)["phase"] == "prepared"
    advanced = dict(state, phase="sqlite_committed")
    write_journal(journal, advanced)
    with pytest.raises(JournalValidationError, match="regressed"):
        write_journal(journal, state)


@pytest.mark.parametrize("phase", ["prepared", "sqlite_committed", "json_published", "complete"])
def test_recovery_restores_exact_hashes_and_removes_journal(tmp_path: Path, phase: str):
    db, data, db_backup, data_backup, state = _fixture(tmp_path)
    state["phase"] = phase
    journal = tmp_path / "reconciliation.journal.json"
    write_journal(journal, state)
    db.write_bytes(b"mutated sqlite")
    data.write_text(json.dumps({"value": "mutated"}), encoding="utf-8")
    lock = ReconciliationLock(tmp_path / "reconciliation.lock", {"journalPath": str(journal)})
    with lock:
        loaded = load_journal(journal)
        result = recover_journal(loaded, lock)
        second = recover_journal(loaded, lock)
    assert result["status"] == "recovered"
    assert second["status"] == "already_recovered"
    assert _sha(db) == state["sqlite"]["beforeSha256"]
    assert _sha(data) == state["json"]["beforeSha256"]
    assert not journal.exists()


def test_damaged_backup_refuses_recovery_and_preserves_journal(tmp_path: Path):
    db, data, db_backup, data_backup, state = _fixture(tmp_path)
    journal = tmp_path / "reconciliation.journal.json"
    write_journal(journal, state)
    db_backup.write_bytes(b"damaged")
    lock = ReconciliationLock(tmp_path / "reconciliation.lock", {"journalPath": str(journal)})
    with lock, pytest.raises(JournalValidationError):
        recover_journal(load_journal(journal), lock)
    assert journal.exists()


def test_sidecar_refuses_recovery_and_preserves_journal(tmp_path: Path):
    db, data, db_backup, data_backup, state = _fixture(tmp_path)
    journal = tmp_path / "reconciliation.journal.json"
    write_journal(journal, state)
    for suffix in ("-wal", "-shm", "-journal"):
        (tmp_path / f"fixture.db{suffix}").write_bytes(b"sidecar")
        lock = ReconciliationLock(tmp_path / f"reconciliation-{suffix[1:]}.lock", {"journalPath": str(journal)})
        with lock, pytest.raises(JournalRecoveryError, match="sidecar"):
            recover_journal(load_journal(journal), lock)
        assert journal.exists()
        (tmp_path / f"fixture.db{suffix}").unlink()


def test_symlink_backup_is_rejected(tmp_path: Path):
    _, _, db_backup, _, state = _fixture(tmp_path)
    link = tmp_path / "fixture.db.link"
    try:
        link.symlink_to(db_backup)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    state["sqlite"]["backupPath"] = str(link)
    with pytest.raises(JournalValidationError, match="symlink"):
        write_journal(tmp_path / "reconciliation.journal.json", state)


def test_recovery_requires_held_lock(tmp_path: Path):
    _, _, _, _, state = _fixture(tmp_path)
    journal = tmp_path / "reconciliation.journal.json"
    write_journal(journal, state)
    with pytest.raises(JournalRecoveryError, match="lock"):
        recover_journal(load_journal(journal), ReconciliationLock(tmp_path / "reconciliation.lock", {"journalPath": str(journal)}))


def test_post_restore_verification_failure_keeps_journal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db, data, _, _, state = _fixture(tmp_path)
    journal = tmp_path / "reconciliation.journal.json"
    write_journal(journal, state)
    db.write_bytes(b"mutated")
    data.write_text("mutated", encoding="utf-8")
    loaded = load_journal(journal)
    original_sha = journal_module._sha256
    monkeypatch.setattr(journal_module, "_sha256", lambda path: "0" * 64 if path == data else original_sha(path))
    lock = ReconciliationLock(tmp_path / "reconciliation.lock", {"journalPath": str(journal)})
    with lock, pytest.raises(JournalRecoveryError, match="hash mismatch"):
        recover_journal(loaded, lock)
    assert journal.exists()


def test_malformed_schema_and_escape_are_rejected(tmp_path: Path):
    _, _, _, _, state = _fixture(tmp_path)
    journal = tmp_path / "reconciliation.journal.json"
    state["schemaVersion"] = 2
    with pytest.raises(JournalValidationError):
        write_journal(journal, state)
    state["schemaVersion"] = 1
    state["sqlite"]["path"] = str(tmp_path.parent / "outside.db")
    with pytest.raises(JournalValidationError, match="escapes"):
        write_journal(journal, state)
    state["sqlite"]["path"] = str(tmp_path / "fixture.db")
    state["sqlite"]["beforeSha256"] = "not-a-hash"
    with pytest.raises(JournalValidationError, match="beforeSha256"):
        write_journal(journal, state)


def test_journal_rejects_unknown_verification_mode(tmp_path: Path):
    _, _, _, _, state = _fixture(tmp_path)
    state["verificationMode"] = "unrecognized-v1"
    with pytest.raises(JournalValidationError, match="verificationMode"):
        write_journal(tmp_path / "reconciliation.journal.json", state)


def test_legacy_staged_path_in_journal_directory_remains_recoverable(tmp_path: Path):
    journal_dir = tmp_path / "journals"
    journal_dir.mkdir()
    db, data, _, _, state = _fixture(journal_dir)
    staged = journal_dir / "legacy.staged.json"
    staged.write_bytes(b"legacy")
    state["json"]["stagedPath"] = str(staged)
    state["json"]["stagedSha256"] = _sha(staged)
    journal = journal_dir / "reconciliation.journal.json"
    write_journal(journal, state)
    assert load_journal(journal)["json"]["stagedPath"] == str(staged)


def test_captured_foreign_bytes_are_recorded_in_recovery_journal(tmp_path: Path):
    db, data, db_backup, data_backup, state = _fixture(tmp_path)
    capture = tmp_path / "data.capture"
    capture.write_bytes(b"foreign-capture")
    state["json"].update({"capturedPath": str(capture), "capturedSha256": _sha(data_backup)})
    journal = tmp_path / "reconciliation.journal.json"
    write_journal(journal, state)
    data.write_text("foreign-target", encoding="utf-8")
    lock = ReconciliationLock(tmp_path / "reconciliation.lock", {"journalPath": str(journal)})
    with lock:
        recover_journal(load_journal(journal), lock)
    assert data.read_bytes() == data_backup.read_bytes()
    assert list(tmp_path.glob(".data.json.captured-observed.*"))
