"""Shared, integrity-first backup manifest contract.

Every producer and consumer uses this small JSON-compatible envelope. Legacy
fields may remain alongside it during migration, but restore/offsite paths only
trust the normalized fields below.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

MANIFEST_SCHEMA = "vinhlong360-backup-manifest-v2"


def _validate_manifest_identity(manifest: "BackupManifest") -> None:
    if not manifest.artifact_id.strip() or not manifest.format.strip():
        raise ValueError("manifest artifact_id and format are required")
    if not isinstance(manifest.source_identity, dict):
        raise ValueError("manifest source_identity must be an object")


def _validate_manifest_counts(row_counts: dict[str, int]) -> None:
    if not isinstance(row_counts, dict) or any(
        not isinstance(key, str) or type(value) is not int or value < 0
        for key, value in row_counts.items()
    ):
        raise ValueError("manifest row_counts must contain non-negative integers")


def _validate_manifest_checksum(checksum: str) -> None:
    if len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum.lower()):
        raise ValueError("manifest checksum must be a SHA-256 hex digest")


def _manifest_schema(payload: Mapping[str, Any]) -> None:
    schema = payload.get("manifest_schema") or payload.get("schema")
    if schema not in {MANIFEST_SCHEMA, "vinhlong360-local-backup-v1", "vinhlong360-pg-backup-v1"}:
        raise ValueError("unsupported backup manifest schema")


def _manifest_artifact_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    artifact = payload.get("artifact") if isinstance(payload.get("artifact"), Mapping) else {}
    checksum = payload.get("checksum") or artifact.get("sha256")
    if not isinstance(checksum, str):
        raise ValueError("manifest checksum is required")
    artifact_id = payload.get("artifact_id") or payload.get("timestamp") or artifact.get("path")
    fmt = payload.get("format") or ("postgres.custom" if artifact.get("path", "").endswith(".dump") else "json+sqlite")
    return {"artifact_id": str(artifact_id or ""), "format": str(fmt), "checksum": checksum}


def _manifest_fields(payload: Mapping[str, Any]) -> tuple[dict[str, Any], str, dict[str, int], str, str]:
    _manifest_schema(payload)
    artifact_fields = _manifest_artifact_fields(payload)
    source = payload.get("source_identity") or payload.get("database_identity") or {}
    counts = payload.get("row_counts") if "row_counts" in payload else payload.get("counts", {})
    return (
        dict(source) if isinstance(source, Mapping) else {},
        artifact_fields["artifact_id"],
        _coerce_manifest_counts(counts),
        artifact_fields["format"],
        artifact_fields["checksum"],
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class BackupManifest:
    artifact_id: str
    format: str
    source_identity: dict[str, Any]
    row_counts: dict[str, int]
    checksum: str
    created_at: str

    def __post_init__(self) -> None:
        _validate_manifest_identity(self)
        _validate_manifest_counts(self.row_counts)
        _validate_manifest_checksum(self.checksum)
        if not self.created_at.strip():
            raise ValueError("manifest created_at is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": MANIFEST_SCHEMA,
            "artifact_id": self.artifact_id,
            "format": self.format,
            "source_identity": self.source_identity,
            "row_counts": self.row_counts,
            "checksum": self.checksum,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BackupManifest":
        if not isinstance(payload, Mapping):
            raise ValueError("backup manifest must be an object")
        source, artifact_id, clean_counts, fmt, checksum = _manifest_fields(payload)
        return cls(
            artifact_id=str(artifact_id or ""),
            format=str(fmt),
            source_identity=source,
            row_counts=clean_counts,
            checksum=checksum,
            created_at=str(payload.get("created_at") or payload.get("completed_at") or ""),
        )


@dataclass(frozen=True)
class RestoreReport:
    success: bool
    artifact_id: str
    row_counts: dict[str, int]
    evidence: dict[str, Any]


def load_manifest(path: Path) -> BackupManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return BackupManifest.from_dict(payload)


def write_manifest(path: Path, manifest: BackupManifest, *, extra: Mapping[str, Any] | None = None) -> Path:
    payload = manifest.to_dict()
    if extra:
        payload.update(dict(extra))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def validate_manifest_artifact(manifest: BackupManifest, artifact: Path) -> None:
    if not artifact.is_file():
        raise ValueError(f"backup artifact not found: {artifact}")
    observed = sha256_file(artifact)
    if observed != manifest.checksum:
        raise ValueError(f"backup checksum mismatch: expected {manifest.checksum}, got {observed}")


def validate_source_identity(manifest: BackupManifest, target_identity: Mapping[str, Any] | None) -> None:
    if target_identity is None:
        return
    for key, expected in manifest.source_identity.items():
        if key not in target_identity or target_identity[key] != expected:
            raise ValueError(f"backup source identity mismatch for {key}")


def _coerce_manifest_counts(counts: Any) -> dict[str, int]:
    if not isinstance(counts, Mapping):
        raise ValueError("manifest row_counts must be an object")
    clean_counts: dict[str, int] = {}
    for key, value in counts.items():
        if not isinstance(key, str) or type(value) is not int or value < 0:
            raise ValueError("manifest row_counts must contain non-negative integers")
        clean_counts[key] = value
    return clean_counts


def validate_row_counts(required: Mapping[str, int], observed: Mapping[str, int]) -> None:
    for table, expected in required.items():
        try:
            actual = int(observed[table])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"required row count missing: {table}") from exc
        if actual != expected:
            raise ValueError(f"required row count mismatch for {table}: expected {expected}, got {actual}")


def _manifest_artifact_path(manifest_path: Path, backup_dir: Path, manifest: BackupManifest) -> Path | None:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = (raw.get("artifact") or {}).get("path") or raw.get("artifact_path")
    if not isinstance(declared, str) or not declared.strip():
        return None
    artifact = (manifest_path.parent / declared).resolve()
    if backup_dir.resolve() not in artifact.parents or artifact.parent != manifest_path.parent.resolve():
        return None
    if not artifact.is_file():
        return None
    validate_manifest_artifact(manifest, artifact)
    return artifact


def _load_manifest_candidate(manifest_path: Path, backup_dir: Path) -> tuple[float, Path, BackupManifest] | None:
    try:
        manifest = load_manifest(manifest_path)
        artifact = _manifest_artifact_path(manifest_path, backup_dir, manifest)
        if artifact is None:
            return None
        return manifest_path.stat().st_mtime, manifest_path.parent, manifest
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def find_latest_manifest(backup_dir: Path) -> tuple[Path, BackupManifest] | None:
    candidates: list[tuple[float, Path, BackupManifest]] = []
    if not backup_dir.is_dir():
        return None
    paths = list(backup_dir.rglob("manifest.json")) + list(backup_dir.rglob("*.manifest.json"))
    for manifest_path in paths:
        candidate = _load_manifest_candidate(manifest_path, backup_dir)
        if candidate is not None:
            candidates.append(candidate)
    if not candidates:
        return None
    _, directory, manifest = max(candidates, key=lambda item: item[0])
    return directory, manifest
