# AdminCP Polish Batch — Implementation Plan
> STATUS (2026-07-10): done — plan đã thực thi & ship.


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Close the 6 genuine polish gaps found in the AdminCP 5-wave audit — where the shipped implementation deviates from the plan's intent. All frontend-only.

**Architecture:** Three grouped FE tasks (by file, to minimize commits against churn-heavy files) + final verification. No backend changes, no new dependencies.

**Tech Stack:** Nuxt 4 SSR / Vue 3 `<script setup lang="ts">`, CSS design tokens.

## Global Constraints

- **FE-only.** No `agent/*.py` changes, no migrations, no new npm deps.
- **CSS tokens:** `--ink`, `--muted`, `--primary`, `--success`, `--warning`, `--error`, `--line`, `--surface`, `--space-N`, `--text-*`, `--radius-*`, `--weight-*`. RGB channels `--primary-rgb`/`--success-rgb` for `rgba()`.
- **Auth/fetch:** admin pages use `$fetch('/admin-api/...', ...)` (proxied to `/admin/...`) — follow each file's existing pattern exactly. Do NOT change how data is fetched, only how it's rendered/edited.
- **XSS:** the only `v-html` introduced (B2e markdown preview) MUST HTML-escape the input FIRST, then apply a whitelist of safe transforms. No raw user/admin HTML may pass through.
- **Parallel-session churn:** `admin/entities.vue`, `admin/index.vue`, and other admin files may carry uncommitted work from concurrent sessions. Stage ONLY your hunks (`git add -p` / extraction); verify `git diff --cached` before committing; disclose any non-separable mixing.
- **Verify:** `cd web-nuxt && npm run build` must pass after each task.
- **No test file** (these are visual FE tweaks) — verification is build + the final task's checks. Do NOT add vitest specs unless trivial.

---

### Task 1: Dashboard polish — B1c (human-readable activity feed) + B1e (stacked completeness bar)

**File:** `web-nuxt/pages/admin/index.vue`

**Audit anchors:**
- B1c: activity rows at `index.vue:183-192` render raw `{{ a.method }}` + `{{ a.path }}` (e.g. "PUT /admin-api/entities/xyz-123") from `/admin-api/audit-log?limit=10` (`index.vue:473`). Gap: not human-readable.
- B1e: completeness bar at `index.vue:168-180` + CSS `:616-617` is a single `--primary` fill driven by `pct`; the 3 sub-metrics (`has_summary`/`has_images`/`has_place`) show as plain text. Gap: not the stacked/segmented bar specified. Data is already in `stats.completeness = {total, has_summary, has_images, has_place, orphans, pct}`.

**B1c fix (FE label mapping):** add a helper that turns an audit row into a Vietnamese action label. Map by method + path prefix. Keep it pure and defensive:

```ts
function activityLabel(a: { method: string; path: string }): string {
  const p = (a.path || '').replace('/admin-api', '').replace('/admin', '')
  const m = (a.method || '').toUpperCase()
  const seg = p.split('?')[0].split('/').filter(Boolean)  // e.g. ['entities','xyz']
  const res = seg[0] || ''
  const NOUN: Record<string, string> = {
    entities: 'địa điểm', relationships: 'quan hệ', moderation: 'kiểm duyệt',
    users: 'người dùng', itineraries: 'lịch trình', media: 'ảnh', settings: 'cài đặt',
    'site-settings': 'cài đặt', backup: 'backup', 'backup-trigger': 'backup',
  }
  const noun = NOUN[res] || res || 'mục'
  const VERB: Record<string, string> = { POST: 'Tạo', PUT: 'Sửa', PATCH: 'Sửa', DELETE: 'Xoá', GET: 'Xem' }
  const verb = VERB[m] || m
  return `${verb} ${noun}`
}
```

Render it as the primary line, keep the raw method+path as a muted secondary (so nothing is lost). Update `index.vue:183-192` roughly to:

```html
<div v-for="(a, i) in activity" :key="i" class="activity-row">
  <span class="activity-label">{{ activityLabel(a) }}</span>
  <span class="activity-meta">{{ a.method }} · {{ timeAgoOrRaw(a) }}</span>
</div>
```

(Reuse the existing time formatting in the file; keep `a.method` for context. Confirm the existing loop variable/field names — adapt to them, don't invent.)

**B1e fix (stacked bar):** replace the single fill with a segmented bar showing summary/images/place coverage. Each segment width = `count/total*100`. Since these overlap (an entity can have all three), render 3 THIN stacked rows (one per metric) OR a grouped mini-bar — simplest and honest is 3 labeled mini-bars:

```html
<div class="dash-comp">
  <div class="dash-comp-head"><strong>{{ stats.completeness.pct }}%</strong> hoàn thiện</div>
  <div v-for="seg in completenessSegments" :key="seg.key" class="dash-comp-seg">
    <span class="dcs-label">{{ seg.label }}</span>
    <div class="dcs-bar"><div class="dcs-fill" :style="{ width: seg.pct + '%', background: seg.color }" /></div>
    <span class="dcs-val">{{ seg.count }}/{{ stats.completeness.total }}</span>
  </div>
</div>
```

```ts
const completenessSegments = computed(() => {
  const c = stats.value?.completeness
  if (!c || !c.total) return []
  const pct = (n: number) => Math.round((n / c.total) * 100)
  return [
    { key: 'summary', label: 'Tóm tắt', count: c.has_summary, pct: pct(c.has_summary), color: 'var(--primary)' },
    { key: 'images',  label: 'Ảnh',     count: c.has_images,  pct: pct(c.has_images),  color: 'var(--success)' },
    { key: 'place',   label: 'Phường-xã', count: c.has_place,  pct: pct(c.has_place),   color: 'var(--warning)' },
  ]
})
```

CSS (append near the existing `.dash-comp*` rules):

```css
.dash-comp-seg { display: grid; grid-template-columns: 72px 1fr 56px; align-items: center; gap: var(--space-2); margin-top: var(--space-1); }
.dcs-label { font-size: var(--text-xs); color: var(--muted); }
.dcs-bar { height: 8px; background: var(--line); border-radius: var(--radius-full); overflow: hidden; }
.dcs-fill { height: 100%; border-radius: var(--radius-full); transition: width .4s var(--ease-out, ease); }
.dcs-val { font-size: var(--text-2xs); color: var(--muted); text-align: right; }
```

Remove/replace the old single `.dash-comp-fill` block. Confirm the exact existing markup before editing.

- [ ] **Step 1:** Read `index.vue` around lines 168-192 + the `activity`/`stats` refs + CSS; confirm exact field names.
- [ ] **Step 2:** Add `activityLabel()` + render enriched activity rows (keep raw as muted secondary).
- [ ] **Step 3:** Add `completenessSegments` + the segmented-bar template + CSS; remove the old single-fill bar.
- [ ] **Step 4:** `cd C:/Code/vinhlong360/web-nuxt && npm run build` → passes.
- [ ] **Step 5:** Stage only your hunks; `git commit -m "fix(admin): dashboard polish — human-readable activity feed + stacked completeness bar"`

---

### Task 2: Entity editor polish — B2a (inline placeId) + B2b (history old→new) + B2e (markdown-lite preview)

**File:** `web-nuxt/pages/admin/entities.vue`

**Audit anchors:**
- B2a: inline edit via `startInline`/`saveInline` (`:754-799`) covers name (`:139`), type (`:148`), and `attr:*` (`:156-171`) — but NOT `placeId`. The full edit modal has `form.placeId` (`:243`). The `PUT /entities/{id}` backend already accepts placeId (it's a core field). Fix: add a placeId column cell with `@dblclick="startInline(e, 'placeId', e.placeId)"` and ensure `saveInline` sends it (it likely already sends `{ [field]: value }` generically — confirm).
- B2b: history at `:392-400` + `fetchEntityHistory()` (`:993`); interface `EntityHistoryRecord` (`:449-454`) declares only `field`/`new_value`/`created_at`. Backend `get_entity_history` (database.py:1521) RETURNS `old_value` too. Fix: add `old_value` to the interface + render "old → new".
- B2e: summary editor at `:249-252` — char counter DONE; `previewSummary` toggle exists but uses `v-text` (plain text, no markdown). Fix: render a MINIMAL, XSS-safe markdown preview.

**B2a:** add a placeId column to the table (near name/type). Confirm `saveInline` already PUTs `{ [inlineEdit.field]: inlineEdit.value }` generically; if it whitelists fields, add `placeId`. Cell:

```html
<td @dblclick="startInline(e, 'placeId', e.placeId)">
  <template v-if="inlineEdit.id === e.id && inlineEdit.field === 'placeId'">
    <input v-model="inlineEdit.value" class="inline-input" @keyup.enter="saveInline" @blur="saveInline" @keyup.esc="cancelInline" />
  </template>
  <span v-else class="inline-cell">{{ e.placeId || '—' }}</span>
</td>
```

(Match the EXACT markup of the existing name/type inline cells — copy their structure, only change the field. Add a matching `<th>` header. If there's a column-visibility system, register placeId there.)

**B2b:** extend the interface + render old→new:

```ts
interface EntityHistoryRecord { field: string; old_value?: string | null; new_value?: string | null; created_at: string; actor?: string }
```

```html
<div v-for="(h, i) in entityHistory" :key="i" class="ent-hist-row">
  <span class="ehr-field">{{ h.field }}</span>
  <span class="ehr-diff"><del v-if="h.old_value">{{ h.old_value }}</del> <ins>{{ h.new_value }}</ins></span>
  <span class="ehr-time">{{ timeAgo(h.created_at) }}</span>
</div>
```

(Confirm `fetchEntityHistory` maps the response fields — ensure `old_value` is carried through, not dropped. Reuse the file's time helper.) CSS: `del { color: var(--error); text-decoration: line-through; } ins { color: var(--success); text-decoration: none; }`.

**B2e (safe markdown-lite):** replace the `v-text` preview with an escaped-then-transformed render. Support only: `**bold**`, `*italic*`, and line breaks. Escape HTML first so nothing raw passes:

```ts
function mdLite(src: string): string {
  const esc = (src || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
  return esc
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>')
    .replace(/\n/g, '<br>')
}
```

```html
<div v-if="previewSummary" class="ent-summary-preview" v-html="mdLite(form.summary)" />
<textarea v-else v-model="form.summary" ... />
```

(Because `mdLite` escapes first and only injects a fixed whitelist of tags, `v-html` here is XSS-safe. Note this in the report.)

- [ ] **Step 1:** Read entities.vue: the inline-edit cells (name/type), `saveInline`, `EntityHistoryRecord` + `fetchEntityHistory`, the summary preview block. Confirm `saveInline` sends the field generically and the PUT accepts placeId.
- [ ] **Step 2:** B2a — add placeId inline column (+ header, + column-visibility registration if present).
- [ ] **Step 3:** B2b — add `old_value` to the interface + render old→new diff; ensure the fetch carries `old_value`.
- [ ] **Step 4:** B2e — add `mdLite()` + escaped `v-html` preview.
- [ ] **Step 5:** `npm run build` → passes.
- [ ] **Step 6:** Stage only your hunks; `git commit -m "fix(admin): entity editor polish — inline placeId + history old→new diff + markdown-lite preview"`

---

### Task 3: Admin prefs wiring — B8b (pageSize + entityTypeFilter persistence)

**Files:** `web-nuxt/composables/useAdminPrefs.ts` (already has the interface), `web-nuxt/pages/admin/entities.vue`

**Audit anchor:** `useAdminPrefs.ts:3-7` declares `sidebarCollapsed`, `pageSize`, `entityTypeFilter`; only `sidebarCollapsed` is wired (layouts/admin.vue). `pageSize`/`entityTypeFilter` are declared-but-dead. entities.vue has its own pagination/type-filter state not reading from prefs.

**Fix:** in `entities.vue`, initialize the page-size and type-filter refs from `useAdminPrefs`, and persist changes via `setPref`. Read the existing pagination + type-filter state first (do NOT introduce a second source of truth — wire the EXISTING refs to prefs).

```ts
const { prefs, setPref } = useAdminPrefs()
// on setup, seed existing refs from persisted prefs (guard for undefined):
if (prefs.value.pageSize) pageSize.value = prefs.value.pageSize          // adapt to the real ref name
if (prefs.value.entityTypeFilter) typeFilter.value = prefs.value.entityTypeFilter
// persist on change:
watch(pageSize, v => setPref('pageSize', v))
watch(typeFilter, v => setPref('entityTypeFilter', v))
```

(Confirm the ACTUAL ref names for page size + type filter in entities.vue — the audit said "its own pagination/filter state." Wire those. If entities.vue uses `usePagination`, seed its pageSize option from prefs. Keep the change minimal — no behavior change other than persistence.)

- [ ] **Step 1:** Read `useAdminPrefs.ts` + entities.vue's pagination/type-filter refs; identify the exact ref names.
- [ ] **Step 2:** Seed the refs from `prefs` on setup + `watch`→`setPref` to persist. Guard against undefined.
- [ ] **Step 3:** `npm run build` → passes.
- [ ] **Step 4:** Manually reason: change page size / type filter → reload → persists. (No test needed.)
- [ ] **Step 5:** Stage only your hunks; `git commit -m "fix(admin): persist entities pageSize + type filter via useAdminPrefs (B8b)"`

---

### Task 4: Final Verification

- [ ] **Step 1:** `cd web-nuxt && npm run build` → passes.
- [ ] **Step 2:** `npm run typecheck` → no NEW errors in `admin/index.vue`, `admin/entities.vue`, `composables/useAdminPrefs.ts` (pre-existing errors elsewhere OK).
- [ ] **Step 3:** Confirm all 6 gaps addressed: B1c (activityLabel), B1e (completenessSegments), B2a (placeId inline cell), B2b (old_value rendered), B2e (mdLite), B8b (pageSize/entityTypeFilter watched→setPref).
- [ ] **Step 4:** Mark complete.

---

## Notes for the Executor

- All FE-only; no backend/migration/dep changes. If any task seems to need a backend change, STOP and report — the audit confirmed the backends already return what's needed (activity-feed raw data → enrich in FE; history already returns `old_value`; placeId is a core PUT field).
- Trivial/naming gaps deliberately EXCLUDED (B1d compare_days, B5b MB-trigger, B5c endpoint name, B3c legend, B2c Levenshtein) — do not implement them.
- Heavy parallel-session churn on admin files: stage only your hunks, verify `git diff --cached`, disclose any non-separable mixing.
- The `v-html` in B2e is the only one; it must escape-first. Flag it explicitly in the report for the reviewer.
