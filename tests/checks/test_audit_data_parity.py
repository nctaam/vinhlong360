import hashlib
import json
import os
import sqlite3
from pathlib import Path

import pytest

from scripts.checks.audit_data_parity import (
    _load_sqlite_records,
    _require_sqlite_columns,
    build_report,
    main,
    render_report,
)


def _make_sqlite(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE entities (
                id TEXT PRIMARY KEY, type TEXT, name TEXT, summary TEXT,
                description TEXT, placeId TEXT, confidence REAL,
                season TEXT, attributes TEXT, source TEXT, images TEXT,
                coordinates TEXT, area TEXT, level TEXT, parentId TEXT,
                legacyArea TEXT, updatedAt TEXT, created_at TEXT,
                status TEXT, verified INTEGER, address TEXT, phone TEXT,
                website TEXT, hours TEXT, price_range TEXT,
                sub_category TEXT, best_time TEXT, highlight TEXT,
                revision INTEGER
            );
            CREATE TABLE relationships (from_id TEXT, to_id TEXT, type TEXT);
            CREATE TABLE itineraries (
                id TEXT PRIMARY KEY, title TEXT, area TEXT, areas TEXT,
                duration TEXT, summary TEXT, stops TEXT, created_at TEXT
            );
            """
        )
        conn.executemany(
            "INSERT INTO entities (id, type, name, summary, attributes, source, images, coordinates, verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("a", "place", "A", "A summary", "{}", "[]", "[]", "[10.0, 106.0]", 1),
                ("b", "place", "B", "B summary", "{}", "[]", "[]", "[10.1, 106.1]", 1),
            ],
        )
        conn.execute("INSERT INTO relationships VALUES ('a', 'b', 'near')")
        conn.execute(
            "INSERT INTO itineraries VALUES ('it-1', 'Trip', 'vinh-long', '[]', '1 day', 'Summary', '[]', '2026-09-22')"
        )


def _make_json(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "entities": [
                    {"id": "a", "type": "place", "name": "A", "summary": "A summary", "attributes": {}, "source": [], "images": [], "coordinates": [10.0, 106.0], "verified": 1},
                    {"id": "b", "type": "place", "name": "B", "summary": "B summary", "attributes": {}, "source": [], "images": [], "coordinates": [10.1, 106.1], "verified": 1},
                ],
                "relationships": [
                    {"from": "a", "to": "b", "type": "related_to"},
                    {"from": "a", "to": "b", "type": "related_to"},
                ],
                "itineraries": [
                    {"id": "it-1", "title": "Trip", "area": "vinh-long", "areas": [], "duration": "1 day", "summary": "Summary", "stops": [], "created_at": "2026-09-22"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_paths(tmp_path: Path) -> tuple[Path, Path]:
    sqlite_path = tmp_path / "fixture.db"
    json_path = tmp_path / "fixture.json"
    _make_sqlite(sqlite_path)
    _make_json(json_path)
    return sqlite_path, json_path


@pytest.mark.parametrize(
    ("table", "json_fields", "expected_message"),
    [
        ("entities", (), "SQLite entities contain a missing or invalid id"),
        ("itineraries", (), "SQLite itineraries contain a missing or invalid id"),
    ],
)
def test_sqlite_record_validation_preserves_invalid_id_messages(
    table: str,
    json_fields: tuple[str, ...],
    expected_message: str,
) -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.row_factory = sqlite3.Row
        connection.execute(f"CREATE TABLE {table} (id TEXT)")
        connection.execute(f"INSERT INTO {table} VALUES (NULL)")

        with pytest.raises(ValueError) as exc_info:
            _load_sqlite_records(connection, table, json_fields, [])

    assert str(exc_info.value) == expected_message


@pytest.mark.parametrize("table", ["entities", "itineraries"])
def test_sqlite_record_validation_preserves_duplicate_id_messages(table: str) -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.row_factory = sqlite3.Row
        connection.execute(f"CREATE TABLE {table} (id TEXT)")
        connection.executemany(f"INSERT INTO {table} VALUES (?)", [("duplicate",), ("duplicate",)])

        with pytest.raises(ValueError) as exc_info:
            _load_sqlite_records(connection, table, (), [])

    assert str(exc_info.value) == f"SQLite {table} contain duplicate id: duplicate"


def test_sqlite_record_loader_rejects_nonapproved_table_identifier() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE relationships (id TEXT)")

        with pytest.raises(ValueError) as exc_info:
            _load_sqlite_records(connection, "relationships", (), [])

    assert str(exc_info.value) == "Unsupported SQLite record table: 'relationships'"


def test_sqlite_schema_helper_rejects_nonapproved_table_identifier() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE unexpected (id TEXT)")

        with pytest.raises(ValueError) as exc_info:
            _require_sqlite_columns(connection, "unexpected", {"id"})

    assert str(exc_info.value) == "Unsupported SQLite table: 'unexpected'"


REPORT_KEYS = {
    "schemaVersion",
    "status",
    "inputs",
    "counts",
    "entityDiff",
    "relationshipDiff",
    "itineraryDiff",
    "provenanceDiff",
    "errors",
}


def test_complete_report_uses_the_versioned_schema_and_derived_counts(tmp_path: Path) -> None:
    sqlite_path, json_path = _fixture_paths(tmp_path)

    report = build_report(sqlite_path, json_path)

    assert set(report) == REPORT_KEYS
    assert report["schemaVersion"] == 1
    assert report["inputs"]["sqlite"]["sha256"] == _sha256(sqlite_path)
    assert report["inputs"]["json"]["sha256"] == _sha256(json_path)
    assert report["counts"] == {
        "sqlite": {
            "entityRows": 2,
            "relationshipRows": 1,
            "relationshipUniqueTriples": 1,
            "itineraries": 1,
        },
        "json": {
            "entityRows": 2,
            "relationshipRows": 2,
            "relationshipUniqueTriples": 1,
            "itineraries": 1,
        },
    }
    assert report["errors"] == []


def test_default_production_input_paths_are_workspace_stable() -> None:
    report = build_report(Path("agent/data/vinhlong360.db"), Path("web/data.json"))

    assert report["inputs"]["sqlite"]["path"] == "agent/data/vinhlong360.db"
    assert report["inputs"]["json"]["path"] == "web/data.json"


def test_error_report_retains_the_versioned_schema_with_safe_empty_sections(tmp_path: Path) -> None:
    report = build_report(tmp_path / "missing.db", tmp_path / "missing.json")

    assert set(report) == REPORT_KEYS
    assert report["schemaVersion"] == 1
    assert report["status"] == "error"
    assert report["counts"] == {
        "sqlite": {
            "entityRows": 0,
            "relationshipRows": 0,
            "relationshipUniqueTriples": 0,
            "itineraries": 0,
        },
        "json": {
            "entityRows": 0,
            "relationshipRows": 0,
            "relationshipUniqueTriples": 0,
            "itineraries": 0,
        },
    }
    assert report["entityDiff"]["fieldDifferences"] == []
    assert report["relationshipDiff"]["sqliteOnlyTriples"] == []
    assert report["itineraryDiff"]["fieldDifferences"] == []
    assert report["provenanceDiff"]["fieldDifferences"] == []
    assert report["errors"]


def test_reports_type_substitution_and_duplicate_json_triple(tmp_path: Path) -> None:
    sqlite_path, json_path = _fixture_paths(tmp_path)

    report = build_report(sqlite_path, json_path)

    assert report["status"] == "drift"
    assert report["relationshipDiff"]["duplicateJsonTriples"] == [
        {"from": "a", "to": "b", "type": "related_to", "extraRows": 1}
    ]
    assert report["relationshipDiff"]["typeSubstitutions"] == [
        {
            "from": "a",
            "to": "b",
            "sqliteTypes": ["near"],
            "jsonTypes": ["related_to"],
        }
    ]


def test_rendering_and_inputs_are_deterministic_and_read_only(tmp_path: Path) -> None:
    sqlite_path, json_path = _fixture_paths(tmp_path)
    before_hashes = (_sha256(sqlite_path), _sha256(json_path))
    before_mtime = sqlite_path.stat().st_mtime_ns

    first = render_report(build_report(sqlite_path, json_path))
    second = render_report(build_report(sqlite_path, json_path))

    assert first.encode("utf-8") == second.encode("utf-8")
    assert (_sha256(sqlite_path), _sha256(json_path)) == before_hashes
    assert sqlite_path.stat().st_mtime_ns == before_mtime


def test_relationship_addition_is_not_reported_as_a_type_substitution(tmp_path: Path) -> None:
    sqlite_path, json_path = _fixture_paths(tmp_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["relationships"] = [
        {"from": "a", "to": "b", "type": "near"},
        {"from": "a", "to": "b", "type": "related_to"},
    ]
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    report = build_report(sqlite_path, json_path)

    assert report["relationshipDiff"]["typeSubstitutions"] == []


def test_relationship_removal_is_not_reported_as_a_type_substitution(tmp_path: Path) -> None:
    sqlite_path, json_path = _fixture_paths(tmp_path)
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute("INSERT INTO relationships VALUES ('a', 'b', 'contains')")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["relationships"] = [{"from": "a", "to": "b", "type": "contains"}]
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    report = build_report(sqlite_path, json_path)

    assert report["relationshipDiff"]["typeSubstitutions"] == []


def test_relationship_mixed_shared_and_changed_types_reports_only_deltas(tmp_path: Path) -> None:
    sqlite_path, json_path = _fixture_paths(tmp_path)
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute("INSERT INTO relationships VALUES ('a', 'b', 'contains')")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["relationships"] = [
        {"from": "a", "to": "b", "type": "contains"},
        {"from": "a", "to": "b", "type": "related_to"},
    ]
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    report = build_report(sqlite_path, json_path)

    assert report["relationshipDiff"]["typeSubstitutions"] == [
        {"from": "a", "to": "b", "sqliteTypes": ["near"], "jsonTypes": ["related_to"]}
    ]


@pytest.mark.parametrize("output_name", ["fixture.db", "fixture.json"])
def test_cli_refuses_output_that_is_a_protected_input(tmp_path: Path, output_name: str) -> None:
    sqlite_path, json_path = _fixture_paths(tmp_path)
    before_hashes = (_sha256(sqlite_path), _sha256(json_path))

    exit_code = main(
        ["--sqlite", str(sqlite_path), "--json", str(json_path), "--output", str(tmp_path / output_name)]
    )

    assert exit_code == 2
    assert (_sha256(sqlite_path), _sha256(json_path)) == before_hashes


def test_cli_refuses_symlink_or_hardlink_to_protected_input(tmp_path: Path) -> None:
    sqlite_path, json_path = _fixture_paths(tmp_path)
    alias_path = tmp_path / "fixture-alias.db"
    try:
        alias_path.symlink_to(sqlite_path)
    except OSError:
        try:
            os.link(sqlite_path, alias_path)
        except OSError:
            pytest.skip("Symlinks and hardlinks are unavailable on this host")
    before_hashes = (_sha256(sqlite_path), _sha256(json_path))

    exit_code = main(["--sqlite", str(sqlite_path), "--json", str(json_path), "--output", str(alias_path)])

    assert exit_code == 2
    assert (_sha256(sqlite_path), _sha256(json_path)) == before_hashes


@pytest.mark.parametrize("collection", ["entities", "itineraries"])
def test_missing_json_ids_produce_error_reports_and_exit_code_two(tmp_path: Path, collection: str) -> None:
    sqlite_path, json_path = _fixture_paths(tmp_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    del payload[collection][0]["id"]
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    report = build_report(sqlite_path, json_path)

    assert report["status"] == "error"
    assert main(["--sqlite", str(sqlite_path), "--json", str(json_path)]) == 2


@pytest.mark.parametrize("collection", ["entities", "itineraries"])
def test_duplicate_json_ids_produce_error_reports_and_exit_code_two(tmp_path: Path, collection: str) -> None:
    sqlite_path, json_path = _fixture_paths(tmp_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload[collection].append(dict(payload[collection][0]))
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    report = build_report(sqlite_path, json_path)

    assert report["status"] == "error"
    assert main(["--sqlite", str(sqlite_path), "--json", str(json_path)]) == 2


def test_missing_sqlite_id_column_produces_error_report_and_exit_code_two(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "missing-id.db"
    json_path = tmp_path / "fixture.json"
    with sqlite3.connect(sqlite_path) as conn:
        conn.executescript(
            """
            CREATE TABLE entities (name TEXT);
            CREATE TABLE relationships (from_id TEXT, to_id TEXT, type TEXT);
            CREATE TABLE itineraries (id TEXT);
            """
        )
    _make_json(json_path)

    report = build_report(sqlite_path, json_path)

    assert report["status"] == "error"
    assert main(["--sqlite", str(sqlite_path), "--json", str(json_path)]) == 2


def test_missing_input_returns_error_report_and_exit_code_two(tmp_path: Path) -> None:
    json_path = tmp_path / "missing.json"

    report = build_report(tmp_path / "missing.db", json_path)

    assert report["status"] == "error"
    assert main(["--sqlite", str(tmp_path / "missing.db"), "--json", str(json_path)]) == 2


def test_cli_normal_and_strict_modes_have_expected_exit_codes(tmp_path: Path) -> None:
    sqlite_path, json_path = _fixture_paths(tmp_path)

    assert main(["--sqlite", str(sqlite_path), "--json", str(json_path)]) == 0
    assert main(["--sqlite", str(sqlite_path), "--json", str(json_path), "--fail-on-drift"]) == 1
