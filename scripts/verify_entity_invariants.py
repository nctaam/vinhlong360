"""Aggregate, read-only verification of entity column and CTI invariants."""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from database import PG_REQUIRED_SCHEMA_VERSION, PG_REQUIRED_TRIGGERS  # noqa: E402
from entity_details import (  # noqa: E402
    DETAIL_TABLES,
    KEY_MAP,
    KIND_TABLE,
    UNIVERSAL,
    norm_value,
    split_typed,
)
from entity_schemas import KIND_OF_TYPE  # noqa: E402


INVARIANT_KEYS = (
    "typed_jsonb_equal",
    "typed_jsonb_conflict",
    "typed_jsonb_without_column",
    "typed_uncoercible",
    "missing_expected_cti",
    "wrong_kind_cti",
    "multi_cti",
    "missing_required_trigger",
    "schema_version_below_required",
)


@dataclass(frozen=True)
class InvariantReport:
    total_entities: int
    counts: dict[str, int]
    schema: dict[str, object]

    @property
    def ok(self) -> bool:
        return all(value == 0 for value in self.counts.values())

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "total_entities": self.total_entities,
            "counts": dict(sorted(self.counts.items())),
            "schema": self.schema,
        }


def _compare_typed_value(counts: dict[str, int], expected: Any, actual: Any) -> None:
    if actual is None:
        counts["typed_jsonb_without_column"] += 1
    elif norm_value(actual) == norm_value(expected):
        counts["typed_jsonb_equal"] += 1
    else:
        counts["typed_jsonb_conflict"] += 1


def _evaluate_schema(counts: dict[str, int], schema: dict[str, object]) -> None:
    required_version = schema.get("required_version", PG_REQUIRED_SCHEMA_VERSION)
    version = schema.get("version")
    if (
        isinstance(required_version, bool)
        or not isinstance(required_version, int)
        or isinstance(version, bool)
        or not isinstance(version, int)
        or version < required_version
    ):
        counts["schema_version_below_required"] = 1

    required = schema.get("required_triggers", PG_REQUIRED_TRIGGERS)
    present = schema.get("triggers", {})
    required_triggers = required if isinstance(required, dict) else {}
    present_triggers = present if isinstance(present, dict) else {}
    counts["missing_required_trigger"] = sum(
        present_triggers.get(name) != table
        for name, table in required_triggers.items()
    )


def evaluate_invariants(
    entities: Iterable[dict[str, Any]],
    details: dict[str, dict[str, dict[str, Any]]],
    schema: dict[str, object],
) -> InvariantReport:
    """Evaluate entity parity and CTI topology without exposing row data."""
    counts = {key: 0 for key in INVARIANT_KEYS}
    total_entities = 0

    for entity in entities:
        total_entities += 1
        entity_id = entity["id"]
        entity_type = entity["type"]
        attributes = entity.get("attributes") or {}
        universal, detail, skipped = split_typed(entity_type, attributes)
        counts["typed_uncoercible"] += len(skipped)

        kind = KIND_OF_TYPE.get(entity_type)
        expected_table = KIND_TABLE.get(kind or "")
        rows_by_table = {
            table: table_rows[entity_id]
            for table, table_rows in details.items()
            if entity_id in table_rows
        }
        present_tables = set(rows_by_table)

        if detail and expected_table is not None and expected_table not in present_tables:
            counts["missing_expected_cti"] += 1
        if any(table != expected_table for table in present_tables):
            counts["wrong_kind_cti"] += 1
        if len(present_tables) > 1:
            counts["multi_cti"] += 1

        for column, expected in universal.items():
            if column not in UNIVERSAL:
                continue
            _compare_typed_value(counts, expected, entity.get(column))

        if expected_table is not None:
            expected_row = rows_by_table.get(expected_table, {})
            for column, expected in detail.items():
                physical_column = KEY_MAP.get(column, column)
                _compare_typed_value(
                    counts, expected, expected_row.get(physical_column)
                )

    _evaluate_schema(counts, schema)
    return InvariantReport(total_entities, counts, schema)


def _load_rows(cursor: Any) -> tuple[list[dict[str, Any]], dict[str, dict]]:
    entity_columns = ", ".join(("id", "type", "attributes", *UNIVERSAL))
    cursor.execute(f"SELECT {entity_columns} FROM entities")
    entities = [dict(row) for row in cursor.fetchall()]

    details: dict[str, dict[str, dict[str, Any]]] = {}
    for table in DETAIL_TABLES:
        cursor.execute(f"SELECT * FROM {table}")
        details[table] = {
            row["entity_id"]: dict(row) for row in cursor.fetchall()
        }
    return entities, details


def _load_schema(cursor: Any) -> dict[str, object]:
    cursor.execute(
        "SELECT version FROM schema_version WHERE component = %s",
        ("agent",),
    )
    version_rows = cursor.fetchall()
    version = version_rows[0]["version"] if version_rows else None

    cursor.execute(
        """
        SELECT tg.tgname AS trigger_name, rel.relname AS table_name
        FROM pg_catalog.pg_trigger AS tg
        JOIN pg_catalog.pg_class AS rel ON rel.oid = tg.tgrelid
        JOIN pg_catalog.pg_namespace AS ns ON ns.oid = rel.relnamespace
        WHERE ns.nspname = %s
          AND NOT tg.tgisinternal
          AND tg.tgname = ANY(%s)
        """,
        ("public", list(PG_REQUIRED_TRIGGERS)),
    )
    triggers = {
        row["trigger_name"]: row["table_name"]
        for row in cursor.fetchall()
        if PG_REQUIRED_TRIGGERS.get(row["trigger_name"]) == row["table_name"]
    }
    return {
        "version": version,
        "required_version": PG_REQUIRED_SCHEMA_VERSION,
        "required_triggers": dict(sorted(PG_REQUIRED_TRIGGERS.items())),
        "triggers": dict(sorted(triggers.items())),
    }


def run(database_url: str) -> InvariantReport:
    """Load PostgreSQL state through a read-only session and aggregate it."""
    if not isinstance(database_url, str) or not database_url.strip().lower().startswith(
        ("postgres://", "postgresql://")
    ):
        raise ValueError("PostgreSQL database URL required")

    import psycopg2
    from psycopg2.extras import RealDictCursor

    connection = psycopg2.connect(database_url, connect_timeout=5)
    cursor = None
    try:
        connection.set_session(readonly=True, autocommit=True)
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        entities, details = _load_rows(cursor)
        schema = _load_schema(cursor)
        return evaluate_invariants(entities, details, schema)
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        report = run(os.environ.get("DATABASE_URL", ""))
    except Exception as exc:  # Boundary intentionally redacts operational details.
        print(
            f"entity invariant verification failed: {type(exc).__name__}",
            file=sys.stderr,
        )
        return 2

    if args.json:
        print(json.dumps(report.as_dict(), sort_keys=True))
    else:
        for key in INVARIANT_KEYS:
            print(f"{key}={report.counts.get(key, 0)}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
