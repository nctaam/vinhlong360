# Planner + Map — `tao-lich-trinh.vue` (6.0) + `ban-do.vue` (6.0)

> **STATUS (2026-07-07): concept Ý TƯỞNG — KHÔNG thực thi nguyên văn.** Viết TRƯỚC declutter 3 đợt (ship 2026-07-07) và TRƯỚC chốt định vị 2026-07-06. Khi xung đột: code hiện tại + CLAUDE.md thắng. Trước khi thực thi bất kỳ mục nào: (1) dẹp mọi copy "miền Tây / ba tỉnh" — dùng khung tỉnh-Vĩnh-Long-mới; (2) KHÔNG dùng địa danh ngoài tỉnh (Cái Bè, Lai Vung… thuộc Đồng Tháp); (3) KHÔNG claim "đã xác minh"/quy mô đội ngũ; (4) re-ground line-number trên code hiện tại. Cảnh báo đầy đủ: 00-narrative-system.md.


> **Unit thesis in one line:** the map stops being a locator you consult and becomes a **surface you browse the Delta on**; the planner stops being a form with arrow-buttons and becomes **a river journey you physically assemble**, stop by stop, like beads on a string of nước ròng/nước lớn (tide).

Both pages are **interaction-heavy utilities**, the opposite of the hero-driven entity pages. The CE language cannot just decorate them — it has to survive contact with drag handles, filter chips, popups, and live map tiles. The design problem here is: *how does an editorial, sediment-toned platform make a Leaflet/MapLibre canvas and a stateful list-builder feel like the same world as the cinematic hero pages, without breaking usability?* The answer is: **treat chrome (frames, controls, empty states, the route ribbon) as CE, and leave the map/interaction internals fast and legible.**

---

## 1. STORY ANGLE

**`ban-do.vue` — Bản đồ**
The map is not "here are pins on a map." The story is: *Vĩnh Long mới is a delta of water and alluvium — the map is a living cù lao/kênh rạch landscape, and every marker is a place someone already loves.* The map should feel like unrolling a hand-drawn river map where you can *wander* — pan along kênh rạch, watch clusters bloom into chợ nổi and vườn trái cây as you zoom, discover something you didn't search for. Browsing IS the destination, not a means to search.

**`tao-lich-trinh.vue` — Tạo lịch trình**
The story is *the traveler as author of their own hành trình* (journey) — not filling a form, but stringing together a chuỗi ngày (string of days) the way a Delta boat threads kênh rạch from one bến (dock) to the next. Every stop card should read like a diary entry stub: nơi đến, giờ, ghi chú — a page from a travel journal being written in real time. The reorder interaction (currently arrow buttons) should feel like *moving a bead on a string*, not editing a database row.

---

## 2. CINEMATIC HERO / THESIS

**Map page hero — replace the generic `.catalog-hero` icon+text bar with a "river unrolling" thesis strip:**
- Height ~180px (not full-bleed — this is a utility page, restraint matters), sand-50 ground, a thin animated (CSS, no JS) horizontal band along the bottom third: a hand-drawn-style SVG river line (reuse the wavy-line motif already in `.premium-empty-state::before`) tinted river-600 at 8-10% opacity, drifting slowly left via `background-position` keyframe (30s loop, `prefers-reduced-motion` freezes it).
- Editorial dateline eyebrow above the H1: `BẢN ĐỒ SỐNG — 1.730 ĐIỂM ĐẾN` (wide-tracked caps, hairline rule), replacing the emoji-in-a-circle icon pattern.
- H1 in `--font-editorial`: **"Một dòng sông, ngàn điểm dừng"** ("One river, a thousand stops") as the actual page headline, with "Bản đồ" demoted to a small kicker/subtitle underneath for wayfinding/SEO clarity.
- The live pin-count (`{{ visibleCount }} địa điểm`) is pulled UP into the hero as a large animated counter (count-up on first load, CSS `@property` or simple JS tick) — turning a utility stat into a "look how much there is to discover" flex.

**Planner page hero — the "empty journal" thesis:**
- Same restrained hero band, but the motif is a dotted/dashed path (a route line, not a river) drawn left-to-right, suggesting an itinerary about to be written.
- H1: **"Vẽ hành trình của riêng bạn"** ("Draw your own journey"), kicker: "TẠO LỊCH TRÌNH".
- The existing 3-step guided indicator (`planner-steps`) stays functionally as-is but gets restyled as a **"trang nhật ký" (journal page) tab strip** — see Typography section — echoing a boarding pass / travel-journal aesthetic rather than a generic wizard.

---

## 3. LAYOUT + RHYTHM

**Map (`ban-do.vue`):**
- Keep the single-column full-width map — that's correct for a browsing surface — but change the *framing*: the map canvas gets a **deckle-edge / torn-paper card treatment** (a subtle SVG mask or `clip-path: polygon()` micro-jitter on the corners, 4-6px amplitude) so it reads as "a map laid on a table," not "an embedded iframe." This is the single highest-leverage move to make the map feel designed rather than bolted-on.
- Filter chips row (`map-filters`) becomes a **sticky "legend rail"** on desktop (≥1024px): pin to the left edge of the map as a translucent glass strip overlaying the map's left margin (like a real map's legend box), collapsing back to the current horizontal chip row below the hero on mobile/tablet. This turns filtering from "form above the map" into "part of the map artifact."
- The `map-list-fallback` grid (the no-JS/reduced-motion pin list) gets promoted from an afterthought into a genuine **"Đang hiện trên bản đồ" editorial rail** below the map on ALL viewports (not just fallback) — a horizontally scrollable strip of the visible pins as small cards, so users get a scannable list *and* a map, reinforcing "browse," not just "locate." (Currently it only shows conditionally; making it a permanent companion rail turns the page into browsing + confirming, a well-established travel-platform pattern per prior research.)
- Rhythm: hero → legend-rail+map (the dominant visual mass) → "on the map right now" rail → thin footer hint ("Không thấy nơi bạn tìm? [Tìm kiếm →]" linking to search) for information-scent continuity.

**Planner (`tao-lich-trinh.vue`):**
- Keep the 2-pane picker+builder layout (it's structurally sound), but re-balance proportions: picker 34% / builder 66% on desktop, and make the **builder's stop-list the visual protagonist** — right now both panes compete equally.
- Introduce a **persistent "spine"**: a vertical sediment-tick line (river→amber→clay, the established signature) running down the LEFT of the stop-list, with stop-number roundels sitting ON the spine — turning `stop-connector` (currently a flat opacity-25 bar) into the actual brand signature element instead of a generic gray line. This single change ties the planner into the CE family visually.
- Add a **date/day-grouping affordance**: if a plan spans multiple days (time field suggests time-of-day only today), let stops visually cluster under "Ngày 1 / Ngày 2" dividers — journal-page pacing instead of one long flat list. (Feasible: pure client-side grouping heuristic or explicit optional `day` field — additive, no backend change required per B2.)
- Route-map section and saved-plans section keep their current position (bottom of builder) but get card-ized with the same torn-edge/deckle treatment as the map page for family resemblance.

---

## 4. TYPOGRAPHY

- H1 on both pages: `--font-editorial` (Fraunces), large fluid size (`--text-3xl`+), same weight/tracking as other CE heroes — currently both pages use a plain default H1 inside `.catalog-hero-inner`, which is the single biggest typographic tell that these pages are "pre-CE." Swap immediately.
- Dateline eyebrow: `--font-sans` (Inter), uppercase, `letter-spacing: .12em`, `font-size: var(--text-xs)`, sitting above a 1px hairline — matches the established pattern from index.vue.
- Stop-card / picker-item names: keep Inter (sans) — these are dense, scannable UI list rows, serif would hurt legibility at that density. **Editorial serif is reserved for headline moments (hero H1, saved-plan titles when rendered large, section H3s like "Bản đồ lộ trình")** — everything transactional (inputs, buttons, chip labels) stays sans. This is the correct CE discipline: serif marks *narrative* moments, sans handles *tool* moments.
- Section H3s ("Bản đồ lộ trình", "Lịch trình đã lưu", "Đang hiện trên bản đồ") promoted to `--font-editorial` italic, small-caps-esque treatment, to give the utility sections a whisper of the editorial voice without overloading them.
- Plan title input (`builder-title`) — when a plan has ≥1 stop, render the title as large serif display text inline-editable (contenteditable-style or an input styled to look like a headline, borderless until focus) — "Tên lịch trình" becomes literally the headline of the traveler's own travel story.

---

## 5. SENSORY + MOTION + CURIOSITY

**Map:**
- Cluster-to-pin zoom (already implemented via MapLibre `clusterMaxZoom`) — add a **soft "bloom" easing** on `easeTo` (already using `easeTo`; just confirm cubic-bezier feels organic, e.g. `--ease-out-expo`) so zooming into a cluster feels like a flower opening, not a jump-cut.
- Popup card: apply the sediment-tick left border treatment already coded (`border-left:4px solid ${color}`) — keep it, it's already good — but add a **soft rise-in animation** (translateY 4px→0, opacity 0→1, 180ms) instead of instant appearance.
- Discovery device: a small **"🎲 Bất ngờ chưa?" (Surprise me) button** floating bottom-right of the map that flies to a *random* pin outside the current viewport and opens its popup — turns passive filtering into active discovery, reinforcing "browse" over "locate." Purely client-side (pick random from `filteredPins`), zero backend cost.
- Sound/texture cues expressed visually, not literally: cluster circles use a **subtle radial gradient (not flat fill)** evoking a water ripple; the unclustered pin uses a **soft drop-shadow "float"** so pins read as sitting slightly above the water/paper.

**Planner:**
- The single biggest interaction upgrade: **replace/augment arrow-button reorder with native HTML5 drag-and-drop** (`draggable="true"` + `dragstart/dragover/drop`) on `.stop-card`, with the sediment-spine roundel as the visible grab handle (cursor: grab). Keep the ↑/↓ buttons as an a11y/keyboard/coarse-pointer fallback (already `aria-label`'d) — additive per B2, don't remove the accessible path.
- Drag feedback: dragged card gets `opacity:.5` + slight rotate(-1deg) (a physical "picked up" tilt), drop target gets a river-tinted insertion line — small CSS-only touches that make reordering feel tactile rather than transactional.
- `addStop` already has a nice `.picker-item.adding` highlight-scale pulse — extend it with a **"flying dot" micro-animation**: a small colored dot animates from the clicked picker-item toward the stop-list panel (CSS `@keyframes` translate, ~350ms, respects reduced-motion) — reinforces "this thing just moved from left to right," which is the core mental model of the page.
- Route ribbon (`route-total`, `route-leg-info`) — style as a **dashed "distance tape"** between stop cards (small perforated-line SVG background) rather than a plain pill, echoing a paper itinerary/boarding-pass aesthetic.
- Curiosity device: when picker is idle/empty-search, show a **"Gợi ý hôm nay" (today's picks) strip** of 3-4 rotating entities (e.g., featured or high-rated) above the picker list — gives the blank-slate moment something to look at besides a search box.

---

## 6. UX FLOW

**Map:** land → hero establishes scale/story → legend rail lets you narrow by type in one tap → map is the sustained attention surface → clicking a pin gives a rich popup with one clear next action ("Xem chi tiết →") → the persistent pin-rail below offers a no-map-required alternative path to the same destinations, closing the loop for low-end devices/motor-impaired users → footer nudge to search or planner ("Thêm vào lịch trình" could be added to the popup itself — currently only a detail link. **Recommended addition**: a small "+ Thêm vào lịch trình" secondary action in `popupHTML`, deep-linking to `/tao-lich-trinh?add={id}` which the planner already supports via `pendingAddId` — this is a *free* cross-page win, wiring an existing capability into a currently-missing entry point).

**Planner:** land → guided steps orient the first-time user → search/browse picker (left) → tap to add (satisfying, already tactile) → stop appears with a landing animation on the right → reorder via drag → add time/notes (turns a stop into a scheduled plan) → route auto-computes and renders a live map (good: automatic, no button) → save with a spring-pulse confirmation → saved plans list becomes the "library" of the user's journeys, with share/publish as the natural exit action (send it to a friend, or make it public so it becomes a source of pride/social proof — the `is_public` toggle already exists, just needs better visual weight as a "make it a story others can read" action, not a checkbox).

Friction reductions:
- Empty picker states are already well-designed (`premium-empty-state`) — keep, extend the wavy-line motif to match map hero for family cohesion.
- `max-stops-warn` and `stopAnnounce` (aria-live) are solid a11y — preserve exactly.
- Consider surfacing estimated total trip time/day count near the plan title once ≥2 stops exist, so the "story" (a real day plan) is visible earlier, not just after scrolling to the route section.

---

## 7. PREMIUM CUES

- Deckle/torn-edge map frame (not a plain rounded rectangle) — signals "this was crafted," not "this is a plugin."
- The sediment-tick spine on the stop-list replacing the flat gray connector — ties a utility list into the brand's signature visual grammar.
- Popup cards, route-leg ribbons, and saved-plan rows all sharing the same hairline/shadow/radius vocabulary already defined in tokens (`--shadow-sm`, `--radius-lg`, `.5px solid var(--line)`) — consistency IS a premium cue; audit for any place these pages diverge (e.g., `route-map` uses `--radius-lg` correctly already).
- Micro-typography discipline: numerals in stop badges, distances, and durations should use tabular figures (`font-variant-numeric: tabular-nums`) so the route ribbon numbers don't jitter as they update — a tiny, expensive-feeling detail.
- Loading state for route calc (`route-loading`) already pulses tastefully — keep, maybe pair with a thin animated dashed line along the route-map placeholder for extra polish.

---

## 8. CULTURAL AUTHENTICITY

- River/wave motifs (already partially present as the `.premium-empty-state::before` wavy SVG) should be pulled forward as the *primary* decorative signature on the map page specifically — not generic "wavy line" but suggestive of kênh rạch (canals) branching, which is literally what the province looks like from above.
- Cluster color and marker palette should map onto real categories with real meaning, not arbitrary hues: craft_village (`#B8860B`, amber-gold) evokes gốm/đất nung (pottery/clay); nature (`#1A7A5C`, deep leaf) evokes miệt vườn; dish (`#D94F3D`, warm clay-red) evokes ẩm thực. This is already roughly true in `MARKER_COLORS` — just make sure the legend rail labels these associations explicitly so users *learn* the color language (small color-swatch + label pairing already implicit in `typeFilterOptions`).
- Planner stop-card empty illustration and the "surprise me" random-pin feature should bias toward under-visited categories (craft villages, Khmer pagodas, chợ nổi) rather than always surfacing the most popular attraction — a subtle way to fulfil the "living invitation" thesis and support less-visible OCOP/cultural entities.
- Avoid generic globe/pin/compass iconography beyond what's functionally necessary (keep 🗺️/📍 as accessible fallbacks, but let the *drawn* motifs — river lines, dashed paths — carry the visual brand rather than stock map emoji clip-art).
- Copy should name real geography (kênh, cù lao, chợ nổi, miệt vườn) in the hero/microcopy rather than generic "explore destinations" phrasing — see Copy Voice below.

---

## 9. COPY VOICE

Tone: warm, second-person-adjacent, inviting motion — "hãy," "đi," "vẽ," "thử" — never corporate SaaS ("Explore our platform's features").

**Map hero:**
> **Một dòng sông, ngàn điểm dừng**
> Từ chợ nổi lúc tinh mơ đến vườn bưởi cuối chiều — kéo bản đồ, phóng to một cù lao, và để Vĩnh Long mới dẫn lối.

**Map empty/filter nudge:**
> Chưa thấy gì ở đây? Có thể nơi bạn tìm đang nằm bên kia con kênh — bỏ bớt bộ lọc, hoặc để chúng tôi gợi ý.

**Planner hero:**
> **Vẽ hành trình của riêng bạn**
> Chọn một điểm dừng, rồi một điểm nữa — như ghe len lỏi qua từng con rạch. Sắp xếp lại bất cứ lúc nào, hành trình là của bạn.

**Planner save confirmation (toast, keep existing mechanic, upgrade wording):**
> Đã cất "​{tên lịch trình}" vào hành trang — mở lại bất cứ lúc nào.

---

## 10. SIGNATURE MOMENT

**The dragged stop-card with the sediment-spine grab handle, mid-reorder, tilted slightly like a card being physically slid along a river-toned string of beads — with a live route ribbon reflowing beneath it in real time.** This is the one screenshot that says "this planner was designed, not templated": a database-row reorder becomes a tactile, river-threaded, physically-metaphored act. On the map side, the companion signature moment is **the deckle-edged map with the legend rail sitting like a hand-drawn map key beside a canal-branching backdrop, clusters blooming open as you zoom** — a map that looks like it was drawn for this specific delta, not dropped in from a generic maps SDK.

---

## 11. COMPONENTS + FEASIBILITY

**New/modified components (CSS-tokens only, no Tailwind, dark-parity + reduced-motion required throughout):**

1. **`PlannerMapHero.vue` (or scoped section, shared shape)** — reusable hero band: dateline eyebrow + serif H1 + subtitle + animated river/dashed-path SVG background (CSS `background-position` keyframe, `prefers-reduced-motion` freezes to static). **Reusable** across both pages (parametrize motif: river-wave vs dashed-path) and potentially other utility pages (search results, favorites) later.
2. **Deckle-edge map/card frame** — CSS `clip-path: polygon(...)` with a handful of hardcoded jitter points, or an SVG `<mask>` wrapper; apply to `#mapContainer` and to `.route-map`. Pure CSS, zero JS cost. **Reusable** as a general "artifact card" frame treatment anywhere a map or image wants a "laid on the table" feel.
3. **Legend rail** — restyle existing `FilterChips` usage in a `position: sticky` glass panel at ≥1024px (media query only, same component, no new JS logic) overlaying the map's left margin; reverts to current horizontal row below that breakpoint. CSS-only responsive change.
4. **"Đang hiện trên bản đồ" persistent pin rail** — promote existing `map-list-fallback` markup out of the `<template #fallback>`-only conditional into an always-rendered horizontal-scroll strip beneath the map (small logic change: currently implicitly tied to no-JS fallback; make it a first-class section using `visibleListPins`, already computed).
5. **"Bất ngờ chưa?" random-pin button** — small floating button, client-only, `Math.random()` pick from `filteredPins`, `map.flyTo` + trigger existing popup logic. Pure addition, no backend.
6. **Sediment-spine stop-list** — replace `.stop-connector` flat bar with a `linear-gradient(var(--river-600), var(--amber-500), var(--clay-600))` vertical tick (reuse the exact gradient already established as the site's "sediment" signature elsewhere), stop-number roundel sits on top.
7. **Drag-and-drop reorder** — native HTML5 DnD on `.stop-card` (draggable, dragstart/dragover/drop handlers calling existing `moveStop`-equivalent array-splice logic); keep arrow buttons as accessible/coarse-pointer fallback (already present, just needs to remain visually secondary, e.g. shown on focus/hover or in a kebab menu on touch).
8. **"Flying dot" add-to-plan animation** — CSS keyframe on a cloned small element animating from click coordinates to the builder panel; ~300-350ms, `prefers-reduced-motion` skips straight to the existing `.picker-item.adding` pulse only.
9. **Day-grouping dividers** in stop-list — optional `day` grouping computed client-side from stop order (e.g., every N stops or explicit user-set day break); purely additive UI grouping, no schema change required for v1 (persist as part of the existing `stops` JSON blob, e.g. add optional `dayBreakBefore: boolean` to `PlanStop` — additive field per B2).
10. **Popup "+ Thêm vào lịch trình" action** — one-line addition to `popupHTML()` linking to `/tao-lich-trinh?add={id}`, wiring into the planner's existing `pendingAddId`/`resolvePlannerEntity` flow. Zero new backend surface.
11. **Distance-tape styling** for `route-leg`/`route-total` — CSS `background-image` dashed/perforated pattern (SVG data-URI, matches existing wavy-motif technique already used elsewhere in this file), `font-variant-numeric: tabular-nums` on all distance/duration numerals.

**Explicitly NOT building:** no new map SDK, no server-side clustering changes, no booking/CTA additions (contact-only constraint untouched — planner/map have no commerce surface to begin with), no paid map tiles/services (stay within existing MapLibre/NDA map setup), no heavy animation libraries — everything above is plain CSS keyframes/transitions plus small vanilla JS, consistent with solo-dev/budget constraints.

**Dark mode + reduced motion:** every new visual (deckle edge, sediment spine, distance tape, river motif) must get a `.dark` variant following the existing pattern in both files (opacity/tint adjustments already modeled throughout current `<style scoped>` blocks) and a `@media (prefers-reduced-motion: reduce)` override disabling flyTo easing swaps, the flying-dot animation, the river background drift, and drag-tilt (keep drag reordering functional, just drop the rotate/opacity flourish).
