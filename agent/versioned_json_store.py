"""Concurrent-safe JSON reads and writes for runtime knowledge-base writers."""

import hashlib
import json
import os
import stat
import tempfile
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

_locks_guard = threading.Lock()
_path_locks: dict[str, threading.RLock] = {}
_lock_dir = Path(tempfile.gettempdir()) / "vinhlong360-json-locks"


def _path_lock(path: Path) -> threading.RLock:
    key = str(path.resolve())
    with _locks_guard:
        return _path_locks.setdefault(key, threading.RLock())


def _lock_path(path: Path) -> Path:
    digest = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()
    return _lock_dir / f"{digest}.lock"


@contextmanager
def _cross_process_lock(path: Path) -> Iterator[None]:
    lock_path = _lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_file:
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"\0")
            lock_file.flush()
        lock_file.seek(0)

        if os.name == "nt":
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


@contextmanager
def _locked(path: Path) -> Iterator[None]:
    with _path_lock(path):
        with _cross_process_lock(path):
            yield


def _version(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_versioned(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), _version(raw)


def load_json(path: Path) -> dict:
    data, _ = _read_versioned(path)
    return data


def load_json_versioned(path: Path) -> tuple[dict, str]:
    return _read_versioned(path)


def json_version(path: Path) -> str:
    return _version(path.read_bytes())


def _fsync_parent(path: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        directory_fd = os.open(path.parent, flags)
    except OSError:
        return
    try:
        os.fsync(directory_fd)
    except OSError:
        pass
    finally:
        os.close(directory_fd)


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    target_mode = None
    try:
        target_mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        pass
    fd, temp_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as temp_file:
            json.dump(data, temp_file, ensure_ascii=False, indent=2)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        if target_mode is not None:
            os.chmod(temp_path, target_mode)
        os.replace(temp_path, path)
        _fsync_parent(path)
    finally:
        temp_path.unlink(missing_ok=True)


def compare_and_swap_json(path: Path, expected_version: str, data: dict) -> bool:
    return replace_json(path, data, expected_version=expected_version)


def replace_json(path: Path, data: dict, expected_version: str | None = None) -> bool:
    """Replace JSON under lock; expected_version enables CAS, None is a force replace."""
    with _locked(path):
        if expected_version is not None and json_version(path) != expected_version:
            return False
        _atomic_write(path, data)
        return True


def mutate_json(path: Path, mutator: Callable[[dict], tuple[bool, T]]) -> T:
    """Load current JSON under lock, apply a targeted mutation, and commit atomically."""
    with _locked(path):
        data = load_json(path)
        changed, result = mutator(data)
        if changed:
            _atomic_write(path, data)
        return result
