"""Cross-process, non-blocking lock used by reconciliation maintenance checks."""

from __future__ import annotations

import json
import os
import socket
import stat
from pathlib import Path
from typing import Any


class ReconciliationLockError(RuntimeError):
    """Base class for controlled reconciliation lock failures."""


class LockBusyError(ReconciliationLockError):
    """Raised immediately when another process owns the lock."""


class LockPathError(ReconciliationLockError):
    """Raised when the lock path cannot be opened or read safely."""


class ReconciliationLock:
    """Acquire an exclusive OS lock without waiting for another owner."""

    def __init__(self, path: Path, metadata: dict[str, Any]):
        self.path = Path(path)
        self.metadata = dict(metadata)
        self._file: Any = None

    def __enter__(self) -> "ReconciliationLock":
        try:
            self._initialize_lock_file()
            self._file = self.path.open("r+b")
        except (OSError, ValueError) as exc:
            raise LockPathError(f"cannot open lock path {self.path}: {exc}") from exc

        try:
            self._acquire(self._file)
        except BlockingIOError as exc:
            self._file.close()
            self._file = None
            raise LockBusyError(f"lock is held by another process: {self.path}") from exc
        except PermissionError as exc:
            self._file.close()
            self._file = None
            winerror = getattr(exc, "winerror", None)
            if os.name == "nt" and (winerror in {32, 33} or getattr(exc, "errno", None) in {13, 33}):
                raise LockBusyError(f"lock is held by another process: {self.path}") from exc
            raise LockPathError(f"cannot acquire lock {self.path}: {exc}") from exc
        except OSError as exc:
            self._file.close()
            self._file = None
            raise LockPathError(f"cannot acquire lock {self.path}: {exc}") from exc

        owner = {
            **self.metadata,
            "pid": os.getpid(),
            "host": socket.gethostname(),
        }
        try:
            payload = (json.dumps(owner, sort_keys=True, separators=(",", ":")) + "\n").encode(
                "utf-8"
            )
            self._file.seek(0)
            self._file.truncate(0)
            self._file.write(payload)
            self._file.flush()
            os.fsync(self._file.fileno())
            self.metadata = owner
        except (OSError, TypeError, ValueError) as exc:
            self._release(self._file)
            self._file.close()
            self._file = None
            raise LockPathError(f"cannot write lock metadata {self.path}: {exc}") from exc
        return self

    def _initialize_lock_file(self) -> None:
        """Create the one-byte lock region without mutating an existing file."""
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, stat.S_IRUSR | stat.S_IWUSR)
        except FileExistsError:
            if self.path.stat().st_size == 0:
                raise LockPathError(f"lock path is uninitialized: {self.path}")
            return
        except OSError:
            raise
        with os.fdopen(fd, "wb") as handle:
            handle.write(b" ")
            handle.flush()
            os.fsync(handle.fileno())

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if self._file is None:
            return
        try:
            self._release(self._file)
        finally:
            self._file.close()
            self._file = None

    @staticmethod
    def _acquire(file_obj: Any) -> None:
        if os.name == "nt":
            import msvcrt

            file_obj.seek(0)
            file_obj.seek(0)
            msvcrt.locking(file_obj.fileno(), msvcrt.LK_NBLCK, 1)
            return
        import fcntl

        fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _release(file_obj: Any) -> None:
        if os.name == "nt":
            import msvcrt

            file_obj.seek(0)
            msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)
            return
        import fcntl

        fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)


def read_lock_metadata(path: Path) -> dict[str, Any] | None:
    """Read lock metadata without modifying or deleting the lock file."""

    lock_path = Path(path)
    try:
        raw = lock_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError) as exc:
        raise LockPathError(f"cannot read lock path {lock_path}: {exc}") from exc
    if not raw.strip():
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LockPathError(f"malformed lock metadata {lock_path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LockPathError(f"lock metadata must be an object: {lock_path}")
    return value
