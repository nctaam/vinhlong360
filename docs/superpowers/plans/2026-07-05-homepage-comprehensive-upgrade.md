# Homepage Comprehensive Upgrade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Lift the vinhlong360 homepage from ~7.5/10 to 9+ via hero-grade AI imagery, editorial restraint, and one signature sensory moment — replacing the below-hero card-row monotony with photo-led feature blocks + a full-bleed spread.

**Architecture:** Add 2 presentational Vue components (`EntityFeature.vue`, `StorySpread.vue`) + 1 sensory composable (`useParallax.ts`), generate ~6 hero-grade AI images, and reorganize `pages/index.vue` (keep strong modules, insert 2 features + 1 spread, cut/slim weak sections, replace empty community). Frontend-only; no backend/schema change except the step-0 data deploy of already-committed entity images.

**Tech Stack:** Nuxt 4 SSR (Vue 3 `<script setup>`), CSS design tokens (no Tailwind), route-scoped `<style>`, `scripts/gen_image.py` (cx/gpt-5.5-image) + Pillow, vitest (frontend unit), `scripts/deploy.sh`.

## Global Constraints

- CSS design tokens only — **no Tailwind, no new CSS framework**. Reuse `variables.css` / `editorial.css` tokens (`--font-editorial`, `--scrim-hero`, `--space-*`, `--ease-*`, `--grain`).
- Images: **AI-generated only** (cx/gpt-5.5-image via `scripts/gen_image.py`, key from `.env` `IMAGE_API_KEY`, never hardcode). No stock/Wikimedia/UGC. No text/watermark/logo in prompts.
- CTA: **contact/discover only** — never order/booking/price-confirm forms.
- CWV must not regress: first feature image `fetchpriority="high"` + preload; all else `loading="lazy"`; parallax **below-fold only**; fixed `aspect-ratio` on images (no CLS).
- `prefers-reduced-motion: reduce` → all parallax/Ken Burns **off** (no transform).
- Dark-mode parity: every new surface works in `.dark` using tokens (dark rules go in `dark-overrides.css` if scoped CSS drops `:global(.dark)`).
- §B5: each task leaves the site building + shippable. Commit per task.
- §B1: `python scripts/backup_data.py` before any data op (already done this session at `scratch/backups/20260704-234632`; re-run if stale).
- §B7: `deploy.sh --replace` is gated — Task 1 requires the prod-sync pre-check + is the only data-destructive-mechanism step.

---

## File Structure

- **Create** `web-nuxt/composables/useParallax.ts` — opt-in scroll parallax (1 IntersectionObserver + rAF; reduced-motion no-op).
- **Create** `web-nuxt/composables/__tests__/useParallax.spec.ts` — unit test for the reduced-motion + no-observer guards.
- **Create** `web-nuxt/components/home/EntityFeature.vue` — photo-led feature block (image + editorial copy + CTA + supporting thumbs), `side` + `priority` props.
- **Create** `web-nuxt/components/home/StorySpread.vue` — full-bleed panorama section (Ken Burns + parallax + overlaid title).
- **Create** `web-nuxt/public/img/features/*.webp` (~4, 16:9 @1200w) + `web-nuxt/public/img/spread/*.webp` (1–2, panorama).
- **Modify** `web-nuxt/pages/index.vue` — hero card fix, insert features/spread, cut trending, slim itineraries/personalization, replace community, editorial copy constants + section CSS.
- **Modify** `web-nuxt/assets/css/dark-overrides.css` — dark rules for new surfaces if needed.

---

## Task 1: Step 0 — Deploy the 31 committed entity images to prod

**Files:** none (ops). Uses committed `web/data.json` + `web-nuxt/public/img/entities/*.webp` (commit `30a3fae`).

**Interfaces:** Produces: live prod homepage where EntityCard covers render real photos (client-fetched from prod `/api/homepage`).

- [ ] **Step 1: Prod-sync pre-check.** Compare prod entity count to local `data.json` (1730) before the destructive re-import.
Run:
```bash
curl -s https://vinhlong360.vn/api/homepage -o /tmp/h.json
python -c "import json;print('prod stats.entities=',json.load(open('/tmp/h.json'))['stats'].get('entities'))"
python -c "import json;print('local data.json entities=',len(json.load(open('web/data.json',encoding='utf-8'))['entities']))"
```
Expected: prod ≈ local (1730). If wildly off, STOP and ask the human (data.json may be stale vs prod).

- [ ] **Step 2: Deploy frontend + data + replace (auto-backs-up prod first).**
Run:
```bash
VL360_DEPLOY_HOST=root@66.42.57.202 bash scripts/deploy.sh --frontend --backend --data --replace
```
Expected tail: `db dump -> backups/db-pre-deploy-*.dump`, `home=200 search=200 agent_ready=200`, `DONE`.

- [ ] **Step 3: Verify live via chrome MCP.** Navigate `https://vinhlong360.vn/`, scroll to the seasonal/trending rows, confirm EntityCard covers show real photos (not gradient+icon). Check console has no new errors.

- [ ] **Step 4: No commit** (code already committed; this is a deploy). Record deploy TS + rollback path in the progress ledger.

---

## Task 2: Hero feature card → real entity image (remove the placeholder island)

**Files:** Modify `web-nuxt/pages/index.vue` (`hfBg` computed ~line 469; hero feature-card template in the hero section ~lines 4–43).

**Interfaces:** Consumes: `heroFeature` (existing computed ~467), `heroFeature.images`. Produces: hero card renders `heroFeature.images[0]` when present.

- [ ] **Step 1:** Locate `const hfBg = computed(() => heroFeature.value && hfMeta.value ? generateCategoryPlaceholder(heroFeature.value.id, hfMeta.value.cat) : '')` and the `.hf-card` markup (grep `hfBg`, `hf-card`, `hfIcon`).

- [ ] **Step 2:** Mirror the spotlight fix (already in this file): prefer the entity's real cover, fall back to the gradient placeholder. Replace `hfBg`:
```ts
const hfBg = computed(() => {
  const img = heroFeature.value?.images?.[0]
  if (img) return `linear-gradient(to top, rgba(18,20,24,.42) 0%, rgba(18,20,24,.06) 45%, rgba(18,20,24,.22) 100%), url(${img})`
  return heroFeature.value && hfMeta.value ? generateCategoryPlaceholder(heroFeature.value.id, hfMeta.value.cat) : ''
})
```
Then in the `.hf-card` template, render the icon (`hfIcon`) only when there is NO real image: add `v-if="!heroFeature?.images?.length"` to the icon span so a real photo shows clean (with scrim already baked into `hfBg`).

- [ ] **Step 3: Build + browser-verify.** `cd web-nuxt && npm run build` (green). Via chrome MCP on the built/live page: hero card shows a real photo (heroFeature has an image after Task 1) with legible text, both light + `.dark`.

- [ ] **Step 4: Commit.**
```bash
git add web-nuxt/pages/index.vue
git commit -m "feat(ui): hero feature card uses real entity image (remove placeholder island)"
```

---

## Task 3: `useParallax` composable (sensory foundation)

**Files:** Create `web-nuxt/composables/useParallax.ts`, `web-nuxt/composables/__tests__/useParallax.spec.ts`.

**Interfaces:** Produces: `useParallax(targets: Ref<HTMLElement[]> | (() => HTMLElement[]), opts?: { intensity?: number })` — attaches an IntersectionObserver; while a target is in view, sets `--parallax: <px>` on it via rAF on scroll; no-op when `prefers-reduced-motion` or no `IntersectionObserver`. Auto-cleans on unmount.

- [ ] **Step 1: Write the failing test** (`useParallax.spec.ts`):
```ts
import { describe, it, expect, vi } from 'vitest'
import { useParallax } from '../useParallax'

describe('useParallax', () => {
  it('is a no-op when reduced-motion is preferred', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true, addEventListener() {}, removeEventListener() {} }))
    const el = document.createElement('div')
    // should not throw and should not attach any inline --parallax
    expect(() => useParallax(() => [el])).not.toThrow()
    expect(el.style.getPropertyValue('--parallax')).toBe('')
  })
  it('is a no-op on server / when IntersectionObserver is missing', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: false, addEventListener() {}, removeEventListener() {} }))
    vi.stubGlobal('IntersectionObserver', undefined)
    const el = document.createElement('div')
    expect(() => useParallax(() => [el])).not.toThrow()
  })
})
```

- [ ] **Step 2: Run test to verify it fails.** `cd web-nuxt && npx vitest run composables/__tests__/useParallax.spec.ts` → FAIL (module not found).

- [ ] **Step 3: Implement** `useParallax.ts`:
```ts
import { onMounted, onUnmounted } from 'vue'

type Targets = (() => HTMLElement[])

export function useParallax(targets: Targets, opts: { intensity?: number } = {}) {
  if (!import.meta.client) return
  const intensity = opts.intensity ?? 0.08
  const reduce = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduce || typeof IntersectionObserver === 'undefined') return

  let observer: IntersectionObserver | null = null
  const visible = new Set<HTMLElement>()
  let ticking = false

  const update = () => {
    ticking = false
    const vh = window.innerHeight || 1
    for (const el of visible) {
      const r = el.getBoundingClientRect()
      // progress: -1 (below) .. +1 (above); 0 at viewport center
      const p = (r.top + r.height / 2 - vh / 2) / vh
      el.style.setProperty('--parallax', `${(-p * intensity * r.height).toFixed(1)}px`)
    }
  }
  const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(update) } }

  onMounted(() => {
    const els = targets()
    if (!els.length) return
    observer = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting) visible.add(e.target as HTMLElement)
        else visible.delete(e.target as HTMLElement)
      }
      if (visible.size) onScroll()
    }, { rootMargin: '10% 0px 10% 0px' })
    els.forEach(el => observer!.observe(el))
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
  })
  onUnmounted(() => {
    observer?.disconnect(); observer = null
    window.removeEventListener('scroll', onScroll)
  })
}
```
Consumers apply `transform: translate3d(0, var(--parallax, 0), 0)` on the parallaxed layer (the image), which has `--parallax` default 0 → safe SSR + reduced-motion.

- [ ] **Step 4: Run test to verify it passes.** `npx vitest run composables/__tests__/useParallax.spec.ts` → PASS.

- [ ] **Step 5: Commit.**
```bash
git add web-nuxt/composables/useParallax.ts web-nuxt/composables/__tests__/useParallax.spec.ts
git commit -m "feat(ui): useParallax composable — below-fold scroll depth, reduced-motion safe"
```

---

## Task 4: Generate feature images + `EntityFeature.vue` + Feature #1 ("Trải nghiệm miệt vườn")

**Files:** Create `web-nuxt/components/home/EntityFeature.vue`; create `web-nuxt/public/img/features/trai-nghiem.webp`, `.../ocop.webp` (+2 spare); Modify `web-nuxt/pages/index.vue` (insert Feature #1 after the events section; add editorial copy constant).

**Interfaces:** Consumes: `useParallax`, `EntityCard` (for thumbs), `entityPath`. Produces: `<EntityFeature :image="string" :kicker="string" :title="string" :lede="string" :ctaText="string" :ctaTo="string" :thumbs="Entity[]" side="left|right" :priority="boolean" />`.

- [ ] **Step 1: Generate the feature images** (16:9, hero-grade). Reuse the batch pattern from `scratch` (`gen_image.generate(prompt, tmp, size="1536x1024")` → Pillow → webp @1200w). Prompts (base style `, Mekong Delta Vietnam, natural golden-hour light, editorial documentary photography, rich authentic detail, no text, no watermark, no logo`):
  - `trai-nghiem.webp`: "a lush Mekong fruit-orchard garden with a wooden sampan on a canal, dappled sunlight, inviting eco-tourism scene"
  - `ocop.webp`: "an artful flat-lay of Mekong OCOP specialty products — coconut candy, honey, dried fruit, woven baskets — on rustic wood"
  - (2 spare, e.g. `craft.webp`, `river.webp`) for later reuse.
Run each via a small loop like `scratch/gen_batch.py` (adapt paths to `public/img/features/`, size 1536x1024, resize width 1200). Verify each with Read (on-subject, no text).

- [ ] **Step 2: Implement `EntityFeature.vue`** — structure (exact CSS is design-iterative, verify in browser; use tokens):
```vue
<template>
  <section class="ef" :class="`ef-${side}`">
    <NuxtLink :to="ctaTo" class="ef-visual" :aria-label="title">
      <div class="ef-img" ref="imgEl" :style="{ backgroundImage: `url(${image})` }" />
    </NuxtLink>
    <div class="ef-body">
      <span class="ef-kicker">{{ kicker }}</span>
      <h2 class="ef-title">{{ title }}</h2>
      <p class="ef-lede">{{ lede }}</p>
      <div v-if="thumbs?.length" class="ef-thumbs">
        <EntityCard v-for="t in thumbs.slice(0,3)" :key="t.id" :entity="t" />
      </div>
      <NuxtLink :to="ctaTo" class="btn btn-primary ef-cta">{{ ctaText }} →</NuxtLink>
    </div>
  </section>
</template>
```
- `<script setup>`: props `{ image, kicker, title, lede, ctaText, ctaTo, thumbs?, side='left', priority=false }`; `const imgEl = ref<HTMLElement|null>(null)`; call `useParallax(() => imgEl.value ? [imgEl.value] : [], { intensity: 0.05 })`.
- CSS (scoped, tokens): 2-col grid (`ef-visual` ~1.1fr / `ef-body` 1fr); `.ef-right` reverses column order; `.ef-visual` `overflow:hidden; border-radius: var(--radius-lg); aspect-ratio: 16/9`; `.ef-img` `background-size:cover; background-position:center; height:120%; transform: translate3d(0, var(--parallax,0), 0)` (over-height so parallax has room); `.ef-kicker` small-caps `--font-editorial` accent; `.ef-title` `--font-editorial` clamp large; `.ef-lede` reading-measure + drop-cap on `::first-letter`; stack to 1-col under 760px. Dark: text tokens already theme-aware; add `.dark` rule in dark-overrides only if a shorthand erases the image.
- `priority` prop → on the LCP-critical image use an `<img fetchpriority="high">` variant instead of background (only Feature #1 with `priority`); simplest: keep background but add a hidden `<link rel=preload>` via `useHead` when `priority`.

- [ ] **Step 3: Insert Feature #1 in `index.vue`** after the "Đang diễn ra" section. Add a copy constant near other consts:
```ts
const FEATURE_EXPERIENCE = { kicker: 'Trải nghiệm', title: 'Miệt vườn mở cửa đón bạn', lede: 'Chèo xuồng qua rạch dừa, hái trái tại vườn, nghe đờn ca giữa cù lao — những ngày chậm rãi rất Nam Bộ.', ctaText: 'Khám phá trải nghiệm', ctaTo: '/du-lich' }
```
Render: `<EntityFeature :image="'/img/features/trai-nghiem.webp'" v-bind="FEATURE_EXPERIENCE" :thumbs="experiences.slice(0,3)" side="left" :priority="true" />` (import EntityFeature; `experiences` computed already exists).

- [ ] **Step 4: Build + browser-verify.** `npm run build` green. chrome MCP: Feature #1 renders (image left, editorial copy, 3 thumbs, CTA), parallax works on scroll (desktop), stacks on mobile (`preview_resize`/window), dark OK, reduced-motion static.

- [ ] **Step 5: Commit.**
```bash
git add web-nuxt/components/home/EntityFeature.vue web-nuxt/public/img/features/ web-nuxt/pages/index.vue
git commit -m "feat(ui): EntityFeature photo-led block + Feature #1 (Trải nghiệm miệt vườn)"
```

---

## Task 5: `StorySpread.vue` + panorama image + full-bleed signature moment

**Files:** Create `web-nuxt/components/home/StorySpread.vue`; create `web-nuxt/public/img/spread/song-nuoc.webp` (panorama ~2400×1000, + 1600/900 srcset variants `-1600`/`-900`); Modify `web-nuxt/pages/index.vue` (insert spread after spotlight); `dark-overrides.css` if needed.

**Interfaces:** Consumes: `useParallax`. Produces: `<StorySpread :image="string" :srcset="string" kicker title subtitle ctaText ctaTo />` — full-bleed, breaks the container.

- [ ] **Step 1: Generate panorama.** Prompt: "a sweeping golden-hour panorama of the Mekong Delta — a wide river winding past coconut groves, fruit orchards and stilt houses, a lone sampan, misty distance" + base style; `size="1536x1024"` then Pillow crop/resize to a 2.4:1 panorama at widths 2400/1600/900 → `public/img/spread/song-nuoc.webp` (+ `-1600.webp`, `-900.webp`). Verify via Read.

- [ ] **Step 2: Implement `StorySpread.vue`** (full-bleed via `100vw` breakout; Ken Burns + parallax):
```vue
<template>
  <section class="spread">
    <div class="spread-img" ref="imgEl" :style="{ backgroundImage: `url(${image})` }" />
    <div class="spread-scrim" />
    <div class="spread-copy">
      <span class="spread-kicker">{{ kicker }}</span>
      <h2 class="spread-title">{{ title }}</h2>
      <p class="spread-sub">{{ subtitle }}</p>
      <NuxtLink v-if="ctaTo" :to="ctaTo" class="btn btn-primary">{{ ctaText }} →</NuxtLink>
    </div>
  </section>
</template>
```
- Full-bleed CSS: `.spread { position: relative; width: 100vw; margin-inline: calc(50% - 50vw); min-height: clamp(24rem, 60vh, 40rem); overflow: hidden; display: grid; place-items: center; isolation: isolate; }`.
- `.spread-img`: `position:absolute; inset:-6%; background-size:cover; background-position:center; transform: translate3d(0, var(--parallax,0), 0) scale(1.06); animation: spread-kenburns var(--dur-kenburns, 24s) var(--ease-in-out) infinite alternate;` (define keyframes: slow scale 1.06→1.12 + slight translate). Reduced-motion: `@media (prefers-reduced-motion: reduce){ .spread-img{ animation:none; transform:none } }`.
- `.spread-scrim`: token `--scrim-hero` (dark gradient for legibility).
- `.spread-copy`: centered, `--font-editorial` oversized title (white via `--text-on-dark`), max reading measure.
- `<script setup>`: props; `imgEl` ref; `useParallax(() => imgEl.value?[imgEl.value]:[], { intensity: 0.12 })`.
- srcset: use `<img>` inside `.spread-img` with `srcset`/`sizes="100vw"` `loading="lazy"` instead of background if simpler for responsive; keep aspect via object-fit cover + absolute fill.

- [ ] **Step 3: Insert in `index.vue`** after the spotlight section:
```ts
const SPREAD = { kicker: 'Vĩnh Long', title: 'Nơi vườn chạm sông', subtitle: 'Ba vùng đất — Vĩnh Long, Bến Tre, Trà Vinh — một miền phù sa, trái ngọt và những phiên chợ nổi.', ctaText: 'Khám phá vùng đất', ctaTo: '/ban-do' }
```
`<StorySpread image="/img/spread/song-nuoc.webp" v-bind="SPREAD" />`.

- [ ] **Step 4: Build + browser-verify.** Full-bleed edge-to-edge (no horizontal scroll on body), Ken Burns + parallax on scroll, legible title over scrim, mobile OK, dark OK, reduced-motion static. Confirm no CLS (fixed min-height).

- [ ] **Step 5: Commit.**
```bash
git add web-nuxt/components/home/StorySpread.vue web-nuxt/public/img/spread/ web-nuxt/pages/index.vue
git commit -m "feat(ui): StorySpread full-bleed signature moment (Ken Burns + parallax)"
```

---

## Task 6: Feature #2 ("Đặc sản OCOP", mirrored side)

**Files:** Modify `web-nuxt/pages/index.vue` (insert Feature #2 after the spread; add copy constant). Reuses `EntityFeature.vue` + `public/img/features/ocop.webp` from Task 4.

**Interfaces:** Consumes: `EntityFeature`, `productsAll` computed (existing).

- [ ] **Step 1:** Add copy constant:
```ts
const FEATURE_OCOP = { kicker: 'Đặc sản OCOP', title: 'Mang cả miền Tây về làm quà', lede: 'Dừa sáp Cầu Kè, kẹo dừa, mật ong rừng bần, gạo thơm — sản vật đạt sao OCOP, gói ghém vị quê.', ctaText: 'Xem đặc sản OCOP', ctaTo: '/ocop' }
```
Render after `<StorySpread>`: `<EntityFeature image="/img/features/ocop.webp" v-bind="FEATURE_OCOP" :thumbs="productsAll.slice(0,3)" side="right" />` (no `priority`).

- [ ] **Step 2: Build + browser-verify.** Feature #2 renders mirrored (image right), OCOP thumbs, alternates visually with Feature #1, dark/mobile OK.

- [ ] **Step 3: Commit.**
```bash
git add web-nuxt/pages/index.vue
git commit -m "feat(ui): Feature #2 (Đặc sản OCOP, mirrored)"
```

---

## Task 7: Subtraction — cut trending row, slim itineraries + personalization

**Files:** Modify `web-nuxt/pages/index.vue` (remove trending section markup + its now-unused computed if nothing else uses it; tighten itineraries + personalization sections).

**Interfaces:** none new. Keep `trending` computed only if still referenced elsewhere; otherwise remove to avoid dead code.

- [ ] **Step 1:** Remove the "Đang được quan tâm" (trending) `<section v-if="trending.length" ...>` block (~index.vue:204). Grep `trending` — if the computed is now unused, remove `const trending = ...` too (and `top`/`trending` references). If Feature thumbs want trending items, pass `trending.slice(0,3)` into a feature instead (optional) — else drop.

- [ ] **Step 2:** Slim the itineraries section: keep it but reduce to a single compact horizontal strip (fewer cards, tighter heading) — visual tighten only, no logic change. Slim personalization (recently viewed / saved): keep client-only sections but reduce vertical padding + limit to one row each (already sliced to 6/4).

- [ ] **Step 3: Build + browser-verify.** Trending row gone; page is shorter/tighter; itineraries + personalization still present but compact; no console errors (no dangling refs). Reveal still 100%.

- [ ] **Step 4: Commit.**
```bash
git add web-nuxt/pages/index.vue
git commit -m "refactor(ui): cut redundant trending row + slim itineraries/personalization (breathing room)"
```

---

## Task 8: Replace empty Community with "Câu chuyện vùng đất" editorial module

**Files:** Modify `web-nuxt/pages/index.vue` (community section: show feed when non-empty, else an always-populated editorial story built from an entity).

**Interfaces:** Consumes: `communityPosts` (existing), an entity with an image (e.g. `spotlight` or a curated pick) for the story.

- [ ] **Step 1:** Wrap the community region: `<template v-if="communityPosts.length"> ...existing feed... </template> <template v-else> <StoryLand /> </template>`. Implement `StoryLand` inline (small block, NOT a new file — it's index-specific): a compact editorial card — hero-grade region image (reuse `/img/features/river.webp` or an area image) + kicker "Câu chuyện vùng đất" + a rotating short narrative (from a small in-file array of 2–3 curated stories, each `{ title, body, to }`) + CTA. Pick the story by `currentMonth % stories.length` (deterministic, SSR-stable — no `Date.now()`).

- [ ] **Step 2:** Ensure the story block reuses existing tokens/editorial type (serif title, reading measure, drop-cap optional). Dark-safe.

- [ ] **Step 3: Build + browser-verify.** With empty feed (current prod state), the "Câu chuyện vùng đất" block renders (no more hole); if feed later has posts, the feed shows instead. Dark/mobile OK.

- [ ] **Step 4: Commit.**
```bash
git add web-nuxt/pages/index.vue
git commit -m "feat(ui): replace empty community section with Câu chuyện vùng đất editorial module"
```

---

## Task 9: Editorial typography + depth/overlap polish pass

**Files:** Modify `web-nuxt/pages/index.vue` (section CSS), possibly `web-nuxt/assets/css/editorial.css` (shared pull-quote/drop-cap if reused).

- [ ] **Step 1:** Apply consistent editorial captions under feature/spread images (small italic serif, muted, token colors). Add drop-cap to feature ledes (`.ef-lede::first-letter`) if not already. Add one pull-quote treatment where a feature has a strong summary.

- [ ] **Step 2:** Depth/overlap: let Feature images overlap the following heading slightly (negative margin / z-index) OR let a caption/kicker overlap the image edge — one or two intentional overlaps, not everywhere. Verify no clipping/overflow on mobile.

- [ ] **Step 3:** Tighten vertical rhythm: confirm the new order reads as hero → nav → what's-happening → **feature** → spotlight → **spread** → **feature** → itineraries(slim) → story → personalization → chatbot. Adjust section spacing tokens for cadence (bigger gap around the spread as a "chapter break").

- [ ] **Step 4: Build + browser-verify** full page top-to-bottom (chrome MCP screenshots at desktop + mobile widths, light + dark). Confirm the "premium editorial, not card-grid" feel; no horizontal scroll; reduced-motion static.

- [ ] **Step 5: Commit.**
```bash
git add web-nuxt/pages/index.vue web-nuxt/assets/css/editorial.css
git commit -m "polish(ui): editorial captions/drop-caps + intentional depth/overlap + vertical rhythm"
```

---

## Task 10: Deploy + full live verification (CWV, dark, mobile, motion)

**Files:** none (deploy + verify).

- [ ] **Step 1:** `cd web-nuxt && npm run build` green; run `npx vitest run` (useParallax test passes; no regressions).
- [ ] **Step 2:** Clear caches + deploy frontend: `rm -rf web-nuxt/.nuxt web-nuxt/node_modules/.cache web-nuxt/node_modules/.vite web-nuxt/.output && VL360_DEPLOY_HOST=root@66.42.57.202 bash scripts/deploy.sh --frontend`. Gate green (home/search=200).
- [ ] **Step 3: Verify live via chrome MCP** on `https://vinhlong360.vn/`:
  - Full-page screenshot desktop + mobile, light + dark → confirm features/spread/story render, imagery real, no card-row monotony.
  - Console: no hydration/error regressions (compare to baseline: was 1–2 non-blocking mismatches).
  - CWV sanity: LCP element = hero (unchanged); no layout shift on the spread (fixed min-height); parallax smooth.
  - Emulate `prefers-reduced-motion` → parallax/Ken Burns off.
- [ ] **Step 4:** Update memory ([[project-cinematic-editorial]]) with the shipped result + score reassessment. No code commit (already committed per task).

---

## Self-Review

**Spec coverage:** §1 architecture → Tasks 3,4,5,8 (components/composable). §2 section-by-section → Tasks 2 (hero),4 (F1),5 (spread),6 (F2),7 (cut/slim),8 (community); kept modules untouched by design. §3 sensory → Task 3 + applied in 4,5. §4 typography → Task 9 + inline in 4. §5 imagery → Tasks 4,5 (gen). §6 CWV → constraints + Tasks 4 (priority),5 (srcset),10 (verify). §7 sequencing → Task order = spec's 10 steps. §8 out-of-scope respected (no scroll-jacking/footer/UGC-seeding). §9 acceptance → Task 10. **No gaps.**

**Placeholder scan:** No TBD/TODO. Visual CSS is intentionally structural + browser-verified (design-iterative surface); concrete logic (useParallax, wiring, prompts, deploy cmds) is fully specified. Acceptable for a frontend-design plan.

**Type consistency:** `useParallax(() => HTMLElement[], {intensity})` used consistently in Tasks 3/4/5. `EntityFeature` props (`image,kicker,title,lede,ctaText,ctaTo,thumbs,side,priority`) consistent in Tasks 4/6. `StorySpread` props consistent in Task 5. Image paths `/img/features/*.webp`, `/img/spread/*.webp` consistent.
