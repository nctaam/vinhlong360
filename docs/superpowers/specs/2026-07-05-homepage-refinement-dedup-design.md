# Homepage Refinement — De-duplicate, Separate Roles, Trim Cruft

**Date:** 2026-07-05
**Scope:** `web-nuxt/pages/index.vue`, `web-nuxt/composables/useJourneyActions.ts` (+ test), optional `web-nuxt/components/ItineraryCard.vue`
**Type:** Frontend-only refinement (no backend, no schema, no data migration). Normal frontend build + `--frontend` deploy. **MUST NOT build with `API_BASE=public`** (proxy-loop outage — see [[project-cinematic-editorial]]).

---

## Problem (from live Chrome audit)

The homepage answers *"what should I do now?"* **four times** in the first three screens (hero feature card + hero pills + decision index 01–04 + journey rail), and they all draw from the same tiny "current" entity pool — so the **same entities repeat 2–4×**:

| Entity | Appears in | Count |
|---|---|---|
| Cua cốm Duyên Hải (`heroFeature`) | hero card · decision card #3 · Trải nghiệm thumbs | **3–4×** |
| Lễ vía Tống Phước Hiệp (`firstUpcomingEvent`) | decision card #1 · journey rail · events hero | **3×** |
| Cô Diễm (`firstDish`) | decision card #4 · Quán ngon list | **2×** |
| Ốc Gạo Cồn Phú Đa (`firstSeasonal`) | decision card #2 · seasonal scroll-row | **2×** |

Root causes in code:
- `heroFeature` (index.vue:555) feeds the hero card **and** decision card #3 (`618–628`) **and** `FEATURE_EXPERIENCE` thumbs (`experiences.slice(0,3)`, `165`).
- `homeJourneyActions` (`658`) calls `homepageDecisionActions()` with `heroFeatureName`/`upcomingEventName` → the rail structurally echoes the index (`useJourneyActions.ts:173–193`).
- Downstream lists (`seasonal`, `topDishes`) render their full arrays including the item already pinned in the decision index.

Other cruft: hero pills duplicate the 6 category tiles; the bottom personalization cluster is **3 stacked sections** (`Xem gần đây` + `Đã lưu gần đây` + `Có thể bạn quan tâm`) where recently-viewed renders **full-width gradient placeholder covers** (the most AI-slop-looking element); itinerary cards all show one shared area illustration.

---

## Approved decisions (user, 2026-07-05)

1. **Decision layer:** keep both index 01–04 *and* the journey rail, but **separate their roles** — index = editorial (season/event/food, for everyone incl. SEO); rail = **personal-only** (from the user's own saved/recent), with the editorial-echo actions removed.
2. **Bottom personalization:** merge the stacked blocks into **one compact "Dành cho bạn" strip** with a layout that tolerates image-less entities (small thumbnail/icon, **no full-width gradient cover**).
3. **Entity de-dup:** downstream sections **exclude entities already shown** in the top zone (hero + decision index).
4. **Hero pills:** **remove entirely** — the 6 category tiles right below already handle category navigation.

---

## Design

### 1. Decision index — drop the `heroFeature` card (`index.vue`)

In `homeDecisionCards` (590–656), **delete the `heroFeature` branch** (618–628, the `title:'Bắt đầu lịch trình'` card). The remaining signals are `firstUpcomingEvent` → `firstSeasonal` → `firstDish`, and the existing `< 4` map-fallback (643–653) tops it to four **distinct** decision paths:

`01 Có lịch gần nhất` · `02 Đang vào mùa` · `03 Ăn gì hôm nay` · `04 Mở bản đồ`

The hero card already exposes the `heroFeature` "Thêm vào lịch trình" CTA (`index.vue:30`), so that intent is not lost. Heading `"Hôm nay bạn muốn bắt đầu thế nào?"` stays (smoke-test asserted).

### 2. Journey rail → personal-only (`useJourneyActions.ts` + `index.vue`)

Refactor `homepageDecisionActions` (148–227) to emit **only actions derived from the user's own state**:

- **Keep:** the logged-in `savedCount > 0` branch → "Tiếp tục từ mục đã lưu" (`164–172`); the `recentCount > 0` branch → "Nối tiếp điểm vừa xem" (`195–204`).
- **Remove:** the `else if heroFeaturePlannerPath` fallback (`173–182`, "Biến gợi ý thành lịch trình" — echoes hero/index); the `upcomingEventPath` branch (`184–193`, "Canh lịch gần nhất" — echoes decision card #1); the always-on `home-map` action (`206–213`, generic — covered by tiles); the `communityPostCount` action (`215–224`, generic — covered by the community section).
- **Signature:** drop the now-unused `heroFeature*`, `upcomingEvent*`, `currentMonth`, `communityPostCount` inputs; keep `{ isLoggedIn, savedCount, recentCount }`. Update the `index.vue` call site (658–671) to pass only those.
- **Result:** anon / first-time visitors → `[]` → rail hidden (it is already `v-if=…length` + `<ClientOnly>`). Returning users with history → 1–2 personal "resume" actions. No entity echoes the index.
- **Copy:** retitle the rail to reflect the personal role — `title="Tiếp tục hành trình của bạn"`, `subtitle="Từ những gì bạn đã lưu và vừa xem."` (replaces the "Decision engine ưu tiên…" line, `index.vue:75–76`).

### 3. Entity de-dup helpers (`index.vue`)

Add computed excluders (pure, SSR-deterministic) and use them where sections currently render full arrays:

```ts
// Entities already surfaced in the top zone (hero + decision index) or the spotlight band,
// so downstream grids don't repeat them. Pure computed → SSR/CSR identical.
const experienceThumbs = computed(() =>
  experiences.value.filter((e:any) => e.id !== heroFeature.value?.id && e.id !== spotId.value).slice(0, 3))
const ocopThumbs = computed(() =>
  productsAll.value.filter((p:any) => p.id !== spotId.value).slice(0, 3))
const topDishesList = computed(() =>
  topDishes.value.filter((d:any) => d.id !== firstDish.value?.id))
const seasonalList = computed(() => {
  const rest = seasonal.value.filter((e:any) => e.id !== firstSeasonal.value?.id)
  return rest.length ? rest : seasonal.value   // never filter the row to empty
})
```

Wire-up:
- `FEATURE_EXPERIENCE` block (161–167): `:thumbs="experienceThumbs"` (was `experiences.slice(0,3)`).
- `FEATURE_OCOP` block (228–233): `:thumbs="ocopThumbs"` (was `productsAll.slice(0,3)`).
- Quán ngon (197–215): `v-if="topDishesList.length"` + `v-for="d in topDishesList"`.
- Seasonal row (151–156): `v-for="e in seasonalList"`.

The events **hero** (canonical home of `firstUpcomingEvent`) and the spotlight **band** (canonical home of `spotlight`) keep their entity — those are the entity's rightful section, and the decision index / rail are the shortcuts that now defer to them.

### 4. Remove hero pills (`index.vue`)

- Template: delete `.hero-pills` block (14–16).
- Script: delete `DEFAULT_HERO_PILLS` (397–404) and `heroPills` (405).
- CSS: delete the now-dead `.hero-pills` / `.hero-pill` rules.
- Leaves the hero as masthead + subtitle + search (cleaner, less duplication with tiles).

### 5. Merge personalization → one "Dành cho bạn" strip (`index.vue`)

Replace the three stacked sections (328–371: `Xem gần đây`, `Đã lưu gần đây`, `LazySmartRecommendations`) with **one** `<ClientOnly>` section — the `LazySmartRecommendations` usage is removed from the homepage (the component stays for detail/saved pages):

- Build `forYou` = dedup-by-id merge, in priority order, of: `recentItems` (viewed) + `favorites` (saved) + `useContextualRecommendations({context:'home'})` items (only when the `ai_recommendations` flag is on; contributes only *new* ids). Cap ~8. Normalize each source to `{ id, name, type, image, to }`.
- Render a **compact horizontal `scroll-row` of chips**. Each chip:
  - thumbnail ~64px: real image if `item.image`/`item.images?.[0]`, else a **small** category-tinted icon tile (reuse `generateCategoryIcon(cat)` at 64px) — **not** the 320×180 `cover-generated` gradient.
  - name (1–2 lines) + small type label.
- Heading `Dành cho bạn`, subtitle `Nội dung bạn vừa xem, đã lưu và gợi ý theo bạn.`
- Section hidden when `forYou` empty (anon/first-timers).

This collapses 3 sections → 1, kills the gradient covers, and de-duplicates with the now-personal rail (rail = forward *actions*; strip = the *items*).

### 6. (Optional) Itinerary cover variety (`ItineraryCard.vue`)

`coverSrc` (47) maps every itinerary in an area to one shared `/img/cat/{…}.jpg`, so homepage itineraries (mostly `lien-vung`) all show the same illustration. **Optional, low-priority:** prefer a real cover from the payload if present (`itinerary.cover` / `itinerary.image` / first-stop image) before falling back to the area illustration. If the `/api/homepage` itinerary objects carry no such field, this is a no-op — leave as-is and note the limitation. Not a blocker for this refinement.

---

## File structure

- `web-nuxt/composables/useJourneyActions.ts` — refactor `homepageDecisionActions` (personal-only) + signature.
- `web-nuxt/tests/journeyActions.test.ts` **(new)** — behavioral unit test for the refactor (§B3: test before refactoring untested logic).
- `web-nuxt/pages/index.vue` — decision-card cut, dedup computeds, pills removal, personalization merge, rail copy + call-site.
- `web-nuxt/components/ItineraryCard.vue` — optional cover preference.
- `web-nuxt/tests/smoke.test.ts` — unchanged (asserted strings all survive: hero card keeps `plannerAddPath(heroFeature.id)`; `homeDecisionCards`/`homeJourneyActions`/`homepageDecisionActions`/`JourneyActionRail`/heading all remain).

## Verification

1. `npx vitest run tests/journeyActions.test.ts` — new behavioral test passes (rail emits only personal actions; no `home-event`/`home-start-planner`/`home-map`/`home-community`).
2. `npm run test` (or `npx vitest run`) — full FE suite green incl. `smoke.test.ts`.
3. `npm run build` — succeeds (run in background; cold build > 4 min).
4. Dev/live check via Chrome: each of Cua cốm / Lễ vía / Cô Diễm / Ốc Gạo appears **once** in the top zone; no hero pills; one "Dành cho bạn" strip with no full-width gradient covers; rail hidden for anon, personal for returning users; 0 console errors / 0 hydration mismatch.
5. Deploy `--frontend` (localhost API_BASE default — **never** public), re-verify live.

## Invariants respected

- CTA contact/discover only — no booking/price form (§1.4). AI images only where added (§B6 — none added here). CSS tokens, no Tailwind. Reduced-motion / dark-parity unchanged (reusing existing card/scroll-row styles). No paid service, no data op, no schema change. §B3 satisfied by the new behavioral test before the composable refactor.
