#!/usr/bin/env python3
"""Build a deterministic, read-only manifest for unresolved data findings."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any

try:
    from agent.media_truth_manifest import reviewed_removal_ids
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from agent.media_truth_manifest import reviewed_removal_ids


class ManifestError(ValueError):
    """Raised when review-manifest inputs are missing or malformed."""


def _sha(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ManifestError(f"unreadable input: {path}") from exc


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
        raise ManifestError(f"malformed {label}: {path}") from exc


def _sqlite_uri(path: Path) -> str:
    return f"file:{path.resolve().as_posix()}?mode=ro&immutable=1"


def _attributes(raw: Any, record_id: str) -> dict[str, Any]:
    if raw in (None, ""):
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ManifestError(f"malformed attributes for {record_id}") from exc
        if isinstance(value, dict):
            return value
    raise ManifestError(f"attributes must be an object for {record_id}")


def _default_ledgers(root: Path) -> dict[str, Path]:
    outputs = root / "outputs"
    return {
        "phase7": outputs / "remediation_phase7_log.json",
        "spatial": outputs / "remediation_spatial.json",
        "master": outputs / "data_remediation_ledger.json",
        "photos": outputs / "batch_culinary_restaurants_photos.json",
        "phase21": outputs / "remediation_phase21_image_log.json",
        "batch7": outputs / "batch7_master_enrichment_log.json",
        "temporal": outputs / "remediation_temporal.json",
    }


def _require(path: Path, label: str) -> Path:
    if not path.is_file():
        raise ManifestError(f"missing {label}: {path}")
    return path


def _sqlite_snapshot(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    try:
        with sqlite3.connect(_sqlite_uri(path), uri=True) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, name, type, coordinates, placeId, address, description, "
                "sub_category, season, images, attributes FROM entities"
            ).fetchall()
            entities = {row["id"]: dict(row) for row in rows}
            orphan_rows = conn.execute(
                "SELECT id, name, type FROM entities "
                "WHERE id NOT IN (SELECT from_id FROM relationships) "
                "AND id NOT IN (SELECT to_id FROM relationships) ORDER BY id"
            ).fetchall()
            relationship_count = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
    except sqlite3.Error as exc:
        raise ManifestError(f"unreadable SQLite fixture: {path}") from exc
    return entities, {
        "entityCount": len(entities),
        "relationshipCount": relationship_count,
        "orphans": [dict(row) for row in orphan_rows],
    }


def _finding(
    finding_id: str,
    category: str,
    record_type: str,
    record_ids: list[str],
    observed: dict[str, Any],
    reason: str,
    evidence: list[str],
    *,
    options: list[Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "findingId": finding_id,
        "category": category,
        "recordType": record_type,
        "recordIds": sorted(record_ids),
        "status": "review_required",
        "mutationAllowed": False,
        "observed": observed,
        "reason": reason,
        "evidence": sorted(set(evidence)),
    }
    if options is not None:
        result["competingOptions"] = options
    return result


def _phase4_record_ids(ledger: list[Any]) -> list[str]:
    return [str(item.get("entity_id") or item.get("id")) for item in ledger if isinstance(item, dict)]


def _phase4_record_matches(
    record_id: str,
    store: str,
    record: dict[str, Any] | None,
    forbidden: tuple[str, ...],
) -> list[dict[str, Any]]:
    if not record:
        return []
    attrs = _attributes(record.get("attributes"), record_id)
    fields = {
        "description": record.get("description"),
        "hours": record.get("hours"),
        "best_time": record.get("best_time"),
        **{f"attributes.{key}": value for key, value in attrs.items()},
    }
    return [
        {"store": store, "recordId": record_id, "field": field, "value": value}
        for field, value in fields.items()
        if isinstance(value, str) and any(token in value.lower() for token in forbidden)
    ]


def _phase4_cliches(root: Path, sqlite_entities: dict[str, dict[str, Any]], json_entities: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ledger_path = _require(root / "outputs/notebooklm_phase4_enrichment_ledger.json", "Phase 4 ledger")
    ledger = _load_json(ledger_path, "Phase 4 ledger")
    if not isinstance(ledger, list):
        raise ManifestError("Phase 4 ledger must be a list")
    ids = _phase4_record_ids(ledger)
    forbidden = ("nổi tiếng", "đậm đà bản sắc", "nhất vùng", "tuyệt vời")
    matches = [
        match
        for record_id in ids
        for store, records in (("sqlite", sqlite_entities), ("json", json_entities))
        for match in _phase4_record_matches(record_id, store, records.get(record_id), forbidden)
    ]
    return _finding(
        "phase4-cliche-review",
        "phase4-cliche",
        "entity",
        sorted({item["recordId"] for item in matches}),
        {"matches": sorted(matches, key=lambda item: (item["recordId"], item["store"], item["field"]))},
        "Phase 4 prose still contains an unreviewed superlative/cliché; no replacement wording is inferred.",
        [_stable(ledger_path, root), "tests/phase4-enrichment-remediated.test.ts"],
    )


def _load_parity(path: Path) -> dict[str, Any]:
    parity = _load_json(path, "parity report")
    if not isinstance(parity, dict) or not isinstance(parity.get("relationshipDiff"), dict):
        raise ManifestError("parity report has invalid relationshipDiff")
    return parity


def _load_json_entities(path: Path) -> dict[str, dict[str, Any]]:
    payload = _load_json(path, "JSON fixture")
    if not isinstance(payload, dict) or not isinstance(payload.get("entities"), list) or not isinstance(payload.get("relationships"), list):
        raise ManifestError("JSON fixture must contain entities and relationships lists")
    entities = {str(item["id"]): item for item in payload["entities"] if isinstance(item, dict) and isinstance(item.get("id"), str)}
    if len(entities) != len(payload["entities"]):
        raise ManifestError("JSON fixture contains malformed or duplicate entity rows")
    return entities


def _load_manifest_inputs(root: Path) -> dict[str, Any]:
    sqlite_path = _require(root / "agent/data/vinhlong360.db", "SQLite fixture")
    json_path = _require(root / "web/data.json", "JSON fixture")
    parity_path = _require(root / "outputs/data-parity-audit-2026-09-22.json", "parity report")
    parity = _load_parity(parity_path)
    json_entities = _load_json_entities(json_path)
    ledger_paths = {name: _require(path, f"{name} ledger") for name, path in _default_ledgers(root).items()}
    sqlite_entities, sqlite_meta = _sqlite_snapshot(sqlite_path)
    return {
        "sqlitePath": sqlite_path,
        "jsonPath": json_path,
        "parityPath": parity_path,
        "parity": parity,
        "ledgerPaths": ledger_paths,
        "sqliteEntities": sqlite_entities,
        "sqliteMeta": sqlite_meta,
        "jsonEntities": json_entities,
        "beforeHashes": {"sqlite": _sha(sqlite_path), "json": _sha(json_path)},
    }


def _prov_entities(inputs: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any], dict[str, Any]]:
    prov_sqlite = inputs["sqliteEntities"].get("prov-1")
    prov_json = inputs["jsonEntities"].get("prov-1")
    return (
        prov_sqlite,
        prov_json,
        _attributes(prov_sqlite.get("attributes"), "prov-1") if prov_sqlite else {},
        _attributes(prov_json.get("attributes"), "prov-1") if prov_json else {},
    )


def _relationship_record_ids(parity: dict[str, Any], tombstones: frozenset[str] = frozenset()) -> list[str]:
    diff = parity["relationshipDiff"]
    return sorted({
        item["from"]
        for item in (diff.get("jsonOnlyTriples") or [])[:20]
        if isinstance(item, dict) and isinstance(item.get("from"), str) and item["from"] not in tombstones
    } | {
        item["from"]
        for item in (diff.get("sqliteOnlyTriples") or [])[:20]
        if isinstance(item, dict) and isinstance(item.get("from"), str) and item["from"] not in tombstones
    })


def _relationship_finding(inputs: dict[str, Any], tombstones: frozenset[str]) -> dict[str, Any]:
    parity = inputs["parity"]
    diff = parity["relationshipDiff"]
    return _finding(
        "relationship-parity-drift",
        "relationship-parity-drift",
        "relationship",
        _relationship_record_ids(parity, tombstones),
        {"sqlite": inputs["sqliteMeta"], "parity": {key: diff.get(key) for key in ("jsonRowCount", "sqliteRowCount", "typeSubstitutions", "jsonOnlyTriples", "sqliteOnlyTriples", "duplicateJsonTriples")}},
        "Relationship rows, types, and one orphan differ between stores; only evidence-backed Phase B proposals may be reviewed.",
        ["outputs/data-parity-audit-2026-09-22.json", "outputs/remediation_graph.json", "tests/data-standardization.test.ts", "tests/data-health-remediated.test.ts"],
    )


def _build_initial_findings(root: Path, inputs: dict[str, Any], tombstones: frozenset[str]) -> list[dict[str, Any]]:
    prov_sqlite, prov_json, prov_sqlite_attrs, prov_json_attrs = _prov_entities(inputs)
    prov_fields = ("coordinates", "placeId", "address", "description", "sub_category", "season")
    findings = [
        _relationship_finding(inputs, tombstones),
        _phase4_cliches(root, inputs["sqliteEntities"], inputs["jsonEntities"]),
    ]
    if "prov-1" not in tombstones and prov_sqlite and prov_json:
        findings[0:0] = [
            _finding(
            "prov-1-contract-gaps",
            "prov-1-contract-gaps",
            "entity",
            ["prov-1"],
            {"sqlite": {field: prov_sqlite.get(field) for field in prov_fields}, "json": {field: prov_json.get(field) for field in prov_fields}, "sqliteAttributes": prov_sqlite_attrs, "jsonAttributes": prov_json_attrs},
            "SQLite and JSON disagree on the deferred prov-1 contract fields; evidence is insufficient for an automatic repair.",
            ["outputs/data-parity-audit-2026-09-22.json", "docs/superpowers/plans/2026-09-23-data-contract-reconciliation-phase-b.md", "tests/data-standardization.test.ts"],
            ),
            _finding(
            "documentary-image-provenance",
            "documentary-image-provenance",
            "entity",
            ["prov-1"],
            {"sqlite": {"images": prov_sqlite.get("images"), "attributes": prov_sqlite_attrs}, "json": {"images": prov_json.get("images"), "source": prov_json.get("source"), "attributes": prov_json_attrs}},
            "The documentary-image bundle still needs an image-specific source URL and explicit permission evidence; no provenance is invented.",
            ["outputs/batch_culinary_restaurants_photos.json", "docs/superpowers/plans/2026-09-23-data-contract-reconciliation-phase-b.md", "tests/image-governance.test.ts"],
            ),
        ]
    return findings


def _superseded_history(tombstones: frozenset[str]) -> list[dict[str, Any]]:
    if "prov-1" not in tombstones:
        return []
    return [{
        "recordId": "prov-1",
        "recordType": "entity",
        "status": "superseded",
        "mutationAllowed": False,
        "supersededBy": "batch-21-media-truth-v1",
        "reason": "Historical prov-1 repair proposals are superseded by reviewed deletion evidence.",
        "evidence": ["docs/standards/batch-21-media-truth.json"],
    }]


def _temporal_finding(root: Path, temporal_path: Path) -> dict[str, Any]:
    temporal = _load_json(temporal_path, "temporal ledger")
    if not isinstance(temporal, dict):
        raise ManifestError("temporal ledger must be an object")
    conflict = next((item for item in temporal.get("remediation_ledger", []) if isinstance(item, dict) and item.get("entity_id") == "le-chol-chhnam-thmay"), None)
    if not isinstance(conflict, dict):
        raise ManifestError("temporal ledger is missing the Chôl Chhnăm conflict")
    return _finding(
        "owner-conflict-le-chol-chhnam-thmay",
        "owner-approved-conflict",
        "entity",
        ["le-chol-chhnam-thmay"],
        {"current": conflict.get("current_values")},
        "The owner-approved Chôl Chhnăm option conflict remains deferred until an owner selects one evidence-backed option.",
        [_stable(temporal_path, root), "docs/superpowers/plans/2026-09-23-data-contract-reconciliation-phase-b.md"],
        options=conflict.get("decision_matrix"),
    )


def _verified_at_finding(parity: dict[str, Any]) -> dict[str, Any]:
    parity_provenance = parity.get("provenanceDiff", {}).get("fieldDifferences", [])
    verified_ids = ["ben-pha-tran-phu-can-tho-vinh-long-vinh-long", "cau-lang-chim", "cau-truong-long-hoa"]
    verified_matches = [item for item in parity_provenance if isinstance(item, dict) and item.get("field") == "attributes.verifiedAt" and item.get("id") in verified_ids]
    return _finding(
        "verifiedAt-phase8-conflicts",
        "verifiedAt-conflicts",
        "entity",
        verified_ids,
        {"differences": sorted(verified_matches, key=lambda item: item.get("id", ""))},
        "Phase 8 verifiedAt values differ between stores; chronology and attestation ownership require review.",
        ["outputs/data-parity-audit-2026-09-22.json", "outputs/notebooklm_phase8_enrichment_ledger.json", "tests/phase8-enrichment-remediated.test.ts"],
    )


def _publish_manifest(output: Path, manifest: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, prefix=f".{output.name}.", suffix=".tmp", delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, output)
    except OSError as exc:
        if "temp_path" in locals() and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise ManifestError(f"cannot publish manifest: {output}") from exc


def build_manifest(root: Path, output: Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    inputs = _load_manifest_inputs(root)
    tombstones = reviewed_removal_ids(root)
    findings = _build_initial_findings(root, inputs, tombstones)
    findings.extend([
        _temporal_finding(root, inputs["ledgerPaths"]["temporal"]),
        _verified_at_finding(inputs["parity"]),
    ])
    findings.sort(key=lambda item: item["findingId"])
    after_hashes = {"sqlite": _sha(inputs["sqlitePath"]), "json": _sha(inputs["jsonPath"])}
    if inputs["beforeHashes"] != after_hashes:
        raise ManifestError("protected fixture changed during manifest generation")
    manifest = {
        "schemaVersion": 1,
        "mode": "read-only-review-manifest",
        "status": "review_required",
        "mutationAllowed": False,
        "inputs": {"sqlite": {"path": _stable(inputs["sqlitePath"], root), "sha256": inputs["beforeHashes"]["sqlite"]}, "json": {"path": _stable(inputs["jsonPath"], root), "sha256": inputs["beforeHashes"]["json"]}, "parity": {"path": _stable(inputs["parityPath"], root), "sha256": _sha(inputs["parityPath"])}},
        "summary": {"findingCount": len(findings), "categories": sorted({item["category"] for item in findings})},
        "findings": findings,
        "history": _superseded_history(tombstones),
    }
    if output is not None:
        _publish_manifest(Path(output), manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = build_manifest(args.root, args.output)
    except ManifestError as exc:
        print(f"review manifest refused: {exc}")
        return 2
    print(json.dumps({"status": manifest["status"], "findingCount": manifest["summary"]["findingCount"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
