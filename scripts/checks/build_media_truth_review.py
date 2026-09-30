#!/usr/bin/env python3
"""Build the final read-only media-truth owner review package.

This module only verifies already-produced evidence.  It deliberately renders
commands as inert review text; it never calls an apply, publish, backup, or
recovery operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.checks.build_media_truth_plan import sqlite_logical_digest
except ModuleNotFoundError:  # direct script execution from the repository root
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.checks.build_media_truth_plan import sqlite_logical_digest


class ReviewError(ValueError):
    """Raised when review evidence is incomplete or inconsistent."""


EXPECTED_SCOPE = {
    "records": 40,
    "deletedEntities": 1,
    "retainedPlaceholders": 37,
    "retainedAi": 2,
    "jsonRelationshipsDeleted": 6,
    "sqliteRelationshipsDeleted": 0,
}
EXPECTED_INVENTORY_COUNTS = {
    "ai-generated": 2,
    "documentary-candidate-missing-evidence": 1732,
    "generated-placeholder": 37,
}
EXPECTED_ARTIFACT_KEYS = {
    "batch_21_ledger",
    "data_review_manifest",
    "entity_index",
    "image_provenance_review",
    "llms",
    "llms_full",
    "renderer_registry",
}
EXPECTED_TARGET_IDS = (
    "ba-nhi-bun-bo-hue-vinh-long",
    "banh-canh-ben-tre",
    "banh-trang-my-long",
    "banh-xeo-mien-tay",
    "bo-nuong-la-lot",
    "bun-bo-co-tam-cho-ben-tre-ben-tre",
    "bun-mam-mien-tay",
    "ca-tai-tuong-chien-xu",
    "caffe-takeaway---tan-ke",
    "cha-gio-chay",
    "chao-ca-loc-rau-dang",
    "chuoi-nuong-gia-truyen",
    "co-dai---sinh-to-giai-khat",
    "com-chay-au-lac-vinh-long",
    "com-ga-xoi-mo-5-vi-ben-tre",
    "cua-com-duyen-hai",
    "duong-dua",
    "goi-cuon-tom-thit",
    "hot-pot-72---quan-lau",
    "khoi---lau-nuong",
    "kimchi-kimchi---mi-cay-han-quoc",
    "lau-bo",
    "lau-mam-ben-tre",
    "lau-tai-co",
    "lu-lu---cake-drink",
    "ma-van-tai-quan---pham-thai-buong",
    "mam-tom-cha-vinh-long",
    "mi-cay-vinh-long",
    "nem-nuong-thanh-binh-ben-tre",
    "nha-hang-thien-tan",
    "prov-1",
    "tep-rang-dua",
    "tiem-ba-khoang",
    "tinh-binh-chay-vinh-long",
    "tom-cang-xanh-nuong",
    "tom-cang-xanh-song-tien",
    "tom-rang-muoi-ot",
    "vys-house-drinks-tea---2-thang-9",
    "xoi-vi-mien-tay",
    "xom-nuong-que-nha",
)
EXPECTED_MUTATION_COUNTS = {
    ("json", "entity", "delete", "entity"): 1,
    ("json", "entity", "remove", "attributes.image_author"): 39,
    ("json", "entity", "remove", "attributes.image_caption"): 39,
    ("json", "entity", "remove", "attributes.image_license"): 39,
    ("json", "entity", "remove", "attributes.image_source"): 39,
    ("json", "entity", "update", "attributes.image_generation_model"): 2,
    ("json", "entity", "update", "attributes.image_generation_reference"): 2,
    ("json", "entity", "update", "attributes.image_type"): 39,
    ("json", "entity", "update", "attributes.is_verified_photo"): 39,
    ("json", "relationship", "delete", "relationship"): 6,
    ("sqlite", "entity", "delete", "entity"): 1,
    ("sqlite", "entity", "remove", "attributes.image_author"): 39,
    ("sqlite", "entity", "remove", "attributes.image_caption"): 39,
    ("sqlite", "entity", "remove", "attributes.image_license"): 39,
    ("sqlite", "entity", "remove", "attributes.image_source"): 39,
    ("sqlite", "entity", "update", "attributes.image_generation_model"): 2,
    ("sqlite", "entity", "update", "attributes.image_generation_reference"): 2,
    ("sqlite", "entity", "update", "attributes.image_type"): 39,
    ("sqlite", "entity", "update", "attributes.is_verified_photo"): 39,
}
PROTECTED_JSON = Path("web/data.json")
PROTECTED_SQLITE = Path("agent/data/vinhlong360.db")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ReviewError(f"unreadable file: {path}") from exc
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewError(f"invalid {label}: {path}") from exc


def _require_file(path: Path, label: str) -> Path:
    raw = Path(path)
    if raw.is_symlink() or not raw.is_file():
        raise ReviewError(f"missing or unsafe {label}: {raw}")
    resolved = raw.resolve()
    if resolved != raw.absolute() and raw.is_symlink():
        raise ReviewError(f"symlink is not allowed for {label}: {raw}")
    return resolved


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read_only_marker(payload: Mapping[str, Any], label: str) -> None:
    if payload.get("mutationAllowed") is not False:
        raise ReviewError(f"{label} must set mutationAllowed=false")
    for key in ("applyAuthorization", "authorized", "authorization"):
        if payload.get(key) is True:
            raise ReviewError(f"{label} contains an authorization marker")


def _canonical_plan(plan_path: Path, approved_plan_path: Path) -> tuple[dict[str, Any], str]:
    plan_path = _require_file(plan_path, "plan")
    approved_plan_path = _require_file(approved_plan_path, "approved plan")
    plan_bytes = plan_path.read_bytes()
    if plan_bytes != approved_plan_path.read_bytes():
        raise ReviewError("approved plan bytes do not match canonical plan")
    plan = _load_json(plan_path, "plan")
    if not isinstance(plan, dict):
        raise ReviewError("plan must be an object")
    _read_only_marker(plan, "plan")
    if plan.get("status") != "review_required":
        raise ReviewError("plan is not review_required")
    if plan.get("mode") != "media-truth-reconciliation":
        raise ReviewError("plan mode mismatch")
    digest = _sha(plan_path)
    if plan.get("planSha256") not in (None, digest):
        raise ReviewError("planSha256 does not bind canonical plan bytes")
    return plan, digest


def _load_candidate_files(stage_result_path: Path) -> tuple[Path, dict[str, Any], Path, Path]:
    stage_result_path = _require_file(stage_result_path, "stage result")
    candidate = stage_result_path.parent.resolve()
    stage = _load_json(stage_result_path, "stage result")
    if not isinstance(stage, dict):
        raise ReviewError("stage result must be an object")
    _read_only_marker(stage, "stage result")
    data_path = _require_file(candidate / "data.json", "candidate JSON")
    sqlite_path = _require_file(candidate / "vinhlong360.db", "candidate SQLite")
    return stage_result_path, stage, data_path, sqlite_path


def _validate_stage_assets(stage: Mapping[str, Any]) -> None:
    assets = stage.get("assets")
    if not isinstance(assets, dict) or not isinstance(assets.get("retained"), list) or not isinstance(assets.get("removed"), list):
        raise ReviewError("stage result asset partitions are malformed")
    if [item.get("id") for item in assets["removed"] if isinstance(item, dict)] != ["prov-1"]:
        raise ReviewError("stage result must contain exactly the prov-1 removal")


def _validate_candidate_payload(data_path: Path) -> list[dict[str, Any]]:
    candidate_payload = _load_json(data_path, "candidate JSON")
    entities = candidate_payload.get("entities") if isinstance(candidate_payload, dict) else None
    if not isinstance(entities, list) or len(entities) != 1771:
        raise ReviewError("candidate JSON must contain exactly 1771 entities")
    if any(not isinstance(item, dict) or not isinstance(item.get("id"), str) for item in entities):
        raise ReviewError("candidate entity identity is malformed")
    if "prov-1" in {item["id"] for item in entities}:
        raise ReviewError("tombstoned prov-1 is present in candidate")
    return entities


def _validate_candidate_sidecars(candidate: Path) -> None:
    sidecars = [candidate / f"vinhlong360.db{suffix}" for suffix in ("-wal", "-shm", "-journal")]
    if any(path.exists() for path in sidecars):
        raise ReviewError("candidate SQLite sidecar is present")


def _validate_candidate_digests(plan: Mapping[str, Any], data_path: Path, sqlite_path: Path) -> tuple[str, str]:
    expected = plan.get("expectedOutputs")
    if not isinstance(expected, dict):
        raise ReviewError("plan expectedOutputs are missing")
    data_sha = _sha(data_path)
    if expected.get("jsonSha256") != data_sha:
        raise ReviewError("candidate JSON digest does not match plan")
    candidate_logical = sqlite_logical_digest(sqlite_path)
    if expected.get("sqliteLogicalDigest") != candidate_logical:
        raise ReviewError("candidate SQLite logical digest does not match plan")
    with sqlite3.connect(sqlite_path) as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise ReviewError("candidate SQLite integrity check failed")
    return data_sha, candidate_logical


def _validate_inventory(root: Path, inventory_path: Path, data_sha: str) -> dict[str, Any]:
    inventory = _load_json(_require_file(inventory_path, "inventory"), "inventory")
    if not isinstance(inventory, dict):
        raise ReviewError("inventory must be an object")
    _read_only_marker(inventory, "inventory")
    items = inventory.get("items")
    counts = inventory.get("counts")
    if not isinstance(items, list) or len(items) != 1771 or counts != EXPECTED_INVENTORY_COUNTS:
        raise ReviewError("inventory row count or taxonomy counts do not match reviewed scope")
    if inventory.get("candidate", {}).get("dataSha256") != data_sha:
        raise ReviewError("inventory is not bound to candidate JSON")
    if any(item.get("proposedMutation") is not None for item in items if isinstance(item, dict)):
        raise ReviewError("inventory contains a proposed mutation")
    return {
        "path": _relative(root, Path(inventory_path)),
        "sha256": _sha(Path(inventory_path)),
        "rows": len(items),
        "counts": counts,
    }


def _plan_mutations(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mutations = plan.get("mutations")
    if not isinstance(mutations, list) or any(not isinstance(item, dict) for item in mutations):
        raise ReviewError("plan mutations are malformed")
    return mutations


def _validate_plan_targets(mutations: list[Mapping[str, Any]]) -> list[str]:
    target_ids = sorted({item.get("recordId") for item in mutations if item.get("recordType") == "entity"})
    if target_ids != list(EXPECTED_TARGET_IDS):
        raise ReviewError("plan entity target ID set mismatch")
    return target_ids


def _validate_mutation_counts(mutations: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    observed = Counter((item.get("store"), item.get("recordType"), item.get("operation"), item.get("field")) for item in mutations)
    if dict(observed) != EXPECTED_MUTATION_COUNTS:
        raise ReviewError("plan mutation-count map mismatch")
    return [
        {"store": store, "recordType": record_type, "operation": operation, "field": field, "count": observed[(store, record_type, operation, field)]}
        for store, record_type, operation, field in sorted(EXPECTED_MUTATION_COUNTS)
    ]


def _validate_relationship_scope(mutations: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    expected_relationships = {
        ("prov-1", "banh-xeo-mien-tay", "near"), ("prov-1", "com-tam-co-tuyet", "near"),
        ("prov-1", "cong-ty-tnhh-mtv-quoc-thao", "near"), ("prov-1", "khu-du-lich-truong-huy", "near"),
        ("prov-1", "mekong-pottery-homestay", "near"), ("prov-1", "vinh-long", "located_in"),
    }
    relationships = {
        ((item.get("before") or {}).get("from"), (item.get("before") or {}).get("to"), (item.get("before") or {}).get("type"))
        for item in mutations if item.get("recordType") == "relationship"
    }
    if relationships != expected_relationships:
        raise ReviewError("plan relationship triples mismatch")
    return [{"from": source, "to": target, "type": relation_type} for source, target, relation_type in sorted(relationships)]


def _validate_plan_scope(plan: Mapping[str, Any]) -> dict[str, Any]:
    summary = plan.get("summary")
    if not isinstance(summary, dict):
        raise ReviewError("plan summary is missing")
    expected_summary = {
        "batch21Records": EXPECTED_SCOPE["records"],
        "deletedEntities": EXPECTED_SCOPE["deletedEntities"],
        "retainedPlaceholders": EXPECTED_SCOPE["retainedPlaceholders"],
        "retainedAi": EXPECTED_SCOPE["retainedAi"],
        "jsonRelationshipsDeleted": EXPECTED_SCOPE["jsonRelationshipsDeleted"],
        "sqliteRelationshipsDeleted": EXPECTED_SCOPE["sqliteRelationshipsDeleted"],
    }
    if any(summary.get(key) != value for key, value in expected_summary.items()):
        raise ReviewError("plan scope summary mismatch")
    mutations = _plan_mutations(plan)
    return {
        "targetIds": _validate_plan_targets(mutations),
        "relationshipTriples": _validate_relationship_scope(mutations),
        "mutationCounts": _validate_mutation_counts(mutations),
    }


def _validate_candidate(root: Path, plan: Mapping[str, Any], stage_result_path: Path, inventory_path: Path) -> dict[str, Any]:
    stage_result_path, stage, data_path, sqlite_path = _load_candidate_files(stage_result_path)
    candidate = stage_result_path.parent.resolve()
    _validate_stage_assets(stage)
    _validate_candidate_payload(data_path)
    _validate_candidate_sidecars(candidate)
    data_sha, candidate_logical = _validate_candidate_digests(plan, data_path, sqlite_path)
    inventory = _validate_inventory(root, inventory_path, data_sha)
    plan_scope = _validate_plan_scope(plan)
    return {
        "root": _relative(root, candidate),
        "stageResult": {"path": _relative(root, stage_result_path), "sha256": _sha(stage_result_path)},
        "data": {"path": _relative(root, data_path), "sha256": data_sha},
        "sqlite": {"path": _relative(root, sqlite_path), "sha256": _sha(sqlite_path), "logicalDigest": candidate_logical},
        "inventory": inventory,
        "scope": plan_scope,
    }


def _validate_artifact_manifest(manifest_path: Path) -> tuple[Path, list[dict[str, Any]]]:
    manifest_path = _require_file(manifest_path, "artifact manifest")
    manifest = _load_json(manifest_path, "artifact manifest")
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 1:
        raise ReviewError("artifact manifest schema mismatch")
    entries = manifest.get("artifacts")
    if not isinstance(entries, list) or len(entries) != len(EXPECTED_ARTIFACT_KEYS):
        raise ReviewError("artifact manifest is incomplete")
    seen_keys: set[str] = set()
    seen_paths: set[str] = set()
    members: list[dict[str, Any]] = []
    for item in entries:
        members.append(_validate_artifact_member(manifest_path, item, seen_keys, seen_paths))
    if seen_keys != EXPECTED_ARTIFACT_KEYS:
        raise ReviewError("artifact manifest key set mismatch")
    return manifest_path, members


def _validate_artifact_member(
    manifest_path: Path,
    item: Any,
    seen_keys: set[str],
    seen_paths: set[str],
) -> dict[str, Any]:
    if not isinstance(item, dict) or not isinstance(item.get("key"), str) or not isinstance(item.get("path"), str):
        raise ReviewError("artifact manifest member is malformed")
    key, relative = item["key"], item["path"].replace("\\", "/")
    if key in seen_keys or relative in seen_paths or relative.startswith("/") or ".." in Path(relative).parts:
        raise ReviewError("artifact manifest contains duplicate or unsafe member")
    seen_keys.add(key)
    seen_paths.add(relative)
    member = _require_file(manifest_path.parent / relative, f"artifact member {key}")
    observed = {"bytes": member.stat().st_size, "sha256": _sha(member)}
    if item.get("bytes") != observed["bytes"] or item.get("sha256") != observed["sha256"]:
        raise ReviewError(f"artifact member hash mismatch: {key}")
    return {"key": key, "path": relative, **observed}


def _validate_review_artifact(manifest_path: Path, members: list[dict[str, Any]]) -> list[Any]:
    review_member = next(item for item in members if item["key"] == "data_review_manifest")
    review_payload = _load_json(manifest_path.parent / review_member["path"], "data review manifest")
    if not isinstance(review_payload, dict):
        raise ReviewError("data review manifest is malformed")
    _read_only_marker(review_payload, "data review manifest")
    findings = review_payload.get("findings")
    if not isinstance(findings, list):
        raise ReviewError("data review findings are malformed")
    _reject_load_bearing_findings(findings)
    return findings


def _validate_provenance_artifact(manifest_path: Path, members: list[dict[str, Any]]) -> None:
    provenance = next(item for item in members if item["key"] == "image_provenance_review")
    provenance_payload = _load_json(manifest_path.parent / provenance["path"], "image provenance review")
    if not isinstance(provenance_payload, dict) or len(provenance_payload.get("records", [])) != EXPECTED_SCOPE["records"]:
        raise ReviewError("image provenance scope must contain 40 records")
    _read_only_marker(provenance_payload, "image provenance review")


def _validate_artifacts(root: Path, manifest_path: Path) -> dict[str, Any]:
    manifest_path, members = _validate_artifact_manifest(manifest_path)
    findings = _validate_review_artifact(manifest_path, members)
    _validate_provenance_artifact(manifest_path, members)
    return {"path": _relative(root, manifest_path), "sha256": _sha(manifest_path), "members": members, "findings": findings}


def _reject_load_bearing_findings(findings: list[Any]) -> None:
    for finding in findings:
        if not isinstance(finding, dict):
            raise ReviewError("finding is malformed")
        severity = str(finding.get("severity", "")).lower()
        status = str(finding.get("status", finding.get("state", "open"))).lower()
        if severity in {"critical", "important"} and status not in {"closed", "resolved", "accepted", "parked"}:
            raise ReviewError("open Critical/Important finding blocks owner review")


def _validate_protected_sources(root: Path, plan: Mapping[str, Any]) -> tuple[Path, Path, str]:
    source_json = _require_file(root / PROTECTED_JSON, "protected JSON")
    source_sqlite = _require_file(root / PROTECTED_SQLITE, "protected SQLite")
    sidecars = [source_sqlite.with_name(source_sqlite.name + suffix) for suffix in ("-wal", "-shm", "-journal")]
    if any(path.exists() for path in sidecars):
        raise ReviewError("protected SQLite sidecar is present")
    plan_inputs = plan.get("inputs")
    if not isinstance(plan_inputs, dict) or plan_inputs.get("json", {}).get("sha256") != _sha(source_json) or plan_inputs.get("sqlite", {}).get("sha256") != _sha(source_sqlite):
        raise ReviewError("protected input hash drift")
    source_sqlite_logical = sqlite_logical_digest(source_sqlite)
    with sqlite3.connect(source_sqlite) as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
    if not integrity or integrity[0] != "ok":
        raise ReviewError("protected SQLite integrity check failed")
    return source_json, source_sqlite, source_sqlite_logical


def _validate_backup_files(backup_dir: Path, source_json: Path, source_sqlite: Path, source_sqlite_logical: str) -> tuple[Path, Path, Path, dict[str, Any], str]:
    backup_dir = Path(backup_dir).resolve()
    manifest_path = _require_file(backup_dir / "manifest.json", "backup manifest")
    manifest = _load_json(manifest_path, "backup manifest")
    copied = manifest.get("copied") if isinstance(manifest, dict) else None
    if copied != ["web/data.json", "agent/data/vinhlong360.db"]:
        raise ReviewError("backup manifest copied-file list mismatch")
    backup_json = _require_file(backup_dir / "data.json", "backup JSON")
    backup_sqlite = _require_file(backup_dir / "vinhlong360.db", "backup SQLite")
    if backup_json.read_bytes() != source_json.read_bytes():
        raise ReviewError("backup JSON is not byte-equal to protected JSON")
    backup_sqlite_logical = sqlite_logical_digest(backup_sqlite)
    with sqlite3.connect(backup_sqlite) as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise ReviewError("backup SQLite integrity check failed")
    if backup_sqlite_logical != source_sqlite_logical:
        raise ReviewError("backup SQLite logical digest mismatch")
    return manifest_path, backup_json, backup_sqlite, manifest, backup_sqlite_logical


def _validate_backup_manifest_hash(manifest: Mapping[str, Any], backup_json: Path) -> None:
    artifact = manifest.get("artifact") if isinstance(manifest, dict) else None
    declared_checksum = (artifact or {}).get("sha256") if isinstance(artifact, dict) else manifest.get("checksum")
    if declared_checksum != _sha(backup_json):
        raise ReviewError("backup manifest JSON hash mismatch")


def _validate_protected_and_backup(root: Path, backup_dir: Path, plan: Mapping[str, Any]) -> dict[str, Any]:
    source_json, source_sqlite, source_sqlite_logical = _validate_protected_sources(root, plan)
    manifest_path, backup_json, backup_sqlite, manifest, backup_sqlite_logical = _validate_backup_files(backup_dir, source_json, source_sqlite, source_sqlite_logical)
    _validate_backup_manifest_hash(manifest, backup_json)
    return {
        "manifest": {"path": _relative(root, manifest_path), "sha256": _sha(manifest_path)},
        "copiedFiles": {
            "json": {"path": _relative(root, backup_json), "sha256": _sha(backup_json), "byteEqualToProtected": True},
            "sqlite": {"path": _relative(root, backup_sqlite), "sha256": _sha(backup_sqlite), "logicalDigest": backup_sqlite_logical, "integrity": "ok"},
        },
        "protected": {
            "json": {"path": _relative(root, source_json), "sha256": _sha(source_json)},
            "sqlite": {"path": _relative(root, source_sqlite), "sha256": _sha(source_sqlite), "logicalDigest": source_sqlite_logical, "integrity": "ok"},
        },
    }


def _validate_evidence_schema(path: Path) -> dict[str, Any]:
    evidence = _load_json(path, "test evidence")
    if not isinstance(evidence, dict) or set(evidence) != {"schemaVersion", "commands", "knownBaseline", "openFindings", "generatedArtifacts"} or evidence.get("schemaVersion") != 1:
        raise ReviewError("test evidence schema mismatch")
    for key in ("mutationAllowed", "applyAuthorization", "authorized", "authorization"):
        if evidence.get(key) is True:
            raise ReviewError(f"test evidence contains an authorization marker: {key}")
    return evidence


def _validate_evidence_commands(evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    checks = evidence.get("commands")
    if not isinstance(checks, list) or not checks or any(
        not isinstance(item, dict)
        or not isinstance(item.get("command"), str)
        or not isinstance(item.get("exitCode"), int)
        or not isinstance(item.get("resultClassification"), str)
        or not isinstance(item.get("outputSha256"), str)
        or (item["exitCode"] != 0 and item["resultClassification"] == "passed")
        for item in checks
    ):
        raise ReviewError("test evidence commands are malformed")
    return checks


def _validate_evidence_markers(evidence: Mapping[str, Any]) -> None:
    markers = evidence.get("generatedArtifacts")
    if not isinstance(markers, dict) or any(markers.get(key) is not True for key in ("plan", "candidate", "inventory", "artifacts")):
        raise ReviewError("deterministic-generation markers are incomplete")
    if not isinstance(evidence.get("knownBaseline"), list) or not all(isinstance(item, str) for item in evidence["knownBaseline"]):
        raise ReviewError("knownBaseline must be a list of strings")


def _validate_evidence_findings(evidence: Mapping[str, Any]) -> list[Any]:
    findings = evidence.get("openFindings", [])
    if not isinstance(findings, list):
        raise ReviewError("test evidence findings are malformed")
    _reject_load_bearing_findings(findings)
    return findings


def _validate_test_evidence(root: Path, path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = _require_file(path, "test evidence")
    evidence = _validate_evidence_schema(path)
    checks = _validate_evidence_commands(evidence)
    _validate_evidence_markers(evidence)
    _validate_evidence_findings(evidence)
    return evidence, {"path": _relative(root, path), "sha256": _sha(path), "checks": len(checks)}


def render_non_authorizing_apply_command(
    approved_plan_path: Path,
    *,
    sqlite_path: Path,
    json_path: Path,
    sqlite_backup: Path,
    json_backup: Path,
    plan_sha256: str,
    lock_path: Path,
    journal_path: Path,
) -> str:
    """Render an inert, digest-bound apply command for owner review."""
    if len(plan_sha256) != 64 or any(char not in "0123456789abcdef" for char in plan_sha256.lower()):
        raise ReviewError("plan_sha256 must be a SHA-256 digest")
    return (
        "# mutationAllowed=false doNotExecute=true owner_approval_required\n"
        "python scripts/checks/apply_data_reconciliation.py "
        f"--plan {Path(approved_plan_path)} --sqlite {Path(sqlite_path)} --json {Path(json_path)} "
        f"--sqlite-backup {Path(sqlite_backup)} --json-backup {Path(json_backup)} "
        f"--plan-sha256 {plan_sha256} --lock-path {Path(lock_path)} --journal-path {Path(journal_path)} --maintenance-window --confirm-phase-b --allow-live-protected-inputs"
    )


def render_recovery_command(journal_path: Path, *, sqlite_backup: Path, json_backup: Path) -> str:
    """Render an inert recovery command bound to the reviewed backups."""
    lock_path = Path(journal_path).with_name(".reconciliation.lock")
    return (
        "# mutationAllowed=false doNotExecute=true owner_approval_required\n"
        "python scripts/checks/apply_data_reconciliation.py --recover-phase-b-journal "
        f"--journal-path {Path(journal_path)} --lock-path {lock_path} "
        f"--sqlite-backup {Path(sqlite_backup)} --json-backup {Path(json_backup)}"
    )


def build_review_package(
    root: Path,
    *,
    plan_path: Path,
    approved_plan_path: Path,
    stage_result_path: Path,
    inventory_path: Path,
    artifact_manifest_path: Path,
    backup_dir: Path,
    test_evidence_path: Path,
) -> dict[str, Any]:
    """Validate all pre-apply evidence and return a non-authorizing package."""
    root = Path(root).resolve()
    plan, plan_sha = _canonical_plan(plan_path, approved_plan_path)
    candidate = _validate_candidate(root, plan, stage_result_path, inventory_path)
    scope_details = candidate.pop("scope")
    artifacts = _validate_artifacts(root, artifact_manifest_path)
    evidence, evidence_ref = _validate_test_evidence(root, test_evidence_path)
    approved_plan = Path(approved_plan_path).resolve()
    sqlite_path = root / PROTECTED_SQLITE
    json_path = root / PROTECTED_JSON
    lock_path = root / ".tmp/media-truth-approved/.reconciliation.lock"
    journal_path = root / ".tmp/media-truth-approved/media-truth-apply-journal.json"
    apply_command = render_non_authorizing_apply_command(
        approved_plan,
        sqlite_path=sqlite_path,
        json_path=json_path,
        sqlite_backup=Path(backup_dir) / "vinhlong360.db",
        json_backup=Path(backup_dir) / "data.json",
        plan_sha256=plan_sha,
        lock_path=lock_path,
        journal_path=journal_path,
    )
    recovery_command = render_recovery_command(
        journal_path,
        sqlite_backup=Path(backup_dir) / "vinhlong360.db",
        json_backup=Path(backup_dir) / "data.json",
    )
    open_findings = list(artifacts["findings"]) + list(evidence.get("findings", []))
    _reject_load_bearing_findings(open_findings)
    backup = _validate_protected_and_backup(root, backup_dir, plan)
    return {
        "schemaVersion": 1,
        "status": "ready_for_owner_review",
        "mutationAllowed": False,
        "plan": {"path": _relative(root, Path(plan_path)), "approvedPath": _relative(root, approved_plan), "sha256": plan_sha, "status": plan["status"], "mutationAllowed": False},
        "candidate": candidate,
        "scope": {"counts": {
            "batch21Records": EXPECTED_SCOPE["records"],
            "deletedEntities": EXPECTED_SCOPE["deletedEntities"],
            "retainedPlaceholders": EXPECTED_SCOPE["retainedPlaceholders"],
            "retainedAi": EXPECTED_SCOPE["retainedAi"],
            "jsonRelationshipsDeleted": EXPECTED_SCOPE["jsonRelationshipsDeleted"],
            "sqliteRelationshipsDeleted": EXPECTED_SCOPE["sqliteRelationshipsDeleted"],
        }, "inventoryRows": candidate["inventory"]["rows"], "inventoryCounts": candidate["inventory"]["counts"], **scope_details},
        "tests": [evidence_ref],
        "protectedInputs": backup["protected"],
        "backupProcedure": {"status": "verified", "mutationAllowed": False, "manifestSha256": backup["manifest"]["sha256"], **backup},
        "applyProcedure": {"status": "ready_for_owner_review", "mutationAllowed": False, "authorization": "owner_approval_required", "doNotExecute": True, "approvedPlanPath": _relative(root, approved_plan), "command": apply_command},
        "recoveryProcedure": {"status": "ready_for_owner_review", "mutationAllowed": False, "authorization": "owner_approval_required", "doNotExecute": True, "command": recovery_command},
        "openFindings": open_findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--approved-plan", type=Path, required=True)
    parser.add_argument("--stage-result", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--artifact-manifest", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--test-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        package = build_review_package(
            args.root,
            plan_path=args.plan,
            approved_plan_path=args.approved_plan,
            stage_result_path=args.stage_result,
            inventory_path=args.inventory,
            artifact_manifest_path=args.artifact_manifest,
            backup_dir=args.backup_dir,
            test_evidence_path=args.test_evidence,
        )
        output = Path(args.output).resolve()
        if output in {(Path(args.root).resolve() / PROTECTED_JSON), (Path(args.root).resolve() / PROTECTED_SQLITE)}:
            raise ReviewError("review output collides with protected store")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(package, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        print(json.dumps({"output": str(output), "mutationAllowed": False, "status": package["status"]}, sort_keys=True))
        return 0
    except (ReviewError, OSError, sqlite3.Error, TypeError, ValueError) as exc:
        print(f"media truth review refused: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
