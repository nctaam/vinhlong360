import subprocess
import sys
import time
import os
from pathlib import Path

import pytest

from scripts.checks.reconciliation_lock import (
    LockBusyError,
    LockPathError,
    ReconciliationLock,
    read_lock_metadata,
)


def test_lock_writes_metadata_and_releases_on_exit(tmp_path: Path) -> None:
    path = tmp_path / "reconciliation.lock"
    with ReconciliationLock(path, {"operationId": "op-1", "targetPaths": ["fixture.db"]}):
        if os.name != "nt":
            metadata = read_lock_metadata(path)
            assert metadata is not None
            assert metadata["operationId"] == "op-1"
            assert metadata["pid"] == os.getpid()
    with ReconciliationLock(path, {"operationId": "op-2"}):
        if os.name != "nt":
            assert read_lock_metadata(path)["operationId"] == "op-2"


def test_contention_is_non_blocking_and_preserves_owner_metadata(tmp_path: Path) -> None:
    path = tmp_path / "reconciliation.lock"
    with ReconciliationLock(path, {"operationId": "owner"}):
        before = path.read_bytes() if os.name != "nt" else None
        with pytest.raises(LockBusyError):
            with ReconciliationLock(path, {"operationId": "contender"}):
                pass
        if os.name != "nt":
            assert path.read_bytes() == before
    if os.name != "nt":
        assert path.read_bytes() == before
    assert read_lock_metadata(path)["operationId"] == "owner"


def test_subprocess_contention_reports_busy_without_waiting(tmp_path: Path) -> None:
    path = tmp_path / "reconciliation.lock"
    ready = tmp_path / "ready"
    code = (
        "import sys,time; "
        "from pathlib import Path; "
        "from scripts.checks.reconciliation_lock import ReconciliationLock; "
        "p=Path(sys.argv[1]); r=Path(sys.argv[2]); "
        "lock=ReconciliationLock(p, {'operationId':'child'}); "
        "lock.__enter__(); r.write_text('ready'); time.sleep(1.5); lock.__exit__(None,None,None)"
    )
    process = subprocess.Popen([sys.executable, "-c", code, str(path), str(ready)])
    try:
        deadline = time.monotonic() + 2
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        started = time.monotonic()
        with pytest.raises(LockBusyError):
            with ReconciliationLock(path, {"operationId": "parent"}):
                pass
        assert time.monotonic() - started < 0.5
        if os.name != "nt":
            assert read_lock_metadata(path)["operationId"] == "child"
    finally:
        process.wait(timeout=5)
    assert read_lock_metadata(path)["operationId"] == "child"
    with ReconciliationLock(path, {"operationId": "after-child"}):
        pass


def test_malformed_or_unreadable_paths_raise_controlled_errors(tmp_path: Path) -> None:
    directory = tmp_path / "directory.lock"
    directory.mkdir()
    with pytest.raises(LockPathError):
        with ReconciliationLock(directory, {}):
            pass
    malformed = tmp_path / "malformed.lock"
    malformed.write_text("not-json", encoding="utf-8")
    with pytest.raises(LockPathError):
        read_lock_metadata(malformed)
