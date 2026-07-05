# Homepage Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De-duplicate the homepage (each "current" entity appears once in the top zone), separate the decision-index (editorial) from the journey-rail (personal-only), remove the hero pills, and collapse the 3-section personalization cluster into one compact image-tolerant strip.

**Architecture:** Frontend-only. A pure-function refactor in `useJourneyActions.ts` (guarded by a new behavioral test), then a single coordinated pass over `pages/index.vue` (dedup computeds + template wiring + a new merged section). No backend, schema, or data changes.

**Tech Stack:** Nuxt 4 SSR, Vue 3 `<script setup>`, CSS design tokens (no Tailwind), Vitest.

**Spec:** `docs/superpowers/specs/2026-07-05-homepage-refinement-dedup-design.md`

## Global Constraints

- **NEVER build with `API_BASE` pointing at a public URL** — it bakes the runtime `/api/**` proxy target and causes an nginx↔nitro loop → site-wide 500. Build with the default (`localhost:8360`). Deploy with `bash scripts/deploy.sh --frontend` **from the repo root** (`/c/Code/vinhlong360`), never from `web-nuxt/`.
- CTA is contact/discover only — no booking/price/order form (§1.4). No new images added (§B6: only AI-gen `cx/gpt-5.5-image` allowed, none needed here). CSS design tokens only, matching nearby rules — no hardcoded hex, no Tailwind.
- Preserve reduced-motion and dark-mode parity by reusing existing `.card` / `.scroll-row` / `.cat-*` patterns.
- Each task leaves the FE building green (§B5). §B3: the composable refactor is covered by a behavioral test written first.
- Cold `nuxt build` can exceed 4 min — run builds in the **background**. If esbuild throws a CSS-cache error, clear `.nuxt`, `node_modules/.cache`, `node_modules/.vite` and rebuild.

---

### Task 1: Journey-rail composable → personal-only (TDD)

**Files:**
- Create: `web-nuxt/tests/journeyActions.test.ts`
- Modify: `web-nuxt/composables/useJourneyActions.ts` (function `homepageDecisionActions`, lines ~148–227)

**Interfaces:**
- Produces: `homepageDecisionActions(input)` now returns **only** personal actions. Keeps ids `home-continue-saved` (logged-in + `savedCount>0`) and `home-recent` (`recentCount>0`). No longer returns `home-start-planner`, `home-event`, `home-map`, or `home-community`. The input **interface is unchanged** (extra fields stay optional and are ignored) so the current `index.vue` call site keeps compiling until Task 2.

- [ ] **Step 1: Write the failing behavioral test**

Create `web-nuxt/tests/journeyActions.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { useJourneyActions } from '../composables/useJourneyActions'

const { homepageDecisionActions } = useJourneyActions()

describe('homepageDecisionActions — personal-only', () => {
  it('returns nothing for an anonymous first-time visitor', () => {
    expect(homepageDecisionActions({ isLoggedIn: false, savedCount: 0, recentCount: 0, currentMonth: 7 })).toEqual([])
  })

  it('never emits editorial/generic echoes (event, heroFeature, map, community)', () => {
    const ids = homepageDecisionActions({
      isLoggedIn: true, savedCount: 5, recentCount: 3, currentMonth: 7,
      heroFeatureName: 'X', heroFeaturePlannerPath: '/tao-lich-trinh?add=x',
      upcomingEventName: 'Lễ', upcomingEventPath: '/dia-diem/le', communityPostCount: 9,
    }).map(a => a.id)
    expect(ids).not.toContain('home-start-planner')
    expect(ids).not.toContain('home-event')
    expect(ids).not.toContain('home-map')
    expect(ids).not.toContain('home-community')
  })

  it('emits the saved→plan action for a logged-in user with saves', () => {
    const ids = homepageDecisionActions({ isLoggedIn: true, savedCount: 5, recentCount: 0, currentMonth: 7 }).map(a => a.id)
    expect(ids).toContain('home-continue-saved')
  })

  it('emits the continue-recent action when there is recent history', () => {
    const ids = homepageDecisionActions({ isLoggedIn: false, savedCount: 0, recentCount: 4, currentMonth: 7 }).map(a => a.id)
    expect(ids).toContain('home-recent')
  })

  it('emits at most the two personal actions', () => {
    const actions = homepageDecisionActions({ isLoggedIn: true, savedCount: 5, recentCount: 4, currentMonth: 7 })
    expect(actions.length).toBeLessThanOrEqual(2)
  })
})
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd web-nuxt && npx vitest run tests/journeyActions.test.ts`
Expected: FAIL — the current function emits `home-start-planner`/`home-event`/`home-map`.

- [ ] **Step 3: Refactor the function body to personal-only**

In `web-nuxt/composables/useJourneyActions.ts`, replace the body of `homepageDecisionActions` (from the first `const savedCount = …` down to `return actions.slice(0, 3)`) with:

```ts
    const savedCount = positiveNumber(input.savedCount)
    const recentCount = positiveNumber(input.recentCount)
    const actions: JourneyAction[] = []

    // Personal-only: the editorial "what's on now" lives in the decision index (index.vue).
    // This rail is strictly the returning-user's own resume points — no event/heroFeature/
    // map/community echoes (those duplicated the index). Empty for anon/first-timers → hidden.
    if (input.isLoggedIn && savedCount > 0) {
      actions.push({
        id: 'home-continue-saved',
        icon: '💾',
        label: 'Tiếp tục từ mục đã lưu',
        text: `${savedCount} mục đã lưu có thể gom thành lịch trình.`,
        to: '/tao-lich-trinh?source=saved',
        tone: 'planner',
      })
    }

    if (recentCount > 0) {
      actions.push({
        id: 'home-recent',
        icon: '🕘',
        label: 'Nối tiếp điểm vừa xem',
        text: `${recentCount} nội dung gần đây, mở lại để so sánh trước khi lưu.`,
        to: '/da-luu?tab=recent',
        tone: 'neutral',
      })
    }

    return actions.slice(0, 2)
```

Leave the `homepageDecisionActions` parameter interface (lines ~148–158) **unchanged** — the extra fields become unused-but-accepted, keeping the `index.vue` call site valid until Task 2.

- [ ] **Step 4: Run the test, verify it passes**

Run: `cd web-nuxt && npx vitest run tests/journeyActions.test.ts`
Expected: PASS (5/5).

- [ ] **Step 5: Run the full FE suite (nothing else regressed)**

Run: `cd web-nuxt && npx vitest run`
Expected: all green (incl. `tests/smoke.test.ts`, which only asserts `homepageDecisionActions` is present/called — still true).

- [ ] **Step 6: Commit**

```bash
git add web-nuxt/composables/useJourneyActions.ts web-nuxt/tests/journeyActions.test.ts
git commit -m "refactor(home): journey rail → personal-only actions + behavioral test"
```

---

### Task 2: index.vue — de-dup, decision cut, pills removal, rail copy, personalization merge

**Files:**
- Modify: `web-nuxt/pages/index.vue` (template + `<script setup>` + `<style>`)

**Interfaces:**
- Consumes: `homepageDecisionActions` (new personal-only behavior from Task 1); existing helpers already in this file — `entityPath`, `savedItemPath`, `getTypeMeta` (via `getFavTypeMeta`), `isRemoteUrl`, `generateCategoryIcon` (aliased `genIcon`), `plannerAddPath`; existing composables `useFavorites` (`favorites`), `useRecentlyViewed` (`recentItems`), and `useContextualRecommendations` (client-safe — no SSR fetch), `useFeature`.

This is one coordinated pass over a single large file. Locate edit sites by the anchor comments/headings quoted below (line numbers drift as you edit). After all edits, the homepage renders each of the four "current" entities once in the top zone, has no hero pills, a personal-only rail, and a single "Dành cho bạn" strip.

- [ ] **Step 1: Remove the hero pills**

Template — delete the `.hero-pills` block (the `<div class="hero-pills">…</div>` with the `v-for="pill in heroPills"`, just under `<SearchAutocomplete … />`).
Script — delete `const DEFAULT_HERO_PILLS = […]` and `const heroPills = computed(…)`.
Style — delete the `.hero-pills` and `.hero-pill` (and any `.hero-pill:hover`/`:focus-visible`) CSS rules.

- [ ] **Step 2: Drop the `heroFeature` card from the decision index**

In `homeDecisionCards` (anchor: `const homeDecisionCards = computed<HomeDecisionCard[]>`), delete the entire `if (heroFeature.value) { cards.push({ … title: 'Bắt đầu lịch trình' … tone: 'planner' }) }` block. Leave the event, seasonal, dish blocks and the trailing `if (cards.length < 4) { … tone: 'map' }` fallback intact — the index now reads `01 Có lịch gần nhất · 02 Đang vào mùa · 03 Ăn gì hôm nay · 04 Mở bản đồ`.

- [ ] **Step 3: Add the de-dup computeds**

In `<script setup>`, after the `spotlight`/`spotId`/`heroFeature`/`firstSeasonal`/`firstDish` definitions exist, add:

```ts
// De-dup: entities already shown in the top zone (hero + decision index) or the spotlight
// band are excluded from the downstream grids so no "current" entity repeats. Pure computeds
// → SSR/CSR identical.
const experienceThumbs = computed(() =>
  experiences.value.filter((e: any) => e.id !== heroFeature.value?.id && e.id !== spotId.value).slice(0, 3))
const ocopThumbs = computed(() =>
  productsAll.value.filter((p: any) => p.id !== spotId.value).slice(0, 3))
const topDishesList = computed(() =>
  topDishes.value.filter((d: any) => d.id !== firstDish.value?.id))
const seasonalList = computed(() => {
  const rest = seasonal.value.filter((e: any) => e.id !== firstSeasonal.value?.id)
  return rest.length ? rest : seasonal.value
})
```

- [ ] **Step 4: Wire the de-dup computeds into the template**

- `FEATURE_EXPERIENCE` block: `:thumbs="experiences.slice(0, 3)"` → `:thumbs="experienceThumbs"`.
- `FEATURE_OCOP` block: `:thumbs="productsAll.slice(0, 3)"` → `:thumbs="ocopThumbs"`.
- Seasonal scroll-row (anchor: `aria-label="Đặc sản theo mùa"`): `v-for="e in seasonal"` → `v-for="e in seasonalList"`.
- Quán ngon block (anchor: `class="top-dishes"`): change its guard `v-if="topDishes.length"` → `v-if="topDishesList.length"` and `v-for="d in topDishes"` → `v-for="d in topDishesList"`.

- [ ] **Step 5: Retitle the journey rail + simplify its call site**

Template (anchor: `<JourneyActionRail`): change
`title="Bước tiếp theo phù hợp"` → `title="Tiếp tục hành trình của bạn"` and
`subtitle="Decision engine ưu tiên theo mục đã lưu, nội dung vừa xem, lịch gần nhất và tín hiệu cộng đồng."` → `subtitle="Từ những gì bạn đã lưu và vừa xem."`

Script (anchor: `const homeJourneyActions = computed`): replace with the minimal input:

```ts
const homeJourneyActions = computed(() => homepageDecisionActions({
  isLoggedIn: isLoggedIn.value,
  savedCount: favorites.value.length,
  recentCount: recentItems.value.length,
  currentMonth: currentMonth.value,
}))
```

- [ ] **Step 6: Replace the 3-section personalization cluster with one "Dành cho bạn" strip**

Template — replace the entire second `<ClientOnly>…</ClientOnly>` block (anchor: comment `<!-- 6. Cá nhân hóa —` — the block containing `Xem gần đây`, `Đã lưu gần đây`, and `<LazySmartRecommendations …/>`) with:

```vue
    <!-- 6. Dành cho bạn — one merged, image-tolerant personalization strip (client-only) -->
    <ClientOnly>
      <section v-if="forYou.length" class="block block-compact reveal" aria-label="Dành cho bạn">
        <div class="section-head section-head-tight">
          <div class="sh-text">
            <h2 class="h2-tight">Dành cho bạn</h2>
            <p class="sh-sub">Nội dung bạn vừa xem, đã lưu và gợi ý theo bạn.</p>
          </div>
        </div>
        <div class="scroll-row for-you-row" role="region" aria-label="Dành cho bạn" tabindex="0">
          <NuxtLink v-for="item in forYou" :key="item.id" :to="item.to" class="fy-chip">
            <span class="fy-thumb" :class="`cat-${getFavTypeMeta(item.type).cat}`">
              <NuxtImg v-if="item.image && isRemoteUrl(item.image)" :src="item.image" :alt="item.name" loading="lazy" decoding="async" width="64" height="64" sizes="64px" @error="onImgError" />
              <img v-else-if="item.image" :src="item.image" :alt="item.name" loading="lazy" decoding="async" width="64" height="64" @error="onImgError" />
              <span v-else class="fy-icon" v-html="genIcon(getFavTypeMeta(item.type).cat)" />
            </span>
            <span class="fy-body">
              <span class="fy-type">{{ getFavTypeMeta(item.type).label }}</span>
              <span class="fy-name">{{ item.name }}</span>
            </span>
          </NuxtLink>
        </div>
      </section>
    </ClientOnly>
```

Script — add the merge (client-safe; `useContextualRecommendations` no-ops on SSR). Place near the other personalization state:

```ts
const { enabled: ff } = useFeature()
const contextualRec = useContextualRecommendations({ context: 'home', limit: 8 })
const forYou = computed(() => {
  const seen = new Set<string>()
  const out: { id: string; name: string; type: string; image: string; to: string }[] = []
  const push = (id: any, name: any, type: any, image: any, to: string) => {
    const key = String(id ?? '')
    if (!key || !name || seen.has(key)) return
    seen.add(key)
    out.push({ id: key, name, type: type || 'place', image: image || '', to })
  }
  recentItems.value.forEach((rv: any) => push(rv.id, rv.name, rv.type, rv.image, entityPath(rv.id)))
  favorites.value.forEach((fav: any) => push(fav.id, fav.name, fav.type, fav.image, savedItemPath(fav)))
  if (ff('ai_recommendations')) contextualRec.items.value.forEach((e: any) => push(e.id, e.name, e.type, e.images?.[0], entityPath(e.id)))
  return out.slice(0, 8)
})
```

Then remove the now-unused `recentlyViewed`, `recentSaved`, and `genPlaceholder` bindings if the build/typecheck flags them as unused (keep `genIcon`, still used by the chips; keep `generateCategoryPlaceholder` import — `hfBg` still uses it).

- [ ] **Step 7: Add the chip strip CSS**

In the page `<style>`, add rules for `.for-you-row` / `.fy-chip` / `.fy-thumb` / `.fy-icon` / `.fy-body` / `.fy-type` / `.fy-name`. Match the design tokens already used by nearby `.card`, `.dish-item`, and `.hf-*` rules (surface/border/shadow/radius/space/text/weight tokens) — do not invent token names or hardcode hex. Target: ~56–64px rounded thumbnail, compact 2-line label, horizontal chips ~15rem wide, hover lift consistent with `.card:hover`. **No full-width gradient cover.**

- [ ] **Step 8: Typecheck + full FE suite + build**

Run: `cd web-nuxt && npx vue-tsc --noEmit` (or the project's typecheck script) — no new errors.
Run: `cd web-nuxt && npx vitest run` — all green (smoke test still passes: hero card still contains `plannerAddPath(heroFeature.id)`; `homeDecisionCards`/`homeJourneyActions`/`JourneyActionRail`/`"Hôm nay bạn muốn bắt đầu thế nào?"` all still present).
Run (background): `cd web-nuxt && npm run build` — succeeds.

- [ ] **Step 9: Commit**

```bash
git add web-nuxt/pages/index.vue
git commit -m "refactor(home): de-dup top zone, cut hero pills, merge personalization strip"
```

---

### Task 3 (optional, low-priority): Itinerary cover variety

**Files:**
- Modify: `web-nuxt/components/ItineraryCard.vue` (`coverSrc`, line ~47)

Only do this if the `/api/homepage` itinerary objects actually carry a real cover field. First check: `console.log` or inspect one itinerary object's keys. If it has `cover`/`image`/first-stop image, prefer it; else the area illustration. If no such field exists, **skip this task** and leave a one-line note — it is not a blocker.

- [ ] **Step 1: Inspect an itinerary object's shape** (via the live `/api/homepage` payload or a dev log) for a usable cover field.
- [ ] **Step 2:** If present, change `coverSrc` to prefer it:
```ts
const coverSrc = computed(() =>
  props.itinerary.cover || props.itinerary.image || `/img/cat/${AREA_IMG[props.itinerary.area] || 'itinerary'}.jpg`)
```
- [ ] **Step 3:** `cd web-nuxt && npx vitest run` green; commit `fix(home): itinerary card prefers real cover when available`. If skipped, record why in the ledger.

---

## Controller-run finalization (not a subagent task)

1. **Build** (background) from `web-nuxt` with default API_BASE.
2. **Deploy** `bash scripts/deploy.sh --frontend` from repo root (`/c/Code/vinhlong360`). Never `API_BASE=public`.
3. **Chrome verify (live):** each of Cua cốm / Lễ vía / Cô Diễm / Ốc Gạo appears once in the top zone; no hero pills; personal-only rail (hidden while anon, resume-actions when logged-in with history); one "Dành cho bạn" strip with 56–64px thumbs/icons and **no** full-width gradient covers; 0 console errors, 0 hydration mismatch; section count ~11.
4. **Final whole-branch code review** (superpowers:requesting-code-review) over the range, then finishing-a-development-branch.

## Self-review notes

- Spec coverage: decision-cut (T2.2), rail personal-only (T1+T2.5), dedup (T2.3–4), pills (T2.1), personalization merge (T2.6–7), optional itinerary (T3) — all covered.
- Type consistency: `getFavTypeMeta` (alias of `getTypeMeta`) returns `{ label, cat }` — used for both the `cat-*` class and `genIcon(cat)`. `forYou` items expose `{ id, name, type, image, to }`, matching the template.
- Build-green invariant: Task 1 keeps the composable signature loose so `index.vue` compiles before Task 2 tightens the call site.
