"""Produce deterministic, read-only parity evidence for SQLite and JSON stores."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any


JSON_ENTITY_FIELDS = ("season", "attributes", "source", "images", "coordinates")
ENTITY_FIELDS = (
    "type", "name", "summary", "description", "placeId", "confidence",
    "season", "source", "images", "coordinates", "area", "level",
    "parentId", "legacyArea", "updatedAt", "created_at", "status",
    "verified", "address", "phone", "website", "hours", "price_range",
    "sub_category", "best_time", "highlight", "revision",
)
PROVENANCE_FIELDS = (
    "verifiedAt", "verifiedSource", "source_citations",
    "image_author", "image_source", "image_license",
)
ITINERARY_FIELDS = (
    "title", "area", "areas", "duration", "summary", "stops", "created_at",
)
_SQLITE_TABLE_IDENTIFIERS = {
    "entities": '"entities"',
    "relationships": '"relationships"',
    "itineraries": '"itineraries"',
}
_SQLITE_RECORD_TABLE_IDENTIFIERS = {
    table: _SQLITE_TABLE_IDENTIFIERS[table] for table in ("entities", "itineraries")
}

Triple = tuple[str, str, str]


def open_readonly(sqlite_path: Path) -> sqlite3.Connection:
    uri = f"file:{sqlite_path.resolve().as_posix()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def decode_json(value: object, *, record_id: str, field: str, errors: list[dict]) -> object:
    if value is None or not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        errors.append({"recordId": record_id, "field": field, "error": type(exc).__name__})
        return {"$malformed": value}


def triple_dict(triple: Triple) -> dict[str, str]:
    return {"from": triple[0], "to": triple[1], "type": triple[2]}


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _stable_input_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(_workspace_root()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _input_evidence(path: Path) -> dict[str, Any]:
    return {
        "path": _stable_input_path(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "mtimeNs": path.stat().st_mtime_ns,
    }


def _safe_input_evidence(path: Path) -> dict[str, Any]:
    evidence: dict[str, Any] = {"path": _stable_input_path(path), "sha256": None, "mtimeNs": None}
    try:
        evidence.update(_input_evidence(path))
    except OSError:
        pass
    return evidence


def _empty_counts() -> dict[str, dict[str, int]]:
    return {
        store: {
            "entityRows": 0,
            "relationshipRows": 0,
            "relationshipUniqueTriples": 0,
            "itineraries": 0,
        }
        for store in ("sqlite", "json")
    }


def _empty_record_diff() -> dict[str, Any]:
    return {
        "sqliteCount": 0,
        "jsonCount": 0,
        "sqliteOnlyIds": [],
        "jsonOnlyIds": [],
        "fieldDifferences": [],
    }


def _empty_relationship_diff() -> dict[str, Any]:
    return {
        "sqliteRowCount": 0,
        "jsonRowCount": 0,
        "duplicateSqliteTriples": [],
        "duplicateJsonTriples": [],
        "sqliteOnlyTriples": [],
        "jsonOnlyTriples": [],
        "typeSubstitutions": [],
        "invalidSqliteEndpoints": [],
        "invalidJsonEndpoints": [],
    }


def _error_report(sqlite_path: Path, json_path: Path, errors: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "status": "error",
        "inputs": {"sqlite": _safe_input_evidence(sqlite_path), "json": _safe_input_evidence(json_path)},
        "counts": _empty_counts(),
        "entityDiff": _empty_record_diff(),
        "relationshipDiff": _empty_relationship_diff(),
        "itineraryDiff": _empty_record_diff(),
        "provenanceDiff": {"fieldDifferences": []},
        "errors": errors,
    }


def _require_sqlite_columns(connection: sqlite3.Connection, table: str, required: set[str]) -> None:
    try:
        table_identifier = _SQLITE_TABLE_IDENTIFIERS[table]
    except KeyError:
        raise ValueError(f"Unsupported SQLite table: {table!r}") from None
    columns = {
        str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table_identifier})")
    }
    missing = sorted(required - columns)
    if missing:
        raise ValueError(f"SQLite table {table!r} is missing required columns: {', '.join(missing)}")


def _load_sqlite_records(
    connection: sqlite3.Connection,
    table: str,
    json_fields: tuple[str, ...],
    errors: list[dict],
) -> dict[str, dict[str, Any]]:
    try:
        table_identifier = _SQLITE_RECORD_TABLE_IDENTIFIERS[table]
    except KeyError:
        raise ValueError(f"Unsupported SQLite record table: {table!r}") from None
    records: dict[str, dict[str, Any]] = {}
    for row in connection.execute(f"SELECT * FROM {table_identifier} ORDER BY id"):
        record_id = row["id"]
        if not isinstance(record_id, str) or not record_id:
            raise ValueError(f"SQLite {table} contain a missing or invalid id")
        if record_id in records:
            raise ValueError(f"SQLite {table} contain duplicate id: {record_id}")
        record = {column: row[column] for column in row.keys()}
        for field in json_fields:
            record[field] = decode_json(record.get(field), record_id=record_id, field=field, errors=errors)
        records[record_id] = record
    return records


def _load_sqlite_relationships(connection: sqlite3.Connection) -> list[Triple]:
    return [
        (str(row["from_id"]), str(row["to_id"]), str(row["type"]))
        for row in connection.execute(
            "SELECT from_id, to_id, type FROM relationships ORDER BY from_id, to_id, type"
        )
    ]


def _load_sqlite(sqlite_path: Path, errors: list[dict]) -> dict[str, Any]:
    with open_readonly(sqlite_path) as connection:
        _require_sqlite_columns(connection, "entities", {"id", *JSON_ENTITY_FIELDS})
        _require_sqlite_columns(connection, "relationships", {"from_id", "to_id", "type"})
        _require_sqlite_columns(connection, "itineraries", {"id", "areas", "stops"})
        entities = _load_sqlite_records(connection, "entities", JSON_ENTITY_FIELDS, errors)
        relationships = _load_sqlite_relationships(connection)
        itineraries = _load_sqlite_records(connection, "itineraries", ("areas", "stops"), errors)

    return {"entities": entities, "relationships": relationships, "itineraries": itineraries}


def _index_json_records(records: list[dict[str, Any]], collection: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records):
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise ValueError(f"JSON {collection}[{index}] requires a non-empty string id")
        if record_id in indexed:
            raise ValueError(f"JSON {collection} contains duplicate id: {record_id}")
        indexed[record_id] = record
    return indexed


def _load_json(json_path: Path) -> dict[str, Any]:
    with json_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")

    collections: dict[str, list[dict[str, Any]]] = {}
    for name in ("entities", "relationships", "itineraries"):
        records = payload.get(name)
        if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
            raise ValueError(f"JSON field {name!r} must be a list of objects")
        collections[name] = records

    entities = _index_json_records(collections["entities"], "entities")
    itineraries = _index_json_records(collections["itineraries"], "itineraries")
    relationships: list[Triple] = []
    for record in collections["relationships"]:
        if not all(isinstance(record.get(field), str) for field in ("from", "to", "type")):
            raise ValueError("JSON relationships require string from, to, and type fields")
        relationships.append((record["from"], record["to"], record["type"]))

    return {"entities": entities, "relationships": relationships, "itineraries": itineraries}


def _field_differences(
    record_id: str,
    left: Any,
    right: Any,
    field: str,
) -> list[dict[str, Any]]:
    if isinstance(left, dict) and isinstance(right, dict):
        differences: list[dict[str, Any]] = []
        for key in sorted(set(left) | set(right)):
            nested_field = f"{field}.{key}" if field else key
            differences.extend(_field_differences(record_id, left.get(key), right.get(key), nested_field))
        return differences
    if left != right:
        return [{"id": record_id, "field": field, "sqlite": left, "json": right}]
    return []


def _attribute_parts(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    attributes = record.get("attributes")
    if not isinstance(attributes, dict):
        return {}, {}
    ordinary = {key: value for key, value in attributes.items() if key not in PROVENANCE_FIELDS}
    provenance = {key: attributes.get(key) for key in PROVENANCE_FIELDS if key in attributes}
    return ordinary, provenance


def _record_diff(
    sqlite_records: dict[str, dict[str, Any]],
    json_records: dict[str, dict[str, Any]],
    fields: tuple[str, ...],
    *,
    compare_attributes: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sqlite_ids = set(sqlite_records)
    json_ids = set(json_records)
    field_differences: list[dict[str, Any]] = []
    provenance_differences: list[dict[str, Any]] = []
    for record_id in sorted(sqlite_ids & json_ids):
        sqlite_record = sqlite_records[record_id]
        json_record = json_records[record_id]
        for field in fields:
            field_differences.extend(
                _field_differences(record_id, sqlite_record.get(field), json_record.get(field), field)
            )
        if compare_attributes:
            sqlite_attributes, sqlite_provenance = _attribute_parts(sqlite_record)
            json_attributes, json_provenance = _attribute_parts(json_record)
            field_differences.extend(
                _field_differences(record_id, sqlite_attributes, json_attributes, "attributes")
            )
            provenance_differences.extend(
                _field_differences(record_id, sqlite_provenance, json_provenance, "attributes")
            )

    field_differences.sort(key=lambda item: (item["id"], item["field"]))
    provenance_differences.sort(key=lambda item: (item["id"], item["field"]))
    return (
        {
            "sqliteCount": len(sqlite_records),
            "jsonCount": len(json_records),
            "sqliteOnlyIds": sorted(sqlite_ids - json_ids),
            "jsonOnlyIds": sorted(json_ids - sqlite_ids),
            "fieldDifferences": field_differences,
        },
        provenance_differences,
    )


def _duplicates(counter: Counter[Triple]) -> list[dict[str, Any]]:
    return [
        {**triple_dict(triple), "extraRows": count - 1}
        for triple, count in sorted(counter.items())
        if count > 1
    ]


def _invalid_endpoints(triples: set[Triple], entity_ids: set[str]) -> list[dict[str, Any]]:
    invalid: list[dict[str, Any]] = []
    for triple in sorted(triples):
        missing_from = triple[0] not in entity_ids
        missing_to = triple[1] not in entity_ids
        if missing_from or missing_to:
            invalid.append(
                {
                    **triple_dict(triple),
                    "missingFrom": missing_from,
                    "missingTo": missing_to,
                }
            )
    return invalid


def _types_by_pair(triples: set[Triple]) -> dict[tuple[str, str], list[str]]:
    types: dict[tuple[str, str], set[str]] = defaultdict(set)
    for from_id, to_id, relationship_type in triples:
        types[(from_id, to_id)].add(relationship_type)
    return {pair: sorted(values) for pair, values in types.items()}


def _relationship_diff(sqlite_rows: list[Triple], json_rows: list[Triple], sqlite_ids: set[str], json_ids: set[str]) -> dict[str, Any]:
    sqlite_counter = Counter(sqlite_rows)
    json_counter = Counter(json_rows)
    sqlite_triples = set(sqlite_counter)
    json_triples = set(json_counter)
    sqlite_only_types = _types_by_pair(sqlite_triples - json_triples)
    json_only_types = _types_by_pair(json_triples - sqlite_triples)
    substitutions = [
        {
            "from": pair[0],
            "to": pair[1],
            "sqliteTypes": sqlite_only_types[pair],
            "jsonTypes": json_only_types[pair],
        }
        for pair in sorted(set(sqlite_only_types) & set(json_only_types))
    ]
    return {
        "sqliteRowCount": len(sqlite_rows),
        "jsonRowCount": len(json_rows),
        "duplicateSqliteTriples": _duplicates(sqlite_counter),
        "duplicateJsonTriples": _duplicates(json_counter),
        "sqliteOnlyTriples": [triple_dict(triple) for triple in sorted(sqlite_triples - json_triples)],
        "jsonOnlyTriples": [triple_dict(triple) for triple in sorted(json_triples - sqlite_triples)],
        "typeSubstitutions": substitutions,
        "invalidSqliteEndpoints": _invalid_endpoints(sqlite_triples, sqlite_ids),
        "invalidJsonEndpoints": _invalid_endpoints(json_triples, json_ids),
    }


def _has_drift(report: dict[str, Any]) -> bool:
    for section in ("entityDiff", "relationshipDiff", "itineraryDiff", "provenanceDiff"):
        values = report[section]
        if any(bool(value) for key, value in values.items() if not key.endswith("Count")):
            return True
    return False


def _counts(sqlite_data: dict[str, Any], json_data: dict[str, Any]) -> dict[str, dict[str, int]]:
    def store_counts(data: dict[str, Any]) -> dict[str, int]:
        relationships = data["relationships"]
        return {
            "entityRows": len(data["entities"]),
            "relationshipRows": len(relationships),
            "relationshipUniqueTriples": len(set(relationships)),
            "itineraries": len(data["itineraries"]),
        }

    return {"sqlite": store_counts(sqlite_data), "json": store_counts(json_data)}


def build_report(sqlite_path: Path, json_path: Path) -> dict:
    """Load protected inputs and return stable evidence without changing either one."""
    errors: list[dict[str, str]] = []
    try:
        sqlite_evidence = _input_evidence(sqlite_path)
        json_evidence = _input_evidence(json_path)
        sqlite_data = _load_sqlite(sqlite_path, errors)
        json_data = _load_json(json_path)
    except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        return _error_report(
            sqlite_path, json_path, [{"error": type(exc).__name__, "message": str(exc)}]
        )

    entity_diff, provenance_differences = _record_diff(
        sqlite_data["entities"], json_data["entities"], ENTITY_FIELDS, compare_attributes=True
    )
    itinerary_diff, _ = _record_diff(
        sqlite_data["itineraries"], json_data["itineraries"], ITINERARY_FIELDS
    )
    relationship_diff = _relationship_diff(
        sqlite_data["relationships"],
        json_data["relationships"],
        set(sqlite_data["entities"]),
        set(json_data["entities"]),
    )
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "status": "clean",
        "inputs": {"sqlite": sqlite_evidence, "json": json_evidence},
        "counts": _counts(sqlite_data, json_data),
        "entityDiff": entity_diff,
        "relationshipDiff": relationship_diff,
        "itineraryDiff": itinerary_diff,
        "provenanceDiff": {"fieldDifferences": provenance_differences},
        "errors": sorted(errors, key=lambda item: (item["recordId"], item["field"])),
    }
    if errors or _has_drift(report):
        report["status"] = "drift"
    return report


def render_report(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _default_path(relative_path: str) -> Path:
    return _workspace_root() / relative_path


def _write_stdout(rendered: str) -> None:
    """Keep CLI evidence UTF-8 even when Windows selects a legacy code page."""
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        buffer.write(rendered.encode("utf-8"))
    else:
        sys.stdout.write(rendered)


def _is_protected_output(output_path: Path, sqlite_path: Path, json_path: Path) -> bool:
    resolved_output = output_path.resolve()
    for protected_path in (sqlite_path, json_path):
        if resolved_output == protected_path.resolve():
            return True
        try:
            if output_path.samefile(protected_path):
                return True
        except OSError:
            pass
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", type=Path, default=_default_path("agent/data/vinhlong360.db"))
    parser.add_argument("--json", dest="json_path", type=Path, default=_default_path("web/data.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-drift", action="store_true")
    args = parser.parse_args(argv)

    if args.output is not None:
        try:
            protected_output = _is_protected_output(args.output, args.sqlite, args.json_path)
        except OSError as exc:
            _write_stdout(
                render_report(
                    _error_report(
                        args.sqlite, args.json_path, [{"error": type(exc).__name__, "message": str(exc)}]
                    )
                )
            )
            return 2
        if protected_output:
            _write_stdout(
                render_report(
                    _error_report(
                        args.sqlite,
                        args.json_path,
                        [
                            {
                                "error": "ProtectedOutputPath",
                                "message": "Output path resolves to a protected audit input",
                            }
                        ],
                    )
                )
            )
            return 2

    report = build_report(args.sqlite, args.json_path)
    rendered = render_report(report)
    if args.output is not None:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            error_report = _error_report(
                args.sqlite, args.json_path, [{"error": type(exc).__name__, "message": str(exc)}]
            )
            _write_stdout(render_report(error_report))
            return 2
    _write_stdout(rendered)
    if report["status"] == "error":
        return 2
    if report["status"] == "drift" and args.fail_on_drift:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
