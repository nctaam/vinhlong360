"""Generate an immutable PostgreSQL publication migration plan."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
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
        sha256_bytes,
        target_fingerprint,
        write_exclusive,
    )
else:
    from postgres_target import (  # noqa: E402
        canonical_json_bytes,
        read_target_identity,
        resolve_database_url,
        sha256_bytes,
        target_fingerprint,
        write_exclusive,
    )


PLAN_SCHEMA = "vinhlong360-entity-status-plan-v1"
APPLY_SCHEMA = "vinhlong360-entity-status-apply-v1"
ROLLBACK_SCHEMA = "vinhlong360-entity-status-rollback-v1"
MAX_PLAN_AGE_SECONDS = 86400
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


def _read_schema_columns(cursor) -> list[tuple[object, object, object]]:
    cursor.execute(
        """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'entities'
        ORDER BY ordinal_position
        """
    )
    return list(cursor.fetchall())


def _read_entity_rows(cursor) -> list[dict[str, object]]:
    cursor.execute("SELECT * FROM entities ORDER BY id")
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


def _read_postgres_snapshot(database_url: str, psycopg2_module):
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
        schema_columns = _read_schema_columns(cursor)
        rows = _read_entity_rows(cursor)
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        _validate_plan_args(args)
        evidence = _generate_plan(args)
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
