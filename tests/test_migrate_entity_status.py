from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import migrate_entity_status as migration
from scripts.postgres_target import (
    canonical_json_bytes,
    sha256_bytes,
    target_fingerprint,
)


IDENTITY = {
    "database": "vl360",
    "server_addr": "10.0.0.3",
    "server_port": 5432,
    "server_version_num": 160004,
}
COLUMNS = [
    ("attributes", "jsonb", "YES"),
    ("id", "text", "NO"),
    ("source", "jsonb", "YES"),
    ("status", "text", "YES"),
    ("type", "text", "NO"),
    ("verified", "integer", "YES"),
]
CREATED_AT = "2026-07-15T02:03:04Z"
REVISION = "6a9f280b07445eaf51e9ebdb7738e1cb14361aa0"


def _row(
    entity_id: str,
    *,
    entity_type: object = "attraction",
    status: object = None,
    verified: object = 1,
    source: object = "https://example.org/source",
    attributes: object = None,
) -> dict[str, object]:
    return {
        "id": entity_id,
        "type": entity_type,
        "status": status,
        "verified": verified,
        "attributes": {} if attributes is None else attributes,
        "source": source,
    }


def _fixture_rows() -> list[dict[str, object]]:
    return [
        _row("b"),
        _row("a"),
        _row("place", entity_type="place"),
        _row("no-source", source=[]),
        _row("existing", status="verified"),
    ]


def _build(rows=None, columns=None) -> dict[str, object]:
    return migration.build_plan(
        rows=_fixture_rows() if rows is None else rows,
        identity=IDENTITY,
        schema_columns=COLUMNS if columns is None else columns,
        created_at=CREATED_AT,
        tool_source_revision=REVISION,
    )


def test_public_constants_define_the_publication_plan_contract() -> None:
    assert migration.PLAN_SCHEMA == "vinhlong360-entity-status-plan-v1"
    assert migration.APPLY_SCHEMA == "vinhlong360-entity-status-apply-v1"
    assert migration.ROLLBACK_SCHEMA == "vinhlong360-entity-status-rollback-v1"
    assert migration.MAX_PLAN_AGE_SECONDS == 86400
    assert migration.LOCK_NAME == "vinhlong360:entity-status:published-v1"
    assert migration.REQUIRED_ENTITY_COLUMNS == {
        "id",
        "type",
        "status",
        "verified",
        "attributes",
        "source",
    }
    assert issubclass(migration.MigrationRefusal, RuntimeError)


def test_build_plan_has_canonical_candidates_exclusions_and_accounting() -> None:
    plan = _build()

    assert plan == {
        "schema": migration.PLAN_SCHEMA,
        "policy_revision": "published-v1",
        "created_at": CREATED_AT,
        "max_age_seconds": migration.MAX_PLAN_AGE_SECONDS,
        "tool_source_revision": REVISION,
        "target_fingerprint": target_fingerprint(IDENTITY),
        "database_identity": IDENTITY,
        "schema_fingerprint": migration.schema_fingerprint(COLUMNS),
        "schema_columns": [
            {"name": "attributes", "type": "jsonb", "nullable": "YES"},
            {"name": "id", "type": "text", "nullable": "NO"},
            {"name": "source", "type": "jsonb", "nullable": "YES"},
            {"name": "status", "type": "text", "nullable": "YES"},
            {"name": "type", "type": "text", "nullable": "NO"},
            {"name": "verified", "type": "integer", "nullable": "YES"},
        ],
        "candidate_ids": ["a", "b"],
        "candidate_count": 2,
        "candidate_sha256": migration.candidate_id_hash(["a", "b"]),
        "reviewed_exclusions": sorted(migration.PUBLISHED_V1_EXCLUSIONS),
        "exclusion_counts": {
            "entity-type-not-allowlisted": 1,
            "external-source-missing": 1,
            "status-not-null": 1,
        },
        "status_groups": {"<null>": 4, "verified": 1},
        "expected_before": {"published": 0, "null": 4},
        "expected_after": {"published": 2, "null": 2},
    }


def test_build_plan_is_deterministic_across_snapshot_and_schema_order() -> None:
    forward = _build()
    reverse = _build(rows=list(reversed(_fixture_rows())), columns=list(reversed(COLUMNS)))

    assert canonical_json_bytes(forward) == canonical_json_bytes(reverse)
    assert reverse["candidate_ids"] == ["a", "b"]
    assert [column["name"] for column in reverse["schema_columns"]] == [
        "attributes",
        "id",
        "source",
        "status",
        "type",
        "verified",
    ]


def test_build_plan_refuses_duplicate_entity_ids() -> None:
    with pytest.raises(migration.MigrationRefusal, match="duplicate entity id: duplicate"):
        _build(rows=[_row("duplicate"), _row("duplicate")])


def test_build_plan_refuses_zero_candidates() -> None:
    with pytest.raises(migration.MigrationRefusal) as error:
        _build(rows=[_row("already-reviewed", status="verified")])

    assert str(error.value) == "publication plan has zero candidates"


def test_build_plan_refuses_missing_required_columns_in_sorted_order() -> None:
    columns = [column for column in COLUMNS if column[0] not in {"attributes", "id"}]

    with pytest.raises(
        migration.MigrationRefusal,
        match="entities schema missing required columns: attributes, id",
    ):
        _build(columns=columns)


def test_build_plan_refuses_non_dictionary_rows() -> None:
    with pytest.raises(migration.MigrationRefusal, match="entity row must be a dict"):
        _build(rows=[list(_row("not-a-dict").items())])


class _EntityId(str):
    pass


@pytest.mark.parametrize("entity_id", ["", 7, _EntityId("subclass")])
def test_build_plan_refuses_invalid_or_empty_exact_string_ids(entity_id: object) -> None:
    with pytest.raises(migration.MigrationRefusal, match="entity id"):
        _build(rows=[_row(entity_id)])  # type: ignore[arg-type]


def test_build_plan_tracks_status_groups_and_before_after_edges() -> None:
    rows = [
        _row("candidate"),
        _row("published", status="published"),
        _row("numeric", status=7),
    ]

    plan = _build(rows=rows)

    assert plan["status_groups"] == {
        "<int>:7": 1,
        "<null>": 1,
        "published": 1,
    }
    assert plan["expected_before"] == {"published": 1, "null": 1}
    assert plan["expected_after"] == {"published": 2, "null": 0}
    assert plan["exclusion_counts"] == {"status-not-null": 2}


def test_build_plan_does_not_mutate_input_rows_or_columns() -> None:
    rows = _fixture_rows()
    rows[0]["attributes"] = {"nested": ["unchanged"]}
    columns = list(reversed(COLUMNS))
    original_rows = copy.deepcopy(rows)
    original_columns = copy.deepcopy(columns)

    _build(rows=rows, columns=columns)

    assert rows == original_rows
    assert columns == original_columns


def test_build_plan_preserves_complete_identity_without_mutating_input() -> None:
    identity = {
        **IDENTITY,
        "cluster_name": "primary-vl360",
        "metadata": {"region": "mekong"},
    }
    original = copy.deepcopy(identity)

    plan = migration.build_plan(
        rows=_fixture_rows(),
        identity=identity,
        schema_columns=COLUMNS,
        created_at=CREATED_AT,
        tool_source_revision=REVISION,
    )

    assert plan["database_identity"] == identity
    assert plan["database_identity"] is not identity
    assert plan["target_fingerprint"] == target_fingerprint(identity)
    assert identity == original


def test_candidate_schema_and_target_hashes_are_canonical_and_deterministic() -> None:
    candidate_ids = ["a", "b", "V\u0129nh Long"]
    normalized_columns = [
        {"name": name, "type": data_type, "nullable": nullable}
        for name, data_type, nullable in sorted(COLUMNS)
    ]

    assert migration.candidate_id_hash(candidate_ids) == hashlib.sha256(
        canonical_json_bytes(candidate_ids)
    ).hexdigest()
    assert migration.schema_fingerprint(COLUMNS) == migration.schema_fingerprint(
        list(reversed(COLUMNS))
    )
    assert migration.schema_fingerprint(COLUMNS) == hashlib.sha256(
        canonical_json_bytes(normalized_columns)
    ).hexdigest()
    assert target_fingerprint(dict(reversed(list(IDENTITY.items())))) == target_fingerprint(
        IDENTITY
    )


def test_write_and_load_immutable_json_preserve_unicode_payload_and_raw_digest(
    tmp_path: Path,
) -> None:
    path = tmp_path / "nested" / "plan.json"
    value = {"z": 1, "place": "V\u0129nh Long"}

    digest = migration.write_immutable_json(path, value)
    loaded, loaded_digest = migration.load_immutable_json(path)

    assert path.read_bytes() == canonical_json_bytes(value)
    assert loaded == value
    assert digest == loaded_digest == hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        migration.write_immutable_json(path, {"replacement": True})
    assert path.read_bytes() == canonical_json_bytes(value)


def test_write_immutable_json_preflights_serialization_without_false_artifact(
    tmp_path: Path,
) -> None:
    path = tmp_path / "report" / "plan.json"

    with pytest.raises(TypeError):
        migration.write_immutable_json(path, {"bad": object()})

    assert not path.exists()


def test_write_immutable_json_does_not_remove_foreign_replacement_on_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "report" / "plan.json"
    foreign = b"other-process"

    def replace_before_failure(destination: Path, _value: object) -> None:
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b"owned-partial")
        destination.unlink()
        destination.write_bytes(foreign)
        raise OSError("simulated write failure")

    monkeypatch.setattr(migration, "write_exclusive", replace_before_failure)

    try:
        with pytest.raises(OSError, match="simulated write failure"):
            migration.write_immutable_json(path, {"valid": True})
    finally:
        assert path.read_bytes() == foreign


def test_write_immutable_json_returns_precomputed_digest_without_path_hashing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "report" / "plan.json"
    value = {"place": "V\u0129nh Long", "valid": True}

    def fail_path_hash(_path: Path) -> str:
        pytest.fail("immutable digest was recomputed from the final path")

    monkeypatch.setattr(migration, "sha256_file", fail_path_hash, raising=False)

    digest = migration.write_immutable_json(path, value)

    assert digest == hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def test_write_immutable_json_never_removes_preexisting_file_on_exclusive_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "plan.json"
    original = b"preexisting-report"
    path.write_bytes(original)

    def refuse_existing(_path: Path, _value: object) -> None:
        raise FileExistsError("already exists")

    monkeypatch.setattr(migration, "write_exclusive", refuse_existing)

    with pytest.raises(FileExistsError):
        migration.write_immutable_json(path, {"replacement": True})

    assert path.read_bytes() == original


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"\xff", "UTF-8"),
        (b"{broken\n", "JSON"),
        (b"[1,2,3]\n", "object"),
    ],
)
def test_load_immutable_json_refuses_invalid_payloads_without_echoing_content(
    tmp_path: Path,
    payload: bytes,
    message: str,
) -> None:
    path = tmp_path / "plan.json"
    path.write_bytes(payload)

    with pytest.raises(migration.MigrationRefusal, match=message) as error:
        migration.load_immutable_json(path)

    decoded_payload = payload.decode("utf-8", errors="ignore").strip()
    if decoded_payload:
        assert decoded_payload not in str(error.value)


def test_load_immutable_json_returns_a_different_digest_for_altered_raw_bytes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "plan.json"
    path.write_bytes(b'{"a":1}\n')
    first_value, first_digest = migration.load_immutable_json(path)
    path.write_bytes(b'{ "a": 1 }\n')
    second_value, second_digest = migration.load_immutable_json(path)

    assert first_value == second_value == {"a": 1}
    assert first_digest != second_digest


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-07-15T02:03:04Z", datetime(2026, 7, 15, 2, 3, 4, tzinfo=UTC)),
        ("2026-07-15T09:03:04+07:00", datetime(2026, 7, 15, 2, 3, 4, tzinfo=UTC)),
    ],
)
def test_parse_utc_accepts_z_and_normalizes_offsets(
    value: str, expected: datetime
) -> None:
    assert migration.parse_utc(value) == expected


@pytest.mark.parametrize("value", ["not-a-date", "2026-07-15T02:03:04"])
def test_parse_utc_refuses_invalid_or_timezone_naive_values(value: str) -> None:
    with pytest.raises(migration.MigrationRefusal):
        migration.parse_utc(value)


def test_utc_text_requires_timezone_and_normalizes_to_rfc3339_z() -> None:
    bangkok = timezone(timedelta(hours=7))

    assert migration.utc_text(datetime(2026, 7, 15, 9, 3, 4, tzinfo=bangkok)) == CREATED_AT
    with pytest.raises(migration.MigrationRefusal, match="timezone"):
        migration.utc_text(datetime(2026, 7, 15, 2, 3, 4))


@pytest.mark.parametrize(
    "unsafe_args",
    [
        ["plan", "--target", "sqlite", "--database-url-env", "TASK6_DB", "--policy", "published-v1"],
        ["plan", "--target", "pg", "--database-url-env", "DATABASE_URL", "--policy", "published-v1"],
        ["plan", "--target", "pg", "--database-url-env", "TASK6_DB", "--policy", "draft-v1"],
    ],
)
def test_cli_refuses_unsafe_options_before_resolve_import_revision_or_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe_args: list[str],
) -> None:
    report = tmp_path / "forbidden.json"
    monkeypatch.setattr(
        migration,
        "resolve_database_url",
        lambda *_args: pytest.fail("database URL resolved before CLI validation"),
    )
    monkeypatch.setattr(
        migration,
        "_load_psycopg2",
        lambda: pytest.fail("psycopg2 imported before CLI validation"),
    )
    monkeypatch.setattr(
        migration,
        "_source_revision",
        lambda **_kwargs: pytest.fail("revision read before CLI validation"),
    )

    assert migration.main([*unsafe_args, "--report-out", str(report)]) == 1
    assert not report.exists()


def test_cli_refuses_existing_report_before_resolve_import_revision_or_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = tmp_path / "existing.json"
    report.write_text("preserve-me", encoding="utf-8")
    monkeypatch.setattr(
        migration,
        "resolve_database_url",
        lambda *_args: pytest.fail("database URL resolved for existing report"),
    )
    monkeypatch.setattr(
        migration,
        "_load_psycopg2",
        lambda: pytest.fail("psycopg2 imported for existing report"),
    )
    monkeypatch.setattr(
        migration,
        "_source_revision",
        lambda **_kwargs: pytest.fail("revision read for existing report"),
    )

    assert migration.main(
        [
            "plan",
            "--target",
            "pg",
            "--database-url-env",
            "TASK6_DB",
            "--policy",
            "published-v1",
            "--report-out",
            str(report),
        ]
    ) == 1
    assert report.read_text(encoding="utf-8") == "preserve-me"


class _FakeCursor:
    def __init__(self, *, fail_schema: bool = False) -> None:
        self.fail_schema = fail_schema
        self.queries: list[str] = []
        self.phase = ""
        self.description = None
        self.closed = False

    def execute(self, query: str) -> None:
        normalized = " ".join(query.split())
        self.queries.append(normalized)
        if "current_database()" in normalized:
            self.phase = "identity"
            return
        if "information_schema.columns" in normalized:
            if self.fail_schema:
                raise RuntimeError("snapshot failed with should-not-leak-secret")
            self.phase = "schema"
            return
        if normalized == "SELECT * FROM public.entities ORDER BY id":
            self.phase = "rows"
            self.description = [
                ("id",),
                ("type",),
                ("status",),
                ("verified",),
                ("attributes",),
                ("source",),
            ]
            return
        raise AssertionError(f"unexpected query: {normalized}")

    def fetchone(self):
        assert self.phase == "identity"
        return ("vl360", "10.0.0.3", 5432, 160004)

    def fetchall(self):
        if self.phase == "schema":
            return COLUMNS
        assert self.phase == "rows"
        return [
            ("b", "attraction", None, 1, {}, "https://example.org/b"),
            ("a", "attraction", None, 1, {}, "https://example.org/a"),
            ("place", "place", None, 1, {}, "https://example.org/place"),
        ]

    def close(self) -> None:
        self.closed = True


class _FakeConnection:
    def __init__(self, *, fail_schema: bool = False) -> None:
        self.fake_cursor = _FakeCursor(fail_schema=fail_schema)
        self.session_options: dict[str, object] | None = None
        self.rollback_count = 0
        self.closed = False

    def set_session(self, **options: object) -> None:
        self.session_options = options

    def cursor(self) -> _FakeCursor:
        return self.fake_cursor

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        self.closed = True


def _valid_cli_args(report: Path) -> list[str]:
    return [
        "plan",
        "--target",
        "pg",
        "--database-url-env",
        "TASK6_DATABASE_URL",
        "--policy",
        "published-v1",
        "--report-out",
        str(report),
    ]


def test_cli_reads_one_readonly_repeatable_snapshot_and_writes_immutable_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = tmp_path / "reports" / "plan.json"
    secret = "publication-secret"
    database_url = f"postgresql://planner:{secret}@db.example/vl360"
    connection = _FakeConnection()
    events: list[tuple[str, object]] = []

    def resolve(environment_name: str) -> str:
        events.append(("resolve", environment_name))
        return database_url

    def connect(value: str) -> _FakeConnection:
        events.append(("connect", value))
        return connection

    monkeypatch.setattr(migration, "resolve_database_url", resolve)
    monkeypatch.setattr(
        migration,
        "_load_psycopg2",
        lambda: SimpleNamespace(connect=connect),
    )
    monkeypatch.setenv("VINHLONG360_RELEASE_REVISION", REVISION)

    assert migration.main(_valid_cli_args(report)) == 0

    plan = json.loads(report.read_text(encoding="utf-8"))
    assert events == [
        ("resolve", "TASK6_DATABASE_URL"),
        ("connect", database_url),
    ]
    assert connection.session_options == {
        "isolation_level": "REPEATABLE READ",
        "readonly": True,
        "autocommit": False,
    }
    assert connection.fake_cursor.queries[0].startswith("SELECT current_database()")
    assert "FROM information_schema.columns" in connection.fake_cursor.queries[1]
    assert "table_schema = 'public'" in connection.fake_cursor.queries[1]
    assert "table_name = 'entities'" in connection.fake_cursor.queries[1]
    assert connection.fake_cursor.queries[1].endswith("ORDER BY ordinal_position")
    assert connection.fake_cursor.queries[2] == "SELECT * FROM public.entities ORDER BY id"
    assert connection.fake_cursor.closed is True
    assert connection.rollback_count == 1
    assert connection.closed is True
    assert plan["database_identity"] == IDENTITY
    assert plan["schema_columns"] == [
        {"name": name, "type": data_type, "nullable": nullable}
        for name, data_type, nullable in COLUMNS
    ]
    assert plan["candidate_ids"] == ["a", "b"]
    assert report.read_bytes() == canonical_json_bytes(plan)

    captured = capsys.readouterr()
    evidence = json.loads(captured.out)
    assert evidence == {
        "candidate_count": 2,
        "report_path": str(report),
        "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "target_fingerprint": target_fingerprint(IDENTITY),
    }
    assert captured.err == ""
    assert secret not in captured.out
    assert database_url not in captured.out
    assert "place" not in captured.out

    with pytest.raises(FileExistsError):
        migration.write_immutable_json(report, {"replacement": True})


def test_cli_snapshot_failure_rolls_back_closes_and_writes_no_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = tmp_path / "plan.json"
    secret = "connection-secret"
    connection = _FakeConnection(fail_schema=True)
    monkeypatch.setattr(
        migration,
        "resolve_database_url",
        lambda _name: f"postgresql://planner:{secret}@db.example/vl360",
    )
    monkeypatch.setattr(
        migration,
        "_load_psycopg2",
        lambda: SimpleNamespace(connect=lambda _url: connection),
    )
    monkeypatch.setenv("VINHLONG360_RELEASE_REVISION", REVISION)

    assert migration.main(_valid_cli_args(report)) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert secret not in captured.err
    assert "should-not-leak-secret" not in captured.err
    assert not report.exists()
    assert connection.fake_cursor.closed is True
    assert connection.rollback_count == 1
    assert connection.closed is True


def test_source_revision_prefers_nonempty_release_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VINHLONG360_RELEASE_REVISION", f"  {REVISION}  ")

    revision = migration._source_revision(
        runner=lambda *_args, **_kwargs: pytest.fail("git ran despite release revision")
    )

    assert revision == REVISION


def test_source_revision_falls_back_to_safe_git_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []
    monkeypatch.setenv("VINHLONG360_RELEASE_REVISION", "  ")

    def runner(command: list[str], **kwargs: object):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, f"{REVISION}\n", "")

    assert migration._source_revision(runner=runner) == REVISION
    assert calls == [
        (
            ["git", "rev-parse", "HEAD"],
            {
                "cwd": migration.ROOT,
                "check": False,
                "capture_output": True,
                "text": True,
            },
        )
    ]


@pytest.mark.parametrize(
    "result",
    [
        subprocess.CompletedProcess(["git"], 1, "", "fatal: secret detail"),
        subprocess.CompletedProcess(["git"], 0, "  \n", ""),
    ],
)
def test_source_revision_refuses_git_failure_or_empty_output(
    monkeypatch: pytest.MonkeyPatch,
    result: subprocess.CompletedProcess[str],
) -> None:
    monkeypatch.delenv("VINHLONG360_RELEASE_REVISION", raising=False)

    with pytest.raises(migration.MigrationRefusal, match="source revision") as error:
        migration._source_revision(runner=lambda *_args, **_kwargs: result)

    assert "secret detail" not in str(error.value)


APPLY_NOW = datetime(2026, 7, 15, 2, 10, tzinfo=UTC)


RESTORE_LISTING = """;
; Archive created at 2026-07-15 02:00:00 UTC
;
1; 1259 100 TABLE public entities owner
2; 1259 101 TABLE public entity_changes owner
"""


def _artifact_sha(value: object) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _valid_apply_plan(rows=None) -> dict[str, object]:
    return migration.build_plan(
        rows=[_row("a"), _row("b")] if rows is None else rows,
        identity=IDENTITY,
        schema_columns=COLUMNS,
        created_at="2026-07-15T02:00:00Z",
        tool_source_revision=REVISION,
    )


def _valid_backup(tmp_path: Path, target: str) -> migration.BackupEvidence:
    root = tmp_path / "backup"
    root.mkdir()
    artifact = root / "postgres.dump"
    artifact.write_bytes(b"PGDMP-test")
    manifest = {
        "schema": "vinhlong360-pg-backup-v1",
        "target": "pg",
        "target_fingerprint": target,
        "database_identity": dict(IDENTITY),
        "started_at": "2026-07-15T02:00:00Z",
        "completed_at": "2026-07-15T02:00:01Z",
        "max_age_seconds": migration.MAX_BACKUP_AGE_SECONDS,
        "tools": {
            "pg_dump": "pg_dump (PostgreSQL) 16.4",
            "pg_restore": "pg_restore (PostgreSQL) 16.4",
        },
        "artifact": {
            "path": artifact.name,
            "size": artifact.stat().st_size,
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        },
        "validation": {
            "pg_restore_list": True,
            "required_tables": ["entities", "entity_changes"],
            "listing_sha256": hashlib.sha256(
                RESTORE_LISTING.encode("utf-8")
            ).hexdigest(),
        },
        "policy_revision": "published-v1",
    }
    return migration.BackupEvidence(
        manifest=manifest,
        manifest_sha256=_artifact_sha(manifest),
        artifact_root=root,
    )


class ApplyFakeStore:
    def __init__(self, rows, *, identity=IDENTITY, columns=COLUMNS) -> None:
        self.rows = {row["id"]: dict(row) for row in rows}
        self.identity = identity
        self.columns = columns
        self.locked: str | None = None
        self.audit: list[dict[str, str]] = []
        self.updated_return: list[str] | None = None
        self.events: list[str] = []

    def acquire_lock(self, name: str) -> None:
        self.events.append("lock")
        self.locked = name

    def target_identity(self):
        self.events.append("identity")
        return self.identity

    def schema_columns(self):
        self.events.append("schema")
        return self.columns

    def rows_for_update(self, ids):
        self.events.append("rows")
        return [dict(self.rows[entity_id]) for entity_id in ids if entity_id in self.rows]

    def audit_rows(self, actor: str):
        self.events.append("audit-read")
        return [dict(row) for row in self.audit if row["actor"] == actor]

    def status_counts(self):
        self.events.append("counts")
        return {
            "published": sum(
                row["status"] == "published" for row in self.rows.values()
            ),
            "null": sum(row["status"] is None for row in self.rows.values()),
        }

    def update_to_published(self, ids):
        self.events.append("update")
        changed = []
        for entity_id in ids:
            if self.rows[entity_id]["status"] is None:
                self.rows[entity_id]["status"] = "published"
                changed.append(entity_id)
        return changed if self.updated_return is None else self.updated_return

    def insert_status_audit(self, ids, actor, old_value, new_value):
        self.events.append("audit-write")
        for entity_id in ids:
            self.audit.append(
                {
                    "entity_id": entity_id,
                    "field": "status",
                    "old_value": old_value,
                    "new_value": new_value,
                    "actor": actor,
                }
            )


def _restore_ok(_artifact: Path) -> str:
    return hashlib.sha256(RESTORE_LISTING.encode("utf-8")).hexdigest()


def _apply_now() -> datetime:
    return APPLY_NOW


def _apply(store: ApplyFakeStore, plan, backup, *, clock=_apply_now):
    return migration.apply_plan(
        store,
        plan,
        plan_sha256=_artifact_sha(plan),
        backup=backup,
        confirm_target=plan["target_fingerprint"],
        now=APPLY_NOW,
        restore_validator=_restore_ok,
        clock=clock,
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema", "wrong", "plan schema"),
        ("policy_revision", "wrong", "plan policy"),
        ("max_age_seconds", True, "plan max age"),
        ("max_age_seconds", "86400", "plan max age"),
        ("max_age_seconds", 0, "plan max age"),
        ("candidate_count", True, "candidate count"),
        ("candidate_sha256", "0" * 64, "candidate hash"),
    ],
)
def test_apply_refuses_malformed_plan_before_store(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    plan = _valid_apply_plan()
    plan[field] = value
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = ApplyFakeStore([_row("a"), _row("b")])

    with pytest.raises(migration.MigrationRefusal, match=message):
        migration.apply_plan(
            store,
            plan,
            plan_sha256=_artifact_sha(plan),
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=APPLY_NOW,
            restore_validator=_restore_ok,
        )

    assert store.events == []


def test_apply_refuses_plan_confirmation_target_age_and_count_algebra_offline(
    tmp_path: Path,
) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = ApplyFakeStore([_row("a"), _row("b")])

    with pytest.raises(migration.MigrationRefusal, match="plan SHA-256 confirmation"):
        migration.apply_plan(
            store,
            plan,
            plan_sha256="0" * 64,
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=APPLY_NOW,
            restore_validator=_restore_ok,
        )
    with pytest.raises(migration.MigrationRefusal, match="target confirmation"):
        migration.apply_plan(
            store,
            plan,
            plan_sha256=_artifact_sha(plan),
            backup=backup,
            confirm_target="0" * 64,
            now=APPLY_NOW,
            restore_validator=_restore_ok,
        )
    drift = copy.deepcopy(plan)
    drift["expected_after"]["published"] += 1
    with pytest.raises(migration.MigrationRefusal, match="expected count algebra"):
        migration.apply_plan(
            store,
            drift,
            plan_sha256=_artifact_sha(drift),
            backup=backup,
            confirm_target=drift["target_fingerprint"],
            now=APPLY_NOW,
            restore_validator=_restore_ok,
        )

    assert store.events == []


def test_apply_refuses_future_plan_and_noncanonical_candidate_ids_offline(
    tmp_path: Path,
) -> None:
    future = _valid_apply_plan()
    future["created_at"] = "2026-07-15T02:11:00Z"
    backup = _valid_backup(tmp_path, future["target_fingerprint"])
    store = ApplyFakeStore([_row("a"), _row("b")])

    with pytest.raises(migration.MigrationRefusal, match="plan is stale"):
        migration.apply_plan(
            store,
            future,
            plan_sha256=_artifact_sha(future),
            backup=backup,
            confirm_target=future["target_fingerprint"],
            now=APPLY_NOW,
            restore_validator=_restore_ok,
        )

    reordered = _valid_apply_plan()
    reordered["candidate_ids"] = ["b", "a"]
    reordered["candidate_sha256"] = migration.candidate_id_hash(["b", "a"])
    with pytest.raises(migration.MigrationRefusal, match="not canonical"):
        migration.apply_plan(
            store,
            reordered,
            plan_sha256=_artifact_sha(reordered),
            backup=backup,
            confirm_target=reordered["target_fingerprint"],
            now=APPLY_NOW,
            restore_validator=_restore_ok,
        )
    assert store.events == []


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda manifest: manifest.update(target="sqlite"), "backup target"),
        (lambda manifest: manifest.update(policy_revision="draft-v1"), "backup policy"),
        (lambda manifest: manifest.update(max_age_seconds=True), "backup max age"),
        (lambda manifest: manifest.update(max_age_seconds=7200), "backup max age"),
        (
            lambda manifest: manifest.update(
                started_at="2026-07-14T01:59:59Z",
                completed_at="2026-07-14T02:00:00Z",
            ),
            "backup evidence is stale",
        ),
        (
            lambda manifest: manifest.update(started_at="2026-07-15T02:00:02Z"),
            "backup timestamps",
        ),
    ],
)
def test_backup_validation_refuses_noncanonical_or_stale_evidence(
    tmp_path: Path, mutate, message: str
) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    mutate(backup.manifest)
    backup = migration.BackupEvidence(
        manifest=backup.manifest,
        manifest_sha256=_artifact_sha(backup.manifest),
        artifact_root=backup.artifact_root,
    )

    with pytest.raises(migration.MigrationRefusal, match=message):
        migration.validate_backup_manifest(
            backup,
            expected_target=plan["target_fingerprint"],
            now=APPLY_NOW,
            require_fresh=True,
        )


def test_backup_validation_checks_manifest_identity_size_hash_and_direct_child(
    tmp_path: Path,
) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])

    with pytest.raises(migration.MigrationRefusal, match="manifest hash"):
        migration.validate_backup_manifest(
            migration.BackupEvidence(
                backup.manifest, "0" * 64, backup.artifact_root
            ),
            expected_target=plan["target_fingerprint"],
            now=APPLY_NOW,
            require_fresh=True,
        )

    for artifact_field, value, message in [
        ("size", 999, "artifact size"),
        ("sha256", "0" * 64, "artifact hash"),
        ("path", "../postgres.dump", "artifact path"),
    ]:
        changed = copy.deepcopy(backup.manifest)
        changed["artifact"][artifact_field] = value
        evidence = migration.BackupEvidence(
            changed, _artifact_sha(changed), backup.artifact_root
        )
        with pytest.raises(migration.MigrationRefusal, match=message):
            migration.validate_backup_manifest(
                evidence,
                expected_target=plan["target_fingerprint"],
                now=APPLY_NOW,
                require_fresh=True,
            )


def test_backup_validation_rejects_direct_child_symlink_before_resolve(
    tmp_path: Path,
) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    artifact = backup.artifact_root / "postgres.dump"
    sibling = backup.artifact_root / "real.dump"
    sibling.write_bytes(artifact.read_bytes())
    artifact.unlink()
    try:
        artifact.symlink_to(sibling.name)
    except OSError:
        pytest.skip("symlinks are unavailable on this platform")

    with pytest.raises(migration.MigrationRefusal, match="artifact path"):
        migration.validate_backup_manifest(
            backup,
            expected_target=plan["target_fingerprint"],
            now=APPLY_NOW,
            require_fresh=True,
        )


@pytest.mark.parametrize(
    "listing",
    [
        "1; 0 0 COMMENT public entities owner\n2; 0 0 TABLE public entity_changes owner\n",
        "1; 0 0 ACL public entities owner\n2; 0 0 TABLE public entity_changes owner\n",
        "1; 0 0 FUNCTION public entities owner\n2; 0 0 TABLE public entity_changes owner\n",
        "1; 0 0 TABLE DATA public entities owner\n2; 0 0 TABLE public entity_changes owner\n",
        "1; 0 0 TABLE public entities_archive owner\n2; 0 0 TABLE public entity_changes owner\n",
        "1; 0 0 TABLE private entities owner\n2; 0 0 TABLE public entity_changes owner\n",
    ],
)
def test_restore_validation_requires_exact_public_table_objects(
    tmp_path: Path, listing: str
) -> None:
    artifact = tmp_path / "postgres.dump"
    artifact.write_bytes(b"PGDMP-test")

    def runner(*_args, **_kwargs):
        return subprocess.CompletedProcess([], 0, listing, "")

    with pytest.raises(
        migration.MigrationRefusal, match="missing tables|invalid table objects"
    ):
        migration.validate_restore_artifact(artifact, runner=runner)


def test_restore_validation_returns_listing_hash_and_rejects_command_failure(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "postgres.dump"
    artifact.write_bytes(b"PGDMP-test")
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, RESTORE_LISTING, "")

    assert migration.validate_restore_artifact(artifact, runner=runner) == hashlib.sha256(
        RESTORE_LISTING.encode("utf-8")
    ).hexdigest()
    assert calls == [
        (
            ["pg_restore", "--list", str(artifact)],
            {"check": False, "capture_output": True, "text": True},
        )
    ]

    with pytest.raises(migration.MigrationRefusal, match="revalidation failed"):
        migration.validate_restore_artifact(
            artifact,
            runner=lambda *args, **kwargs: subprocess.CompletedProcess(
                args[0], 1, "", "secret stderr"
            ),
        )


def test_restore_validation_allows_exact_table_data_after_table_definitions(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "postgres.dump"
    artifact.write_bytes(b"PGDMP-test")
    listing = """1; 1259 100 TABLE public entities owner
2; 0 100 TABLE DATA public entities owner
3; 1259 101 TABLE public entity_changes owner
4; 0 101 TABLE DATA public entity_changes owner
"""

    digest = migration.validate_restore_artifact(
        artifact,
        runner=lambda command, **_kwargs: subprocess.CompletedProcess(
            command, 0, listing, ""
        ),
    )

    assert digest == hashlib.sha256(listing.encode("utf-8")).hexdigest()


def test_restore_validation_rejects_wrong_schema_even_with_public_definitions(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "postgres.dump"
    artifact.write_bytes(b"PGDMP-test")
    listing = """1; 1259 100 TABLE public entities owner
2; 1259 101 TABLE public entity_changes owner
3; 1259 102 TABLE private entities owner
"""

    with pytest.raises(migration.MigrationRefusal, match="invalid table objects"):
        migration.validate_restore_artifact(
            artifact,
            runner=lambda command, **_kwargs: subprocess.CompletedProcess(
                command, 0, listing, ""
            ),
        )


def test_restore_validation_rejects_foreign_table_even_with_public_definitions(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "postgres.dump"
    artifact.write_bytes(b"PGDMP-test")
    listing = """1; 1259 100 TABLE public entities owner
2; 1259 101 TABLE public entity_changes owner
3; 1259 102 FOREIGN TABLE public entities owner
"""

    with pytest.raises(migration.MigrationRefusal, match="invalid table objects"):
        migration.validate_restore_artifact(
            artifact,
            runner=lambda command, **_kwargs: subprocess.CompletedProcess(
                command, 0, listing, ""
            ),
        )


@pytest.mark.parametrize(
    "masquerade",
    [
        "3; 0 0 ACL public TABLE entities owner",
        "3; 0 0 COMMENT public TABLE entities owner",
        "3; 1255 102 FUNCTION public entities() owner",
    ],
)
def test_restore_validation_rejects_realistic_masquerade_with_definitions(
    tmp_path: Path, masquerade: str
) -> None:
    artifact = tmp_path / "postgres.dump"
    artifact.write_bytes(b"PGDMP-test")
    listing = (
        "1; 1259 100 TABLE public entities owner\n"
        "2; 1259 101 TABLE public entity_changes owner\n"
        f"{masquerade}\n"
    )

    with pytest.raises(migration.MigrationRefusal, match="invalid table objects"):
        migration.validate_restore_artifact(
            artifact,
            runner=lambda command, **_kwargs: subprocess.CompletedProcess(
                command, 0, listing, ""
            ),
        )


def test_restore_validation_rejects_malformed_table_token_without_definition(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "postgres.dump"
    artifact.write_bytes(b"PGDMP-test")
    listing = (
        "1; 1259 101 TABLE public entity_changes owner\n"
        "2; 0 0 TABLE public TABLE entities owner\n"
    )

    with pytest.raises(migration.MigrationRefusal, match="invalid table objects"):
        migration.validate_restore_artifact(
            artifact,
            runner=lambda command, **_kwargs: subprocess.CompletedProcess(
                command, 0, listing, ""
            ),
        )


def test_apply_revalidates_listing_hash_and_detects_artifact_replacement(
    tmp_path: Path,
) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = ApplyFakeStore([_row("a"), _row("b")])

    with pytest.raises(migration.MigrationRefusal, match="listing hash"):
        migration.apply_plan(
            store,
            plan,
            plan_sha256=_artifact_sha(plan),
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=APPLY_NOW,
            restore_validator=lambda _path: "0" * 64,
        )

    artifact = backup.artifact_root / "postgres.dump"

    def replace(path: Path) -> str:
        assert path != artifact
        path.write_bytes(b"pinned replacement")
        artifact.write_bytes(b"replacement")
        return backup.manifest["validation"]["listing_sha256"]

    with pytest.raises(migration.MigrationRefusal, match="artifact changed"):
        migration.apply_plan(
            store,
            plan,
            plan_sha256=_artifact_sha(plan),
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=APPLY_NOW,
            restore_validator=replace,
        )
    assert artifact.read_bytes() == b"replacement"
    assert store.events == []


@pytest.mark.parametrize("listing_hash", [None, "", "0" * 63, "g" * 64, 7])
def test_apply_requires_exact_restore_listing_digest_before_lock(
    tmp_path: Path, listing_hash: object
) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = ApplyFakeStore([_row("a"), _row("b")])

    with pytest.raises(
        migration.MigrationRefusal, match="restore listing hash is invalid"
    ):
        migration.apply_plan(
            store,
            plan,
            plan_sha256=_artifact_sha(plan),
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=APPLY_NOW,
            restore_validator=lambda _path: listing_hash,
        )

    assert store.events == []


def test_apply_rechecks_locked_state_updates_and_audits_exact_plan_ownership(
    tmp_path: Path,
) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = ApplyFakeStore([_row("a"), _row("b")])

    report = _apply(store, plan, backup)

    assert report["result"] == "applied"
    assert report["candidate_ids"] == report["updated_ids"] == ["a", "b"]
    assert report["candidate_sha256"] == migration.candidate_id_hash(["a", "b"])
    assert store.locked == migration.LOCK_NAME
    actor = migration.audit_actor("apply", _artifact_sha(plan))
    assert store.audit == [
        {
            "entity_id": entity_id,
            "field": "status",
            "old_value": "null",
            "new_value": "published",
            "actor": actor,
        }
        for entity_id in ["a", "b"]
    ]
    assert store.events[:4] == ["lock", "identity", "schema", "rows"]


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([_row("a")], "planned IDs are missing or reordered"),
        ([_row("a", source=[]), _row("b")], "candidate drift"),
        ([_row("a", status="verified"), _row("b")], "candidate status drift"),
    ],
)
def test_apply_refuses_locked_candidate_drift(
    tmp_path: Path, rows, message: str
) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])

    with pytest.raises(migration.MigrationRefusal, match=message):
        _apply(ApplyFakeStore(rows), plan, backup)


def test_apply_refuses_reordered_update_ids_and_post_audit_cardinality_drift(
    tmp_path: Path,
) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    reordered = ApplyFakeStore([_row("a"), _row("b")])
    reordered.updated_return = ["b", "a"]

    with pytest.raises(migration.MigrationRefusal, match="status update IDs drift"):
        _apply(reordered, plan, backup)

    class MissingAuditStore(ApplyFakeStore):
        def insert_status_audit(self, ids, actor, old_value, new_value):
            super().insert_status_audit(ids[:1], actor, old_value, new_value)

    with pytest.raises(migration.MigrationRefusal, match="audit ownership"):
        _apply(MissingAuditStore([_row("a"), _row("b")]), plan, backup)


def test_apply_normalizes_db_row_and_audit_order_before_exact_comparison(
    tmp_path: Path,
) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])

    class CollationStore(ApplyFakeStore):
        def rows_for_update(self, ids):
            return list(reversed(super().rows_for_update(ids)))

        def audit_rows(self, actor: str):
            return list(reversed(super().audit_rows(actor)))

    report = _apply(CollationStore([_row("a"), _row("b")]), plan, backup)

    assert report["result"] == "applied"


def test_apply_idempotency_requires_exact_unique_owned_audits_and_counts(
    tmp_path: Path,
) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = ApplyFakeStore([_row("a"), _row("b")])
    first = _apply(store, plan, backup)
    second = _apply(store, plan, backup)

    assert first["result"] == "applied"
    assert second["result"] == "already-applied"
    assert second["candidate_ids"] == ["a", "b"]
    assert second["updated_ids"] == ["a", "b"]
    assert second["recovery_ready"] is True
    assert second["recovery_contract"] == "apply-audit-exact-v1"
    assert len(store.audit) == 2

    store.audit.append(dict(store.audit[0]))
    with pytest.raises(migration.MigrationRefusal, match="audit ownership"):
        _apply(store, plan, backup)


def test_apply_revalidates_freshness_after_lock_before_mutation(tmp_path: Path) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = ApplyFakeStore([_row("a"), _row("b")])
    after_lock = APPLY_NOW + timedelta(hours=2)

    with pytest.raises(migration.MigrationRefusal, match="backup evidence is stale"):
        _apply(store, plan, backup, clock=lambda: after_lock)

    assert store.locked == migration.LOCK_NAME
    assert "update" not in store.events
    assert store.status_counts() == {"published": 0, "null": 2}


def test_apply_uses_fresh_default_clock_after_lock_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = ApplyFakeStore([_row("a"), _row("b")])
    after_lock = APPLY_NOW + timedelta(hours=2)
    monkeypatch.setattr(migration, "_utc_now", lambda: after_lock)

    with pytest.raises(migration.MigrationRefusal, match="backup evidence is stale"):
        migration.apply_plan(
            store,
            plan,
            plan_sha256=_artifact_sha(plan),
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=APPLY_NOW,
            restore_validator=_restore_ok,
        )

    assert store.locked == migration.LOCK_NAME
    assert "update" not in store.events
    assert store.status_counts() == {"published": 0, "null": 2}


def test_apply_refuses_preexisting_apply_audit_on_null_candidate(tmp_path: Path) -> None:
    plan = _valid_apply_plan(rows=[_row("a")])
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = ApplyFakeStore([_row("a")])
    store.audit.append(
        {
            "entity_id": "a",
            "field": "status",
            "old_value": "null",
            "new_value": "published",
            "actor": migration.audit_actor("apply", _artifact_sha(plan)),
        }
    )

    with pytest.raises(migration.MigrationRefusal, match="pre-existing apply audit"):
        _apply(store, plan, backup)


class StoreCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.description = [("id",), ("status",)]
        self.rows = []
        self.one = (0, 0)

    def execute(self, query: str, params=None) -> None:
        self.calls.append((" ".join(query.split()), params))

    def executemany(self, query: str, params) -> None:
        self.calls.append((" ".join(query.split()), params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.one


def test_postgres_store_uses_qualified_parameterized_sql() -> None:
    cursor = StoreCursor()
    store = migration.PostgresPublicationStore(cursor)

    store.acquire_lock("lock-name")
    cursor.rows = [("a", None)]
    assert store.rows_for_update(["a"]) == [{"id": "a", "status": None}]
    cursor.rows = [("a",)]
    assert store.update_to_published(["a"]) == ["a"]
    store.insert_status_audit(["a"], "actor", "null", "published")

    assert cursor.calls[0] == (
        "SELECT pg_advisory_xact_lock(hashtext(%s))",
        ("lock-name",),
    )
    rows_query, rows_params = cursor.calls[1]
    assert "FROM public.entities" in rows_query
    assert "ORDER BY id FOR UPDATE" in rows_query
    assert rows_params == (["a"],)
    update_query, update_params = cursor.calls[2]
    assert "UPDATE public.entities" in update_query
    assert "RETURNING id" in update_query
    assert update_params == (["a"],)
    audit_query, audit_params = cursor.calls[3]
    assert "INSERT INTO public.entity_changes" in audit_query
    assert audit_params == [("a", "null", "published", "actor")]


def test_postgres_store_and_snapshot_readers_accept_only_safe_qualified_schema() -> None:
    cursor = StoreCursor()
    store = migration.PostgresPublicationStore(cursor, schema="task9_fixture_1")
    store.acquire_lock("lock-name")
    cursor.rows = [("a", None)]
    store.rows_for_update(["a"])
    migration._read_entity_rows(cursor, schema="task9_fixture_1")

    assert "FROM task9_fixture_1.entities" in cursor.calls[1][0]
    assert cursor.calls[2][0] == "SELECT * FROM task9_fixture_1.entities ORDER BY id"
    with pytest.raises(migration.MigrationRefusal, match="schema identifier"):
        migration.PostgresPublicationStore(cursor, schema="public; DROP TABLE entities")
    with pytest.raises(migration.MigrationRefusal, match="schema identifier"):
        migration._read_entity_rows(cursor, schema="../public")


def _apply_cli_args(
    plan_path: Path, manifest_path: Path, report: Path, target: str
) -> list[str]:
    return [
        "apply",
        "--target",
        "pg",
        "--database-url-env",
        "TASK7_DATABASE_URL",
        "--plan",
        str(plan_path),
        "--backup-manifest",
        str(manifest_path),
        "--confirm-target",
        target,
        "--confirm-plan-sha256",
        hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "--confirm-backup-manifest-sha256",
        hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "--report-out",
        str(report),
    ]


def _write_apply_artifacts(tmp_path: Path):
    plan = _valid_apply_plan()
    plan_path = tmp_path / "plan.json"
    plan_path.write_bytes(canonical_json_bytes(plan))
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    manifest_path = backup.artifact_root / "manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(backup.manifest))
    return plan, plan_path, backup, manifest_path


@pytest.mark.parametrize(
    "mutate",
    [
        lambda args: args.__setitem__(2, "sqlite"),
        lambda args: args.__setitem__(4, "DATABASE_URL"),
        lambda args: args.__setitem__(10, "bad-target"),
        lambda args: args.__setitem__(12, "bad-plan-sha"),
        lambda args: args.__setitem__(14, "bad-backup-sha"),
    ],
)
def test_apply_cli_refuses_unsafe_args_before_artifact_access_import_or_connect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutate
) -> None:
    plan = tmp_path / "missing-plan.json"
    manifest = tmp_path / "missing-manifest.json"
    report = tmp_path / "report.json"
    args = [
        "apply", "--target", "pg", "--database-url-env", "TASK7_DATABASE_URL",
        "--plan", str(plan), "--backup-manifest", str(manifest),
        "--confirm-target", "0" * 64, "--confirm-plan-sha256", "0" * 64,
        "--confirm-backup-manifest-sha256", "0" * 64,
        "--report-out", str(report),
    ]
    mutate(args)
    monkeypatch.setattr(
        migration,
        "load_immutable_json",
        lambda *_args: pytest.fail("artifact accessed before apply CLI preflight"),
    )
    monkeypatch.setattr(
        migration,
        "_load_psycopg2",
        lambda: pytest.fail("psycopg2 imported before apply CLI preflight"),
    )
    monkeypatch.setattr(
        migration,
        "resolve_database_url",
        lambda *_args: pytest.fail("database URL resolved before apply CLI preflight"),
    )

    assert migration.main(args) == 1
    assert not report.exists()


def test_apply_cli_refuses_existing_report_before_artifact_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = tmp_path / "missing-plan.json"
    manifest = tmp_path / "missing-manifest.json"
    report = tmp_path / "existing.json"
    report.write_text("preserve", encoding="utf-8")
    args = [
        "apply", "--target", "pg", "--database-url-env", "TASK7_DATABASE_URL",
        "--plan", str(plan), "--backup-manifest", str(manifest),
        "--confirm-target", "0" * 64, "--confirm-plan-sha256", "0" * 64,
        "--confirm-backup-manifest-sha256", "0" * 64,
        "--report-out", str(report),
    ]
    monkeypatch.setattr(
        migration,
        "load_immutable_json",
        lambda *_args: pytest.fail("existing report did not short-circuit artifacts"),
    )

    assert migration.main(args) == 1
    assert report.read_text(encoding="utf-8") == "preserve"


def test_apply_cli_refuses_noncanonical_plan_bytes_before_resolve_or_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, plan_path, _backup, manifest_path = _write_apply_artifacts(tmp_path)
    plan_path.write_bytes(json.dumps(plan, indent=2).encode("utf-8"))
    report = tmp_path / "report.json"
    monkeypatch.setattr(
        migration,
        "resolve_database_url",
        lambda *_args: pytest.fail("database resolved for noncanonical plan"),
    )
    monkeypatch.setattr(
        migration,
        "_load_psycopg2",
        lambda: pytest.fail("psycopg2 imported for noncanonical plan"),
    )

    assert migration.main(
        _apply_cli_args(plan_path, manifest_path, report, plan["target_fingerprint"])
    ) == 1
    assert not report.exists()


def test_apply_cli_requires_exact_raw_plan_confirmation_before_resolve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, plan_path, _backup, manifest_path = _write_apply_artifacts(tmp_path)
    report = tmp_path / "report.json"
    args = _apply_cli_args(
        plan_path, manifest_path, report, plan["target_fingerprint"]
    )
    args[12] = "0" * 64
    monkeypatch.setattr(
        migration,
        "resolve_database_url",
        lambda *_args: pytest.fail("database resolved for wrong plan confirmation"),
    )

    assert migration.main(args) == 1
    assert not report.exists()


def test_apply_cli_requires_exact_raw_backup_confirmation_before_resolve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, plan_path, _backup, manifest_path = _write_apply_artifacts(tmp_path)
    report = tmp_path / "report.json"
    args = _apply_cli_args(
        plan_path, manifest_path, report, plan["target_fingerprint"]
    )
    args[14] = "0" * 64
    monkeypatch.setattr(
        migration,
        "resolve_database_url",
        lambda *_args: pytest.fail("database resolved for wrong backup confirmation"),
    )

    assert migration.main(args) == 1
    assert not report.exists()


class ApplyCliCursor:
    def __init__(self, events: list[object]) -> None:
        self.events = events

    def execute(self, query: str, params=None) -> None:
        self.events.append(("execute", " ".join(query.split()), params))

    def close(self) -> None:
        self.events.append("cursor-close")


class ApplyCliConnection:
    def __init__(self, events: list[object], *, fail_commit: bool = False) -> None:
        self.events = events
        self.fail_commit = fail_commit
        self.cursor_value = ApplyCliCursor(events)

    def set_session(self, **kwargs) -> None:
        self.events.append(("session", kwargs))

    def cursor(self):
        self.events.append("cursor")
        return self.cursor_value

    def commit(self) -> None:
        self.events.append("commit")
        if self.fail_commit:
            raise RuntimeError("commit failed")

    def rollback(self) -> None:
        self.events.append("rollback")

    def close(self) -> None:
        self.events.append("connection-close")


def test_apply_cli_validates_offline_then_commits_before_immutable_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, plan_path, backup, manifest_path = _write_apply_artifacts(tmp_path)
    report = tmp_path / "apply.json"
    events: list[object] = []
    connection = ApplyCliConnection(events)
    completed_at = APPLY_NOW + timedelta(seconds=5)
    clock_values = iter([APPLY_NOW, completed_at])

    def clock():
        value = next(clock_values)
        events.append(("clock", value))
        return value

    monkeypatch.setattr(migration, "_utc_now", clock)
    expected_report = {
        "schema": migration.APPLY_SCHEMA,
        "result": "applied",
        "candidate_count": plan["candidate_count"],
        "completed_at": migration.utc_text(APPLY_NOW),
    }

    monkeypatch.setattr(
        migration,
        "validate_restore_artifact",
        lambda _path: events.append("restore")
        or backup.manifest["validation"]["listing_sha256"],
    )
    monkeypatch.setattr(
        migration,
        "resolve_database_url",
        lambda name: events.append(("resolve", name)) or "postgresql://secret@db/vl360",
    )
    monkeypatch.setattr(
        migration,
        "_load_psycopg2",
        lambda: SimpleNamespace(
            connect=lambda dsn: events.append(("connect", dsn)) or connection
        ),
    )
    monkeypatch.setattr(
        migration,
        "_apply_locked",
        lambda *_args, **_kwargs: events.append("locked-apply") or expected_report,
    )

    assert migration.main(
        _apply_cli_args(plan_path, manifest_path, report, plan["target_fingerprint"])
    ) == 0
    assert json.loads(report.read_text(encoding="utf-8")) == expected_report
    assert expected_report["completed_at"] == migration.utc_text(completed_at)
    assert events.index("restore") < events.index(("resolve", "TASK7_DATABASE_URL"))
    assert events.index("commit") < events.index("cursor-close")
    assert events.index("commit") < events.index(("clock", completed_at))
    assert events[events.index("cursor") + 1] == (
        "execute",
        "SET LOCAL search_path = public",
        None,
    )
    assert ("session", {
        "isolation_level": "SERIALIZABLE",
        "readonly": False,
        "autocommit": False,
    }) in events


def test_apply_cli_commit_failure_rolls_back_and_writes_no_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, plan_path, backup, manifest_path = _write_apply_artifacts(tmp_path)
    report = tmp_path / "apply.json"
    events: list[object] = []
    connection = ApplyCliConnection(events, fail_commit=True)
    monkeypatch.setattr(migration, "_utc_now", lambda: APPLY_NOW)
    monkeypatch.setattr(
        migration,
        "validate_restore_artifact",
        lambda _path: backup.manifest["validation"]["listing_sha256"],
    )
    monkeypatch.setattr(migration, "resolve_database_url", lambda _name: "postgresql://x/db")
    monkeypatch.setattr(
        migration,
        "_load_psycopg2",
        lambda: SimpleNamespace(connect=lambda _dsn: connection),
    )
    monkeypatch.setattr(
        migration,
        "_apply_locked",
        lambda *_args, **_kwargs: {"schema": migration.APPLY_SCHEMA},
    )

    assert migration.main(
        _apply_cli_args(plan_path, manifest_path, report, plan["target_fingerprint"])
    ) == 1
    assert "commit" in events
    assert "rollback" in events
    assert not report.exists()


def test_apply_cli_report_write_failure_after_commit_never_claims_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    plan, plan_path, backup, manifest_path = _write_apply_artifacts(tmp_path)
    report = tmp_path / "apply.json"
    retry_report = tmp_path / "apply-recovery.json"
    events: list[object] = []
    connection = ApplyCliConnection(events)
    original_writer = migration.write_immutable_json
    monkeypatch.setattr(migration, "_utc_now", lambda: APPLY_NOW)
    monkeypatch.setattr(
        migration,
        "validate_restore_artifact",
        lambda _path: backup.manifest["validation"]["listing_sha256"],
    )
    monkeypatch.setattr(migration, "resolve_database_url", lambda _name: "postgresql://x/db")
    monkeypatch.setattr(
        migration,
        "_load_psycopg2",
        lambda: SimpleNamespace(connect=lambda _dsn: connection),
    )
    reports = iter(
        [
            {
                "schema": migration.APPLY_SCHEMA,
                "result": "applied",
                "candidate_count": plan["candidate_count"],
                "completed_at": migration.utc_text(APPLY_NOW),
            },
            {
                "schema": migration.APPLY_SCHEMA,
                "result": "already-applied",
                "candidate_count": plan["candidate_count"],
                "candidate_ids": plan["candidate_ids"],
                "candidate_sha256": plan["candidate_sha256"],
                "updated_ids": plan["candidate_ids"],
                "recovery_ready": True,
                "recovery_contract": "apply-audit-exact-v1",
                "completed_at": migration.utc_text(APPLY_NOW),
            },
        ]
    )
    monkeypatch.setattr(
        migration, "_apply_locked", lambda *_args, **_kwargs: next(reports)
    )
    monkeypatch.setattr(
        migration,
        "write_immutable_json",
        lambda *_args: (_ for _ in ()).throw(OSError("write failed")),
    )

    assert migration.main(
        _apply_cli_args(plan_path, manifest_path, report, plan["target_fingerprint"])
    ) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "commit" in events
    assert not report.exists()

    monkeypatch.setattr(migration, "write_immutable_json", original_writer)
    assert migration.main(
        _apply_cli_args(
            plan_path, manifest_path, retry_report, plan["target_fingerprint"]
        )
    ) == 0
    recovery = json.loads(retry_report.read_text(encoding="utf-8"))
    assert recovery["result"] == "already-applied"
    assert recovery["updated_ids"] == plan["candidate_ids"]
    assert recovery["recovery_ready"] is True
    assert recovery["recovery_contract"] == "apply-audit-exact-v1"
