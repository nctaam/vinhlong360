import json
import os
import stat
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from versioned_json_store import mutate_json, publication_lock


def test_mutation_leaves_no_adjacent_lock_or_temp_artifacts(tmp_path):
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps({"count": 0}), encoding="utf-8")

    result = mutate_json(data_path, lambda data: (True, data.update(count=1) or "saved"))

    assert result == "saved"
    assert json.loads(data_path.read_text(encoding="utf-8")) == {"count": 1}
    assert list(tmp_path.glob(".data.json.*.tmp")) == []
    assert not (tmp_path / ".data.json.lock").exists()


def test_failed_mutation_releases_lock_without_write_artifacts(tmp_path):
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps({"count": 0}), encoding="utf-8")

    def fail(_data):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        mutate_json(data_path, fail)

    result = mutate_json(data_path, lambda data: (True, data.update(count=1) or "recovered"))

    assert result == "recovered"
    assert json.loads(data_path.read_text(encoding="utf-8")) == {"count": 1}
    assert list(tmp_path.glob(".data.json.*.tmp")) == []
    assert not (tmp_path / ".data.json.lock").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode and directory fsync semantics")
def test_atomic_replace_preserves_mode_and_fsyncs_parent(tmp_path, monkeypatch):
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps({"count": 0}), encoding="utf-8")
    data_path.chmod(0o644)
    real_fsync = os.fsync
    fsynced_modes = []

    def record_fsync(fd):
        fsynced_modes.append(os.fstat(fd).st_mode)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", record_fsync)

    mutate_json(data_path, lambda data: (True, data.update(count=1)))

    assert stat.S_IMODE(data_path.stat().st_mode) == 0o644
    assert any(stat.S_ISDIR(mode) for mode in fsynced_modes)


def _hold_then_reach(outer, inner, mine, theirs, outcomes):
    """Hold `outer`, wait for the partner thread, then reach for `inner`."""
    try:
        with publication_lock(outer):
            mine.set()
            theirs.wait(5)
            with publication_lock(inner):
                pass
        outcomes.append("acquired")
    except RuntimeError:
        # Refusing an out-of-canonical-order acquisition is deadlock-free too.
        outcomes.append("refused")


def test_opposing_nested_path_lock_orders_cannot_deadlock(tmp_path):
    first = tmp_path / "first.lock"
    second = tmp_path / "second.lock"
    holds_first = threading.Event()
    holds_second = threading.Event()
    outcomes = []
    threads = [
        threading.Thread(
            target=_hold_then_reach,
            args=(first, second, holds_first, holds_second, outcomes),
            daemon=True,
        ),
        threading.Thread(
            target=_hold_then_reach,
            args=(second, first, holds_second, holds_first, outcomes),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert not any(thread.is_alive() for thread in threads), (
        "AB-BA cycle: two threads nesting path locks in opposing orders deadlocked"
    )
    assert len(outcomes) == 2


def test_multi_path_publication_lock_is_order_independent(tmp_path):
    first = tmp_path / "first.lock"
    second = tmp_path / "second.lock"
    barrier = threading.Barrier(2)
    entered = []

    def worker(paths):
        barrier.wait(10)
        for _ in range(20):
            with publication_lock(*paths):
                entered.append(paths[0].name)

    threads = [
        threading.Thread(target=worker, args=((first, second),), daemon=True),
        threading.Thread(target=worker, args=((second, first),), daemon=True),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert not any(thread.is_alive() for thread in threads)
    assert len(entered) == 40


def test_publication_lock_deduplicates_repeated_paths(tmp_path):
    lock_path = tmp_path / "shared.lock"

    with publication_lock(lock_path, lock_path):
        assert lock_path.exists()


def test_publication_lock_requires_at_least_one_path():
    with pytest.raises(ValueError):
        with publication_lock():
            pass
