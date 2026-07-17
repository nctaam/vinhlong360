"""Durable publication and loading for immutable sitemap bundles."""

import hashlib
import json
import math
import os
import re
import shutil
import stat
import sys
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

try:
    from .versioned_json_store import (
        atomic_write_json,
        fsync_directory,
        publication_lock,
    )
except ImportError:  # Direct agent/ imports are the repository's test convention.
    from versioned_json_store import (
        atomic_write_json,
        fsync_directory,
        publication_lock,
    )


_REVISION_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_METADATA_NAME = "metadata.json"
_DOCUMENT_NAMES = (
    "sitemap.xml",
    "sitemap-media.xml",
    "sitemap-index.xml",
)
_BUNDLE_ENTRY_NAMES = frozenset((_METADATA_NAME, *_DOCUMENT_NAMES))
_POINTER_KEYS = frozenset(("batch_revision", "published_at", "published_batches"))
_LEDGER_ENTRY_KEYS = frozenset(("batch_revision", "published_at"))
SITEMAP_METADATA_SCHEMA_VERSION = 1
_REQUIRED_METADATA_KEYS = frozenset(
    ("schema_version", "batch_revision", "documents")
)
_OPTIONAL_METADATA_KEYS = frozenset(("renderer_evidence",))


class SitemapStateUnavailable(RuntimeError):
    """The persisted sitemap publication state cannot be trusted or reached."""


class SitemapBundleConflict(RuntimeError):
    """An existing content-addressed directory differs from its candidate."""


class SitemapPublicationStage(str, Enum):
    AFTER_DIRECTORY_RENAME = "after-directory-rename-before-active-pointer"
    BEFORE_ACTIVE_POINTER_REPLACE = "before-active-pointer-replace"


@dataclass(frozen=True)
class StoredBundle:
    batch_revision: str
    metadata: dict
    documents: dict[str, bytes]


@dataclass(frozen=True)
class _PreparedBundle:
    bundle: StoredBundle
    metadata_bytes: bytes


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_revision(revision: object, *, state_error: bool = False) -> str:
    if isinstance(revision, str) and _REVISION_PATTERN.fullmatch(revision):
        return revision
    error = SitemapStateUnavailable if state_error else ValueError
    raise error("batch revision must be exactly 64 lowercase hexadecimal characters")


def _is_json_value(value: object) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_value(item)
            for key, item in value.items()
        )
    return False


def _canonical_metadata_bytes(metadata: dict) -> bytes:
    return json.dumps(
        metadata,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _copy_bundle_documents(documents: object) -> dict[str, bytes]:
    if not isinstance(documents, dict):
        raise ValueError("bundle documents must be a mapping")
    if set(documents) != set(_DOCUMENT_NAMES):
        raise ValueError("bundle documents must contain exactly the three sitemap files")

    copied: dict[str, bytes] = {}
    for name in _DOCUMENT_NAMES:
        body = documents[name]
        if not isinstance(body, bytes):
            raise ValueError(f"{name} must contain bytes")
        copied[name] = bytes(body)
    return copied


def _validate_metadata_envelope(metadata: object, revision: str) -> dict:
    if not isinstance(metadata, dict) or not _is_json_value(metadata):
        raise ValueError("metadata must be a valid JSON object")

    metadata_keys = set(metadata)
    if not _REQUIRED_METADATA_KEYS.issubset(metadata_keys):
        raise ValueError("metadata is missing a required root key")
    if not metadata_keys.issubset(_REQUIRED_METADATA_KEYS | _OPTIONAL_METADATA_KEYS):
        raise ValueError("metadata contains an unknown root key")
    schema_version = metadata["schema_version"]
    if schema_version != SITEMAP_METADATA_SCHEMA_VERSION or isinstance(
        schema_version, bool
    ):
        raise ValueError("metadata schema_version is unsupported")
    if metadata.get("batch_revision") != revision:
        raise ValueError("metadata batch_revision must match the bundle")
    renderer_evidence = metadata.get("renderer_evidence")
    if "renderer_evidence" in metadata and not isinstance(renderer_evidence, dict):
        raise ValueError("metadata renderer_evidence must be a JSON object")
    return metadata


def _validate_document_hashes(
    document_hashes: object,
    documents: dict[str, bytes],
) -> None:
    if not isinstance(document_hashes, dict) or set(document_hashes) != set(
        _DOCUMENT_NAMES
    ):
        raise ValueError("metadata documents must be the exact sitemap digest mapping")
    for name, body in documents.items():
        digest = document_hashes.get(name)
        if not isinstance(digest, str) or not _REVISION_PATTERN.fullmatch(digest):
            raise ValueError(f"metadata digest for {name} must be lowercase SHA-256")
        if digest != hashlib.sha256(body).hexdigest():
            raise ValueError(f"metadata digest for {name} does not match its bytes")


def _prepare_bundle(bundle: StoredBundle) -> _PreparedBundle:
    revision = _validate_revision(bundle.batch_revision)
    documents = _copy_bundle_documents(bundle.documents)
    metadata = _validate_metadata_envelope(bundle.metadata, revision)
    _validate_document_hashes(metadata.get("documents"), documents)
    metadata_bytes = _canonical_metadata_bytes(metadata)
    metadata_copy = json.loads(metadata_bytes.decode("utf-8"))
    return _PreparedBundle(
        StoredBundle(revision, metadata_copy, documents),
        metadata_bytes,
    )


def _is_reparse_point(file_stat: os.stat_result) -> bool:
    attributes = getattr(file_stat, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _lstat(path: Path) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None


def _require_regular_file(path: Path) -> None:
    try:
        file_stat = path.lstat()
    except OSError as error:
        raise SitemapStateUnavailable(f"missing sitemap state file: {path.name}") from error
    if (
        path.is_symlink()
        or _is_reparse_point(file_stat)
        or not stat.S_ISREG(file_stat.st_mode)
    ):
        raise SitemapStateUnavailable(f"sitemap state entry is not a regular file: {path.name}")


def _require_bundle_directory(path: Path) -> None:
    try:
        directory_stat = path.lstat()
    except OSError as error:
        raise SitemapStateUnavailable("immutable sitemap bundle is missing") from error
    if (
        path.is_symlink()
        or _is_reparse_point(directory_stat)
        or not stat.S_ISDIR(directory_stat.st_mode)
    ):
        raise SitemapStateUnavailable("immutable sitemap bundle is not a regular directory")


def _read_and_validate_bundle(directory: Path, revision: str) -> StoredBundle:
    _validate_revision(revision, state_error=True)
    if directory.name != revision:
        raise SitemapStateUnavailable("immutable sitemap bundle directory name is invalid")
    _require_bundle_directory(directory)
    try:
        entries = tuple(directory.iterdir())
    except OSError as error:
        raise SitemapStateUnavailable("immutable sitemap bundle is unreachable") from error
    if {entry.name for entry in entries} != _BUNDLE_ENTRY_NAMES:
        raise SitemapStateUnavailable("immutable sitemap bundle has an invalid entry set")
    for entry in entries:
        _require_regular_file(entry)

    metadata_path = directory / _METADATA_NAME
    try:
        metadata_bytes = metadata_path.read_bytes()
        metadata = json.loads(metadata_bytes.decode("utf-8"))
        documents = {
            name: (directory / name).read_bytes() for name in _DOCUMENT_NAMES
        }
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SitemapStateUnavailable("immutable sitemap bundle cannot be decoded") from error

    try:
        prepared = _prepare_bundle(StoredBundle(revision, metadata, documents))
    except ValueError as error:
        raise SitemapStateUnavailable("immutable sitemap bundle validation failed") from error
    if prepared.metadata_bytes != metadata_bytes:
        raise SitemapStateUnavailable("immutable sitemap metadata is not canonical")
    return prepared.bundle


def _read_conflict_directory_entries(directory: Path) -> tuple[Path, ...]:
    try:
        directory_stat = directory.lstat()
    except OSError as error:
        raise SitemapBundleConflict("content-addressed directory is unreachable") from error
    if (
        directory.is_symlink()
        or _is_reparse_point(directory_stat)
        or not stat.S_ISDIR(directory_stat.st_mode)
    ):
        raise SitemapBundleConflict("content-addressed path is not a regular directory")
    try:
        return tuple(directory.iterdir())
    except OSError as error:
        raise SitemapBundleConflict("content-addressed directory is unreachable") from error


def _read_conflict_entry(entry: Path) -> bytes:
    try:
        entry_stat = entry.lstat()
    except OSError as error:
        raise SitemapBundleConflict(
            f"content-addressed entry is unreachable: {entry.name}"
        ) from error
    if (
        entry.is_symlink()
        or _is_reparse_point(entry_stat)
        or not stat.S_ISREG(entry_stat.st_mode)
    ):
        raise SitemapBundleConflict(
            f"content-addressed entry is not a regular file: {entry.name}"
        )
    try:
        return entry.read_bytes()
    except OSError as error:
        raise SitemapBundleConflict(
            f"content-addressed entry is unreachable: {entry.name}"
        ) from error


def validate_completed_bundle_matches(directory: Path, bundle: StoredBundle) -> None:
    prepared = _prepare_bundle(bundle)
    if directory.name != prepared.bundle.batch_revision:
        raise SitemapBundleConflict("content-addressed directory name differs")
    entries = _read_conflict_directory_entries(directory)
    if {entry.name for entry in entries} != _BUNDLE_ENTRY_NAMES:
        raise SitemapBundleConflict("content-addressed directory entry set differs")

    expected = {_METADATA_NAME: prepared.metadata_bytes, **prepared.bundle.documents}
    for entry in entries:
        actual = _read_conflict_entry(entry)
        if actual != expected[entry.name]:
            raise SitemapBundleConflict(
                f"content-addressed entry bytes differ: {entry.name}"
            )


def _write_file_and_fsync(path: Path, content: bytes) -> None:
    with path.open("xb") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())


def write_bundle_and_fsync(directory: Path, bundle: StoredBundle) -> None:
    prepared = _prepare_bundle(bundle)
    directory.mkdir()
    _write_file_and_fsync(directory / _METADATA_NAME, prepared.metadata_bytes)
    for name in _DOCUMENT_NAMES:
        _write_file_and_fsync(directory / name, prepared.bundle.documents[name])
    fsync_directory(directory)


def _validate_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise SitemapStateUnavailable("publication timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise SitemapStateUnavailable("publication timestamp is malformed") from error
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise SitemapStateUnavailable("publication timestamp must be UTC-aware")
    return parsed


def _validate_ledger_entry(item: object) -> dict:
    if not isinstance(item, dict) or set(item) != _LEDGER_ENTRY_KEYS:
        raise SitemapStateUnavailable("active sitemap pointer ledger entry is invalid")
    revision = _validate_revision(item.get("batch_revision"), state_error=True)
    published_at = item.get("published_at")
    _validate_timestamp(published_at)
    return {"batch_revision": revision, "published_at": published_at}


def _validate_pointer_ledger(ledger: object, active: str, published_at: object) -> list:
    if not isinstance(ledger, list) or not ledger:
        raise SitemapStateUnavailable("active sitemap pointer ledger is empty")

    seen = set()
    validated_ledger = []
    for item in ledger:
        validated = _validate_ledger_entry(item)
        revision = validated["batch_revision"]
        if revision in seen:
            raise SitemapStateUnavailable("active sitemap pointer ledger is duplicated")
        seen.add(revision)
        validated_ledger.append(validated)
    active_entries = [item for item in validated_ledger if item["batch_revision"] == active]
    if len(active_entries) != 1 or active_entries[0]["published_at"] != published_at:
        raise SitemapStateUnavailable("active sitemap pointer does not match its ledger")
    if validated_ledger[-1]["batch_revision"] != active:
        raise SitemapStateUnavailable("active sitemap revision must be newest in the ledger")
    return validated_ledger


def _validate_pointer_payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != _POINTER_KEYS:
        raise SitemapStateUnavailable("active sitemap pointer has invalid keys")
    active = _validate_revision(payload.get("batch_revision"), state_error=True)
    published_at = payload.get("published_at")
    _validate_timestamp(published_at)
    validated_ledger = _validate_pointer_ledger(
        payload.get("published_batches"), active, published_at
    )
    return {
        "batch_revision": active,
        "published_at": published_at,
        "published_batches": validated_ledger,
    }


def _read_active_pointer(root: Path) -> dict:
    path = root / "active.json"
    _require_regular_file(path)
    try:
        payload = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SitemapStateUnavailable("active sitemap pointer cannot be decoded") from error
    return _validate_pointer_payload(payload)


def _format_publication_time(now: Callable[[], datetime]) -> str:
    value = now()
    if not isinstance(value, datetime):
        raise ValueError("now must return a datetime")
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("publication time must be UTC-aware")
    return value.isoformat()


def _require_root_directory_component(path: Path) -> None:
    try:
        path_stat = path.lstat()
    except OSError as error:
        raise SitemapStateUnavailable("sitemap bundle root is unreachable") from error
    if path.is_symlink() or _is_reparse_point(path_stat) or not stat.S_ISDIR(
        path_stat.st_mode
    ):
        raise SitemapStateUnavailable("sitemap bundle root is not a regular directory")


def _root_directory_component_stat(path: Path) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise SitemapStateUnavailable("sitemap bundle root is unreachable") from error


def _ensure_root_directory(root: Path) -> None:
    missing = []
    current = root
    while _root_directory_component_stat(current) is None:
        missing.append(current)
        parent = current.parent
        if parent == current:
            raise SitemapStateUnavailable("sitemap bundle root has no reachable ancestor")
        current = parent

    _require_root_directory_component(current)
    for component in reversed(missing):
        _require_root_directory_component(component.parent)
        try:
            component.mkdir()
        except FileExistsError:
            pass
        except OSError as error:
            raise SitemapStateUnavailable("sitemap bundle root is unreachable") from error
        _require_root_directory_component(component)
        fsync_directory(component.parent)


def _require_existing_root(root: Path) -> None:
    if _root_directory_component_stat(root) is None:
        raise SitemapStateUnavailable("sitemap bundle root is missing")
    _require_root_directory_component(root)


@contextmanager
def _root_lock(root: Path, *, create: bool) -> Iterator[None]:
    if create:
        _ensure_root_directory(root)
    else:
        _require_existing_root(root)
    lock = publication_lock(root / ".publish.lock")
    # Map acquisition failures without wrapping exceptions raised by store work.
    try:
        lock.__enter__()
    except (OSError, RuntimeError) as error:
        raise SitemapStateUnavailable("sitemap publication lock is unavailable") from error
    try:
        yield
    finally:
        lock.__exit__(*sys.exc_info())


def _revision_entries(root: Path) -> tuple[str, ...]:
    try:
        return tuple(
            entry.name
            for entry in root.iterdir()
            if _REVISION_PATTERN.fullmatch(entry.name)
        )
    except OSError as error:
        raise SitemapStateUnavailable("sitemap bundle root cannot be inspected") from error


def _remove_operation_staging(staging: Path) -> None:
    staging_stat = _lstat(staging)
    if staging_stat is None:
        return
    if stat.S_ISDIR(staging_stat.st_mode) and not staging.is_symlink():
        shutil.rmtree(staging)
    else:
        staging.unlink()


def _remove_validated_bundle_directory(root: Path, revision: str) -> None:
    revision = _validate_revision(revision, state_error=True)
    target = root / revision
    _read_and_validate_bundle(target, revision)
    try:
        resolved_root = root.resolve(strict=True)
        resolved_target = target.resolve(strict=True)
    except OSError as error:
        raise SitemapStateUnavailable("immutable sitemap bundle cannot be resolved") from error
    if resolved_target.parent != resolved_root or resolved_target.name != revision:
        raise SitemapStateUnavailable("immutable sitemap bundle escaped its root")
    shutil.rmtree(target)
    fsync_directory(root)


class SitemapBundleStore:
    DEFAULT_RETENTION = timedelta(hours=24)

    def __init__(
        self,
        root: Path,
        *,
        retention: timedelta = DEFAULT_RETENTION,
        now: Callable[[], datetime] = _utc_now,
        failure_injector: Callable[[SitemapPublicationStage], None] | None = None,
    ):
        if not isinstance(retention, timedelta) or retention < timedelta(0):
            raise ValueError("retention must be a non-negative timedelta")
        if not callable(now):
            raise TypeError("now must be callable")
        if failure_injector is not None and not callable(failure_injector):
            raise TypeError("failure_injector must be callable")
        self.root = Path(root)
        self.retention = retention
        self.now = now
        self._failure_injector = failure_injector

    @classmethod
    def from_release_root(
        cls,
        release_root: Path | None = None,
        **kwargs,
    ) -> "SitemapBundleStore":
        base = (
            Path(release_root)
            if release_root is not None
            else Path(__file__).resolve().parents[1]
        )
        return cls(base / "agent" / "data" / "sitemap-bundles", **kwargs)

    def _reach_publication_stage(self, stage: SitemapPublicationStage) -> None:
        if self._failure_injector is not None:
            self._failure_injector(stage)

    def _write_active_pointer(self, payload: Mapping[str, object]) -> None:
        validated = _validate_pointer_payload(dict(payload))
        self._reach_publication_stage(
            SitemapPublicationStage.BEFORE_ACTIVE_POINTER_REPLACE
        )
        atomic_write_json(self.root / "active.json", validated)

    def _pointer_for_publish(self, prepared: _PreparedBundle) -> dict | None:
        active_stat = _lstat(self.root / "active.json")
        target = self.root / prepared.bundle.batch_revision
        target_stat = _lstat(target)
        if active_stat is None:
            revisions = _revision_entries(self.root)
            if not revisions:
                return None
            if revisions == (prepared.bundle.batch_revision,) and target_stat is not None:
                validate_completed_bundle_matches(target, prepared.bundle)
                return None
            raise SitemapStateUnavailable(
                "active sitemap pointer is missing beside immutable bundle state"
            )

        pointer = _read_active_pointer(self.root)
        active_revision = pointer["batch_revision"]
        if active_revision == prepared.bundle.batch_revision:
            if target_stat is None:
                raise SitemapStateUnavailable("active immutable sitemap bundle is missing")
            validate_completed_bundle_matches(target, prepared.bundle)
        else:
            _read_and_validate_bundle(self.root / active_revision, active_revision)
        return pointer

    def publish(self, bundle: StoredBundle) -> None:
        prepared = _prepare_bundle(bundle)
        with _root_lock(self.root, create=True):
            pointer = self._pointer_for_publish(prepared)
            target = self.root / prepared.bundle.batch_revision
            target_stat = _lstat(target)
            if target_stat is not None:
                validate_completed_bundle_matches(target, prepared.bundle)
            else:
                staging = self.root / (
                    f".{prepared.bundle.batch_revision}.{uuid4().hex}.staging"
                )
                renamed = False
                try:
                    write_bundle_and_fsync(staging, prepared.bundle)
                    os.replace(staging, target)
                    renamed = True
                    fsync_directory(self.root)
                    self._reach_publication_stage(
                        SitemapPublicationStage.AFTER_DIRECTORY_RENAME
                    )
                except BaseException:
                    if not renamed:
                        _remove_operation_staging(staging)
                    raise

            published_at = _format_publication_time(self.now)
            ledger = [] if pointer is None else list(pointer["published_batches"])
            ledger = [
                item
                for item in ledger
                if item["batch_revision"] != prepared.bundle.batch_revision
            ]
            ledger.append(
                {
                    "batch_revision": prepared.bundle.batch_revision,
                    "published_at": published_at,
                }
            )
            self._write_active_pointer(
                {
                    "batch_revision": prepared.bundle.batch_revision,
                    "published_at": published_at,
                    "published_batches": ledger,
                }
            )

    def load_active_on_startup(self) -> StoredBundle:
        return self.load_active()

    def load_active(self) -> StoredBundle:
        with _root_lock(self.root, create=False):
            pointer = _read_active_pointer(self.root)
            revision = pointer["batch_revision"]
            return _read_and_validate_bundle(self.root / revision, revision)

    def load_batch(self, revision: str) -> StoredBundle:
        with _root_lock(self.root, create=False):
            pointer = _read_active_pointer(self.root)
            revision = _validate_revision(revision, state_error=True)
            ledger_revisions = {
                item["batch_revision"] for item in pointer["published_batches"]
            }
            if revision not in ledger_revisions:
                raise SitemapStateUnavailable(
                    "requested sitemap bundle is not in the publication ledger"
                )
            return _read_and_validate_bundle(self.root / revision, revision)

    def list_batches(self) -> tuple[str, ...]:
        with _root_lock(self.root, create=False):
            pointer = _read_active_pointer(self.root)
            return tuple(
                item["batch_revision"] for item in pointer["published_batches"]
            )

    def cleanup(self) -> None:
        cutoff = self.now() - self.retention
        if cutoff.tzinfo is None or cutoff.utcoffset() != timedelta(0):
            raise ValueError("cleanup time must be UTC-aware")
        with _root_lock(self.root, create=False):
            pointer = _read_active_pointer(self.root)
            ledger = list(pointer["published_batches"])
            active = pointer["batch_revision"]
            previous = next(
                (
                    item["batch_revision"]
                    for item in reversed(ledger)
                    if item["batch_revision"] != active
                ),
                None,
            )
            keep = {active}
            if previous is not None:
                keep.add(previous)
            keep.update(
                item["batch_revision"]
                for item in ledger
                if _validate_timestamp(item["published_at"]) >= cutoff
            )
            retired = [
                item["batch_revision"]
                for item in ledger
                if item["batch_revision"] not in keep
            ]

            for item in ledger:
                revision = item["batch_revision"]
                _read_and_validate_bundle(self.root / revision, revision)

            filtered_ledger = [
                item for item in ledger if item["batch_revision"] in keep
            ]
            self._write_active_pointer(
                {
                    "batch_revision": active,
                    "published_at": pointer["published_at"],
                    "published_batches": filtered_ledger,
                }
            )
            for revision in retired:
                _remove_validated_bundle_directory(self.root, revision)
