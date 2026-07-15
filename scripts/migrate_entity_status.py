"""Generate an immutable PostgreSQL publication migration plan."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT / "agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from publication_status import (  # noqa: E402
    PUBLICATION_POLICY_REVISION,
    PUBLISHED_V1_EXCLUSIONS,
    decide_publication_candidate,
)

if __package__:
    from .postgres_target import (  # noqa: E402
        canonical_json_bytes,
        read_target_identity,
        resolve_database_url,
        sha256_file,
        sha256_bytes,
        target_fingerprint,
        write_exclusive,
    )
else:
    from postgres_target import (  # noqa: E402
        canonical_json_bytes,
        read_target_identity,
        resolve_database_url,
        sha256_file,
        sha256_bytes,
        target_fingerprint,
        write_exclusive,
    )


PLAN_SCHEMA = "vinhlong360-entity-status-plan-v1"
APPLY_SCHEMA = "vinhlong360-entity-status-apply-v1"
ROLLBACK_SCHEMA = "vinhlong360-entity-status-rollback-v1"
MAX_PLAN_AGE_SECONDS = 86400
MAX_BACKUP_AGE_SECONDS = 3600
LOCK_NAME = "vinhlong360:entity-status:published-v1"
REQUIRED_ENTITY_COLUMNS = {
    "id",
    "type",
    "status",
    "verified",
    "attributes",
    "source",
}


class MigrationRefusal(RuntimeError):
    """Refuse unsafe or non-canonical migration planning input."""


@dataclass(frozen=True)
class BackupEvidence:
    manifest: dict[str, object]
    manifest_sha256: str
    artifact_root: Path


def audit_actor(prefix: str, plan_sha256: str) -> str:
    if prefix not in {"apply", "rollback"} or not re.fullmatch(
        r"[0-9a-f]{64}", plan_sha256
    ):
        raise MigrationRefusal("audit actor inputs are invalid")
    return f"entity-status:{prefix}:{PUBLICATION_POLICY_REVISION}:{plan_sha256}"


def validate_schema_identifier(value: object) -> str:
    if (
        type(value) is not str
        or len(value) > 63
        or not re.fullmatch(r"[a-z_][a-z0-9_]*", value)
    ):
        raise MigrationRefusal("PostgreSQL schema identifier is invalid")
    return value


def parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        raise MigrationRefusal("invalid UTC timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MigrationRefusal("UTC timestamp requires a timezone")
    return parsed.astimezone(UTC)


def utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise MigrationRefusal("datetime requires a timezone")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def candidate_id_hash(ids) -> str:
    return sha256_bytes(canonical_json_bytes(ids))


def _normalized_schema_columns(columns) -> list[dict[str, object]]:
    return [
        {"name": name, "type": data_type, "nullable": nullable}
        for name, data_type, nullable in sorted(columns)
    ]


def schema_fingerprint(columns) -> str:
    return sha256_bytes(canonical_json_bytes(_normalized_schema_columns(columns)))


def write_immutable_json(path: Path, value: object) -> str:
    canonical_payload = canonical_json_bytes(value)
    digest = sha256_bytes(canonical_payload)
    write_exclusive(path, value)
    return digest


def load_immutable_json(path: Path) -> tuple[dict[str, object], str]:
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise MigrationRefusal("immutable JSON is not valid UTF-8") from None
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        raise MigrationRefusal("immutable JSON is invalid JSON") from None
    if type(value) is not dict:
        raise MigrationRefusal("immutable JSON root must be an object")
    return value, digest


_PLAN_KEYS = {
    "schema",
    "policy_revision",
    "created_at",
    "max_age_seconds",
    "tool_source_revision",
    "target_fingerprint",
    "database_identity",
    "schema_fingerprint",
    "schema_columns",
    "candidate_ids",
    "candidate_count",
    "candidate_sha256",
    "reviewed_exclusions",
    "exclusion_counts",
    "status_groups",
    "expected_before",
    "expected_after",
}
_BACKUP_KEYS = {
    "schema",
    "target",
    "target_fingerprint",
    "database_identity",
    "started_at",
    "completed_at",
    "max_age_seconds",
    "tools",
    "artifact",
    "validation",
    "policy_revision",
}


def _require_exact_keys(value: object, expected: set[str], label: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != expected:
        raise MigrationRefusal(f"{label} fields are malformed")
    return value


def _require_sha(value: object, label: str) -> str:
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise MigrationRefusal(f"{label} is invalid")
    return value


def _require_nonnegative_counts(value: object, label: str) -> dict[str, int]:
    counts = _require_exact_keys(value, {"published", "null"}, label)
    if any(type(item) is not int or item < 0 for item in counts.values()):
        raise MigrationRefusal(f"{label} are invalid")
    return {key: int(item) for key, item in counts.items()}


def _require_counter(value: object, label: str) -> dict[str, int]:
    if type(value) is not dict or any(
        type(key) is not str or type(item) is not int or item < 0
        for key, item in value.items()
    ):
        raise MigrationRefusal(f"{label} are invalid")
    return dict(value)


def _require_aware_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise MigrationRefusal(f"{label} requires a timezone")
    return value.astimezone(UTC)


def _validate_plan_header(
    plan: dict[str, object], plan_sha256: str, confirm_target: str, now: datetime
) -> str:
    if plan.get("schema") != PLAN_SCHEMA:
        raise MigrationRefusal("plan schema mismatch")
    if plan.get("policy_revision") != PUBLICATION_POLICY_REVISION:
        raise MigrationRefusal("plan policy mismatch")
    if _require_sha(plan_sha256, "plan SHA-256 confirmation") != sha256_bytes(
        canonical_json_bytes(plan)
    ):
        raise MigrationRefusal("plan SHA-256 confirmation mismatch")
    target = plan.get("target_fingerprint")
    if _require_sha(target, "plan target fingerprint") != confirm_target:
        raise MigrationRefusal("target confirmation mismatch")
    created_at = parse_utc(plan.get("created_at"))
    now = _require_aware_datetime(now, "apply time")
    max_age = plan.get("max_age_seconds")
    if type(max_age) is not int or max_age != MAX_PLAN_AGE_SECONDS:
        raise MigrationRefusal("plan max age is invalid")
    age = (now - created_at).total_seconds()
    if age < 0 or age > MAX_PLAN_AGE_SECONDS:
        raise MigrationRefusal("plan is stale")
    return target


def _plan_identity_fingerprint(plan: dict[str, object]) -> str:
    identity = plan.get("database_identity")
    try:
        return target_fingerprint(identity)
    except (KeyError, TypeError):
        raise MigrationRefusal("plan database identity is invalid") from None


def _valid_plan_schema_column(column: object) -> bool:
    return (
        type(column) is dict
        and set(column) == {"name", "type", "nullable"}
        and all(type(column[key]) is str for key in ("name", "type", "nullable"))
    )


def _plan_schema_column_tuples(
    plan: dict[str, object],
) -> list[tuple[str, str, str]]:
    columns = plan.get("schema_columns")
    if type(columns) is not list or not all(
        _valid_plan_schema_column(column) for column in columns
    ):
        raise MigrationRefusal("plan schema columns are invalid")
    return [
        (column["name"], column["type"], column["nullable"]) for column in columns
    ]


def _validate_plan_identity_schema(plan: dict[str, object], target: str) -> None:
    if _plan_identity_fingerprint(plan) != target:
        raise MigrationRefusal("plan target identity mismatch")

    columns = plan.get("schema_columns")
    column_tuples = _plan_schema_column_tuples(plan)
    if len({column[0] for column in column_tuples}) != len(column_tuples):
        raise MigrationRefusal("plan schema columns contain duplicates")
    if columns != _normalized_schema_columns(column_tuples):
        raise MigrationRefusal("plan schema columns are not canonical")
    if schema_fingerprint(column_tuples) != _require_sha(
        plan.get("schema_fingerprint"), "plan schema fingerprint"
    ):
        raise MigrationRefusal("plan schema fingerprint mismatch")


def _validate_plan_candidates(plan: dict[str, object]) -> tuple[list[str], int]:
    candidate_ids = plan.get("candidate_ids")
    if type(candidate_ids) is not list or not candidate_ids or any(
        type(item) is not str or not item for item in candidate_ids
    ):
        raise MigrationRefusal("plan candidate IDs are invalid")
    if candidate_ids != sorted(set(candidate_ids)):
        raise MigrationRefusal("plan candidate IDs are not canonical")
    count = plan.get("candidate_count")
    if type(count) is not int or count != len(candidate_ids):
        raise MigrationRefusal("plan candidate count mismatch")
    if candidate_id_hash(candidate_ids) != plan.get("candidate_sha256"):
        raise MigrationRefusal("plan candidate hash mismatch")
    return list(candidate_ids), count


def _validate_plan_accounting(plan: dict[str, object], count: int) -> None:
    before = _require_nonnegative_counts(plan.get("expected_before"), "plan expected counts")
    after = _require_nonnegative_counts(plan.get("expected_after"), "plan expected counts")
    if after != {
        "published": before["published"] + count,
        "null": before["null"] - count,
    } or before["null"] < count:
        raise MigrationRefusal("plan expected count algebra mismatch")
    if plan.get("reviewed_exclusions") != sorted(PUBLISHED_V1_EXCLUSIONS):
        raise MigrationRefusal("plan policy exclusions mismatch")
    _require_counter(plan.get("exclusion_counts"), "plan exclusion counts")
    _require_counter(plan.get("status_groups"), "plan status groups")
    if type(plan.get("tool_source_revision")) is not str or not plan["tool_source_revision"]:
        raise MigrationRefusal("plan source revision is invalid")


def _validate_plan_for_apply(
    plan: dict[str, object], plan_sha256: str, confirm_target: str, now: datetime
) -> tuple[str, list[str]]:
    if type(plan) is not dict:
        raise MigrationRefusal("plan must be an object")
    _require_exact_keys(plan, _PLAN_KEYS, "plan")
    target = _validate_plan_header(plan, plan_sha256, confirm_target, now)
    _validate_plan_identity_schema(plan, target)
    candidate_ids, count = _validate_plan_candidates(plan)
    _validate_plan_accounting(plan, count)
    return target, candidate_ids


def _validate_schema(columns) -> list[dict[str, object]]:
    normalized = _normalized_schema_columns(columns)
    names = {column["name"] for column in normalized}
    missing = sorted(REQUIRED_ENTITY_COLUMNS - names)
    if missing:
        raise MigrationRefusal(
            f"entities schema missing required columns: {', '.join(missing)}"
        )
    return normalized


def _validate_rows(rows) -> list[dict[str, object]]:
    validated: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in rows:
        if type(row) is not dict:
            raise MigrationRefusal("entity row must be a dict")
        entity_id = row.get("id")
        if type(entity_id) is not str or not entity_id:
            raise MigrationRefusal("entity id must be an exact nonempty string")
        if entity_id in seen:
            raise MigrationRefusal(f"duplicate entity id: {entity_id}")
        seen.add(entity_id)
        validated.append(row)
    return validated


def _is_linklike(metadata: os.stat_result) -> bool:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return (
        stat.S_ISLNK(metadata.st_mode)
        or bool(getattr(metadata, "st_reparse_tag", 0))
        or bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)
    )


def _artifact_state(path: Path) -> tuple[int, int, int, str]:
    try:
        metadata = path.lstat()
    except OSError:
        raise MigrationRefusal("backup artifact is unavailable") from None
    if _is_linklike(metadata) or not stat.S_ISREG(metadata.st_mode):
        raise MigrationRefusal("backup artifact path is invalid")
    return metadata.st_dev, metadata.st_ino, metadata.st_size, sha256_file(path)


def _validate_backup_header(manifest, expected_target: str) -> None:
    if manifest["schema"] != "vinhlong360-pg-backup-v1":
        raise MigrationRefusal("backup schema mismatch")
    if manifest["target"] != "pg":
        raise MigrationRefusal("backup target must be pg")
    if manifest["policy_revision"] != PUBLICATION_POLICY_REVISION:
        raise MigrationRefusal("backup policy mismatch")
    if manifest["target_fingerprint"] != expected_target:
        raise MigrationRefusal("backup target mismatch")
    try:
        if target_fingerprint(manifest["database_identity"]) != expected_target:
            raise MigrationRefusal("backup database identity mismatch")
    except (KeyError, TypeError):
        raise MigrationRefusal("backup database identity mismatch") from None


def _validate_backup_freshness(
    manifest: dict[str, object], now: datetime, require_fresh: bool
) -> None:
    started = parse_utc(manifest["started_at"])
    completed = parse_utc(manifest["completed_at"])
    if started > completed:
        raise MigrationRefusal("backup timestamps are invalid")
    max_age = manifest["max_age_seconds"]
    if type(max_age) is not int or max_age != MAX_BACKUP_AGE_SECONDS:
        raise MigrationRefusal("backup max age is invalid")
    age = (now - completed).total_seconds()
    if require_fresh and (age < 0 or age > MAX_BACKUP_AGE_SECONDS):
        raise MigrationRefusal("backup evidence is stale")


def _validate_backup_tools_and_evidence(manifest: dict[str, object]) -> None:
    tools = _require_exact_keys(manifest["tools"], {"pg_dump", "pg_restore"}, "backup tools")
    if any(type(value) is not str or not value.strip() for value in tools.values()):
        raise MigrationRefusal("backup tools are invalid")
    validation = _require_exact_keys(
        manifest["validation"],
        {"pg_restore_list", "required_tables", "listing_sha256"},
        "backup validation",
    )
    if validation["pg_restore_list"] is not True:
        raise MigrationRefusal("backup restore-list validation is missing")
    if validation["required_tables"] != ["entities", "entity_changes"]:
        raise MigrationRefusal("backup required-table evidence mismatch")
    _require_sha(validation["listing_sha256"], "backup listing hash")


def _valid_backup_artifact_name(value: object) -> bool:
    if type(value) is not str or not value:
        return False
    path = Path(value)
    return (
        path.name == value
        and not path.is_absolute()
        and "/" not in value
        and "\\" not in value
        and value not in {".", ".."}
    )


def _backup_artifact_metadata(manifest) -> tuple[str, int, str]:
    artifact_info = _require_exact_keys(
        manifest["artifact"], {"path", "size", "sha256"}, "backup artifact"
    )
    artifact_name = artifact_info["path"]
    if not _valid_backup_artifact_name(artifact_name):
        raise MigrationRefusal("backup artifact path is invalid")
    artifact_size = artifact_info["size"]
    if type(artifact_size) is not int or artifact_size < 0:
        raise MigrationRefusal("backup artifact size is invalid")
    expected_hash = _require_sha(artifact_info["sha256"], "backup artifact hash")
    return artifact_name, artifact_size, expected_hash


def _validated_backup_root(root: Path) -> Path:
    try:
        root_metadata = root.lstat()
    except OSError:
        raise MigrationRefusal("backup artifact root is unavailable") from None
    if _is_linklike(root_metadata) or not root.is_dir():
        raise MigrationRefusal("backup artifact root is invalid")
    return root.resolve()


def _validated_backup_artifact_path(root: Path, artifact_name: str) -> Path:
    artifact = root / artifact_name
    if artifact.parent != root:
        raise MigrationRefusal("backup artifact path is invalid")
    try:
        artifact_metadata = artifact.lstat()
    except OSError:
        raise MigrationRefusal("backup artifact is unavailable") from None
    if _is_linklike(artifact_metadata) or not stat.S_ISREG(artifact_metadata.st_mode):
        raise MigrationRefusal("backup artifact path is invalid")
    return artifact


def _validate_backup_artifact(backup: BackupEvidence, manifest) -> Path:
    artifact_name, artifact_size, expected_hash = _backup_artifact_metadata(manifest)
    root = _validated_backup_root(backup.artifact_root)
    artifact = _validated_backup_artifact_path(root, artifact_name)
    state = _artifact_state(artifact)
    if state[2] != artifact_size:
        raise MigrationRefusal("backup artifact size mismatch")
    if state[3] != expected_hash:
        raise MigrationRefusal("backup artifact hash mismatch")
    return artifact


def validate_backup_manifest(
    backup: BackupEvidence,
    *,
    expected_target: str,
    now: datetime,
    require_fresh: bool,
) -> Path:
    manifest = _require_exact_keys(backup.manifest, _BACKUP_KEYS, "backup manifest")
    now = _require_aware_datetime(now, "backup validation time")
    if backup.manifest_sha256 != sha256_bytes(canonical_json_bytes(manifest)):
        raise MigrationRefusal("backup manifest hash mismatch")
    _validate_backup_header(manifest, expected_target)
    _validate_backup_freshness(manifest, now, require_fresh)
    _validate_backup_tools_and_evidence(manifest)
    return _validate_backup_artifact(backup, manifest)


_REQUIRED_RESTORE_TABLES = ("entities", "entity_changes")


def _restore_object_is_related(schema: str, name: str) -> bool:
    if name in _REQUIRED_RESTORE_TABLES:
        return True
    return schema == "public" and any(
        name.startswith(prefix) for prefix in _REQUIRED_RESTORE_TABLES
    )


def _reject_malformed_restore_reference(body: str, match, name: str) -> None:
    trailing = body[match.end() :].split()
    if name != "TABLE" or not trailing:
        return
    if any(trailing[0].startswith(prefix) for prefix in _REQUIRED_RESTORE_TABLES):
        raise MigrationRefusal("pg_restore listing contains invalid table objects")


def _validated_required_restore_object(
    foreign: str | None, kind: str, schema: str, name: str
) -> str | None:
    if foreign or schema != "public" or name not in _REQUIRED_RESTORE_TABLES:
        raise MigrationRefusal("pg_restore listing contains invalid table objects")
    if kind == "TABLE DATA":
        return None
    if kind != "TABLE":
        raise MigrationRefusal("pg_restore listing contains invalid table objects")
    return name


def _restore_required_object(text: str) -> str | None:
    prefix = re.match(r"^\d+;\s+\S+\s+\S+\s+(.*)$", text)
    body = prefix.group(1) if prefix else text
    match = re.match(
        r"^(FOREIGN\s+)?(TABLE DATA|TABLE|COMMENT|ACL|FUNCTION)\s+"
        r"(\S+)\s+(\S+)(?:\s|$)",
        body,
    )
    if not match:
        return None
    foreign, kind, schema, name = match.groups()
    if not _restore_object_is_related(schema, name):
        _reject_malformed_restore_reference(body, match, name)
        return None
    return _validated_required_restore_object(foreign, kind, schema, name)


def validate_restore_artifact(path: Path, runner=subprocess.run) -> str:
    result = runner(
        ["pg_restore", "--list", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise MigrationRefusal("pg_restore --list revalidation failed")
    found: Counter[str] = Counter()
    for line in result.stdout.splitlines():
        text = line.strip()
        if not text or text.startswith(";"):
            continue
        required_object = _restore_required_object(text)
        if required_object:
            found[required_object] += 1
    missing = [table for table in ("entities", "entity_changes") if found[table] != 1]
    if missing:
        raise MigrationRefusal(f"backup revalidation missing tables: {', '.join(missing)}")
    return sha256_bytes(result.stdout.encode("utf-8"))


class PostgresPublicationStore:
    def __init__(self, cursor, schema: str = "public") -> None:
        self.cursor = cursor
        self.schema = validate_schema_identifier(schema)
        self.entities = f"{self.schema}.entities"
        self.entity_changes = f"{self.schema}.entity_changes"

    def target_identity(self):
        return read_target_identity(self.cursor)

    def schema_columns(self):
        self.cursor.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            f"WHERE table_schema = '{self.schema}' AND table_name = 'entities' "
            "ORDER BY column_name"
        )
        return list(self.cursor.fetchall())

    def acquire_lock(self, name: str) -> None:
        self.cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (name,))

    def rows_for_update(self, ids):
        self.cursor.execute(
            f"SELECT * FROM {self.entities} WHERE id = ANY(%s) "
            "ORDER BY id FOR UPDATE",
            (ids,),
        )
        names = [item[0] for item in self.cursor.description]
        return [dict(zip(names, row, strict=True)) for row in self.cursor.fetchall()]

    def audit_rows(self, actor: str):
        self.cursor.execute(
            "SELECT entity_id, field, old_value, new_value, actor "
            f"FROM {self.entity_changes} WHERE actor = %s ORDER BY entity_id",
            (actor,),
        )
        names = [item[0] for item in self.cursor.description]
        return [dict(zip(names, row, strict=True)) for row in self.cursor.fetchall()]

    def audit_ids(self, actor, old_value, new_value):
        return {
            row["entity_id"]
            for row in self.audit_rows(actor)
            if row["old_value"] == old_value and row["new_value"] == new_value
        }

    def apply_audit_rows(self, ids):
        self.cursor.execute(
            "SELECT entity_id, field, old_value, new_value, actor "
            f"FROM {self.entity_changes} WHERE entity_id = ANY(%s) "
            "AND field = %s AND old_value = %s AND new_value = %s "
            "AND actor LIKE %s ORDER BY entity_id, actor",
            (
                ids,
                "status",
                "null",
                "published",
                f"entity-status:apply:{PUBLICATION_POLICY_REVISION}:%",
            ),
        )
        names = [item[0] for item in self.cursor.description]
        return [dict(zip(names, row, strict=True)) for row in self.cursor.fetchall()]

    def update_to_published(self, ids):
        self.cursor.execute(
            "WITH updated AS ("
            f"UPDATE {self.entities} SET status = 'published' "
            "WHERE id = ANY(%s) AND status IS NULL RETURNING id"
            ") SELECT id FROM updated ORDER BY id",
            (ids,),
        )
        return [row[0] for row in self.cursor.fetchall()]

    def insert_status_audit(self, ids, actor, old_value, new_value):
        self.cursor.executemany(
            f"INSERT INTO {self.entity_changes} "
            "(entity_id, field, old_value, new_value, actor) "
            "VALUES (%s, 'status', %s, %s, %s)",
            [(entity_id, old_value, new_value, actor) for entity_id in ids],
        )

    def status_counts(self):
        self.cursor.execute(
            "SELECT COUNT(*) FILTER (WHERE status = 'published'), "
            f"COUNT(*) FILTER (WHERE status IS NULL) FROM {self.entities}"
        )
        row = self.cursor.fetchone()
        return {"published": int(row[0]), "null": int(row[1])}


def _audit_records(store, actor: str) -> list[dict[str, object]]:
    if hasattr(store, "audit_rows"):
        return list(store.audit_rows(actor))
    ids = store.audit_ids(actor, "null", "published")
    return [
        {
            "entity_id": entity_id,
            "field": "status",
            "old_value": "null",
            "new_value": "published",
            "actor": actor,
        }
        for entity_id in ids
    ]


def _candidate_apply_records(store, candidate_ids, actor: str) -> list[dict[str, object]]:
    if hasattr(store, "apply_audit_rows"):
        return list(store.apply_audit_rows(candidate_ids))
    if hasattr(store, "audit"):
        prefix = f"entity-status:apply:{PUBLICATION_POLICY_REVISION}:"
        return [
            dict(row)
            for row in store.audit
            if row.get("entity_id") in candidate_ids
            and str(row.get("actor", "")).startswith(prefix)
        ]
    return _audit_records(store, actor)


def _audit_owned_exact(records, candidate_ids: list[str], actor: str) -> bool:
    expected = [
        {
            "entity_id": entity_id,
            "field": "status",
            "old_value": "null",
            "new_value": "published",
            "actor": actor,
        }
        for entity_id in candidate_ids
    ]
    positions = {entity_id: index for index, entity_id in enumerate(candidate_ids)}
    if len(records) != len(candidate_ids) or any(
        row.get("entity_id") not in positions for row in records
    ):
        return False
    ordered = sorted(records, key=lambda row: positions[row["entity_id"]])
    normalized = [
        {
            "entity_id": row.get("entity_id"),
            "field": row.get("field"),
            "old_value": row.get("old_value"),
            "new_value": row.get("new_value"),
            "actor": row.get("actor"),
        }
        for row in ordered
    ]
    return normalized == expected


def _apply_report(
    result: str,
    plan: dict[str, object],
    plan_sha256: str,
    backup: BackupEvidence,
    updated_ids: list[str],
    now: datetime,
) -> dict[str, object]:
    candidate_ids = list(plan["candidate_ids"])
    return {
        "schema": APPLY_SCHEMA,
        "policy_revision": PUBLICATION_POLICY_REVISION,
        "result": result,
        "target_fingerprint": plan["target_fingerprint"],
        "schema_fingerprint": plan["schema_fingerprint"],
        "plan_sha256": plan_sha256,
        "backup_manifest_sha256": backup.manifest_sha256,
        "candidate_ids": candidate_ids,
        "candidate_count": len(candidate_ids),
        "candidate_sha256": candidate_id_hash(candidate_ids),
        "expected_before": dict(plan["expected_before"]),
        "expected_after": dict(plan["expected_after"]),
        "updated_ids": list(updated_ids),
        "started_at": utc_text(now),
        "completed_at": utc_text(now),
    }


def _locked_freshness(
    plan,
    plan_sha256: str,
    backup: BackupEvidence,
    target: str,
    now: datetime,
    clock,
) -> None:
    current = _require_aware_datetime(
        clock() if clock else _utc_now(), "locked apply time"
    )
    _validate_plan_header(plan, plan_sha256, target, current)
    _validate_backup_freshness(backup.manifest, current, True)


def _locked_rows(
    store,
    plan,
    plan_sha256: str,
    backup: BackupEvidence,
    target: str,
    candidate_ids: list[str],
    now: datetime,
    clock,
):
    store.acquire_lock(LOCK_NAME)
    _locked_freshness(plan, plan_sha256, backup, target, now, clock)
    if target_fingerprint(store.target_identity()) != target:
        raise MigrationRefusal("connected target drift")
    if schema_fingerprint(store.schema_columns()) != plan["schema_fingerprint"]:
        raise MigrationRefusal("entity schema drift")
    rows = store.rows_for_update(candidate_ids)
    row_ids = [row.get("id") for row in rows]
    if (
        len(row_ids) != len(candidate_ids)
        or any(type(entity_id) is not str for entity_id in row_ids)
        or len(set(row_ids)) != len(row_ids)
        or set(row_ids) != set(candidate_ids)
    ):
        raise MigrationRefusal("planned IDs are missing or reordered")
    positions = {entity_id: index for index, entity_id in enumerate(candidate_ids)}
    return sorted(rows, key=lambda row: positions[row["id"]])


def _already_applied_report(
    store,
    plan,
    plan_sha256: str,
    backup: BackupEvidence,
    candidate_ids: list[str],
    actor: str,
    audit_records,
    candidate_audits,
    now: datetime,
):
    if not _audit_owned_exact(audit_records, candidate_ids, actor) or not _audit_owned_exact(
        candidate_audits, candidate_ids, actor
    ):
        raise MigrationRefusal("published rows lack exact audit ownership")
    if store.status_counts() != plan["expected_after"]:
        raise MigrationRefusal("already-applied global count drift")
    report = _apply_report(
        "already-applied", plan, plan_sha256, backup, candidate_ids, now
    )
    report["recovery_ready"] = True
    report["recovery_contract"] = "apply-audit-exact-v1"
    return report


def _apply_new_candidates(
    store,
    plan,
    plan_sha256: str,
    backup: BackupEvidence,
    candidate_ids: list[str],
    actor: str,
    audit_records,
    rows,
    now: datetime,
):
    if any(row.get("status") is not None for row in rows):
        raise MigrationRefusal("candidate status drift")
    if audit_records:
        raise MigrationRefusal("pre-existing apply audit on null candidate")
    if store.status_counts() != plan["expected_before"]:
        raise MigrationRefusal("pre-apply global count drift")
    eligible_ids = [
        str(row["id"])
        for row in rows
        if decide_publication_candidate(row).eligible
    ]
    if eligible_ids != candidate_ids:
        raise MigrationRefusal("candidate drift")
    if candidate_id_hash(eligible_ids) != plan["candidate_sha256"]:
        raise MigrationRefusal("candidate hash drift")
    updated_ids = store.update_to_published(candidate_ids)
    if updated_ids != candidate_ids:
        raise MigrationRefusal("status update IDs drift")
    store.insert_status_audit(updated_ids, actor, "null", "published")
    if not _audit_owned_exact(
        _audit_records(store, actor), candidate_ids, actor
    ) or not _audit_owned_exact(
        _candidate_apply_records(store, candidate_ids, actor), candidate_ids, actor
    ):
        raise MigrationRefusal("audit ownership/cardinality drift")
    if store.status_counts() != plan["expected_after"]:
        raise MigrationRefusal("post-apply global count drift")
    return _apply_report("applied", plan, plan_sha256, backup, updated_ids, now)


def _apply_locked(
    store,
    plan: dict[str, object],
    *,
    plan_sha256: str,
    backup: BackupEvidence,
    target: str,
    candidate_ids: list[str],
    now: datetime,
    clock=None,
) -> dict[str, object]:
    rows = _locked_rows(
        store,
        plan,
        plan_sha256,
        backup,
        target,
        candidate_ids,
        now,
        clock,
    )
    actor = audit_actor("apply", plan_sha256)
    audit_records = _audit_records(store, actor)
    candidate_audits = _candidate_apply_records(store, candidate_ids, actor)
    statuses = [row.get("status") for row in rows]
    published = all(status == "published" for status in statuses)
    if candidate_audits and not published:
        raise MigrationRefusal("pre-existing apply audit on null candidate")
    if published:
        return _already_applied_report(
            store,
            plan,
            plan_sha256,
            backup,
            candidate_ids,
            actor,
            audit_records,
            candidate_audits,
            now,
        )
    return _apply_new_candidates(
        store,
        plan,
        plan_sha256,
        backup,
        candidate_ids,
        actor,
        audit_records,
        rows,
        now,
    )


def _assert_artifact_unchanged(artifact: Path, state: tuple[int, int, int, str]) -> None:
    if _artifact_state(artifact) != state:
        raise MigrationRefusal("backup artifact changed during validation")


def _open_validated_artifact(artifact: Path, state):
    metadata = artifact.lstat()
    if _is_linklike(metadata) or not stat.S_ISREG(metadata.st_mode):
        raise MigrationRefusal("backup artifact path is invalid")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(artifact, flags)
    except OSError:
        raise MigrationRefusal("backup artifact changed during pinning") from None
    opened = os.fstat(descriptor)
    if (opened.st_dev, opened.st_ino, opened.st_size) != state[:3]:
        os.close(descriptor)
        raise MigrationRefusal("backup artifact changed during pinning")
    return os.fdopen(descriptor, "rb")


def _validate_pinned_restore(artifact: Path, state, restore_validator) -> str:
    with tempfile.TemporaryDirectory(prefix="vinhlong360-publication-apply-") as directory:
        pinned = Path(directory) / "postgres.dump"
        with _open_validated_artifact(artifact, state) as source, pinned.open(
            "xb"
        ) as destination:
            while chunk := source.read(1024 * 1024):
                destination.write(chunk)
            destination.flush()
            os.fsync(destination.fileno())
        _assert_artifact_unchanged(artifact, state)
        if sha256_file(pinned) != state[3]:
            raise MigrationRefusal("backup artifact changed during pinning")
        listing_hash = _require_sha(
            restore_validator(pinned), "restore listing hash"
        )
        _assert_artifact_unchanged(artifact, state)
        return listing_hash


def apply_plan(
    store,
    plan: dict[str, object],
    *,
    plan_sha256: str,
    backup: BackupEvidence,
    confirm_target: str,
    now: datetime,
    restore_validator,
    clock=None,
) -> dict[str, object]:
    target, candidate_ids = _validate_plan_for_apply(
        plan, plan_sha256, confirm_target, now
    )
    artifact = validate_backup_manifest(
        backup, expected_target=target, now=now, require_fresh=True
    )
    state = _artifact_state(artifact)
    listing_hash = _validate_pinned_restore(artifact, state, restore_validator)
    expected_listing = backup.manifest["validation"]["listing_sha256"]
    if listing_hash != expected_listing:
        raise MigrationRefusal("backup listing hash mismatch")
    _assert_artifact_unchanged(artifact, state)
    return _apply_locked(
        store,
        plan,
        plan_sha256=plan_sha256,
        backup=backup,
        target=target,
        candidate_ids=candidate_ids,
        now=now,
        clock=clock,
    )


def _status_group(value: object) -> str:
    if value is None:
        return "<null>"
    if type(value) is str:
        return value
    return f"<{type(value).__name__}>:{value!r}"


def _summarize_rows(
    rows: list[dict[str, object]],
) -> tuple[list[str], Counter[str], Counter[str], int, int]:
    candidates: list[str] = []
    exclusions: Counter[str] = Counter()
    status_groups: Counter[str] = Counter()
    published_before = 0
    null_before = 0
    for row in rows:
        status = row.get("status")
        status_groups[_status_group(status)] += 1
        published_before += int(status == "published")
        null_before += int(status is None)
        decision = decide_publication_candidate(row)
        if decision.eligible:
            candidates.append(row["id"])
        else:
            exclusions.update(decision.reasons)
    return candidates, exclusions, status_groups, published_before, null_before


def _sorted_counter(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _database_identity(identity) -> dict[str, object]:
    return dict(identity)


def build_plan(
    *,
    rows,
    identity,
    schema_columns,
    created_at,
    tool_source_revision,
) -> dict[str, object]:
    normalized_columns = _validate_schema(schema_columns)
    validated_rows = _validate_rows(rows)
    candidates, exclusions, status_groups, published_before, null_before = (
        _summarize_rows(validated_rows)
    )
    candidates.sort()
    if not candidates:
        raise MigrationRefusal("publication plan has zero candidates")
    database_identity = _database_identity(identity)
    candidate_count = len(candidates)
    return {
        "schema": PLAN_SCHEMA,
        "policy_revision": PUBLICATION_POLICY_REVISION,
        "created_at": created_at,
        "max_age_seconds": MAX_PLAN_AGE_SECONDS,
        "tool_source_revision": tool_source_revision,
        "target_fingerprint": target_fingerprint(identity),
        "database_identity": database_identity,
        "schema_fingerprint": sha256_bytes(canonical_json_bytes(normalized_columns)),
        "schema_columns": normalized_columns,
        "candidate_ids": candidates,
        "candidate_count": candidate_count,
        "candidate_sha256": candidate_id_hash(candidates),
        "reviewed_exclusions": sorted(PUBLISHED_V1_EXCLUSIONS),
        "exclusion_counts": _sorted_counter(exclusions),
        "status_groups": _sorted_counter(status_groups),
        "expected_before": {"published": published_before, "null": null_before},
        "expected_after": {
            "published": published_before + candidate_count,
            "null": null_before - candidate_count,
        },
    }


def _load_psycopg2():
    try:
        import psycopg2
    except ImportError:
        raise MigrationRefusal("psycopg2 is required for PostgreSQL planning") from None
    return psycopg2


def _source_revision(runner=subprocess.run) -> str:
    release_revision = os.environ.get("VINHLONG360_RELEASE_REVISION", "").strip()
    if release_revision:
        return release_revision
    try:
        result = runner(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        raise MigrationRefusal("unable to determine source revision") from None
    revision = result.stdout.strip() if result.returncode == 0 else ""
    if not revision:
        raise MigrationRefusal("unable to determine source revision")
    return revision


def _read_schema_columns(
    cursor, schema: str = "public"
) -> list[tuple[object, object, object]]:
    schema = validate_schema_identifier(schema)
    cursor.execute(
        f"""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = '{schema}'
          AND table_name = 'entities'
        ORDER BY ordinal_position
        """
    )
    return list(cursor.fetchall())


def _read_entity_rows(cursor, schema: str = "public") -> list[dict[str, object]]:
    schema = validate_schema_identifier(schema)
    cursor.execute(f"SELECT * FROM {schema}.entities ORDER BY id")
    names = [description[0] for description in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def _safe_method(target, method_name: str) -> None:
    if target is None:
        return
    try:
        getattr(target, method_name)()
    except Exception:
        return


def _close_snapshot(connection, cursor) -> None:
    _safe_method(cursor, "close")
    _safe_method(connection, "rollback")
    _safe_method(connection, "close")


def _read_postgres_snapshot(database_url: str, psycopg2_module, schema: str = "public"):
    schema = validate_schema_identifier(schema)
    connection = None
    cursor = None
    try:
        connection = psycopg2_module.connect(database_url)
        connection.set_session(
            isolation_level="REPEATABLE READ",
            readonly=True,
            autocommit=False,
        )
        cursor = connection.cursor()
        identity = read_target_identity(cursor)
        schema_columns = _read_schema_columns(cursor, schema)
        rows = _read_entity_rows(cursor, schema)
        return identity, schema_columns, rows
    except Exception:
        raise MigrationRefusal("unable to read PostgreSQL publication snapshot") from None
    finally:
        _close_snapshot(connection, cursor)


def _validate_plan_args(args: argparse.Namespace) -> None:
    if args.target != "pg":
        raise MigrationRefusal("plan target must be pg")
    if not args.database_url_env or args.database_url_env == "DATABASE_URL":
        raise MigrationRefusal(
            "plan requires a named database URL environment other than DATABASE_URL"
        )
    if args.policy != PUBLICATION_POLICY_REVISION:
        raise MigrationRefusal("plan policy must be published-v1")
    if args.report_out.exists():
        raise MigrationRefusal("report output already exists")


def _validate_apply_args(args: argparse.Namespace) -> None:
    if args.target != "pg":
        raise MigrationRefusal("apply target must be pg")
    if not args.database_url_env or args.database_url_env == "DATABASE_URL":
        raise MigrationRefusal(
            "apply requires a named database URL environment other than DATABASE_URL"
        )
    if args.report_out.exists():
        raise MigrationRefusal("report output already exists")
    _require_sha(args.confirm_target, "target confirmation")
    _require_sha(args.confirm_plan_sha256, "plan SHA-256 confirmation")
    _require_sha(
        args.confirm_backup_manifest_sha256,
        "backup manifest SHA-256 confirmation",
    )
    if not args.plan.is_file() or not args.backup_manifest.is_file():
        raise MigrationRefusal("plan and backup manifest paths must be files")


def _load_apply_artifacts(
    args: argparse.Namespace, now: datetime
) -> tuple[dict[str, object], str, BackupEvidence, Path, tuple[int, int, int, str]]:
    plan, plan_sha256 = load_immutable_json(args.plan)
    if plan_sha256 != args.confirm_plan_sha256:
        raise MigrationRefusal("plan SHA-256 confirmation mismatch")
    if plan_sha256 != sha256_bytes(canonical_json_bytes(plan)):
        raise MigrationRefusal("plan bytes are not canonical")
    target, _candidate_ids = _validate_plan_for_apply(
        plan, plan_sha256, args.confirm_target, now
    )
    manifest, manifest_sha256 = load_immutable_json(args.backup_manifest)
    if manifest_sha256 != args.confirm_backup_manifest_sha256:
        raise MigrationRefusal("backup manifest SHA-256 confirmation mismatch")
    if manifest_sha256 != sha256_bytes(canonical_json_bytes(manifest)):
        raise MigrationRefusal("backup manifest bytes are not canonical")
    backup = BackupEvidence(
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        artifact_root=args.backup_manifest.parent,
    )
    artifact = validate_backup_manifest(
        backup, expected_target=target, now=now, require_fresh=True
    )
    state = _artifact_state(artifact)
    listing_hash = _validate_pinned_restore(
        artifact, state, validate_restore_artifact
    )
    if listing_hash != manifest["validation"]["listing_sha256"]:
        raise MigrationRefusal("backup listing hash mismatch")
    _assert_artifact_unchanged(artifact, state)
    return plan, plan_sha256, backup, artifact, state


def _generate_apply(args: argparse.Namespace) -> dict[str, object]:
    now = _utc_now()
    plan, plan_sha256, backup, artifact, artifact_state = _load_apply_artifacts(args, now)
    database_url = _resolved_database_url(args.database_url_env)
    psycopg2_module = _load_psycopg2()
    connection = None
    cursor = None
    report: dict[str, object] | None = None
    try:
        connection = psycopg2_module.connect(database_url)
        connection.set_session(
            isolation_level="SERIALIZABLE", readonly=False, autocommit=False
        )
        cursor = connection.cursor()
        cursor.execute("SET LOCAL search_path = public")
        _assert_artifact_unchanged(artifact, artifact_state)
        target, candidate_ids = _validate_plan_for_apply(
            plan, plan_sha256, args.confirm_target, now
        )
        report = _apply_locked(
            PostgresPublicationStore(cursor),
            plan,
            plan_sha256=plan_sha256,
            backup=backup,
            target=target,
            candidate_ids=candidate_ids,
            now=now,
            clock=_utc_now,
        )
        connection.commit()
        report["completed_at"] = utc_text(_utc_now())
    except MigrationRefusal:
        _safe_method(connection, "rollback")
        raise
    except Exception:
        _safe_method(connection, "rollback")
        raise MigrationRefusal("publication apply transaction failed") from None
    finally:
        _safe_method(cursor, "close")
        _safe_method(connection, "close")
    if report is None:
        raise MigrationRefusal("publication apply did not produce a report")
    digest = write_immutable_json(args.report_out, report)
    return {
        "report_path": str(args.report_out),
        "sha256": digest,
        "result": report["result"],
        "candidate_count": report["candidate_count"],
    }


def _resolved_database_url(environment_name: str) -> str:
    try:
        return resolve_database_url(environment_name)
    except RuntimeError as exc:
        raise MigrationRefusal(str(exc)) from None


def _generate_plan(args: argparse.Namespace) -> dict[str, object]:
    database_url = _resolved_database_url(args.database_url_env)
    psycopg2_module = _load_psycopg2()
    identity, schema_columns, rows = _read_postgres_snapshot(
        database_url, psycopg2_module
    )
    plan = build_plan(
        rows=rows,
        identity=identity,
        schema_columns=schema_columns,
        created_at=utc_text(datetime.now(UTC)),
        tool_source_revision=_source_revision(),
    )
    digest = write_immutable_json(args.report_out, plan)
    return {
        "report_path": str(args.report_out),
        "sha256": digest,
        "candidate_count": plan["candidate_count"],
        "target_fingerprint": plan["target_fingerprint"],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument("--target", required=True)
    plan.add_argument("--database-url-env", required=True)
    plan.add_argument("--policy", required=True)
    plan.add_argument("--report-out", required=True, type=Path)
    apply = subparsers.add_parser("apply")
    apply.add_argument("--target", required=True)
    apply.add_argument("--database-url-env", required=True)
    apply.add_argument("--plan", required=True, type=Path)
    apply.add_argument("--backup-manifest", required=True, type=Path)
    apply.add_argument("--confirm-target", required=True)
    apply.add_argument("--confirm-plan-sha256", required=True)
    apply.add_argument("--confirm-backup-manifest-sha256", required=True)
    apply.add_argument("--report-out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "plan":
            _validate_plan_args(args)
            evidence = _generate_plan(args)
        else:
            _validate_apply_args(args)
            evidence = _generate_apply(args)
    except MigrationRefusal as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except FileExistsError:
        print("ERROR: report output already exists", file=sys.stderr)
        return 1
    except Exception:
        print("ERROR: publication plan generation failed", file=sys.stderr)
        return 1
    print(
        json.dumps(
            evidence,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
