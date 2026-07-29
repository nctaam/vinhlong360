# NP-1.1 Location Remediation Implementation Plan

> STATUS: active - đặc tả đã duyệt; implementation chưa bắt đầu.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cách ly dứt điểm dữ liệu khu vực legacy không thể chứng minh an toàn, sửa precedence của manual `Toàn tỉnh`, và chuyển GPS/IP confirmation sang token stateless v2 bind preference revision mà không thêm bảng one-time token.

**Architecture:** Migration 073 thêm remediation state, provenance metadata, revision `BIGINT` và PostgreSQL constraints; runtime dùng một canonical region validator tại mọi read/final-write/import boundary. Resolver phát HMAC token v2 gắn user + revision, còn read guard và bounded worker tự cách ly drift về `default/off` mà không làm mất interests, consent history hoặc workspace.

**Tech Stack:** Python 3, FastAPI/Pydantic, PostgreSQL/psycopg2, SQLite test adapter, Nuxt 3/Vue 3/TypeScript, Vitest + Nuxt Test Utils, pytest, PowerShell, existing feature flags and scheduler.

## Global Constraints

- Raw GPS/IP không được lưu trong DB, frontend state, audit, cache, response telemetry hoặc log.
- Precedence chính xác: `manual > gps > ip > default`; manual `Toàn tỉnh` có `region_id = NULL` vẫn là manual.
- Explicit interests luôn thắng inferred interests và phải được giữ nguyên khi quarantine location.
- Tắt location giữ manual region nhưng chặn GPS/IP.
- Migration 073 giữ `explicit_interests`, `personalization_enabled`, `recommendation_reset_at`, `consent_version`, consent history và workspace.
- `location_reconfirm_required` là public read-only state; `location_provenance_version` là internal-only metadata.
- Resolver provenance mới là `resolver-v2`; token purpose mới là `location-confirmation-v2`.
- Token v2 bind `user_id`, `issued_at`, `expires_at`, `preference_revision` và normalized region; TTL là `300` giây.
- Token stale trả `409`; tamper/expiry/cross-user/contract invalid trả `422`.
- Không thêm one-time token table, nonce table/store, used-token cache, token column hoặc token cleanup job.
- Preference revision dùng PostgreSQL `BIGINT` nhưng bị chặn ở `Number.MAX_SAFE_INTEGER = 9_007_199_254_740_991`.
- Frontend tests phải mount component/composable thật; cấm `readFileSync(...).toContain(...)` hoặc source-text assertions.
- Browser/Stitch rendered verification và homepage redesign không thuộc scope NP-1.1.
- Official backend runner chỉ được ghi pass nếu thực sự chạy lại; affected suites không được mô tả là tương đương.
- Mỗi task dùng strict RED -> GREEN, fresh implementer, spec reviewer, code-quality reviewer và commit riêng; cập nhật ledger `.superpowers/sdd/2026-07-29-np1-1-location-remediation/progress.md` sau mỗi gate.

---

## File Structure and Ownership

| File | Responsibility in NP-1.1 |
|---|---|
| `agent/migrations/073_location_preference_remediation.sql` | Schema 73, legacy quarantine, revision widening and PostgreSQL constraints |
| `agent/database.py` | Release readiness contract at schema 73 |
| `agent/user_preferences.py` | Canonical invariant, public/internal projection, read/final-write guard and bounded worker |
| `agent/location_resolver.py` | Revision-bound token v2 issue/verify contract |
| `agent/public_api.py` | HTTP 409/422 mapping and resolve/confirm orchestration |
| `agent/personalization_events.py` | Recommendation reset through sanitized preference boundary |
| `agent/scheduler.py` | Invoke bounded preference self-healing without raw telemetry |
| `web-nuxt/types/personalization.ts` | Public `location_reconfirm_required` state |
| `web-nuxt/composables/usePersonalizationPreferences.ts` | Snapshot normalization and stale confirmation behavior |
| `web-nuxt/pages/cai-dat.vue` | Reconfirm banner, CTA and focus recovery |
| `web-nuxt/components/PersonalizeSetupSheet.vue` | Discard stale token and require explicit resolve again |
| `agent/tests/test_location_remediation_postgres.py` | Disposable PostgreSQL migration/runtime privacy contract |
| `docs/superpowers/reports/2026-07-29-np1-1-location-remediation-verification.md` | Final command evidence and explicit limitations |

## Task Dependency Map

```text
Task 1 schema 73
   |
   v
Task 2 canonical invariant + precedence
   |
   v
Task 3 read/final-write/reset healing
   |
   +----------> Task 4 token v2
   |                 |
   v                 v
Task 5 worker    Task 6 PostgreSQL/API privacy integration
   \                 /
    \               /
     v             v
       Task 7 frontend state/UI
                 |
                 v
       Task 8 final gates/report/review
```

---

### Task 1: Migration 073 and schema readiness

**Files:**
- Create: `agent/migrations/073_location_preference_remediation.sql`
- Create: `agent/tests/test_location_remediation_postgres.py`
- Modify: `agent/database.py:92-112`
- Modify: `agent/tests/test_database.py:95-221`
- Modify: `agent/tests/test_migration_chain.py`
- Modify: `agent/tests/test_migration_apply.py:15-49`
- Modify: `agent/tests/test_migration_readiness_postgres.py:64-80`

**Interfaces:**
- Produces DB columns `location_reconfirm_required BOOLEAN NOT NULL DEFAULT FALSE` and `location_provenance_version VARCHAR(32)`.
- Produces SQL function `vl360_region_text_is_safe(TEXT) -> BOOLEAN` used by constraints and worker candidate selection.
- Produces schema version `73` and `revision BIGINT CHECK (revision <= 9007199254740991)`.
- Does not expose either internal provenance or raw legacy location through an audit table.

- [ ] **Step 1: Write RED schema/readiness and migration-contract tests**

Add the release assertions first:

```python
def test_pg_schema_contract_tracks_latest_release_tables():
    assert PG_REQUIRED_SCHEMA_VERSION == 73
    assert {
        "location_reconfirm_required",
        "location_provenance_version",
    } <= PG_REQUIRED_COLUMNS["user_preferences"]


def test_pg_startup_rejects_schema_version_72():
    database = Database.__new__(Database)
    with pytest.raises(RuntimeError, match=r"schema_version agent=72, expected >= 73"):
        database._verify_pg_schema(_release_schema(version=72))
```

Add a static migration ownership test in `test_migration_chain.py`:

```python
MIG_073 = (ROOT / "agent" / "migrations" / "073_location_preference_remediation.sql").read_text(encoding="utf-8")


def test_073_owns_location_remediation_contract():
    assert "location_reconfirm_required" in MIG_073
    assert "location_provenance_version" in MIG_073
    assert "location-confirmation" not in MIG_073
    assert "resolver-v2" in MIG_073
    assert "VALUES ('agent', 73," in MIG_073
    assert "CREATE TABLE" not in MIG_073
```

Create `test_location_remediation_postgres.py` with a loopback-only disposable database guard identical in safety to `test_migration_readiness_postgres.py`. Apply migrations through 072 from a temporary migration directory, seed users and the following rows, then apply 073:

```python
import shutil

from scripts.apply_migrations import (
    DEFAULT_MIGRATIONS,
    apply_sql_file,
    migration_files,
    record_schema_version,
    run as apply_migrations,
)


LEGACY_CASES = {
    "raw-ip": ("203.0.113.9", "203.0.113.9", "manual"),
    "raw-coordinate": ("10.2500,105.9700", "10.2500, 105.9700", "manual"),
    "arbitrary-manual": ("district-untrusted", "Khu vực tự khai", "manual"),
    "legacy-gps": ("province-vl", "Vĩnh Long", "gps"),
    "legacy-ip": ("province-vl", "Vĩnh Long", "ip"),
}


@pytest.fixture
def pre73_database(tmp_path):
    assert TEST_DATABASE_URL is not None
    migrations_dir = tmp_path / "migrations-through-072"
    migrations_dir.mkdir()
    for migration in migration_files(DEFAULT_MIGRATIONS):
        if migration.version <= 72:
            shutil.copy2(migration.path, migrations_dir / migration.path.name)

    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE")
            cursor.execute("CREATE SCHEMA public")

    apply_migrations(
        TEST_DATABASE_URL,
        migrations_dir=migrations_dir,
        init_baseline=True,
    )
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    return adapter


def apply_migration_073():
    migration = DEFAULT_MIGRATIONS / "073_location_preference_remediation.sql"
    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            apply_sql_file(cursor, migration)
            record_schema_version(cursor, 73, migration.name)
        conn.commit()
```

Assert invalid rows become `default/off/reconfirm=true`, while canonical Vĩnh Long and manual `Toàn tỉnh` remain unchanged. Assert interests, personalization, consent rows and a saved workspace row remain.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
python -m pytest -q agent/tests/test_database.py -k "schema_contract_tracks_latest_release_tables or schema_version_72 or missing_np1_column"
python -m pytest -q agent/tests/test_migration_chain.py -k "073"
```

Expected: FAIL because schema version remains 72, the two columns are absent and migration 073 does not exist.

If `MIGRATION_APPLY_TEST_DATABASE_URL` is configured to a loopback database containing `test`, also run:

```powershell
$env:LOCATION_REMEDIATION_TEST_DATABASE_URL = $env:MIGRATION_APPLY_TEST_DATABASE_URL
python -m pytest -q agent/tests/test_location_remediation_postgres.py
```

Expected: FAIL because the migration contract is absent.

- [ ] **Step 3: Implement migration 073 and readiness 73**

The migration must perform these operations in order:

```sql
ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS location_reconfirm_required BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS location_provenance_version VARCHAR(32);

ALTER TABLE user_preferences
    ALTER COLUMN revision TYPE BIGINT;

ALTER TABLE user_preferences
    ADD CONSTRAINT ck_user_preferences_revision_json_safe
    CHECK (revision >= 0 AND revision <= 9007199254740991);

CREATE OR REPLACE FUNCTION vl360_region_text_is_safe(value TEXT)
RETURNS BOOLEAN
LANGUAGE SQL
IMMUTABLE
PARALLEL SAFE
AS $$
    SELECT value IS NULL OR (
        value !~ '(^|[^0-9])([0-9]{1,3}\.){3}[0-9]{1,3}([^0-9]|$)'
        AND value !~* '(^|[^0-9a-f])([0-9a-f]{1,4}:){2,7}[0-9a-f]{0,4}([^0-9a-f]|$)'
        AND value !~* '[-+]?[0-9]{1,3}(\.[0-9]+)?[[:space:]]*[,;/][[:space:]]*[-+]?[0-9]{1,3}(\.[0-9]+)?'
        AND value !~* '[0-9]{1,3}[[:space:]]*[°º][[:space:]]*[0-9]{1,2}'
        AND value !~* '[-+]?[0-9]{1,3}(\.[0-9]+)?[[:space:]]*[NSEW]'
    );
$$;
```

Use one `DO` block for quarantine and aggregate-only notice. The valid predicate must preserve only exact canonical manual/default tuples or an already valid `resolver-v2` tuple:

```sql
DO $$
DECLARE
    quarantined_count BIGINT;
BEGIN
    UPDATE user_preferences
    SET region_id = NULL,
        region_label = NULL,
        region_scope = 'unknown',
        location_source = 'default',
        location_accuracy = 'unknown',
        location_consent_state = 'off',
        location_enabled = FALSE,
        location_provenance_version = NULL,
        location_reconfirm_required = TRUE,
        revision = revision + 1,
        updated_at = NOW()
    WHERE NOT vl360_region_text_is_safe(region_id)
       OR NOT vl360_region_text_is_safe(region_label)
       OR NOT (
            (
                location_source = 'manual'
                AND location_provenance_version IS NULL
                AND (
                    (region_id = 'province-vl' AND region_label = 'Vĩnh Long' AND region_scope = 'province' AND location_accuracy = 'province')
                    OR (region_id = 'province-bt' AND region_label = 'Bến Tre' AND region_scope = 'province' AND location_accuracy = 'province')
                    OR (region_id = 'province-tv' AND region_label = 'Trà Vinh' AND region_scope = 'province' AND location_accuracy = 'province')
                    OR (region_id IS NULL AND region_label IS NULL AND region_scope = 'all' AND location_accuracy = 'unknown')
                )
            )
            OR (
                location_source = 'default'
                AND region_id IS NULL
                AND region_label IS NULL
                AND region_scope = 'unknown'
                AND location_accuracy = 'unknown'
                AND location_provenance_version IS NULL
            )
            OR (
                location_source IN ('gps', 'ip')
                AND region_id IS NOT NULL
                AND region_scope IN ('ward', 'district', 'province')
                AND location_accuracy IN ('ward', 'district', 'province', 'unknown')
                AND location_enabled = TRUE
                AND location_consent_state = 'granted'
                AND location_provenance_version = 'resolver-v2'
            )
       )
       OR (
            location_reconfirm_required = TRUE
            AND NOT (
                location_source = 'default'
                AND region_id IS NULL
                AND region_label IS NULL
                AND region_scope = 'unknown'
                AND location_accuracy = 'unknown'
                AND location_enabled = FALSE
                AND location_consent_state = 'off'
                AND location_provenance_version IS NULL
            )
       );
    GET DIAGNOSTICS quarantined_count = ROW_COUNT;
    RAISE NOTICE 'NP-1.1 quarantined % legacy location preference rows', quarantined_count;
END $$;
```

Add CHECK constraints named `ck_user_preferences_region_text_safe_v2`, `ck_user_preferences_region_tuple_v2` and `ck_user_preferences_reconfirm_state_v1`, mirroring the three predicates. Then record schema 73 with the existing monotonic `schema_version` pattern. Do not insert into `user_preference_consents` and do not create any table.

Update `PG_REQUIRED_SCHEMA_VERSION`, `PG_REQUIRED_COLUMNS`, `_NP1_REQUIRED_COLUMNS`, fresh-chain expectations and migration apply lower bound from 72 to 73.

- [ ] **Step 4: Run GREEN migration/readiness tests**

Run:

```powershell
python -m pytest -q agent/tests/test_database.py -k "schema_contract_tracks_latest_release_tables or schema_version_72 or missing_np1_column"
python -m pytest -q agent/tests/test_migration_chain.py -k "073"
python -m pytest -q agent/tests/test_migration_apply.py -k "schema_version"
```

When the disposable URL is available:

```powershell
$env:LOCATION_REMEDIATION_TEST_DATABASE_URL = $env:MIGRATION_APPLY_TEST_DATABASE_URL
python -m pytest -q agent/tests/test_location_remediation_postgres.py
python -m pytest -q agent/tests/test_migration_readiness_postgres.py
```

Expected: all selected tests pass; invalid rows are quarantined, canonical manual/default rows survive and constraints reject direct invalid writes.

- [ ] **Step 5: Commit Task 1**

```powershell
git add agent/migrations/073_location_preference_remediation.sql agent/database.py agent/tests/test_database.py agent/tests/test_migration_chain.py agent/tests/test_migration_apply.py agent/tests/test_migration_readiness_postgres.py agent/tests/test_location_remediation_postgres.py
git diff --cached --check
git commit -m "feat: add location remediation migration"
```

---

### Task 2: Canonical region invariant and manual precedence

**Files:**
- Modify: `agent/user_preferences.py:25-390`
- Modify: `agent/public_api.py:448-467`
- Modify: `agent/tests/test_user_preferences.py:1-330`
- Modify: `agent/tests/test_user_preferences.py:331-390`

**Interfaces:**
- Produces `PersistedPreferenceSnapshot`, internal `location_provenance_version`, and public `PreferenceSnapshot.location_reconfirm_required`.
- Produces `invalid_region_reason(snapshot: Mapping[str, Any]) -> str | None` with allowlisted reasons only.
- Produces `quarantine_location_snapshot(snapshot: Mapping[str, Any]) -> PersistedPreferenceSnapshot` without preserving raw region fields.
- Keeps client PATCH fields separate from public snapshot fields; clients cannot set remediation/provenance fields.

- [ ] **Step 1: Write RED pure-contract and precedence tests**

Add these tests before changing production code:

```python
def test_manual_all_region_wins_over_valid_gps_confirmation():
    merged = merge_preference_patch(
        {
            "region_id": None,
            "region_label": None,
            "region_scope": "all",
            "location_source": "manual",
            "location_accuracy": "unknown",
            "revision": 4,
        },
        {
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_source": "gps",
            "location_accuracy": "province",
            "location_enabled": True,
        },
        expected_revision=4,
    )
    assert merged["region_id"] is None
    assert merged["region_scope"] == "all"
    assert merged["location_source"] == "manual"


@pytest.mark.parametrize(
    ("snapshot", "reason"),
    [
        ({"region_id": "203.0.113.9", "region_label": "Vĩnh Long", "region_scope": "province", "location_source": "manual", "location_accuracy": "province"}, "raw_shape"),
        ({"region_id": "district-x", "region_label": "Tự khai", "region_scope": "district", "location_source": "manual", "location_accuracy": "district"}, "manual_tuple"),
        ({"region_id": "province-vl", "region_label": "Vĩnh Long", "region_scope": "province", "location_source": "gps", "location_accuracy": "province", "location_enabled": True, "location_consent_state": "granted", "location_provenance_version": None}, "provenance"),
    ],
)
def test_invalid_region_reason_is_bounded(snapshot, reason):
    assert invalid_region_reason({**_default_persisted_snapshot(), **snapshot}) == reason
```

Add exact client-field and revision boundary tests:

```python
@pytest.mark.parametrize(
    "field",
    ["location_reconfirm_required", "location_provenance_version"],
)
def test_remediation_fields_are_not_client_patchable(field):
    with pytest.raises(PreferenceValidationError, match="Unknown preference fields"):
        normalize_preference_patch({field: True})


def test_revision_accepts_json_safe_bigint_boundary():
    assert normalize_preference_patch(
        {"revision": 9_007_199_254_740_991}
    )["revision"] == 9_007_199_254_740_991


def test_revision_rejects_value_above_json_safe_bigint_boundary():
    with pytest.raises(PreferenceValidationError):
        normalize_preference_patch({"revision": 9_007_199_254_740_992})
```

- [ ] **Step 2: Run RED unit tests**

Run:

```powershell
python -m pytest -q agent/tests/test_user_preferences.py -k "manual_all_region or invalid_region_reason or max_safe or remediation_fields"
```

Expected: FAIL because the invariant/public-internal split does not exist and manual all can be overwritten.

- [ ] **Step 3: Implement the canonical in-memory contract**

Refactor field ownership explicitly:

```python
MAX_PREFERENCE_REVISION = 9_007_199_254_740_991
LOCATION_PROVENANCE_RESOLVER_V2 = "resolver-v2"

_PUBLIC_SNAPSHOT_FIELDS = (
    "region_id",
    "region_label",
    "region_scope",
    "location_source",
    "location_accuracy",
    "location_consent_state",
    "location_enabled",
    "personalization_enabled",
    "explicit_interests",
    "recommendation_reset_at",
    "consent_version",
    "location_reconfirm_required",
    "revision",
)
_PERSISTED_FIELDS = (*_PUBLIC_SNAPSHOT_FIELDS, "location_provenance_version")
_PATCH_FIELDS = frozenset(
    field
    for field in _PUBLIC_SNAPSHOT_FIELDS
    if field not in {"location_reconfirm_required"}
)
```

Define the public/internal types:

```python
class PreferenceSnapshot(TypedDict):
    region_id: str | None
    region_label: str | None
    region_scope: str
    location_source: str
    location_accuracy: str
    location_consent_state: str
    location_enabled: bool
    personalization_enabled: bool
    explicit_interests: list[str]
    recommendation_reset_at: datetime | str | None
    consent_version: str | None
    location_reconfirm_required: bool
    revision: int


class PersistedPreferenceSnapshot(PreferenceSnapshot):
    location_provenance_version: str | None
```

Add an internal default and keep the public default as a projection:

```python
def _default_persisted_snapshot() -> PersistedPreferenceSnapshot:
    return {
        "region_id": None,
        "region_label": None,
        "region_scope": "unknown",
        "location_source": "default",
        "location_accuracy": "unknown",
        "location_consent_state": "unknown",
        "location_enabled": False,
        "personalization_enabled": False,
        "explicit_interests": [],
        "recommendation_reset_at": None,
        "consent_version": None,
        "location_reconfirm_required": False,
        "revision": 0,
        "location_provenance_version": None,
    }


def _public_snapshot(snapshot: Mapping[str, Any]) -> PreferenceSnapshot:
    return {field: snapshot[field] for field in _PUBLIC_SNAPSHOT_FIELDS}
```

Implement `invalid_region_reason()` in this order: raw shape, exact manual tuple, resolver tuple/state/provenance, exact default tuple, reconfirm consistency. Return only `raw_shape`, `manual_tuple`, `resolver_tuple`, `default_tuple`, `provenance` or `state_mismatch`.

`quarantine_location_snapshot()` must copy the non-location fields and replace location with:

```python
{
    "region_id": None,
    "region_label": None,
    "region_scope": "unknown",
    "location_source": "default",
    "location_accuracy": "unknown",
    "location_consent_state": "off",
    "location_enabled": False,
    "location_reconfirm_required": True,
    "location_provenance_version": None,
}
```

Keep `_authorize_region_patch()` limited to public region fields. After merge, call an internal-only finalizer so client normalization never sees remediation metadata:

```python
def _apply_internal_location_metadata(
    merged: PersistedPreferenceSnapshot,
    *,
    authorized_patch: Mapping[str, Any],
    confirmed_location: LocationResolution | None,
) -> None:
    if merged["location_source"] == "manual":
        merged["location_provenance_version"] = None
        if authorized_patch.get("location_source") == "manual":
            merged["location_reconfirm_required"] = False
        return
    if merged["location_source"] in {"gps", "ip"} and confirmed_location is not None:
        merged["location_provenance_version"] = LOCATION_PROVENANCE_RESOLVER_V2
        merged["location_reconfirm_required"] = False
        return
    if merged["location_source"] == "default":
        merged["location_provenance_version"] = None
```

Do not add `location_reconfirm_required` or `location_provenance_version` to `PreferencePatchIn`. Other mutations preserve the current reconfirm flag.

Update `_preference_columns()`, `_write_values()` and update assignments to use `_PERSISTED_FIELDS`. Keep JSON serialization keyed by the field name `explicit_interests`, not by a stale tuple index. Every route return calls `_public_snapshot()` so internal provenance never crosses the API boundary.

Replace the truthy region guard with source priority only:

```python
elif region_change and (resolver_disabled or lower_quality):
    for field in _REGION_FIELDS:
        normalized.pop(field, None)
```

Also strip internal resolver fields when lower priority is blocked so a GPS/IP confirmation cannot alter provenance behind a manual tuple.

Update the SQLite `user_preferences` fixture with the two schema-73 columns and `BIGINT`-compatible revision semantics.

- [ ] **Step 4: Run GREEN unit and route-schema tests**

Run:

```powershell
python -m pytest -q agent/tests/test_user_preferences.py -k "manual or precedence or invalid_region_reason or revision or remediation_fields"
python -m pytest -q agent/tests/test_user_preferences.py -k "forged_resolver_source or canonical_manual_region"
```

Expected: all selected tests pass; manual all stays manual and internal fields are not client writable.

- [ ] **Step 5: Commit Task 2**

```powershell
git add agent/user_preferences.py agent/public_api.py agent/tests/test_user_preferences.py
git diff --cached --check
git commit -m "fix: enforce canonical location preference state"
```

---

### Task 3: Read guard, final-write guard and reset sanitization

**Files:**
- Modify: `agent/user_preferences.py:410-590`
- Modify: `agent/personalization_events.py:551-579`
- Modify: `agent/tests/test_user_preferences.py:331-760`
- Modify: `agent/tests/test_personalization_events.py:1978-2050`

**Interfaces:**
- Produces `_load_persisted_preferences_in_connection(conn, owner, *, for_update, heal) -> PersistedPreferenceSnapshot`.
- `load_preferences(user_id) -> PreferenceSnapshot` always returns public sanitized state.
- Final mutation performs at most one write/revision increment for an invalid legacy base plus a valid user patch.
- Consent events are recorded only for explicit user decisions, never for automatic quarantine.
- `record_recommendation_reset()` uses the same sanitized persistence boundary.

- [ ] **Step 1: Write RED read/final-write/reset behavior tests**

Seed unsafe rows through a shared test helper and assert load heals them:

```python
def _insert_unsafe_preference(database, user_id="user-1", revision=7):
    with database._conn() as conn:
        conn.execute(
            "INSERT INTO user_preferences "
            "(user_id, region_id, region_label, region_scope, location_source, "
            "location_accuracy, location_consent_state, location_enabled, "
            "personalization_enabled, explicit_interests, consent_version, revision) "
            "VALUES (?, ?, ?, 'province', 'manual', 'province', 'granted', 1, 1, ?, 'privacy-v1', ?)",
            (user_id, "203.0.113.9", "10.25,105.97", '["food"]', revision),
        )


def test_load_preferences_quarantines_unsafe_region_without_losing_non_location_state(
    preference_database,
):
    _insert_unsafe_preference(preference_database)

    snapshot = load_preferences("user-1")

    assert snapshot["region_id"] is None
    assert snapshot["location_source"] == "default"
    assert snapshot["location_consent_state"] == "off"
    assert snapshot["location_reconfirm_required"] is True
    assert snapshot["explicit_interests"] == ["food"]
    assert snapshot["personalization_enabled"] is True
    assert snapshot["consent_version"] == "privacy-v1"
    assert snapshot["revision"] == 8
```

Add the remaining boundary tests:

```python
def test_second_load_after_quarantine_is_idempotent(preference_database):
    _insert_unsafe_preference(preference_database)
    assert load_preferences("user-1")["revision"] == 8
    assert load_preferences("user-1")["revision"] == 8


def test_unrelated_patch_sanitizes_once_without_synthetic_location_consent(
    preference_database,
):
    _insert_unsafe_preference(preference_database)
    snapshot = patch_preferences_with_consents(
        "user-1",
        {"explicit_interests": ["culture"]},
        expected_revision=7,
    )
    assert snapshot["revision"] == 8
    assert snapshot["region_id"] is None
    assert snapshot["location_reconfirm_required"] is True
    assert snapshot["explicit_interests"] == ["culture"]
    assert load_preference_consents("user-1") == []


def test_manual_patch_completes_reconfirm_in_the_same_write(preference_database):
    _insert_unsafe_preference(preference_database)
    snapshot = patch_preferences(
        "user-1",
        {
            "region_id": None,
            "region_label": None,
            "region_scope": "all",
            "location_source": "manual",
            "location_accuracy": "unknown",
        },
        expected_revision=7,
    )
    assert snapshot["revision"] == 8
    assert snapshot["location_source"] == "manual"
    assert snapshot["region_scope"] == "all"
    assert snapshot["location_reconfirm_required"] is False


def test_recommendation_reset_uses_sanitized_preference_boundary(
    preference_database, monkeypatch
):
    _insert_unsafe_preference(preference_database)
    monkeypatch.setattr(personalization_events, "db", preference_database)
    snapshot = personalization_events.record_recommendation_reset("user-1")
    assert snapshot["region_id"] is None
    assert snapshot["location_reconfirm_required"] is True
    assert snapshot["explicit_interests"] == ["food"]
    assert snapshot["recommendation_reset_at"] is not None
    assert "location_provenance_version" not in snapshot
```

- [ ] **Step 2: Run RED persistence tests**

Run:

```powershell
python -m pytest -q agent/tests/test_user_preferences.py -k "quarantines_unsafe or unrelated_patch or consent_history or completes_reconfirm"
python -m pytest -q agent/tests/test_personalization_events.py -k "recommendation_reset and preference"
```

Expected: FAIL because load/export/reset return the raw persisted snapshot and final merge can rewrite it.

- [ ] **Step 3: Implement atomic sanitize-on-read and sanitize-before-write**

Change `load_preferences()` to use a committing transaction. Normalize the persisted row, call `invalid_region_reason()`, and on invalid state issue one compare-and-update:

```python
UPDATE user_preferences
SET region_id = ?,
    region_label = ?,
    region_scope = ?,
    location_source = ?,
    location_accuracy = ?,
    location_consent_state = ?,
    location_enabled = ?,
    location_reconfirm_required = ?,
    location_provenance_version = ?,
    revision = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE user_id = ? AND revision = ?
RETURNING region_id, region_label, region_scope, location_source,
          location_accuracy, location_consent_state, location_enabled,
          personalization_enabled, explicit_interests,
          recommendation_reset_at, consent_version,
          location_reconfirm_required, revision,
          location_provenance_version
```

Use PostgreSQL placeholders/casts through the existing database adapter. If the compare-update loses a race, reload once. If the reloaded row remains invalid, return an in-memory quarantined public snapshot that retains the latest database revision and leave persistence to the bounded worker; never return raw fields or invent an unpersisted revision.

In `_patch_preferences_in_connection()`:

1. read the persisted row under `FOR UPDATE`;
2. validate the original persisted snapshot;
3. use quarantine state as the merge base when invalid;
4. authorize/merge the user patch;
5. validate the complete final persisted snapshot;
6. write once with `WHERE revision = expected`;
7. project public state only after the returned row passes the invariant.

Replace compare-only consent detection with explicit-patch detection:

```python
def _requested_consent_changes(
    current: PreferenceSnapshot,
    snapshot: PreferenceSnapshot,
    authorized_patch: Mapping[str, Any],
    *,
    confirmed_location: LocationResolution | None,
) -> list[tuple[str, str]]:
    changes: list[tuple[str, str]] = []
    if "location_consent_state" in authorized_patch or confirmed_location is not None:
        if current["location_consent_state"] != snapshot["location_consent_state"]:
            changes.append(("location", snapshot["location_consent_state"]))
    if "personalization_enabled" in authorized_patch:
        if current["personalization_enabled"] != snapshot["personalization_enabled"]:
            changes.append(("personalization", "granted" if snapshot["personalization_enabled"] else "off"))
    return changes
```

Refactor `record_recommendation_reset()` to lock/load through the same persisted helper, merge `recommendation_reset_at`, validate and write once. Do not keep the current direct upsert that can return an unsafe row.

- [ ] **Step 4: Run GREEN persistence/export/reset tests**

Run:

```powershell
python -m pytest -q agent/tests/test_user_preferences.py
python -m pytest -q agent/tests/test_personalization_events.py -k "recommendation_reset or export_includes_safe_preferences"
```

Expected: selected suites pass; raw values are overwritten before return, no synthetic consent is created and reset returns sanitized state.

- [ ] **Step 5: Commit Task 3**

```powershell
git add agent/user_preferences.py agent/personalization_events.py agent/tests/test_user_preferences.py agent/tests/test_personalization_events.py
git diff --cached --check
git commit -m "fix: self-heal unsafe location preferences"
```

---

### Task 4: Revision-bound location confirmation token v2

**Files:**
- Modify: `agent/location_resolver.py:40-380`
- Modify: `agent/public_api.py:1055-1210`
- Modify: `agent/tests/test_location_resolver.py`
- Modify: `agent/tests/test_user_preferences.py:760-900`

**Interfaces:**
- `issue_location_confirmation(resolution, user_id, preference_revision) -> str | None`.
- `verify_location_confirmation(token, user_id) -> VerifiedLocationConfirmation`.
- `VerifiedLocationConfirmation` contains `resolution: LocationResolution` and `preference_revision: int`.
- Signed revision mismatch maps directly to HTTP `409`; `LocationConfirmationError` maps invalid token contracts to `422`.

- [ ] **Step 1: Write RED token-v2 route tests**

Define the route helper and update the route test to assert the token is revision-bound and effectively one-use:

```python
def _resolve_fixture_location(client, logged_in_user, monkeypatch):
    now = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    monkeypatch.setattr(location_resolver, "_utc_now", lambda: now, raising=False)
    client.app.dependency_overrides[public_api.get_reverse_geocoder] = lambda: (
        lambda *_: {
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_accuracy": "province",
        }
    )
    return client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=logged_in_user.csrf_headers,
    )


def test_location_confirmation_token_is_revision_bound_and_effectively_one_use(
    client, logged_in_user, monkeypatch
):
    resolution = _resolve_fixture_location(client, logged_in_user, monkeypatch)
    token = resolution.json()["confirmation_token"]

    first = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "location_confirmation_token": token,
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )
    assert first.status_code == 200
    assert first.json()["revision"] == 1

    replay = client.patch(
        "/api/me/preferences",
        json={
            "revision": 1,
            "location_confirmation_token": token,
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )
    assert replay.status_code == 409
    assert replay.json()["revision"] == 1
```

Add payload and stale-transition tests:

```python
def test_confirmation_token_payload_has_revision_but_no_nonce_or_raw_coordinates(
    client, logged_in_user, monkeypatch
):
    response = _resolve_fixture_location(client, logged_in_user, monkeypatch)
    encoded = response.json()["confirmation_token"].split(".", 1)[0]
    envelope = json.loads(
        base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    )
    payload = envelope["payload"]
    assert payload["preference_revision"] == 0
    assert "issued_at" in payload
    assert "nonce" not in payload
    serialized = json.dumps(payload)
    assert "10.25" not in serialized
    assert "105.97" not in serialized


def test_preference_mutation_after_token_issue_returns_409(
    client, logged_in_user, monkeypatch
):
    token = _resolve_fixture_location(
        client, logged_in_user, monkeypatch
    ).json()["confirmation_token"]
    changed = client.patch(
        "/api/me/preferences",
        json={"revision": 0, "explicit_interests": ["food"]},
        headers=logged_in_user.csrf_headers,
    )
    assert changed.status_code == 200
    stale = client.patch(
        "/api/me/preferences",
        json={
            "revision": 1,
            "location_confirmation_token": token,
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )
    assert stale.status_code == 409
    assert stale.json()["revision"] == 1
```

Retain and update the existing malformed/tampered/expired/cross-user tests to expect 422. Add the old-purpose and sanitized-issuance cases:

```python
def test_v1_confirmation_purpose_is_rejected(
    client, logged_in_user, monkeypatch
):
    now = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    monkeypatch.setattr(location_resolver, "_utc_now", lambda: now, raising=False)
    old_token = generate_user_bound_token(
        "location-confirmation-v1",
        "user-1",
        {
            "issued_at": int(now.timestamp()),
            "preference_revision": 0,
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_source": "gps",
            "location_accuracy": "province",
        },
        expires_at=int(now.timestamp()) + 300,
    )
    response = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "location_confirmation_token": old_token,
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )
    assert response.status_code == 422


def test_resolve_token_binds_post_quarantine_revision(
    client, preference_database, logged_in_user, monkeypatch
):
    _insert_unsafe_preference(preference_database)
    response = _resolve_fixture_location(client, logged_in_user, monkeypatch)
    encoded = response.json()["confirmation_token"].split(".", 1)[0]
    envelope = json.loads(
        base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    )
    assert envelope["payload"]["preference_revision"] == 8
    assert load_preferences("user-1")["revision"] == 8
```

- [ ] **Step 2: Run RED token tests**

Run:

```powershell
python -m pytest -q agent/tests/test_user_preferences.py -k "confirmation_token and (revision or one_use or stale or old_purpose)"
python -m pytest -q agent/tests/test_location_resolver.py -k "confirmation"
```

Expected: FAIL because tokens are v1, carry a random nonce and are not bound to preference revision.

- [ ] **Step 3: Implement token purpose v2 and HTTP status split**

Define the verified contract:

```python
@dataclass(frozen=True)
class VerifiedLocationConfirmation:
    resolution: LocationResolution
    preference_revision: int


def _validated_preference_revision(value: Any) -> int:
    if type(value) is not int or value < 0 or value > 9_007_199_254_740_991:
        raise LocationConfirmationError("Invalid location confirmation")
    return value
```

Change the purpose and payload:

```python
_LOCATION_CONFIRMATION_PURPOSE = "location-confirmation-v2"


def issue_location_confirmation(
    resolution: LocationResolution,
    user_id: str,
    preference_revision: int,
) -> str | None:
    if not resolution.region_id or resolution.location_source not in {"gps", "ip"}:
        return None
    now = _utc_now()
    payload = {
        "issued_at": int(now.timestamp()),
        "preference_revision": _validated_preference_revision(preference_revision),
        "region_id": resolution.region_id,
        "region_label": resolution.region_label,
        "region_scope": resolution.region_scope,
        "location_source": resolution.location_source,
        "location_accuracy": resolution.location_accuracy,
    }
    return generate_user_bound_token(
        _LOCATION_CONFIRMATION_PURPOSE,
        user_id,
        payload,
        expires_at=int(now.timestamp()) + LOCATION_CONFIRMATION_TTL_SECONDS,
    )
```

`verify_location_confirmation()` validates `issued_at`, revision bounds and normalized resolution, then returns `VerifiedLocationConfirmation`.

In `resolve_my_location()`, call `load_preferences(owner)` after transient resolve and pass its sanitized `revision` into token issuance.

In `update_my_preferences()`:

```python
confirmation = (
    verify_location_confirmation(confirmation_token, owner)
    if confirmation_token is not None
    else None
)
if confirmation is not None and confirmation.preference_revision != expected_revision:
    current = await asyncio.to_thread(load_preferences, owner)
    return JSONResponse(
        status_code=409,
        content=jsonable_encoder(current),
        headers={"Cache-Control": "no-store"},
    )
confirmed_location = confirmation.resolution if confirmation is not None else None
```

Keep database optimistic update as the second stale check. Remove `secrets` import if it is no longer used. Do not introduce persistence for token or nonce.

- [ ] **Step 4: Run GREEN token and route tests**

Run:

```powershell
python -m pytest -q agent/tests/test_location_resolver.py
python -m pytest -q agent/tests/test_user_preferences.py -k "resolver or confirmation_token or preferences_revision_conflict"
```

Expected: all selected tests pass; stale is 409, invalid is 422 and the second confirmation cannot win.

- [ ] **Step 5: Commit Task 4**

```powershell
git add agent/location_resolver.py agent/public_api.py agent/tests/test_location_resolver.py agent/tests/test_user_preferences.py
git diff --cached --check
git commit -m "fix: bind location confirmations to preference revision"
```

---

### Task 5: Bounded self-healing worker and aggregate observability

**Files:**
- Modify: `agent/user_preferences.py`
- Modify: `agent/scheduler.py:882-925`
- Modify: `agent/tests/test_personalization_events.py:2109-2208`
- Modify: `agent/tests/test_location_remediation_postgres.py`

**Interfaces:**
- `quarantine_invalid_preferences_batch(limit: int = 100) -> dict[str, int]`.
- Return keys are allowlisted reason names only; values are successful quarantine counts.
- Scheduler calls the worker only for PostgreSQL and logs aggregate count/reason, never user or raw values.

- [ ] **Step 1: Write RED worker boundedness/idempotence/privacy tests**

In the disposable PostgreSQL test, temporarily remove only `ck_user_preferences_region_text_safe_v2`, `ck_user_preferences_region_tuple_v2` and `ck_user_preferences_reconfirm_state_v1`, insert 105 invalid rows plus valid rows, then call the worker:

```python
def test_self_healing_worker_is_bounded_idempotent_and_preserves_non_location_state(
    remediation_database,
):
    first = quarantine_invalid_preferences_batch(limit=100)
    assert sum(first.values()) == 100

    second = quarantine_invalid_preferences_batch(limit=100)
    assert sum(second.values()) == 5

    third = quarantine_invalid_preferences_batch(limit=100)
    assert sum(third.values()) == 0
```

Assert all healed rows retain interests/personalization and contain no raw region. Re-add and validate constraints before fixture teardown.

Add a scheduler behavior test by monkeypatching the worker:

```python
def test_scheduler_logs_only_aggregate_location_quarantine(monkeypatch, caplog):
    monkeypatch.setattr(
        user_preferences,
        "quarantine_invalid_preferences_batch",
        lambda limit=100: {"raw_shape": 2, "provenance": 1},
    )
    with caplog.at_level("INFO", logger="scheduler"):
        scheduler.task_personalization_cleanup()
    output = "\n".join(record.getMessage() for record in caplog.records)
    assert "3" in output
    assert "203.0.113" not in output
    assert "province-vl" not in output
```

- [ ] **Step 2: Run RED worker tests**

Run:

```powershell
python -m pytest -q agent/tests/test_personalization_events.py -k "aggregate_location_quarantine"
```

When disposable PostgreSQL is configured:

```powershell
$env:LOCATION_REMEDIATION_TEST_DATABASE_URL = $env:MIGRATION_APPLY_TEST_DATABASE_URL
python -m pytest -q agent/tests/test_location_remediation_postgres.py -k "self_healing_worker"
```

Expected: FAIL because no bounded worker exists.

- [ ] **Step 3: Implement candidate selection, compare-update and scheduler call**

Clamp the batch size:

```python
bounded_limit = max(1, min(int(limit), 100))
```

For PostgreSQL, query only invalid candidates using `vl360_region_text_is_safe`, the canonical tuple predicate and reconfirm predicate from migration 073. Select persisted fields ordered by `updated_at, user_id` with `LIMIT %s FOR UPDATE SKIP LOCKED`.

For each row:

1. compute `reason = invalid_region_reason(snapshot)`;
2. skip if `reason is None`;
3. create `quarantine_location_snapshot(snapshot)` and advance revision once;
4. update with `WHERE user_id = %s::uuid AND revision = %s`;
5. increment `counts[reason]` only when one row was returned.

Do not log inside the persistence loop. In `task_personalization_cleanup()`, import and run the worker after event TTL cleanup:

```python
counts = quarantine_invalid_preferences_batch(limit=100)
healed = sum(counts.values())
if healed:
    summary = ", ".join(f"{reason}={count}" for reason, count in sorted(counts.items()))
    _sched_logger.info(
        "Location preference self-healing: quarantined %d rows (%s)",
        healed,
        summary,
    )
```

Reason names are fixed constants; never interpolate raw row data.

- [ ] **Step 4: Run GREEN worker/scheduler tests**

Run:

```powershell
python -m pytest -q agent/tests/test_personalization_events.py -k "scheduler_ttl_cleanup or aggregate_location_quarantine or exact_cutover"
```

When disposable PostgreSQL is configured:

```powershell
$env:LOCATION_REMEDIATION_TEST_DATABASE_URL = $env:MIGRATION_APPLY_TEST_DATABASE_URL
python -m pytest -q agent/tests/test_location_remediation_postgres.py -k "self_healing_worker or constraints"
```

Expected: worker handles 100/5/0 rows, scheduler keeps legacy/event cleanup behavior and logs no raw data.

- [ ] **Step 5: Commit Task 5**

```powershell
git add agent/user_preferences.py agent/scheduler.py agent/tests/test_personalization_events.py agent/tests/test_location_remediation_postgres.py
git diff --cached --check
git commit -m "feat: add bounded location preference self-healing"
```

---

### Task 6: PostgreSQL API/export/concurrency privacy integration

**Files:**
- Modify: `agent/tests/test_location_remediation_postgres.py`
- Modify: `agent/tests/test_personalization_events.py:1978-2050`
- Modify: `agent/tests/test_user_preferences.py:783-900`
- Modify production files only if these integration tests reveal a boundary defect

**Interfaces:**
- Confirms the migration, runtime guard, token and export boundaries work together on real PostgreSQL.
- Confirms public API/export includes `location_reconfirm_required` but omits `location_provenance_version` and token data.

- [ ] **Step 1: Add RED cross-boundary integration tests**

Add a real PostgreSQL export assertion to the existing auth client test:

```python
exported_preferences = response.json()["personalization"]["preferences"]
assert exported_preferences["location_reconfirm_required"] is True
assert "location_provenance_version" not in exported_preferences
serialized = json.dumps(exported_preferences, ensure_ascii=False)
assert "203.0.113.9" not in serialized
assert "10.25,105.97" not in serialized
assert "confirmation_token" not in serialized
```

Add an atomic replay test against PostgreSQL using two threads/barriers. Both requests use the same token/revision:

```python
def test_postgres_confirmation_token_has_one_atomic_winner(
    auth_client, monkeypatch
):
    auth_client.client.app.dependency_overrides[public_api.get_reverse_geocoder] = (
        lambda: lambda *_: {
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_accuracy": "province",
        }
    )
    resolution = auth_client.client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=auth_client.csrf_headers,
    )
    token = resolution.json()["confirmation_token"]
    barrier = threading.Barrier(2)

    def confirm_once():
        barrier.wait(timeout=5)
        return auth_client.client.patch(
            "/api/me/preferences",
            json={
                "revision": 0,
                "location_confirmation_token": token,
                "location_consent_state": "granted",
                "location_enabled": True,
            },
            headers=auth_client.csrf_headers,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: confirm_once(), range(2)))

    assert sorted(response.status_code for response in responses) == [200, 409]
    current = auth_client.client.get(
        "/api/me/preferences",
        headers=auth_client.headers,
    ).json()
    assert current["revision"] == 1
    assert current["location_source"] == "gps"
```

Import `threading` and `ThreadPoolExecutor` in the test module. The real resolve route must issue the token; do not sign a fixture token directly.

Add constraint inventory assertions:

```python
with remediation_database._conn(commit_on_success=False) as conn:
    rows = remediation_database._fetchall(
        conn,
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'user_preferences'",
    )
columns = {remediation_database._row_to_dict(row)["column_name"] for row in rows}
assert not {"latitude", "longitude", "ip", "token", "nonce", "score", "weight"} & columns
```

- [ ] **Step 2: Run cross-boundary tests and observe any RED gaps**

Run:

```powershell
python -m pytest -q agent/tests/test_user_preferences.py -k "one_use or concurrent or export"
python -m pytest -q agent/tests/test_personalization_events.py -k "export_includes_safe_preferences"
```

When disposable PostgreSQL is configured:

```powershell
$env:LOCATION_REMEDIATION_TEST_DATABASE_URL = $env:MIGRATION_APPLY_TEST_DATABASE_URL
python -m pytest -q agent/tests/test_location_remediation_postgres.py
```

Expected: this is an integration checkpoint. Assertions may already pass because Tasks 1-5 were implemented through RED/GREEN cycles. Record the actual first-run result; if GREEN, retain the tests as cross-boundary regression coverage and do not fabricate RED evidence.

- [ ] **Step 3: Apply only integration-boundary fixes revealed by Step 2**

Allowed fixes are limited to:

- public projection stripping internal provenance;
- `Cache-Control: no-store` on 409/success responses;
- atomic revision predicate/response mapping;
- export using `load_preferences()` rather than direct row mapping;
- test fixture schema parity.

Do not refactor unrelated auth, recommendation or scheduler code in this task.

- [ ] **Step 4: Run GREEN PostgreSQL/API/privacy matrix**

Run:

```powershell
python -m pytest -q agent/tests/test_user_preferences.py agent/tests/test_location_resolver.py
python -m pytest -q agent/tests/test_personalization_events.py -k "export_includes_safe_preferences or postgres_preference_route or recommendation_reset"
```

When configured:

```powershell
$env:LOCATION_REMEDIATION_TEST_DATABASE_URL = $env:MIGRATION_APPLY_TEST_DATABASE_URL
python -m pytest -q agent/tests/test_location_remediation_postgres.py
```

Expected: all selected tests pass with one successful concurrent confirm, one 409 and no raw/internal leakage.

- [ ] **Step 5: Commit Task 6**

```powershell
git add agent/tests/test_location_remediation_postgres.py agent/tests/test_personalization_events.py agent/tests/test_user_preferences.py agent/auth.py agent/public_api.py agent/user_preferences.py agent/location_resolver.py
git diff --cached --check
git commit -m "test: verify location remediation privacy boundaries"
```

Before staging, omit production paths that have no Task 6 diff; do not create empty or unrelated changes.

---

### Task 7: Frontend reconfirm state and stale-token recovery

**Files:**
- Modify: `web-nuxt/types/personalization.ts:1-64`
- Modify: `web-nuxt/composables/usePersonalizationPreferences.ts:40-115`
- Modify: `web-nuxt/pages/cai-dat.vue:378-445`
- Modify: `web-nuxt/pages/cai-dat.vue:680-850`
- Modify: `web-nuxt/components/PersonalizeSetupSheet.vue:40-165`
- Modify: `web-nuxt/components/PersonalizeSetupSheet.vue:190-390`
- Modify: `web-nuxt/tests/personalization-preferences.test.ts:30-1100`
- Modify: `web-nuxt/tests/location-consent.test.ts:28-820`

**Interfaces:**
- `PreferenceSnapshot.location_reconfirm_required: boolean` is required in local state and defaults to false for backward-compatible old responses.
- Settings CTA uses `data-action="choose-region-again"` and moves focus to `[data-region-group="manual"]`.
- Setup stale state uses `locationState = 'stale'`, clears `resolvedLocation`, and exposes `data-action="retry-location"`.

- [ ] **Step 1: Write RED mounted behavior tests**

Update both snapshot fixtures with `location_reconfirm_required: false`, then add:

```ts
it('shows the privacy reconfirm banner, preserves interests, and focuses manual choices', async () => {
  const wrapper = await mountSettingsPage({
    preferences: preferenceFixture({
      location_consent_state: 'off',
      location_reconfirm_required: true,
      explicit_interests: ['food'],
      revision: 8,
    }),
  })
  const panel = wrapper.get('#khu-vuc-de-xuat')
  expect(panel.get('[data-state="location-reconfirm"]').text()).toContain('cần được chọn lại')
  expect(panel.text()).toContain('Ẩm thực')

  await panel.get('[data-action="choose-region-again"]').trigger('click')
  expect(document.activeElement).toBe(panel.get('[data-region-group="manual"]').element)
  wrapper.unmount()
})
```

Add a manual success test where the server returns `location_reconfirm_required: false`; assert the banner disappears without geolocation:

```ts
it('clears reconfirm only from the server manual-selection response', async () => {
  const getCurrentPosition = vi.fn()
  Object.defineProperty(navigator, 'geolocation', {
    configurable: true,
    value: { getCurrentPosition },
  })
  const wrapper = await mountSettingsPage({
    preferences: preferenceFixture({
      location_consent_state: 'off',
      location_reconfirm_required: true,
      explicit_interests: ['food'],
      revision: 8,
    }),
    preferenceMutations: [preferenceFixture({
      region_id: null,
      region_label: null,
      region_scope: 'all',
      location_source: 'manual',
      location_accuracy: 'unknown',
      location_consent_state: 'off',
      location_reconfirm_required: false,
      explicit_interests: ['food'],
      revision: 9,
    })],
  })
  const panel = wrapper.get('#khu-vuc-de-xuat')
  await panel.get('[data-action="choose-region-again"]').trigger('click')
  await panel.get('[data-region="all"]').trigger('click')
  await flushUi()
  expect(panel.find('[data-state="location-reconfirm"]').exists()).toBe(false)
  expect(panel.text()).toContain('Ẩm thực')
  expect(getCurrentPosition).not.toHaveBeenCalled()
  wrapper.unmount()
})
```

Add a setup-sheet stale token test with explicit interaction steps:

```ts
it('discards a stale location token and requires an explicit resolve again', async () => {
  authState.user.value = { id: 'user-1' }
  authState.isLoggedIn.value = true
  Object.defineProperty(navigator, 'geolocation', {
    configurable: true,
    value: {
      getCurrentPosition: (success: PositionCallback) => success({
        coords: { latitude: 10.24, longitude: 105.97 },
      } as GeolocationPosition),
    },
  })
  const wrapper = await mountSetupHarness()
  await flushUi()
  const dialog = () => document.body.querySelector('[role="dialog"]') as HTMLElement
  ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
  await flushUi()
  ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
  await flushUi()
  ;(dialog().querySelector('[data-action="use-location"]') as HTMLButtonElement).click()
  await flushUi()
  apiFetchMock.mockRejectedValueOnce({
    response: { status: 409, _data: snapshot({ revision: 2, location_reconfirm_required: true }) },
  })

  ;(dialog().querySelector('[data-action="confirm-location"]') as HTMLButtonElement).click()
  await flushUi()

  expect(dialog().textContent).toContain('xác định lại khu vực')
  expect(dialog().querySelector('[data-action="confirm-location"]')).toBeNull()
  expect(dialog().querySelector('[data-action="retry-location"]')).toBeTruthy()
  wrapper.unmount()
})
```

Assert no geolocation call occurs when the settings reconfirm banner mounts or its manual CTA is clicked.

- [ ] **Step 2: Run RED mounted frontend tests**

Run from `web-nuxt`:

```powershell
npm test -- tests/personalization-preferences.test.ts tests/location-consent.test.ts
```

Expected: FAIL because the snapshot field, banner, focus target and stale state do not exist.

- [ ] **Step 3: Implement public state normalization and existing-style UI**

Add the required field to types/defaults:

```ts
export interface PreferenceSnapshot {
  region_id: string | null
  region_label: string | null
  region_scope: PreferenceRegionScope
  location_source: PreferenceLocationSource
  location_accuracy: PreferenceLocationAccuracy
  location_consent_state: PreferenceConsentState
  location_enabled: boolean
  personalization_enabled: boolean
  explicit_interests: string[]
  recommendation_reset_at: string | null
  consent_version: string | null
  location_reconfirm_required: boolean
  revision: number
  derived_age_band?: PreferenceAgeBand
}
```

Normalize backward-compatible absence as false:

```ts
location_reconfirm_required: value.location_reconfirm_required === true,
```

Do not add this field to `PreferencePatch`.

In settings, place the reconfirm banner after offline/conflict banners:

```vue
<div
  v-if="preferenceView.location_reconfirm_required"
  class="preference-banner preference-reconfirm"
  data-state="location-reconfirm"
  role="status"
  aria-live="polite"
>
  <div>
    <strong>Chọn lại khu vực ưu tiên</strong>
    <p>Khu vực trước đây cần được chọn lại để bảo vệ quyền riêng tư. Sở thích và dữ liệu đã lưu của bạn vẫn được giữ nguyên.</p>
  </div>
  <button type="button" class="btn btn-primary btn-sm" data-action="choose-region-again" @click="focusManualRegionChoices">
    Chọn lại khu vực
  </button>
</div>
```

Give the manual group `ref="manualRegionGroup"`, `data-region-group="manual"`, `tabindex="-1"`, then implement exact focus/scroll behavior:

```ts
function focusManualRegionChoices() {
  const target = manualRegionGroup.value
  if (!target) return
  target.focus({ preventScroll: true })
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  target.scrollIntoView({ block: 'center', behavior: reduced ? 'auto' : 'smooth' })
}
```

When applying a manual region, optimistic view may set `location_reconfirm_required: false`, but the request body must not include it. Server response remains authoritative and rollback restores the previous banner on failure.

In `PersonalizeSetupSheet`, extend the state union with `stale`. On confirmation result status 409:

```ts
resolvedLocation.value = null
locationAttempted.value = false
locationState.value = 'stale'
```

Render the stale copy and a `retry-location` button that calls `useLocation()` only after a new user gesture. Do not automatically reuse or resolve the old token.

- [ ] **Step 4: Run GREEN frontend tests, typecheck and build**

Run from `web-nuxt`:

```powershell
npm test -- tests/personalization-preferences.test.ts tests/location-consent.test.ts tests/personalization-feature-flags.test.ts
npm run typecheck
npm run build
```

Expected: mounted tests pass, no geolocation is triggered by banner/CTA mount, stale token requires a new gesture, typecheck/build exit 0.

- [ ] **Step 5: Commit Task 7**

```powershell
git add web-nuxt/types/personalization.ts web-nuxt/composables/usePersonalizationPreferences.ts web-nuxt/pages/cai-dat.vue web-nuxt/components/PersonalizeSetupSheet.vue web-nuxt/tests/personalization-preferences.test.ts web-nuxt/tests/location-consent.test.ts
git diff --cached --check
git commit -m "feat: add location reconfirm recovery UI"
```

---

### Task 8: Final verification, report and whole-branch review

**Files:**
- Create: `docs/superpowers/reports/2026-07-29-np1-1-location-remediation-verification.md`
- Modify: `.superpowers/sdd/2026-07-29-np1-1-location-remediation/progress.md` (ignored local ledger)
- Modify production/tests only for findings returned by the scoped final review

**Interfaces:**
- Produces fresh evidence for migration, privacy, backend, frontend and staged repository gates.
- Produces explicit `not run/not in scope` wording for official full backend and Browser/Stitch when unavailable.
- Branch is merge-ready only after whole-branch reviewer approves base `2bca1dd7f3afce9ad47f70b51b815da62305e559..HEAD` including NP-1.1.

- [ ] **Step 1: Run focused backend and disposable PostgreSQL gates**

Run:

```powershell
python -m pytest -q agent/tests/test_database.py agent/tests/test_migration_chain.py agent/tests/test_migration_apply.py agent/tests/test_user_preferences.py agent/tests/test_location_resolver.py agent/tests/test_public_api.py agent/tests/test_auth_security_hardening.py
```

Run the existing real PostgreSQL personalization matrix only when its loopback test database variable is present:

```powershell
if ($env:PERSONALIZATION_EVENTS_TEST_DATABASE_URL) {
  python -m pytest -q agent/tests/test_personalization_events.py
} else {
  Write-Output 'NOT RUN: PERSONALIZATION_EVENTS_TEST_DATABASE_URL is not configured'
}
```

Run migration/remediation databases when configured:

```powershell
$env:LOCATION_REMEDIATION_TEST_DATABASE_URL = $env:MIGRATION_APPLY_TEST_DATABASE_URL
python -m pytest -q agent/tests/test_location_remediation_postgres.py agent/tests/test_migration_readiness_postgres.py
```

Record exact pass/skip/fail counts and elapsed time. If an environment variable is absent, record the command as `not run` with the missing variable; do not claim pass.

- [ ] **Step 2: Run frontend behavior/type/build gates**

Run from `web-nuxt`:

```powershell
npm test
npm run typecheck
npm run build
```

Record exact Vitest file/test counts and build warnings. Existing warnings may be retained, but no build error is acceptable.

- [ ] **Step 3: Run privacy/static/repository gates**

Run from repository root:

```powershell
python -m py_compile agent/user_preferences.py agent/location_resolver.py agent/public_api.py agent/personalization_events.py agent/scheduler.py
git diff --check
git status --short --untracked-files=all
```

Run searches that fail if remediation introduces persistent sensitive fields:

```powershell
rg -n "latitude|longitude|confirmation_token|location_confirmation_token|nonce" agent/migrations/073_location_preference_remediation.sql agent/user_preferences.py agent/scheduler.py
rg -n "readFileSync\(|toContain\(.*\.vue|toContain\(.*\.ts" web-nuxt/tests/personalization-preferences.test.ts web-nuxt/tests/location-consent.test.ts
```

Interpret the first search manually: transient route/token references are allowed only in resolver/API code, not migration/schema/persistence/logging. The behavior-test search must return no source-inspection assertions.

Stage only intended NP-1.1 paths, then run:

```powershell
git diff --cached --check
python scripts/checks/run_hard.py --staged
```

Expected: `hard=0`, ratchet does not increase and no package manifest/lock, homepage, public catalog or unrelated migration is staged.

- [ ] **Step 4: Write verification report and request whole-branch review**

The report must contain:

```markdown
# NP-1.1 location remediation verification

Base: 2bca1dd7f3afce9ad47f70b51b815da62305e559
Head source: exact output of `git rev-parse HEAD` captured at report time

## Migration and PostgreSQL
- command, result, counts, elapsed time

## Backend
- command, result, counts, elapsed time

## Frontend
- command, result, counts, build warnings

## Privacy and scope
- no raw GPS/IP/token persistence
- no token/nonce table
- manual Toàn tỉnh precedence evidence
- interests/consent/workspace preservation evidence

## Limitations
- official backend runner: pass only if freshly run; otherwise not run
- Browser/Stitch rendered verification: not in scope/not run

## Rollout runbook
1. Disable `preference_ui_v1`, `PREFERENCE_PROFILE_V1` and `LOCATION_RESOLVER_V1`.
2. Drain in-flight preference/resolver mutations.
3. Apply migration 073 and verify readiness 73.
4. Deploy runtime guard, worker, token v2 and frontend state.
5. Enable `PREFERENCE_PROFILE_V1`, then `preference_ui_v1`.
6. Enable `LOCATION_RESOLVER_V1` last and monitor aggregate quarantine/stale counts.
7. On rollback, keep mutation flags off; never remove constraints, restore quarantined location or re-enable token v1.
```

Use `superpowers:requesting-code-review` for a whole-branch review of `2bca1dd7..HEAD`. Any finding gets strict systematic-debugging + TDD, fresh scoped reviewer and ledger entry. Do not merge while findings remain.

- [ ] **Step 5: Commit final evidence after approval**

```powershell
git add docs/superpowers/reports/2026-07-29-np1-1-location-remediation-verification.md
git diff --cached --check
git commit -m "test: verify NP-1.1 location remediation"
git status --short --branch --untracked-files=all
```

Expected: worktree clean except ignored SDD ledger, final review approved, and no Browser/Stitch or official-runner evidence is overstated.

---

## Final Acceptance Checklist

- [ ] Migration 073 quarantines all pre-cutover GPS/IP and every invalid manual/default tuple.
- [ ] Canonical manual Vĩnh Long/Bến Tre/Trà Vinh/`Toàn tỉnh` and valid default survive migration.
- [ ] Interests, personalization state, consent history, reset timestamp and workspace survive quarantine.
- [ ] Load, export, unrelated PATCH and recommendation reset cannot return or rewrite unsafe region.
- [ ] Manual `Toàn tỉnh` is not overwritten by GPS/IP.
- [ ] Resolver token v2 is user-bound, revision-bound, 300-second TTL and effectively one-use.
- [ ] No one-time token/nonce table, cache, column or cleanup job exists.
- [ ] Stale token returns 409; invalid/expired/tampered/cross-user token returns 422.
- [ ] PostgreSQL direct invalid writes fail constraints.
- [ ] Self-healing worker is bounded to 100, idempotent and logs aggregate reasons only.
- [ ] UI reconfirm banner preserves interests and focuses manual choices without geolocation.
- [ ] Frontend stale confirmation discards the old token and requires a new user gesture.
- [ ] Behavior-level frontend tests, typecheck and build pass.
- [ ] Focused backend/PostgreSQL/migration/privacy gates pass with fresh evidence.
- [ ] Browser/Stitch and official backend limitations are reported honestly.
- [ ] Rollout runbook disables mutation flags before migration and never rolls back constraints/token v1.
- [ ] Whole-branch review approves NP-1.1 before merge.
