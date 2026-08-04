#!/usr/bin/env python3
"""Verify that an incoming migration chain exactly matches PostgreSQL state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import stat
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "agent" / "migrations"
MIGRATION_RE = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_ENVIRONMENT_BYTES = 1024 * 1024
POSTGRES_URL_PREFIXES = ("postgres://", "postgresql://")


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    message: str


@dataclass(frozen=True)
class MigrationAuthority:
    version: int
    migration: str
    migration_set_sha256: str
    records: tuple[dict[str, object], ...]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def migration_files(migrations_dir: Path = MIGRATIONS) -> list[Path]:
    return sorted(migrations_dir.glob("*.sql"))


def _parse_prefixes(files: list[Path], issues: list[Issue]) -> list[int]:
    prefixes: list[int] = []
    seen: set[int] = set()
    duplicate_prefixes: set[int] = set()
    for path in files:
        match = MIGRATION_RE.fullmatch(path.name)
        if match is None:
            issues.append(
                Issue("error", "bad_filename", f"{path.name} must match 000_name.sql")
            )
            continue
        prefix = int(match.group(1))
        if prefix in seen:
            duplicate_prefixes.add(prefix)
        seen.add(prefix)
        prefixes.append(prefix)
    if duplicate_prefixes:
        issues.append(
            Issue(
                "error",
                "duplicate_prefix",
                f"duplicate migration prefixes: {sorted(duplicate_prefixes)}",
            )
        )
    return prefixes


def _check_prefix_sequence(prefixes: list[int], issues: list[Issue]) -> None:
    if not prefixes:
        issues.append(Issue("error", "missing_migrations", "no migrations supplied"))
        return
    expected = list(range(min(prefixes), max(prefixes) + 1))
    missing = sorted(set(expected) - set(prefixes))
    if min(prefixes) != 2:
        issues.append(
            Issue(
                "error",
                "unexpected_baseline",
                f"first migration prefix is {min(prefixes)}, expected 002 after init.sql baseline",
            )
        )
    if missing:
        issues.append(
            Issue("error", "missing_prefix", f"missing migration prefixes: {missing}")
        )


def _check_required_contracts(
    files: list[Path], authority: MigrationAuthority | None, issues: list[Issue]
) -> None:
    all_sql = "\n".join(_read(path) for path in files)
    required_contracts = {
        "saved_entities_kind": ["saved_entities", "kind", "itinerary"],
        "superadmin_role": ["users_role_check", "superadmin"],
        "admin_audit_db": [
            "admin_audit_events",
            "actor_scopes",
            "request_id",
            "before_json",
            "after_json",
        ],
        "shared_rate_idempotency": [
            "shared_rate_limits",
            "request_idempotency_keys",
            "expires_at",
        ],
        "perf_quality_trends": [
            "quality_metric_snapshots",
            "idx_entities_public_type_area_updated",
            "idx_posts_review_entity_recent_public",
        ],
        "itinerary_areas_schema": [
            "ALTER TABLE itineraries",
            "ADD COLUMN IF NOT EXISTS areas",
            "to_jsonb(ARRAY[area])",
        ],
    }
    if authority is not None:
        required_contracts["schema_version"] = [
            "schema_version",
            str(authority.version),
            authority.migration,
        ]
    for code, tokens in required_contracts.items():
        missing = [token for token in tokens if token not in all_sql]
        if missing:
            issues.append(
                Issue(
                    "error",
                    code,
                    f"schema contract missing tokens: {', '.join(missing)}",
                )
            )


def _check_destructive_sql(files: list[Path], issues: list[Issue]) -> None:
    destructive_pattern = re.compile(
        r"\b(DROP\s+TABLE|TRUNCATE|DELETE\s+FROM)\b", re.IGNORECASE
    )
    for path in files:
        sql = _read(path)
        for match in destructive_pattern.finditer(sql):
            line_no = sql[: match.start()].count("\n") + 1
            issues.append(
                Issue(
                    "error",
                    "destructive_sql",
                    f"{path.name}:{line_no} contains {match.group(1)}",
                )
            )


def _derive_migration_authority(files: list[Path]) -> MigrationAuthority | None:
    records: list[dict[str, object]] = []
    for path in files:
        match = MIGRATION_RE.fullmatch(path.name)
        if match is None:
            continue
        raw = path.read_bytes()
        records.append(
            {
                "name": path.name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size": len(raw),
            }
        )
    if not records:
        return None
    records.sort(key=lambda item: str(item["name"]))
    latest_name = str(records[-1]["name"])
    match = MIGRATION_RE.fullmatch(latest_name)
    assert match is not None
    canonical = json.dumps(
        records,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return MigrationAuthority(
        version=int(match.group(1)),
        migration=latest_name,
        migration_set_sha256=hashlib.sha256(canonical).hexdigest(),
        records=tuple(records),
    )


def validate_static(
    migrations_dir: Path = MIGRATIONS,
) -> tuple[list[Issue], dict[str, Any]]:
    issues: list[Issue] = []
    files = migration_files(migrations_dir)
    prefixes = _parse_prefixes(files, issues)
    _check_prefix_sequence(prefixes, issues)
    authority = _derive_migration_authority(files)
    _check_required_contracts(files, authority, issues)
    _check_destructive_sql(files, issues)
    return issues, {
        "migration_count": len(files),
        "latest": authority.migration if authority else None,
        "latest_schema_version": authority.version if authority else None,
        "migration_set_sha256": authority.migration_set_sha256 if authority else None,
        "migration_authority": authority,
    }


def _database_checks() -> list[tuple[str, str]]:
    return [
        (
            "saved_entities_kind_column",
            "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='saved_entities' AND column_name='kind'",
        ),
        (
            "saved_entities_id_column",
            "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='saved_entities' AND column_name='id'",
        ),
        (
            "admin_audit_events_table",
            "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='admin_audit_events'",
        ),
        (
            "shared_rate_limits_table",
            "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='shared_rate_limits'",
        ),
        (
            "request_idempotency_keys_table",
            "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='request_idempotency_keys'",
        ),
        (
            "quality_metric_snapshots_table",
            "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='quality_metric_snapshots'",
        ),
        (
            "itineraries_areas_column",
            "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='itineraries' AND column_name='areas'",
        ),
        (
            "entities_status_column",
            "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='entities' AND column_name='status'",
        ),
        (
            "entities_verified_column",
            "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='entities' AND column_name='verified'",
        ),
    ]


def _schema_rows(cursor: Any) -> list[tuple[object, ...]]:
    cursor.execute(
        "SELECT version, migration FROM public.schema_version WHERE component = %s",
        ("agent",),
    )
    fetchall = getattr(cursor, "fetchall", None)
    if callable(fetchall):
        return list(fetchall())
    row = cursor.fetchone()
    return [] if row is None else [row]


def _validate_database_state(
    database_url: str, authority: MigrationAuthority
) -> tuple[list[Issue], tuple[int, str] | None]:
    try:
        import psycopg2  # type: ignore
    except Exception:
        return [
            Issue(
                "error",
                "missing_psycopg2",
                "PostgreSQL driver is unavailable",
            )
        ], None
    issues: list[Issue] = []
    observed: tuple[int, str] | None = None
    try:
        with psycopg2.connect(database_url, connect_timeout=5) as connection:
            connection.set_session(readonly=True, autocommit=True)
            with connection.cursor() as cursor:
                for code, sql in _database_checks():
                    cursor.execute(sql)
                    if cursor.fetchone() is None:
                        issues.append(
                            Issue("error", code, f"database check failed: {code}")
                        )
                cursor.execute(
                    """
                    SELECT 1
                    FROM pg_catalog.pg_constraint con
                    JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
                    JOIN pg_catalog.pg_namespace ns ON ns.oid = rel.relnamespace
                    WHERE ns.nspname = 'public'
                      AND rel.relname = 'users'
                      AND con.contype = 'c'
                      AND pg_catalog.pg_get_constraintdef(con.oid) LIKE '%superadmin%'
                    """
                )
                if cursor.fetchone() is None:
                    issues.append(
                        Issue(
                            "error",
                            "users_role_superadmin",
                            "users role constraint does not include superadmin",
                        )
                    )
                rows = _schema_rows(cursor)
                if len(rows) != 1 or len(rows[0]) < 2:
                    issues.append(
                        Issue(
                            "error",
                            "schema_version_agent_row",
                            "public.schema_version must contain exactly one agent row",
                        )
                    )
                else:
                    observed = (int(rows[0][0]), str(rows[0][1]))
                    expected = (authority.version, authority.migration)
                    if observed != expected:
                        issues.append(
                            Issue(
                                "error",
                                "schema_version_agent_mismatch",
                                "database agent schema is "
                                f"{observed[0]} ({observed[1]}), required "
                                f"{expected[0]} ({expected[1]})",
                            )
                        )
    except Exception:
        issues.append(
            Issue(
                "error",
                "db_connect",
                "database verification failed without exposing connection details",
            )
        )
    return issues, observed


def validate_database(
    database_url: str,
    required_version: int | None = None,
    required_migration: str | None = None,
    *,
    migrations_dir: Path = MIGRATIONS,
) -> list[Issue]:
    authority = _derive_migration_authority(migration_files(migrations_dir))
    if authority is None:
        return [Issue("error", "missing_migrations", "no migrations supplied")]
    if required_version is not None or required_migration is not None:
        authority = MigrationAuthority(
            required_version if required_version is not None else authority.version,
            required_migration if required_migration is not None else authority.migration,
            authority.migration_set_sha256,
            authority.records,
        )
    return _validate_database_state(database_url, authority)[0]


def _validate_snapshot_descriptor(
    named_before: os.stat_result,
    observed: os.stat_result,
    *,
    require_mode_0600: bool,
) -> None:
    if not stat.S_ISREG(observed.st_mode) or not os.path.samestat(
        named_before, observed
    ):
        raise ValueError("environment authority must be a regular file")
    if require_mode_0600 and os.name != "nt" and stat.S_IMODE(observed.st_mode) != 0o600:
        raise ValueError("environment pin mode must be 0600")
    if observed.st_size > MAX_ENVIRONMENT_BYTES:
        raise ValueError("environment authority exceeds maximum size")


def _read_bounded_descriptor(descriptor: int) -> bytes:
    raw = bytearray()
    while True:
        chunk = os.read(descriptor, 64 * 1024)
        if not chunk:
            return bytes(raw)
        raw.extend(chunk)
        if len(raw) > MAX_ENVIRONMENT_BYTES:
            raise ValueError("environment authority exceeds maximum size")


def _read_regular_snapshot(path: Path, *, require_mode_0600: bool = False) -> bytes:
    named_before = path.lstat()
    if stat.S_ISLNK(named_before.st_mode) or not stat.S_ISREG(named_before.st_mode):
        raise ValueError("environment authority must be a regular file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags)
    try:
        observed = os.fstat(descriptor)
        _validate_snapshot_descriptor(
            named_before, observed, require_mode_0600=require_mode_0600
        )
        raw = _read_bounded_descriptor(descriptor)
        named_after = path.lstat()
        if not os.path.samestat(observed, named_after):
            raise ValueError("environment authority changed during snapshot")
        return raw
    finally:
        os.close(descriptor)


def _write_environment_pin(path: Path, raw: bytes) -> None:
    if os.path.lexists(path):
        raise FileExistsError("environment pin already exists")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("environment pin parent must be a real directory")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("environment pin write made no progress")
            view = view[written:]
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o600)
        opened = os.fstat(descriptor)
        named = path.lstat()
        if not stat.S_ISREG(named.st_mode) or not os.path.samestat(opened, named):
            raise ValueError("environment pin path changed during publish")
        if os.name != "nt" and stat.S_IMODE(opened.st_mode) != 0o600:
            raise ValueError("environment pin mode must be 0600")
    except BaseException:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    finally:
        os.close(descriptor)


def pin_environment_authority(source: Path, destination: Path) -> bytes:
    raw = _read_regular_snapshot(source)
    _parse_environment(raw)
    _write_environment_pin(destination, raw)
    return raw


def _normalize_environment_value(value: str, line_number: int) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    elif value.startswith(("'", '"')) or value.endswith(("'", '"')):
        raise ValueError(f"environment quoting is invalid at line {line_number}")
    if any(token in value for token in ("$", "`")):
        raise ValueError(f"environment interpolation is forbidden at line {line_number}")
    return value


def _parse_environment_assignment(
    original: str, line_number: int
) -> tuple[str, str] | None:
    line = original.strip()
    if not line or line.startswith("#"):
        return None
    if line.endswith("\\"):
        raise ValueError(f"environment continuation is forbidden at line {line_number}")
    if "=" not in line:
        raise ValueError(f"environment assignment is invalid at line {line_number}")
    key, value = line.split("=", 1)
    key = key.strip()
    if ENV_KEY_RE.fullmatch(key) is None:
        raise ValueError(f"environment key is invalid at line {line_number}")
    return key, _normalize_environment_value(value.strip(), line_number)


def _validate_production_environment(values: Mapping[str, str]) -> None:
    if values.get("ENVIRONMENT", "").strip().lower() != "production":
        raise ValueError("environment authority requires ENVIRONMENT=production")
    database_url = values.get("DATABASE_URL", "").strip().lower()
    if not database_url.startswith(POSTGRES_URL_PREFIXES):
        raise ValueError("environment authority requires a PostgreSQL DATABASE_URL")
    if values.get("ENTITY_DETAILS_TABLES", "").strip().lower() != "true":
        raise ValueError("environment authority requires ENTITY_DETAILS_TABLES=true")


def _parse_environment(raw: bytes) -> dict[str, str]:
    if b"\0" in raw:
        raise ValueError("environment authority contains NUL")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("environment authority is not strict UTF-8") from exc
    values: dict[str, str] = {}
    for line_number, original in enumerate(text.splitlines(), 1):
        assignment = _parse_environment_assignment(original, line_number)
        if assignment is None:
            continue
        key, value = assignment
        if key in values:
            raise ValueError(f"duplicate environment key: {key}")
        values[key] = value
    database_keys = [key for key in values if key == "DATABASE_URL"]
    if len(database_keys) != 1 or not values.get("DATABASE_URL"):
        raise ValueError("environment authority requires exactly one DATABASE_URL")
    unlock_keys = [key for key, value in values.items() if "UNLOCK" in key and value]
    if unlock_keys:
        raise ValueError("environment authority contains a nonempty unlock key")
    _validate_production_environment(values)
    return values


def _load_release_evidence(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    raw = _read_regular_snapshot(path)
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("release evidence is invalid") from exc
    if not isinstance(value, dict):
        raise ValueError("release evidence must be an object")
    migration = value.get("migration_prerequisites")
    if not isinstance(migration, dict):
        raise ValueError("release evidence lacks migration prerequisites")
    return value


def _write_evidence(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise ValueError("gate evidence parent must be a real directory")
    raw = (json.dumps(dict(payload), sort_keys=True, indent=2) + "\n").encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary)
    try:
        os.fchmod(descriptor, 0o600)
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("gate evidence write made no progress")
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.link(temporary_path, path)
        temporary_path.unlink()
    finally:
        if descriptor != -1:
            os.close(descriptor)
        temporary_path.unlink(missing_ok=True)


def print_report(issues: list[Issue], stats: Mapping[str, Any]) -> None:
    print("VinhLong360 migration gate")
    print("==========================")
    print(f"migration_count: {stats.get('migration_count')}")
    print(f"latest: {stats.get('latest')}")
    print(f"latest_schema_version: {stats.get('latest_schema_version')}")
    if issues:
        print("\nIssues:")
        for issue in issues:
            print(f"  [{issue.severity}] {issue.code}: {issue.message}")
    else:
        print("\nOK")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--migrations", type=Path, default=MIGRATIONS)
    parser.add_argument("--db-check", action="store_true")
    parser.add_argument("--environment-authority", type=Path)
    parser.add_argument("--environment-pin", type=Path)
    parser.add_argument("--reuse-environment-pin", action="store_true")
    parser.add_argument("--release-evidence", type=Path)
    parser.add_argument("--evidence", type=Path)
    return parser


def _resolve_environment_authority(args: argparse.Namespace) -> tuple[str, str | None]:
    database_url = os.getenv("DATABASE_URL", "")
    environment_pin_sha256: str | None = None
    if args.environment_authority is not None:
        if args.reuse_environment_pin or args.environment_pin is None:
            raise ValueError("first authority pin requires a new --environment-pin")
        raw_environment = pin_environment_authority(
            args.environment_authority, args.environment_pin
        )
        database_url = _parse_environment(raw_environment)["DATABASE_URL"]
        environment_pin_sha256 = hashlib.sha256(raw_environment).hexdigest()
    elif args.environment_pin is not None:
        if not args.reuse_environment_pin:
            raise ValueError("existing environment pin requires --reuse-environment-pin")
        raw_environment = _read_regular_snapshot(
            args.environment_pin, require_mode_0600=True
        )
        database_url = _parse_environment(raw_environment)["DATABASE_URL"]
        environment_pin_sha256 = hashlib.sha256(raw_environment).hexdigest()
    elif args.reuse_environment_pin:
        raise ValueError("--reuse-environment-pin requires --environment-pin")
    return database_url, environment_pin_sha256


def _load_bound_release_evidence(
    path: Path | None, authority: object
) -> dict[str, Any]:
    release_evidence = _load_release_evidence(path)
    if not isinstance(authority, MigrationAuthority) or not release_evidence:
        return release_evidence
    packaged = release_evidence["migration_prerequisites"]
    if packaged.get("migration_set_sha256") != authority.migration_set_sha256:
        raise ValueError("supplied migrations do not match verified release evidence")
    if packaged.get("migration_latest") != {
        "version": authority.version,
        "migration": authority.migration,
    }:
        raise ValueError("supplied migration latest does not match release evidence")
    return release_evidence


def _run_database_gate(
    database_url: str, authority: object
) -> tuple[list[Issue], tuple[int, str] | None]:
    if not database_url:
        return [Issue("error", "missing_database_url", "DATABASE_URL is required")], None
    if not isinstance(authority, MigrationAuthority):
        return [], None
    return _validate_database_state(database_url, authority)


def _evidence_payload(
    *,
    status: str,
    stats: Mapping[str, Any],
    release_evidence: Mapping[str, Any],
    observed: tuple[int, str] | None,
    environment_pin_sha256: str | None,
) -> dict[str, Any]:
    packaged = release_evidence.get("migration_prerequisites", {})
    return {
        "schema_version": 1,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "archive_sha256": packaged.get("archive_sha256"),
        "verifier_sha256": packaged.get("verifier_sha256"),
        "checker_sha256": packaged.get("checker_sha256"),
        "installer_sha256": packaged.get("installer_sha256"),
        "migration_set_sha256": stats.get("migration_set_sha256"),
        "migration_latest": {
            "version": stats.get("latest_schema_version"),
            "migration": stats.get("latest"),
        },
        "observed_database": (
            {"version": observed[0], "migration": observed[1]}
            if observed is not None
            else None
        ),
        "environment_pin_sha256": environment_pin_sha256,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    issues, stats = validate_static(args.migrations)
    authority = stats.get("migration_authority")
    database_url = ""
    environment_pin_sha256: str | None = None
    observed: tuple[int, str] | None = None
    release_evidence: dict[str, Any] = {}
    try:
        database_url, environment_pin_sha256 = _resolve_environment_authority(args)
        release_evidence = _load_bound_release_evidence(
            args.release_evidence, authority
        )
    except (FileExistsError, OSError, ValueError) as exc:
        issues.append(Issue("error", "authority", str(exc)))

    if args.db_check:
        database_issues, observed = _run_database_gate(database_url, authority)
        issues.extend(database_issues)

    print_report(issues, stats)
    status = "failed" if any(issue.severity == "error" for issue in issues) else "passed"
    if args.evidence is not None:
        evidence = _evidence_payload(
            status=status,
            stats=stats,
            release_evidence=release_evidence,
            observed=observed,
            environment_pin_sha256=environment_pin_sha256,
        )
        try:
            _write_evidence(args.evidence, evidence)
        except (FileExistsError, OSError, ValueError):
            return 1
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
