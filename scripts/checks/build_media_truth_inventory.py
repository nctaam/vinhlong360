#!/usr/bin/env python3
"""Build a deterministic, non-authorizing media-truth inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.generate_llms_txt import sourced_photo_evidence


class InventoryError(ValueError):
    """Raised when candidate evidence cannot be verified fail-closed."""


CLASSIFICATIONS = (
    "generated-placeholder",
    "ai-generated",
    "rights-cleared",
    "documentary-candidate-missing-evidence",
    "unknown-quarantined",
)
DOCUMENTARY_TYPES = {"documentary", "journalistic", "official", "press"}
TRUTH_KEYS = {"schemaVersion", "revision", "sourceLedgerCommit", "aiEvidenceCommit", "delete", "ai_generated", "generated_placeholder"}
TRUTH_METADATA = {
    "schemaVersion": 1,
    "revision": "batch-21-media-truth-v1",
    "sourceLedgerCommit": "68d59f0f",
    "aiEvidenceCommit": "30a3fae9",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(path: Path, root: Path) -> Path:
    resolved = path.resolve(strict=False)
    root_resolved = root.resolve(strict=False)
    try:
        if os.path.commonpath((str(resolved), str(root_resolved))) != str(root_resolved):
            raise InventoryError(f"path escapes candidate root: {path}")
    except ValueError as exc:
        raise InventoryError(f"path is not on the candidate volume: {path}") from exc
    return resolved


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InventoryError(f"invalid {label}: {path}") from exc


def _truth_partition(truth: dict[str, Any], key: str) -> set[str]:
    values = truth.get(key)
    if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
        raise InventoryError(f"truth manifest field {key} must be a list of IDs")
    if values != sorted(set(values)):
        raise InventoryError(f"truth manifest field {key} must be sorted and unique")
    return set(values)


def _truth_sets(truth_path: Path) -> dict[str, set[str]]:
    truth = _load_json(truth_path, "truth manifest")
    if not isinstance(truth, dict) or set(truth) != TRUTH_KEYS:
        raise InventoryError("truth manifest schema mismatch")
    if {key: truth.get(key) for key in TRUTH_METADATA} != TRUTH_METADATA:
        raise InventoryError("truth manifest schema mismatch")
    sets = {key: _truth_partition(truth, key) for key in ("delete", "ai_generated", "generated_placeholder")}
    if sets["delete"] & (sets["ai_generated"] | sets["generated_placeholder"]):
        raise InventoryError("truth manifest classifications overlap deleted IDs")
    if sets["ai_generated"] & sets["generated_placeholder"]:
        raise InventoryError("truth manifest classifications overlap")
    if tuple(len(sets[key]) for key in ("delete", "ai_generated", "generated_placeholder")) != (1, 2, 37):
        raise InventoryError("truth manifest partition counts must be 1/2/37")
    if len(set.union(*sets.values())) != 40:
        raise InventoryError("truth manifest partitions must contain 40 IDs")
    return sets


def _relative_image_path(image: str, entity_id: str) -> str:
    normalized = image.replace("\\", "/").lstrip("/")
    marker = "img/entities/"
    if normalized.startswith(marker):
        relative = normalized[len(marker) :]
    elif "/" not in normalized:
        relative = Path(normalized).name
    else:
        raise InventoryError(f"unsafe image path for {entity_id}: {image}")
    if not relative or relative in {".", ".."} or Path(relative).name != relative:
        raise InventoryError(f"unsafe image path for {entity_id}: {image}")
    return relative


def _image_paths(entity: dict[str, Any], asset_root: Path) -> list[tuple[str, Path]]:
    images = entity.get("images")
    if not isinstance(images, list) or not images or any(not isinstance(value, str) or not value.strip() for value in images):
        raise InventoryError(f"entity {entity.get('id')} has no valid image list")
    result: list[tuple[str, Path]] = []
    for image in images:
        relative = _relative_image_path(image, entity["id"])
        path = _inside(asset_root / relative, asset_root)
        if not path.is_file():
            raise InventoryError(f"missing image asset for {entity.get('id')}: {relative}")
        result.append((f"public/img/entities/{relative}", path))
    return result


def _retained_asset(item: Any) -> tuple[str, str, str | None]:
    if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("sha256"), str):
        raise InventoryError("candidate stage result contains malformed asset identity")
    source_hash = item.get("sourceSha256")
    if source_hash is not None and not isinstance(source_hash, str):
        raise InventoryError(f"staged source hash is malformed: {item['id']}")
    return item["id"], item["sha256"], source_hash


def _stage_lists(root: Path) -> tuple[list[Any], list[Any]]:
    stage_path = root / "stage-result.json"
    if not stage_path.is_file():
        raise InventoryError("candidate stage result is missing")
    stage = _load_json(stage_path, "stage result")
    if not isinstance(stage, dict) or stage.get("mutationAllowed") is not False:
        raise InventoryError("candidate stage result must be non-authorizing")
    assets = stage.get("assets")
    if not isinstance(assets, dict) or not isinstance(assets.get("retained"), list) or not isinstance(assets.get("removed"), list):
        raise InventoryError("candidate stage result must contain retained and removed asset lists")
    return assets["retained"], assets["removed"]


def _actual_asset_hashes(root: Path) -> dict[str, str]:
    asset_root = root / "public/img/entities"
    paths = [path for path in asset_root.glob("*") if path.is_file()]
    actual = {path.stem: _sha256(path) for path in paths}
    if len(actual) != len(paths):
        raise InventoryError("candidate asset filenames are not unique by entity ID")
    return actual


def _retained_hashes(retained: list[Any]) -> dict[str, str]:
    expected: dict[str, str] = {}
    for item in retained:
        entity_id, digest, source_hash = _retained_asset(item)
        if entity_id in expected:
            raise InventoryError(f"duplicate staged asset: {entity_id}")
        if source_hash is not None and source_hash != digest:
            raise InventoryError(f"staged source hash mismatch: {entity_id}")
        expected[entity_id] = digest
    return expected


def _validate_removed_assets(removed: list[Any], truth: dict[str, set[str]]) -> None:
    if any(not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("sha256"), str) for item in removed):
        raise InventoryError("candidate stage result contains malformed removed asset")
    if [item["id"] for item in removed] != sorted(truth["delete"]):
        raise InventoryError("staged removed assets do not match the frozen delete partition")


def _stage_asset_hashes(root: Path, truth: dict[str, set[str]]) -> dict[str, str]:
    retained, removed = _stage_lists(root)
    expected = _retained_hashes(retained)
    _validate_removed_assets(removed, truth)
    actual = _actual_asset_hashes(root)
    if set(expected) != set(actual) or any(expected[key] != actual[key] for key in actual):
        raise InventoryError("staged retained assets do not match candidate asset hashes")
    return expected


def _missing_requirements(attrs: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in ("image_author", "image_source", "image_license"):
        if not isinstance(attrs.get(field), str) or not attrs[field].strip():
            missing.append(field)
    source_url = attrs.get("image_source_url")
    if not isinstance(source_url, str) or not source_url.strip().startswith(("http://", "https://")):
        missing.append("image-specific source URL")
    permission = attrs.get("permission_evidence") or attrs.get("rights_evidence") or attrs.get("permission")
    if not isinstance(permission, str) or not permission.strip():
        missing.append("explicit permission evidence")
    if not sourced_photo_evidence(attrs):
        missing.append("license or re-host scope")
    return sorted(set(missing))


def _truth_classification(entity_id: str, attrs: dict[str, Any], truth: dict[str, set[str]]) -> tuple[str, str, str, list[str]] | None:
    if entity_id in truth["delete"]:
        raise InventoryError(f"deleted entity present in candidate: {entity_id}")
    if entity_id in truth["ai_generated"]:
        if (
            attrs.get("image_type") != "ai-generated"
            or attrs.get("is_verified_photo") is not False
            or not attrs.get("image_generation_reference")
        ):
            raise InventoryError(f"AI entity lacks explicit generation evidence: {entity_id}")
        return "ai-generated", "Batch 21 truth manifest with explicit generation reference", "non_photographic", []
    if entity_id in truth["generated_placeholder"]:
        if attrs.get("image_type") != "generated-placeholder" or attrs.get("is_verified_photo") is not False:
            raise InventoryError(f"placeholder entity lacks explicit placeholder type: {entity_id}")
        return "generated-placeholder", "Batch 21 truth manifest classification", "non_photographic", []
    return None


def _classify(entity: dict[str, Any], truth: dict[str, set[str]]) -> tuple[str, str, str, list[str]]:
    entity_id = entity["id"]
    attrs = entity.get("attributes") or {}
    frozen = _truth_classification(entity_id, attrs, truth)
    if frozen:
        return frozen
    if sourced_photo_evidence(attrs):
        return "rights-cleared", "complete image-specific rights evidence", "owner_review", []
    image_type = str(attrs.get("image_type") or "").strip().lower()
    if image_type in DOCUMENTARY_TYPES:
        return "documentary-candidate-missing-evidence", "documentary family without complete rights evidence", "owner_review", _missing_requirements(attrs)
    if image_type == "ai-generated" and attrs.get("image_generation_reference") and attrs.get("is_verified_photo") is False:
        return "ai-generated", "explicit generation reference", "non_photographic", []
    if image_type == "generated-placeholder" and attrs.get("is_verified_photo") is False:
        return "generated-placeholder", "explicit placeholder classification", "non_photographic", []
    return "unknown-quarantined", "no explicit evidence-backed media classification", "quarantine", []


def _validate_candidate_paths(root: Path, data_path: Path, asset_root: Path) -> tuple[Path, Path]:
    root = root.resolve(strict=True)
    data_path = _inside(data_path, root)
    asset_root = _inside(asset_root, root)
    if data_path != (root / "data.json").resolve() or asset_root != (root / "public/img/entities").resolve():
        raise InventoryError("candidate paths do not match the fixed layout")
    if not data_path.is_file() or not asset_root.is_dir():
        raise InventoryError("candidate data or asset root is missing")
    return data_path, asset_root


def _load_entities(data_path: Path) -> list[dict[str, Any]]:
    payload = _load_json(data_path, "candidate data")
    if not isinstance(payload, dict) or not isinstance(payload.get("entities"), list):
        raise InventoryError("candidate data must contain an entities list")
    entities = payload["entities"]
    ids = [entity.get("id") if isinstance(entity, dict) else None for entity in entities]
    if any(not isinstance(entity, dict) or not isinstance(entity.get("id"), str) or not entity["id"].strip() for entity in entities):
        raise InventoryError("candidate contains an entity without a valid ID")
    if len(ids) != len(set(ids)):
        raise InventoryError("candidate contains duplicate entity IDs")
    if "prov-1" in ids:
        raise InventoryError("tombstoned prov-1 is present in candidate")
    return entities


def _load_candidate_inputs(
    root: Path, data_path: Path, asset_root: Path, truth_path: Path
) -> tuple[list[dict[str, Any]], Path, Path, dict[str, set[str]], dict[str, str]]:
    root = root.resolve(strict=True)
    data_path, _ = _validate_candidate_paths(root, data_path, asset_root)
    truth_path = truth_path.resolve(strict=True)
    db_path = root / "vinhlong360.db"
    if not db_path.is_file():
        raise InventoryError("candidate SQLite database is missing")
    if any((root / suffix).exists() for suffix in ("vinhlong360.db-wal", "vinhlong360.db-shm", "vinhlong360.db-journal", ".reconciliation.lock")):
        raise InventoryError("candidate SQLite sidecar or reconciliation lock is present")
    truth = _truth_sets(truth_path)
    entities = _load_entities(data_path)
    entity_ids = {entity["id"] for entity in entities}
    active_truth_ids = truth["ai_generated"] | truth["generated_placeholder"]
    if not active_truth_ids <= entity_ids or truth["delete"] & entity_ids:
        raise InventoryError("candidate entity IDs do not match the frozen media truth scope")
    return entities, data_path, truth_path, truth, _stage_asset_hashes(root, truth)


def _build_item(
    entity: dict[str, Any],
    asset_root: Path,
    truth: dict[str, set[str]],
    stage_hashes: dict[str, str],
) -> dict[str, Any]:
    entity_id = entity["id"]
    paths = _image_paths(entity, asset_root)
    assets = [{"path": relative, "sha256": _sha256(path)} for relative, path in paths]
    if entity_id in stage_hashes and len(assets) != 1:
        raise InventoryError(f"staged asset identity is ambiguous: {entity_id}")
    if entity_id in stage_hashes and assets[0]["sha256"] != stage_hashes[entity_id]:
        raise InventoryError(f"staged asset hash mismatch: {entity_id}")
    classification, reason, review_status, missing = _classify(entity, truth)
    attrs = entity.get("attributes") or {}
    return {
        "entityId": entity_id,
        "imagePaths": assets,
        "currentClaims": {
            "imageType": attrs.get("image_type"),
            "isVerifiedPhoto": attrs.get("is_verified_photo"),
            "imageAuthor": attrs.get("image_author"),
            "imageSource": attrs.get("image_source"),
            "imageSourceUrl": attrs.get("image_source_url"),
        },
        "evidenceReferences": {
            "permission": attrs.get("permission_evidence") or attrs.get("rights_evidence") or attrs.get("permission"),
            "generation": attrs.get("image_generation_reference"),
        },
        "missingRequirements": missing,
        "classification": classification,
        "classificationReason": reason,
        "reviewStatus": review_status,
        "proposedMutation": None,
    }


def build_inventory(root: Path, data_path: Path, asset_root: Path, truth_path: Path) -> dict[str, Any]:
    entities, data_path, truth_path, truth, stage_hashes = _load_candidate_inputs(
        root, data_path, asset_root, truth_path
    )
    asset_root = (root / "public/img/entities").resolve()
    items = [
        _build_item(entity, asset_root, truth, stage_hashes)
        for entity in sorted(entities, key=lambda item: item["id"])
    ]
    counts = dict(sorted(Counter(item["classification"] for item in items).items()))
    return {
        "schemaVersion": 1,
        "status": "review_required",
        "mutationAllowed": False,
        "candidate": {
            "root": ".tmp/media-truth-candidate/candidate",
            "dataSha256": _sha256(data_path),
            "assetRoot": "public/img/entities",
        },
        "sourceTruth": {"path": "docs/standards/batch-21-media-truth.json", "sha256": _sha256(truth_path)},
        "counts": counts,
        "items": items,
    }


def render_inventory(inventory: dict[str, Any]) -> bytes:
    if inventory.get("mutationAllowed") is not False:
        raise InventoryError("inventory must remain non-authorizing")
    return (json.dumps(inventory, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _protected_output_collision(output: Path, protected: set[Path]) -> bool:
    return output.resolve(strict=False) in protected or any(
        output.exists() and os.path.exists(path) and os.path.samefile(output, path) for path in protected
    )


def _safe_output_path(output: Path, root: Path, data_path: Path, truth_path: Path) -> Path:
    if output.exists() and output.is_symlink():
        raise InventoryError("output path must not be a symlink")
    resolved = output.resolve(strict=False)
    repo_root = Path(__file__).resolve().parents[2]
    protected = {
        data_path.resolve(),
        truth_path.resolve(),
        (root / "vinhlong360.db").resolve(),
        (root / "stage-result.json").resolve(),
        (repo_root / "web/data.json").resolve(),
        (repo_root / "agent/data/vinhlong360.db").resolve(),
    }
    protected.update(path.with_name(path.name + suffix) for path in tuple(protected) for suffix in ("-wal", "-shm", "-journal"))
    if _protected_output_collision(output, protected):
        raise InventoryError("output path collides with a protected input or sidecar")
    try:
        if os.path.commonpath((str(resolved), str(root.resolve()))) == str(root.resolve()):
            raise InventoryError("output path must be outside the candidate root")
    except ValueError as exc:
        raise InventoryError("output path is not on a compatible volume") from exc
    if resolved == (root / "public/img/entities").resolve() or resolved.is_dir():
        raise InventoryError("output path must be a file outside the candidate layout")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.data.resolve(strict=True).parent
    inventory = build_inventory(root, args.data, args.asset_root, args.truth)
    output = _safe_output_path(args.output, root, args.data, args.truth)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(render_inventory(inventory))
    print(json.dumps({"items": len(inventory["items"]), "mutationAllowed": False, "output": str(output)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
