# Adaptive Nocturne Public Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> STATUS: proposed - implementation plan waiting for user execution choice

**Goal:** Triển khai Adaptive Nocturne Public Upgrade theo lát dọc có thể kiểm thử, rollback và đo lường, bắt đầu từ foundation → homepage/catalog → search/map → detail → planner → adaptive intelligence.

**Architecture:** Giữ route/API/auth/RBAC hiện có, bổ sung các contract public dùng chung cho surface state, context, trust, freshness và continuity. Mỗi page family dùng composition riêng nhưng nhận token và primitive chung; intelligence chỉ thay đổi priority trong giới hạn, có giải thích, undo và deterministic fallback.

**Tech Stack:** Nuxt 4.4.8, Vue 3.5.35, TypeScript 6.0.3, Vitest 4.1.9, `@nuxt/test-utils`, MapLibre GL 5.24.0, CSS variables hiện có trong `web-nuxt/assets/css`.

## Global Constraints

- Giữ `Adaptive Nocturne System`, Mekong Ink & Clay, Controlled Serif, Framed Dossier và Existing Stitch Screen Evolution theo design authority.
- Nocturne là mặc định; Daylight Parchment chỉ là accessibility/material variant và không tự đổi theo giờ.
- Không thay đổi route, API, auth, RBAC, SEO, data ownership hoặc mô hình không-booking/ordering/payment nếu chưa có spec riêng.
- Không lưu hoặc lộ raw GPS/IP; location phải là exact, approximate, selected hoặc unavailable với confidence và TTL.
- Component mới chỉ dùng semantic/component tokens; không dùng raw color, radius, shadow hoặc gradient tùy ý.
- Mỗi viewport chỉ có một primary action; action chính hit area tối thiểu 44×44px, có focus/loading/disabled state.
- Không dùng emoji làm structural icon, status, navigation, CTA hoặc empty state.
- Body contrast mục tiêu 7:1; UI tối thiểu 3:1; kiểm tra Nocturne/Parchment, forced colors, reduced motion và text zoom 200%.
- Map/media/intelligence lỗi không được làm mất content/task còn sử dụng được.
- Giữ nguyên mọi thay đổi dirty worktree không do plan tạo ra, đặc biệt `docs/standards/scorecard-history.jsonl`.
- Mỗi task phải có behavior test, visual/performance gate phù hợp và một commit nhỏ có rollback rõ.

---

## Task 1: Shared public state và context contracts

**Files:**
- Create: `web-nuxt/types/publicExperience.ts`
- Create: `web-nuxt/composables/useSurfaceState.ts`
- Create: `web-nuxt/composables/usePublicContextEnvelope.ts`
- Create: `web-nuxt/utils/publicStateUrl.ts`
- Test: `web-nuxt/tests/public-surface-state.test.ts`
- Test: `web-nuxt/tests/public-context-envelope.test.ts`
- Test: `web-nuxt/tests/public-state-url.test.ts`

**Interfaces:**
- Consumes: existing `AreaRef`/area metadata from `web-nuxt/composables/useConstants.ts`, preference readers from `useRegionPref.ts` and `usePersonalizationPreferences.ts`.
- Produces: `SurfaceState<T>`, `ContextEnvelope`, `SearchViewState`, `serializeSearchViewState()`, `parseSearchViewState()`, `useSurfaceState()` and `usePublicContextEnvelope()`.

- [ ] **Step 1: Write failing contract tests**

```ts
it('keeps partial data when one panel fails', () => {
  const state = surfaceState({ data: { facts: true }, failedPanels: ['media'] })
  expect(state.value.kind).toBe('partial')
  expect(state.value.failedPanels).toEqual(['media'])
})

it('never serializes raw location coordinates', () => {
  const encoded = serializeSearchViewState({
    query: 'gốm', intent: 'place', filters: {},
    area: { id: 'vinh-long' },
    viewport: { center: [10.2, 105.9], zoom: 12 }, panel: 'list',
  })
  expect(encoded).not.toContain('10.2')
  expect(encoded).toContain('area=vinh-long')
})
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `npm --prefix web-nuxt test -- public-surface-state.test.ts public-context-envelope.test.ts public-state-url.test.ts`

Expected: FAIL because the new types/composables and serializers do not exist.

- [ ] **Step 3: Implement the smallest typed contracts**

Implement `SurfaceState<T>` transitions with explicit `loading`, `ready`, `partial`, `stale`, `empty`, `error` and `offline` constructors. `usePublicContextEnvelope()` must default to `location.mode = 'unavailable'`, use the persisted region preference only as `selected`, and expose `explainableSignals` without raw coordinates.

Implement URL parsing with a whitelist of query/intent/filter/area/viewport keys, bounded string lengths and deterministic defaults. Reject malformed values instead of throwing during SSR.

- [ ] **Step 4: Run focused tests and typecheck**

Run: `npm --prefix web-nuxt test -- public-surface-state.test.ts public-context-envelope.test.ts public-state-url.test.ts` and `npm --prefix web-nuxt run typecheck`

Expected: all focused tests pass and typecheck exits 0.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/types/publicExperience.ts web-nuxt/composables/useSurfaceState.ts web-nuxt/composables/usePublicContextEnvelope.ts web-nuxt/utils/publicStateUrl.ts web-nuxt/tests/public-surface-state.test.ts web-nuxt/tests/public-context-envelope.test.ts web-nuxt/tests/public-state-url.test.ts
git commit -m "feat: add public experience state contracts"
```

## Task 2: Token/theme foundation và public shell

**Files:**
- Modify: `web-nuxt/assets/css/variables.css`
- Modify: `web-nuxt/assets/css/shell.css`
- Modify: `web-nuxt/assets/css/base.css`
- Modify: `web-nuxt/layouts/default.vue`
- Modify: `web-nuxt/components/shell/PublicContextBar.vue`
- Modify: `web-nuxt/components/shell/PublicBottomNav.vue`
- Modify: `web-nuxt/components/shell/ThemeModeControl.vue`
- Test: `web-nuxt/tests/nocturne-theme-contract.test.ts`
- Test: `web-nuxt/tests/theme-mode-control.test.ts`
- Test: `web-nuxt/tests/ui-foundation-shell.test.ts`

**Interfaces:**
- Consumes: `ContextEnvelope` from Task 1 and current auth/navigation contracts in `layouts/default.vue`.
- Produces: stable `NocturneShell` DOM anatomy, semantic `data-theme` behavior, five-item mobile navigation and context control that can be reused by every public page.

- [ ] **Step 1: Extend failing shell/theme tests**

Add assertions for:

```ts
expect(wrapper.get('[data-public-shell]').exists()).toBe(true)
expect(wrapper.findAll('[data-mobile-nav-item]')).toHaveLength(5)
expect(document.documentElement.dataset.theme).toBe('nocturne')
await wrapper.get('button[aria-label="Nền sáng dễ đọc"]').trigger('click')
expect(document.documentElement.dataset.theme).toBe('parchment')
```

Also assert that context changes preserve the current route and do not expose coordinates in rendered HTML.

- [ ] **Step 2: Run the shell tests to verify the new assertions fail**

Run: `npm --prefix web-nuxt test -- nocturne-theme-contract.test.ts theme-mode-control.test.ts ui-foundation-shell.test.ts`

Expected: FAIL on the new data attributes/theme contract before implementation.

- [ ] **Step 3: Implement token and shell changes**

Add semantic variables for canvas/surface/text/border/action/focus/source/status in both Nocturne and Parchment branches. Keep existing legacy variables as aliases until all pilot CSS is migrated. In `default.vue`, preserve auth and navigation behavior while exposing stable shell markers, context line and primary task nav. Keep mobile bottom nav at five destinations and add safe-area padding to the shell dock.

Remove only shell-level decorative gradients/lifts that violate the authority; do not perform broad CSS rewrites in unrelated page families.

- [ ] **Step 4: Run tests and responsive checks**

Run: `npm --prefix web-nuxt test -- nocturne-theme-contract.test.ts theme-mode-control.test.ts ui-foundation-shell.test.ts` and `npm --prefix web-nuxt run typecheck`.

Manual browser checks: 390×844, 768×1024 and 1440×900; verify no nav overlap, focus restoration after Escape and 200% zoom.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/assets/css/variables.css web-nuxt/assets/css/shell.css web-nuxt/assets/css/base.css web-nuxt/layouts/default.vue web-nuxt/components/shell/PublicContextBar.vue web-nuxt/components/shell/PublicBottomNav.vue web-nuxt/components/shell/ThemeModeControl.vue web-nuxt/tests/nocturne-theme-contract.test.ts web-nuxt/tests/theme-mode-control.test.ts web-nuxt/tests/ui-foundation-shell.test.ts
git commit -m "feat: establish adaptive nocturne public shell"
```

## Task 3: Shared trust, freshness và page-state primitives

**Files:**
- Create: `web-nuxt/components/public/PageState.vue`
- Create: `web-nuxt/components/public/WhyThisControl.vue`
- Create: `web-nuxt/components/public/ActionDock.vue`
- Modify: `web-nuxt/components/SourceMark.vue`
- Modify: `web-nuxt/components/FreshnessLine.vue`
- Modify: `web-nuxt/components/FramedDossier.vue`
- Modify: `web-nuxt/components/DossierLineItem.vue`
- Modify: `web-nuxt/assets/css/dossier.css`
- Modify: `web-nuxt/assets/css/components.css`
- Test: `web-nuxt/tests/source-freshness-mark.test.ts`
- Test: `web-nuxt/tests/framed-dossier.test.ts`
- Create: `web-nuxt/tests/public-page-state.test.ts`

**Interfaces:**
- Consumes: `SurfaceState<T>` and trust metadata from Task 1.
- Produces: `PageState` props `{ state, title, retry, recovery }`, `ActionDock` with one primary slot, `WhyThisControl` with `reason`, `signals` and `onReset`, and stable `data-source-mark`, `data-freshness-line` and `data-page-state` markers.

- [ ] **Step 1: Add failing tests for every state and trust channel**

```ts
it('renders stale label and update time without pretending to be an error', async () => {
  const wrapper = await mountSuspended(PageState, { props: { state: { kind: 'stale', data: {}, updatedAt: '2026-08-01' } } })
  expect(wrapper.get('[data-page-state="stale"]').text()).toContain('Có thể đã cũ')
  expect(wrapper.get('[data-page-state="stale"]').attributes('role')).not.toBe('alert')
})
```

Test that official/verified/community/unknown always render icon plus visible label, and that an `ActionDock` cannot render two primary actions.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `npm --prefix web-nuxt test -- public-page-state.test.ts source-freshness-mark.test.ts framed-dossier.test.ts`

Expected: FAIL for the new page-state and action-dock contracts.

- [ ] **Step 3: Implement primitives without changing existing caller semantics**

Keep `SourceMark` and `FreshnessLine` backward-compatible. Add explicit stale/unknown/conflict copy, icon and accessible labels. Implement `PageState` so partial state renders available slot content and a local retry per failed panel. Use opaque dossier surfaces, no generic hover lift and no content glass.

- [ ] **Step 4: Run focused tests and a11y assertions**

Run: `npm --prefix web-nuxt test -- public-page-state.test.ts source-freshness-mark.test.ts framed-dossier.test.ts`.

Expected: PASS, with no unlabeled icon-only buttons and no duplicated primary action.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/public web-nuxt/components/SourceMark.vue web-nuxt/components/FreshnessLine.vue web-nuxt/components/FramedDossier.vue web-nuxt/components/DossierLineItem.vue web-nuxt/assets/css/dossier.css web-nuxt/assets/css/components.css web-nuxt/tests/public-page-state.test.ts web-nuxt/tests/source-freshness-mark.test.ts web-nuxt/tests/framed-dossier.test.ts
git commit -m "feat: add shared public trust and state primitives"
```

## Task 4: Homepage và catalog vertical slice

**Files:**
- Modify: `web-nuxt/pages/index.vue`
- Modify: `web-nuxt/pages/du-lich.vue`
- Modify: `web-nuxt/components/home/HomeLocalBriefing.vue`
- Modify: `web-nuxt/components/home/HomeDecisionLedger.vue`
- Modify: `web-nuxt/components/home/HomeFeatureDossier.vue`
- Modify: `web-nuxt/components/home/HomeCategoryIndex.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Modify: `web-nuxt/assets/css/catalog.css`
- Test: `web-nuxt/tests/home-nocturne-page.test.ts`
- Test: `web-nuxt/tests/home-nocturne-components.test.ts`
- Test: `web-nuxt/tests/home-nocturne-presentation.test.ts`
- Create: `web-nuxt/tests/public-discovery-composition.test.ts`

**Interfaces:**
- Consumes: shell and public primitives from Tasks 1-3; existing `homePresentation` and public API responses.
- Produces: homepage composition `context → editorial lead → quick decisions → signals → journey continuation` and catalog composition `orientation → filter/decision → result → evidence → continuation`.

- [ ] **Step 1: Write failing composition tests**

Assert that homepage renders at most one media-led feature, quick decisions link to real routes, signals include source/freshness and degraded data does not render fake metrics. Assert catalog renders filters before results and uses an `EntityRow`/`EntityTile` contract instead of a repeated generic grid for all result kinds.

- [ ] **Step 2: Run homepage/catalog tests to verify failure**

Run: `npm --prefix web-nuxt test -- home-nocturne-page.test.ts home-nocturne-components.test.ts home-nocturne-presentation.test.ts public-discovery-composition.test.ts`

Expected: new composition assertions fail against legacy ordering or missing markers.

- [ ] **Step 3: Refactor template ordering and responsive composition**

Preserve existing API/composable data mapping. Reorder only public sections to the approved anatomy, keep `ClientOnly` around volatile personalized/community blocks to avoid hydration mismatch, and replace repeated feature/card sections with existing dossier/row components where data shape permits. Add explicit `data-home-section`/`data-catalog-section` markers for visual QA.

- [ ] **Step 4: Implement responsive and state styling**

Use container-aware layout rules in `home-nocturne.css` and `catalog.css`; mobile must put context and action before media. Remove decorative gradients/lifts only in touched selectors. Keep image dimensions/aspect ratios to protect CLS and preserve AI/media disclosure.

- [ ] **Step 5: Run tests, typecheck and visual baseline**

Run the focused tests, `npm --prefix web-nuxt run typecheck`, then capture 390×844 and 1440×900 screenshots for homepage/catalog in both themes. Review overflow, focus, Vietnamese typography, source disclosure and first useful action.

- [ ] **Step 6: Commit**

```bash
git add web-nuxt/pages/index.vue web-nuxt/pages/du-lich.vue web-nuxt/components/home web-nuxt/assets/css/home-nocturne.css web-nuxt/assets/css/catalog.css web-nuxt/tests/home-nocturne-page.test.ts web-nuxt/tests/home-nocturne-components.test.ts web-nuxt/tests/home-nocturne-presentation.test.ts web-nuxt/tests/public-discovery-composition.test.ts
git commit -m "feat: compose adaptive public discovery surfaces"
```

## Task 5: Search/map continuity và recovery

**Files:**
- Modify: `web-nuxt/pages/tim-kiem.vue`
- Modify: `web-nuxt/pages/ban-do.vue`
- Modify: `web-nuxt/composables/useUnifiedSearch.ts`
- Modify: `web-nuxt/composables/useFilterUrl.ts`
- Modify: `web-nuxt/composables/useNDAMap.ts`
- Create: `web-nuxt/composables/useSearchViewState.ts`
- Create: `web-nuxt/components/public/MapListSurface.vue`
- Create: `web-nuxt/components/public/MapFallback.vue`
- Modify: `web-nuxt/assets/css/catalog.css`
- Modify: `web-nuxt/assets/css/base.css`
- Test: `web-nuxt/tests/search-tri-region-integration.test.ts`
- Test: `web-nuxt/tests/use-nda-map-lifecycle.test.ts`
- Create: `web-nuxt/tests/search-map-continuity.test.ts`
- Create: `web-nuxt/tests/search-zero-result-recovery.test.ts`

**Interfaces:**
- Consumes: `SearchViewState` and URL serializer from Task 1, `SourceMark`/`PageState` from Task 3.
- Produces: `useSearchViewState()` with `state`, `setQuery`, `setFilter`, `setViewport`, `selectResult`, `openPanel`, `restoreBackStack`; `MapListSurface` props `{ results, selectedId, viewport, mapState }` and emits `select`, `viewport-change`, `search-area`.

- [ ] **Step 1: Write failing URL/list-map tests**

```ts
it('restores query, filters, selected result and scroll key after back navigation', () => {
  const view = useSearchViewState('/tim-kiem?q=gốm&area=vinh-long&intent=place')
  view.selectResult('entity-42')
  expect(view.state.value.query).toBe('gốm')
  expect(view.state.value.selectedId).toBe('entity-42')
})
```

Add tests for marker selection, filter persistence, zero-result recovery and map failure preserving list results.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `npm --prefix web-nuxt test -- search-map-continuity.test.ts search-zero-result-recovery.test.ts search-tri-region-integration.test.ts use-nda-map-lifecycle.test.ts`

Expected: FAIL because the shared view state and map/list contract are not present.

- [ ] **Step 3: Implement shared search view state**

Use the Task 1 serializer whitelist. Debounce viewport updates, require an explicit `Tìm trong khu vực này` action after pan/zoom and keep `selectedId` session-local. Preserve existing API response shapes and search recents.

- [ ] **Step 4: Implement desktop list/map and mobile bottom sheet**

Render `EntityRow` list and map markers from the same result identity. Keyboard focus selects markers without unexpected panning. Add map/list toggle and safe-area bottom sheet. Render `MapFallback` when tile/SDK fails; list and address remain actionable.

- [ ] **Step 5: Implement zero-result recovery**

Expose recovery actions in deterministic order: remove least important filter, widen selected area, correct spelling/synonym, change intent to `all`, then recent/saved. Do not mutate query without user activation.

- [ ] **Step 6: Run tests, typecheck and responsive QA**

Run focused tests and `npm --prefix web-nuxt run typecheck`. Verify 390×844 bottom sheet, 1024 split layout, 1440 list/map, keyboard marker focus, slow network and map unavailable.

- [ ] **Step 7: Commit**

```bash
git add web-nuxt/pages/tim-kiem.vue web-nuxt/pages/ban-do.vue web-nuxt/composables/useUnifiedSearch.ts web-nuxt/composables/useFilterUrl.ts web-nuxt/composables/useNDAMap.ts web-nuxt/composables/useSearchViewState.ts web-nuxt/components/public/MapListSurface.vue web-nuxt/components/public/MapFallback.vue web-nuxt/assets/css/catalog.css web-nuxt/assets/css/base.css web-nuxt/tests/search-map-continuity.test.ts web-nuxt/tests/search-zero-result-recovery.test.ts web-nuxt/tests/search-tri-region-integration.test.ts web-nuxt/tests/use-nda-map-lifecycle.test.ts
git commit -m "feat: unify public search and map continuity"
```

## Task 6: Detail Dossier và false-404 correctness

**Files:**
- Modify: `web-nuxt/pages/dia-diem/[id].vue`
- Modify: `web-nuxt/pages/xa-phuong/[id].vue`
- Modify: `web-nuxt/components/FramedDossier.vue`
- Modify: `web-nuxt/components/EntityTrustPanel.vue`
- Modify: `web-nuxt/components/KnowBeforeYouGo.vue`
- Modify: `web-nuxt/assets/css/detail.css`
- Modify: `web-nuxt/assets/css/detail-shared.css`
- Test: `web-nuxt/tests/detail-grid-containment-gate.test.mjs`
- Test: `web-nuxt/tests/detail-admin-unit-breadcrumb.test.ts`
- Test: `web-nuxt/tests/entity-image-detail.test.ts`
- Create: `web-nuxt/tests/detail-surface-states.test.ts`
- Create: `web-nuxt/tests/detail-false-404.test.ts`

**Interfaces:**
- Consumes: `SurfaceState`, `SourceMark`, `FreshnessLine`, `ActionDock` and `Journey Thread` from earlier tasks.
- Produces: detail loader that maps only confirmed `not_found` to 404; `resolveDetailAction(entity, context)` returning one primary CTA and a stable dossier anatomy.

- [ ] **Step 1: Write failing false-404 and CTA tests**

```ts
it('does not convert a timeout into not-found', async () => {
  const result = resolveDetailFetchError({ statusCode: 504, kind: 'timeout' })
  expect(result).toEqual({ kind: 'error', retryable: true })
})

it('uses directions only when coordinates are valid', () => {
  expect(resolveDetailAction({ coords: [10.2, 105.9], phone: null }, selectedContext).id).toBe('directions')
  expect(resolveDetailAction({ coords: null, phone: '0900' }, selectedContext).id).toBe('call')
})
```

Add tests for partial media, stale facts, source labels, conflict display and mobile action-dock safe area marker.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `npm --prefix web-nuxt test -- detail-false-404.test.ts detail-surface-states.test.ts detail-grid-containment-gate.test.mjs detail-admin-unit-breadcrumb.test.ts entity-image-detail.test.ts`

Expected: FAIL on the new error mapping and action resolution.

- [ ] **Step 3: Separate fetch error classes**

In the detail page, distinguish confirmed API `not_found`, hidden/private, network timeout, 5xx, parse failure and offline cache. Preserve route state for retryable failures; use the existing error boundary/recovery patterns instead of calling `createError({ statusCode: 404 })` for every fetch exception.

- [ ] **Step 4: Compose the dossier**

Use 8/4 desktop columns and mobile identity → trust → action → facts → narrative → related ordering. Render only supplied anatomy, definition-list facts and source/freshness beside time-sensitive claims. Keep existing image disclosure and admin-unit breadcrumb behavior.

- [ ] **Step 5: Run tests, typecheck and visual QA**

Run focused tests and `npm --prefix web-nuxt run typecheck`. Verify 390×844 action dock does not overlap hero/content, 200% zoom, stale/partial states and an API timeout that still allows retry/back navigation.

- [ ] **Step 6: Commit**

```bash
git add web-nuxt/pages/dia-diem/[id].vue web-nuxt/pages/xa-phuong/[id].vue web-nuxt/components/FramedDossier.vue web-nuxt/components/EntityTrustPanel.vue web-nuxt/components/KnowBeforeYouGo.vue web-nuxt/assets/css/detail.css web-nuxt/assets/css/detail-shared.css web-nuxt/tests/detail-surface-states.test.ts web-nuxt/tests/detail-false-404.test.ts web-nuxt/tests/detail-grid-containment-gate.test.mjs web-nuxt/tests/detail-admin-unit-breadcrumb.test.ts web-nuxt/tests/entity-image-detail.test.ts
git commit -m "feat: harden public detail dossiers"
```

## Task 7: Planner timeline, friction và preview optimizer

**Files:**
- Modify: `web-nuxt/pages/tao-lich-trinh.vue`
- Modify: `web-nuxt/composables/useItineraryOptimization.ts`
- Modify: `web-nuxt/composables/useRouting.ts`
- Create: `web-nuxt/components/planner/PlannerSummary.vue`
- Create: `web-nuxt/components/planner/PlannerFrictionNotice.vue`
- Create: `web-nuxt/components/planner/PlannerOptimizationPreview.vue`
- Modify: `web-nuxt/assets/css/base.css`
- Modify: `web-nuxt/assets/css/catalog.css`
- Test: `web-nuxt/tests/itinerary-optimization.test.ts`
- Test: `web-nuxt/tests/itinerary-routing.test.ts`
- Test: `web-nuxt/tests/itinerary-time-schedule.test.ts`
- Create: `web-nuxt/tests/planner-friction.test.ts`
- Create: `web-nuxt/tests/planner-optimization-preview.test.ts`

**Interfaces:**
- Consumes: existing `PlanStop`, `PlannerInputState`, routing helpers and `SurfaceState`.
- Produces: `PlannerSummary` props `{ stopCount, totalDuration, travelDuration, warnings }`, `PlannerFrictionNotice` props `{ code, severity, reason, recovery }`, and `PlannerOptimizationPreview` props `{ before, after, changes, tradeoffs }` with `confirm`/`cancel` events.

- [ ] **Step 1: Write failing planner behavior tests**

```ts
it('does not mutate stops before optimizer confirmation', async () => {
  const preview = await createPlannerOptimizationPreview(initialStops)
  expect(preview.after.map(stop => stop.id)).not.toEqual(initialStops.map(stop => stop.id))
  expect(currentStops.value).toEqual(initialStops)
})
```

Test opening-hour conflict, travel-time over budget, stale stop data, missing coordinates, offline draft and revision conflict.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `npm --prefix web-nuxt test -- planner-friction.test.ts planner-optimization-preview.test.ts itinerary-optimization.test.ts itinerary-routing.test.ts itinerary-time-schedule.test.ts`

Expected: FAIL for preview/no-mutation and friction contract assertions.

- [ ] **Step 3: Extract planner summary/friction/preview components**

Keep route optimization bounded and reuse `mergeOptimizedStops`, `requestOptimizedOrder` and existing U-turn safeguards. Move summary, warnings and preview UI into focused components without changing API payloads.

- [ ] **Step 4: Recompose desktop/mobile planner**

Desktop timeline/map/summary uses 5/4/3 columns; 1024px uses 6/6 with summary drawer; mobile orders budget → warnings → timeline → map sheet → dock. Drag and manual edit remain available offline. Add conflict diff per stop and keep local draft when the server revision changes.

- [ ] **Step 5: Run tests, typecheck and visual QA**

Run focused tests, `npm --prefix web-nuxt run typecheck`, and verify 390×844 drag/edit/action dock, 1024 split, 1440 three-column, reduced motion and map failure fallback.

- [ ] **Step 6: Commit**

```bash
git add web-nuxt/pages/tao-lich-trinh.vue web-nuxt/composables/useItineraryOptimization.ts web-nuxt/composables/useRouting.ts web-nuxt/components/planner web-nuxt/assets/css/base.css web-nuxt/assets/css/catalog.css web-nuxt/tests/planner-friction.test.ts web-nuxt/tests/planner-optimization-preview.test.ts web-nuxt/tests/itinerary-optimization.test.ts web-nuxt/tests/itinerary-routing.test.ts web-nuxt/tests/itinerary-time-schedule.test.ts
git commit -m "feat: add resilient itinerary planning surfaces"
```

## Task 8: Journey Thread và adaptive priority

**Files:**
- Create: `web-nuxt/composables/useJourneyThread.ts`
- Create: `web-nuxt/composables/useAdaptivePriority.ts`
- Create: `web-nuxt/composables/useAttentionBudget.ts`
- Modify: `web-nuxt/composables/useJourneyActions.ts`
- Modify: `web-nuxt/composables/useContextualRecommendations.ts`
- Modify: `web-nuxt/composables/usePersonalizationPreferences.ts`
- Modify: `web-nuxt/composables/useRecentlyViewed.ts`
- Modify: `web-nuxt/components/JourneyActionRail.vue`
- Modify: `web-nuxt/components/WhyThisDrawer.vue`
- Test: `web-nuxt/tests/journeyActions.test.ts`
- Test: `web-nuxt/tests/why-this-trust.test.ts`
- Create: `web-nuxt/tests/journey-thread.test.ts`
- Create: `web-nuxt/tests/adaptive-priority.test.ts`
- Create: `web-nuxt/tests/attention-budget.test.ts`

**Interfaces:**
- Consumes: `ContextEnvelope`, `SearchViewState`, saved/recent composables and route history.
- Produces: `useJourneyThread()` with `snapshot()`, `pushIntent()`, `restore()`, `clear()`, `returnPath`; `useAdaptivePriority()` with `resolve({ context, intent, candidates })`; `useAttentionBudget()` with `canSuggest()`, `dismiss()` and `resetSession()`.

- [ ] **Step 1: Write failing adaptation tests**

```ts
it('changes CTA only for high-confidence intent', () => {
  expect(resolvePriority({ confidence: 'low', defaultCta: 'view', candidateCta: 'directions' }).primaryCta).toBe('view')
  expect(resolvePriority({ confidence: 'high', defaultCta: 'view', candidateCta: 'directions' }).primaryCta).toBe('directions')
})
```

Also test Journey Thread restoration from search → detail → planner, dismiss persistence and no more than one primary/two secondary suggestions per viewport.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `npm --prefix web-nuxt test -- journey-thread.test.ts adaptive-priority.test.ts attention-budget.test.ts journeyActions.test.ts why-this-trust.test.ts`

Expected: FAIL until the shared thread, confidence and budget contracts exist.

- [ ] **Step 3: Implement deterministic, reversible priority resolution**

`useAdaptivePriority()` must return `{ primaryCta, orderedBlocks, suggestions, reasons, reversible }`. Confidence `low` returns defaults; `medium` may reorder metadata; `high` may change the primary CTA only when the action data is valid. Every non-default decision includes a reason and reset action.

- [ ] **Step 4: Integrate Journey Thread without hydration reorder**

Keep volatile client-only saved/recent/community actions behind `ClientOnly` where needed. Preserve query/filter/context/back-stack/auth return path and use a bounded TTL for recent/saved context.

- [ ] **Step 5: Run tests, typecheck and smoke navigation**

Run focused tests and `npm --prefix web-nuxt run typecheck`. Smoke: homepage → search → detail → planner → back; guest auth return; `Hiển thị gọn hơn`; dismiss suggestion and reload.

- [ ] **Step 6: Commit**

```bash
git add web-nuxt/composables/useJourneyThread.ts web-nuxt/composables/useAdaptivePriority.ts web-nuxt/composables/useAttentionBudget.ts web-nuxt/composables/useJourneyActions.ts web-nuxt/composables/useContextualRecommendations.ts web-nuxt/composables/usePersonalizationPreferences.ts web-nuxt/composables/useRecentlyViewed.ts web-nuxt/components/JourneyActionRail.vue web-nuxt/components/WhyThisDrawer.vue web-nuxt/tests/journey-thread.test.ts web-nuxt/tests/adaptive-priority.test.ts web-nuxt/tests/attention-budget.test.ts web-nuxt/tests/journeyActions.test.ts web-nuxt/tests/why-this-trust.test.ts
git commit -m "feat: add reversible public journey adaptation"
```

## Task 9: Accessibility, reliability, RUM và feature kill switches

**Files:**
- Create: `web-nuxt/types/accessibility.ts`
- Create: `web-nuxt/composables/useAccessibilityProfile.ts`
- Create: `web-nuxt/composables/usePublicTelemetry.ts`
- Modify: `web-nuxt/composables/useFeature.ts`
- Modify: `web-nuxt/utils/featureFlags.ts`
- Modify: `web-nuxt/assets/css/base.css`
- Modify: `web-nuxt/assets/css/shell.css`
- Modify: `web-nuxt/assets/css/dark-overrides.css`
- Modify: `web-nuxt/nuxt.config.ts`
- Create: `web-nuxt/tests/accessibility-profile.test.ts`
- Create: `web-nuxt/tests/public-telemetry.test.ts`
- Create: `web-nuxt/tests/public-kill-switch.test.ts`
- Test: `web-nuxt/tests/service-worker-policy.test.ts`

**Interfaces:**
- Consumes: `ContextEnvelope`, feature flag patterns and existing launch-safety/service-worker policy.
- Produces: `AccessibilityProfile`, `useAccessibilityProfile()`, `trackPublicOutcome()`, `trackPublicHarm()`, `trackPerformanceBudget()` and independent flags for personalization, recommendation, search expansion, optimizer and proactive notices.

- [ ] **Step 1: Write failing accessibility/telemetry tests**

```ts
it('disables ambient motion when reduced motion is requested', () => {
  const profile = resolveAccessibilityProfile({ reducedMotion: true, textScale: 2 })
  expect(profile.reducedMotion).toBe(true)
  expect(profile.textScale).toBe(2)
})

it('redacts raw coordinates from telemetry payloads', () => {
  const event = sanitizePublicTelemetry({ area: 'vinh-long', lat: 10.2, lng: 105.9 })
  expect(event).not.toHaveProperty('lat')
  expect(event).not.toHaveProperty('lng')
})
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `npm --prefix web-nuxt test -- accessibility-profile.test.ts public-telemetry.test.ts public-kill-switch.test.ts service-worker-policy.test.ts`

Expected: FAIL because the profile, redaction and independent kill-switch APIs are not implemented.

- [ ] **Step 3: Implement accessibility profile and CSS media contracts**

Persist user-selected theme/density/text scale without auto-changing theme by time. Add `prefers-reduced-motion`, `prefers-contrast: more`, forced-colors and safe-area rules. Keep content readable and focusable at 200% zoom.

- [ ] **Step 4: Implement redacted telemetry and flags**

`usePublicTelemetry()` must accept event name, outcome/harm class, route family, viewport, network, theme and area id only. Reject raw coordinates, phone numbers, query text containing private data and arbitrary payload keys. Feature flags must fail closed to deterministic UI when unavailable.

- [ ] **Step 5: Run tests, typecheck and build**

Run focused tests, `npm --prefix web-nuxt run typecheck`, `npm --prefix web-nuxt test`, and `npm --prefix web-nuxt run build`. Verify no flag-off path blocks search/detail/planner.

- [ ] **Step 6: Commit**

```bash
git add web-nuxt/types/accessibility.ts web-nuxt/composables/useAccessibilityProfile.ts web-nuxt/composables/usePublicTelemetry.ts web-nuxt/composables/useFeature.ts web-nuxt/utils/featureFlags.ts web-nuxt/assets/css/base.css web-nuxt/assets/css/shell.css web-nuxt/assets/css/dark-overrides.css web-nuxt/nuxt.config.ts web-nuxt/tests/accessibility-profile.test.ts web-nuxt/tests/public-telemetry.test.ts web-nuxt/tests/public-kill-switch.test.ts web-nuxt/tests/service-worker-policy.test.ts
git commit -m "feat: add public quality controls and kill switches"
```

## Task 10: Visual regression, RUM gates và rollout closure

**Files:**
- Create: `web-nuxt/tests/public-visual-baseline.test.ts`
- Create: `web-nuxt/tests/public-state-matrix.test.ts`
- Modify: `web-nuxt/tests/smoke.test.ts`
- Modify: `scripts/smoke_e2e_chrome.mjs`
- Create: `docs/superpowers/reports/2026-08-09-adaptive-nocturne-public-upgrade-verification.md`

**Interfaces:**
- Consumes: all public surfaces and telemetry/flag contracts from Tasks 1-9.
- Produces: repeatable browser checks, state matrix evidence, RUM budget report and rollback verification for the public vertical slice.

- [ ] **Step 1: Add deterministic state matrix tests**

Cover routes `/`, `/du-lich`, `/tim-kiem`, `/ban-do`, `/dia-diem/{id}` and `/tao-lich-trinh` for loading, ready, partial, stale, empty, error, offline, 404-confirmed and retryable-5xx. Assert the content/action recovery rules from the design spec.

- [ ] **Step 2: Add visual baseline scenarios**

Capture Nocturne/Parchment at 375, 390, 768, 1024 and 1440px. Name screenshots by route, theme, viewport and state so a review can distinguish layout regression from data variance.

- [ ] **Step 3: Extend smoke flow**

The browser smoke must complete homepage → search → map/list toggle → detail → planner → back, then run map failure fallback and retryable detail error. It must assert no console error, no action-dock overlap and preserved query/filter state.

- [ ] **Step 4: Run all verification gates**

Run:

```bash
npm --prefix web-nuxt run typecheck
npm --prefix web-nuxt test
npm --prefix web-nuxt run build
python scripts/checks/run_hard.py --all
node scripts/smoke_e2e_chrome.mjs
```

Expected: typecheck, tests, build and hard checks pass; browser flow records any external backend limitation without converting it into a false product failure.

- [ ] **Step 5: Document rollout/rollback evidence**

Record baseline metrics, feature flag values, screenshots, known backend limitations, false-404 checks, map fallback, accessibility checks and the exact kill-switch command/path in `docs/superpowers/reports/2026-08-09-adaptive-nocturne-public-upgrade-verification.md`.

- [ ] **Step 6: Commit verification artifacts**

```bash
git add web-nuxt/tests/public-visual-baseline.test.ts web-nuxt/tests/public-state-matrix.test.ts web-nuxt/tests/smoke.test.ts scripts/smoke_e2e_chrome.mjs docs/superpowers/reports/2026-08-09-adaptive-nocturne-public-upgrade-verification.md
git commit -m "test: close adaptive public upgrade quality gates"
```

## Self-review checklist

- [ ] Every spec section maps to at least one task: foundation, homepage/catalog, search/map, detail, planner, continuity, adaptive intelligence, accessibility, reliability, telemetry, rollout and rollback.
- [ ] No task changes route/API/auth/RBAC without an explicit contract task.
- [ ] Every new interface name is defined before a later task consumes it.
- [ ] Every task has failing test → focused run → implementation → passing run → commit.
- [ ] Search/map, detail and planner each have a usable fallback when a dependent panel fails.
- [ ] False-404, raw location redaction, reduced motion, 200% zoom and feature kill switches are explicit tests.
- [ ] No incomplete or vague instruction, fake metric, unbounded retry or silent mutation remains.
