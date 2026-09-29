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


def _truth_sets(truth_path: Path) -> dict[str, set[str]]:
    truth = _load_json(truth_path, "truth manifest")
    if not isinstance(truth, dict) or set(truth) != TRUTH_KEYS or truth.get("schemaVersion") != 1:
        raise InventoryError("truth manifest schema mismatch")
    sets: dict[str, set[str]] = {}
    for key in ("delete", "ai_generated", "generated_placeholder"):
        values = truth.get(key)
        if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
            raise InventoryError(f"truth manifest field {key} must be a list of IDs")
        if len(values) != len(set(values)):
            raise InventoryError(f"truth manifest field {key} contains duplicate IDs")
        sets[key] = set(values)
    if sets["delete"] & (sets["ai_generated"] | sets["generated_placeholder"]):
        raise InventoryError("truth manifest classifications overlap deleted IDs")
    if sets["ai_generated"] & sets["generated_placeholder"]:
        raise InventoryError("truth manifest classifications overlap")
    return sets


def _image_paths(entity: dict[str, Any], asset_root: Path) -> list[tuple[str, Path]]:
    images = entity.get("images")
    if not isinstance(images, list) or not images or any(not isinstance(value, str) or not value.strip() for value in images):
        raise InventoryError(f"entity {entity.get('id')} has no valid image list")
    result: list[tuple[str, Path]] = []
    for image in images:
        normalized = image.replace("\\", "/").lstrip("/")
        marker = "img/entities/"
        if normalized.startswith(marker):
            relative = normalized[len(marker) :]
        else:
            relative = Path(normalized).name
        if not relative or relative in {".", ".."} or Path(relative).name != relative:
            raise InventoryError(f"unsafe image path for {entity.get('id')}: {image}")
        path = _inside(asset_root / relative, asset_root)
        if not path.is_file():
            raise InventoryError(f"missing image asset for {entity.get('id')}: {relative}")
        result.append((f"public/img/entities/{relative}", path))
    return result


def _stage_asset_hashes(root: Path) -> dict[str, str]:
    stage_path = root / "stage-result.json"
    if not stage_path.is_file():
        raise InventoryError("candidate stage result is missing")
    stage = _load_json(stage_path, "stage result")
    if not isinstance(stage, dict) or stage.get("mutationAllowed") is not False:
        raise InventoryError("candidate stage result must be non-authorizing")
    retained = (stage.get("assets") or {}).get("retained", [])
    if not isinstance(retained, list):
        raise InventoryError("candidate stage result retained assets must be a list")
    expected: dict[str, str] = {}
    for item in retained:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("sha256"), str):
            raise InventoryError("candidate stage result contains malformed asset identity")
        if item["id"] in expected:
            raise InventoryError(f"duplicate staged asset: {item['id']}")
        expected[item["id"]] = item["sha256"]
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


def _classify(entity: dict[str, Any], truth: dict[str, set[str]]) -> tuple[str, str, str, list[str]]:
    entity_id = entity["id"]
    attrs = entity.get("attributes") or {}
    if entity_id in truth["delete"]:
        raise InventoryError(f"deleted entity present in candidate: {entity_id}")
    if entity_id in truth["ai_generated"]:
        if attrs.get("image_type") != "ai-generated" or not attrs.get("image_generation_reference"):
            raise InventoryError(f"AI entity lacks explicit generation evidence: {entity_id}")
        return "ai-generated", "Batch 21 truth manifest with explicit generation reference", "non_photographic", []
    if entity_id in truth["generated_placeholder"]:
        if attrs.get("image_type") != "generated-placeholder":
            raise InventoryError(f"placeholder entity lacks explicit placeholder type: {entity_id}")
        return "generated-placeholder", "Batch 21 truth manifest classification", "non_photographic", []
    if sourced_photo_evidence(attrs):
        return "rights-cleared", "complete image-specific rights evidence", "owner_review", []
    image_type = str(attrs.get("image_type") or "").strip().lower()
    if image_type in DOCUMENTARY_TYPES:
        return "documentary-candidate-missing-evidence", "documentary family without complete rights evidence", "owner_review", _missing_requirements(attrs)
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
    return _load_entities(data_path), data_path, truth_path, _truth_sets(truth_path), _stage_asset_hashes(root)


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.data.resolve(strict=True).parent
    while root.name != "candidate" and root != root.parent:
        root = root.parent
    inventory = build_inventory(root, args.data, args.asset_root, args.truth)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(render_inventory(inventory))
    print(json.dumps({"items": len(inventory["items"]), "mutationAllowed": False, "output": str(args.output)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
