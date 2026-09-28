"""Build the reviewed, offline Batch 21 media-truth reconciliation plan."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

try:
    from agent.media_truth_manifest import load_batch_21_truth
    from scripts.checks import apply_data_reconciliation as apply_module
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from agent.media_truth_manifest import load_batch_21_truth
    from scripts.checks import apply_data_reconciliation as apply_module


class PlanError(ValueError):
    """Raised when the frozen media-truth scope cannot be proven."""


PRESS_FIELDS = (
    "image_author", "image_source", "image_source_url", "image_license",
    "permission_evidence", "rights_evidence", "permission", "image_caption",
)


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha(path: Path) -> str:
    try:
        return _sha_bytes(path.read_bytes())
    except OSError as exc:
        raise PlanError(f"unreadable input: {path}") from exc


def _uri(path: Path) -> str:
    return f"file:{path.resolve().as_posix()}?mode=ro&immutable=1"


def _stable(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanError(f"malformed JSON input: {path}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("entities"), list) or not isinstance(value.get("relationships"), list):
        raise PlanError("JSON input must contain entities and relationships lists")
    return value


def _decode(value: Any, field: str, record_id: str) -> Any:
    if field in {"attributes", "images", "coordinates"} and isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise PlanError(f"malformed SQLite {field} for {record_id}") from exc
    return value


def _sqlite_snapshot(path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    sidecars = [Path(str(path) + suffix) for suffix in ("-wal", "-shm", "-journal")]
    if any(item.exists() for item in sidecars):
        raise PlanError("SQLite sidecar present")
    conn = None
    try:
        conn = sqlite3.connect(_uri(path), uri=True)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT rowid, * FROM entities ORDER BY id").fetchall()
        entities = {
            row["id"]: {key: _decode(row[key], key, row["id"]) for key in row.keys() if key != "rowid"}
            for row in rows
        }
        relationships = [
            {"from": row[0], "to": row[1], "type": row[2], "rowid": row[3]}
            for row in conn.execute("SELECT from_id, to_id, type, rowid FROM relationships ORDER BY rowid")
        ]
    except (sqlite3.Error, OSError) as exc:
        raise PlanError(f"unreadable SQLite input: {path}") from exc
    finally:
        if conn is not None:
            conn.close()
    return entities, relationships


def sqlite_logical_digest(sqlite_path: Path) -> str:
    """Hash canonical logical rows, never SQLite's physical file bytes."""
    entities, relationships = _sqlite_snapshot(Path(sqlite_path))
    payload = {
        "entities": [entities[key] for key in sorted(entities)],
        "relationships": sorted(
            [{key: row[key] for key in ("from", "to", "type")} for row in relationships],
            key=lambda row: (row["from"], row["to"], row["type"]),
        ),
    }
    return _sha_bytes(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def _mutation(store: str, record_type: str, record_id: str, operation: str, field: str,
              before: Any, after: Any, **metadata: Any) -> dict[str, Any]:
    seed = json.dumps([store, record_type, record_id, operation, field, before, after, metadata], ensure_ascii=False, sort_keys=True)
    item: dict[str, Any] = {
        "mutationId": "media-" + hashlib.sha256(seed.encode()).hexdigest()[:16],
        "store": store,
        "recordType": record_type,
        "recordId": record_id,
        "operation": operation,
        "field": field,
        "before": before,
        "after": after,
    }
    if metadata:
        item["metadata"] = metadata
    return item


def _entity_projection(item: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(item)


def _target_mutations(store: str, record: dict[str, Any], record_id: str, index: int | None) -> list[dict[str, Any]]:
    attrs = record.get("attributes")
    if not isinstance(attrs, dict):
        raise PlanError(f"attributes missing for {record_id}")
    metadata = {} if index is None else {"index": index}
    mutations: list[dict[str, Any]] = []
    values = [("attributes.image_type", attrs.get("image_type"), "generated-placeholder")]
    if record_id in {"cua-com-duyen-hai", "tep-rang-dua"}:
        values[0] = ("attributes.image_type", attrs.get("image_type"), "ai-generated")
        values.extend([
            ("attributes.image_generation_model", attrs.get("image_generation_model"), "cx/gpt-5.5-image"),
            ("attributes.image_generation_reference", attrs.get("image_generation_reference"), "git:30a3fae9"),
        ])
    values.append(("attributes.is_verified_photo", attrs.get("is_verified_photo"), False))
    for field, before, after in values:
        if field.removeprefix("attributes.") not in attrs and field not in {"attributes.image_generation_model", "attributes.image_generation_reference"}:
            raise PlanError(f"expected field missing: {record_id}:{field}")
        mutations.append(_mutation(store, "entity", record_id, "update", field, before, after, **metadata))
    for field in PRESS_FIELDS:
        if field in attrs and (field != "image_caption" or _is_false_photographic_caption(attrs)):
            mutations.append(_mutation(store, "entity", record_id, "remove", f"attributes.{field}", attrs[field], None, **metadata))
    return mutations


def _is_false_photographic_caption(attrs: dict[str, Any]) -> bool:
    return attrs.get("image_type") == "documentary" and attrs.get("is_verified_photo") is True


def _json_render(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _asset_hashes(asset_root: Path, ids: list[str], root: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for record_id in ids:
        path = asset_root / f"{record_id}.webp"
        if not path.is_file():
            raise PlanError(f"asset hash missing: {path}")
        result[record_id] = {"path": path.resolve().relative_to(root.resolve()).as_posix(), "sha256": _sha(path)}
    return result


def _digest_bundle(sqlite_path: Path, json_payload: dict[str, Any], target_ids: set[str]) -> dict[str, str]:
    entities, relationships = _sqlite_snapshot(sqlite_path)
    sqlite_entities = [value for key, value in sorted(entities.items()) if key not in target_ids and key != "prov-1"]
    sqlite_relationships = [
        (row["from"], row["to"], row["type"])
        for row in relationships if row["from"] not in target_ids and row["to"] not in target_ids
    ]
    json_entities = [value for value in sorted(json_payload["entities"], key=lambda x: x.get("id", "")) if value.get("id") not in target_ids and value.get("id") != "prov-1"]
    json_relationships = [
        (value.get("from"), value.get("to"), value.get("type"))
        for value in json_payload["relationships"] if value.get("from") not in target_ids and value.get("to") not in target_ids
    ]
    return {
        "sqlite": {"entities": apply_module._digest_rows(sqlite_entities), "relationships": apply_module._digest_rows(sqlite_relationships)},
        "json": {"entities": apply_module._digest_rows(json_entities), "relationships": apply_module._digest_rows(json_relationships)},
    }


def _load_plan_inputs(
    root: Path, sqlite_path: Path, json_path: Path, truth_path: Path,
) -> tuple[Any, dict[str, Any], dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not truth_path.is_file():
        raise PlanError(f"missing truth manifest: {truth_path}")
    try:
        truth = load_batch_21_truth(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PlanError(str(exc)) from exc
    if truth_path.read_bytes() != (root / "docs/standards/batch-21-media-truth.json").read_bytes():
        raise PlanError("truth manifest path is not the frozen Batch 21 manifest")
    payload = _load_json(json_path)
    sqlite_entities, sqlite_relationships = _sqlite_snapshot(sqlite_path)
    json_entities = {item.get("id"): item for item in payload["entities"] if isinstance(item, dict) and isinstance(item.get("id"), str)}
    if len(json_entities) != len(payload["entities"]):
        raise PlanError("JSON entities contain missing or duplicate IDs")
    return truth, payload, sqlite_entities, sqlite_relationships, json_entities


def _validate_scope(
    root: Path, truth: Any, payload: dict[str, Any], sqlite_entities: dict[str, dict[str, Any]],
    sqlite_relationships: list[dict[str, Any]], json_entities: dict[str, dict[str, Any]],
) -> dict[str, dict[str, str]]:
    all_ids = tuple(truth.delete + truth.ai_generated + truth.generated_placeholder)
    if any(record_id not in sqlite_entities or record_id not in json_entities for record_id in all_ids):
        raise PlanError("expected Batch 21 entity ID is absent")
    expected_json_rels = [item for item in payload["relationships"] if item.get("from") == "prov-1"]
    if len(expected_json_rels) != 6 or any(item.get("to") == "prov-1" for item in payload["relationships"]):
        raise PlanError("unexpected relationship references prov-1")
    if any(item["from"] == "prov-1" or item["to"] == "prov-1" for item in sqlite_relationships):
        raise PlanError("unexpected SQLite relationship references prov-1")
    asset_root = root / "web-nuxt/public/img/entities"
    affected_asset_ids = [*truth.delete, *truth.ai_generated, *truth.generated_placeholder]
    return _asset_hashes(asset_root, affected_asset_ids, root)


def _entity_index(payload: dict[str, Any], record_id: str) -> int:
    return next(i for i, row in enumerate(payload["entities"]) if row.get("id") == record_id)


def _build_mutations(
    truth: Any, payload: dict[str, Any], sqlite_entities: dict[str, dict[str, Any]],
    sqlite_relationships: list[dict[str, Any]], json_entities: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    mutations: list[dict[str, Any]] = []
    mutations.append(_mutation("sqlite", "entity", "prov-1", "delete", "entity", _entity_projection(sqlite_entities["prov-1"]), None))
    mutations.append(_mutation("json", "entity", "prov-1", "delete", "entity", _entity_projection(json_entities["prov-1"]), None, index=_entity_index(payload, "prov-1")))
    for index, row in enumerate(payload["relationships"]):
        if row.get("from") == "prov-1":
            mutations.append(_mutation("json", "relationship", f"prov-1->{row.get('to')}", "delete", "relationship", copy.deepcopy(row), None, index=index))
    for record_id in truth.ai_generated + truth.generated_placeholder:
        mutations.extend(_target_mutations("sqlite", sqlite_entities[record_id], record_id, None))
        mutations.extend(_target_mutations("json", json_entities[record_id], record_id, _entity_index(payload, record_id)))
    mutations.sort(key=lambda item: (item["store"], item["recordType"], item["recordId"], item.get("field", ""), item["operation"], item["mutationId"]))
    return mutations


def _populate_expected_outputs(
    plan: dict[str, Any], root: Path, sqlite_path: Path, payload: dict[str, Any],
    mutations: list[dict[str, Any]], target_ids: set[str], truth: Any,
) -> None:
    with tempfile.TemporaryDirectory(prefix="media-truth-plan-") as temp:
        temp_root = Path(temp)
        candidate_db = temp_root / "candidate.db"; candidate_json = temp_root / "candidate.json"
        shutil.copy2(sqlite_path, candidate_db)
        conn = sqlite3.connect(candidate_db)
        try:
            for mutation in mutations:
                if mutation["store"] == "sqlite":
                    apply_module._sqlite_mutation(conn, mutation)
            conn.commit()
        finally:
            conn.close()
        candidate_payload = copy.deepcopy(payload)
        apply_module._apply_json_mutations(candidate_payload, [m for m in mutations if m["store"] == "json"])
        candidate_json.write_bytes(_json_render(candidate_payload))
        before_digests = _digest_bundle(sqlite_path, payload, target_ids)
        after_digests = _digest_bundle(candidate_db, candidate_payload, target_ids)
        plan["verification"]["unrelatedDigests"] = {
            "sqlite": {"before": before_digests["sqlite"], "after": after_digests["sqlite"]},
            "json": {"before": before_digests["json"], "after": after_digests["json"]},
        }
        plan["verification"]["targets"] = {
            record_id: {"sqlite": _sqlite_snapshot(candidate_db)[0].get(record_id), "json": next(row for row in candidate_payload["entities"] if row.get("id") == record_id)}
            for record_id in truth.ai_generated + truth.generated_placeholder
        }
        sqlite_snapshot = _sqlite_snapshot(candidate_db)
        plan["expectedOutputs"] = {
            "jsonSha256": _sha(candidate_json),
            "sqliteLogicalDigest": sqlite_logical_digest(candidate_db),
            "candidateRowCounts": {"sqliteEntities": len(sqlite_snapshot[0]), "jsonEntities": len(candidate_payload["entities"]), "sqliteRelationships": len(sqlite_snapshot[1]), "jsonRelationships": len(candidate_payload["relationships"])},
            "assetSha256": {record_id: item["sha256"] for record_id, item in plan["affectedAssets"].items()},
        }


def build_plan(root: Path, sqlite_path: Path, json_path: Path, truth_path: Path) -> dict[str, Any]:
    root, sqlite_path, json_path, truth_path = map(Path, (root, sqlite_path, json_path, truth_path))
    root = root.resolve(); sqlite_path = sqlite_path.resolve(); json_path = json_path.resolve(); truth_path = truth_path.resolve()
    truth, payload, sqlite_entities, sqlite_relationships, json_entities = _load_plan_inputs(root, sqlite_path, json_path, truth_path)
    assets = _validate_scope(root, truth, payload, sqlite_entities, sqlite_relationships, json_entities)
    mutations = _build_mutations(truth, payload, sqlite_entities, sqlite_relationships, json_entities)
    all_ids = tuple(truth.delete + truth.ai_generated + truth.generated_placeholder)
    plan: dict[str, Any] = {
        "schemaVersion": 1,
        "mode": "media-truth-reconciliation",
        "status": "review_required",
        "mutationAllowed": False,
        "inputs": {
            "sqlite": {"path": _stable(sqlite_path, root), "sha256": _sha(sqlite_path)},
            "json": {"path": _stable(json_path, root), "sha256": _sha(json_path)},
            "truthManifest": {"path": _stable(truth_path, root), "sha256": _sha(truth_path)},
        },
        "summary": {"batch21Records": 40, "deletedEntities": 1, "retainedPlaceholders": 37, "retainedAi": 2, "jsonRelationshipsDeleted": 6, "sqliteRelationshipsDeleted": 0},
        "mutations": mutations,
        "verification": {"mode": "targeted-media-v1", "entityIds": sorted(all_ids)},
        "affectedAssets": assets,
    }
    target_ids = set(all_ids)
    _populate_expected_outputs(plan, root, sqlite_path, payload, mutations, target_ids, truth)
    return plan


def render_plan(plan: dict[str, Any]) -> bytes:
    return (json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--sqlite", type=Path, default=Path("agent/data/vinhlong360.db"))
    parser.add_argument("--json", dest="json_path", type=Path, default=Path("web/data.json"))
    parser.add_argument("--truth", type=Path, default=Path("docs/standards/batch-21-media-truth.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    def rooted(path: Path) -> Path:
        return path if path.is_absolute() else root / path
    try:
        plan = build_plan(root, rooted(args.sqlite), rooted(args.json_path), rooted(args.truth))
        output = rooted(args.output).resolve()
        protected = {(root / "agent/data/vinhlong360.db").resolve(), (root / "web/data.json").resolve()}
        if output in protected:
            raise PlanError("protected output path")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(render_plan(plan))
    except (PlanError, OSError, sqlite3.Error, ValueError) as exc:
        print(f"media truth plan refused: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
