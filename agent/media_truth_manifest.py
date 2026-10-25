"""Immutable Batch 21 media truth and legacy revocation loaders."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock


_MANIFEST_REL = Path("docs/standards/batch-21-media-truth.json")
_REVOCATIONS_REL = Path("docs/standards/r10.6-legacy-image-revocations.txt")
_REVISION = "batch-21-media-truth-v1"
_SCHEMA_VERSION = 1
_SOURCE_LEDGER_COMMIT = "68d59f0f"
_AI_EVIDENCE_COMMIT = "30a3fae9"
_MANIFEST_KEYS = {
    "schemaVersion",
    "revision",
    "sourceLedgerCommit",
    "aiEvidenceCommit",
    "delete",
    "ai_generated",
    "generated_placeholder",
}
_cache_lock = Lock()
_truth_cache: dict[Path, tuple[int, int, Batch21Truth, frozenset[str]]] = {}
_revoked_cache: dict[Path, tuple[tuple[int, int], tuple[int, int] | None, frozenset[str]]] = {}


@dataclass(frozen=True)
class Batch21Truth:
    schema_version: int
    revision: str
    source_ledger_commit: str
    ai_evidence_commit: str
    delete: tuple[str, ...]
    ai_generated: tuple[str, ...]
    generated_placeholder: tuple[str, ...]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _validate_manifest_metadata(payload: object) -> None:
    if not isinstance(payload, dict) or set(payload) != _MANIFEST_KEYS:
        raise ValueError("Batch 21 manifest has unexpected top-level keys")
    if (
        payload["schemaVersion"] != _SCHEMA_VERSION
        or payload["revision"] != _REVISION
        or payload["sourceLedgerCommit"] != _SOURCE_LEDGER_COMMIT
        or payload["aiEvidenceCommit"] != _AI_EVIDENCE_COMMIT
    ):
        raise ValueError("Batch 21 manifest metadata does not match the frozen contract")


def _validate_manifest_partitions(payload: dict) -> list[list[str]]:
    partitions = [payload[name] for name in ("delete", "ai_generated", "generated_placeholder")]
    if any(
        not isinstance(partition, list)
        or any(not isinstance(item, str) or not item for item in partition)
        or partition != sorted(set(partition))
        for partition in partitions
    ):
        raise ValueError("Batch 21 manifest partitions must be sorted, unique string lists")
    if tuple(map(len, partitions)) != (1, 2, 37):
        raise ValueError("Batch 21 manifest partition counts must be 1/2/37")
    if len(set().union(*map(set, partitions))) != 40:
        raise ValueError("Batch 21 manifest partitions must be disjoint and total 40 IDs")
    return partitions


def _file_sig(path: Path) -> tuple[int, int]:
    st = path.stat()
    return (st.st_mtime_ns, st.st_size)


def load_batch_21_truth(root: Path | None = None) -> Batch21Truth:
    resolved_root = (root or _repo_root()).resolve()
    path = resolved_root / _MANIFEST_REL
    mtime_ns, size = _file_sig(path)
    with _cache_lock:
        cached = _truth_cache.get(path)
        if cached is not None and cached[0] == mtime_ns and cached[1] == size:
            return cached[2]
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_manifest_metadata(payload)
    _validate_manifest_partitions(payload)
    truth = Batch21Truth(
        schema_version=payload["schemaVersion"],
        revision=payload["revision"],
        source_ledger_commit=payload["sourceLedgerCommit"],
        ai_evidence_commit=payload["aiEvidenceCommit"],
        delete=tuple(payload["delete"]),
        ai_generated=tuple(payload["ai_generated"]),
        generated_placeholder=tuple(payload["generated_placeholder"]),
    )
    delete_set = frozenset(truth.delete)
    with _cache_lock:
        _truth_cache[path] = (mtime_ns, size, truth, delete_set)
    return truth


def reviewed_removal_ids(root: Path) -> frozenset[str]:
    resolved_root = root.resolve()
    path = resolved_root / _MANIFEST_REL
    mtime_ns, size = _file_sig(path)
    with _cache_lock:
        cached = _truth_cache.get(path)
        if cached is not None and cached[0] == mtime_ns and cached[1] == size:
            return cached[3]
    return frozenset(load_batch_21_truth(resolved_root).delete)


def revoked_legacy_image_ids() -> frozenset[str]:
    return _load_revoked_legacy_image_ids(_repo_root())


def _parse_revocation_ids(lines: list[str]) -> tuple[str, ...]:
    if not lines or lines[0] != f"# Manifest revision: {_REVISION}":
        raise ValueError("legacy revocation inventory is not bound to the manifest revision")
    ids = tuple(line.strip() for line in lines[2:] if line.strip() and not line.startswith("#"))
    if ids != tuple(sorted(set(ids))):
        raise ValueError("legacy revocation inventory must be sorted and unique")
    return ids


def _load_revoked_legacy_image_ids(root: Path) -> frozenset[str]:
    resolved_root = root.resolve()
    path = resolved_root / _REVOCATIONS_REL
    if not path.exists():
        return frozenset()
    rev_sig = _file_sig(path)
    manifest_path = resolved_root / _MANIFEST_REL
    manifest_sig = _file_sig(manifest_path) if manifest_path.exists() else None
    with _cache_lock:
        cached = _revoked_cache.get(path)
        if cached is not None and cached[0] == rev_sig and cached[1] == manifest_sig:
            return cached[2]
    ids = _parse_revocation_ids(path.read_text(encoding="utf-8").splitlines())
    result = frozenset(ids)
    if manifest_sig is not None:
        truth = load_batch_21_truth(resolved_root)
        expected = truth.delete + truth.ai_generated + truth.generated_placeholder
        if result != frozenset(expected):
            raise ValueError("legacy revocation inventory does not match Batch 21 truth")
    with _cache_lock:
        _revoked_cache[path] = (rev_sig, manifest_sig, result)
    return result
