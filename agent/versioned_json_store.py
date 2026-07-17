"""Concurrent-safe JSON reads and writes for runtime knowledge-base writers."""

import hashlib
import errno
import json
import os
import stat
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

_locks_guard = threading.Lock()
_path_locks: dict[str, threading.Lock] = {}
_held_path_locks = threading.local()
_lock_dir = Path(tempfile.gettempdir()) / "vinhlong360-json-locks"


def _canonical_path(path: Path) -> str:
    canonical = os.path.realpath(os.path.abspath(os.fspath(path)))
    return os.path.normcase(canonical) if os.name == "nt" else canonical


def _path_lock(path: Path) -> threading.Lock:
    key = _canonical_path(path)
    with _locks_guard:
        return _path_locks.setdefault(key, threading.Lock())


def _lock_path(path: Path) -> Path:
    digest = hashlib.sha256(_canonical_path(path).encode("utf-8")).hexdigest()
    return _lock_dir / f"{digest}.lock"


def _is_reparse_point(file_stat: os.stat_result) -> bool:
    attributes = getattr(file_stat, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _open_lock_file(lock_path: Path):
    try:
        lock_stat = lock_path.lstat()
    except FileNotFoundError:
        lock_stat = None
    if lock_stat is not None and (
        lock_path.is_symlink()
        or _is_reparse_point(lock_stat)
        or not stat.S_ISREG(lock_stat.st_mode)
    ):
        raise OSError("lock path must be a regular file")

    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        opened_stat = os.fstat(fd)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise OSError("lock path must be a regular file")
        return os.fdopen(fd, "r+b")
    except BaseException:
        os.close(fd)
        raise


@contextmanager
def _cross_process_lock_file(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with _open_lock_file(lock_path) as lock_file:
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"\0")
            lock_file.flush()
        lock_file.seek(0)

        if os.name == "nt":
            import msvcrt

            while True:
                lock_file.seek(0)
                try:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as error:
                    if error.errno == errno.EINTR:
                        continue
                    if error.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                        time.sleep(0.01)
                        continue
                    raise
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
def _thread_locked(path: Path) -> Iterator[None]:
    key = _canonical_path(path)
    held = getattr(_held_path_locks, "keys", set())
    if key in held:
        raise RuntimeError("path locks are non-reentrant")
    with _path_lock(path):
        held.add(key)
        _held_path_locks.keys = held
        try:
            yield
        finally:
            held.remove(key)


@contextmanager
def publication_lock(lock_path: Path) -> Iterator[None]:
    """Lock one explicit persistent file across threads and processes."""
    lock_path = Path(lock_path)
    with _thread_locked(lock_path):
        with _cross_process_lock_file(lock_path):
            yield


@contextmanager
def _locked(path: Path) -> Iterator[None]:
    with _thread_locked(path):
        with _cross_process_lock_file(_lock_path(path)):
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


def fsync_directory(directory: Path) -> None:
    """Persist directory entries on POSIX; Windows has no equivalent API."""
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_fd = os.open(directory, flags)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _atomic_write_impl(
    path: Path,
    data: dict,
    *,
    strict_directory_fsync: bool,
) -> None:
    path = Path(path)
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
            if target_mode is not None:
                os.chmod(temp_path, target_mode)
            os.fsync(temp_file.fileno())
        os.replace(temp_path, path)
        if strict_directory_fsync:
            fsync_directory(path.parent)
        else:
            try:
                fsync_directory(path.parent)
            except OSError:
                pass
    finally:
        temp_path.unlink(missing_ok=True)


def atomic_write_json(path: Path, data: dict) -> None:
    """Replace JSON and require parent-directory durability on POSIX."""
    _atomic_write_impl(path, data, strict_directory_fsync=True)


def _atomic_write(path: Path, data: dict) -> None:
    _atomic_write_impl(path, data, strict_directory_fsync=False)


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
