"""Immutable Batch 21 media truth and legacy revocation loaders."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


_MANIFEST_REL = Path("docs/standards/batch-21-media-truth.json")
_REVOCATIONS_REL = Path("docs/standards/r10.6-legacy-image-revocations.txt")
_REVISION = "batch-21-media-truth-v1"


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


def load_batch_21_truth(root: Path | None = None) -> Batch21Truth:
    path = (root or _repo_root()) / _MANIFEST_REL
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Batch21Truth(
        schema_version=payload["schemaVersion"],
        revision=payload["revision"],
        source_ledger_commit=payload["sourceLedgerCommit"],
        ai_evidence_commit=payload["aiEvidenceCommit"],
        delete=tuple(payload["delete"]),
        ai_generated=tuple(payload["ai_generated"]),
        generated_placeholder=tuple(payload["generated_placeholder"]),
    )


def reviewed_removal_ids(root: Path) -> frozenset[str]:
    return frozenset(load_batch_21_truth(root).delete)


def revoked_legacy_image_ids() -> frozenset[str]:
    return _load_revoked_legacy_image_ids(_repo_root())


def _load_revoked_legacy_image_ids(root: Path) -> frozenset[str]:
    path = root / _REVOCATIONS_REL
    if not path.exists():
        return frozenset()
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != f"# Manifest revision: {_REVISION}":
        raise ValueError("legacy revocation inventory is not bound to the manifest revision")
    ids = tuple(line.strip() for line in lines[2:] if line.strip() and not line.startswith("#"))
    if ids != tuple(sorted(set(ids))):
        raise ValueError("legacy revocation inventory must be sorted and unique")
    manifest_path = root / _MANIFEST_REL
    if manifest_path.exists():
        truth = load_batch_21_truth(root)
        expected = truth.delete + truth.ai_generated + truth.generated_placeholder
        if frozenset(ids) != frozenset(expected):
            raise ValueError("legacy revocation inventory does not match Batch 21 truth")
    return frozenset(ids)
