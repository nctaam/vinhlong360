#!/usr/bin/env python3
"""Build a deterministic, non-authorizing image provenance review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any

try:
    from agent.media_truth_manifest import reviewed_removal_ids
    from .provenance_evidence_policy import select_affirmative_license_scope
    from .provenance_url_policy import is_public_provenance_url
except ImportError:  # pragma: no cover - direct script execution
    from agent.media_truth_manifest import reviewed_removal_ids
    from provenance_evidence_policy import select_affirmative_license_scope
    from provenance_url_policy import is_public_provenance_url


SCHEMA_VERSION = 1
IMAGE_ATTRIBUTE_FIELDS = (
    "image_type",
    "is_verified_photo",
    "image_author",
    "image_source",
    "image_license",
    "image_source_url",
    "image_caption",
)
LEDGER_FIELDS = (
    "entity_id",
    "image",
    "author",
    "source",
    "caption",
    "license",
    "image_source_url",
    "permission_evidence",
    "rights_evidence",
    "permission",
)
_OWNER_REFERENCE = re.compile(r"^(?:case-file|document|owner-record):[A-Za-z0-9][A-Za-z0-9._/-]*$")


class ProvenanceReviewError(ValueError):
    """Raised when provenance review inputs are missing, malformed, or unsafe."""


def _sha(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ProvenanceReviewError(f"unreadable input: {path}") from exc


def _stable(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _load_json(path: Path, label: str) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvenanceReviewError(f"malformed {label}: {path}") from exc


def _canonical_json_sha(payload: Any) -> str:
    if isinstance(payload, list):
        payload = sorted(payload, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _attributes(raw: Any, label: str) -> dict[str, Any]:
    if raw in (None, ""):
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProvenanceReviewError(f"malformed attributes for {label}") from exc
        if isinstance(value, dict):
            return value
    raise ProvenanceReviewError(f"attributes must be an object for {label}")


def _images(raw: Any, label: str) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProvenanceReviewError(f"malformed images for {label}") from exc
        if isinstance(value, list):
            return value
    raise ProvenanceReviewError(f"images must be a list for {label}")


def _sqlite_entity(path: Path, entity_id: str) -> dict[str, Any]:
    uri = f"file:{path.resolve().as_posix()}?mode=ro&immutable=1"
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT id, images, attributes FROM entities WHERE id = ?", (entity_id,)
            ).fetchone()
    except sqlite3.Error as exc:
        raise ProvenanceReviewError(f"unreadable SQLite fixture: {path}") from exc
    if row is None:
        raise ProvenanceReviewError(f"missing target entity: {entity_id}")
    return dict(row)


def _find_entity(path: Path, entity_id: str) -> dict[str, Any] | None:
    payload = _load_json(path, "JSON fixture")
    if not isinstance(payload, dict) or not isinstance(payload.get("entities"), list):
        raise ProvenanceReviewError("JSON fixture must contain an entities list")
    matches = [item for item in payload["entities"] if isinstance(item, dict) and item.get("id") == entity_id]
    if len(matches) > 1:
        raise ProvenanceReviewError(f"JSON fixture must contain exactly one {entity_id}")
    return matches[0] if matches else None


def _normalized_image_path(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("\\", "/")
    for prefix in ("web-nuxt/public", "public"):
        if normalized.startswith(prefix + "/"):
            normalized = normalized[len(prefix):]
            break
    return normalized if normalized.startswith("/") else "/" + normalized


def _target_image_paths(raw: Any, entity_id: str) -> set[str]:
    images = _images(raw, f"JSON {entity_id}")
    paths = {_normalized_image_path(image) for image in images}
    paths.discard(None)
    if not paths:
        raise ProvenanceReviewError(f"missing valid target image for {entity_id}")
    return paths


def _ledger_rows(path: Path, target_paths: set[str], entity_id: str) -> tuple[list[dict[str, Any]], str]:
    payload = _load_json(path, "photo ledger")
    if not isinstance(payload, list):
        raise ProvenanceReviewError("photo ledger must be a list")
    entity_rows = [item for item in payload if isinstance(item, dict) and item.get("entity_id") == entity_id]
    if not entity_rows:
        raise ProvenanceReviewError(f"photo ledger is missing {entity_id}")
    matching_rows = [
        row for row in entity_rows
        if (image_path := _normalized_image_path(row.get("image"))) is not None and image_path in target_paths
    ]
    emitted_rows = [
        {
            **{key: row.get(key) for key in LEDGER_FIELDS if key in row},
            "status": "review_required",
            "mutationAllowed": False,
        }
        for row in matching_rows
    ]
    emitted_rows.sort(
        key=lambda item: json.dumps(
            item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    )
    return emitted_rows, _canonical_json_sha(emitted_rows)


def _selected_attributes(raw: Any, label: str) -> dict[str, Any]:
    attributes = _attributes(raw, label)
    return {field: attributes.get(field) for field in IMAGE_ATTRIBUTE_FIELDS if field in attributes}


def _source_urls(attributes: dict[str, Any], ledger: list[dict[str, Any]]) -> list[str]:
    values: list[Any] = [attributes.get("image_source_url")]
    values.extend(item.get("image_source_url") for item in ledger)
    return sorted({value.strip() for value in values if isinstance(value, str) and value.strip()})


def _valid_source_url(value: str) -> bool:
    return is_public_provenance_url(value)


def _first_nonempty(values: list[Any]) -> str | None:
    return next((value.strip() for value in values if isinstance(value, str) and value.strip()), None)


def _permission_evidence(ledger: list[dict[str, Any]]) -> str | None:
    values = [row.get(key) for row in ledger for key in ("permission_evidence", "rights_evidence", "permission")]
    return next((value.strip() for value in values if _valid_permission_reference(value)), None)


def _valid_permission_reference(value: object) -> bool:
    if not isinstance(value, str):
        return False
    reference = value.strip()
    if _OWNER_REFERENCE.fullmatch(reference):
        return True
    return _valid_source_url(reference)


def _license_scope(values: list[Any]) -> str | None:
    return select_affirmative_license_scope(values)


def _requirements(json_entity: dict[str, Any], ledger: list[dict[str, Any]], entity_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    attributes = _attributes(json_entity.get("attributes"), entity_id)
    observed = {
        "image-specific source URL": next(
            (value for value in _source_urls(attributes, ledger) if _valid_source_url(value)), None
        ),
        "image author": _first_nonempty([attributes.get("image_author"), *[row.get("author") for row in ledger]]),
        "publication/source": _first_nonempty([attributes.get("image_source"), *[row.get("source") for row in ledger]]),
        "license or re-host scope": _license_scope([attributes.get("image_license"), *[row.get("license") for row in ledger]]),
        "explicit permission evidence": _permission_evidence(ledger),
    }
    missing = [label for label, value in observed.items() if value is None]
    checklist = [
        {
            "requirement": label,
            "satisfied": value is not None,
            "observedValue": value,
            "status": "review_required",
            "mutationAllowed": False,
        }
        for label, value in observed.items()
    ]
    return {"required": list(observed), "missing": missing}, checklist


def _observed(sqlite_entity: dict[str, Any], json_entity: dict[str, Any], entity_id: str) -> dict[str, Any]:
    source = json_entity.get("source")
    return {
        "sqlite": {
            "images": _images(sqlite_entity.get("images"), f"SQLite {entity_id}"),
            "attributes": _selected_attributes(sqlite_entity.get("attributes"), f"SQLite {entity_id}"),
        },
        "json": {
            "images": _images(json_entity.get("images"), f"JSON {entity_id}"),
            "attributes": _selected_attributes(json_entity.get("attributes"), f"JSON {entity_id}"),
            "source": source if isinstance(source, list) else [],
        },
    }


def _publish(output: Path, packet: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = (
        json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, output)
        _fsync_directory(output.parent)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise ProvenanceReviewError(f"cannot publish review packet: {output}") from exc


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _reject_output_collision(output: Path | None, inputs: tuple[Path, ...]) -> None:
    if output is None:
        return
    resolved_output = Path(output).resolve()
    if any(resolved_output == path.resolve() for path in inputs):
        raise ProvenanceReviewError("output collides with a review input")


def _protected_sqlite_outputs(database: Path) -> tuple[Path, ...]:
    return tuple(
        database.with_name(f"{database.name}{suffix}")
        for suffix in ("-wal", "-shm", "-journal", ".reconciliation.lock")
    )


def _target_absent_packet(entity_id: str, image_path: str) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "mode": "read-only-image-provenance-review",
        "status": "target_absent",
        "mutationAllowed": False,
        "target": {"entityId": entity_id, "imagePath": image_path},
        "supersededBy": "batch-21-media-truth-v1",
        "evidenceChecklist": [],
    }


def _build_present_target_packet(
    root: Path,
    *,
    entity: dict[str, Any],
    sqlite_entity: dict[str, Any],
    entity_id: str,
    image_path: str,
    sqlite_path: Path,
    json_path: Path,
    photo_ledger: Path,
    protected_sqlite: Path,
    protected_json: Path,
) -> dict[str, Any]:
    target_paths = {_normalized_image_path(image_path)}
    target_paths.discard(None)
    if not target_paths:
        raise ProvenanceReviewError("image_path must be a non-empty path")
    ledger, canonical_ledger_sha = _ledger_rows(photo_ledger, target_paths, entity_id)
    requirements, checklist = _requirements(entity, ledger, entity_id)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "mode": "read-only-image-provenance-review",
        "status": "ready_for_owner_review",
        "mutationAllowed": False,
        "target": {"entityId": entity_id, "imagePath": image_path, "imageClass": "documentary"},
        "inputs": {
            "sqlite": {"path": _stable(sqlite_path, root), "sha256": _sha(sqlite_path)},
            "json": {"path": _stable(json_path, root), "sha256": _sha(json_path)},
            "photoLedger": {
                "path": _stable(photo_ledger, root),
                "sha256": _sha(photo_ledger),
                "canonicalEvidenceSha256": canonical_ledger_sha,
            },
        },
        "observedStores": _observed(sqlite_entity, entity, entity_id),
        "ledgerEvidence": ledger,
        "requirements": requirements,
        "evidenceChecklist": checklist,
        "nextReviewActions": [
            "Provide a traceable image-specific source URL from the publisher or rights holder.",
            "Attach explicit evidence that re-hosting is permitted and retain its owner-review reference.",
            "Have the owner verify author, publication/source, license scope, and visible credit before any data proposal.",
        ],
    }


def build_packet(
    root: Path,
    output: Path | None = None,
    *,
    entity_id: str,
    image_path: str,
    sqlite_path: Path | None = None,
    json_path: Path | None = None,
    photo_ledger: Path | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    protected_sqlite = root / "agent/data/vinhlong360.db"
    protected_json = root / "web/data.json"
    before = {"sqlite": _sha(protected_sqlite), "json": _sha(protected_json)}
    sqlite_path = Path(sqlite_path) if sqlite_path is not None else protected_sqlite
    json_path = Path(json_path) if json_path is not None else protected_json
    photo_ledger = Path(photo_ledger) if photo_ledger is not None else root / "outputs/batch_culinary_restaurants_photos.json"
    _reject_output_collision(
        output,
        (
            sqlite_path,
            json_path,
            photo_ledger,
            protected_sqlite,
            protected_json,
            *_protected_sqlite_outputs(protected_sqlite),
        ),
    )
    json_entity = _find_entity(json_path, entity_id)
    if json_entity is None:
        if entity_id not in reviewed_removal_ids(root):
            raise ProvenanceReviewError(f"entity not found: {entity_id}")
        after = {"sqlite": _sha(protected_sqlite), "json": _sha(protected_json)}
        if before != after:
            raise ProvenanceReviewError("protected fixture changed during review packet generation")
        packet = _target_absent_packet(entity_id, image_path)
        if output is not None:
            _publish(Path(output), packet)
        return packet
    sqlite_entity = _sqlite_entity(sqlite_path, entity_id)
    after = {"sqlite": _sha(protected_sqlite), "json": _sha(protected_json)}
    if before != after:
        raise ProvenanceReviewError("protected fixture changed during review packet generation")
    packet = _build_present_target_packet(
        root,
        entity=json_entity,
        sqlite_entity=sqlite_entity,
        entity_id=entity_id,
        image_path=image_path,
        sqlite_path=sqlite_path,
        json_path=json_path,
        photo_ledger=photo_ledger,
        protected_sqlite=protected_sqlite,
        protected_json=protected_json,
    )
    if output is not None:
        _publish(Path(output), packet)
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--sqlite", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--photo-ledger", type=Path)
    parser.add_argument("--entity-id", required=True)
    parser.add_argument("--image-path", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        packet = build_packet(
            args.root,
            args.output,
            entity_id=args.entity_id,
            image_path=args.image_path,
            sqlite_path=args.sqlite,
            json_path=args.json_path,
            photo_ledger=args.photo_ledger,
        )
    except ProvenanceReviewError as exc:
        print(f"provenance review refused: {exc}")
        return 2
    print(json.dumps({
        "status": packet["status"],
        "missingRequirementCount": len(packet.get("requirements", {}).get("missing", [])),
        "mutationAllowed": packet["mutationAllowed"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
