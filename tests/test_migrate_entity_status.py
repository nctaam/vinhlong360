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
from scripts.postgres_target import canonical_json_bytes, target_fingerprint


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
    with pytest.raises(migration.MigrationRefusal, match="no publication candidates"):
        _build(rows=[_row("already-reviewed", status="verified")])


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
        if normalized == "SELECT * FROM entities ORDER BY id":
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
    assert connection.fake_cursor.queries[2] == "SELECT * FROM entities ORDER BY id"
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
