# Wave 1 Data Integrity Hardening Implementation Plan

> STATUS: proposed - design approved; awaiting execution choice; production remains out of scope

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gia cố đường ghi entity, CTI/cache, cấu hình production và PostgreSQL readiness; bổ sung verifier chỉ đọc và migration `071` hoàn toàn trong workspace, không kết nối production.

**Architecture:** Giữ `Database.upsert_entity()` và `_bulk_load()` làm đường ghi runtime chuẩn. Bổ sung các validator/hàm kiểm tra thuần, stage cache mutation tới sau commit, dùng một registry CTI xác định, và tách hai CLI chỉ đọc cho invariant/source guard để các release test có thể gọi độc lập.

**Tech Stack:** Python 3, Pydantic Settings, SQLite test fixtures, psycopg2/PostgreSQL disposable integration tests, pytest, PostgreSQL SQL migrations.

## Global Constraints

- Chỉ sửa và kiểm thử trong `C:\Code\vinhlong360`; không SSH/VPS, không đọc hoặc ghi production.
- Không áp `071` lên production trong task này.
- Không reconcile/backfill/strip dữ liệu thật; Wave 1 chỉ tạo guard, readiness và verifier.
- Không thêm dependency, service, container hoặc API bên ngoài.
- Development/test tiếp tục hỗ trợ SQLite; production bắt buộc PostgreSQL và `ENTITY_DETAILS_TABLES=true`.
- Mọi output lỗi mới phải redacted: không DSN, secret, entity ID, tên, địa chỉ hoặc payload attributes.
- Bảo toàn mọi thay đổi đang có của người dùng; mỗi commit chỉ stage đúng file của task tương ứng.
- Viết test thất bại trước, xác nhận red, viết implementation tối thiểu, xác nhận green, rồi mới commit.

---

## File Map

- Modify `agent/config.py`: PostgreSQL URL predicate, typed `ENTITY_DETAILS_TABLES`, production validator.
- Modify `agent/database.py`: backend selection, cache-after-commit wiring, schema/trigger readiness.
- Modify `agent/entity_details.py`: CTI table registry, stale-row cleanup, staged cache mutations, duplicate detection.
- Modify `scripts/check_migration_gate.py`: production authority validation.
- Create `agent/migrations/071_restore_entity_rating_triggers.sql`: restore two rating triggers and advance schema version.
- Create `scripts/verify_entity_invariants.py`: aggregate read-only verifier.
- Create `scripts/check_entity_write_paths.py`: AST source guard for direct entity SQL writes.
- Modify existing tests under `tests/` and `agent/tests/`; create focused new test modules listed below.
- Modify `docs/superpowers/specs/2026-07-29-wave1-data-integrity-hardening-design.md`: correct the frozen source-guard inventory to include the existing backfill helper.

### Task 1: Fail-closed production configuration

**Files:**
- Modify: `tests/test_config.py`
- Modify: `agent/config.py:20-142`
- Modify: `agent/database.py:24-42`

**Interfaces:**
- Produces: `is_postgresql_url(value: str) -> bool`
- Produces: `Settings.ENTITY_DETAILS_TABLES: bool`
- Changes: `Settings.validate_production_keys()` rejects non-PostgreSQL production and disabled detail-table reads.
- Consumed later by: Task 4 (`entity_details.reads_enabled`) and Task 5 (runtime backend/schema readiness).

- [ ] **Step 1: Write failing configuration tests**

Add a helper and explicit cases to `tests/test_config.py`; update existing valid-production cases to set the required flag:

```python
def _production_settings(**overrides):
    from config import Settings

    values = {
        "ENVIRONMENT": "production",
        "LLM_API_KEY": "k",
        "LLM_BASE_URL": "https://api.example.com",
        "ADMIN_API_KEY": "a",
        "DATABASE_URL": "postgresql://user:pass@localhost/db",
        "ENTITY_DETAILS_TABLES": True,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("database_url", [
    "postgres://user:pass@localhost/db",
    "postgresql://user:pass@localhost/db",
])
def test_production_accepts_postgresql_urls(database_url):
    assert _production_settings(DATABASE_URL=database_url).is_production is True


def test_production_rejects_sqlite_database_url():
    with pytest.raises(ValueError, match="DATABASE_URL.*PostgreSQL"):
        _production_settings(DATABASE_URL="sqlite:///knowledge.db")


def test_production_requires_entity_detail_tables():
    with pytest.raises(ValueError, match="ENTITY_DETAILS_TABLES"):
        _production_settings(ENTITY_DETAILS_TABLES=False)


def test_development_still_allows_sqlite_and_disabled_detail_tables():
    from config import Settings

    settings = Settings(
        _env_file=None,
        ENVIRONMENT="development",
        DATABASE_URL="sqlite:///knowledge.db",
        ENTITY_DETAILS_TABLES=False,
    )
    assert settings.is_production is False
```

- [ ] **Step 2: Run the tests and confirm red**

Run:

```powershell
python -m pytest tests/test_config.py -q
```

Expected: the valid production helper fails because `ENTITY_DETAILS_TABLES` is not defined/checked yet, and SQLite production is incorrectly accepted.

- [ ] **Step 3: Implement the shared PostgreSQL predicate and validator**

Add near the top of `agent/config.py`:

```python
POSTGRES_URL_PREFIXES = ("postgres://", "postgresql://")


def is_postgresql_url(value: str) -> bool:
    return value.strip().lower().startswith(POSTGRES_URL_PREFIXES)
```

Add the typed setting beside `DATABASE_URL`:

```python
ENTITY_DETAILS_TABLES: bool = False
```

Extend `validate_production_keys()` without emitting the URL:

```python
if not self.DATABASE_URL:
    missing.append("DATABASE_URL")
elif not is_postgresql_url(self.DATABASE_URL):
    missing.append("DATABASE_URL (PostgreSQL required)")
if not self.ENTITY_DETAILS_TABLES:
    missing.append("ENTITY_DETAILS_TABLES=true")
```

In `agent/database.py`, replace the single-prefix backend test:

```python
from config import is_postgresql_url

DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_PG = is_postgresql_url(DATABASE_URL)
```

Do not log or interpolate `DATABASE_URL` in new errors.

- [ ] **Step 4: Run configuration tests and the database import smoke test**

Run:

```powershell
python -m pytest tests/test_config.py agent/tests/test_database.py::test_initialize_creates_core_tables -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```powershell
git add -- tests/test_config.py agent/config.py agent/database.py
git commit -m "fix: fail closed for production data backend"
```

### Task 2: Validate production deployment authority

**Files:**
- Modify: `tests/test_check_migration_gate.py`
- Modify: `tests/launch_safety/test_deploy_migration_prerequisite.py`
- Modify: `scripts/check_migration_gate.py:463-499`

**Interfaces:**
- Produces: `_validate_production_environment(values: Mapping[str, str]) -> None`
- Changes: `_parse_environment(raw: bytes) -> dict[str, str]` validates the full production authority after parsing.
- Preserves: environment pinning remains bounded, no-follow and immutable after publication.

- [ ] **Step 1: Add red tests for authority requirements**

Add to `tests/test_check_migration_gate.py`:

```python
def _production_authority(**overrides: str) -> bytes:
    values = {
        "ENVIRONMENT": "production",
        "DATABASE_URL": "postgresql://gate-user:password-canary@db/vl360",
        "ENTITY_DETAILS_TABLES": "true",
    }
    values.update(overrides)
    return "".join(f"{key}={value}\n" for key, value in values.items()).encode()


def test_environment_authority_accepts_explicit_production_contract():
    gate = _load_checker()
    values = gate._parse_environment(_production_authority())
    assert values["ENVIRONMENT"] == "production"


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"DATABASE_URL=postgresql://db/vl360\nENTITY_DETAILS_TABLES=true\n", "ENVIRONMENT=production"),
        (_production_authority(ENVIRONMENT="development"), "ENVIRONMENT=production"),
        (_production_authority(DATABASE_URL="sqlite:///knowledge.db"), "PostgreSQL"),
        (_production_authority(ENTITY_DETAILS_TABLES="false"), "ENTITY_DETAILS_TABLES=true"),
    ],
)
def test_environment_authority_rejects_nonproduction_contract(raw, message):
    gate = _load_checker()
    with pytest.raises(ValueError, match=message):
        gate._parse_environment(raw)
```

Update authority bytes in `tests/launch_safety/test_deploy_migration_prerequisite.py` so valid fixtures contain all three required lines. Preserve the CRLF/LF parameterization.

- [ ] **Step 2: Run authority tests and confirm red**

Run:

```powershell
python -m pytest tests/test_check_migration_gate.py tests/launch_safety/test_deploy_migration_prerequisite.py -q
```

Expected: new parser cases fail because only `DATABASE_URL` is currently mandatory.

- [ ] **Step 3: Implement the authority validator**

Add to `scripts/check_migration_gate.py`:

```python
POSTGRES_URL_PREFIXES = ("postgres://", "postgresql://")


def _validate_production_environment(values: Mapping[str, str]) -> None:
    if values.get("ENVIRONMENT", "").strip().lower() != "production":
        raise ValueError("environment authority requires ENVIRONMENT=production")
    database_url = values.get("DATABASE_URL", "").strip().lower()
    if not database_url.startswith(POSTGRES_URL_PREFIXES):
        raise ValueError("environment authority requires a PostgreSQL DATABASE_URL")
    if values.get("ENTITY_DETAILS_TABLES", "").strip().lower() != "true":
        raise ValueError("environment authority requires ENTITY_DETAILS_TABLES=true")
```

Call it at the end of `_parse_environment()` after duplicate/unlock validation and before returning `values`.

Do not include the observed URL or value in exception messages.

- [ ] **Step 4: Run migration-gate and deploy-prerequisite tests**

Run:

```powershell
python -m pytest tests/test_check_migration_gate.py tests/launch_safety/test_deploy_migration_prerequisite.py -q
```

Expected: PASS, including pin/reuse and CRLF fixtures.

- [ ] **Step 5: Commit Task 2**

```powershell
git add -- tests/test_check_migration_gate.py tests/launch_safety/test_deploy_migration_prerequisite.py scripts/check_migration_gate.py
git commit -m "fix: require explicit production deployment authority"
```

### Task 3: Remove stale CTI rows on every entity sync

**Files:**
- Modify: `agent/tests/test_entity_details_sync.py`
- Modify: `agent/entity_details.py:22-202`

**Interfaces:**
- Produces: `DETAIL_TABLES: tuple[str, ...]`
- Changes: `sync_entity_details(...)` guarantees zero rows in every non-current CTI table.
- Preserves: universal-column mirroring and current-table upsert behavior.

- [ ] **Step 1: Write failing kind-transition tests**

Add to `agent/tests/test_entity_details_sync.py`:

```python
def test_changing_kind_removes_the_previous_cti_row():
    db.upsert_entity({
        "id": TEST_ID,
        "type": "product",
        "name": "Product",
        "attributes": {"producer": "HTX cũ"},
    })
    assert _fetch_detail("entity_product_details") is not None

    db.upsert_entity({
        "id": TEST_ID,
        "type": "cafe",
        "name": "Cafe",
        "attributes": {"wifi": True},
    })

    assert _fetch_detail("entity_product_details") is None
    assert _fetch_detail("entity_food_details") is not None


def test_changing_to_type_without_cti_removes_all_detail_rows():
    db.upsert_entity({
        "id": TEST_ID,
        "type": "person",
        "name": "Person",
        "attributes": {"role": "Danh nhân"},
    })
    db.upsert_entity({
        "id": TEST_ID,
        "type": "itinerary",
        "name": "Không dùng CTI",
        "attributes": {"duration": "2 ngày"},
    })

    for table in entity_details.DETAIL_TABLES:
        assert _fetch_detail(table) is None
```

Import `entity_details` in the test module.

- [ ] **Step 2: Run the transition tests and confirm red**

Run:

```powershell
python -m pytest agent/tests/test_entity_details_sync.py::test_changing_kind_removes_the_previous_cti_row agent/tests/test_entity_details_sync.py::test_changing_to_type_without_cti_removes_all_detail_rows -q
```

Expected: the old CTI row remains after the type/kind change.

- [ ] **Step 3: Implement one deterministic CTI registry and stale cleanup**

In `agent/entity_details.py`, define once after `KIND_TABLE`:

```python
DETAIL_TABLES = tuple(dict.fromkeys(KIND_TABLE.values()))
```

At the start of CTI handling in `sync_entity_details()`:

```python
kind = KIND_OF_TYPE.get(etype)
table = KIND_TABLE.get(kind or "")
for stale_table in DETAIL_TABLES:
    if stale_table != table:
        _exec(
            conn,
            is_pg,
            f"DELETE FROM {stale_table} WHERE entity_id = {ph}",
            [entity_id],
        )
if not table:
    _cache_put(entity_id, None)
    return
```

Replace every `KIND_TABLE.values()` iteration in delete/load code with `DETAIL_TABLES`. Keep the current-table delete when `det` is empty.

- [ ] **Step 4: Run all entity-detail sync tests**

Run:

```powershell
python -m pytest agent/tests/test_entity_details_sync.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```powershell
git add -- agent/tests/test_entity_details_sync.py agent/entity_details.py
git commit -m "fix: remove stale entity detail rows"
```

### Task 4: Publish detail cache only after commit

**Files:**
- Modify: `agent/tests/test_entity_details_read_flip.py`
- Modify: `agent/tests/test_database.py`
- Modify: `agent/entity_details.py:250-315`
- Modify: `agent/database.py:780-950,1477-1575`

**Interfaces:**
- Produces: `DetailCacheMutation(entity_id: str, detail_items: tuple[tuple[str, Any], ...] | None)`
- Produces: `apply_detail_cache_mutations(mutations, *, reset: bool = False) -> None`
- Changes: `sync_entity_details(...) -> DetailCacheMutation`
- Changes: `delete_entity_details(...) -> DetailCacheMutation`
- Changes: `_bulk_load(...) -> tuple[dict, list[DetailCacheMutation]]`
- Changes: `reads_enabled()` reads the typed singleton setting created in Task 1.

- [ ] **Step 1: Write failing cache rollback, replacement and duplicate tests**

Add focused tests to `agent/tests/test_entity_details_read_flip.py`:

```python
def test_failed_upsert_does_not_publish_uncommitted_detail_cache(flip, monkeypatch):
    db.upsert_entity({
        "id": IDS["product"],
        "type": "product",
        "name": "Before",
        "attributes": {"ocop_star": 3},
    })
    flip()
    real_sync = entity_details.sync_entity_details

    def sync_then_fail(*args, **kwargs):
        real_sync(*args, **kwargs)
        raise RuntimeError("fail after detail SQL")

    monkeypatch.setattr(entity_details, "sync_entity_details", sync_then_fail)
    with pytest.raises(RuntimeError, match="fail after detail SQL"):
        db.upsert_entity({
            "id": IDS["product"],
            "type": "product",
            "name": "After",
            "attributes": {"ocop_star": 5},
        })

    assert _attrs(IDS["product"])["ocop_star"] == 3


def test_load_detail_cache_rejects_multi_cti_without_replacing_old_cache(flip):
    db.upsert_entity({
        "id": IDS["product"],
        "type": "product",
        "name": "Product",
        "attributes": {"producer": "HTX an toàn"},
    })
    flip()
    before = dict(entity_details._DETAIL_CACHE or {})
    with db._conn() as conn:
        conn.execute(
            "INSERT INTO entity_food_details (entity_id, wifi) VALUES (?, ?)",
            (IDS["product"], 1),
        )

    with db._conn() as conn, pytest.raises(RuntimeError, match="multiple detail tables"):
        entity_details.load_detail_cache(conn, False)

    assert entity_details._DETAIL_CACHE == before
```

Add to `agent/tests/test_database.py` a replace-cache test using the existing temp DB and destructive override:

```python
def test_replace_from_json_replaces_detail_cache_instead_of_merging(db, tmp_path, monkeypatch):
    import entity_details

    monkeypatch.setattr(entity_details.settings, "ENTITY_DETAILS_TABLES", True)
    db.reload_entity_details_cache()
    db.upsert_entity(_entity(eid="old-cache", etype="product", attributes={"producer": "Old"}))
    payload = {"entities": [_entity(eid="new-cache", etype="product", attributes={"producer": "New"})], "relationships": [], "itineraries": []}
    path = tmp_path / "replace-cache.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB_REPLACE", "1")

    db.replace_from_json(str(path))

    assert "old-cache" not in (entity_details._DETAIL_CACHE or {})
    assert (entity_details._DETAIL_CACHE or {})["new-cache"]["producer"] == "New"
```

Change existing detail-read fixtures that set `ENTITY_DETAILS_TABLES` via `monkeypatch.setenv` to set `entity_details.settings.ENTITY_DETAILS_TABLES` instead. Restore the prior boolean in fixture teardown.

- [ ] **Step 2: Run the new cache tests and confirm red**

Run:

```powershell
python -m pytest agent/tests/test_entity_details_read_flip.py agent/tests/test_database.py::test_replace_from_json_replaces_detail_cache_instead_of_merging -q
```

Expected: cache changes before rollback, duplicate CTI silently overwrites, or replacement leaves the old cached entity.

- [ ] **Step 3: Add staged cache mutation primitives**

In `agent/entity_details.py`:

```python
from dataclasses import dataclass
from typing import Any, Iterable
from config import settings


@dataclass(frozen=True)
class DetailCacheMutation:
    entity_id: str
    detail_items: tuple[tuple[str, Any], ...] | None

    @classmethod
    def from_detail(cls, entity_id: str, detail: dict | None):
        items = None if not detail else tuple(sorted(detail.items()))
        return cls(entity_id=entity_id, detail_items=items)


def apply_detail_cache_mutations(
    mutations: Iterable[DetailCacheMutation], *, reset: bool = False
) -> None:
    global _DETAIL_CACHE
    if _DETAIL_CACHE is None:
        return
    updated = {} if reset else dict(_DETAIL_CACHE)
    for mutation in mutations:
        if mutation.detail_items is None:
            updated.pop(mutation.entity_id, None)
        else:
            updated[mutation.entity_id] = dict(mutation.detail_items)
    _DETAIL_CACHE = updated
```

Change `sync_entity_details()` and `delete_entity_details()` to return a mutation and remove every in-transaction `_cache_put()` call. Change `reads_enabled()` to:

```python
def reads_enabled() -> bool:
    return settings.ENTITY_DETAILS_TABLES
```

- [ ] **Step 4: Detect duplicate CTI before publishing cache**

Build `cache`, `locations`, `duplicate_ids` and `duplicate_tables` locally in `load_detail_cache()`. Do not assign `_DETAIL_CACHE` until the scan is complete:

```python
if duplicate_ids:
    tables = ", ".join(sorted(duplicate_tables))
    raise RuntimeError(
        f"CTI cache load rejected: {len(duplicate_ids)} entities occur in "
        f"multiple detail tables ({tables})"
    )
_DETAIL_CACHE = cache
```

The message may contain table names and a count, but never entity IDs or row values.

- [ ] **Step 5: Wire cache publication after transaction success**

In `Database.upsert_entity()`:

```python
with self._conn() as conn:
    self._write_entity_row(...)
    mutation = _entity_details.sync_entity_details(...)
_entity_details.apply_detail_cache_mutations([mutation])
```

Restructure `delete_entity()` so it stores `deleted` and `mutation`, exits the connection context, applies the mutation, then returns `deleted`.

Change `_bulk_load()` to collect and return mutations:

```python
mutations = [
    _entity_details.sync_entity_details(
        conn,
        self._use_pg,
        entity["id"],
        entity["type"],
        entity.get("attributes") or {},
    )
    for entity in data.get("entities", [])
]
return result, mutations
```

In `replace_from_json()`, unpack inside the transaction and atomically replace cache only after commit:

```python
with self._conn() as conn:
    self._clear_knowledge_tables(conn)
    result, mutations = self._bulk_load(conn, data)
_entity_details.apply_detail_cache_mutations(mutations, reset=True)
```

- [ ] **Step 6: Run CTI/cache and database transaction tests**

Run:

```powershell
python -m pytest agent/tests/test_entity_details_sync.py agent/tests/test_entity_details_read_flip.py agent/tests/test_entity_details_cleanup.py agent/tests/test_database.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 4**

```powershell
git add -- agent/tests/test_entity_details_read_flip.py agent/tests/test_entity_details_cleanup.py agent/tests/test_database.py agent/entity_details.py agent/database.py
git commit -m "fix: publish entity detail cache after commit"
```

### Task 5: Restore rating triggers and enforce PostgreSQL readiness

**Files:**
- Create: `agent/migrations/071_restore_entity_rating_triggers.sql`
- Create: `agent/tests/test_pg_schema_readiness.py`
- Create: `tests/test_migration_071_rating_triggers.py`
- Modify: `agent/tests/test_database.py:92-105`
- Modify: `agent/tests/test_migration_apply.py`
- Modify: `tests/test_check_migration_gate.py`
- Modify: `tests/test_release_quality_gates.py`
- Modify: `agent/database.py:40-190,581-650`

**Interfaces:**
- Produces: `PG_REQUIRED_SCHEMA_VERSION = 71`
- Produces: `PG_REQUIRED_TRIGGERS: dict[str, str]`
- Produces: `_pg_missing_triggers(cur) -> list[str]`
- Produces: `_pg_schema_snapshot(conn) -> dict[str, object]`
- Changes: `_verify_pg_schema()` and `pg_schema_status()` consume the same snapshot/issues.

- [ ] **Step 1: Write static migration tests and update latest-version expectations**

Create `tests/test_migration_071_rating_triggers.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "agent" / "migrations" / "071_restore_entity_rating_triggers.sql"


def test_migration_071_restores_both_rating_triggers_only():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "DROP TRIGGER IF EXISTS trg_entity_ratings ON posts" in sql
    assert "AFTER INSERT OR UPDATE ON posts" in sql
    assert "WHEN (NEW.post_type = 'review')" in sql
    assert "DROP TRIGGER IF EXISTS trg_entity_ratings_del ON posts" in sql
    assert "AFTER DELETE ON posts" in sql
    assert "WHEN (OLD.post_type = 'review')" in sql
    assert sql.count("EXECUTE FUNCTION update_entity_ratings()") == 2
    assert "CREATE OR REPLACE FUNCTION update_entity_ratings" not in sql
    assert "UPDATE entity_ratings" not in sql
    assert "VALUES ('agent', 71, '071_restore_entity_rating_triggers.sql'" in sql
```

Update every fixed `070`/`70` latest expectation in:

- `tests/test_check_migration_gate.py`
- `tests/test_release_quality_gates.py`
- `agent/tests/test_migration_apply.py`

Keep the existing `070` comment-trigger behavioral assertions unchanged.

- [ ] **Step 2: Write failing runtime readiness tests**

Create `agent/tests/test_pg_schema_readiness.py` with pure helper coverage:

```python
from database import (
    PG_REQUIRED_SCHEMA_VERSION,
    PG_REQUIRED_TRIGGERS,
    _pg_missing_triggers,
    _pg_schema_issues,
)


class TriggerCursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""
        self.params = None

    def execute(self, sql, params=None):
        self.sql = " ".join(sql.split())
        self.params = params

    def fetchall(self):
        return self.rows


def test_required_schema_version_and_rating_trigger_registry():
    assert PG_REQUIRED_SCHEMA_VERSION == 71
    assert PG_REQUIRED_TRIGGERS == {
        "trg_entity_ratings": "posts",
        "trg_entity_ratings_del": "posts",
    }


def test_missing_trigger_scan_requires_name_and_table():
    cursor = TriggerCursor([
        {"trigger_name": "trg_entity_ratings", "table_name": "posts"},
        {"trigger_name": "trg_entity_ratings_del", "table_name": "wrong_table"},
    ])
    assert _pg_missing_triggers(cursor) == ["trg_entity_ratings_del on posts"]
    assert "pg_catalog.pg_trigger" in cursor.sql


def test_schema_issues_include_missing_triggers():
    issues = _pg_schema_issues([], [], ["trg_entity_ratings on posts"], 71)
    assert issues == ["missing triggers: trg_entity_ratings on posts"]
```

- [ ] **Step 3: Run new schema/migration tests and confirm red**

Run:

```powershell
python -m pytest tests/test_migration_071_rating_triggers.py agent/tests/test_pg_schema_readiness.py tests/test_check_migration_gate.py::test_db_gate_requires_the_latest_version_from_the_supplied_migration_chain tests/test_release_quality_gates.py::test_migration_gate_static_contracts_pass_current_repo -q
```

Expected: migration file/constants/helpers are absent and latest-version assertions fail.

- [ ] **Step 4: Create migration 071**

Create `agent/migrations/071_restore_entity_rating_triggers.sql`:

```sql
-- Restore rating trigger wiring. Migration 070 owns the corrected function body.
DROP TRIGGER IF EXISTS trg_entity_ratings ON posts;
CREATE TRIGGER trg_entity_ratings
    AFTER INSERT OR UPDATE ON posts
    FOR EACH ROW
    WHEN (NEW.post_type = 'review')
    EXECUTE FUNCTION update_entity_ratings();

DROP TRIGGER IF EXISTS trg_entity_ratings_del ON posts;
CREATE TRIGGER trg_entity_ratings_del
    AFTER DELETE ON posts
    FOR EACH ROW
    WHEN (OLD.post_type = 'review')
    EXECUTE FUNCTION update_entity_ratings();

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 71, '071_restore_entity_rating_triggers.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE
        WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration
        ELSE schema_version.migration
    END,
    updated_at = NOW();
```

- [ ] **Step 5: Implement trigger-aware runtime schema snapshots**

In `agent/database.py`:

```python
PG_REQUIRED_SCHEMA_VERSION = 71
PG_REQUIRED_TRIGGERS = {
    "trg_entity_ratings": "posts",
    "trg_entity_ratings_del": "posts",
}
```

Add `_pg_missing_triggers(cur)` that queries `pg_catalog.pg_trigger`, `pg_catalog.pg_class` and `pg_catalog.pg_namespace`, filters `NOT tg.tgisinternal` and `public`, and compares `(trigger_name, table_name)` pairs with the registry.

Extend the issue builder signature:

```python
def _pg_schema_issues(
    missing_tables: list[str],
    missing_columns: list[str],
    missing_triggers: list[str],
    schema_version: int,
) -> list[str]:
    issues = []
    if missing_tables:
        issues.append("missing tables: " + ", ".join(missing_tables))
    if missing_columns:
        issues.append("missing columns: " + ", ".join(missing_columns))
    if missing_triggers:
        issues.append("missing triggers: " + ", ".join(missing_triggers))
    if schema_version < PG_REQUIRED_SCHEMA_VERSION:
        issues.append(
            f"schema_version agent={schema_version}, expected >= {PG_REQUIRED_SCHEMA_VERSION}"
        )
    return issues
```

Extract `_pg_schema_snapshot(conn)` so `_verify_pg_schema()` and `pg_schema_status()` consume the same `schema_version`, missing lists and `issues`. `pg_schema_status()` returns `required_triggers` and `missing_triggers`, but no DSN.

- [ ] **Step 6: Add PostgreSQL integration assertions without using production**

In `agent/tests/test_migration_apply.py`, add a PG-only test:

```python
@pg_only
def test_migration_071_rating_triggers_have_expected_events():
    with db._conn() as conn:
        rows = db._fetchall(
            conn,
            "SELECT trigger_name, event_manipulation FROM information_schema.triggers "
            "WHERE event_object_schema = 'public' "
            "AND trigger_name IN ('trg_entity_ratings', 'trg_entity_ratings_del')",
            (),
        )
    events = {}
    for row in rows:
        item = db._row_to_dict(row)
        events.setdefault(item["trigger_name"], set()).add(item["event_manipulation"])
    assert events == {
        "trg_entity_ratings": {"INSERT", "UPDATE"},
        "trg_entity_ratings_del": {"DELETE"},
    }
```

This test may run only against a disposable PostgreSQL database initialized by the test migration chain. Never point it at production.

- [ ] **Step 7: Run schema, migration and trigger suites**

Run local/static tests:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
$env:ENVIRONMENT='test'
python -m pytest agent/tests/test_pg_schema_readiness.py tests/test_migration_071_rating_triggers.py tests/test_check_migration_gate.py tests/test_release_quality_gates.py agent/tests/test_migration_apply.py agent/tests/test_trigger_correctness.py -q
```

Expected: local/static tests PASS; PostgreSQL-only tests SKIP unless a disposable local DB was explicitly configured.

- [ ] **Step 8: Commit Task 5**

```powershell
git add -- agent/migrations/071_restore_entity_rating_triggers.sql agent/tests/test_pg_schema_readiness.py tests/test_migration_071_rating_triggers.py agent/tests/test_database.py agent/tests/test_migration_apply.py tests/test_check_migration_gate.py tests/test_release_quality_gates.py agent/database.py
git commit -m "fix: restore rating triggers and verify schema readiness"
```

### Task 6: Add aggregate read-only entity invariant verifier

**Files:**
- Create: `scripts/verify_entity_invariants.py`
- Create: `tests/test_verify_entity_invariants.py`

**Interfaces:**
- Produces: `InvariantReport(total_entities: int, counts: dict[str, int], schema: dict[str, object])`
- Produces: `evaluate_invariants(entities, details, schema) -> InvariantReport`
- Produces: `run(database_url: str) -> InvariantReport`
- Produces: `main(argv: list[str] | None = None) -> int`
- Exit codes: `0` clean, `1` connected with invariant violations, `2` invalid backend/config/connection.

- [ ] **Step 1: Write failing pure verifier tests**

Create `tests/test_verify_entity_invariants.py` and load the script through `importlib.util`. Cover each counter with small synthetic rows:

```python
def test_equal_conflict_missing_and_uncoercible_counts():
    verifier = _load_verifier()
    entities = [
        {
            "id": "sentinel-equal",
            "type": "product",
            "attributes": {"ocop_star": 4, "producer": "JSON producer"},
            "address": None,
        },
        {
            "id": "sentinel-uncoercible",
            "type": "person",
            "attributes": {"birth_year": "Thế kỷ 19"},
        },
    ]
    details = {
        "entity_product_details": {
            "sentinel-equal": {"entity_id": "sentinel-equal", "ocop_star": 4, "producer": "Column producer"},
        },
        "entity_person_details": {},
    }

    report = verifier.evaluate_invariants(entities, details, _ready_schema())

    assert report.counts["typed_jsonb_equal"] == 1
    assert report.counts["typed_jsonb_conflict"] == 1
    assert report.counts["typed_uncoercible"] == 1
```

Add separate tests for:

```python
assert report.counts["missing_expected_cti"] == 1
assert report.counts["wrong_kind_cti"] == 1
assert report.counts["multi_cti"] == 1
assert report.counts["missing_required_trigger"] == 1
assert report.counts["schema_version_below_required"] == 1
```

Add output/exit tests using sentinel values:

```python
def test_json_output_is_aggregate_and_redacted(capsys, monkeypatch):
    verifier = _load_verifier()
    report = verifier.InvariantReport(
        total_entities=1,
        counts={"typed_jsonb_conflict": 1},
        schema={"version": 70, "required_version": 71},
    )
    monkeypatch.setattr(verifier, "run", lambda _dsn: report)
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret-user:secret-pass@db/prod")

    assert verifier.main(["--json"]) == 1
    output = capsys.readouterr().out
    assert "secret-user" not in output
    assert "secret-pass" not in output
    assert "sentinel" not in output
```

- [ ] **Step 2: Run verifier tests and confirm red**

Run:

```powershell
python -m pytest tests/test_verify_entity_invariants.py -q
```

Expected: module/functions do not exist.

- [ ] **Step 3: Implement the pure invariant evaluator**

Create `scripts/verify_entity_invariants.py`. Import the canonical registries and coercion rules from `agent/entity_details.py` and `agent/entity_schemas.py`; do not copy them.

Use these stable counter keys:

```python
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
```

Define the report:

```python
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
```

For each entity, use `split_typed()`, `KIND_OF_TYPE`, `KIND_TABLE`, `UNIVERSAL`, `KEY_MAP`, `norm_value()` and normalized CTI values. Count individual typed keys for equal/conflict/without-column and individual skipped values for uncoercible. Count CTI invariants per entity.

- [ ] **Step 4: Implement the read-only PostgreSQL loader and CLI boundary**

Require a PostgreSQL URL. Open psycopg2 and immediately set a read-only session:

```python
conn = psycopg2.connect(database_url, connect_timeout=5)
conn.set_session(readonly=True, autocommit=True)
```

Read only:

- required entity columns plus `attributes`;
- every table in `DETAIL_TABLES`;
- current agent schema version;
- required trigger names/tables.

Return only aggregate data. Render JSON with `sort_keys=True`; render text as one line per invariant code/count. At the `main()` boundary:

```python
try:
    report = run(os.environ.get("DATABASE_URL", ""))
except Exception as exc:  # boundary redacts details
    print(f"entity invariant verification failed: {type(exc).__name__}", file=sys.stderr)
    return 2
return 0 if report.ok else 1
```

Never print `str(exc)`, DSN, entity IDs or row values.

- [ ] **Step 5: Run verifier tests**

Run:

```powershell
python -m pytest tests/test_verify_entity_invariants.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 6**

```powershell
git add -- scripts/verify_entity_invariants.py tests/test_verify_entity_invariants.py
git commit -m "feat: add read-only entity invariant verifier"
```

### Task 7: Add AST source guard for direct entity SQL writes

**Files:**
- Create: `scripts/check_entity_write_paths.py`
- Create: `tests/test_entity_write_guard.py`
- Modify: `docs/superpowers/specs/2026-07-29-wave1-data-integrity-hardening-design.md`

**Interfaces:**
- Produces: `WriteSite(path: str, function: str, kind: str, line: int)`
- Produces: `find_write_sites(root: Path) -> list[WriteSite]`
- Produces: `unapproved_write_sites(root: Path) -> list[WriteSite]`
- Exit codes: `0` frozen inventory respected, `1` unapproved direct write found.

- [ ] **Step 1: Correct the approved frozen inventory in the design document**

Add this existing offline helper to the allowlist section of the design spec:

```text
- `_apply_universal()` trong `scripts/backfill_entity_details.py`.
```

This is an inventory correction, not a new runtime exception: the helper already exists and mirrors universal columns during an explicit backfill.

- [ ] **Step 2: Write failing scanner tests**

Create `tests/test_entity_write_guard.py`:

```python
def test_scanner_detects_literal_and_dynamic_entity_writes(tmp_path):
    checker = _load_checker()
    (tmp_path / "unsafe.py").write_text(
        """
def literal(cur):
    cur.execute('UPDATE entities SET attributes = ? WHERE id = ?', ('{}', 'e1'))

def dynamic(cur, field):
    cur.execute(f'UPDATE entities SET {field} = ? WHERE id = ?', ('x', 'e1'))

def insert(cur, cols):
    cur.execute(f'INSERT INTO entities ({cols}) VALUES (?)', ('x',))
""",
        encoding="utf-8",
    )
    sites = checker.find_write_sites(tmp_path)
    assert {(site.function, site.kind) for site in sites} == {
        ("literal", "attributes-update"),
        ("dynamic", "dynamic-update"),
        ("insert", "insert"),
    }


def test_current_repository_has_no_unapproved_direct_entity_writes():
    checker = _load_checker()
    assert checker.unapproved_write_sites(ROOT) == []
```

Add a test proving a path-level allowlist cannot exempt a second function in the same file.

- [ ] **Step 3: Run guard tests and confirm red**

Run:

```powershell
python -m pytest tests/test_entity_write_guard.py -q
```

Expected: checker module does not exist.

- [ ] **Step 4: Implement AST scanning and exact allowlist**

Create `scripts/check_entity_write_paths.py`. Walk Python files only under `agent/` and `scripts/`; ignore `tests`, migrations SQL and generated/cache directories.

Render string nodes as follows:

```python
def _sql_shape(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            part.value if isinstance(part, ast.Constant) else "{}"
            for part in node.values
        )
    return None
```

Normalize whitespace/case. Classify:

- any `INSERT INTO entities` as `insert`;
- `UPDATE entities SET attributes ...` as `attributes-update`;
- `UPDATE entities SET {}` or equivalent dynamic first assignment as `dynamic-update`.

Use an exact `(relative_path, qualified_function, kind)` allowlist:

```python
ALLOWED_WRITE_SITES = {
    ("agent/database.py", "Database._write_entity_row", "insert"),
    ("agent/database.py", "Database._bulk_insert_rows", "insert"),
    ("agent/entity_details.py", "sync_entity_details", "dynamic-update"),
    ("scripts/backfill_entity_details.py", "_apply_universal", "dynamic-update"),
    ("scripts/cleanup_entity_jsonb.py", "_process_entity", "attributes-update"),
    ("scripts/sp2_reconcile.py", "_apply_one_local_fix", "attributes-update"),
    ("scripts/sp2_reconcile.py", "_apply_one_local_fix", "dynamic-update"),
    ("scripts/sp2_reconcile.py", "_prod_patch_one", "attributes-update"),
    ("scripts/sp2_reconcile.py", "_prod_patch_one", "dynamic-update"),
    ("scripts/sp2_reconcile.py", "_prod_insert", "insert"),
    ("scripts/sp6_fill_required.py", "_apply_sqlite", "attributes-update"),
    ("scripts/sp6_fill_required.py", "_apply_pg", "attributes-update"),
    ("scripts/import_enrichment_tips.py", "_apply_enrichment_row", "attributes-update"),
    ("scripts/fix_tinh_moi.py", "apply_sqlite", "dynamic-update"),
    ("scripts/fix_tinh_moi.py", "apply_pg", "attributes-update"),
    ("scripts/fix_tinh_moi.py", "apply_pg", "dynamic-update"),
}
```

If actual AST qualification reveals a different exact function name, fix the allowlist to the real name; do not broaden it to a file wildcard. CLI output may show path/function/line but never source literals or SQL parameter values.

- [ ] **Step 5: Run guard tests and checker CLI**

Run:

```powershell
python -m pytest tests/test_entity_write_guard.py -q
python scripts/check_entity_write_paths.py
```

Expected: both exit `0` and report no unapproved sites.

- [ ] **Step 6: Commit Task 7**

```powershell
git add -- scripts/check_entity_write_paths.py tests/test_entity_write_guard.py docs/superpowers/specs/2026-07-29-wave1-data-integrity-hardening-design.md
git commit -m "test: guard direct entity SQL writes"
```

### Task 8: Run Wave 1 regression and safety verification

**Files:**
- Modify only if a test exposes a Wave 1 regression: the owning implementation/test file from Tasks 1-7.
- Do not modify unrelated user files or relax an existing gate to obtain green.

**Interfaces:**
- Consumes all interfaces from Tasks 1-7.
- Produces a clean verification record in the final handoff; no production state change.

- [ ] **Step 1: Prove the test process cannot inherit a production DSN**

Run in the current PowerShell session before all local suites:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
$env:ENVIRONMENT='test'
$env:ENTITY_DETAILS_TABLES='false'
```

Do not source `.env`, do not open SSH and do not use a VPS hostname.

- [ ] **Step 2: Run the focused Wave 1 suite**

```powershell
python -m pytest tests/test_config.py tests/test_check_migration_gate.py tests/test_release_quality_gates.py tests/test_migration_071_rating_triggers.py tests/test_verify_entity_invariants.py tests/test_entity_write_guard.py agent/tests/test_pg_schema_readiness.py agent/tests/test_entity_details_sync.py agent/tests/test_entity_details_read_flip.py agent/tests/test_entity_details_cleanup.py agent/tests/test_database.py agent/tests/test_migration_apply.py agent/tests/test_trigger_correctness.py -q
```

Expected: PASS; PostgreSQL-only tests SKIP because `DATABASE_URL` was removed.

- [ ] **Step 3: Run launch-safety regressions affected by authority parsing**

```powershell
python -m pytest tests/launch_safety/test_deploy_migration_prerequisite.py tests/launch_safety/test_deploy_readiness.py tests/launch_safety/test_closed_installer.py -q
```

Expected: PASS. If a fixture represents production authority, update it with the three required keys; do not weaken `_parse_environment()`.

- [ ] **Step 4: Run repository gates and the full Python suite**

```powershell
python scripts/check_entity_write_paths.py
python scripts/check_migration_gate.py --migrations agent/migrations
python -m pytest -q
```

Expected: guard/gate exit `0`; full suite PASS with only pre-existing/expected skips.

- [ ] **Step 5: Optionally run PostgreSQL integration only against a verified local disposable DSN**

Skip this step unless `VL360_TEST_DATABASE_URL` is explicitly set and its parsed hostname is `localhost`, `127.0.0.1` or `::1`. Never substitute the production `DATABASE_URL`.

When the guard passes:

```powershell
$env:DATABASE_URL=$env:VL360_TEST_DATABASE_URL
$env:ENVIRONMENT='test'
python scripts/apply_migrations.py --database-url $env:DATABASE_URL
python -m pytest agent/tests/test_migration_apply.py agent/tests/test_trigger_correctness.py -q
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
```

Expected: migration chain reaches 71; both rating triggers exist; trigger behavior tests PASS.

- [ ] **Step 6: Verify no formatting, scope or workspace contamination**

Run:

```powershell
git diff --check
git status --short
Get-Process ssh -ErrorAction SilentlyContinue
Get-NetTCPConnection -RemotePort 22 -ErrorAction SilentlyContinue
```

Expected:

- no whitespace errors;
- only Wave 1 files plus the user's known pre-existing dirty files are present;
- no SSH process or TCP/22 connection created by this work.

- [ ] **Step 7: Final verification commit only if Task 8 required fixes**

If and only if regression fixes were necessary, stage the exact affected Wave 1 files and commit:

```powershell
git add -- agent/config.py agent/database.py agent/entity_details.py scripts/check_migration_gate.py scripts/verify_entity_invariants.py scripts/check_entity_write_paths.py agent/migrations/071_restore_entity_rating_triggers.sql tests/test_config.py tests/test_check_migration_gate.py tests/test_release_quality_gates.py tests/test_migration_071_rating_triggers.py tests/test_verify_entity_invariants.py tests/test_entity_write_guard.py tests/launch_safety/test_deploy_migration_prerequisite.py agent/tests/test_pg_schema_readiness.py agent/tests/test_entity_details_sync.py agent/tests/test_entity_details_read_flip.py agent/tests/test_entity_details_cleanup.py agent/tests/test_database.py agent/tests/test_migration_apply.py agent/tests/test_trigger_correctness.py docs/superpowers/specs/2026-07-29-wave1-data-integrity-hardening-design.md
git commit -m "test: close wave 1 regression gaps"
```

If no files changed in Task 8, do not create an empty commit.

## Completion Checklist

- [ ] Production config fails closed for wrong backend or disabled detail tables.
- [ ] Production deployment authority requires explicit `ENVIRONMENT=production`.
- [ ] Entity kind changes leave at most one CTI row.
- [ ] Cache updates only after commit and rejects multi-CTI input.
- [ ] Migration chain latest is `071_restore_entity_rating_triggers.sql` / version 71.
- [ ] PostgreSQL readiness requires both rating triggers.
- [ ] Verifier is read-only, aggregate-only and redacted.
- [ ] Source guard freezes the exact existing write inventory.
- [ ] Focused tests, launch-safety tests and full suite pass locally.
- [ ] No SSH/VPS or production database connection was used.
