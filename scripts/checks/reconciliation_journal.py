"""Durable journal validation and fixture-only recovery for reconciliation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any

from .reconciliation_lock import ReconciliationLock

SCHEMA_VERSION = 1
PHASES = ("prepared", "sqlite_committed", "json_published", "complete")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class JournalError(RuntimeError):
    """Base class for controlled journal failures."""


class JournalValidationError(JournalError):
    """Raised when a journal or its referenced artifacts are unsafe."""


class JournalRecoveryError(JournalError):
    """Raised when recovery cannot verify both restored stores."""


class JournalState:
    """Validator for the versioned reconciliation journal state."""

    @classmethod
    def validate(cls, state: dict[str, Any], *, scope: Path | None = None) -> dict[str, Any]:
        _validate_journal_header(state)
        for store_name in ("sqlite", "json"):
            _validate_store_entry(store_name, state.get(store_name), scope)
        return state


def _validate_journal_header(state: Any) -> None:
    if not isinstance(state, dict):
        raise JournalValidationError("journal must be an object")
    if state.get("schemaVersion") != SCHEMA_VERSION:
        raise JournalValidationError("unsupported journal schemaVersion")
    if state.get("phase") not in PHASES:
        raise JournalValidationError("invalid journal phase")
    for key in ("operationId", "planSha256"):
        if not isinstance(state.get(key), str) or not state[key]:
            raise JournalValidationError(f"missing journal {key}")
    _validate_hash(state["planSha256"], "planSha256")
    if "verificationMode" in state and state["verificationMode"] not in {"global-parity-v1", "targeted-media-v1"}:
        raise JournalValidationError("unsupported journal verificationMode")


def _validate_store_entry(store_name: str, store: Any, scope: Path | None) -> None:
    if not isinstance(store, dict):
        raise JournalValidationError(f"missing journal {store_name} store")
    required = ("path", "backupPath", "beforeSha256", "backupSha256", "beforeIdentity")
    for key in required:
        if key not in store:
            raise JournalValidationError(f"missing {store_name}.{key}")
    _validate_hash(store["beforeSha256"], f"{store_name}.beforeSha256")
    _validate_hash(store["backupSha256"], f"{store_name}.backupSha256")
    if not isinstance(store["path"], str) or not isinstance(store["backupPath"], str):
        raise JournalValidationError(f"invalid {store_name} paths")
    _validate_identity(store["beforeIdentity"], store_name)
    _validate_staged_json(store_name, store)
    _validate_store_scope(store_name, store, scope)
    _validate_backup(store, store_name)


def _validate_staged_json(store_name: str, store: dict[str, Any]) -> None:
    if store_name != "json":
        return
    for path_key, hash_key in (
        ("stagedPath", "stagedSha256"),
        ("candidatePath", "candidateSha256"),
        ("candidateObservedPath", "candidateObservedSha256"),
        ("capturedPath", "capturedSha256"),
        ("capturedObservedPath", "capturedObservedSha256"),
        ("observedPath", "observedSha256"),
    ):
        if path_key in store:
            if not isinstance(store[path_key], str):
                raise JournalValidationError(f"invalid json.{path_key}")
            _validate_hash(store.get(hash_key), f"json.{hash_key}")
    if "publishedSha256" in store:
        _validate_hash(store["publishedSha256"], "json.publishedSha256")
    if "publishedIdentity" in store:
        _validate_identity(store["publishedIdentity"], "json.published")
    for key in ("candidateIdentity", "candidateObservedIdentity"):
        if key in store:
            _validate_identity(store[key], f"json.{key}")


def _validate_store_scope(store_name: str, store: dict[str, Any], scope: Path | None) -> None:
    if scope is None:
        return
    keys = ["path", "backupPath"]
    artifact_scope = Path(store["path"]).parent.resolve() if store_name == "json" else scope
    artifact_keys = []
    if store_name == "json":
        artifact_keys = [key for key in ("stagedPath", "candidatePath", "candidateObservedPath", "capturedPath", "capturedObservedPath", "observedPath") if key in store]
    for key in keys:
        _ensure_within(Path(store[key]), scope, f"{store_name}.{key}")
    for key in artifact_keys:
        artifact = Path(store[key])
        try:
            artifact.resolve(strict=False).relative_to(artifact_scope)
        except ValueError:
            if key == "stagedPath":
                _ensure_within(artifact, scope, f"{store_name}.{key}")
            else:
                raise JournalValidationError(f"{store_name}.{key} escapes JSON artifact scope")


def write_journal(path: Path, state: dict[str, Any]) -> None:
    """Validate and atomically fsync a journal, enforcing monotonic phases."""
    journal_path = Path(path)
    scope = journal_path.parent.resolve()
    JournalState.validate(state, scope=scope)
    if journal_path.exists():
        previous = load_journal(journal_path)
        if previous.get("operationId") != state.get("operationId"):
            raise JournalValidationError("journal operationId changed")
        if PHASES.index(state["phase"]) < PHASES.index(previous["phase"]):
            raise JournalValidationError("journal phase regressed")
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{journal_path.name}.", dir=journal_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(state, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, journal_path)
        _fsync_directory(journal_path.parent)
    except (OSError, TypeError, ValueError) as exc:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise JournalError(f"cannot write journal {journal_path}: {exc}") from exc


def load_journal(path: Path) -> dict[str, Any]:
    """Load a journal and validate its schema, scope, backups, and hashes."""
    journal_path = Path(path)
    try:
        with journal_path.open("r", encoding="utf-8") as handle:
            state = json.load(handle)
    except FileNotFoundError as exc:
        raise JournalValidationError(f"journal does not exist: {journal_path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise JournalValidationError(f"cannot read journal {journal_path}: {exc}") from exc
    JournalState.validate(state, scope=journal_path.parent.resolve())
    state["journalPath"] = str(journal_path)
    return state


def recover_journal(state: dict[str, Any], lock: ReconciliationLock) -> dict[str, Any]:
    """Restore both stores from verified backups and remove the journal on success."""
    journal_hint = state.get("journalPath") or lock.metadata.get("journalPath")
    if not journal_hint:
        raise JournalRecoveryError("journal path is not declared")
    journal_path = Path(journal_hint)
    JournalState.validate(state, scope=journal_path.parent.resolve())
    if getattr(lock, "_file", None) is None:
        raise JournalRecoveryError("recovery requires the reconciliation lock to be held")
    if not journal_path.exists():
        for name in ("sqlite", "json"):
            if _sha256(Path(state[name]["path"])) != state[name]["beforeSha256"]:
                raise JournalRecoveryError(f"{name} hash mismatch after prior recovery")
        return {"status": "already_recovered", "phase": state["phase"], "journalPath": str(journal_path)}
    try:
        # Refuse before consuming the JSON capture; a late SQLite sidecar must
        # leave every recovery artifact available for a later safe retry.
        _ensure_no_sqlite_sidecars(state["sqlite"])
        _restore_json(state["json"], state, journal_path)
        _restore_sqlite(state["sqlite"])
        for name in ("sqlite", "json"):
            target = Path(state[name]["path"])
            actual = _sha256(target)
            if actual != state[name]["beforeSha256"]:
                raise JournalRecoveryError(f"{name} hash mismatch after recovery")
        journal_path.unlink()
        _fsync_directory(journal_path.parent)
    except (OSError, JournalError) as exc:
        raise JournalRecoveryError(str(exc)) from exc
    return {"status": "recovered", "phase": state["phase"], "journalPath": str(journal_path)}


def _validate_hash(value: Any, label: str) -> None:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise JournalValidationError(f"invalid {label}")


def _validate_identity(value: Any, store_name: str) -> None:
    if not isinstance(value, dict) or not all(key in value for key in ("device", "inode", "size")):
        raise JournalValidationError(f"invalid {store_name}.beforeIdentity")
    if not all(isinstance(value[key], (str, int)) for key in ("device", "inode", "size")):
        raise JournalValidationError(f"invalid {store_name}.beforeIdentity")


def _ensure_within(path: Path, scope: Path, label: str) -> None:
    try:
        path.resolve(strict=False).relative_to(scope.resolve())
    except ValueError as exc:
        raise JournalValidationError(f"{label} escapes journal scope") from exc


def _validate_backup(store: dict[str, Any], store_name: str) -> None:
    backup = Path(store["backupPath"])
    target = Path(store["path"])
    try:
        link_info = backup.lstat()
        if stat.S_ISLNK(link_info.st_mode):
            raise JournalValidationError(f"{store_name} backup must not be a symlink")
        info = backup.stat()
    except OSError as exc:
        raise JournalValidationError(f"cannot inspect {store_name} backup: {exc}") from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise JournalValidationError(f"{store_name} backup is not an independent regular file")
    try:
        if backup.samefile(target):
            raise JournalValidationError(f"{store_name} backup aliases target")
    except FileNotFoundError:
        pass
    if _sha256(backup) != store["backupSha256"]:
        raise JournalValidationError(f"{store_name} backup hash mismatch")
    if store["backupSha256"] != store["beforeSha256"]:
        raise JournalValidationError(f"{store_name} backup does not match before hash")


def _restore_json(store: dict[str, Any], state: dict[str, Any], journal_path: Path) -> None:
    target = Path(store["path"])
    captured = Path(store.get("capturedPath", store["backupPath"]))
    if "capturedPath" not in store:
        _copy_atomic(captured, target)
        _remove_candidate(store, state, journal_path)
        return
    if target.exists():
        _capture_observed(target, store, state, journal_path)
    if target.exists():
        raise JournalRecoveryError("JSON target was recreated during recovery")
    captured_valid = captured.exists() and _sha256(captured) == store["capturedSha256"]
    if not captured_valid:
        # A race hook may have populated or altered the capture path. Preserve
        # those foreign bytes, then fall back to the independently verified
        # backup so the journal remains recoverable.
        if captured.exists():
            preserved = target.with_name(f".{target.name}.captured-observed.{os.urandom(16).hex()}")
            os.rename(captured, preserved)
            store["capturedObservedPath"] = str(preserved)
            store["capturedObservedSha256"] = _sha256(preserved)
            write_journal(journal_path, state)
        captured = Path(store["backupPath"])
        if not captured.exists() or _sha256(captured) != store["backupSha256"]:
            raise JournalRecoveryError("captured JSON hash mismatch")
        _copy_atomic(captured, target)
        _fsync_directory(target.parent)
        _remove_candidate(store, state, journal_path)
        return
    try:
        os.link(captured, target)
        captured.unlink()
    except FileExistsError as exc:
        raise JournalRecoveryError("JSON target was recreated during recovery") from exc
    _fsync_directory(target.parent)
    _remove_candidate(store, state, journal_path)


def _remove_candidate(store: dict[str, Any], state: dict[str, Any], journal_path: Path) -> None:
    candidate = store.get("candidatePath")
    if isinstance(candidate, str):
        path = Path(candidate)
        if not path.exists():
            return
        actual_sha, actual_identity = _sha256(path), _identity(path)
        owned = actual_sha == store.get("candidateSha256")
        expected = store.get("candidateIdentity")
        if expected is not None:
            owned = owned and actual_identity == expected
        if owned:
            path.unlink()
            return
        observed = Path(store["path"]).with_name(f".{Path(store['path']).name}.candidate-observed.{os.urandom(16).hex()}")
        os.rename(path, observed)
        store.update(candidateObservedPath=str(observed), candidateObservedSha256=actual_sha, candidateObservedIdentity=actual_identity)
        write_journal(journal_path, state)


def _capture_observed(target: Path, store: dict[str, Any], state: dict[str, Any], journal_path: Path) -> None:
    observed = target.with_name(f".{target.name}.observed.{os.urandom(16).hex()}")
    os.rename(target, observed)
    observed_sha = _sha256(observed)
    observed_identity = _identity(observed)
    matches = observed_sha == store.get("publishedSha256") and observed_identity == store.get("publishedIdentity")
    if matches:
        observed.unlink()
        return
    store.update(observedPath=str(observed), observedSha256=observed_sha, observedIdentity=observed_identity)
    write_journal(journal_path, state)


def _restore_sqlite(store: dict[str, Any]) -> None:
    target = Path(store["path"])
    _ensure_no_sqlite_sidecars(store)
    source = Path(store["backupPath"])
    if os.name != "nt":
        _copy_atomic(source, target)
        return
    # Windows may retain an open SQLite handle that blocks rename-over-target.
    # In-place replacement is the explicit platform crash boundary.
    try:
        with target.open("wb") as handle, source.open("rb") as source_handle:
            shutil.copyfileobj(source_handle, handle)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise JournalRecoveryError(f"cannot restore sqlite target: {exc}") from exc


def _ensure_no_sqlite_sidecars(store: dict[str, Any]) -> None:
    target = Path(store["path"])
    for suffix in ("-wal", "-shm", "-journal"):
        if target.with_name(target.name + suffix).exists():
            raise JournalRecoveryError(f"sqlite sidecar exists: {target.name + suffix}")


def _copy_atomic(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.restore.", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle, source.open("rb") as source_handle:
            shutil.copyfileobj(source_handle, handle)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temp_name, target)
        except PermissionError:
            # Windows cannot replace an existing file held by a reader; the
            # reconciliation lock makes this unlink-and-replace sequence safe.
            target.unlink()
            os.replace(temp_name, target)
        _fsync_directory(target.parent)
    except OSError:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(path: Path) -> dict[str, int]:
    info = path.stat()
    return {"device": info.st_dev, "inode": info.st_ino, "size": info.st_size}


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
