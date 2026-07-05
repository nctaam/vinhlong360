# Region Guide — `khu-vuc/[area].vue` (Vĩnh Long / Bến Tre / Trà Vinh / Liên vùng)

> Prior grade: **7.5**. Diagnosis: cinematic hero + editorial intro land well, then the page collapses into a repeated `EntityCard` grid — six sections that all look and feel identical (Featured → Type 1 → Type 2 → … → Wards → Full grid). There is no sense of *chapter*, no geography, no texture that differentiates Vĩnh Long from Bến Tre from Trà Vinh below the fold. This concept turns the region page into what it actually is: **a chapter of a book**, with its own dialect, its own map, its own rhythm — while every fix stays inside existing CSS-token/EntityCard/component machinery.

---

## 1. STORY ANGLE

A region page is not "a filtered list of entities where area=X." It is **the chapter opener of a three-part book** — *Vĩnh Long Mới* — where each of the three provinces-turned-districts is a distinct character with its own temperament:

- **Vĩnh Long** — the *orchard heart*: cù lao, miệt vườn, gốm đỏ Mang Thít, the calm center of the delta.
- **Bến Tre** — the *coconut nation*: an entire province literally built from one tree, 70,000 hectares of it, ringed by three river mouths and the sea.
- **Trà Vinh** — the *braided culture*: Khmer temple spires over ao Bà Om, the only place in Vietnam where dừa sáp grows, Ok Om Bok drums.

The story angle: **"Nếu Vĩnh Long mới là một cuốn sách, đây là chương của [Tên vùng]."** Each region page should read like turning to a new chapter — same book (same design system, same trust, same nav), different voice, different palette temperature, different opening image, different "the one thing you must know before you go" fact. The entity grid below isn't inventory — it's *what fills that chapter*: its dishes, its craft villages, its stays, organized the way a local would tell you about them, not the way a database groups by `type`.

Liên vùng (`lien-vung`) gets its own angle: **the connective tissue** — not a fourth province but the story of *routes between the other three* (the ferry, the coastal road, the river that ties Mỹ Tho–Bến Tre–Trà Vinh together). It should read as an epilogue/appendix chapter: "Cách 3 vùng nối nhau."

## 2. CINEMATIC HERO / THESIS

Keep the existing photographic hero (`area-vinh-long.webp` / `area-ben-tre.webp` / `area-tra-vinh.webp`) — it's the strongest asset on the page and already CE'd. Deepen it:

- **A one-line "chapter number" mark** above the eyebrow: `CHƯƠNG I · VĨNH LONG`, `CHƯƠNG II · BẾN TRE`, `CHƯƠNG III · TRÀ VINH` (roman-numeral-style, ultra-small, wide-tracked, in `--font-sans`). This is the single cheapest move that reframes the entire page as *book*, not *filter view*. Liên vùng becomes `PHỤ LỤC · LIÊN VÙNG` (appendix), reinforcing its connective role rather than making it feel like a lesser 4th region.
- **A live micro-map glyph** inline in the hero, next to the stats: a tiny abstracted SVG of the Mekong branching (2-3 river lines + a dot marking this region's position relative to the other two) — not a real map (no geo dependency, no Mapbox cost), just an iconographic wayfinding glyph reused across all 4 region heroes with the "you are here" dot repositioned. This single glyph does more for "which region am I in and where does it sit" than the current emoji/text alone, and it's pure inline SVG — zero cost, zero dependency.
- **One signature sentence, not a blurb** — replace/augment the existing `blurb` with a punchier single-sentence *thesis* rendered in serif italic beneath the h1, e.g. for Bến Tre: *"Một tỉnh được dựng nên từ một loài cây."* This is the "curiosity ignition" the brief asks for — it must be quotable, not descriptive.
- Keep Ken-Burns-style slow zoom (already used elsewhere in CE) on the hero background at low amplitude (4-6% scale over 20s), reduced-motion-gated.

## 3. LAYOUT + RHYTHM

The core fix: **stop presenting `typeSections` as N identical `scroll-row` blocks.** Introduce three distinct *movements* after the hero + editorial lede:

**Movement I — "Bức tranh vùng" (The Map Moment).**
Immediately after the editorial lede, before any card grid: a horizontal *geography strip* — a light SVG/CSS ribbon showing this region's defining physical facts as an infographic band, not prose and not cards. E.g. for Vĩnh Long: cù lao count, number of orchards types, km of kênh rạch. For Bến Tre: 3 river mouths + hectares of dừa. For Trà Vinh: number of chùa Khmer + km of coastline. This reuses the existing `.catalog-stats`/`CountUp` pattern but restyles it as a horizontal editorial infographic (icons + big serif numerals + hairline separators over a tinted ground), distinct from the hero stat-pills so it doesn't feel repeated.

**Movement II — "Theo nhịp sống" (Curated Trails, not Type Grid).**
Replace the flat `typeSections` loop (currently: experience → attraction → dish → product → lodging → craft_village, one identical scroll-row each) with **2-3 named, hand-authored "trails"** per region that cut *across* types — this is the highest-leverage structural change:
  - Vĩnh Long: "Một ngày miệt vườn" (orchard experience + dish + lodging mixed), "Nghề và người" (craft_village + organization).
  - Bến Tre: "Đường dừa" (everything coconut: product + craft_village + dish), "Ở lại bên sông" (lodging + experience).
  - Trà Vinh: "Chùa và lễ hội" (attraction + culture), "Vị Khmer" (dish + product).
  This turns 5-6 mechanically-identical rows into 2-3 *storied* rows with their own mini-heading + one-line curatorial note ("Không phải điểm nào cũng cần đi hết — chọn 1 buổi sáng cho vườn, 1 buổi chiều cho làng nghề."). Remaining ungrouped types fall back to the current generic scroll-row treatment beneath a "Khám phá thêm theo loại hình" sub-head, so nothing is dropped — just re-prioritized. This is additive on top of existing `typeSections` computed data (trails are curated groupings of the *same* entities, defined in a small per-area config object, not new data fetches).

**Movement III — "Bản đồ hành chính"(Wards) stays, but gets a visual demotion/reframe** — present as a compact reference module (already de-emphasized via `band` styling) rather than a full card grid; keep chip-row, it's appropriately lightweight.

**Movement IV — Full grid** stays as the "everything else, for completionists" tail — but retitle its divider from generic "Tất cả N mục" to region-flavored: *"Toàn bộ [Vùng] — N điểm đến"* and keep `LoadMoreButton` progressive loading (good existing pattern, no change needed).

Responsive posture: trails use the same `scroll-row` horizontal-scroll-on-mobile pattern already established (no new interaction model — reuse, don't reinvent). Geography strip stacks to 2-column on mobile, hides the SVG river-glyph micro-map (decorative, not required at narrow width) via a media query — pure CSS, no JS branching needed since it's inline SVG.

## 4. TYPOGRAPHY

- Chapter mark (`CHƯƠNG I`) — `--font-sans`, 700 weight, `letter-spacing: .3em`, `--text-2xs`, sits above the existing `.area-eyebrow` (which becomes the secondary line: `Miền Tây · Cửu Long`). Two-tier eyebrow stack: chapter-number (smallest, boldest tracking) → region context (existing style).
- New thesis sentence — `--font-editorial` italic, `clamp(1.15rem, 1rem + 1vw, 1.6rem)`, sits directly under `h1`, `color: rgba(255,255,255,.95)` on the photo hero, max-width ~34ch so it breaks like a pull-quote, not a paragraph.
- Trail headings (Movement II) — same serif treatment as existing `.section-head h2` (with the phù-sa tick) but each trail additionally gets a small serif *curatorial note* line beneath in `--font-editorial` italic, `--text-sm`, `color: var(--muted)` — this is new: a one-sentence "why this trail" in a human, non-database voice.
- Geography-strip numerals — largest serif weight on the page after H1, `--font-editorial`, tabular-ish scale (reuse `CountUp` styling but bump size), so the facts read as *headline data*, not caption text.

## 5. SENSORY + MOTION + CURIOSITY

- **Ken Burns** on hero photo — slow, subtle (already noted above), reduced-motion turns it off entirely (static frame).
- **Geography-strip reveal**: numbers count up via existing `CountUp` on scroll-into-view (already used elsewhere — reuse, don't rebuild) but stagger by 80-120ms per item so they arrive like a heartbeat, not all at once.
- **Trail card hover**: within a trail row, add a **1-line "why" caption that appears on hover/focus for each EntityCard** — not new copy per entity (too costly to author for 1700+ entities) but a *type-based* micro-caption keyed off `entity.type` within that trail's context, e.g. inside "Đường dừa" trail, a `product` card's hover caption reads "Sản phẩm OCOP" while an `experience` card reads "Trải nghiệm tại vườn." This is a cheap CSS/JS-driven overlay (a small lookup table, not per-entity authored content) that adds discovery texture without new data-entry burden.
- **Discovery device — "Vùng lân cận" nudge**: at the tail of Movement IV (full grid), before the cross-links section, insert a slim horizontal card that says *"Khám phá thêm: [other 2 regions]"* with their hero thumbnails as small chips — the region-to-region hop that currently doesn't exist anywhere on this page (you can arrive at `/khu-vuc/ben-tre` and have literally no path to `/khu-vuc/tra-vinh` except backing out to nav). This closes an actual navigation gap and is a natural "curiosity forward" device — book chapters imply the next chapter.
- **Sensory copy, not sensory FX**: resist adding more animation (over-animation is a stated AI-slop risk). Instead push sensation into *copy* — the thesis line, the trail curatorial notes, the geography-strip labels (e.g. "70.000 ha dừa" rather than "Diện tích dừa: 70000") should carry rhythm and specificity rather than the page carrying more moving parts.

## 6. UX FLOW

Entry → hero (chapter framing + thesis, 2-3s orientation) → editorial lede (drop-cap, ~15s read, "why this region matters") → geography strip (5s glance, the facts that make you feel the place is real and specific) → **Movement II trails** (the actual browsing/decision zone — this is where "explore" intent should resolve, ideally within 2 trail rows before the visitor has seen a *contact-worthy* place) → wards (utility, low-friction reference) → full grid (completionist tail with progressive load, keeps scroll cost low via existing `LoadMoreButton`) → cross-links + **new region-hop nudge** (send the visitor either onward to a sibling region, or into a cross-cutting interest page).

Every `EntityCard` already carries its own contact/detail CTA — this page's job is not to add friction with new CTAs, but to get the *right* card in front of the visitor fastest. The trail restructuring (Movement II) is the main lever: it front-loads curated, cross-type combinations instead of forcing the visitor to scroll past an entire `attraction` row before reaching `dish`.

Empty/loading/error states are already solid (`SkeletonGrid`, `EmptyState`, retry) — no change needed, just confirm the new geography-strip and trail blocks degrade gracefully to nothing when `entities.length === 0` (guard with existing `v-if`).

## 7. PREMIUM CUES

- Chapter numbering + consistent "one book, three/four chapters" framing across all `AREA_META` keys signals editorial intentionality (a real magazine/guidebook would number its regions; a database dump would not).
- Curatorial notes under trail headings (short, opinionated, human sentences) are the cheapest, highest-signal "someone who knows this place wrote this" cue — more premium than any additional visual chrome.
- The geography-strip's specificity (exact-feeling numbers, not rounded marketing stats) reads as researched rather than templated.
- Hairline dividers + phù-sa tick already establish craft; extending the *same* tick motif to trail sub-headings (not just top-level `section-head`) keeps the visual grammar disciplined rather than inventing a second signature per section.
- Region-hop nudge at the tail signals "this is a connected system," not "this is one page in isolation" — trust cue by implication of information architecture.

## 8. CULTURAL AUTHENTICITY

- Vĩnh Long trails keyed to miệt vườn/cù lao/gốm Mang Thít — already present in editorial copy; trails should surface `craft_village` (gốm) and orchard `experience` entities specifically, not generic "attraction."
- Bến Tre trail "Đường dừa" must foreground the *literal totality* of coconut — product, craft, drink, roof-thatch, boat — the thesis line ("một tỉnh dựng từ một loài cây") only lands if the trail beneath it visibly proves it across multiple types, not just `product`.
- Trà Vinh: Khmer chùa architecture + Ok Om Bok + dừa sáp Cầu Kè are specific, correct, non-generic details already in the editorial block — the "Vị Khmer" and "Chùa và lễ hội" trails should pull `attraction` entities tagged to Khmer temples specifically where metadata allows, avoiding a generic "temples of Vietnam" tourism-cliché framing.
- Avoid the AI-slop tell of generic river/lotus/conical-hat iconography in the micro-map glyph — keep it purely abstract (branching lines + dot), not decorative Vietnam-tourism clip art.
- Liên vùng chapter must resist becoming "leftover entities" — frame explicitly as routes/connections (ferry, coastal corridor, river) per the story angle in §1.

## 9. COPY VOICE

Voice: **a knowledgeable local writing a chapter introduction for a friend visiting, not a tourism board press release.** Specific, warm, slightly wry, never superlative-stacked ("tuyệt đẹp," "không thể bỏ lỡ" banned as generic filler).

Example lines (Vietnamese):

- Bến Tre hero thesis: **"Một tỉnh được dựng nên từ một loài cây — không phải ẩn dụ, mà là bảy mươi ngàn hecta dừa thật."**
- Trà Vinh trail curatorial note ("Chùa và lễ hội"): **"Không phải chùa nào cũng cho khách vào giờ nào — ghé buổi sáng, tránh giờ tụng kinh, và đừng quên hỏi trước khi chụp ảnh trong chánh điện."**
- Vĩnh Long trail curatorial note ("Một ngày miệt vườn"): **"Sáng đi vườn hái trái, trưa ăn ngay tại chỗ, chiều mới tới lượt gốm Mang Thít — thứ tự này quan trọng hơn bạn nghĩ."**
- Region-hop nudge: **"Vĩnh Long xong rồi — bên kia sông Cổ Chiên, Bến Tre đang đợi."**

## 10. SIGNATURE MOMENT

**The Chapter Mark + Thesis Line pairing at the hero** (`CHƯƠNG I · VĨNH LONG` + *"Miệt vườn giữa hai dòng sông"*-style italic pull-quote) is the one thing this page should be remembered by: it single-handedly converts four filtered-list pages into four chapters of one coherent book, which is the exact narrative repositioning the brief calls for — and it costs almost nothing (a text layer + a tiny inline SVG glyph, zero new data, zero new dependencies, fully reusable across all four `AREA_META` entries and future regions if the province ever adds a fifth).

## 11. COMPONENTS + FEASIBILITY

All items below are CSS-token-based, dark-parity, reduced-motion-respecting, and use only entities/images already present in the API response for this route (`/api/entities?area=X`) plus small hand-authored config objects (no new endpoints, no new images required beyond the 3 existing hero photos).

- **`ChapterMark` (new, tiny)** — inline component/markup: renders `CHƯƠNG {n} · {NAME}` or `PHỤ LỤC · LIÊN VÙNG`. Config: a `AREA_CHAPTER: Record<areaKey, {n: string|null, label: string}>` map alongside existing `AREA_META`. Reusable pattern for any future "chaptered" collection page (e.g. could extend to `xa-phuong` sub-groupings later).
- **Micro-map river glyph (new, inline SVG, ~20 lines)** — one shared SVG defined once (3 curved paths representing sông Tiền/sông Hậu/coastal line) with a positioned `<circle>` "you are here" dot whose `cx/cy` is parameterized per area via a small lookup table. Zero image cost, themable via `currentColor`/CSS var, hidden below `640px` via media query.
- **Thesis line** — new field in `AREA_META` (`thesis: string`) rendered under `h1` in the existing hero markup; falls back silently to nothing if absent (safe additive change, per B2 additive-first).
- **`RegionGeoStrip` (new component)** — horizontal stat-band; reuses existing `CountUp` component and `.catalog-stats`-style pill visuals but in a new scoped class so it reads as a distinct movement, not a repeat of hero stats. Data: small `AREA_GEO_FACTS: Record<areaKey, {icon, value, label}[]>` config (hand-authored, ~3-4 facts per region — one-time content task, not per-entity).
- **`RegionTrail` (new component, the highest-leverage build)** — takes a title, an optional curatorial note, and a filter function/id-list over the already-fetched `entities` array; renders existing `EntityCard` in the existing `.scroll-row` pattern (zero new card component work — pure reuse of `EntityCard`, `scroll-row`, `see-all-toggle` already in this file). Config: `AREA_TRAILS: Record<areaKey, {title, note, match: (e: Entity) => boolean}[]>` — match functions can filter on `entity.type` combinations or tags/metadata already present. Remaining types not claimed by any trail fall through to the existing generic `typeSections` loop unchanged (guarantees nothing currently visible disappears — additive per B2).
- **Region-hop nudge (new, small)** — a slim card row at the tail of the full grid, links to the other `AREA_META` keys (excluding current), using each region's existing hero thumbnail as a small chip image (no new image asset). Pure `NuxtLink` + existing card styling primitives.
- **Hover micro-caption on trail cards** — CSS-only `::after`/tooltip pattern keyed by a small `type → caption` map passed as a prop/data attribute to `EntityCard` instances inside a `RegionTrail` context only (does not touch `EntityCard`'s default appearance elsewhere — scoped via a wrapper class, e.g. `.trail-row [data-trail-caption]`).

**Explicitly reusable across other catalog-style pages** (`/kham-pha`, interest pages, potentially `xa-phuong`): `RegionGeoStrip`'s stat-band pattern, the trail-row concept (`RegionTrail` could generalize into a `CuratedRow` component taking any title/note/filter), and the region-hop nudge pattern (generalizes to "related X" nudges elsewhere). The `ChapterMark` and micro-map glyph are area-specific (only meaningful where there are exactly 3-4 sibling regions) and should stay local to this page.

**Explicitly NOT built**: no interactive/zoomable real map (Mapbox/Leaflet would add a paid or heavy dependency — against budget constraint); no per-entity authored hover captions (cost scales with 1700+ entities — use type-based captions only); no new photography (only 3 region hero photos exist and are reused as-is; Liên vùng gets no hero photo — falls back to the existing generic `.catalog-hero` gradient treatment, which is fine since it's the "appendix" chapter and doesn't need the same cinematic weight).
