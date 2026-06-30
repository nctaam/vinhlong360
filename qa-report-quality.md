# QA Quality Report - vinhlong360

Audit date: 2026-06-28

Scope: edge cases, performance/DoS, data integrity, API contract, accessibility, test quality, dependencies, and maintainability.

## Summary

| Severity | Count | Notes |
|---|---:|---|
| P0 Critical | 0 | No quality issue rises to immediate data-loss criticality by itself. |
| P1 High | 2 | Cross-thread comment integrity is in the security report; quality adds unbounded public data shaping. |
| P2 Medium | 13 | Main risks are unbounded reads, entity orphaning, API inconsistency, a11y widget bugs. |
| P3 Low | 4 | God files, loose tests, deprecation/dependency hygiene. |

## Findings

### [P1] Finding-027: Homepage builds from up to 100,000 entities per cache rebuild

**Chiều:** Performance / DoS / API Contract  
**File:** `agent/public_api.py:476`, `agent/public_api.py:497`, `agent/public_api.py:568`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-400

**Mô tả:** `/api/homepage` fetches `db.list_entities(limit=100000)` and unbounded itineraries on cache misses. A single cold cache rebuild does broad filtering/scoring in Python.

**Exploit scenario:**
1. Attacker triggers repeated cold-cache requests after deploy/restart.
2. Backend loads and scores a very large corpus.
3. CPU and memory spike before cache is warm.

**Root cause:** The endpoint has curated output but unbounded input selection.

**Fix:**
```python
featured = db.list_entities(limit=2000, offset=0, public_only=True, sort="newest")
all_itineraries = db.list_itineraries(limit=100)
```

**Test:**
```python
def test_homepage_uses_bounded_entity_query(monkeypatch, client):
    seen = {}
    monkeypatch.setattr(db, "list_entities", lambda **kw: seen.update(kw) or [])
    client.get("/api/homepage")
    assert seen["limit"] <= 2000
```

**Effort:** M

### [P1] Finding-028: Map-pins endpoint can materialize 100,000 entities and enrich per pin

**Chiều:** Performance / DoS  
**File:** `agent/public_api.py:720`, `agent/public_api.py:739`, `agent/public_api.py:763`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-400

**Mô tả:** `/api/map-pins` fetches up to 100,000 entities and then calls `_get_place` for each entity with `placeId`. Cache helps repeated places, but first-hit behavior is still broad.

**Exploit scenario:**
1. Attacker requests many type/area combinations.
2. Each cache key rebuilds a large pin list.
3. API spends CPU/memory serializing data not needed by the viewport.

**Root cause:** No bounding box, zoom-aware clustering, or hard limit.

**Fix:**
```python
async def get_map_pins(..., limit: int = Query(2000, ge=1, le=5000)):
    all_ents = db.list_entities(limit=limit, offset=0, ...)
```

**Test:**
```python
def test_map_pins_enforces_limit(client):
    assert client.get("/api/map-pins?limit=100000").status_code == 422
```

**Effort:** M

### [P2] Finding-029: Events endpoint ignores `limit` until after loading all event entities

**Chiều:** Performance / API Contract  
**File:** `agent/public_api.py:776`, `agent/public_api.py:781`, `agent/public_api.py:786`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-400

**Mô tả:** `/api/events` exposes a `limit` parameter but fetches `limit=100000` events first. The API contract suggests caller-controlled bounding, but the expensive part has already happened.

**Exploit scenario:**
1. Attacker calls `/api/events?include_past=true` repeatedly.
2. Backend loads every event before sorting/filtering.
3. Cache misses cause unnecessary CPU and DB work.

**Root cause:** Pagination is applied after broad data retrieval.

**Fix:**
```python
all_ents = db.list_entities(entity_type="event", limit=min(limit * 5, 1000), offset=0, public_only=True)
```

**Test:**
```python
def test_events_passes_bounded_limit_to_db(monkeypatch, client):
    seen = {}
    monkeypatch.setattr(db, "list_entities", lambda **kw: seen.update(kw) or [])
    client.get("/api/events?limit=20")
    assert seen["limit"] <= 1000
```

**Effort:** M

### [P2] Finding-030: Review stats loads all review content for sentiment/mentions

**Chiều:** Performance / DoS / Privacy  
**File:** `agent/public_api.py:980`, `agent/public_api.py:1010`, `agent/public_api.py:1037`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-400

**Mô tả:** `/api/entities/{id}/review-stats` selects every approved review `content` for an entity with no limit before mention extraction. Popular entities can create large memory and CPU work.

**Exploit scenario:**
1. Attacker requests review stats for a high-review entity.
2. Backend loads all text rows into memory.
3. Mention extraction processes an unbounded list.

**Root cause:** Aggregation query is bounded for ratings but not content analysis.

**Fix:**
```python
content_rows = db._fetchall(conn, f"""
    SELECT content FROM posts
    WHERE entity_id = {ph} AND post_type = 'review'
      AND moderation_status = 'approved' AND content IS NOT NULL AND content != ''
    ORDER BY created_at DESC
    LIMIT 500
""", (entity_id,))
```

**Test:**
```python
def test_review_stats_content_query_has_limit():
    assert "LIMIT 500" in inspect.getsource(public_api.get_review_stats)
```

**Effort:** S

### [P2] Finding-031: Itinerary listing has no pagination

**Chiều:** Performance / API Contract  
**File:** `agent/database.py:948`, `agent/database.py:955`, `agent/public_api.py:327`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-400

**Mô tả:** `db.list_itineraries()` returns every itinerary, and the public endpoint has no `limit` or `offset`. This is acceptable for tiny data but not as a production contract.

**Exploit scenario:**
1. Dataset grows through admin imports.
2. `/api/itineraries` returns every row.
3. Response size and render time grow without bound.

**Root cause:** Knowledge data was treated as static/small and never given list pagination.

**Fix:**
```python
def list_itineraries(self, area: str = None, limit: int = 100, offset: int = 0):
    rows = self._fetchall(conn, f"SELECT * FROM itineraries LIMIT {ph} OFFSET {ph}", (limit, offset))
```

**Test:**
```python
def test_itineraries_have_pagination(client):
    r = client.get("/api/itineraries?limit=0")
    assert r.status_code == 422
```

**Effort:** M

### [P2] Finding-032: Entity relationship table has no foreign keys to entities

**Chiều:** Data Integrity  
**File:** `init.sql:49`, `agent/database.py:289`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-1048

**Mô tả:** `relationships(from_id, to_id, type)` has a composite primary key but no FK to `entities(id)`. Orphan relationships can survive bad imports or manual edits.

**Exploit scenario:**
1. Import contains relationship to deleted entity.
2. DB accepts it.
3. Graph and related-place features return incomplete or misleading data.

**Root cause:** Knowledge graph integrity is validated in application/import code, not the database.

**Fix:**
```sql
ALTER TABLE relationships
  ADD CONSTRAINT relationships_from_fk FOREIGN KEY (from_id) REFERENCES entities(id) ON DELETE CASCADE,
  ADD CONSTRAINT relationships_to_fk FOREIGN KEY (to_id) REFERENCES entities(id) ON DELETE CASCADE;
```

**Test:**
```python
def test_relationship_to_missing_entity_rejected(pg_conn):
    with pytest.raises(Exception):
        pg_conn.execute("INSERT INTO relationships(from_id,to_id,type) VALUES ('missing','e1','near')")
```

**Effort:** M

### [P2] Finding-033: User entity references can orphan when knowledge entities change

**Chiều:** Data Integrity / Cross-DB Boundary  
**File:** `init.sql:208`, `agent/migrations/009_user_visits.sql:4`, `agent/migrations/011_share_plan_rsvp.sql:6`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-1048

**Mô tả:** `saved_entities`, `user_visits`, and `event_rsvp` keep `entity_id TEXT` without FK to entities. This may be intentional for snapshot rendering, but stale IDs need cleanup and validation.

**Exploit scenario:**
1. Admin deletes or renames an entity ID.
2. Saved/visited/RSVP rows remain.
3. User profile and counts reference missing content.

**Root cause:** PostgreSQL UGC and knowledge entity lifecycle are not fully coupled.

**Fix:**
```python
def cleanup_orphan_entity_refs():
    valid = {e["id"] for e in db.list_entities(limit=100000)}
    delete_saved_where_entity_not_in(valid)
```

**Test:**
```python
def test_orphan_saved_entity_cleanup_removes_missing(pg_user):
    insert_saved(pg_user, "missing")
    cleanup_orphan_entity_refs()
    assert not saved_exists(pg_user, "missing")
```

**Effort:** M

### [P2] Finding-034: PostgreSQL pooling is opt-in/off, causing connection churn under load

**Chiều:** Performance / Deployment  
**File:** `agent/database.py:100`, `agent/database.py:110`, `agent/database.py:135`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-400

**Mô tả:** The pool is disabled unless `PG_USE_POOL=true`; otherwise every DB operation opens a new psycopg2 connection. The comment explains a prior pool startup hang, but direct connections can exhaust Postgres under bursts.

**Exploit scenario:**
1. Many concurrent public/API requests arrive.
2. Each creates new database connections.
3. Postgres hits connection churn or max-connection pressure.

**Root cause:** Reliability workaround became the default performance posture.

**Fix:**
```python
PG_USE_POOL=true
PG_POOL_MAX=5
# plus startup smoke test that falls back if pool creation exceeds 5s
```

**Test:**
```python
def test_pool_enabled_uses_bounded_pool(monkeypatch):
    monkeypatch.setenv("PG_USE_POOL", "true")
    assert db._get_pg_pool() is not None
```

**Effort:** M

### [P2] Finding-035: Comment pagination can drop replies when parent is outside the current page

**Chiều:** Edge Cases / API Contract  
**File:** `agent/social.py:1071`, `agent/social.py:1088`, `agent/social.py:1101`  
**OWASP:** N/A  
**CWE:** CWE-840

**Mô tả:** `get_comments` fetches a flat page of comments, then nests replies only if parent and child appear in that page. Replies whose parent is outside the page are neither top-level nor attached.

**Exploit scenario:**
1. A post has more than 100 comments.
2. A reply is returned without its parent in the page.
3. UI silently drops or misplaces the reply.

**Root cause:** Pagination is applied before thread assembly.

**Fix:**
```python
# Page top-level comments first, then fetch replies for those parent ids.
top = SELECT ... WHERE parent_id IS NULL LIMIT ? OFFSET ?
replies = SELECT ... WHERE parent_id = ANY(top_ids)
```

**Test:**
```python
def test_comment_pagination_keeps_replies_with_parent(client, seeded_thread):
    data = client.get(f"/api/posts/{seeded_thread.post}/comments?limit=10").json()
    assert all("replies" in c for c in data["comments"])
```

**Effort:** M

### [P2] Finding-036: Planner picker nests a real button inside a `role="button"` row

**Chiều:** Accessibility / WCAG 2.2 AA  
**File:** `web-nuxt/pages/tao-lich-trinh.vue:56`, `web-nuxt/pages/tao-lich-trinh.vue:71`  
**OWASP:** N/A  
**CWE:** CWE-1021

**Mô tả:** The picker item is a focusable `div role="button"` and contains a nested `<button>`. Nested interactive controls confuse keyboard focus and screen-reader activation.

**Exploit scenario:**
1. Keyboard user tabs to the row or inner plus button.
2. Enter/Space activation target is ambiguous.
3. User adds the wrong item or cannot predict focus.

**Root cause:** Row-level click target and explicit button are implemented together.

**Fix:**
```vue
<button type="button" class="picker-item" @click="addStop(e)">
  <span class="picker-emoji" aria-hidden="true">{{ getTypeMeta(e.type).emoji }}</span>
  <span class="picker-info">...</span>
  <span class="btn btn-sm btn-ghost" aria-hidden="true">+</span>
</button>
```

**Test:**
```ts
test('planner picker has no nested interactive controls', async () => {
  const rows = screen.getAllByRole('button', { name: /thêm/i })
  expect(rows.every(row => row.querySelector('button') === null)).toBe(true)
})
```

**Effort:** S

### [P2] Finding-037: Search autocomplete options contain nested remove buttons

**Chiều:** Accessibility / WCAG 2.2 AA  
**File:** `web-nuxt/components/SearchAutocomplete.vue:49`, `web-nuxt/components/SearchAutocomplete.vue:61`  
**OWASP:** N/A  
**CWE:** CWE-1021

**Mô tả:** Recent-search option rows use `role="option"` and include a nested remove button. In ARIA listbox patterns, options should not contain independent interactive descendants.

**Exploit scenario:**
1. Screen reader enters the combobox listbox.
2. A row is announced as an option while also containing a button.
3. Remove action may be unreachable or mis-announced.

**Root cause:** Recent-item selection and deletion are combined in the same ARIA option.

**Fix:**
```vue
<div role="option" @mousedown.prevent="useRecent(term)">...</div>
<button type="button" aria-label="Xóa tìm kiếm gần đây ..." @mousedown.stop.prevent="removeRecent(i)" />
```

**Test:**
```ts
test('listbox options do not contain buttons', () => {
  for (const opt of screen.getAllByRole('option')) expect(opt.querySelector('button')).toBeNull()
})
```

**Effort:** S

### [P2] Finding-038: ModalBase can reference a missing accessible title

**Chiều:** Accessibility / WCAG 2.2 AA  
**File:** `web-nuxt/components/ModalBase.vue:9`, `web-nuxt/components/ModalBase.vue:36`  
**OWASP:** N/A  
**CWE:** CWE-1021

**Mô tả:** `ModalBase` defaults `aria-labelledby="modal-title"` even when slot content may not provide that element. A dialog with a dangling label reference has a weak accessible name.

**Exploit scenario:**
1. Developer opens a modal without a header id of `modal-title`.
2. Screen reader announces an unnamed dialog.
3. User loses context.

**Root cause:** The base component assumes a slot implementation detail.

**Fix:**
```vue
<div role="dialog" aria-modal="true" :aria-labelledby="titleId || undefined" :aria-label="titleId ? undefined : fallbackLabel">
```

**Test:**
```ts
test('modal has an accessible name', () => {
  expect(screen.getByRole('dialog')).toHaveAccessibleName()
})
```

**Effort:** S

### [P2] Finding-039: `npm audit` reports a low esbuild advisory

**Chiều:** Code Quality / Dependency Audit  
**File:** `web-nuxt/package-lock.json`  
**OWASP:** A06:2021 Vulnerable and Outdated Components  
**CWE:** CWE-1104

**Mô tả:** `npm audit --omit=dev --json` reports `esbuild` advisory `GHSA-g7r4-m6w7-qqqr`, severity low, range `>=0.27.3 <0.28.1`, fix available. The advisory is Windows dev-server arbitrary file read; production impact is low but fixable.

**Exploit scenario:**
1. Developer runs affected dev server on Windows.
2. A local-network attacker can hit the dev server.
3. Arbitrary file read may occur under advisory conditions.

**Root cause:** Transitive dependency version is in the affected range.

**Fix:**
```powershell
cd web-nuxt
npm update esbuild
npm audit --omit=dev
```

**Test:**
```python
def test_npm_audit_clean():
    result = subprocess.run(["npm", "audit", "--omit=dev", "--json"], cwd="web-nuxt", text=True, capture_output=True)
    assert '"total": 0' in result.stdout
```

**Effort:** S

### [P3] Finding-040: Large route modules concentrate unrelated responsibilities

**Chiều:** Code Quality / Architecture  
**File:** `agent/server.py:1`, `agent/admin.py:1`, `agent/social.py:1`, `agent/database.py:1`  
**OWASP:** N/A  
**CWE:** CWE-1059

**Mô tả:** Current line counts are large: `server.py` 3157, `admin.py` 1751, `social.py` 1588, `database.py` 1304. These files mix routing, policy, data access, background/system features, and formatting.

**Exploit scenario:**
1. Developer changes one endpoint in a high-churn module.
2. Review misses a side effect in shared helpers.
3. Regression lands in unrelated behavior.

**Root cause:** Module boundaries are too broad for the number of endpoints and policies.

**Fix:**
```text
agent/routes/system.py
agent/routes/chat.py
agent/routes/social/posts.py
agent/routes/social/comments.py
agent/repositories/entities.py
```

**Test:**
```python
def test_route_modules_import_without_server_side_effects():
    import agent.routes.system
```

**Effort:** L

### [P3] Finding-041: Current tests include loose status-code assertions and environment skips

**Chiều:** Code Quality / Test Quality  
**File:** `agent/tests/test_writepaths_ugc.py:80`, `tests/test_integration.py:383`, `agent/tests/test_admin.py:24`  
**OWASP:** N/A  
**CWE:** CWE-665

**Mô tả:** The suite is large, but some tests accept broad outcomes such as `(401, 403)` or `(200, 422)`, and some skip when imports are unavailable. These are useful smoke tests but weak as release gates.

**Exploit scenario:**
1. Endpoint changes from 401 to 403 or even masks a validation issue.
2. Test still passes because it allows multiple unrelated outcomes.
3. Client contract drift is missed.

**Root cause:** Some tests are defensive around environment variance instead of pinning contracts.

**Fix:**
```python
assert response.status_code == 401
assert response.json()["error"]["code"] == "auth_required"
```

**Test:**
```python
def test_no_broad_status_assertions():
    assert not rg("status_code in \\(", "tests", "agent/tests")
```

**Effort:** M

### [P3] Finding-042: Pytest collection shows a Starlette TestClient deprecation warning

**Chiều:** Code Quality / Dependency Audit  
**File:** `pytest output`, `fastapi.testclient` import path  
**OWASP:** N/A  
**CWE:** CWE-1104

**Mô tả:** `python -m pytest --collect-only -q` collected `3050/3118` tests and emitted a `StarletteDeprecationWarning` about `httpx` with `starlette.testclient`. This is not a failing bug today, but it predicts future dependency friction.

**Exploit scenario:**
1. Dependencies are upgraded.
2. Deprecated test client behavior is removed.
3. Security regression suite cannot run during an emergency patch.

**Root cause:** Test infrastructure depends on a deprecated compatibility path.

**Fix:**
```python
# Upgrade test harness to the recommended Starlette/httpx2 path once FastAPI supports it in this repo.
```

**Test:**
```python
def test_pytest_has_no_deprecation_warnings(pytester):
    result = pytester.runpytest("--collect-only", "-W", "error::DeprecationWarning")
    result.assert_outcomes()
```

**Effort:** M

### [P3] Finding-043: Frontend route/page files are large enough to slow a11y and state reviews

**Chiều:** Code Quality / Accessibility  
**File:** `web-nuxt/pages/index.vue:1`, `web-nuxt/pages/cong-dong.vue:1`, `web-nuxt/pages/dia-diem/[id].vue:1`  
**OWASP:** N/A  
**CWE:** CWE-1059

**Mô tả:** Current page sizes include `index.vue` 1113 lines, `cong-dong.vue` 1277 lines, and `dia-diem/[id].vue` 1017 lines. Large pages mix data fetching, state, layout, and interaction logic.

**Exploit scenario:**
1. A small UI change affects keyboard/focus behavior elsewhere in the same page.
2. Reviewer cannot isolate the affected interaction.
3. A11y regression ships.

**Root cause:** Page components own too much state and markup.

**Fix:**
```text
Extract page sections into focused components:
- HomeHeroSearch.vue
- CommunityComposer.vue
- EntityDetailGallerySection.vue
```

**Test:**
```ts
test('community composer can be mounted independently', () => {
  mount(CommunityComposer)
})
```

**Effort:** L
