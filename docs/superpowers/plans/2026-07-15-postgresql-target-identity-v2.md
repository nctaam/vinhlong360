# PostgreSQL Target Identity v2 Implementation Plan

> STATUS: proposed; owner-approved design at `8673cac`; implementation must not start until this plan is reviewed and approved; Stage C remains unauthorized

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the tunnel-ambiguous PostgreSQL target fingerprint with a strict cluster-and-database identity v2, then regenerate a private, credential-free, fully attested Stage B package while preserving global `noindex` and proving that apply, rollback, export, and deploy did not run.

**Architecture:** A single strict identity normalizer in `scripts/postgres_target.py` owns the seven-field `postgres-cluster-v2` contract and is reused by backup, plan, apply, rollback, integration tests, and attestation. Windows artifact security is established before sensitive bytes are written, normalized after generation, and independently summarized in a canonical attestation only after the temporary PostgreSQL role and SSH tunnel are confirmed absent. Production Stage B is the final operational task and is separated from all code tasks by full test, spec-review, quality-review, and owner checkpoints.

**Tech Stack:** Python 3.14, pytest, psycopg2, PostgreSQL 16, `pg_dump`, `pg_restore`, PowerShell 7, Windows ACL APIs, OpenSSH, Git, Nuxt 4 noindex source guards.

---

## Authority and Non-Negotiable Boundaries

- Approved design: `docs/superpowers/specs/2026-07-15-postgresql-target-identity-v2-design.md` at commit `8673cacd15711b7ccfd18606131edebb6fe48831`.
- Execution worktree: `C:\Users\Administrator\.config\superpowers\worktrees\vinhlong360\codex-launch-safety-gate-continuation` on branch `codex/launch-safety-gate-continuation`.
- Identity revision is exactly `postgres-cluster-v2`; there is no identity-v1 compatibility mode or silent fallback.
- Global `noindex, follow` stays active in source and production. Do not activate selective indexing or change `NUXT_PUBLIC_SITE_NOINDEX`.
- Tasks 1-11 are repository engineering and disposable-test work only. They must not connect to production, read `/opt/vinhlong360/.env`, create a production role, open a production tunnel, deploy, export, apply, rollback, or mutate project rows.
- Task 12 is Stage B backup + plan + attestation only. It must stop with `apply_run=false`, `rollback_run=false`, `export_run=false`, and `deploy_run=false`.
- Stage C requires a later owner authorization naming the exact v2 target fingerprint and all new artifact hashes. Nothing in this plan grants that authorization.
- The existing v1 package at `C:\Users\Administrator\Documents\vinhlong360-stage-b\20260715T225652` remains immutable evidence. Its plan, manifest, dump, and hardlinks must not be edited or deleted.
- Every numbered task uses a fresh implementer agent. After the implementer commits, a fresh spec reviewer checks the exact task against this plan and the approved design; after spec approval, a separate fresh quality reviewer checks correctness, maintainability, refusal ordering, secret handling, and test isolation.
- Every Critical or Important review finding is fixed by the task implementer and re-reviewed before the next task starts. One task equals one coherent commit unless the task explicitly identifies a separate evidence-only commit.
- If a task discovers a new production dependency, a need to read a secret from the VPS, a need to alter global noindex, or a need to mutate application rows, stop and return to the owner instead of expanding scope.

## Locked File Structure

### Identity and migration contract

- Modify `scripts/postgres_target.py`: v2 revision constant, strict canonical identity validation, one-query identity reader, deterministic fingerprint.
- Modify `scripts/backup_data.py`: validate identity before output directory creation or `pg_dump`; embed exact v2 identity.
- Modify `scripts/migrate_entity_status.py`: strict v2 plan/backup/apply/rollback validation, exact cross-artifact equality, identity-bearing reports, pre-lock live identity verification.
- Modify `tests/test_postgres_target.py`, `tests/test_backup_data.py`, `tests/test_migrate_entity_status.py`, and `tests/test_migrate_entity_status_postgres.py`: RED/GREEN unit, CLI, refusal-order, and disposable PostgreSQL coverage.

### Stage B security and evidence

- Create `scripts/secure_stage_b_artifacts.ps1`: create a protected root, recursively normalize ACLs, reject reparse points/alternate streams/unexpected principals, and emit a machine-readable summary.
- Create `scripts/stage_b_attestation.py`: validate canonical artifacts and cleanup/noindex/ACL evidence, reject secrets, and write immutable canonical `stage-b-attestation.json`.
- Create `scripts/run_entity_status_stage_b.ps1`: one-shot production Stage B orchestration with in-memory password, loopback-only tunnel, temporary restricted role, mandatory cleanup, and no apply path.
- Create `tests/test_secure_stage_b_artifacts.py`, `tests/test_stage_b_attestation.py`, and `tests/test_run_entity_status_stage_b.py`: focused Windows and cross-platform source/behavior tests.
- Modify `docs/runbooks/entity-published-status-migration.md` and `tests/test_entity_status_migration_guardrails.py`: replace manual Stage B with the reviewed runner and lock the v2/noindex/cleanup contract.

## Shared Identity and Attestation Contracts

The Stage B filesystem layout is fixed and preserves the existing timestamped destination created by `backup_data.py`:

```text
yyyyMMddTHHmmssZ/
  published-v1-plan.json
  .pending-write-plan-hardlink
  pg-restore-list.txt
  stage-b-attestation.json
  .pending-write-attestation-hardlink
  backup/
    yyyyMMdd-HHmmss/
      manifest.json
      .pending-write-manifest-hardlink
      postgres.dump
```

There must be exactly one real directory under `backup/`. The attestation stores artifact paths relative to the Stage B root and rejects extra backup-run directories, links, or path traversal.

The canonical identity object has exactly these keys and types:

```python
POSTGRES_IDENTITY_REVISION = "postgres-cluster-v2"
IDENTITY_KEYS = (
    "identity_revision",   # exact str: postgres-cluster-v2
    "database",            # nonempty exact str
    "database_oid",        # positive exact int
    "system_identifier",   # decimal exact str, no sign/whitespace
    "server_addr",         # nonempty exact str
    "server_port",         # positive exact int
    "server_version_num",  # positive exact int
)
```

The canonical Stage B attestation uses these top-level fields:

```python
{
    "schema": "vinhlong360-stage-b-attestation-v1",
    "attestation_revision": "postgres-identity-v2",
    "generated_at": "2026-07-15T16:30:00Z",  # illustrative writer-generated UTC value
    "source": {
        "head": "8673cacd15711b7ccfd18606131edebb6fe48831",
        "worktree_clean": True,
    },
    "artifacts": {
        "plan": {"path": "published-v1-plan.json", "sha256": "0" * 64},
        "manifest": {"path": "backup/20260715-230716/manifest.json", "sha256": "1" * 64},
        "dump": {"path": "backup/20260715-230716/postgres.dump", "size": 954965, "sha256": "2" * 64},
        "restore_list": {"path": "pg-restore-list.txt", "sha256": "3" * 64},
    },
    "target": {
        "database_identity": {
            "identity_revision": "postgres-cluster-v2",
            "database": "vinhlong360",
            "database_oid": 16384,
            "system_identifier": "7463376938976342231",
            "server_addr": "127.0.0.1/32",
            "server_port": 5432,
            "server_version_num": 160004,
        },
        "target_fingerprint": "4" * 64,
    },
    "noindex": {
        "url": "https://vinhlong360.vn/",
        "checked_at": "2026-07-15T16:28:00Z",
        "status": 200,
        "x_robots_tag": "noindex, follow",
        "robots_meta_count": 1,
        "robots_meta_value": "noindex, follow",
        "body_sha256": "5" * 64,
    },
    "temporary_role": {
        "name": "vl360_stage_b_0123456789abcdef0123456789abcdef",
        "expires_at": "2026-07-15T18:00:00Z",
        "role_absent": True,
        "absent_checked_at": "2026-07-15T16:29:00Z",
    },
    "tunnel": {
        "endpoint": "127.0.0.1:15432",
        "pid": 7712,
        "process_absent": True,
        "listener_absent": True,
        "absent_checked_at": "2026-07-15T16:29:10Z",
    },
    "acl": {
        "checked_at": "2026-07-15T16:29:20Z",
        "allowed_principals": [
            "DESKTOP-NFGCVJP\\Administrator",
            "NT AUTHORITY\\SYSTEM",
            "BUILTIN\\Administrators",
        ],
        "object_count": 11,
        "protected_object_count": 11,
        "unexpected_principals": [],
        "inherited_rule_count": 0,
        "reparse_point_count": 0,
        "alternate_data_stream_count": 0,
    },
    "operations": {
        "apply_run": False,
        "rollback_run": False,
        "export_run": False,
        "deploy_run": False,
    },
}
```

Commands below contain no secret or owner-supplied placeholder.

## Task 1: Implement the strict PostgreSQL identity v2 primitive

**Files:**
- Modify: `scripts/postgres_target.py:12-115`
- Modify: `tests/test_postgres_target.py:197-246`

- [ ] **Step 1: Write failing query, normalization, revision, and fingerprint tests**

Replace the `_Cursor` fixture and the two current identity tests, then add the refusal/fingerprint cases:

```python
class _Cursor:
    def __init__(self, row=("vl360", 16384, "7463376938976342231", "10.0.0.8", 5432, 160004)):
        self.query = ""
        self.row = row

    def execute(self, query: str) -> None:
        self.query = query

    def fetchone(self):
        return self.row


def _identity_v2() -> dict[str, object]:
    return {
        "identity_revision": "postgres-cluster-v2",
        "database": "vl360",
        "database_oid": 16384,
        "system_identifier": "7463376938976342231",
        "server_addr": "10.0.0.8",
        "server_port": 5432,
        "server_version_num": 160004,
    }


def test_read_target_identity_reads_cluster_and_database_identity_in_one_query() -> None:
    cursor = _Cursor()
    identity = postgres_target.read_target_identity(cursor)

    assert cursor.query.upper().count("SELECT") == 1
    assert "pg_catalog.pg_database" in cursor.query
    assert "pg_catalog.pg_control_system()" in cursor.query
    assert "current_database()" in cursor.query
    assert identity == _identity_v2()


@pytest.mark.parametrize(
    "row",
    [
        None,
        ("vl360", None, "7463376938976342231", "10.0.0.8", 5432, 160004),
        ("vl360", 16384, None, "10.0.0.8", 5432, 160004),
        ("vl360", True, "7463376938976342231", "10.0.0.8", 5432, 160004),
        ("vl360", 16384, 7463376938976342231, "10.0.0.8", 5432, 160004),
    ],
)
def test_read_target_identity_rejects_missing_null_or_wrong_types(row) -> None:
    with pytest.raises(RuntimeError, match="PostgreSQL target identity"):
        postgres_target.read_target_identity(_Cursor(row))


def test_read_target_identity_propagates_pg_control_system_permission_failure() -> None:
    class PermissionCursor:
        def execute(self, _query: str) -> None:
            raise PermissionError("permission denied for function pg_control_system")

    with pytest.raises(PermissionError, match="pg_control_system"):
        postgres_target.read_target_identity(PermissionCursor())


def test_canonical_target_identity_rejects_legacy_revision_explicitly() -> None:
    legacy = {
        "database": "vl360",
        "server_addr": "127.0.0.1/32",
        "server_port": 5432,
        "server_version_num": 160004,
    }
    with pytest.raises(RuntimeError, match="target identity revision"):
        postgres_target.canonical_target_identity(legacy, exact_keys=True)


def test_canonical_target_identity_rejects_noncanonical_system_identifier() -> None:
    with pytest.raises(RuntimeError, match="system identifier"):
        postgres_target.canonical_target_identity(
            {**_identity_v2(), "system_identifier": "07463376938976342231"},
            exact_keys=True,
        )


def test_target_fingerprint_changes_for_database_oid_or_system_identifier() -> None:
    identity = _identity_v2()
    changed_oid = {**identity, "database_oid": 16385}
    changed_cluster = {**identity, "system_identifier": "7463376938976342232"}

    assert postgres_target.target_fingerprint(identity) != postgres_target.target_fingerprint(changed_oid)
    assert postgres_target.target_fingerprint(identity) != postgres_target.target_fingerprint(changed_cluster)


def test_target_fingerprint_is_credential_independent_and_hashes_only_v2_keys() -> None:
    identity = {**_identity_v2(), "password": "must-not-be-hashed", "ssh_host": "66.42.57.202"}
    canonical = postgres_target.canonical_target_identity(identity)
    expected = hashlib.sha256(postgres_target.canonical_json_bytes(canonical)).hexdigest()

    assert postgres_target.target_fingerprint(identity) == expected
    assert "must-not-be-hashed" not in expected
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```powershell
python -m pytest tests/test_postgres_target.py -q
```

Expected: FAIL because `canonical_target_identity` and `postgres-cluster-v2` do not exist and the current query returns only four v1 fields.

- [ ] **Step 3: Add strict normalization and the one-query v2 reader**

Implement this contract in `scripts/postgres_target.py`:

```python
import re


POSTGRES_IDENTITY_REVISION = "postgres-cluster-v2"
IDENTITY_KEYS = (
    "identity_revision",
    "database",
    "database_oid",
    "system_identifier",
    "server_addr",
    "server_port",
    "server_version_num",
)


def canonical_target_identity(
    identity: Mapping[str, object], *, exact_keys: bool = False
) -> dict[str, object]:
    if not isinstance(identity, Mapping):
        raise RuntimeError("PostgreSQL target identity must be an object")
    if identity.get("identity_revision") != POSTGRES_IDENTITY_REVISION:
        raise RuntimeError(
            "target identity revision mismatch: expected postgres-cluster-v2"
        )
    if exact_keys and set(identity) != set(IDENTITY_KEYS):
        raise RuntimeError("PostgreSQL target identity fields are malformed")

    result = {key: identity.get(key) for key in IDENTITY_KEYS}
    if type(result["database"]) is not str or not result["database"]:
        raise RuntimeError("PostgreSQL target identity database is invalid")
    if type(result["database_oid"]) is not int or result["database_oid"] <= 0:
        raise RuntimeError("PostgreSQL target identity database OID is invalid")
    if (
        type(result["system_identifier"]) is not str
        or re.fullmatch(r"[1-9][0-9]*", result["system_identifier"]) is None
    ):
        raise RuntimeError("PostgreSQL target identity system identifier is invalid")
    if type(result["server_addr"]) is not str or not result["server_addr"]:
        raise RuntimeError("PostgreSQL target identity server address is invalid")
    if type(result["server_port"]) is not int or not 1 <= result["server_port"] <= 65535:
        raise RuntimeError("PostgreSQL target identity server_port is invalid")
    if type(result["server_version_num"]) is not int or result["server_version_num"] <= 0:
        raise RuntimeError("PostgreSQL target identity server_version_num is invalid")
    return result


def read_target_identity(cursor) -> dict[str, object]:
    cursor.execute(
        """
        SELECT
            current_database(),
            database.oid::bigint,
            control.system_identifier::text,
            inet_server_addr()::text,
            inet_server_port(),
            current_setting('server_version_num')::int
        FROM pg_catalog.pg_database AS database
        CROSS JOIN pg_catalog.pg_control_system() AS control
        WHERE database.datname = current_database()
        """
    )
    row = cursor.fetchone()
    if row is None or len(row) != 6:
        raise RuntimeError("PostgreSQL target identity query returned no exact row")
    database, database_oid, system_identifier, server_addr, server_port, version = row
    return canonical_target_identity(
        {
            "identity_revision": POSTGRES_IDENTITY_REVISION,
            "database": database,
            "database_oid": database_oid,
            "system_identifier": system_identifier,
            "server_addr": server_addr,
            "server_port": server_port,
            "server_version_num": version,
        },
        exact_keys=True,
    )


def target_fingerprint(identity: Mapping[str, object]) -> str:
    return sha256_bytes(canonical_json_bytes(canonical_target_identity(identity)))
```

Do not catch database permission exceptions inside `read_target_identity()`; `backup_data.py` and `migrate_entity_status.py` already convert connection-bound failures into credential-safe high-level errors.

- [ ] **Step 4: Run GREEN and static checks**

Run:

```powershell
python -m pytest tests/test_postgres_target.py -q
python -m ruff check scripts/postgres_target.py tests/test_postgres_target.py
```

Expected: all `test_postgres_target.py` tests PASS; Ruff exits 0.

- [ ] **Step 5: Commit the identity primitive**

```powershell
git add scripts/postgres_target.py tests/test_postgres_target.py
git commit -m "feat: add PostgreSQL target identity v2"
```

- [ ] **Step 6: Run fresh spec review, then fresh quality review**

Spec reviewer checks exact seven-field identity, one query, decimal-string system identifier, explicit v1 refusal, and credential-independent hashing. Quality reviewer checks exact-type validation, exception hygiene, deterministic canonical bytes, and regression coverage. Resolve and re-review all Critical/Important findings before Task 2.

## Task 2: Bind PostgreSQL backups to exact v2 identity before any dump write

**Files:**
- Modify: `scripts/backup_data.py:19-25,453-525`
- Modify: `tests/test_backup_data.py:545-620`

- [ ] **Step 1: Update backup fixtures and add a pre-output legacy refusal test**

Use this identity fixture:

```python
def _identity() -> dict[str, object]:
    return {
        "identity_revision": "postgres-cluster-v2",
        "database": "vl360",
        "database_oid": 16384,
        "system_identifier": "7463376938976342231",
        "server_addr": "10.0.0.8",
        "server_port": 5432,
        "server_version_num": 160004,
    }
```

Add:

```python
def test_create_postgres_backup_rejects_legacy_identity_before_directory_or_pg_dump(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "pg-backup"
    runner = FakeRunner()
    legacy = {
        "database": "vl360",
        "server_addr": "127.0.0.1/32",
        "server_port": 5432,
        "server_version_num": 160004,
    }

    with pytest.raises(RuntimeError, match="target identity revision"):
        backup_data.create_postgres_backup(
            database_url="postgresql://backup:secret@db.example/vl360",
            destination=destination,
            identity=legacy,
            runner=runner,
            now=_clock(),
        )

    assert not destination.exists()
    assert runner.calls == []
```

Update the success assertion to require exact v2 identity and verify that unrelated metadata is not serialized:

```python
assert manifest["database_identity"] == _identity()
assert manifest["target_fingerprint"] == backup_data.target_fingerprint(_identity())
assert set(manifest["database_identity"]) == set(backup_data.IDENTITY_KEYS)
```

- [ ] **Step 2: Run focused RED**

```powershell
python -m pytest tests/test_backup_data.py -q
```

Expected: FAIL because `create_postgres_backup()` currently creates the directory and may run tools before identity-v2 validation.

- [ ] **Step 3: Canonicalize before creating the destination**

Import `canonical_target_identity`, then make it the first stateful boundary:

```python
def create_postgres_backup(
    *,
    database_url: str,
    destination: Path,
    identity: dict[str, object],
    runner=subprocess.run,
    now=_utc_now,
) -> Path:
    database_identity = canonical_target_identity(identity, exact_keys=True)
    destination.mkdir(parents=True, exist_ok=False)
```

This is an insertion immediately before the current `destination.mkdir(parents=True, exist_ok=False)`; the existing artifact path, timestamps, tool-version checks, `pg_dump`, `pg_restore --list`, required-table checks, and dump hash checks remain byte-for-byte unchanged.

At manifest construction, remove the old unrestricted key copy and use the prevalidated object:

```python
manifest = {
    "schema": "vinhlong360-pg-backup-v1",
    "target": "pg",
    "target_fingerprint": target_fingerprint(database_identity),
    "database_identity": database_identity,
    "started_at": started_at,
    "completed_at": now(),
    "max_age_seconds": 3600,
    "tools": versions,
    "artifact": {
        "path": artifact.name,
        "size": artifact.stat().st_size,
        "sha256": sha256_file(artifact),
    },
    "validation": {
        "pg_restore_list": True,
        "required_tables": list(PG_REQUIRED_TABLES),
        "listing_sha256": sha256_bytes(listing.encode("utf-8")),
    },
    "policy_revision": "published-v1",
}
```

The outer backup schema remains `vinhlong360-pg-backup-v1`; the identity revision is explicit inside `database_identity` and legacy artifacts are rejected by identity preflight.

- [ ] **Step 4: Run GREEN, secret-safety assertions, and Ruff**

```powershell
python -m pytest tests/test_backup_data.py -q
python -m ruff check scripts/backup_data.py tests/test_backup_data.py
```

Expected: PASS; no destination or runner calls for legacy identity; password remains in child-process environment only and is absent from argv/manifest/output.

- [ ] **Step 5: Commit the backup producer change**

```powershell
git add scripts/backup_data.py tests/test_backup_data.py
git commit -m "feat: bind backups to PostgreSQL identity v2"
```

- [ ] **Step 6: Run fresh spec review, then fresh quality review**

Reviewers must prove validation occurs before `destination.mkdir`, tool version calls, and `pg_dump`; manifest identity is exact; required-table and restore-list checks are unchanged; secrets remain absent.

## Task 3: Propagate exact v2 identity through plan, apply, and rollback reports

**Files:**
- Modify: `scripts/migrate_entity_status.py:29-48,154-206,834-861,1164-1225,1478-1521`
- Modify: `tests/test_migrate_entity_status.py:21-26,78-127,215-250,740-877,1324-1714`

- [ ] **Step 1: Convert the shared test identity and expected artifact shapes to v2**

Replace `IDENTITY` with:

```python
IDENTITY = {
    "identity_revision": "postgres-cluster-v2",
    "database": "vl360",
    "database_oid": 16384,
    "system_identifier": "7463376938976342231",
    "server_addr": "10.0.0.3",
    "server_port": 5432,
    "server_version_num": 160004,
}
```

Replace the current “preserves complete identity” test with exact artifact behavior:

```python
def test_build_plan_serializes_only_exact_canonical_v2_identity_without_mutating_input() -> None:
    identity = {**IDENTITY, "password": "excluded", "ssh_host": "66.42.57.202"}
    original = copy.deepcopy(identity)

    plan = migration.build_plan(
        rows=_fixture_rows(),
        identity=identity,
        schema_columns=COLUMNS,
        created_at=CREATED_AT,
        tool_source_revision=REVISION,
    )

    assert plan["database_identity"] == IDENTITY
    assert set(plan["database_identity"]) == set(migration.IDENTITY_KEYS)
    assert plan["target_fingerprint"] == target_fingerprint(IDENTITY)
    assert identity == original
```

Add assertions to successful apply/rollback tests:

```python
assert applied["database_identity"] == IDENTITY
assert rolled_back["database_identity"] == IDENTITY
assert repeated["database_identity"] == IDENTITY
assert repeated_rollback["database_identity"] == IDENTITY
```

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/test_migrate_entity_status.py -q
```

Expected: FAIL because `_database_identity()` preserves extras and apply/rollback reports do not contain `database_identity`.

- [ ] **Step 3: Canonicalize plan identity and add identity to report contracts**

Import `IDENTITY_KEYS` and `canonical_target_identity`. Replace `_database_identity()`:

```python
def _database_identity(identity) -> dict[str, object]:
    try:
        return canonical_target_identity(identity)
    except RuntimeError as exc:
        raise MigrationRefusal(str(exc)) from None
```

Add `"database_identity"` to `_APPLY_REPORT_KEYS` and therefore `_APPLY_RECOVERY_KEYS`. Define exact rollback keys instead of accepting unbounded report dictionaries:

```python
_ROLLBACK_REPORT_KEYS = {
    "schema",
    "policy_revision",
    "result",
    "target_fingerprint",
    "database_identity",
    "schema_fingerprint",
    "plan_sha256",
    "apply_report_sha256",
    "backup_manifest_sha256",
    "candidate_ids",
    "candidate_count",
    "candidate_sha256",
    "expected_before",
    "expected_after",
    "restored_ids",
    "restored_count",
    "started_at",
    "completed_at",
}
_ROLLBACK_RECOVERY_KEYS = _ROLLBACK_REPORT_KEYS | {
    "recovery_ready",
    "recovery_contract",
}
```

When building apply/recovery reports, copy `plan["database_identity"]` through `_database_identity()`. When building rollback/recovery reports, copy the validated apply-report identity the same way. Do not reread or infer it from a URL.

- [ ] **Step 4: Run GREEN and verify canonical report hashes**

```powershell
python -m pytest tests/test_migrate_entity_status.py -q
python -m ruff check scripts/migrate_entity_status.py tests/test_migrate_entity_status.py
```

Expected: PASS; all four report outcomes carry exact identity v2 and immutable report hash tests remain green.

- [ ] **Step 5: Commit report propagation**

```powershell
git add scripts/migrate_entity_status.py tests/test_migrate_entity_status.py
git commit -m "feat: propagate PostgreSQL identity through migration evidence"
```

- [ ] **Step 6: Run fresh spec review, then fresh quality review**

Reviewers check that every target-bearing artifact contains exact identity v2; report recovery shapes are exact; extra metadata/credentials are excluded; existing apply/rollback state and audit semantics are unchanged.

## Task 4: Reject legacy artifacts before hashes, confirmations, connections, or locks

**Files:**
- Modify: `scripts/migrate_entity_status.py:243-355,404-527,1164-1225,1663-1712`
- Modify: `tests/test_migrate_entity_status.py:880-1073,1905-2059,2271-2316`

- [ ] **Step 1: Add parameterized offline legacy-refusal tests**

Add a helper:

```python
def _legacy_identity() -> dict[str, object]:
    return {
        "database": "vl360",
        "server_addr": "127.0.0.1/32",
        "server_port": 5432,
        "server_version_num": 160004,
    }
```

Add tests proving the revision error wins over stale hashes and target confirmations:

```python
@pytest.mark.parametrize("artifact_kind", ["plan", "backup"])
def test_apply_rejects_identity_v1_before_confirmation_hash_or_store(
    tmp_path: Path, artifact_kind: str
) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    if artifact_kind == "plan":
        plan["database_identity"] = _legacy_identity()
    else:
        backup.manifest["database_identity"] = _legacy_identity()
    store = ApplyFakeStore([_row("a"), _row("b")])

    with pytest.raises(migration.MigrationRefusal, match="target identity revision"):
        migration.apply_plan(
            store,
            plan,
            plan_sha256="0" * 64,
            backup=backup,
            confirm_target="f" * 64,
            now=APPLY_NOW,
            restore_validator=_restore_ok,
        )

    assert store.events == []
```

Add rollback coverage by replacing the apply report’s `database_identity` with `_legacy_identity()` and asserting no store events. Add CLI tests that monkeypatch `_resolved_database_url` and `_load_psycopg2` to `pytest.fail`, use wrong confirmation hashes, and still receive `target identity revision` with no report created.

Use this rollback assertion body:

```python
def test_rollback_rejects_identity_v1_before_confirmation_or_store(tmp_path: Path) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    apply_report = _apply(ApplyFakeStore([_row("a"), _row("b")]), plan, backup)
    apply_report["database_identity"] = _legacy_identity()
    store = ApplyFakeStore([_row("a", status="published"), _row("b", status="published")])

    with pytest.raises(migration.MigrationRefusal, match="target identity revision"):
        migration.rollback_apply(
            store,
            apply_report,
            apply_report_sha256="0" * 64,
            backup=backup,
            confirm_target="f" * 64,
            now=APPLY_NOW,
            restore_validator=_restore_ok,
        )

    assert store.events == []
```

For both apply and rollback CLI tests, patch the two connection boundaries exactly as follows before calling `migration.main(args)` with a legacy artifact:

```python
monkeypatch.setattr(
    migration,
    "_resolved_database_url",
    lambda *_args: pytest.fail("URL resolution ran before identity revision preflight"),
)
monkeypatch.setattr(
    migration,
    "_load_psycopg2",
    lambda: pytest.fail("psycopg import ran before identity revision preflight"),
)
assert migration.main(args) == 1
assert "target identity revision" in capsys.readouterr().err
assert not report_path.exists()
```

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/test_migrate_entity_status.py -q
```

Expected: FAIL because current validators compare canonical hashes and confirmations before identity revision and do not enforce exact cross-artifact identity equality.

- [ ] **Step 3: Add one shared revision preflight and reorder validators**

Implement:

```python
def _artifact_database_identity(value: object, label: str) -> dict[str, object]:
    try:
        return canonical_target_identity(value, exact_keys=True)
    except RuntimeError as exc:
        message = str(exc)
        if "target identity revision" in message:
            raise MigrationRefusal(message) from None
        raise MigrationRefusal(f"{label} database identity is invalid") from None
```

Then enforce this order:

```python
def _validate_plan_for_apply(plan, plan_sha256, confirm_target, now):
    if type(plan) is not dict:
        raise MigrationRefusal("plan must be an object")
    identity = _artifact_database_identity(plan.get("database_identity"), "plan")
    _require_exact_keys(plan, _PLAN_KEYS, "plan")
    target = _validate_plan_header(plan, plan_sha256, confirm_target, now)
    if target_fingerprint(identity) != target:
        raise MigrationRefusal("plan target identity mismatch")
    _validate_plan_identity_schema(plan, target)
    candidate_ids, count = _validate_plan_candidates(plan)
    _validate_plan_accounting(plan, count)
    return target, candidate_ids
```

In `validate_backup_manifest()`, preflight `backup.manifest.get("database_identity")` before exact keys and manifest hash. In `_validate_apply_report()`, preflight identity before exact report keys, report SHA, target confirmation, and result-specific validation.

After individual validation, require exact equality:

```python
if plan_identity != backup_identity:
    raise MigrationRefusal("plan and backup database identity mismatch")
```

Rollback similarly requires exact apply-report/backup identity equality. `_load_apply_artifacts()` and `_load_rollback_artifacts()` perform revision preflight immediately after each JSON load, before confirmation comparison or database URL resolution.

- [ ] **Step 4: Run GREEN and refusal-order tests**

```powershell
python -m pytest tests/test_migrate_entity_status.py -q
python -m ruff check scripts/migrate_entity_status.py tests/test_migrate_entity_status.py
```

Expected: PASS; all legacy artifacts fail with the exact revision message before store events, URL resolution, psycopg import, connection, locks, or output writes.

- [ ] **Step 5: Commit validator ordering and equality checks**

```powershell
git add scripts/migrate_entity_status.py tests/test_migrate_entity_status.py
git commit -m "fix: reject legacy PostgreSQL identity evidence first"
```

- [ ] **Step 6: Run fresh spec review, then fresh quality review**

Reviewers explicitly trace plan, backup, apply report, rollback input, and both CLI loaders. They must confirm revision preflight precedes hashes/confirmations and exact identity equality is enforced across artifacts.

## Task 5: Verify live v2 identity before acquiring apply or rollback locks

**Files:**
- Modify: `scripts/migrate_entity_status.py:877-930,1337-1385`
- Modify: `tests/test_migrate_entity_status.py:1324-1466,1485-1773,2060-2489`

- [ ] **Step 1: Add event-order and live identity drift tests**

Update successful event assertions to require identity before lock:

```python
assert store.events.index("identity") < store.events.index("lock")
```

Add:

```python
def test_apply_refuses_live_cluster_identity_drift_before_lock(tmp_path: Path) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    drifted = {**IDENTITY, "system_identifier": "7463376938976342232"}
    store = ApplyFakeStore([_row("a"), _row("b")], identity=drifted)

    with pytest.raises(migration.MigrationRefusal, match="live target identity mismatch"):
        _apply(store, plan, backup)

    assert store.events == ["identity"]


def test_rollback_refuses_live_database_oid_drift_before_lock(tmp_path: Path) -> None:
    plan = _valid_apply_plan()
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    apply_report = _apply(ApplyFakeStore([_row("a"), _row("b")]), plan, backup)
    drifted = {**IDENTITY, "database_oid": 16385}
    store = ApplyFakeStore([_row("a", status="published"), _row("b", status="published")], identity=drifted)

    with pytest.raises(migration.MigrationRefusal, match="live target identity mismatch"):
        migration.rollback_apply(
            store,
            apply_report,
            apply_report_sha256=_artifact_sha(apply_report),
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=APPLY_NOW,
            restore_validator=_restore_ok,
        )

    assert store.events == ["identity"]
```

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/test_migrate_entity_status.py -q
```

Expected: FAIL because current apply and rollback paths acquire the advisory lock before reading live identity.

- [ ] **Step 3: Move exact live identity comparison ahead of locks**

Add a focused helper:

```python
def _verify_live_target_identity(store, expected_identity: dict[str, object]) -> None:
    live_identity = _artifact_database_identity(store.target_identity(), "live target")
    if live_identity != expected_identity:
        raise MigrationRefusal("live target identity mismatch")
```

Call it after offline plan/backup/apply-report validation and before `store.acquire_lock()`. Keep the existing post-lock schema, candidate row, count, audit ownership, and freshness checks unchanged. This change does not remove the transaction or reduce drift validation; it only ensures an obviously wrong cluster is rejected before lock acquisition.

- [ ] **Step 4: Run GREEN and CLI transaction tests**

```powershell
python -m pytest tests/test_migrate_entity_status.py -q
python -m ruff check scripts/migrate_entity_status.py tests/test_migrate_entity_status.py
```

Expected: PASS; identity is the first store event for apply/rollback; drift stops without lock/update/audit events; CLI commit/recovery tests remain green.

- [ ] **Step 5: Commit pre-lock identity verification**

```powershell
git add scripts/migrate_entity_status.py tests/test_migrate_entity_status.py
git commit -m "fix: verify PostgreSQL identity before migration locks"
```

- [ ] **Step 6: Run fresh spec review, then fresh quality review**

Reviewers check both normal and recovery paths, ensure live identity comparison is exact, ensure no lock/mutation happens on mismatch, and ensure later locked-state checks were not weakened.

## Task 6: Prove identity v2 with disposable PostgreSQL restricted roles

**Files:**
- Modify: `tests/test_migrate_entity_status_postgres.py:1-350`

- [ ] **Step 1: Add disposable-role fixtures and permission tests**

Extend the opt-in integration suite with administrator-only setup guarded by the existing disposable confirmation. Use generated role names and passwords and always drop them in `finally`:

```python
from urllib.parse import quote, urlsplit, urlunsplit


def _role_url(base_url: str, role: str, password: str) -> str:
    parsed = urlsplit(base_url)
    host = parsed.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    netloc = f"{quote(role, safe='')}:{quote(password, safe='')}@{host}:{parsed.port or 5432}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, ""))


def _quote_role(role: str) -> str:
    if not re.fullmatch(r"entity_identity_[0-9a-f]{32}", role):
        raise AssertionError("role must be generated by the disposable fixture")
    return f'"{role}"'


@pytest.fixture
def identity_roles():
    if not TEST_URL or TEST_CONFIRM != "disposable":
        pytest.skip("requires explicitly disposable PostgreSQL")
    psycopg2 = pytest.importorskip("psycopg2")
    sql = pytest.importorskip("psycopg2.sql")
    allowed = f"entity_identity_{uuid.uuid4().hex}"
    denied = f"entity_identity_{uuid.uuid4().hex}"
    passwords = {allowed: uuid.uuid4().hex, denied: uuid.uuid4().hex}
    admin = psycopg2.connect(TEST_URL, connect_timeout=5)
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            database_name = cursor.fetchone()[0]
            for role in (allowed, denied):
                cursor.execute(
                    f"CREATE ROLE {_quote_role(role)} LOGIN PASSWORD %s "
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT NOREPLICATION "
                    "NOBYPASSRLS CONNECTION LIMIT 2 VALID UNTIL %s",
                    (passwords[role], datetime.now(UTC) + timedelta(minutes=15)),
                )
                cursor.execute(f"ALTER ROLE {_quote_role(role)} SET default_transaction_read_only = on")
                cursor.execute(f"ALTER ROLE {_quote_role(role)} SET statement_timeout = '5min'")
            cursor.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(database_name),
                    sql.Identifier(allowed),
                )
            )
            cursor.execute(f"GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO {_quote_role(allowed)}")
            cursor.execute(f"GRANT pg_read_all_data TO {_quote_role(allowed)}")
        yield psycopg2, allowed, denied, passwords
    finally:
        with admin.cursor() as cursor:
            for role in (allowed, denied):
                cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = %s", (role,))
                cursor.execute(f"REVOKE pg_read_all_data FROM {_quote_role(role)}")
                cursor.execute(f"REVOKE EXECUTE ON FUNCTION pg_catalog.pg_control_system() FROM {_quote_role(role)}")
                cursor.execute(f"DROP ROLE IF EXISTS {_quote_role(role)}")
        admin.close()
```

Construct role URLs by parsing `TEST_URL` and replacing only username/password in memory; never print them. Add:

```python
def test_restricted_role_reads_v2_identity_and_is_transaction_read_only(identity_roles) -> None:
    psycopg2, allowed, _denied, passwords = identity_roles
    connection = psycopg2.connect(_role_url(TEST_URL, allowed, passwords[allowed]), connect_timeout=5)
    try:
        with connection.cursor() as cursor:
            identity = migration.read_target_identity(cursor)
            cursor.execute("SHOW transaction_read_only")
            assert cursor.fetchone() == ("on",)
            cursor.execute("SELECT pg_has_role(current_user, 'pg_read_all_data', 'USAGE')")
            assert cursor.fetchone() == (True,)
            cursor.execute("SELECT has_function_privilege(current_user, 'pg_catalog.pg_control_system()', 'EXECUTE')")
            assert cursor.fetchone() == (True,)
        assert identity["identity_revision"] == "postgres-cluster-v2"
        assert type(identity["database_oid"]) is int and identity["database_oid"] > 0
        assert identity["system_identifier"].isdigit()
    finally:
        connection.close()


def test_identity_query_fails_without_pg_control_system_execute(identity_roles) -> None:
    psycopg2, _allowed, denied, passwords = identity_roles
    connection = psycopg2.connect(_role_url(TEST_URL, denied, passwords[denied]), connect_timeout=5)
    try:
        with connection.cursor() as cursor, pytest.raises(psycopg2.Error):
            migration.read_target_identity(cursor)
    finally:
        connection.close()
```

- [ ] **Step 2: Run integration RED or safe skip**

```powershell
python -m pytest tests/test_migrate_entity_status_postgres.py -q -m entity_status_postgres
```

Expected with disposable env present: RED until the fixture grants and query contract align. Expected without env: safe SKIP with no connection attempt.

- [ ] **Step 3: Complete URL construction and privilege cleanup helpers**

Use `urllib.parse.urlsplit`, `urlunsplit`, and `quote` to replace credentials without logging them. Ensure cleanup revokes function EXECUTE if needed, terminates only sessions whose `usename` equals the generated role, drops both roles, and closes admin connection in `finally`. Do not grant `pg_write_all_data`, ownership, superuser, createdb, createrole, replication, or bypassrls.

- [ ] **Step 4: Run GREEN and the complete disposable suite**

```powershell
$env:ENTITY_STATUS_TEST_CONFIRM = 'disposable'
python -m pytest tests/test_migrate_entity_status_postgres.py -q -m entity_status_postgres
```

Expected: PASS against the explicitly disposable URL; allowed role returns stable v2 identity in read-only mode; denied role receives a PostgreSQL permission error; generated roles are absent after the suite.

- [ ] **Step 5: Commit integration coverage**

```powershell
git add tests/test_migrate_entity_status_postgres.py
git commit -m "test: cover restricted PostgreSQL identity roles"
```

- [ ] **Step 6: Run fresh spec review, then fresh quality review**

Reviewers confirm the fixture cannot run without both disposable gates, grants only EXECUTE on `pg_control_system()` beyond login/connect/read needs, never emits credentials, and always drops roles.

## Task 7: Create and verify an ACL-first Stage B artifact root

**Files:**
- Create: `scripts/secure_stage_b_artifacts.ps1`
- Create: `tests/test_secure_stage_b_artifacts.py`

- [ ] **Step 1: Write Windows-only RED tests for root creation and hostile descendants**

Create tests that invoke PowerShell 7 only on Windows:

```python
import json
import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows ACL contract")
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "secure_stage_b_artifacts.ps1"


def _pwsh(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["pwsh", "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_create_root_is_protected_before_artifact_write(tmp_path: Path) -> None:
    root = tmp_path / "stage-b"
    result = _pwsh("-Mode", "CreateRoot", "-Root", str(root))
    assert result.returncode == 0, result.stderr
    evidence = json.loads(result.stdout)
    assert evidence["root"] == str(root.resolve())
    assert evidence["object_count"] == 1
    assert evidence["protected_object_count"] == 1
    assert evidence["unexpected_principals"] == []
    assert evidence["inherited_rule_count"] == 0


def test_verify_rejects_alternate_data_stream(tmp_path: Path) -> None:
    root = tmp_path / "stage-b"
    assert _pwsh("-Mode", "CreateRoot", "-Root", str(root)).returncode == 0
    artifact = root / "manifest.json"
    artifact.write_text("{}\n", encoding="utf-8")
    stream = Path(f"{artifact}:unexpected")
    try:
        stream.write_text("blocked", encoding="utf-8")
    except OSError:
        pytest.skip("NTFS alternate streams unavailable")
    result = _pwsh("-Mode", "NormalizeAndVerify", "-Root", str(root))
    assert result.returncode != 0
    assert "alternate data stream" in result.stderr.lower()
```

Add these exact hostile-object tests; helper functions use `Get-Acl`/`Set-Acl` through a one-line `pwsh -Command` invocation and never delete the objects:

```python
def _grant_read_rule(path: Path, principal: str) -> None:
    command = r"""
param([string]$Path, [string]$Principal)
$ErrorActionPreference = 'Stop'
$acl = Get-Acl -LiteralPath $Path
$rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
    $Principal,
    [System.Security.AccessControl.FileSystemRights]::Read,
    [System.Security.AccessControl.AccessControlType]::Allow
)
[void]$acl.AddAccessRule($rule)
Set-Acl -LiteralPath $Path -AclObject $acl
"""
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", command, str(path), principal],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_verify_rejects_unexpected_principal(tmp_path: Path) -> None:
    root = tmp_path / "stage-b"
    assert _pwsh("-Mode", "CreateRoot", "-Root", str(root)).returncode == 0
    artifact = root / "manifest.json"
    artifact.write_text("{}\n", encoding="utf-8")
    _grant_read_rule(artifact, "BUILTIN\\Users")
    result = _pwsh("-Mode", "Verify", "-Root", str(root))
    assert result.returncode != 0
    assert "unexpected principal" in result.stderr.lower()
    assert artifact.exists()


def test_verify_rejects_reparse_point(tmp_path: Path) -> None:
    root = tmp_path / "stage-b"
    assert _pwsh("-Mode", "CreateRoot", "-Root", str(root)).returncode == 0
    target = tmp_path / "outside.txt"
    target.write_text("outside", encoding="utf-8")
    link = root / "linked.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("reparse-point creation unavailable")
    result = _pwsh("-Mode", "NormalizeAndVerify", "-Root", str(root))
    assert result.returncode != 0
    assert "reparse point" in result.stderr.lower()
    assert link.exists()


def test_verify_rejects_safe_but_inherited_child_before_normalization(tmp_path: Path) -> None:
    root = tmp_path / "stage-b"
    assert _pwsh("-Mode", "CreateRoot", "-Root", str(root)).returncode == 0
    artifact = root / "manifest.json"
    artifact.write_text("{}\n", encoding="utf-8")
    result = _pwsh("-Mode", "Verify", "-Root", str(root))
    assert result.returncode != 0
    assert "inherited" in result.stderr.lower()
    assert artifact.exists()
```

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/test_secure_stage_b_artifacts.py -q
```

Expected: FAIL because the script does not exist.

- [ ] **Step 3: Implement the PowerShell ACL helper**

Use an advanced script with exact modes and JSON-only stdout:

```powershell
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('CreateRoot', 'NormalizeAndVerify', 'Verify')]
    [string]$Mode,

    [Parameter(Mandatory)]
    [string]$Root
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-AllowedPrincipals {
    @(
        [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        'NT AUTHORITY\SYSTEM'
        'BUILTIN\Administrators'
    ) | Sort-Object -Unique
}

function New-AccessRule([string]$Identity, [bool]$IsDirectory) {
    $inheritance = if ($IsDirectory) {
        [System.Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
    } else {
        [System.Security.AccessControl.InheritanceFlags]::None
    }
    [System.Security.AccessControl.FileSystemAccessRule]::new(
        $Identity,
        [System.Security.AccessControl.FileSystemRights]::FullControl,
        $inheritance,
        [System.Security.AccessControl.PropagationFlags]::None,
        [System.Security.AccessControl.AccessControlType]::Allow
    )
}

function Set-ExactProtectedAcl([System.IO.FileSystemInfo]$Item) {
    $acl = Get-Acl -LiteralPath $Item.FullName
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) {
        [void]$acl.RemoveAccessRuleSpecific($rule)
    }
    foreach ($identity in Get-AllowedPrincipals) {
        [void]$acl.AddAccessRule((New-AccessRule $identity $Item.PSIsContainer))
    }
    Set-Acl -LiteralPath $Item.FullName -AclObject $acl
}
```

The complete script must also:

- resolve the root to one absolute path and reject an existing root in `CreateRoot` mode;
- create the root, immediately call `Set-ExactProtectedAcl`, and verify it before returning;
- enumerate the root plus descendants without following links;
- reject `FileAttributes.ReparsePoint` before ACL normalization;
- reject every named stream other than `:$DATA` using `Get-Item -Stream *`;
- in final `Verify`, require `AreAccessRulesProtected=$true`, zero inherited rules, exactly the three allowed Allow/FullControl principals, no Deny rules, and correct directory/file inheritance flags;
- in `NormalizeAndVerify`, first reject every unexpected, Deny, reparse, or alternate-stream condition; accept inherited rules only when they name an allowed principal inherited from the protected root; only then convert safe inherited rules to the exact protected ACL and run the same strict verifier;
- emit compact JSON containing a writer-generated UTC `checked_at`, root, allowed principals, object count, protected count, unexpected principals, inherited-rule count, reparse-point count, and alternate-stream count;
- write errors only to stderr and return nonzero without deleting, renaming, or repairing artifact bytes.

- [ ] **Step 4: Run GREEN twice to prove idempotence**

```powershell
python -m pytest tests/test_secure_stage_b_artifacts.py -q
python -m pytest tests/test_secure_stage_b_artifacts.py -q
```

Expected: PASS twice; clean roots normalize deterministically; hostile streams/reparse points/principals fail; no artifact contents change.

- [ ] **Step 5: Commit the ACL helper**

```powershell
git add scripts/secure_stage_b_artifacts.ps1 tests/test_secure_stage_b_artifacts.py
git commit -m "feat: secure Stage B artifact roots before writes"
```

- [ ] **Step 6: Run fresh spec review, then fresh quality review**

Spec review checks the exact three principals and pre-write boundary. Quality review checks Windows SID/name behavior, inheritance flags, ADS and reparse refusal, JSON/stderr separation, idempotence, and preservation-on-failure.

## Task 8: Write canonical credential-free Stage B attestation

**Files:**
- Create: `scripts/stage_b_attestation.py`
- Create: `tests/test_stage_b_attestation.py`

- [ ] **Step 1: Write RED tests around a complete synthetic artifact root**

Build a fixture containing root-level canonical `published-v1-plan.json` and `pg-restore-list.txt` plus `backup/20260715-230716/manifest.json` and `backup/20260715-230716/postgres.dump`, all with matching v2 identity/hashes. Pipe evidence JSON to the CLI stdin. The success test must assert exact top-level shape and canonical bytes:

```python
def test_attestation_writer_validates_and_writes_canonical_secret_free_evidence(
    stage_b_root: Path, evidence: dict[str, object]
) -> None:
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode == 0, result.stderr
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["schema"] == "vinhlong360-stage-b-attestation-v1"
    assert document["attestation_revision"] == "postgres-identity-v2"
    assert document["target"]["database_identity"] == IDENTITY
    assert document["target"]["target_fingerprint"] == target_fingerprint(IDENTITY)
    assert document["temporary_role"]["role_absent"] is True
    assert document["tunnel"]["process_absent"] is True
    assert document["tunnel"]["listener_absent"] is True
    assert document["operations"] == {
        "apply_run": False,
        "rollback_run": False,
        "export_run": False,
        "deploy_run": False,
    }
    assert output.read_bytes() == canonical_json_bytes(document)
```

Add parameterized failures for:

```python
@pytest.mark.parametrize(
    "mutation,message",
    [
        (lambda e: e["noindex"].update(x_robots_tag="index, follow"), "noindex"),
        (lambda e: e["noindex"].update(robots_meta_count=0), "robots meta"),
        (lambda e: e["temporary_role"].update(role_absent=False), "role cleanup"),
        (lambda e: e["tunnel"].update(process_absent=False), "tunnel cleanup"),
        (lambda e: e["operations"].update(apply_run=True), "operation flags"),
        (lambda e: e.update(database_url="postgresql://secret"), "secret field"),
    ],
)
def test_attestation_refuses_failed_gate_without_output(stage_b_root, evidence, mutation, message):
    mutation(evidence)
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode != 0
    assert message.lower() in result.stderr.lower()
    assert not output.exists()
```

Add separate artifact tests that mutate plan/manifest identity, dump bytes, listing bytes, and source HEAD. Add evidence cases for a dirty worktree and timestamps older than five minutes. Add Windows ACL cases that place an unexpected principal, reparse point, or alternate stream under the root before invoking the writer; the writer must fail before allocating attestation paths.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/test_stage_b_attestation.py -q
```

Expected: FAIL because the attestation writer does not exist.

- [ ] **Step 3: Implement strict artifact and evidence validation**

The writer CLI is fixed:

```python
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()
```

Read one JSON object from stdin with a 1 MiB limit. Reject secret-bearing keys recursively using this exact normalized set:

```python
EVIDENCE_KEYS = {
    "source",
    "noindex",
    "temporary_role",
    "tunnel",
    "operations",
}
SECRET_KEYS = {
    "password",
    "password_hash",
    "database_url",
    "connection_url",
    "session_token",
    "otp",
    "private_key",
}
SECRET_VALUE_MARKERS = ("postgresql://", "BEGIN OPENSSH PRIVATE KEY")
```

Run recursive secret-key/value rejection before exact-key validation so an injected `database_url` receives the explicit secret-field refusal instead of a generic shape error.

Implement `load_canonical_object(path)` so raw bytes must equal `canonical_json_bytes(parsed)` and root must be an object. Implement `validate_artifacts(root)` to:

- require root-level `published-v1-plan.json`, `pg-restore-list.txt`, and a real `backup` directory before attestation output;
- require exactly one real non-reparse directory directly under `backup/`, then require `manifest.json` and `postgres.dump` directly inside that run directory;
- reject symlinks/reparse points/non-regular files;
- verify plan/manifest canonical bytes and raw SHA-256;
- validate exact identity v2 in both and exact equality;
- recompute target fingerprint and require it in both;
- verify dump size/hash against manifest;
- verify listing SHA-256 against manifest `validation.listing_sha256`;
- call existing `migrate_entity_status.validate_restore_artifact(dump)` to run a fresh `pg_restore --list`, require its returned hash to equal both the stored listing file hash and manifest listing hash, and thereby require exact public TABLE definitions for `entities` and `entity_changes`;
- independently run `git rev-parse HEAD` and `git status --porcelain` in the repository; require the real HEAD, evidence `source.head`, and plan `tool_source_revision` to match and require both real/evidenced worktree states to be clean.

Implement `validate_evidence()` to require `set(evidence) == EVIDENCE_KEYS`, exact nested keys and types, exact `200`, exact `X-Robots-Tag: noindex, follow`, exactly one `robots` meta with `noindex, follow`, 64-hex body hash, clean worktree, `role_absent=true`, process/listener absent, and all four operation flags false. Noindex/role/tunnel checks must be no older than 300 seconds at writer time. ACL evidence is never accepted from stdin; the writer obtains it directly from `secure_stage_b_artifacts.ps1` and requires its `checked_at` to be no older than 300 seconds.

Build the final document from validated/recomputed values, not by copying unbounded input. The output sequence is exact:

1. Run `secure_stage_b_artifacts.ps1 -Mode Verify` before creating an attestation path; any hostile or non-explicit ACL state fails with no output path.
2. Serialize every section except `acl`, so JSON/type failures happen before filesystem allocation.
3. Create one empty random `.pending-write-<32 hex>` file with exclusive create and hardlink the requested final path to it while both are empty.
4. Run `secure_stage_b_artifacts.ps1 -Mode NormalizeAndVerify`; the two empty attestation links inherit only safe root rules, become explicitly protected, and are included in the returned summary.
5. Insert that exact summary as `acl`, canonicalize the complete document, write through the owned pending file, flush, `fsync`, close, and verify pending/final file identity, size, SHA-256, and ACL again.
6. Retain the pending hardlink intentionally, matching the existing immutable writer convention.

This sequence makes the attestation’s own final and pending paths part of the persisted ACL summary without writing attestation bytes before their ACL is protected. Print only:

```json
{"attestation_path":"C:\\Users\\Administrator\\Documents\\vinhlong360-stage-b\\20260715T163000Z\\stage-b-attestation.json","sha256":"0000000000000000000000000000000000000000000000000000000000000000"}
```

- [ ] **Step 4: Run GREEN, malformed-input tests, and Ruff**

```powershell
python -m pytest tests/test_stage_b_attestation.py -q
python -m ruff check scripts/stage_b_attestation.py tests/test_stage_b_attestation.py
```

Expected: PASS; every failed gate creates no attestation; success output is canonical, immutable, hashable, and contains no credential or raw row.

- [ ] **Step 5: Commit the attestation writer**

```powershell
git add scripts/stage_b_attestation.py tests/test_stage_b_attestation.py
git commit -m "feat: write canonical Stage B attestations"
```

- [ ] **Step 6: Run fresh spec review, then fresh quality review**

Reviewers check all required evidence fields, freshness, canonical/raw hashes, secret scanning, direct-child restrictions, exact identity agreement, noindex exactness, cleanup gates, and fail-closed output behavior.

## Task 9: Orchestrate one-shot Stage B with in-memory credentials and mandatory cleanup

**Files:**
- Create: `scripts/run_entity_status_stage_b.ps1`
- Create: `tests/test_run_entity_status_stage_b.py`

- [ ] **Step 1: Write source-contract and fake-tool RED tests**

The runner exposes these non-secret parameters with safe defaults:

```powershell
param(
    [string]$SshTarget = 'root@66.42.57.202',
    [string]$SshKeyPath = "$HOME\.ssh\vinhlong_vps",
    [string]$RemoteDatabase = 'vinhlong360',
    [string]$DatabaseUrlEnvironment = 'VL360_STAGE_B_DATABASE_URL',
    [uri]$LiveNoindexUrl = 'https://vinhlong360.vn/',
    [int]$LocalPort = 15432,
    [string]$ArtifactParent = "$HOME\Documents\vinhlong360-stage-b"
)
```

Add these static assertions so status words such as `APPLY_NOT_RUN` are allowed but executable forbidden paths are not:

```python
def test_runner_has_no_stage_c_export_deploy_or_secret_read_path() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    for forbidden in (
        "migrate_entity_status.py apply",
        "migrate_entity_status.py rollback",
        "scripts/export_data.py",
        "scripts/deploy.sh",
        "/opt/vinhlong360/.env",
        "cat .env",
    ):
        assert forbidden not in source
    assert "APPLY_NOT_RUN" in source
```

Add a fake-tool harness through environment variables used only in tests:

```python
def test_runner_cleanup_executes_when_plan_fails(fake_stage_b_tools, tmp_path: Path) -> None:
    fake_stage_b_tools.plan_exit_code = 17
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode != 0
    assert fake_stage_b_tools.events == [
        "verify-source-noindex",
        "create-root",
        "create-role",
        "open-tunnel",
        "verify-readonly-identity",
        "backup",
        "plan",
        "drop-role",
        "close-tunnel",
        "verify-role-absent",
        "verify-tunnel-absent",
    ]
    assert not list(tmp_path.rglob("stage-b-attestation.json"))
```

Add success ordering, role-creation failure, backup failure, cleanup failure, noindex failure, occupied local port, and attestation failure. In all cases, assert no apply/export/deploy event and no password in stdout/stderr/event files/process arguments.

Lock the failure matrix with:

```python
@pytest.mark.parametrize(
    "failure_stage,attestation_expected",
    [
        ("noindex", False),
        ("create-role", False),
        ("occupied-port", False),
        ("open-tunnel", False),
        ("backup", False),
        ("plan", False),
        ("drop-role", False),
        ("close-tunnel", False),
        ("attestation", True),
    ],
)
def test_runner_failure_matrix_is_cleanup_first_and_never_runs_stage_c(
    fake_stage_b_tools, tmp_path: Path, failure_stage: str, attestation_expected: bool
) -> None:
    fake_stage_b_tools.failure_stage = failure_stage
    result = fake_stage_b_tools.run(tmp_path)
    combined = result.stdout + result.stderr + fake_stage_b_tools.log_text
    assert result.returncode != 0
    assert ("write-attestation" in fake_stage_b_tools.events) is attestation_expected
    assert not ({"apply", "rollback", "export", "deploy"} & set(fake_stage_b_tools.events))
    assert fake_stage_b_tools.password not in combined
    if "create-role" in fake_stage_b_tools.events:
        assert "drop-role" in fake_stage_b_tools.events
    if "open-tunnel" in fake_stage_b_tools.events:
        assert "close-tunnel" in fake_stage_b_tools.events
```

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/test_run_entity_status_stage_b.py -q
```

Expected: FAIL because the runner does not exist.

- [ ] **Step 3: Implement fail-closed orchestration with a mandatory `finally` path**

The runner must perform this exact order:

1. Require PowerShell 7+, clean Git worktree, and record `git rev-parse HEAD`.
2. Verify live URL returns status 200, exact `X-Robots-Tag: noindex, follow`, and exactly one root robots meta `noindex, follow`; compute response-body SHA-256.
3. Create a new timestamped root under `ArtifactParent` through `secure_stage_b_artifacts.ps1 -Mode CreateRoot` before any dump/plan/listing/attestation write.
4. Generate a role name by concatenating `vl360_stage_b_` with 32 lowercase hexadecimal characters and hold a 32-byte cryptographic password only in a local variable.
5. Send role SQL over SSH stdin to `sudo -u postgres psql --no-psqlrc --set ON_ERROR_STOP=1 --dbname vinhlong360`; the SSH argv contains no password or SQL.
6. Role SQL grants only login, database CONNECT, inherited membership in `pg_read_all_data`, and EXECUTE on `pg_catalog.pg_control_system()`; sets `default_transaction_read_only=on`, `statement_timeout=5min`, two-hour `VALID UNTIL`, and connection limit 2; explicitly sets NOSUPERUSER/NOCREATEDB/NOCREATEROLE/INHERIT/NOREPLICATION/NOBYPASSRLS.
7. Ensure `127.0.0.1:15432` is free, open `ssh -N -L 127.0.0.1:15432:127.0.0.1:5432`, record PID, and verify listener ownership plus tunnel process health.
8. Build the URL only in memory, set `Env:VL360_STAGE_B_DATABASE_URL` at Process scope, verify identity v2 and `transaction_read_only=on`, run exactly one backup with `--out-dir "$Root\backup"`, require exactly one generated backup-run directory, then run exactly one `published-v1` plan to `$Root\published-v1-plan.json`.
9. Run `pg_restore --list` once against the generated `backup\yyyyMMdd-HHmmss\postgres.dump`, capture stdout in memory, create root-level `pg-restore-list.txt` with `FileMode.CreateNew`, flush it, and verify its SHA-256 equals the nested manifest listing hash.
10. In `finally`, remove the process environment value, revoke/drop the temporary role through SSH stdin, stop the exact tunnel PID, and freshly verify both role and listener/process absence.
11. If and only if backup, plan, listing, role cleanup, and tunnel cleanup succeeded, normalize/verify every artifact ACL and pipe bounded evidence JSON to `stage_b_attestation.py`.
12. Normalize/verify ACLs again after attestation, recompute the attestation SHA-256, print the artifact root and non-secret hashes, and print `APPLY_NOT_RUN`.

Use a .NET `System.Diagnostics.Process` helper for SSH/psql stdin so password-bearing SQL never appears in argv. Set `RedirectStandardInput`, `RedirectStandardOutput`, and `RedirectStandardError`; never echo the SQL. Redact stderr by refusing to print input or connection URLs.

The role creation SQL is generated with validated role/database identifiers and psql variables for the password and expiry. The cleanup SQL is independently generated from the validated role identifier and executes even when backup or plan fails. Cleanup failure blocks attestation and returns nonzero.

The test-only fake-tool seam must be enabled only when `VL360_STAGE_B_TEST_MODE=1` and all fake executables resolve under a pytest-owned temporary directory; production mode ignores those variables.

- [ ] **Step 4: Run GREEN and inspect command-line secrecy**

```powershell
python -m pytest tests/test_run_entity_status_stage_b.py -q
python -m pytest tests/test_secure_stage_b_artifacts.py tests/test_stage_b_attestation.py -q
```

Expected: PASS; fake-tool events have exact order; every failure runs cleanup; cleanup failure prevents attestation; no secret appears in logs, argv captures, artifacts, or persistent environment.

- [ ] **Step 5: Commit the runner**

```powershell
git add scripts/run_entity_status_stage_b.ps1 tests/test_run_entity_status_stage_b.py
git commit -m "feat: orchestrate fail-closed Stage B evidence"
```

- [ ] **Step 6: Run fresh spec review, then fresh quality review**

Spec review traces all 12 ordered stages and confirms no apply/export/deploy path. Quality review checks PowerShell quoting, process lifecycle, PID/listener ownership, environment restoration, role SQL privilege minimality, stderr redaction, cleanup idempotence, and test-mode isolation.

## Task 10: Replace the manual Stage B runbook with identity-v2 guardrails

**Files:**
- Modify: `docs/runbooks/entity-published-status-migration.md:3-121,276-282`
- Modify: `tests/test_entity_status_migration_guardrails.py:271-330`

- [ ] **Step 1: Write failing runbook contract assertions**

Extend `test_runbook_is_fail_closed_and_reproducible()` with exact required phrases/snippets:

```python
for phrase in (
    "postgres-cluster-v2",
    "database_oid",
    "system_identifier",
    "stage-b-attestation.json",
    "secure_stage_b_artifacts.ps1",
    "run_entity_status_stage_b.ps1",
    "role_absent = true",
    "listener_absent",
    "APPLY_NOT_RUN",
    "target-identity-v1-not-unique",
    "Stage C remains unauthorized",
):
    assert phrase in runbook

for forbidden in (
    "/opt/vinhlong360/.env",
    "cat /opt/vinhlong360/.env",
    "NUXT_PUBLIC_SITE_NOINDEX=false",
):
    assert forbidden not in runbook
```

Assert the Stage B executable block invokes only:

```powershell
& pwsh -NoLogo -NoProfile -File scripts/run_entity_status_stage_b.ps1
```

and does not directly call `backup_data.py`, `migrate_entity_status.py apply`, rollback, export, or deploy.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/test_entity_status_migration_guardrails.py -q
```

Expected: FAIL because the current runbook still documents manual v1 Stage B commands and lacks attestation/cleanup/supersession gates.

- [ ] **Step 3: Rewrite Stage B and strengthen safety text**

Keep the existing Stage A, Stage C, export, rollback, and STOP separation, but replace Stage B with:

```powershell
$ErrorActionPreference = 'Stop'
& pwsh -NoLogo -NoProfile -File scripts/run_entity_status_stage_b.ps1
if ($LASTEXITCODE -ne 0) { throw 'Stage B runner failed; preserve evidence and STOP.' }
```

Document the exact review inventory:

- v2 identity fields and fingerprint equal across plan, manifest, and attestation;
- plan, manifest, dump, restore-list, and attestation SHA-256;
- source HEAD and clean worktree;
- live noindex URL/status/header/meta/body hash and freshness;
- protected ACL object/principal counts;
- temporary role expiry and fresh `role_absent = true` timestamp;
- tunnel endpoint/PID and fresh process/listener absence timestamp;
- all operation flags false and terminal `APPLY_NOT_RUN`;
- v1 package is immutable but superseded for reason `target-identity-v1-not-unique`;
- Stage C remains unauthorized until exact new v2 evidence is separately approved.

The runbook must state that operators never read/copy production `DATABASE_URL`; the runner creates the temporary credential in memory and sends role SQL through SSH stdin.

- [ ] **Step 4: Run GREEN**

```powershell
python -m pytest tests/test_entity_status_migration_guardrails.py -q
```

Expected: PASS; source noindex guard remains green and the runbook contains no direct production secret-reading or Stage C shortcut.

- [ ] **Step 5: Commit runbook and guardrails**

```powershell
git add docs/runbooks/entity-published-status-migration.md tests/test_entity_status_migration_guardrails.py
git commit -m "docs: require identity v2 Stage B attestation"
```

- [ ] **Step 6: Run fresh spec review, then fresh quality review**

Reviewers verify command reproducibility, stop boundaries, global noindex, exact evidence inventory, v1 supersession language, and absence of production secret instructions.

## Task 11: Run full repository evidence before production access

**Files:**
- No source changes expected
- Evidence only: terminal output captured in the task review record

- [ ] **Step 1: Record protected data baselines**

```powershell
$DataJsonPath = (Resolve-Path 'web/data.json').Path
$RepositoryDbPath = (Resolve-Path 'agent/data/vinhlong360.db').Path
$DataJsonBefore = (Get-FileHash -LiteralPath $DataJsonPath -Algorithm SHA256).Hash
$RepositoryDbBefore = (Get-FileHash -LiteralPath $RepositoryDbPath -Algorithm SHA256).Hash
git status --short
```

Expected: worktree clean; both hashes recorded. Do not run a data backup because Tasks 1-11 do not mutate project data.

- [ ] **Step 2: Run focused identity, backup, migration, ACL, attestation, runner, and guard tests**

```powershell
python -m pytest tests/test_postgres_target.py tests/test_backup_data.py tests/test_migrate_entity_status.py tests/test_secure_stage_b_artifacts.py tests/test_stage_b_attestation.py tests/test_run_entity_status_stage_b.py tests/test_entity_status_migration_guardrails.py -q
```

Expected: PASS with only explicitly platform-gated skips.

- [ ] **Step 3: Run disposable PostgreSQL integration**

```powershell
python -m pytest tests/test_migrate_entity_status_postgres.py -q -m entity_status_postgres
```

Expected: PASS when `ENTITY_STATUS_TEST_DATABASE_URL` and `ENTITY_STATUS_TEST_CONFIRM=disposable` are present; otherwise safe SKIP. A skip is not sufficient for production Stage B approval: obtain a disposable URL and rerun before Task 12.

- [ ] **Step 4: Run full default regression, Ruff, complexity, and whitespace checks**

```powershell
python -m pytest -q
python -m ruff check scripts/postgres_target.py scripts/backup_data.py scripts/migrate_entity_status.py scripts/stage_b_attestation.py tests/test_postgres_target.py tests/test_backup_data.py tests/test_migrate_entity_status.py tests/test_migrate_entity_status_postgres.py tests/test_secure_stage_b_artifacts.py tests/test_stage_b_attestation.py tests/test_run_entity_status_stage_b.py tests/test_entity_status_migration_guardrails.py
python -m ruff check scripts/postgres_target.py scripts/backup_data.py scripts/migrate_entity_status.py scripts/stage_b_attestation.py --select C901 --config lint.mccabe.max-complexity=12
git diff --check 8673cac..HEAD
```

Expected: no new failure versus the documented baseline, Ruff exits 0, complexity does not exceed the repository ratchet, and diff check exits 0.

- [ ] **Step 5: Prove project data and global noindex source did not change**

```powershell
$DataJsonAfter = (Get-FileHash -LiteralPath $DataJsonPath -Algorithm SHA256).Hash
$RepositoryDbAfter = (Get-FileHash -LiteralPath $RepositoryDbPath -Algorithm SHA256).Hash
if ($DataJsonAfter -ne $DataJsonBefore) { throw 'web/data.json changed during identity-v2 engineering.' }
if ($RepositoryDbAfter -ne $RepositoryDbBefore) { throw 'repository SQLite changed during identity-v2 engineering.' }
python -m pytest tests/test_entity_status_migration_guardrails.py::test_global_noindex_default_and_authoritative_header_are_executable_code -q
git status --short
```

Expected: hashes unchanged, noindex source guard PASS, worktree clean.

- [ ] **Step 6: Run a final fresh spec review and final fresh quality review over the complete range**

Use `8673cac..HEAD` as the review range. The spec reviewer checks every acceptance criterion in the approved design. The quality reviewer checks cross-task interfaces, failure ordering, secret handling, Windows/Python process boundaries, and test isolation. Fix findings in small reviewed commits and rerun Steps 2-5.

## Task 12: Regenerate protected production Stage B and supersede v1 evidence

**Files:**
- No tracked source changes expected
- Create external artifacts under a new `C:\Users\Administrator\Documents\vinhlong360-stage-b\yyyyMMddTHHmmssZ` directory generated from the current UTC time
- Create external marker `C:\Users\Administrator\Documents\vinhlong360-stage-b\20260715T225652\superseded-by-postgres-identity-v2.json` only after the new package passes both reviews

- [ ] **Step 1: Stop for the production Stage B checkpoint**

Present the owner with:

- clean branch HEAD;
- complete Task 11 test output;
- final spec and quality approvals;
- live target `vinhlong360.vn` and SSH target `root@66.42.57.202`;
- explicit statement: backup + plan + attestation only, global noindex retained, no Stage C/apply/rollback/export/deploy.

Do not continue until the owner explicitly authorizes this exact Stage B run.

- [ ] **Step 2: Verify live global noindex before opening SSH**

```powershell
$Response = Invoke-WebRequest -Uri 'https://vinhlong360.vn/' -Method Get -MaximumRedirection 0 -SkipHttpErrorCheck
if ([int]$Response.StatusCode -ne 200) { throw 'Live root did not return 200.' }
if ([string]$Response.Headers['X-Robots-Tag'] -ne 'noindex, follow') { throw 'Live X-Robots-Tag mismatch.' }
```

Expected: status 200 and exact header. The runner repeats and persists the full header/meta/body evidence.

- [ ] **Step 3: Execute exactly one reviewed Stage B runner**

```powershell
& pwsh -NoLogo -NoProfile -File scripts/run_entity_status_stage_b.ps1
if ($LASTEXITCODE -ne 0) { throw 'Stage B failed; preserve all evidence and STOP.' }
```

Expected: one fresh protected root, one backup, one plan, one restore list, one attestation, temporary role absent, tunnel absent, and terminal `APPLY_NOT_RUN`. Do not retry automatically; a failed run requires read-only diagnosis and a fresh root/role/tunnel.

- [ ] **Step 4: Independently review the new package without connecting to production**

Set `$Root` to the exact path printed by the runner, then run:

```powershell
& pwsh -NoLogo -NoProfile -File scripts/secure_stage_b_artifacts.ps1 -Mode Verify -Root $Root
if ($LASTEXITCODE -ne 0) { throw 'Final ACL verification failed.' }

$Plan = Join-Path $Root 'published-v1-plan.json'
$BackupParent = Join-Path $Root 'backup'
$BackupRuns = @(Get-ChildItem -LiteralPath $BackupParent -Directory -Force)
if ($BackupRuns.Count -ne 1) { throw 'Expected exactly one Stage B backup run directory.' }
$Manifest = Join-Path $BackupRuns[0].FullName 'manifest.json'
$Dump = Join-Path $BackupRuns[0].FullName 'postgres.dump'
$Listing = Join-Path $Root 'pg-restore-list.txt'
$Attestation = Join-Path $Root 'stage-b-attestation.json'

Get-FileHash -Algorithm SHA256 -LiteralPath $Plan, $Manifest, $Dump, $Listing, $Attestation
& 'C:\Program Files\PostgreSQL\16\bin\pg_restore.exe' --list $Dump | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Independent pg_restore --list failed.' }
'{}' | & python scripts/stage_b_attestation.py --artifact-root $Root --out $Attestation
if ($LASTEXITCODE -eq 0) { throw 'Attestation writer unexpectedly overwrote immutable evidence.' }
```

Review exact equality of plan/manifest/attestation identity and fingerprint, candidate count/hash, schema fingerprint/columns, all exclusions/status accounting, source HEAD, live noindex, role/tunnel cleanup, ACL inventory, freshness, and four false operation flags.

- [ ] **Step 5: Run fresh package spec review, then fresh package quality review**

Use two new agents. The spec reviewer checks every design acceptance criterion against immutable bytes and hashes. The quality reviewer independently recomputes hashes/listing, checks ACLs/hardlinks, searches artifacts for secret markers, and verifies cleanup/noindex evidence. Any mismatch makes the package ineligible; do not repair bytes in place.

- [ ] **Step 6: Add a canonical supersession marker beside the old v1 package**

Only after both new-package reviews approve, create this exact canonical object through `scripts.postgres_target.write_exclusive()`:

```python
{
    "schema": "vinhlong360-stage-b-supersession-v1",
    "reason": "target-identity-v1-not-unique",
    "superseded_artifacts": {
        "plan_sha256": "a125cd72e72990f932ce885179039fbfed11f4dd706520f4d427857e8cd87e16",
        "manifest_sha256": "9259acd54b03b2b5789c01dbbcee6a506f2b23f7b2735249c647769dc5772b26",
        "dump_sha256": "779780a4a2063b895d1309a7a368e4153df06eab2c35c2730df45710c0d93c29",
    },
    "replacement": {
        "artifact_root": str(new_root),
        "target_fingerprint": new_attestation["target"]["target_fingerprint"],
        "attestation_sha256": sha256_file(new_root / "stage-b-attestation.json"),
    },
}
```

Run the ACL normalizer on the old root after writing the marker, then verify that the three old artifact hashes above and all old hardlink identities remain unchanged. Record the new marker hash. Do not delete or rename the v1 evidence.

- [ ] **Step 7: Hand the exact Stage B decision record to the owner and stop**

Report:

- new artifact root;
- v2 target fingerprint;
- plan, manifest, dump, restore-list, attestation, and supersession-marker SHA-256;
- candidate count and candidate-ID hash;
- source HEAD;
- exact live noindex result;
- role and tunnel absence timestamps;
- `APPLY_NOT_RUN`.

End with: `Stage C remains unauthorized.` Do not run apply, rollback, export, deploy, indexing activation, or any application-row mutation.

## Completion Criteria

This plan is complete only when:

- every producer and consumer uses exact `postgres-cluster-v2` identity;
- a system identifier or database OID change changes the target fingerprint;
- every identity-v1 plan/manifest/apply-report path fails with an explicit revision error before hashes, confirmations, connections, or locks;
- apply and rollback verify live identity before lock and preserve all existing post-lock drift/audit checks;
- disposable PostgreSQL proves the restricted-role success and permission-denied paths;
- the artifact root is protected before sensitive output and every final descendant has an exact protected ACL;
- attestation is canonical, fresh, hash-consistent, secret-free, and blocked by any failed noindex/cleanup/ACL/source/artifact gate;
- the temporary production role and SSH tunnel are freshly verified absent;
- production remains globally `noindex, follow`;
- the v1 package remains byte-identical and receives only a protected canonical supersession marker after v2 approval;
- `APPLY_NOT_RUN` remains true and Stage C is still a separate owner decision.
