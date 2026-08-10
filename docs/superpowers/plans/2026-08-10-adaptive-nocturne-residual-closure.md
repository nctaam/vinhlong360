# Adaptive Nocturne Residual Closure Implementation Plan

> STATUS: active - approved implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining planner-concurrency, feature-flag resilience, ward contact telemetry, and CI accessibility-independence findings without changing existing public/auth/RBAC/data-ownership behavior.

**Architecture:** Use an additive Postgres migration plus one optimistic-concurrency `PUT` route for planner updates; keep legacy feature visibility independent from new rollout capabilities; reuse the existing privacy-safe contact beacon on the ward surface; and make every accessibility CI step carry an explicit `always()` condition and unavailable failure marker. Each slice owns its focused tests and commit, then a final verification task runs the combined quality gates.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, PostgreSQL 16, Nuxt 3, Vue 3, TypeScript, Vitest, GitHub Actions, pytest.

## Global Constraints

- Work only in `C:/Code/vinhlong360/.worktrees/adaptive-nocturne-residual-closure` on branch `codex/adaptive-nocturne-residual-closure`, based on commit `294d9891` plus approved spec commit `fc2b4d09`.
- Do not edit, stage, overwrite, or clean the protected dirty files in the primary checkout at `C:/Code/vinhlong360`.
- `revision` starts at integer `1`, increments exactly once per successful mutation, and stale writes return HTTP `409` with code `plan_revision_conflict` plus the current server snapshot.
- Preserve `GET`, `POST`, `DELETE`, `merge`, `publish`, Postgres-only, auth, CSRF, rate-limit, and owner-bound behavior for `/api/my-plans`.
- Established flags keep registry defaults when settings are null, empty, missing, or malformed; new `_v1` rollout flags and unknown keys fail closed.
- `ai_recommendations`, `ai_tips`, and `ai_best_time` are not AND-gated by `public_*_v1` flags.
- Contact telemetry sends only public entity id plus the allowlisted action; it never sends phone numbers, raw queries, coordinates, cookies, or arbitrary metadata.
- Contact telemetry is synchronous best-effort and never prevents `tel:` navigation.
- Visual smoke failure must not skip preview, axe scan, accessibility gate, teardown, or artifact-upload declarations.
- No new runtime dependency, telemetry provider, event-sourcing layer, ETag protocol, or server-side plan merge behavior.

## File Map

- `agent/migrations/079_user_plans_revision.sql`: additive/idempotent revision and update-timestamp schema.
- `agent/plans.py`: plan snapshot serialization, `PlanUpdateBody`, atomic revision update, conflict response, publish revision bump.
- `agent/tests/test_plans_revision.py`: validation, serialization, route, SQL/ownership, success, conflict, and mutation regression tests.
- `agent/tests/test_session_be.py`: route-mount and SQLite/Postgres guard contract for the new PUT route.
- `agent/tests/test_phase16_coverage.py`: CSRF, path-validation, and rate-limit coverage lists for `update_plan`.
- `docs/api-contract.md`: documented additive fields, PUT route, and `409` payload.
- `web-nuxt/utils/featureFlags.ts`: established-vs-rollout resolution policy.
- `web-nuxt/tests/personalization-feature-flags.test.ts`: resolver matrix for missing, malformed, explicit, rollout, and unknown values.
- `web-nuxt/pages/xa-phuong/[id].vue`: ward phone CTA contact metadata and beacon handler.
- `web-nuxt/tests/contact-funnel-beacon.test.ts`: mounted ward phone-action behavior and privacy contract.
- `.github/workflows/ci.yml`: explicit independent step conditions and `a11y-unavailable` markers.
- `web-nuxt/tests/public-accessibility-gate.test.mjs`: static CI condition/failure-path contract.

---

### Task 1: Add Revision-Safe Planner Updates

**Files:**
- Create: `agent/migrations/079_user_plans_revision.sql`
- Create: `agent/tests/test_plans_revision.py`
- Modify: `agent/plans.py`
- Modify: `agent/tests/test_session_be.py`
- Modify: `agent/tests/test_phase16_coverage.py`
- Modify: `docs/api-contract.md`

**Interfaces:**
- Consumes: existing `PlanBody`, `_row_plan(row)`, `db._conn()`, `db._ph`, `require_user`, `require_csrf`, `validate_path_id`, `check_rate`.
- Produces: `PlanUpdateBody(title: str, stops: list[dict], expected_revision: int)`, `PUT /api/my-plans/{plan_id}`, and the stable `PlanSnapshot` fields `id`, `title`, `stops`, `is_public`, `savedAt`, `revision`, `updatedAt`.

- [ ] **Step 1: Write the additive migration and migration contract tests**

Create `agent/migrations/079_user_plans_revision.sql` with exactly one additive ownership-neutral migration:

```sql
ALTER TABLE user_plans
    ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE user_plans
SET revision = 1
WHERE revision IS NULL OR revision < 1;

CREATE INDEX IF NOT EXISTS idx_user_plans_user_updated
    ON user_plans(user_id, updated_at DESC);
```

In `agent/tests/test_plans_revision.py`, add static migration checks and Pydantic RED tests:

```python
from pathlib import Path

import pytest
from pydantic import ValidationError

import plans


MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "079_user_plans_revision.sql"


def test_revision_migration_is_additive_and_idempotent():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1" in sql
    assert "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_user_plans_user_updated" in sql
    assert "DROP TABLE" not in sql.upper()
    assert "DELETE FROM user_plans" not in sql


@pytest.mark.parametrize("bad", [True, "3", 0, -1])
def test_update_body_rejects_non_positive_integer_revision(bad):
    with pytest.raises(ValidationError):
        plans.PlanUpdateBody(title="A", stops=[], expected_revision=bad)
```

- [ ] **Step 2: Run the planner tests to verify RED**

Run:

```powershell
python -m pytest agent/tests/test_plans_revision.py -q
```

Expected: FAIL because `PlanUpdateBody` and the migration file do not exist.

- [ ] **Step 3: Add snapshot serialization and the update body**

In `agent/plans.py`, add strict validation and include the two additive read fields:

```python
class PlanUpdateBody(PlanBody):
    expected_revision: int = Field(ge=1, strict=True)


def _row_plan(row) -> dict:
    d = db._row_to_dict(row)
    stops = d.get("stops") or []
    if isinstance(stops, str):
        try:
            stops = json.loads(stops)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Corrupted stops JSON for plan %s", d.get("id"))
            stops = []
    return {
        "id": str(d["id"]),
        "title": d.get("title") or "Lịch trình",
        "stops": stops if isinstance(stops, list) else [],
        "is_public": bool(d.get("is_public")),
        "savedAt": str(d.get("created_at") or ""),
        "revision": int(d.get("revision") or 1),
        "updatedAt": str(d.get("updated_at") or d.get("created_at") or ""),
    }
```

Update every plan SELECT/RETURNING list to request explicit columns `id, title, stops, is_public, created_at, revision, updated_at`; do not introduce `SELECT *`.

Change `_insert` to `RETURNING id, title, stops, is_public, created_at, revision, updated_at` and return `_row_plan(row)`. Keep `POST /api/my-plans` backward compatible by returning the existing `id` and `saved` keys plus an additive `plan` snapshot; make `merge_plans` ignore the returned snapshot and continue returning the full list.

```python
def _insert(conn, uid: str, body: PlanBody) -> dict:
    ph = db._ph
    stops = (body.stops or [])[:MAX_STOPS]
    row = db._fetchone(conn, f"""
        INSERT INTO user_plans (user_id, title, stops, revision, updated_at)
        VALUES ({ph}::uuid, {ph}, {ph}::jsonb, 1, NOW())
        RETURNING id, title, stops, is_public, created_at, revision, updated_at
    """, (uid, (body.title or "Lịch trình")[:120], json.dumps(stops, ensure_ascii=False)))
    return _row_plan(row)
```

`add_plan` returns `{"id": plan["id"], "saved": True, "plan": plan}`; `merge_plans` calls `_insert` for side effects and discards its return value.

- [ ] **Step 4: Write behavior tests for success, conflict, ownership, and existing mutations**

Extend `agent/tests/test_plans_revision.py` with a small fake connection that records SQL and returns controlled rows. Call `asyncio.run(plans.update_plan(plan_id=PLAN_ID, body=plans.PlanUpdateBody(title="Mới", stops=[], expected_revision=3), user={"id": OWNER_ID}, _csrf=None))` directly. The tests must assert:

```python
def test_row_plan_exposes_revision_and_updated_at():
    out = plans._row_plan({
        "id": "11111111-1111-4111-8111-111111111111",
        "title": "Cuối tuần",
        "stops": [],
        "is_public": False,
        "created_at": "2026-08-10T01:00:00+00:00",
        "revision": 4,
        "updated_at": "2026-08-10T02:00:00+00:00",
    })
    assert out["revision"] == 4
    assert out["savedAt"].startswith("2026-08-10T01:00")
    assert out["updatedAt"].startswith("2026-08-10T02:00")


def test_update_sql_is_atomic_and_owner_bound(recording_db):
    # recording_db returns an updated row with revision=4.
    result = asyncio.run(plans.update_plan(
        plan_id=PLAN_ID,
        body=plans.PlanUpdateBody(title="Mới", stops=[], expected_revision=3),
        user={"id": OWNER_ID},
        _csrf=None,
    ))
    sql, params = recording_db.last_fetchone
    assert "WHERE id::text" in sql
    assert "user_id" in sql
    assert "revision" in sql
    assert "revision = revision + 1" in sql
    assert result["plan"]["revision"] == 4


def test_stale_update_returns_409_with_current_snapshot(recording_db):
    recording_db.update_row = None
    recording_db.current_row = SERVER_SNAPSHOT_ROW
    response = asyncio.run(plans.update_plan(
        plan_id=PLAN_ID,
        body=plans.PlanUpdateBody(title="Local", stops=[], expected_revision=3),
        user={"id": OWNER_ID},
        _csrf=None,
    ))
    assert response.status_code == 409
    payload = json.loads(response.body)
    assert payload["code"] == "plan_revision_conflict"
    assert payload["current"]["revision"] == 4
```

Also assert a missing/foreign-owner current row returns `404`, `_insert` produces revision `1`, `publish_plan` executes `revision = revision + 1, updated_at = NOW()`, and `merge_plans` still invokes `_insert` rather than an update/upsert path.

- [ ] **Step 5: Implement `PUT /api/my-plans/{plan_id}`**

Add `from fastapi.responses import JSONResponse` and place the route after create and before delete so literal `/merge` routing remains unaffected:

```python
@router.put("/{plan_id}", summary="Update a plan with optimistic concurrency")
async def update_plan(
    plan_id: str,
    body: PlanUpdateBody,
    user=Depends(require_user),
    _csrf=Depends(require_csrf),
):
    plan_id = validate_path_id(plan_id, "plan_id")
    check_rate(f"plan:{user['id']}", 30, 300, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    uid = str(user["id"])

    def _query():
        ph = db._ph
        with db._conn() as conn:
            updated = db._fetchone(conn, f"""
                UPDATE user_plans
                SET title = {ph}, stops = {ph}::jsonb,
                    revision = revision + 1, updated_at = NOW()
                WHERE id::text = {ph} AND user_id = {ph}::uuid
                  AND revision = {ph}
                RETURNING id, title, stops, is_public, created_at, revision, updated_at
            """, (
                (body.title or "Lịch trình")[:120],
                json.dumps((body.stops or [])[:MAX_STOPS], ensure_ascii=False),
                plan_id,
                uid,
                body.expected_revision,
            ))
            if updated:
                return {"plan": _row_plan(updated)}

            current = db._fetchone(conn, f"""
                SELECT id, title, stops, is_public, created_at, revision, updated_at
                FROM user_plans WHERE id::text = {ph} AND user_id = {ph}::uuid
            """, (plan_id, uid))
            if not current:
                raise HTTPException(404, "Lịch trình không tồn tại hoặc không thuộc về bạn")
            return JSONResponse(status_code=409, content={
                "detail": "Lịch trình đã thay đổi trên thiết bị khác",
                "code": "plan_revision_conflict",
                "current": _row_plan(current),
            })

    return await asyncio.to_thread(_query)
```

Update `publish_plan` to atomically set `is_public`, increment `revision`, update `updated_at`, and return the new revision without removing the existing `is_public` response field.

- [ ] **Step 6: Update route/security regression lists and API docs**

In `agent/tests/test_session_be.py`, assert:

```python
assert ("PUT", "/api/my-plans/{plan_id}") in pairs
```

and preserve the SQLite `503` guard for `client.put("/api/my-plans/test", json={"title": "test", "stops": [], "expected_revision": 1})`.

In `agent/tests/test_phase16_coverage.py`, add `update_plan` to plan mutation CSRF/rate-limit checks and to path validation coverage. In `docs/api-contract.md`, add the PUT route to both planner tables and document the `expected_revision`, `200 PlanSnapshot`, and `409 plan_revision_conflict` contract.

- [ ] **Step 7: Run GREEN planner tests**

Run:

```powershell
python -m pytest agent/tests/test_plans_revision.py agent/tests/test_session_be.py agent/tests/test_phase16_coverage.py -q
```

Expected: PASS; Postgres-only cases may skip locally, while static/unit contracts must pass.

- [ ] **Step 8: Commit the planner slice**

```powershell
git add agent/migrations/079_user_plans_revision.sql agent/plans.py agent/tests/test_plans_revision.py agent/tests/test_session_be.py agent/tests/test_phase16_coverage.py docs/api-contract.md
git commit -m "feat: add revision-safe plan updates"
```

---

### Task 2: Preserve Established Feature Defaults

**Files:**
- Modify: `web-nuxt/utils/featureFlags.ts`
- Modify: `web-nuxt/tests/personalization-feature-flags.test.ts`

**Interfaces:**
- Consumes: `FEATURE_FLAGS`, `PUBLIC_CAPABILITY_FLAGS`, `featureFlagDefault`, `resolveFeatureFlag`, `resolvePublicCapabilityMode`.
- Produces: `isEstablishedFeatureFlag(key: string): boolean` and deterministic resolution that never AND-gates established `ai_*` sections with `public_*_v1`.

- [ ] **Step 1: Write the RED resolver matrix**

Change the test import to include `resolveFeatureFlag` and `resolvePublicCapabilityMode`, then add:

```ts
describe('feature flag resilience', () => {
  it.each([undefined, null, {}, { ai_recommendations: 'false' }, []])(
    'preserves established defaults for malformed settings %#',
    (flags) => {
      expect(resolveFeatureFlag('ai_recommendations', flags as Record<string, unknown>)).toBe(true)
      expect(resolveFeatureFlag('ai_tips', flags as Record<string, unknown>)).toBe(true)
      expect(resolveFeatureFlag('ai_best_time', flags as Record<string, unknown>)).toBe(true)
    },
  )

  it('honors explicit established overrides without a rollout capability', () => {
    expect(resolveFeatureFlag('ai_recommendations', { ai_recommendations: false })).toBe(false)
    expect(resolveFeatureFlag('ai_recommendations', { ai_recommendations: true })).toBe(true)
    expect(resolveFeatureFlag('ai_recommendations', { public_recommendation_v1: false })).toBe(true)
  })

  it('fails closed for rollout and unknown keys', () => {
    expect(resolveFeatureFlag('public_recommendation_v1', {})).toBe(false)
    expect(resolveFeatureFlag('preference_ui_v1', { preference_ui_v1: 'true' })).toBe(false)
    expect(resolveFeatureFlag('unknown_flag', { unknown_flag: true })).toBe(false)
    expect(resolvePublicCapabilityMode('recommendation', null)).toBe('deterministic')
  })

  it('keeps new enhancement flags behind their public capability', () => {
    expect(resolveFeatureFlag('recommendation_explanations_v1', {
      recommendation_explanations_v1: true,
      public_personalization_v1: false,
    })).toBe(false)
    expect(resolveFeatureFlag('recommendation_explanations_v1', {
      recommendation_explanations_v1: true,
      public_personalization_v1: true,
    })).toBe(true)
  })
})
```

- [ ] **Step 2: Run the feature tests to verify RED**

```powershell
npm --prefix web-nuxt test -- --run tests/personalization-feature-flags.test.ts
```

Expected: FAIL because established AI flags are currently AND-gated with missing public capability flags.

- [ ] **Step 3: Implement explicit established/rollout classification**

In `web-nuxt/utils/featureFlags.ts`, add a frozen established-key set and remove only the established AI flags from `LEGACY_PUBLIC_CAPABILITY` gating. Keep capability gating for `preference_ui_v1` and `recommendation_explanations_v1`, so new enhancements still require both their own flag and the relevant public capability:

```ts
const ESTABLISHED_FEATURE_FLAGS = new Set([
  'chat_widget',
  'ai_recommendations',
  'ai_tips',
  'ai_best_time',
  'reviews',
  'nearby',
  'onboarding',
])

const LEGACY_PUBLIC_CAPABILITY: Partial<Record<string, PublicCapability>> = Object.freeze({
  preference_ui_v1: 'personalization',
  recommendation_explanations_v1: 'personalization',
})

export function isEstablishedFeatureFlag(key: string): boolean {
  return ESTABLISHED_FEATURE_FLAGS.has(key)
}

export function resolveFeatureFlag(
  key: string,
  flags: Record<string, unknown> | null | undefined,
): boolean {
  const definition = FEATURE_FLAGS.find(flag => flag.key === key)
  if (!definition) return false

  const safeFlags = flags && typeof flags === 'object' && !Array.isArray(flags) ? flags : null
  const override = safeFlags?.[key]
  const enabled = typeof override === 'boolean'
    ? override
    : isEstablishedFeatureFlag(key) ? definition.default : false
  const capability = LEGACY_PUBLIC_CAPABILITY[key]
  if (!capability || !enabled) return enabled
  return safeFlags?.[PUBLIC_CAPABILITY_FLAGS[capability]] === true
}
```

`resolvePublicCapabilityMode` must continue resolving the exact `public_*_v1` key, so absent/malformed capability flags remain `deterministic`.

- [ ] **Step 4: Run GREEN feature tests and typecheck the touched contract**

```powershell
npm --prefix web-nuxt test -- --run tests/personalization-feature-flags.test.ts tests/public-kill-switch.test.ts
npm --prefix web-nuxt run typecheck
```

Expected: both commands PASS.

- [ ] **Step 5: Commit the feature-flag slice**

```powershell
git add web-nuxt/utils/featureFlags.ts web-nuxt/tests/personalization-feature-flags.test.ts
git commit -m "fix: preserve established feature defaults"
```

---

### Task 3: Instrument Ward Phone CTAs

**Files:**
- Modify: `web-nuxt/pages/xa-phuong/[id].vue`
- Modify: `web-nuxt/tests/contact-funnel-beacon.test.ts`

**Interfaces:**
- Consumes: `trackContactView(entityId: unknown, action: ContactAction): boolean` from `~/composables/useContactBeacon`.
- Produces: ward phone links carrying `data-contact-action="phone"`, `data-contact-surface`, `data-contact-entity-id`, `data-contact-outcome="navigation"`, and a synchronous click beacon.

- [ ] **Step 1: Add RED mounted ward behavior tests**

Import the real ward page and mount it with the existing Nuxt test harness. Mock its entity/ward fetches so the fixture renders a ward-level phone, police phone, and one facility phone. Assert behavior rather than only source text:

```ts
it('instruments every rendered ward phone action without blocking tel navigation', async () => {
  const wrapper = await mountWard({
    place: {
      id: 'phuong-1',
      name: 'Phường 1',
      level: 'phuong',
      area: 'vinh-long',
      attributes: { phone: '02703822100', police_phone: '02703822101' },
    },
    facilities: [{ id: 'tram-y-te-1', name: 'Trạm y tế', attributes: { phone: '02703822102' } }],
  })

  const links = wrapper.findAll('a[href^="tel:"]')
  expect(links.length).toBeGreaterThanOrEqual(3)
  for (const link of links) {
    expect(link.attributes('data-contact-action')).toBe('phone')
    expect(link.attributes('data-contact-surface')).toMatch(/^ward-(detail|directory)$/)
    expect(link.attributes('data-contact-entity-id')).toBeTruthy()
    expect(link.attributes('data-contact-outcome')).toBe('navigation')
    const event = new MouseEvent('click', { bubbles: true, cancelable: true })
    expect(link.element.dispatchEvent(event)).toBe(true)
    expect(event.defaultPrevented).toBe(false)
  }

  expect(fetchMock.mock.calls.every(([url]) => !String(url).includes('02703822'))).toBe(true)
})
```

Add a second assertion that repeated clicks on the same entity/action produce one beacon while two facility ids produce independent beacons.

- [ ] **Step 2: Run the contact test to verify RED**

```powershell
npm --prefix web-nuxt test -- --run tests/contact-funnel-beacon.test.ts
```

Expected: FAIL because the ward page does not import or call `trackContactView` and its two residual phone links have no contact metadata.

- [ ] **Step 3: Wire the existing contact beacon into every ward phone link**

In the page script, import:

```ts
import { trackContactView } from '~/composables/useContactBeacon'
```

Apply the exact metadata/handler patterns:

```vue
<a
  v-if="wardPrimaryAction.id === 'call'"
  class="ward-primary-action"
  data-color-role="action-primary"
  data-contact-action="phone"
  data-contact-surface="ward-detail"
  :data-contact-entity-id="data.place.id"
  data-contact-outcome="navigation"
  :href="wardPrimaryAction.href"
  @click="trackContactView(data.place.id, 'phone')"
>
  {{ wardPrimaryAction.label }}
</a>
```

For `attrs.police_phone`, use `data.place.id` and surface `ward-detail`. For each facility phone, use `f.id` and surface `ward-directory`. Do not add a request body, phone metadata, `preventDefault`, `await`, or new telemetry endpoint.

- [ ] **Step 4: Run GREEN contact tests and focused typecheck**

```powershell
npm --prefix web-nuxt test -- --run tests/contact-funnel-beacon.test.ts
npm --prefix web-nuxt run typecheck
```

Expected: both commands PASS.

- [ ] **Step 5: Commit the contact slice**

```powershell
git add -- web-nuxt/pages/xa-phuong/[id].vue web-nuxt/tests/contact-funnel-beacon.test.ts
git commit -m "fix: instrument ward contact actions"
```

---

### Task 4: Make Accessibility CI Independent of Visual Smoke

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `web-nuxt/tests/public-accessibility-gate.test.mjs`

**Interfaces:**
- Consumes: the existing `frontend` workflow job, `scripts/smoke_e2e_chrome.mjs`, `scripts/axe_scan.mjs`, and `checks.check_axe`.
- Produces: explicit `if: always()` execution conditions, `A11Y_AVAILABLE`, and the marker text `a11y-unavailable`.

- [ ] **Step 1: Write RED workflow-condition tests**

Extend `public-accessibility-gate.test.mjs` with helpers that isolate a named workflow step and assert exact conditions:

```js
function workflowStep(workflow, name) {
  const marker = `      - name: ${name}\n`
  const start = workflow.indexOf(marker)
  expect(start).toBeGreaterThanOrEqual(0)
  const next = workflow.indexOf('\n      - name:', start + marker.length)
  return workflow.slice(start, next === -1 ? workflow.length : next)
}

it('runs visual and accessibility evidence independently after failures', async () => {
  const ci = await readFile(resolve(import.meta.dirname, '../../.github/workflows/ci.yml'), 'utf8')
  for (const name of [
    'Capture fresh public visual evidence',
    'Start preview server for a11y scan',
    'Accessibility scan (axe-core, 14 trang)',
    'Accessibility gate (R30.6)',
    'Stop preview server',
    'Upload axe report',
  ]) {
    expect(workflowStep(ci, name)).toContain('if: always()')
  }
  expect(workflowStep(ci, 'Start preview server for a11y scan')).toContain('a11y-unavailable')
  expect(workflowStep(ci, 'Accessibility scan (axe-core, 14 trang)')).toContain('A11Y_AVAILABLE')
})
```

- [ ] **Step 2: Run the CI contract test to verify RED**

```powershell
npm --prefix web-nuxt test -- --run tests/public-accessibility-gate.test.mjs
```

Expected: FAIL because the visual, preview, axe, and gate steps currently rely on GitHub's implicit `success()` behavior.

- [ ] **Step 3: Add explicit independent workflow conditions**

In `.github/workflows/ci.yml`:

```yaml
      - name: Capture fresh public visual evidence
        if: always()
```

Use this preview startup body under `if: always()`:

```yaml
      - name: Start preview server for a11y scan
        if: always()
        run: |
          if [ ! -d .output ]; then
            echo "a11y-unavailable: build output missing" | tee ../a11y-status.txt
            echo "A11Y_AVAILABLE=false" >> "$GITHUB_ENV"
            exit 1
          fi
          npm run preview &
          echo "PREVIEW_PID=$!" >> "$GITHUB_ENV"
          echo "A11Y_AVAILABLE=true" >> "$GITHUB_ENV"
```

Add `if: always()` to the axe scan and gate. Start each command with this explicit guard, preserving a non-zero result:

```yaml
        run: |
          if [ "${A11Y_AVAILABLE:-false}" != "true" ]; then
            echo "a11y-unavailable: preview not started" | tee a11y-status.txt
            exit 1
          fi
          node scripts/axe_scan.mjs
```

For `check_axe`, use the same guard before `python3 -m checks.check_axe`. Keep `Stop preview server` and `Upload axe report` at `if: always()`; make teardown tolerate an unset PID with `if [ -n "${PREVIEW_PID:-}" ]; then kill "$PREVIEW_PID" 2>/dev/null || true; fi`. Upload both `axe-report.json` and `a11y-status.txt` with `if-no-files-found: warn`.

- [ ] **Step 4: Run GREEN CI contract tests**

```powershell
npm --prefix web-nuxt test -- --run tests/public-accessibility-gate.test.mjs
python -m pytest tests/checks/test_fe_gates.py tests/test_release_quality_gates.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the CI slice**

```powershell
git add .github/workflows/ci.yml web-nuxt/tests/public-accessibility-gate.test.mjs
git commit -m "fix: keep accessibility gates independent"
```

---

### Task 5: Run Cross-Slice Verification and Record Evidence

**Files:**
- Create: `.superpowers/sdd/2026-08-10-adaptive-nocturne-residual-closure/verification-report.md` (git-ignored execution artifact)
- Modify only if a preceding test exposes a real regression in Task 1-4 files; fixes require the task review loop before this task can complete.

**Interfaces:**
- Consumes: commits produced by Tasks 1-4 and their task reports/reviews.
- Produces: one reproducible verification report containing commands, exit codes, pass/skip counts, and branch/worktree status.

- [ ] **Step 1: Verify the worktree and protected-checkout boundary**

Run:

```powershell
git status --short --branch
git -C C:/Code/vinhlong360 status --short --branch
```

Record the branch status. Confirm Task 1-4 commits exist only on `codex/adaptive-nocturne-residual-closure`; do not stage or modify primary-checkout dirty paths.

- [ ] **Step 2: Run focused backend tests**

```powershell
python -m pytest agent/tests/test_plans_revision.py agent/tests/test_session_be.py agent/tests/test_phase16_coverage.py tests/checks/test_fe_gates.py tests/test_release_quality_gates.py -q
```

Expected: PASS with only environment-declared Postgres skips.

- [ ] **Step 3: Run focused frontend tests**

```powershell
npm --prefix web-nuxt test -- --run tests/personalization-feature-flags.test.ts tests/public-kill-switch.test.ts tests/contact-funnel-beacon.test.ts tests/public-accessibility-gate.test.mjs
```

Expected: PASS.

- [ ] **Step 4: Run typecheck and non-coverage hard gates**

```powershell
npm --prefix web-nuxt run typecheck
python scripts/checks/run_hard.py --all
```

Expected: both commands exit `0`. If `run_hard.py --all` requires generated coverage unavailable in this worktree, run and record every non-coverage hard check individually; do not claim the coverage ratchet passed without `coverage.json`.

- [ ] **Step 5: Write the verification report**

Create `.superpowers/sdd/2026-08-10-adaptive-nocturne-residual-closure/verification-report.md` with:

```markdown
# Residual Closure Verification

- Branch: codex/adaptive-nocturne-residual-closure
- Base: 294d9891
- Spec: fc2b4d09
- Planner tests: record the exact command from Task 5 Step 2, exit code, pass count, and Postgres skip count.
- Frontend tests: record the exact command from Task 5 Step 3, exit code, and pass count.
- Typecheck: record the exact command and exit code.
- Hard gates: record each exact command and exit code; distinguish coverage-ratchet unavailable from a passing coverage run.
- Postgres coverage: record the executed run count or the explicit environment skip reason.
- Primary checkout: protected dirty files unchanged
```

Replace each instruction line with exact observed evidence before completing the task; the report remains git-ignored and is referenced from the SDD ledger.

- [ ] **Step 6: Commit only tracked verification fixes, if any**

If verification changed no tracked source, do not create an empty commit. If a reviewed fix was required, stage only its approved Task 1-4 files and commit with:

```powershell
git commit -m "fix: close residual verification regressions"
```

---

## Plan Completion Gates

- Every Task 1-4 commit has a clean task-scoped spec and quality review.
- Task 5 records all test commands and honest environment skips.
- A final whole-branch review covers `294d9891..HEAD`, including deferred-minor ledger entries.
- No Critical or Important finding remains unaddressed or unadjudicated.
- The final branch contains only approved residual-closure work and the committed spec/plan.
