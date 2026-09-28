"""Safely apply an approved reconciliation plan to fixture stores.

This module deliberately keeps the write path separate from the read-only
parity and dry-run commands.  Callers must provide an approval marker, the
canonical plan digest, verified backups, and an explicit confirmation.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any
import uuid

try:
    from .reconciliation_journal import JournalError, load_journal, recover_journal
    from .reconciliation_journal import write_journal
    from .reconciliation_lock import LockBusyError, LockPathError, ReconciliationLock
except ImportError:  # pragma: no cover - supports direct script execution
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.checks.reconciliation_journal import JournalError, load_journal, recover_journal
    from scripts.checks.reconciliation_journal import write_journal
    from scripts.checks.reconciliation_lock import LockBusyError, LockPathError, ReconciliationLock


class ApplyError(ValueError):
    """Raised when an apply request fails closed."""


_RACE_HOOKS: dict[str, Any] = {}


def _race_hook(name: str, *args: Any, **kwargs: Any) -> Any:
    callback = _RACE_HOOKS.get(name)
    if callback is not None:
        return callback(*args, **kwargs)
    return None


def _identity_dict(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {"device": stat.st_dev, "inode": stat.st_ino, "size": stat.st_size}


def _unique_json_artifact(json_path: Path, label: str) -> Path:
    return json_path.with_name(f".{json_path.name}.{label}.{uuid.uuid4().hex}")


def _capture_json_target(
    json_path: Path,
    capture_path: Path,
    expected_sha256: str,
    expected_identity: tuple[int, int, int, int],
) -> None:
    """Move the approved target aside without overwriting an existing capture."""
    json_path, capture_path = Path(json_path), Path(capture_path)
    if capture_path.exists():
        raise ApplyError("JSON capture path already exists")
    _race_hook("before_capture", json_path, capture_path)
    if capture_path.exists():
        raise ApplyError("JSON capture path was recreated")
    # A hard link is the portable exclusive-create primitive.  Linking first
    # avoids an overwrite window that exists with rename on Windows.
    try:
        os.link(json_path, capture_path)
    except FileExistsError as exc:
        raise ApplyError("JSON capture path was recreated") from exc
    except OSError as exc:
        raise ApplyError(f"JSON target capture failed: {exc}") from exc
    try:
        if _sha(capture_path) != expected_sha256 or _file_identity(capture_path) != expected_identity:
            raise ApplyError("captured JSON does not match approved input")
    except OSError as exc:
        raise ApplyError("captured JSON cannot be verified") from exc
    try:
        if _sha(json_path) != expected_sha256 or _file_identity(json_path) != expected_identity:
            raise ApplyError("JSON target changed during capture")
        json_path.unlink()
    except OSError as exc:
        raise ApplyError(f"JSON target capture finalization failed: {exc}") from exc
    _race_hook("after_capture", json_path, capture_path)
    try:
        if _sha(capture_path) != expected_sha256 or _file_identity(capture_path) != expected_identity:
            raise ApplyError("captured JSON changed after capture")
    except OSError as exc:
        raise ApplyError("captured JSON cannot be verified") from exc


def _publish_json_no_overwrite(candidate_path: Path, json_path: Path) -> tuple[int, int, int, int]:
    """Publish a candidate with an exclusive hard link, never replacing a target."""
    candidate_path, json_path = Path(candidate_path), Path(json_path)
    _race_hook("before_publish", candidate_path, json_path)
    try:
        os.link(candidate_path, json_path)
    except FileExistsError as exc:
        raise ApplyError("JSON target changed before publication") from exc
    except OSError as exc:
        raise ApplyError(f"JSON publication failed: {exc}") from exc
    try:
        identity = _file_identity(json_path)
    except OSError as exc:
        raise ApplyError("published JSON cannot be verified") from exc
    _race_hook("after_publish", candidate_path, json_path)
    return identity


def _restore_captured_json(
    json_path: Path,
    capture_path: Path,
    *,
    published_sha256: str | None = None,
    published_identity: dict[str, int] | tuple[int, int, int, int] | None = None,
    state: dict[str, Any] | None = None,
    journal_path: Path | None = None,
) -> Path | None:
    """Preserve an observed target, then restore the original capture atomically."""
    json_path, capture_path = Path(json_path), Path(capture_path)
    observed_path: Path | None = None
    _race_hook("before_rollback_capture", json_path, capture_path)
    if json_path.exists():
        observed_path = _unique_json_artifact(json_path, "observed")
        try:
            os.rename(json_path, observed_path)
        except OSError as exc:
            raise ApplyError(f"JSON rollback capture failed: {exc}") from exc
        observed_sha256 = _sha(observed_path)
        observed_identity = _identity_dict(observed_path)
        matches = published_sha256 is not None and observed_sha256 == published_sha256
        if matches and published_identity is not None:
            if isinstance(published_identity, dict):
                expected = tuple(int(published_identity[key]) for key in ("device", "inode", "size"))
            else:
                expected = tuple(published_identity[:3])
            matches = tuple(observed_identity[key] for key in ("device", "inode", "size")) == expected
        if state is not None and not matches:
            store = state.setdefault("json", {})
            store["observedPath"] = str(observed_path)
            store["observedSha256"] = observed_sha256
            store["observedIdentity"] = observed_identity
            if journal_path is not None:
                write_journal(Path(journal_path), state)
        elif matches:
            observed_path.unlink(missing_ok=True)
            observed_path = None
    if not capture_path.exists():
        raise ApplyError("original JSON capture is missing")
    if json_path.exists():
        raise ApplyError("JSON target was recreated during rollback")
    try:
        os.link(capture_path, json_path)
        capture_path.unlink()
    except FileExistsError as exc:
        raise ApplyError("JSON target was recreated during rollback") from exc
    except OSError as exc:
        raise ApplyError(f"JSON capture restore failed: {exc}") from exc
    return observed_path


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _file_identity(path: Path) -> tuple[int, int, int, int]:
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def _json_target_matches(path: Path, expected_bytes: bytes, expected_identity: tuple[int, int, int, int]) -> bool:
    try:
        return _file_identity(path) == expected_identity and path.read_bytes() == expected_bytes
    except OSError:
        return False


def _verify_recovery_json_ownership(state: dict[str, Any]) -> None:
    """Refuse recovery unless JSON is still a journaled state we own.

    The shared advisory lock coordinates cooperating writers. A non-cooperating
    writer can still race after this check, so this is fail-closed validation,
    not a portable cross-process compare-and-swap guarantee.
    """
    store = state["json"]
    target = Path(store["path"])
    try:
        actual = _sha(target)
        actual_identity = _file_identity(target)
    except OSError as exc:
        raise ApplyError("JSON target ownership cannot be verified") from exc
    before_sha256 = store["beforeSha256"]
    if actual == before_sha256:
        before_identity = store["beforeIdentity"]
        try:
            expected_identity = (
                int(before_identity["device"]),
                int(before_identity["inode"]),
                int(before_identity["size"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ApplyError("JSON target ownership cannot be verified") from exc
        if actual_identity[:3] != expected_identity:
            raise ApplyError("JSON target ownership cannot be verified")
        return
    staged_sha256 = store.get("stagedSha256")
    if not isinstance(staged_sha256, str) or actual != staged_sha256:
        raise ApplyError("JSON target ownership cannot be verified")


def _canonical_payload(plan: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(plan)
    payload.pop("planSha256", None)
    return payload


def canonical_plan_sha256(plan: dict[str, Any]) -> str:
    """Return the stable digest callers must pass back at apply time."""
    encoded = json.dumps(_canonical_payload(plan), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return _sha_bytes(encoded)


def _json_load(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ApplyError(f"unreadable JSON input: {path}") from exc
    if not isinstance(value, dict):
        raise ApplyError(f"JSON input must be an object: {path}")
    return value


def _verify_backup(path: Path, expected: Path, kind: str) -> None:
    path_stat, expected_stat = _backup_stats(path, expected)
    _verify_backup_identity(path, expected, path_stat, expected_stat)
    _verify_backup_content(path, expected, kind)


def _backup_stats(path: Path, expected: Path) -> tuple[os.stat_result, os.stat_result]:
    try:
        path_stat = path.lstat()
        expected_stat = expected.stat()
    except OSError as exc:
        raise ApplyError(f"backup is missing or unreadable: {path}") from exc
    return path_stat, expected_stat


def _verify_backup_identity(path: Path, expected: Path, path_stat: os.stat_result, expected_stat: os.stat_result) -> None:
    if not path_stat or not path_stat.st_mode or not path.is_file() or path.is_symlink():
        raise ApplyError(f"backup is not a regular independent file: {path}")
    if path.resolve() == expected.resolve() or path_stat.st_ino == expected_stat.st_ino:
        raise ApplyError(f"backup aliases target: {path}")
    if path_stat.st_nlink != 1:
        raise ApplyError(f"backup must have one independent link: {path}")


def _verify_backup_content(path: Path, expected: Path, kind: str) -> None:
    try:
        backup_bytes = path.read_bytes()
    except OSError as exc:
        raise ApplyError(f"backup is missing or unreadable: {path}") from exc
    if _sha_bytes(backup_bytes) != _sha(expected):
        raise ApplyError(f"backup does not match current {kind} input")
    if kind == "sqlite":
        _verify_sqlite_backup(path)
    else:
        _json_load(path)


def _verify_sqlite_backup(path: Path) -> None:
    try:
        with sqlite3.connect(path) as conn:
            result = conn.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error as exc:
        raise ApplyError("SQLite backup is unreadable") from exc
    if not result or result[0] != "ok":
        raise ApplyError("SQLite backup failed integrity check")


def _reject_live_paths(sqlite_path: Path, json_path: Path, allow_live: bool) -> None:
    root = Path(__file__).resolve().parents[2]
    live = {(root / "agent/data/vinhlong360.db").resolve(), (root / "web/data.json").resolve()}
    if (sqlite_path.resolve() in live or json_path.resolve() in live) and not allow_live:
        raise ApplyError("live protected inputs require --allow-live-protected-inputs")


def _default_artifact_path(sqlite_path: Path, suffix: str) -> Path:
    """Keep fixture journals beside their inputs so journal scope is enforced."""
    return sqlite_path.with_name(f"{sqlite_path.name}.reconciliation{suffix}")


def _journal_identity(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {"device": stat.st_dev, "inode": stat.st_ino, "size": stat.st_size}


def _entity_row(conn: sqlite3.Connection, record_id: str) -> sqlite3.Row:
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT rowid, * FROM entities WHERE id = ?", (record_id,)).fetchone()
    if row is None:
        raise ApplyError(f"entity not found: {record_id}")
    return row


def _sqlite_mutation(conn: sqlite3.Connection, mutation: dict[str, Any]) -> None:
    if mutation.get("recordType") == "relationship":
        _relationship_mutation(conn, mutation)
        return
    if mutation.get("recordType") != "entity":
        raise ApplyError(f"unsupported mutation record type: {mutation.get('recordType')}")
    if mutation.get("operation") == "delete":
        _delete_sqlite_entity(conn, mutation)
        return
    if mutation.get("operation") in {"update", "remove"}:
        _update_sqlite_entity(conn, mutation)
        return
    raise ApplyError(f"unsupported entity mutation: {mutation.get('mutationId')}")


def _sqlite_entity_projection(row: sqlite3.Row) -> dict[str, Any]:
    projection = {key: row[key] for key in row.keys() if key != "rowid"}
    for field in ("attributes", "images", "coordinates"):
        if isinstance(projection.get(field), str):
            try:
                projection[field] = json.loads(projection[field])
            except json.JSONDecodeError as exc:
                raise ApplyError(f"malformed entity field: {field}") from exc
    return projection


def _delete_sqlite_entity(conn: sqlite3.Connection, mutation: dict[str, Any]) -> None:
    row = _entity_row(conn, mutation["recordId"])
    if _sqlite_entity_projection(row) != mutation.get("before"):
        raise ApplyError(f"entity before value mismatch: {mutation.get('mutationId')}")
    changed = conn.execute("DELETE FROM entities WHERE id = ?", (mutation["recordId"],)).rowcount
    if changed != 1:
        raise ApplyError(f"entity row missing: {mutation['recordId']}")


def _update_sqlite_entity(conn: sqlite3.Connection, mutation: dict[str, Any]) -> None:
    update_kind, field, record_id, value = _prepare_entity_update(conn, mutation)
    if update_kind == "attributes":
        changed = conn.execute("UPDATE entities SET attributes = ? WHERE id = ?", (value, record_id)).rowcount
    else:
        changed = conn.execute(f'UPDATE entities SET "{field}" = ? WHERE id = ?', (value, record_id)).rowcount
    if changed != 1:
        raise ApplyError(f"entity row missing: {record_id}")


def _relationship_mutation(conn: sqlite3.Connection, mutation: dict[str, Any]) -> None:
    if mutation.get("operation") == "insert":
        _insert_relationship(conn, mutation)
        return
    rowid = (mutation.get("metadata") or {}).get("rowid")
    if not isinstance(rowid, int):
        raise ApplyError(f"relationship rowid missing: {mutation.get('mutationId')}")
    current = conn.execute("SELECT from_id, to_id, type FROM relationships WHERE rowid = ?", (rowid,)).fetchone()
    if current is None:
        raise ApplyError(f"relationship row missing: {mutation.get('mutationId')}")
    changed = _update_or_delete_relationship(conn, mutation, rowid, current)
    if changed != 1:
        raise ApplyError(f"relationship row missing: {mutation.get('mutationId')}")


def _insert_relationship(conn: sqlite3.Connection, mutation: dict[str, Any]) -> None:
    value = mutation.get("after")
    if not isinstance(value, dict):
        raise ApplyError(f"relationship insert value missing: {mutation.get('mutationId')}")
    source, target = value.get("from", value.get("from_id")), value.get("to", value.get("to_id"))
    relationship_type = value.get("type")
    values = (source, target, relationship_type)
    if not all(isinstance(item, str) and item.strip() for item in values):
        raise ApplyError(f"relationship insert value invalid: {mutation.get('mutationId')}")
    duplicate = conn.execute(
        "SELECT 1 FROM relationships WHERE from_id = ? AND to_id = ? AND type = ? LIMIT 1", values
    ).fetchone()
    if duplicate is not None:
        raise ApplyError(f"duplicate relationship triple: {mutation.get('mutationId')}")
    conn.execute("INSERT INTO relationships (from_id, to_id, type) VALUES (?, ?, ?)", values)


def _update_or_delete_relationship(conn: sqlite3.Connection, mutation: dict[str, Any], rowid: int, current: sqlite3.Row) -> int:
    operation = mutation.get("operation")
    if operation == "update" and mutation.get("field") == "type":
        if current[2] != _required_mutation_value(mutation, "before"):
            raise ApplyError(f"relationship before value mismatch: {mutation.get('mutationId')}")
        after = _required_mutation_value(mutation, "after")
        return conn.execute("UPDATE relationships SET type = ? WHERE rowid = ?", (after, rowid)).rowcount
    if operation == "delete":
        current_tuple = {"from": current[0], "to": current[1], "type": current[2]}
        if current_tuple != _required_mutation_value(mutation, "before"):
            raise ApplyError(f"relationship before value mismatch: {mutation.get('mutationId')}")
        return conn.execute("DELETE FROM relationships WHERE rowid = ?", (rowid,)).rowcount
    raise ApplyError(f"unsupported relationship mutation: {mutation.get('mutationId')}")


def _prepare_entity_update(conn: sqlite3.Connection, mutation: dict[str, Any]) -> tuple[str, str, str, Any]:
    record_id = mutation["recordId"]
    field = mutation["field"]
    row = _entity_row(conn, record_id)
    if field.startswith("attributes."):
        return "attributes", field, record_id, _prepare_attribute_update(row, mutation, record_id)
    if field not in row.keys() or field == "id":
        raise ApplyError(f"unsupported entity field: {field}")
    current_value = row[field]
    if field in {"images", "coordinates"} and current_value is not None:
        try:
            current_value = json.loads(current_value)
        except json.JSONDecodeError as exc:
            raise ApplyError(f"malformed entity field: {field}") from exc
    if current_value != _required_mutation_value(mutation, "before"):
        raise ApplyError(f"entity before value mismatch: {mutation.get('mutationId')}")
    if mutation.get("operation") == "remove":
        raise ApplyError(f"remove requires a nested entity field: {mutation.get('mutationId')}")
    value = _required_mutation_value(mutation, "after")
    if field in {"images", "coordinates", "season"} and not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False) if value is not None else None
    return "dynamic", field, record_id, value


def _prepare_attribute_update(row: sqlite3.Row, mutation: dict[str, Any], record_id: str) -> str:
    try:
        attributes = json.loads(row["attributes"] or "{}")
    except json.JSONDecodeError as exc:
        raise ApplyError(f"malformed entity attributes: {record_id}") from exc
    attribute_name = mutation["field"].removeprefix("attributes.")
    if attribute_name not in attributes or attributes[attribute_name] != _required_mutation_value(mutation, "before"):
        raise ApplyError(f"entity before value mismatch: {mutation.get('mutationId')}")
    if mutation.get("operation") == "remove":
        del attributes[attribute_name]
    else:
        attributes[attribute_name] = _required_mutation_value(mutation, "after")
    return json.dumps(attributes, ensure_ascii=False)


def _required_mutation_value(mutation: dict[str, Any], key: str) -> Any:
    if key not in mutation:
        raise ApplyError(f"mutation {key} is required: {mutation.get('mutationId')}")
    return mutation[key]


def _json_mutation(payload: dict[str, Any], mutation: dict[str, Any]) -> None:
    if mutation.get("recordType") == "entity":
        _json_entity_mutation(payload, mutation)
        return
    if mutation.get("recordType") != "relationship" or mutation.get("field") != "relationship":
        raise ApplyError(f"unsupported JSON mutation: {mutation.get('mutationId')}")
    relationships = payload.get("relationships")
    if not isinstance(relationships, list):
        raise ApplyError("JSON relationships must be a list")
    index = (mutation.get("metadata") or {}).get("index")
    if not isinstance(index, int) or index < 0 or index >= len(relationships):
        raise ApplyError(f"JSON relationship index missing: {mutation.get('mutationId')}")
    if relationships[index] != _required_mutation_value(mutation, "before"):
        raise ApplyError(f"JSON before value mismatch: {mutation.get('mutationId')}")
    if mutation.get("operation") == "delete":
        relationships.pop(index)
    elif mutation.get("operation") == "update":
        relationships[index] = _required_mutation_value(mutation, "after")
    else:
        raise ApplyError(f"unsupported JSON operation: {mutation.get('operation')}")


def _json_entity_mutation(payload: dict[str, Any], mutation: dict[str, Any]) -> None:
    entities = payload.get("entities")
    index = (mutation.get("metadata") or {}).get("index")
    if not isinstance(entities, list) or not isinstance(index, int) or index < 0 or index >= len(entities):
        raise ApplyError(f"JSON entity index missing: {mutation.get('mutationId')}")
    entity = entities[index]
    _assert_json_entity_target(entity, mutation)
    if mutation.get("operation") == "delete":
        _assert_json_before(entity, mutation)
        entities.pop(index)
        return
    field = mutation.get("field")
    if not isinstance(field, str) or field == "id":
        raise ApplyError(f"unsupported JSON entity field: {field}")
    if field.startswith("attributes."):
        _json_nested_entity_mutation(entity, field, mutation)
        return

    _json_top_level_entity_mutation(entity, field, mutation)


def _json_nested_entity_mutation(entity: dict[str, Any], field: str, mutation: dict[str, Any]) -> None:
    attributes = entity.get("attributes")
    name = field.removeprefix("attributes.")
    if not isinstance(attributes, dict) or name not in attributes:
        raise ApplyError(f"JSON before value mismatch: {mutation.get('mutationId')}")
    _assert_json_before(attributes[name], mutation)
    _mutate_json_attribute(attributes, name, mutation)


def _json_top_level_entity_mutation(entity: dict[str, Any], field: str, mutation: dict[str, Any]) -> None:
    if field not in entity:
        raise ApplyError(f"JSON before value mismatch: {mutation.get('mutationId')}")
    _assert_json_before(entity[field], mutation)
    if mutation.get("operation") == "remove":
        raise ApplyError(f"remove requires a nested entity field: {mutation.get('mutationId')}")
    if mutation.get("operation") != "update":
        raise ApplyError(f"unsupported JSON operation: {mutation.get('operation')}")
    entity[field] = _required_mutation_value(mutation, "after")


def _assert_json_before(current: Any, mutation: dict[str, Any]) -> None:
    if current != _required_mutation_value(mutation, "before"):
        raise ApplyError(f"JSON before value mismatch: {mutation.get('mutationId')}")


def _assert_json_entity_target(entity: Any, mutation: dict[str, Any]) -> None:
    if not isinstance(entity, dict) or entity.get("id") != mutation.get("recordId"):
        raise ApplyError(f"JSON entity ID mismatch: {mutation.get('mutationId')}")


def _mutate_json_attribute(attributes: dict[str, Any], name: str, mutation: dict[str, Any]) -> None:
    if mutation.get("operation") == "remove":
        del attributes[name]
        return
    if mutation.get("operation") == "update":
        attributes[name] = _required_mutation_value(mutation, "after")
        return
    raise ApplyError(f"unsupported JSON operation: {mutation.get('operation')}")


def _parity(sqlite_path: Path, json_path: Path, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Verify the stores agree on IDs and relationship triples after apply."""
    payload = _json_load(json_path)
    entities, relationship_rows = _sqlite_parity_data(sqlite_path, connection)
    _, json_entity_rows, entities_shape_valid, json_entities = _json_entity_data(payload)
    _, json_relationship_rows, relationships_shape_valid = _json_relationship_data(payload)
    sqlite_counter = Counter(relationship_rows)
    json_counter = Counter(json_relationship_rows)
    sqlite_invalid = sum(1 for source, target, _ in relationship_rows if source not in entities or target not in entities)
    json_invalid = sum(1 for source, target, _ in json_relationship_rows if source not in json_entities or target not in json_entities)
    sqlite_duplicates = sum(count - 1 for count in sqlite_counter.values() if count > 1)
    json_duplicates = sum(count - 1 for count in json_counter.values() if count > 1)
    status = _parity_status(
        entities, json_entities, entities_shape_valid, relationships_shape_valid,
        json_entity_rows, relationship_rows, json_relationship_rows,
        sqlite_counter, json_counter, sqlite_duplicates, json_duplicates,
        sqlite_invalid, json_invalid,
    )
    return {
        "status": status,
        "entityIds": {"sqlite": len(entities), "json": len(json_entities)},
        "entityRows": {"sqlite": len(entities), "json": len(json_entity_rows)},
        "relationships": {"sqlite": len(relationship_rows), "json": len(json_relationship_rows)},
        "duplicateTriples": {"sqlite": sqlite_duplicates, "json": json_duplicates},
        "invalidEndpoints": {"sqlite": sqlite_invalid, "json": json_invalid},
    }


def _sqlite_parity_data(sqlite_path: Path, connection: sqlite3.Connection | None) -> tuple[set[str], list[tuple[Any, ...]]]:
    if connection is None:
        with sqlite3.connect(sqlite_path) as conn:
            return _sqlite_parity_data(sqlite_path, conn)
    entities = {row[0] for row in connection.execute("SELECT id FROM entities")}
    relationships = [tuple(row) for row in connection.execute("SELECT from_id, to_id, type FROM relationships")]
    return entities, relationships


def _json_entity_data(payload: dict[str, Any]) -> tuple[Any, list[Any], bool, set[str]]:
    value = payload.get("entities")
    rows = value if isinstance(value, list) else []
    shape_valid = isinstance(value, list) and all(
        isinstance(item, dict) and isinstance(item.get("id"), str) and bool(item["id"].strip())
        for item in rows
    )
    entities = {item["id"] for item in rows if isinstance(item, dict) and isinstance(item.get("id"), str)}
    return value, rows, shape_valid, entities


def _json_relationship_data(payload: dict[str, Any]) -> tuple[Any, list[tuple[str, str, str]], bool]:
    value = payload.get("relationships")
    rows = value if isinstance(value, list) else []
    shape_valid = isinstance(value, list) and all(
        isinstance(item, dict)
        and all(isinstance(item.get(key), str) and bool(item[key].strip()) for key in ("from", "to", "type"))
        for item in rows
    )
    triples = [
        (item["from"], item["to"], item["type"])
        for item in rows
        if isinstance(item, dict) and all(isinstance(item.get(key), str) for key in ("from", "to", "type"))
    ]
    return value, triples, shape_valid


def _parity_status(
    entities: set[str], json_entities: set[str], entities_shape_valid: bool,
    relationships_shape_valid: bool, json_entity_rows: list[Any],
    relationship_rows: list[tuple[Any, ...]], json_relationship_rows: list[tuple[str, str, str]],
    sqlite_counter: Counter, json_counter: Counter, sqlite_duplicates: int,
    json_duplicates: int, sqlite_invalid: int, json_invalid: int,
) -> str:
    checks = (
        entities == json_entities,
        entities_shape_valid,
        relationships_shape_valid,
        len(entities) == len(json_entity_rows),
        len(relationship_rows) == len(json_relationship_rows),
        sqlite_counter == json_counter,
        sqlite_duplicates == 0,
        json_duplicates == 0,
        sqlite_invalid == 0,
        json_invalid == 0,
    )
    return "clean" if all(checks) else "drift"


def _digest_rows(rows: list[Any]) -> str:
    encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return _sha_bytes(encoded)


def _targeted_media_verification(
    plan: dict[str, Any], sqlite_path: Path, json_path: Path, connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    verification = plan.get("verification") or {}
    targets = _targeted_targets(verification)
    payload = _json_load(json_path)
    if connection is None:
        with sqlite3.connect(sqlite_path) as conn:
            return _targeted_media_verification(plan, sqlite_path, json_path, conn)
    connection.row_factory = sqlite3.Row
    sqlite_rows = {row["id"]: _sqlite_entity_projection(row) for row in connection.execute("SELECT rowid, * FROM entities")}
    json_rows = {row.get("id"): row for row in payload.get("entities", []) if isinstance(row, dict) and row.get("id")}
    target_ids = set(targets)
    _verify_target_projections(targets, sqlite_rows, json_rows)
    sqlite_relationships, json_relationships = _relationship_rows(connection, payload)
    _verify_unrelated_digests(verification, target_ids, sqlite_rows, json_rows, sqlite_relationships, json_relationships)
    return {"mode": "targeted-media-v1", "status": "clean", "globalParity": "known-drift-preserved"}


def _targeted_targets(verification: dict[str, Any]) -> dict[str, Any]:
    targets = verification.get("targets") or verification.get("expectedProjections") or {}
    if isinstance(targets, list):
        targets = {item.get("id"): item for item in targets if isinstance(item, dict) and item.get("id")}
    if not isinstance(targets, dict):
        raise ApplyError("targeted verification targets must be an object")
    return targets


def _verify_unrelated_digests(verification: dict[str, Any], target_ids: set[str], sqlite_rows: dict[str, Any], json_rows: dict[str, Any], sqlite_relationships: list[Any], json_relationships: list[Any]) -> None:
    unrelated = verification.get("unrelatedDigests") or verification.get("nonTargetDigests") or {}
    if not isinstance(unrelated, dict):
        raise ApplyError("targeted unrelated digests are required")
    for store_name, entities, relationships in (("sqlite", sqlite_rows, sqlite_relationships), ("json", json_rows, json_relationships)):
        expected = unrelated.get(store_name)
        if not isinstance(expected, dict):
            raise ApplyError(f"targeted unrelated digests missing: {store_name}")
        before = _validate_digest_bundle(expected.get("before"), store_name, "before")
        after = _validate_digest_bundle(expected.get("after"), store_name, "after")
        if before != after:
            raise ApplyError(f"targeted unrelated digest changed: {store_name}")
        entity_rows = [value for key, value in sorted(entities.items()) if key not in target_ids and key != "prov-1"]
        relation_rows = [row for row in relationships if row[0] not in target_ids and row[1] not in target_ids]
        actual = {"entities": _digest_rows(entity_rows), "relationships": _digest_rows(relation_rows)}
        _assert_digest_match(actual, after, store_name)


def _validate_digest_bundle(value: Any, store_name: str, phase: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"entities", "relationships"}:
        raise ApplyError(f"targeted unrelated {phase} digests incomplete: {store_name}")
    if not all(isinstance(value[key], str) and len(value[key]) == 64 for key in value):
        raise ApplyError(f"targeted unrelated {phase} digests invalid: {store_name}")
    return {key: value[key] for key in ("entities", "relationships")}


def _assert_digest_match(actual: dict[str, str], expected: Any, store_name: str) -> None:
    if any(actual[key] != expected[key] for key in actual):
        raise ApplyError(f"targeted unrelated digest mismatch: {store_name}")


def _verify_target_projections(targets: dict[str, Any], sqlite_rows: dict[str, Any], json_rows: dict[str, Any]) -> None:
    if "prov-1" in sqlite_rows or "prov-1" in json_rows:
        raise ApplyError("targeted media verification requires prov-1 absence")
    for record_id, expected in targets.items():
        expected_sqlite = expected.get("sqlite", expected) if isinstance(expected, dict) else expected
        expected_json = expected.get("json", expected) if isinstance(expected, dict) else expected
        if sqlite_rows.get(record_id) != expected_sqlite or json_rows.get(record_id) != expected_json:
            raise ApplyError(f"targeted entity projection mismatch: {record_id}")


def _relationship_rows(connection: sqlite3.Connection, payload: dict[str, Any]) -> tuple[list[Any], list[Any]]:
    sqlite_rows = [tuple(row) for row in connection.execute("SELECT from_id, to_id, type FROM relationships")]
    json_rows = [(item.get("from"), item.get("to"), item.get("type")) for item in payload.get("relationships", []) if isinstance(item, dict)]
    if any("prov-1" in edge[:2] for edge in sqlite_rows + json_rows):
        raise ApplyError("targeted media verification found prov-1 relationship endpoint")
    return sqlite_rows, json_rows


def verify_plan_result(
    plan: dict[str, Any], sqlite_path: Path, json_path: Path, connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    mode = ((plan.get("verification") or {}).get("mode"))
    if mode in {None, "global-parity-v1"}:
        return {"mode": "global-parity-v1", **_parity(sqlite_path, json_path, connection)}
    if mode == "targeted-media-v1":
        return _targeted_media_verification(plan, sqlite_path, json_path, connection)
    raise ApplyError(f"unsupported verification mode: {mode}")


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _validate_apply_request(
    plan: dict[str, Any], sqlite_path: Path, json_path: Path, sqlite_backup: Path, json_backup: Path,
    *, confirm: bool, plan_sha256: str | None, accept_deferred: bool, accept_deferred_items: bool | None,
    allow_live: bool, maintenance_mode: bool, lock_path: Path | None, journal_path: Path | None,
) -> tuple[Path, Path]:
    if not confirm:
        raise ApplyError("--confirm-phase-b is required")
    if plan.get("status") != "approved":
        raise ApplyError("plan status must be approved")
    if not plan.get("reviewedPlanMarker"):
        raise ApplyError("reviewed plan marker is required")
    if plan_sha256 != canonical_plan_sha256(plan) or (plan.get("planSha256") and plan["planSha256"] != plan_sha256):
        raise ApplyError("plan hash mismatch")
    if accept_deferred_items is not None:
        accept_deferred = accept_deferred_items
    if plan.get("deferred") and not accept_deferred:
        raise ApplyError("deferred items require explicit acceptance")
    selected_lock = Path(lock_path) if lock_path is not None else _default_artifact_path(sqlite_path, ".lock")
    selected_journal = Path(journal_path) if journal_path is not None else _default_artifact_path(sqlite_path, ".journal.json")
    return selected_lock, selected_journal


def _verify_apply_inputs(
    plan: dict[str, Any], sqlite_path: Path, json_path: Path, sqlite_backup: Path, json_backup: Path,
    *, allow_live: bool, maintenance_mode: bool,
) -> tuple[str, str]:
    _reject_live_paths(sqlite_path, json_path, allow_live and maintenance_mode)
    try:
        expected_sqlite = plan["inputs"]["sqlite"]["sha256"]
        expected_json = plan["inputs"]["json"]["sha256"]
    except (KeyError, TypeError) as exc:
        raise ApplyError("plan input hashes are required") from exc
    if _sha(sqlite_path) != expected_sqlite or _sha(json_path) != expected_json:
        raise ApplyError("stale input hash")
    _verify_backup(sqlite_backup, sqlite_path, "sqlite")
    _verify_backup(json_backup, json_path, "json")
    return expected_sqlite, expected_json


def _prepare_mutations(plan: dict[str, Any], json_path: Path) -> tuple[bytes, tuple[int, int, int, int], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    original_json = json_path.read_bytes()
    original_identity = _file_identity(json_path)
    payload = _json_load(json_path)
    mutations, json_mutations, sqlite_mutations = _validated_mutations(plan)
    _apply_json_mutations(payload, json_mutations)
    return original_json, original_identity, payload, sqlite_mutations, mutations


def _validated_mutations(plan: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    mutations = plan.get("mutations", [])
    if not isinstance(mutations, list) or not all(isinstance(item, dict) for item in mutations):
        raise ApplyError("mutations must be a list of objects")
    json_mutations = [item for item in mutations if item.get("store") == "json"]
    index_keys = [
        (item.get("recordType"), (item.get("metadata") or {}).get("index"))
        for item in json_mutations
    ]
    if len(index_keys) != len(set(index_keys)):
        raise ApplyError("conflicting JSON mutation index")
    sqlite_mutations = [item for item in mutations if item.get("store") == "sqlite"]
    unknown = [item for item in mutations if item.get("store") not in {"sqlite", "json"}]
    if unknown:
        raise ApplyError(f"unknown mutation store: {unknown[0].get('store')}")
    return mutations, json_mutations, sqlite_mutations


def _apply_json_mutations(payload: dict[str, Any], json_mutations: list[dict[str, Any]]) -> None:
    grouped: dict[Any, list[dict[str, Any]]] = {}
    for mutation in json_mutations:
        grouped.setdefault(mutation.get("recordType"), []).append(mutation)
    for group in grouped.values():
        for mutation in sorted(group, key=lambda item: (item.get("metadata") or {}).get("index", -1), reverse=True):
            _json_mutation(payload, mutation)


def _stage_apply_journal(
    payload: dict[str, Any], journal_path: Path, operation_id: str, plan_sha256: str,
    sqlite_path: Path, json_path: Path, sqlite_backup: Path, json_backup: Path,
    expected_sqlite: str, expected_json: str, verification_mode: str = "global-parity-v1",
) -> tuple[Path, dict[str, Any]]:
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    temp_json: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=json_path.parent, delete=False) as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            temp_json = Path(handle.name)
        state = {
            "schemaVersion": 1, "operationId": operation_id, "phase": "prepared", "planSha256": plan_sha256,
            "verificationMode": verification_mode,
            "sqlite": {"path": str(sqlite_path), "beforeSha256": expected_sqlite, "backupPath": str(sqlite_backup),
                        "backupSha256": _sha(sqlite_backup), "beforeIdentity": _journal_identity(sqlite_path)},
             "json": {"path": str(json_path), "beforeSha256": expected_json, "backupPath": str(json_backup),
                      "backupSha256": _sha(json_backup), "candidatePath": str(temp_json),
                      "candidateSha256": _sha(temp_json), "beforeIdentity": _journal_identity(json_path)},
        }
        write_journal(journal_path, state)
        return temp_json, state
    except (JournalError, OSError, TypeError, ValueError):
        if temp_json is not None:
            temp_json.unlink(missing_ok=True)
        raise


def _execute_apply_transaction(
    plan: dict[str, Any], sqlite_path: Path, json_path: Path, temp_json: Path, journal_path: Path, state: dict[str, Any],
    sqlite_mutations: list[dict[str, Any]], mutations: list[dict[str, Any]],
    expected_sqlite: str, expected_json: str, original_json: bytes, original_identity: tuple[int, int, int, int],
) -> dict[str, Any]:
    connection: sqlite3.Connection | None = None
    transaction_active = False
    try:
        connection = sqlite3.connect(sqlite_path)
        connection.execute("BEGIN")
        transaction_active = True
        if _sha(sqlite_path) != expected_sqlite or _sha(json_path) != expected_json:
            raise ApplyError("stale input hash")
        for mutation in sqlite_mutations:
            _sqlite_mutation(connection, mutation)
        parity = verify_plan_result(plan, sqlite_path, temp_json, connection)
        if parity["status"] != "clean":
            raise ApplyError("post-apply parity verification failed")
        connection.commit()
        transaction_active = False
        state["phase"] = "sqlite_committed"
        write_journal(journal_path, state)
        capture_path = _unique_json_artifact(json_path, "capture")
        state["json"]["capturedPath"] = str(capture_path)
        state["json"]["capturedSha256"] = expected_json
        write_journal(journal_path, state)
        _capture_json_target(json_path, capture_path, expected_json, original_identity)
        published_identity = _publish_json_no_overwrite(temp_json, json_path)
        state["json"]["publishedIdentity"] = {
            "device": published_identity[0], "inode": published_identity[1], "size": published_identity[2]
        }
        state["json"]["publishedSha256"] = state["json"]["candidateSha256"]
        state["phase"] = "json_published"
        write_journal(journal_path, state)
        final_parity = verify_plan_result(plan, sqlite_path, json_path)
        if final_parity["status"] != "clean":
            raise ApplyError("post-apply parity verification failed")
        if _sha(json_path) != state["json"]["publishedSha256"]:
            raise ApplyError("published JSON changed during final verification")
        published = state["json"]["publishedIdentity"]
        if _file_identity(json_path)[:3] != (published["device"], published["inode"], published["size"]):
            raise ApplyError("published JSON identity changed during final verification")
        if _sha(capture_path) != expected_json:
            raise ApplyError("captured JSON changed during final verification")
        for suffix in ("-wal", "-shm", "-journal"):
            if sqlite_path.with_name(sqlite_path.name + suffix).exists():
                raise ApplyError(f"SQLite sidecar appeared during final verification: {suffix}")
        state["phase"] = "complete"
        write_journal(journal_path, state)
        # Recheck after the durable completion record; a sidecar can appear
        # between the pre-journal check and this crash boundary.
        for suffix in ("-wal", "-shm", "-journal"):
            if sqlite_path.with_name(sqlite_path.name + suffix).exists():
                raise ApplyError(f"SQLite sidecar appeared after final journal: {suffix}")
        capture_path.unlink()
        temp_json.unlink(missing_ok=True)
        journal_path.unlink()
        _fsync_directory(journal_path.parent)
        return {
            "status": "applied",
            "verification": final_parity,
            "parity": final_parity,
            "mutationCount": len(mutations),
        }
    except (ApplyError, OSError, sqlite3.Error, json.JSONDecodeError) as exc:
        if connection is not None and transaction_active:
            connection.rollback()
        if isinstance(exc, ApplyError):
            raise
        raise ApplyError(str(exc)) from exc
    finally:
        if connection is not None:
            connection.close()


def _apply_plan_impl(
    plan: dict[str, Any],
    sqlite_path: Path,
    json_path: Path,
    sqlite_backup: Path,
    json_backup: Path,
    *,
    confirm: bool = False,
    plan_sha256: str | None = None,
    accept_deferred: bool = False,
    accept_deferred_items: bool | None = None,
    allow_live: bool = False,
    lock_path: Path | None = None,
    journal_path: Path | None = None,
    maintenance_mode: bool = False,
) -> dict[str, Any]:
    sqlite_path, json_path = Path(sqlite_path), Path(json_path)
    sqlite_backup, json_backup = Path(sqlite_backup), Path(json_backup)
    lock_path, journal_path = _validate_apply_request(
        plan, sqlite_path, json_path, sqlite_backup, json_backup, confirm=confirm,
        plan_sha256=plan_sha256, accept_deferred=accept_deferred,
        accept_deferred_items=accept_deferred_items, allow_live=allow_live,
        maintenance_mode=maintenance_mode, lock_path=lock_path, journal_path=journal_path,
    )
    operation_id = uuid.uuid4().hex
    metadata = {
        "operationId": operation_id,
        "journalPath": str(journal_path),
        "targetPaths": [str(sqlite_path), str(json_path)],
    }
    lock = ReconciliationLock(lock_path, metadata)
    try:
        lock.__enter__()
        expected_sqlite, expected_json = _verify_apply_inputs(
            plan, sqlite_path, json_path, sqlite_backup, json_backup,
            allow_live=allow_live, maintenance_mode=maintenance_mode,
        )
        if journal_path.exists():
            raise ApplyError(f"existing reconciliation journal requires recovery: {journal_path}")
        original_json, original_identity, payload, sqlite_mutations, mutations = _prepare_mutations(plan, json_path)
        temp_json, state = _stage_apply_journal(
            payload, journal_path, operation_id, plan_sha256, sqlite_path, json_path,
            sqlite_backup, json_backup, expected_sqlite, expected_json,
            ((plan.get("verification") or {}).get("mode") or "global-parity-v1"),
        )
        try:
            return _execute_apply_transaction(
                plan, sqlite_path, json_path, temp_json, journal_path, state, sqlite_mutations, mutations,
                expected_sqlite, expected_json, original_json, original_identity,
            )
        finally:
            # Keep candidate/capture artifacts while a journal is recoverable.
            # Removing them here would turn a failed transaction into a
            # non-recoverable journal.
            if not journal_path.exists():
                temp_json.unlink(missing_ok=True)
    except (LockBusyError, LockPathError, JournalError) as exc:
        raise ApplyError(str(exc)) from exc
    finally:
        lock.__exit__(None, None, None)


def recover_interrupted_apply(
    journal_path: Path,
    lock_path: Path,
    *,
    allow_live: bool = False,
) -> dict[str, Any]:
    """Explicitly roll an interrupted apply back to its journaled snapshot."""
    journal_path, lock_path = Path(journal_path), Path(lock_path)
    metadata = {"operationId": uuid.uuid4().hex, "journalPath": str(journal_path)}
    try:
        with ReconciliationLock(lock_path, metadata) as lock:
            state = load_journal(journal_path)
            sqlite_path = Path(state["sqlite"]["path"])
            json_path = Path(state["json"]["path"])
            _reject_live_paths(sqlite_path, json_path, allow_live)
            return recover_journal(state, lock)
    except (LockBusyError, LockPathError, JournalError, KeyError, OSError, ApplyError) as exc:
        if isinstance(exc, ApplyError):
            raise
        raise ApplyError(str(exc)) from exc


def apply_plan(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Apply a plan and normalize malformed input into a controlled refusal."""
    try:
        return _apply_plan_impl(*args, **kwargs)
    except ApplyError:
        raise
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError, sqlite3.Error, OSError) as exc:
        raise ApplyError(f"malformed apply request: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--sqlite", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--sqlite-backup", type=Path)
    parser.add_argument("--json-backup", type=Path)
    parser.add_argument("--plan-sha256")
    parser.add_argument("--lock-path", type=Path)
    parser.add_argument("--journal-path", type=Path)
    parser.add_argument("--maintenance-window", action="store_true")
    parser.add_argument("--recover-phase-b-journal", action="store_true")
    parser.add_argument("--confirm-phase-b", action="store_true")
    parser.add_argument("--accept-deferred", "--accept-deferred-items", dest="accept_deferred", action="store_true")
    parser.add_argument("--allow-live-protected-inputs", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.recover_phase_b_journal:
            if args.journal_path is None or args.lock_path is None:
                raise ApplyError("--journal-path and --lock-path are required for recovery")
            recover_interrupted_apply(args.journal_path, args.lock_path, allow_live=args.allow_live_protected_inputs)
            return 0
        required = {
            "--plan": args.plan,
            "--sqlite": args.sqlite,
            "--json": args.json_path,
            "--sqlite-backup": args.sqlite_backup,
            "--json-backup": args.json_backup,
            "--plan-sha256": args.plan_sha256,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise ApplyError(f"missing required arguments: {', '.join(missing)}")
        plan = _json_load(args.plan)
        apply_plan(
            plan,
            args.sqlite,
            args.json_path,
            args.sqlite_backup,
            args.json_backup,
            confirm=args.confirm_phase_b,
            plan_sha256=args.plan_sha256,
            accept_deferred=args.accept_deferred,
            allow_live=args.allow_live_protected_inputs,
            lock_path=args.lock_path,
            journal_path=args.journal_path,
            maintenance_mode=args.maintenance_window,
        )
    except (ApplyError, OSError, TypeError, KeyError, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(f"apply refused: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
