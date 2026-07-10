# Wave 1 — Story-Card Foundation Implementation Plan
> STATUS (2026-07-10): done — plan đã thực thi & ship.


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the reusable foundation the whole 36-page redesign consumes — a story-hook composable, the "Story Card" redesign of `EntityCard` (the unit on ~15 grids), a shared sediment section-head class, and a no-photo hero-placeholder component.

**Architecture:** Pure-function composable (`useEntityStory`) turns existing entity attributes into a one-line story teaser + dateline, with no backend/schema change. `EntityCard` consumes it and gains editorial treatment (serif title, dateline eyebrow, tri-province rule, grain placeholder). Two shared primitives (`.sediment-head` global class, `EntityHeroPlaceholder.vue`) are added additively for later per-page waves. Everything is CSS-token-driven with dark-mode + reduced-motion parity.

**Tech Stack:** Nuxt 4 SSR, Vue 3 `<script setup>` + TS, Vitest, CSS design tokens in `web-nuxt/assets/css/` (NO Tailwind).

## Global Constraints

- CSS design tokens only (`--font-editorial`, `--font-sans`, `--text-*`, `--space-*`, `--clay-600`/`--leaf-600`/`--river-600`/`--amber-500` etc.) — NO Tailwind, NO hardcoded hex for brand colours.
- Real images are AI-gen only; ~97% of entities have no photo → the designed SVG placeholder is the default, never a "failure" fallback.
- CTA is contact-only (Zalo/phone) — no booking/cart/price-as-CTA. Price is a footnote, never a headline.
- Every new visual MUST have a `.dark` variant and MUST be neutralised under `@media (prefers-reduced-motion: reduce)`.
- NO backend/schema change — v1 only re-sequences attributes already present on the entity object.
- Provenance before price: for `product`/`craft_village`, the teaser leads with maker/place, not price.
- Verify each task: `cd web-nuxt && npm run build` passes + `npx vitest run` green + (for visual tasks) preview-probe. **After any rebuild, clear the preview service worker before probing** (`navigator.serviceWorker.getRegistrations().then(r=>r.forEach(x=>x.unregister()))` + `caches.keys().then(k=>k.forEach(x=>caches.delete(x)))`).
- Scoped/additive: do NOT remove existing `.home`/`.ce-area`/`.ce-ward` sediment rules in Wave 1 (later waves migrate them). `EntityCard` change is high-blast-radius (~15 pages) → ship + review before dependent waves.

---

### Task 1: `useEntityStory` composable (hook teaser + dateline + provenance)

**Files:**
- Create: `web-nuxt/composables/useEntityStory.ts`
- Test: `web-nuxt/tests/entityStory.test.ts`

**Interfaces:**
- Consumes: `AREA_META` from `~/composables/useConstants` (shape: `Record<string,{name:string,emoji:string}>`).
- Produces:
  - `entityStoryTeaser(entity: Record<string, any>): string` — one-line story hook via fallback chain; provenance-prefixed for product/craft_village; `''` if nothing usable.
  - `entityDateline(entity: Record<string, any>, typeLabel: string): string` — `"{TYPELABEL} · {AREA}"` (area omitted when unknown).

- [ ] **Step 1: Write the failing test**

Create `web-nuxt/tests/entityStory.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { entityStoryTeaser, entityDateline } from '../composables/useEntityStory'

describe('entityStoryTeaser', () => {
  it('prefers attributes.hook over everything', () => {
    expect(entityStoryTeaser({ type: 'dish', attributes: { hook: 'Nước lèo nấu từ mắm bò hóc.' }, description: 'x'.repeat(60), summary: 's' }))
      .toBe('Nước lèo nấu từ mắm bò hóc.')
  })
  it('falls back highlight → famous_for → first sentence → summary', () => {
    expect(entityStoryTeaser({ type: 'attraction', attributes: { highlight: 'H' } })).toBe('H')
    expect(entityStoryTeaser({ type: 'attraction', attributes: { famous_for: 'F' } })).toBe('F')
    expect(entityStoryTeaser({ type: 'dish', attributes: { signature_dish: 'Bún nước lèo' } })).toBe('Bún nước lèo')
    expect(entityStoryTeaser({ type: 'attraction', description: 'Câu đầu tiên ở đây. Câu hai.' })).toBe('Câu đầu tiên ở đây.')
    expect(entityStoryTeaser({ type: 'attraction', summary: 'Chỉ có summary.' })).toBe('Chỉ có summary.')
    expect(entityStoryTeaser({ type: 'attraction' })).toBe('')
  })
  it('prefixes provenance (place) for product/craft_village, before any price', () => {
    expect(entityStoryTeaser({ type: 'product', attributes: { highlight: 'Ngọt thanh' }, place_name: 'Vườn bưởi Bình Minh' }))
      .toBe('Vườn bưởi Bình Minh — Ngọt thanh')
    // no double-prefix when hook already names the place
    expect(entityStoryTeaser({ type: 'product', attributes: { hook: 'Vườn bưởi Bình Minh trồng theo lối xưa.' }, place_name: 'Vườn bưởi Bình Minh' }))
      .toBe('Vườn bưởi Bình Minh trồng theo lối xưa.')
  })
})

describe('entityDateline', () => {
  it('joins type label and area name', () => {
    expect(entityDateline({ area: 'ben-tre' }, 'Đặc sản')).toBe('Đặc sản · Bến Tre')
  })
  it('reads place_area and omits area when unknown', () => {
    expect(entityDateline({ place_area: 'tra-vinh' }, 'Điểm đến')).toBe('Điểm đến · Trà Vinh')
    expect(entityDateline({}, 'Điểm đến')).toBe('Điểm đến')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web-nuxt && npx vitest run tests/entityStory.test.ts`
Expected: FAIL — "Failed to resolve import '../composables/useEntityStory'".

- [ ] **Step 3: Write minimal implementation**

Create `web-nuxt/composables/useEntityStory.ts`:

```ts
// Turns attributes already present on an entity into a one-line STORY HOOK + a dateline
// eyebrow. No backend/schema change — pure re-sequencing of existing fields.
// Fallback chain (narrative §1): attributes.hook → attributes.highlight →
// famous_for / signature_dish → first sentence of description → summary.
import { AREA_META } from '~/composables/useConstants'

const PROVENANCE_TYPES = new Set(['product', 'craft_village'])

function firstSentence(s: string): string {
  const t = (s || '').trim()
  if (!t) return ''
  const m = t.split(/(?<=[.!?…])\s/)[0]
  return (m || t).trim()
}

/** One-line story hook. '' when nothing usable. Provenance-prefixed for product/craft_village. */
export function entityStoryTeaser(entity: Record<string, any>): string {
  const a = entity?.attributes || {}
  let teaser = (a.hook || a.highlight || a.famous_for || a.signature_dish || '').toString().trim()
  if (!teaser) teaser = firstSentence(entity?.description || '')
  if (!teaser) teaser = (entity?.summary || '').toString().trim()
  if (!teaser) return ''
  // provenance-first (place before price/anything): prefix maker/place if not already named
  if (PROVENANCE_TYPES.has(entity?.type)) {
    const place = (entity?.place_name || entity?.placeName || a.origin || a.maker || '').toString().trim()
    if (place && !teaser.includes(place)) teaser = `${place} — ${teaser}`
  }
  return teaser
}

/** "{TYPE LABEL} · {AREA}" — area omitted when unknown. */
export function entityDateline(entity: Record<string, any>, typeLabel: string): string {
  const key = entity?.area || entity?.place_area || ''
  const area = key && (AREA_META as Record<string, { name: string }>)[key]?.name
  return area ? `${typeLabel} · ${area}` : typeLabel
}

export default function useEntityStory() {
  return { entityStoryTeaser, entityDateline }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web-nuxt && npx vitest run tests/entityStory.test.ts`
Expected: PASS (2 suites, all cases).

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/composables/useEntityStory.ts web-nuxt/tests/entityStory.test.ts
git commit -m "feat(story): useEntityStory — hook-fallback teaser + dateline (v1, no schema change)"
```

---

### Task 2: `EntityCard` → Story Card

**Files:**
- Modify: `web-nuxt/components/EntityCard.vue` (template: dateline eyebrow, tri-province rule, story teaser, grain overlay; `<script setup>`: import + computeds; `<style scoped>`: serif name, dateline, rule, grain)
- Modify: `web-nuxt/tests/smoke.test.ts` (add Story-Card source assertions)

**Interfaces:**
- Consumes: `entityStoryTeaser`, `entityDateline` from Task 1; existing `typeMeta`, `generateCategoryPlaceholder/Icon`.
- Produces: the new grid card look every catalog/discovery/detail-adjacent page inherits.

- [ ] **Step 1: Add the composable import + computeds to `<script setup>`**

In `web-nuxt/components/EntityCard.vue`, after the existing import block (line 70, `import { generateCategoryPlaceholder, generateCategoryIcon } ...`) add:

```ts
import { entityStoryTeaser, entityDateline } from '~/composables/useEntityStory'
```

Then after `const cardSummary = computed(...)` (ends line 105) add:

```ts
const storyTeaser = computed(() => entityStoryTeaser(props.entity) || cardSummary.value)
const dateline = computed(() => entityDateline(props.entity, typeMeta.value.label))
```

- [ ] **Step 2: Update the template — dateline eyebrow, serif name, tri-province rule, story teaser, grain**

Replace the cover-tag on BOTH covers (lines 7 and 21, the `<span class="cover-tag" ...>{{ typeMeta.label }}</span>`) with the dateline eyebrow:

```html
<span class="cover-tag cover-dateline" :class="`cat-${typeMeta.cat}`">{{ dateline }}</span>
```

Add a grain overlay inside the generated-cover `<div>` (line 18), immediately after the opening tag's `:style` element — i.e. as the first child before the `<NuxtLink>` on line 19:

```html
<span class="cover-grain" aria-hidden="true"></span>
```

Replace the card body block (lines 26-28: `card-type`, `card-name`, `summary`) with:

```html
      <span class="card-dateline">{{ dateline }}</span>
      <h3 class="card-name">{{ entity.name }}</h3>
      <span class="card-rule" aria-hidden="true"></span>
      <p class="summary card-teaser">{{ storyTeaser }}</p>
```

(Leave lines 29-49 — place, meta, rating, amenities, badges — unchanged.)

- [ ] **Step 3: Add scoped CSS for the Story-Card treatment**

In the `<style scoped>` block, replace the line `.card-type { display: none; }` (line 228) with:

```css
/* ── Story Card (Wave 1 keystone) — editorial treatment on every grid card ── */
.card-type { display: none; }
.card-name { font-family: var(--font-editorial); font-weight: 600; letter-spacing: -.01em; }
/* dateline eyebrow — small-caps, hairline accent top border, NOT a solid pill */
.card-dateline {
  display: inline-block; margin-bottom: 2px;
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  letter-spacing: .1em; text-transform: uppercase; color: var(--muted);
}
/* the on-cover dateline stays legible on imagery — keep the readable chip form there */
.cover-dateline { text-transform: uppercase; letter-spacing: .08em; }
/* tri-province "sediment" rule between name and teaser (card-scale sediment tick) */
.card-rule {
  display: block; width: 26px; height: 2px; border-radius: 2px; margin: 5px 0 6px;
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .card-rule { background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }
.card-teaser { color: var(--muted); }
/* grain overlay turns the flat placeholder gradient into an intentional illustration */
.cover-grain {
  position: absolute; inset: 0; z-index: 1; pointer-events: none;
  background-image: var(--grain); background-size: 120px 120px; opacity: .06; mix-blend-mode: normal;
}
.dark .cover-grain { opacity: .09; }
```

- [ ] **Step 4: Update the smoke test to lock the Story-Card contract**

In `web-nuxt/tests/smoke.test.ts`, find the EntityCard smoke assertions (search for `EntityCard.vue`); add these assertions inside that test (or create one `it('EntityCard is a Story Card', ...)`):

```ts
const ec = src('components/EntityCard.vue')
expect(ec).toContain("entityStoryTeaser")
expect(ec).toContain('class="card-rule"')
expect(ec).toContain('card-dateline')
expect(ec).toContain('cover-grain')
expect(ec).toContain('font-family: var(--font-editorial)') // serif card name
```

(Use the existing `src()` helper already imported in smoke.test.ts.)

- [ ] **Step 5: Run tests + build**

Run: `cd web-nuxt && npx vitest run tests/smoke.test.ts --hookTimeout=30000 && npm run build 2>&1 | tail -2`
Expected: smoke PASS, build "✨ Build complete!".

- [ ] **Step 6: Preview-probe verify (visual contract)**

Restart preview, clear the service worker + caches (see Global Constraints), navigate to `/kham-pha/am-thuc` (a grid page), then probe a card:

```js
(() => { const c=document.querySelector('.card .card-name'); const dl=document.querySelector('.card .card-dateline'); const rule=document.querySelector('.card .card-rule');
  return JSON.stringify({ nameSerif: c ? /Fraunces|serif/i.test(getComputedStyle(c).fontFamily) : null, hasDateline: !!dl, hasRule: !!rule, ruleW: rule?getComputedStyle(rule).width:null, overflow: document.documentElement.scrollWidth-document.documentElement.clientWidth }); })()
```
Expected: `nameSerif:true, hasDateline:true, hasRule:true, ruleW:"26px", overflow:0`. Also probe `.dark` (add `document.documentElement.classList.add('dark')`) — rule + grain still present, no contrast break.

- [ ] **Step 7: Commit**

```bash
git add web-nuxt/components/EntityCard.vue web-nuxt/tests/smoke.test.ts
git commit -m "feat(story): EntityCard -> Story Card — serif title, dateline eyebrow, tri-province rule, story teaser, grain placeholder"
```

---

### Task 3: Shared `.sediment-head` section-head class

**Files:**
- Modify: `web-nuxt/assets/css/components.css` (append the shared class near the end, before any `@media`/print block)
- Test: `web-nuxt/tests/smoke.test.ts` (assert the class exists)

**Interfaces:**
- Produces: global class `.sediment-head` — any page adds it to a `.section-head`/heading wrapper to get the serif + river→amber→clay vertical tick (the phù-sa section signature), without re-implementing the `.home`/`.ce-*` scoped copies.

- [ ] **Step 1: Add the shared class**

Append to `web-nuxt/assets/css/components.css`:

```css
/* ── Shared phù-sa section head (Wave 1 foundation; pages opt in with .sediment-head) ── */
.sediment-head h2, h2.sediment-head {
  font-family: var(--font-editorial); font-weight: 600; letter-spacing: -.01em;
  position: relative; padding-left: var(--space-4);
}
.sediment-head h2::before, h2.sediment-head::before {
  content: ""; position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 4px; height: 1.05em; border-radius: var(--radius-full);
  background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .sediment-head h2::before, .dark h2.sediment-head::before {
  background: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%);
}
```

- [ ] **Step 2: Add smoke assertion**

In `web-nuxt/tests/smoke.test.ts` add (near other CSS assertions):

```ts
expect(src('assets/css/components.css')).toContain('.sediment-head')
```

- [ ] **Step 3: Build + test**

Run: `cd web-nuxt && npx vitest run tests/smoke.test.ts --hookTimeout=30000 && npm run build 2>&1 | tail -2`
Expected: PASS + build complete.

- [ ] **Step 4: Commit**

```bash
git add web-nuxt/assets/css/components.css web-nuxt/tests/smoke.test.ts
git commit -m "feat(story): shared .sediment-head section-head class (foundation for per-page waves)"
```

---

### Task 4: `EntityHeroPlaceholder.vue` (no-photo hero)

**Files:**
- Create: `web-nuxt/components/EntityHeroPlaceholder.vue`
- Test: `web-nuxt/tests/smoke.test.ts` (assert component renders the pieces)

**Interfaces:**
- Consumes: `generateCategoryPlaceholder`, `generateCategoryIcon` from `~/composables/useCategoryPlaceholder`.
- Produces: `<EntityHeroPlaceholder :id="entity.id" :cat="typeMeta.cat" />` — a full-bleed hash-unique hero backdrop (gradient + off-centre motif + grain + sediment wash + honest microcopy) for detail/hero no-photo states (consumed by Wave-2 detail work).

- [ ] **Step 1: Create the component**

Create `web-nuxt/components/EntityHeroPlaceholder.vue`:

```vue
<template>
  <div class="ehp" :class="`cat-${cat}`" :style="{ backgroundImage: bg }" role="img" :aria-label="`Ảnh minh hoạ theo tông màu ${label}`">
    <span class="ehp-grain" aria-hidden="true"></span>
    <span class="ehp-wash" aria-hidden="true"></span>
    <span class="ehp-motif" aria-hidden="true" v-html="motif"></span>
    <span class="ehp-note">Ảnh minh hoạ theo tông màu đặc trưng — chưa có ảnh thật cho nơi này.</span>
  </div>
</template>

<script setup lang="ts">
import { generateCategoryPlaceholder, generateCategoryIcon } from '~/composables/useCategoryPlaceholder'
const props = defineProps<{ id: string | number; cat: string; label?: string }>()
const bg = computed(() => generateCategoryPlaceholder(props.id, props.cat))
const motif = computed(() => generateCategoryIcon(props.cat))
const label = computed(() => props.label || '')
</script>

<style scoped>
.ehp {
  position: relative; width: 100%; height: 100%; min-height: 100%;
  background-size: cover; background-position: center; overflow: hidden; isolation: isolate;
}
.ehp-grain { position: absolute; inset: 0; z-index: 1; pointer-events: none;
  background-image: var(--grain); background-size: 140px 140px; opacity: .07; }
.dark .ehp-grain { opacity: .1; }
/* horizontal river→amber→clay sediment wash, low opacity, anchored bottom */
.ehp-wash { position: absolute; inset: 0; z-index: 1; pointer-events: none;
  background: linear-gradient(105deg, rgba(51,100,110,.28) 0%, rgba(232,163,61,.14) 50%, rgba(156,61,34,.24) 100%);
  mix-blend-mode: soft-light; }
/* oversized off-centre category motif bleeding off the right edge */
.ehp-motif { position: absolute; right: -6%; bottom: -8%; z-index: 1; width: 46%; max-width: 320px;
  color: rgba(255,255,255,.5); opacity: .5; }
.ehp-motif :deep(svg) { width: 100%; height: auto; display: block; }
.ehp-note { position: absolute; left: var(--space-4); bottom: var(--space-3); z-index: 2;
  font-size: var(--text-2xs); color: rgba(255,255,255,.82); text-shadow: 0 1px 3px rgba(0,0,0,.45);
  max-width: 62%; line-height: 1.3; }
@media (prefers-reduced-motion: reduce) { .ehp { } }
</style>
```

- [ ] **Step 2: Add smoke assertion**

In `web-nuxt/tests/smoke.test.ts`:

```ts
const ehp = src('components/EntityHeroPlaceholder.vue')
expect(ehp).toContain('generateCategoryPlaceholder')
expect(ehp).toContain('ehp-motif')
expect(ehp).toContain('chưa có ảnh thật')
```

- [ ] **Step 3: Build + test**

Run: `cd web-nuxt && npx vitest run tests/smoke.test.ts --hookTimeout=30000 && npm run build 2>&1 | tail -2`
Expected: PASS + build complete. (Component is standalone; Nuxt auto-imports it — no page wiring in Wave 1.)

- [ ] **Step 4: Commit**

```bash
git add web-nuxt/components/EntityHeroPlaceholder.vue web-nuxt/tests/smoke.test.ts
git commit -m "feat(story): EntityHeroPlaceholder — phù-sa no-photo hero (foundation for detail wave)"
```

---

## Deploy (after all 4 tasks reviewed)

- [ ] Build once, deploy frontend, verify grid card live:

```bash
cd /c/Code/vinhlong360
VL360_DEPLOY_HOST=root@66.42.57.202 bash scripts/deploy.sh --frontend 2>&1 | tail -10   # builds + ships
```
Expected: `home=200 … public_api_homepage=200 … DONE`. Then curl a grid page's inlined CSS or probe prod for `.card-rule` to confirm the Story Card shipped.

---

## Self-Review

- **Spec coverage:** Task 1 = hook-fallback composable + dateline (narrative §1) ✓. Task 2 = Story Card §2 (serif title, dateline eyebrow, tri-province rule, story teaser provenance-first, grain) ✓. Task 3 = shared sediment-head partial ✓. Task 4 = phù-sa hero placeholder ✓. The "one curiosity affordance" discipline is deferred (existing informative badges kept — they are data, not decoration; a later pass can consolidate).
- **No placeholders:** every step has exact code/paths/commands ✓.
- **Type consistency:** `entityStoryTeaser`/`entityDateline` signatures identical across Task 1 (def), Task 2 (use), and tests ✓. `EntityHeroPlaceholder` props `{id,cat,label?}` consistent ✓.
- **Blast radius note:** Task 2 touches a component on ~15 pages — the smoke assertions + preview-probe (light + dark) are the gate; deploy only after review.
