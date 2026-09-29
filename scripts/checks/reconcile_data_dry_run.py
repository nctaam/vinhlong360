"""Generate a deterministic, read-only data reconciliation plan."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any
from urllib.parse import urlparse

try:
    from agent.media_truth_manifest import reviewed_removal_ids
    from .provenance_url_policy import is_placeholder_hostname
except ImportError:  # pragma: no cover - direct script execution
    from agent.media_truth_manifest import reviewed_removal_ids
    from provenance_url_policy import is_placeholder_hostname


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _uri(path: Path) -> str:
    return f"file:{path.resolve().as_posix()}?mode=ro&immutable=1"


def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _stable(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path(__file__).resolve().parents[2]).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _mutation(store: str, record_type: str, record_id: str, operation: str, field: str,
              before: Any, after: Any, reason: str, evidence: list[str], **meta: Any) -> dict[str, Any]:
    seed = json.dumps([store, record_type, record_id, operation, field, before, after], sort_keys=True, ensure_ascii=False)
    mutation_id = "mut-" + hashlib.sha256(seed.encode()).hexdigest()[:16]
    out = {"mutationId": mutation_id, "store": store, "recordType": record_type, "recordId": record_id,
           "operation": operation, "field": field, "before": before, "after": after,
           "reason": reason, "evidence": sorted(evidence)}
    if meta:
        out["metadata"] = meta
    return out


def _records(path: Path) -> dict[str, dict[str, Any]]:
    payload = _load(path)
    return {str(r["id"]): r for r in payload["entities"]}


def _sqlite_entities(path: Path) -> dict[str, dict[str, Any]]:
    with sqlite3.connect(_uri(path), uri=True) as conn:
        conn.row_factory = sqlite3.Row
        return {row["id"]: dict(row) for row in conn.execute("SELECT * FROM entities")}


def _sqlite_value(record: dict[str, Any], field: str) -> Any:
    if field.startswith("attributes."):
        attributes = json.loads(record.get("attributes") or "{}")
        return attributes.get(field.removeprefix("attributes."))
    return record.get(field)


def _photo_provenance_requirements(item: dict[str, Any]) -> list[str]:
    """Return the missing evidence needed before proposing a documentary image."""
    requirements = []
    if not _has_image_source_url(item):
        requirements.append("image-specific source URL")
    if not _has_permission_evidence(item):
        requirements.append("explicit permission evidence")
    return requirements


def _has_image_source_url(item: dict[str, Any]) -> bool:
    source_url = item.get("image_source_url")
    if not isinstance(source_url, str):
        return False
    parsed = urlparse(source_url.strip())
    hostname = (parsed.hostname or "").lower().rstrip(".")
    return bool(
        parsed.scheme in {"http", "https"}
        and parsed.netloc
        and hostname
        and not is_placeholder_hostname(hostname)
    )


def _has_permission_evidence(item: dict[str, Any]) -> bool:
    permission = item.get("permission_evidence") or item.get("rights_evidence") or item.get("permission")
    return isinstance(permission, str) and bool(permission.strip())


def _validate_parity_inputs(parity: dict[str, Any], sqlite_path: Path, json_path: Path) -> None:
    expected = parity.get("inputs", {})
    for name, path in (("sqlite", sqlite_path), ("json", json_path)):
        if expected.get(name, {}).get("sha256") != _sha(path):
            raise ValueError(f"parity input hash mismatch for {name}")


def _relationship_context(sqlite_path: Path, json_path: Path, parity: dict[str, Any], phase7_path: Path) -> dict[str, Any]:
    rel = parity["relationshipDiff"]
    phase7 = _load(phase7_path)
    phase7_tuples = {(x.get("from"), x.get("to"), x.get("old_type"), x.get("new_type")) for x in phase7}
    sqlite_only = {(x["from"], x["to"], x["type"]) for x in rel.get("sqliteOnlyTriples", [])}
    json_only = {(x["from"], x["to"], x["type"]) for x in rel.get("jsonOnlyTriples", [])}
    shared = {(x["from"], x["to"], x["type"]) for x in rel.get("sharedTriples", [])}
    if not shared:
        shared = {(x["from"], x["to"], x["type"]) for x in rel.get("shared", [])}
    with sqlite3.connect(_uri(sqlite_path), uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT rowid, from_id, to_id, type FROM relationships ORDER BY rowid").fetchall()
    rowmap = {(r["from_id"], r["to_id"], r["type"]): r for r in rows}
    json_rels = _load(json_path)["relationships"]
    if not shared:
        shared = set(rowmap).intersection({(x.get("from"), x.get("to"), x.get("type")) for x in json_rels})
    return {"rel": rel, "phase7Tuples": phase7_tuples, "sqliteOnly": sqlite_only,
            "jsonOnly": json_only, "shared": shared, "rowmap": rowmap, "jsonRels": json_rels}


def _relationship_substitutions(context: dict[str, Any], phase7_path: Path) -> list[dict[str, Any]]:
    mutations = []
    rel, phase7_tuples = context["rel"], context["phase7Tuples"]
    for item in rel.get("typeSubstitutions", []):
        old = (item["from"], item["to"], item["sqliteTypes"][0])
        new = (item["from"], item["to"], item["jsonTypes"][0])
        marker = (item["from"], item["to"], old[2], new[2])
        row = context["rowmap"].get(old)
        if old not in context["sqliteOnly"] or new not in context["jsonOnly"] or marker not in phase7_tuples or not row:
            continue
        mutations.append(_mutation("sqlite", "relationship", f"{item['from']}->{item['to']}", "update", "type",
            old[2], new[2], "Phase 7 relationship type reconciliation", [_stable(phase7_path)], rowid=row["rowid"]))
    return mutations


def _relationship_obsolete(context: dict[str, Any], phase7_path: Path) -> list[dict[str, Any]]:
    mutations = []
    rel, phase7_tuples = context["rel"], context["phase7Tuples"]
    substituted = {(x["from"], x["to"], x["sqliteTypes"][0]) for x in rel.get("typeSubstitutions", [])}
    json_triples = {(x["from"], x["to"], x["type"]) for x in context["jsonRels"]}
    for old in sorted(context["sqliteOnly"] - substituted):
        new = (old[0], old[1], "related_to")
        marker = (old[0], old[1], old[2], "related_to")
        row = context["rowmap"].get(old)
        if new not in context["shared"] or marker not in phase7_tuples or old in json_triples or not row:
            continue
        mutations.append(_mutation("sqlite", "relationship", f"{old[0]}->{old[1]}", "delete", "relationship",
            {"from": old[0], "to": old[1], "type": old[2]}, None,
            "SQLite-only obsolete relationship", [_stable(phase7_path)], rowid=row["rowid"]))
    return mutations


def _duplicate_relationship_mutations(context: dict[str, Any], parity_path: Path) -> list[dict[str, Any]]:
    mutations = []
    for duplicate in context["rel"].get("duplicateJsonTriples", []):
        triple = (duplicate["from"], duplicate["to"], duplicate["type"])
        indexes = [i for i, row in enumerate(context["jsonRels"])
                   if (row.get("from"), row.get("to"), row.get("type")) == triple]
        if len(indexes) <= 1:
            continue
        index = max(indexes)
        mutations.append(_mutation("json", "relationship", f"{triple[0]}->{triple[1]}", "delete", "relationship",
            context["jsonRels"][index], None, "Remove highest-index duplicate relationship", [_stable(parity_path)], index=index))
    return mutations


def _relationship_mutations(context: dict[str, Any], phase7_path: Path, parity_path: Path) -> list[dict[str, Any]]:
    return (
        _relationship_substitutions(context, phase7_path)
        + _relationship_obsolete(context, phase7_path)
        + _duplicate_relationship_mutations(context, parity_path)
    )


def _spatial_mutations(sqlite_entities: dict[str, dict[str, Any]], spatial_path: Path,
                       tombstones: frozenset[str]) -> list[dict[str, Any]]:
    if "prov-1" in tombstones:
        return []
    spatial = _load(spatial_path)
    prov = spatial.get("coordinate_remediations", {}).get("prov_1_fix", {})
    current = sqlite_entities.get("prov-1", {})
    mutations = []
    fields = (
        ("coordinates", prov.get("current_value"), prov.get("proposed_value")),
        ("placeId", prov.get("place_id_remediation", {}).get("current_place_id"), prov.get("place_id_remediation", {}).get("proposed_place_id")),
        ("address", prov.get("address_remediation", {}).get("current_address"), prov.get("address_remediation", {}).get("proposed_address")),
    )
    for field, before, after in fields:
        meta = {"storage": "json_text"} if field in {"coordinates", "images"} or field.startswith("attributes.") else {}
        mutations.append(_mutation("sqlite", "entity", "prov-1", "update", field, current.get(field, before), after,
            "Spatial remediation for prov-1", [_stable(spatial_path)], **meta))
    return mutations


def _photo_mutations(current: dict[str, Any], photos_path: Path,
                     tombstones: frozenset[str]) -> tuple[list[dict[str, Any]], list[str], bool]:
    if "prov-1" in tombstones:
        return [], [], False
    mutations = []
    requirements = []
    has_deferred = False
    for item in _load(photos_path):
        if item.get("entity_id") != "prov-1":
            continue
        missing = _photo_provenance_requirements(item)
        if missing:
            has_deferred = True
            for requirement in missing:
                if requirement not in requirements:
                    requirements.append(requirement)
            continue
        fields = (("images", ["/img/entities/prov-1.webp"]), ("attributes.image_type", "documentary"),
                  ("attributes.is_verified_photo", True), ("attributes.image_author", item.get("author")),
                  ("attributes.image_source", item.get("source")), ("attributes.image_caption", item.get("caption")),
                  ("attributes.image_license", item.get("license")))
        for field, value in fields:
            mutations.append(_mutation("sqlite", "entity", "prov-1", "update", field, _sqlite_value(current, field), value,
                "Culinary photo attribution ledger", [_stable(photos_path)], storage="json_text"))
    return mutations, requirements, has_deferred


def _orphan_mutations(master_path: Path, tombstones: frozenset[str]) -> list[dict[str, Any]]:
    if "prov-1" in tombstones:
        return []
    remediations = _load(master_path)["remediations"]
    relationship = next((item for item in remediations
                         if item.get("entity_id") == "prov-1" and item.get("field") == "relationships"), {})
    return [_mutation("sqlite", "relationship", f"prov-1->{edge['to_id']}", "insert", "relationship", None, edge,
                      "Explicit orphan graph remediation", [_stable(master_path)])
            for edge in relationship.get("proposed_value", [])]


def _phase21_mutations(sqlite_entities: dict[str, dict[str, Any]], phase21_path: Path) -> list[dict[str, Any]]:
    mutations = []
    for item in _load(phase21_path).get("remediated", []):
        if "Bến Phà" not in item.get("name", ""):
            continue
        record = sqlite_entities.get(item["id"], {})
        current = _sqlite_value(record, "attributes.image_caption")
        if current in (None, item.get("old_caption")):
            mutations.append(_mutation("sqlite", "entity", item["id"], "update", "attributes.image_caption", current,
                item.get("new_caption"), "Phase 21 caption correction", [_stable(phase21_path)], storage="json_text"))
    return mutations


def _batch7_mutations(sqlite_entities: dict[str, dict[str, Any]], batch7_path: Path) -> list[dict[str, Any]]:
    mutations = []
    for item in _load(batch7_path):
        if item.get("id") != "ben-pha-tran-phu-can-tho-vinh-long-vinh-long" or "key_facts" not in item.get("changes", {}):
            continue
        change = item["changes"]["key_facts"]
        record = sqlite_entities[item["id"]]
        current = _sqlite_value(record, "attributes.key_facts")
        if current in (None, change.get("old")):
            mutations.append(_mutation("sqlite", "entity", item["id"], "update", "attributes.key_facts", current,
                change.get("new"), "Batch 7 enrichment", [_stable(batch7_path)], storage="json_text"))
    return mutations


def _deferred_items(sqlite_entities: dict[str, dict[str, Any]], json_path: Path, parity_path: Path,
                    ledger_paths: dict[str, Path], photo_requirements: list[str], photo_has_deferred: bool,
                    tombstones: frozenset[str]) -> list[dict[str, Any]]:
    temporal = _load(ledger_paths["temporal"])
    conflict = next(item for item in temporal["remediation_ledger"] if item.get("entity_id") == "le-chol-chhnam-thmay")
    deferred = [{"itemId": "owner-conflict-le-chol-chhnam-thmay", "recordType": "entity", "recordId": "le-chol-chhnam-thmay",
                 "reason": "Owner conflict requires review", "current": conflict["current_values"],
                 "options": conflict["decision_matrix"], "evidence": [_stable(ledger_paths["temporal"])]}]
    if photo_has_deferred and "prov-1" not in tombstones:
        deferred.append({"itemId": "prov-1-image-provenance", "recordType": "entity", "recordId": "prov-1",
                         "reason": "Documentary image provenance deferred until requirements are met",
                         "requirements": photo_requirements, "evidence": [_stable(ledger_paths["photos"])]})
    deferred.extend([
        *([{"itemId": "prov-1-text-gaps", "recordType": "entity", "recordId": "prov-1",
            "reason": "Description, subcategory, and season gaps deferred", "evidence": [_stable(parity_path)]}]
          if "prov-1" not in tombstones else []),
        {"itemId": "vuon-trai-cay-noi-tieng", "recordType": "entity", "recordId": "vuon-trai-cay-cu-lao-dai",
         "reason": "Unresolved nổi tiếng prose", "evidence": [_stable(parity_path)]},
    ])
    json_entities = _records(json_path)
    verified_ids = ("ben-pha-tran-phu-can-tho-vinh-long-vinh-long", "vuon-trai-cay-cu-lao-dai", "prov-1")
    for record_id in verified_ids:
        if record_id in tombstones:
            continue
        sqlite_value = _sqlite_value(sqlite_entities.get(record_id, {}), "attributes.verifiedAt")
        json_value = (json_entities.get(record_id, {}).get("attributes") or {}).get("verifiedAt")
        deferred.append({"itemId": f"verifiedAt-{record_id}", "recordType": "entity", "recordId": record_id,
                         "reason": "verifiedAt differs between stores", "current": {"sqlite": sqlite_value, "json": json_value},
                         "evidence": [_stable(parity_path)]})
    return deferred


def _plan_document(sqlite_path: Path, json_path: Path, parity_path: Path,
                   mutations: list[dict[str, Any]], deferred: list[dict[str, Any]]) -> dict[str, Any]:
    mutations.sort(key=lambda m: (m["store"], m["recordType"], m["recordId"], m["field"], m["operation"], m["mutationId"]))
    deferred.sort(key=lambda d: (d["recordType"], d["recordId"], d["itemId"]))
    inputs = {
        "sqlite": {"path": _stable(sqlite_path), "sha256": _sha(sqlite_path)},
        "json": {"path": _stable(json_path), "sha256": _sha(json_path)},
        "parity": {"path": _stable(parity_path), "sha256": _sha(parity_path)},
    }
    return {"schemaVersion": 1, "mode": "dry-run", "status": "review_required", "inputs": inputs,
            "summary": {"mutationCount": len(mutations), "deferredCount": len(deferred)},
            "mutations": mutations, "deferred": deferred, "errors": []}


def build_plan(sqlite_path, json_path, parity_path, ledger_paths, *, root: Path | None = None) -> dict[str, Any]:
    sqlite_path, json_path, parity_path = map(Path, (sqlite_path, json_path, parity_path))
    manifest_root = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    tombstones = reviewed_removal_ids(manifest_root)
    parity = _load(parity_path)
    _validate_parity_inputs(parity, sqlite_path, json_path)
    ledgers = {key: Path(value) for key, value in ledger_paths.items()}
    context = _relationship_context(sqlite_path, json_path, parity, ledgers["phase7"])
    mutations = _relationship_mutations(context, ledgers["phase7"], parity_path)
    sqlite_entities = _sqlite_entities(sqlite_path)
    mutations.extend(_spatial_mutations(sqlite_entities, ledgers["spatial"], tombstones))
    photo_changes, photo_requirements, photo_has_deferred = _photo_mutations(sqlite_entities.get("prov-1", {}), ledgers["photos"], tombstones)
    mutations.extend(photo_changes)
    mutations.extend(_orphan_mutations(ledgers["master"], tombstones))
    mutations.extend(_phase21_mutations(sqlite_entities, ledgers["phase21"]))
    mutations.extend(_batch7_mutations(sqlite_entities, ledgers["batch7"]))
    deferred = _deferred_items(sqlite_entities, json_path, parity_path, ledgers, photo_requirements, photo_has_deferred, tombstones)
    return _plan_document(sqlite_path, json_path, parity_path, mutations, deferred)


def render_plan(plan: dict[str, Any]) -> str:
    return json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default="agent/data/vinhlong360.db")
    parser.add_argument("--json", dest="json_path", default="web/data.json")
    parser.add_argument("--parity", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    def rooted(value: str) -> Path:
        candidate = Path(value)
        return candidate if candidate.is_absolute() else root / candidate
    sqlite_arg, json_arg, parity_arg, output = rooted(args.sqlite), rooted(args.json_path), rooted(args.parity), rooted(args.output).resolve()
    protected = {sqlite_arg.resolve(), json_arg.resolve(), parity_arg.resolve()}
    ledger_files = list((root / "outputs").glob("*.json"))
    targets = protected | {path.resolve() for path in ledger_files}
    try:
        collision = output.exists() or any(output.samefile(path) for path in targets if path.exists())
    except OSError:
        collision = False
    if collision or output in targets:
        return 2
    try:
        ledgers = {p.stem: p for p in (root / "outputs").glob("*.json")}
        aliases = {"phase7": ledgers["remediation_phase7_log"], "spatial": ledgers["remediation_spatial"], "master": ledgers["data_remediation_ledger"], "photos": ledgers["batch_culinary_restaurants_photos"], "phase21": ledgers["remediation_phase21_image_log"], "batch7": ledgers["batch7_master_enrichment_log"], "temporal": ledgers["remediation_temporal"]}
        plan = build_plan(sqlite_arg, json_arg, parity_arg, aliases)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_plan(plan), encoding="utf-8")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(json.dumps({"schemaVersion": 1, "mode": "dry-run", "status": "error", "errors": [{"type": type(exc).__name__, "message": str(exc)}]}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
