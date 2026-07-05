# xa-phuong/[id].vue — Hồ sơ Xã/Phường ("Ward/Commune Profile")

*Prior grade: 7.0. 124 wards, mostly imageless. This is the single most-repeated "place" template on the whole site — it stands in for the everyday geography of the merged tỉnh: a commune is where 99% of residents and most content actually lives, versus the glamorous few dozen "điểm đến" pages. The brief: make a small, ordinary, often-photo-less commune feel like a place with a soul, not a database row.*

---

## 1. STORY ANGLE

The current page tells an **administrative** story: "here is a polygon called Phường X, here are its stats, here is what's inside it, here is who to call." That is correct but soulless — it reads like a GIS attribute table with nice CSS.

**Reframe: a xã/phường page is a PORTRAIT, not a record.** Every commune in the Mekong Delta has an identity carried in things a database schema doesn't have fields for — what grows on the banks, what the market smells like at 5am, which family has made the same thing for three generations, what the place is called *before* it was renamed by the 2025 sáp nhập. The story angle is:

> **"Đây là nơi người ta sống, chứ không chỉ là nơi có tọa độ."**
> *(This is a place people live, not just a place with coordinates.)*

Concretely, the page should answer, in order of emotional priority:
1. **What does this place smell/taste/sound like right now?** (seasonal framing — flood season, harvest, Tết)
2. **What is it known for, in one sentence a local would actually say** — not a Wikipedia-style summary, a proud, specific claim ("phường có lò gốm đỏ cuối cùng còn đốt bằng trấu ven sông Cổ Chiên").
3. **What can I actually do here today** (tourism/lodging/products — existing data)
4. **Who do I call if I need something** (facilities/emergency — existing data)
5. **Where does this sit in the larger fabric** (its province-area, neighboring wards, its old name if renamed) — this is the connective tissue that turns 124 isolated pages into a *navigable region*, which is the single best lever for a mostly-imageless page: **make the NETWORK the visual interest, not the photo.**

For the ~64 wards with zero tourism/lodging/product entities (the `wp-empty-card` case), the story angle flips from "explore here" to **"belonging"** — a civic-pride mini-portrait built entirely from data that DOES exist (name etymology/old name, area stats, neighbors, administrative facilities, and the province-area's blurb). An empty commune should still feel like *somewhere*, not a 404-adjacent dead end.

---

## 2. CINEMATIC HERO / THESIS

Keep the real-photo hero when an entity photo exists for the ward (rare), but design primarily for the **no-photo case**, since that's 124-ish of these.

**"Sổ địa bạ hiện đại" (the modern land-register) hero** — an editorial reinterpretation of a Vietnamese cadastral/ledger page, not a stock-photo banner substitute:

- Full-bleed hero keeps the tri-province gradient (already good, keep it) but the **decorative motif upgrades from a faint line-pattern SVG to a *custom cartographic vignette***: a soft single-line contour trace of the ward's own polygon (we already have `coordinates`/place polygon data from the map layer) rendered as a thin gold-on-clay line-art silhouette, positioned right-aligned, bleeding off the hero edge — like a wax-seal stamp of the commune's actual shape. This is 100% CSS/SVG generated from data already on the page (no photo needed) and is **unique per ward** — solves the "all 124 heroes look the same" problem cheaply.
- Large serif `h1` stays, but add a **second small serif line beneath it in italic** for the old/pre-merger name where available (`Trước 2025: xã An Bình`) — this single detail does enormous cultural-authenticity work: acknowledging that this ward used to be something else, which every long-time Mekong Delta resident feels acutely after the 2025 sáp nhập. Where no old-name data exists, fall back silently (no placeholder text).
- **Season strip**: a thin horizontal ribbon under the stats bar showing "what's in season right now here" derived from any tourism/product entities' `season` attribute already loaded in `data.tourism`/`data.products` (reuse `useSeason` composable already imported by EntityCard) — e.g. "🌊 Đang mùa nước nổi · 🍊 Cam sành đang rộ" — small, quiet, factual, never invented.
- Keep stats row (diện tích/dân số/địa điểm) but reframe the *地điểm* stat label from generic "Địa điểm" to a warmer count noun when zero: instead of "0 Địa điểm" show nothing and let the empty-state card do that work (avoid a hero that visually announces "nothing here").

**Thesis line:** the hero motif *is* the map — this ward's outline, not a generic wave pattern — so even a completely photo-less commune gets one non-generic, place-specific visual the instant the page loads.

---

## 3. LAYOUT + RHYTHM

Current structure (breadcrumb → hero → summary → map → 2-col body[content|sidebar]) is sound and should be **kept as the skeleton** — this is a utility/reference page, not a long-form scrollytelling piece, and over-theatricalizing it would read as slop. The rhythm upgrade is about **sequencing and connective tissue**, not adding sections wholesale:

1. Breadcrumb (unchanged)
2. Hero (upgraded per §2)
3. **NEW: "Trong vùng" neighbor strip** — a slim horizontal scroller of 4-6 neighboring wards (same `area`, nearest by whatever ordering is available — alphabetical or DB order is fine as v1) as small pill-chips with emoji, immediately below the hero, before the summary. This is the single highest-leverage addition: it turns each lonely ward page into a *node in a network you can walk*, which is exactly what solves "124 pages that all look isolated and interchangeable."
4. Summary (lede) — keep, but treat typographically as an editorial dek (see §4)
5. Map (unchanged, already good — full width, real interactive data)
6. Two-column body:
   - Main: Tourism → Lodging → Products (unchanged order/logic), OR the redesigned empty-state (§10) when count=0
   - Sidebar: emergency contact card (unchanged) → facilities list (unchanged) → **NEW: "Thuộc về" (belongs to) mini-card**: area name + blurb (already have `areaMeta.blurb` from AREA_META, currently unused on this page!) + a link to the region hub. This single card recovers copy that's already written and loaded (`AREA_META[area].blurb`) but currently thrown away.
7. Footer-of-page **NEW: lightweight "Khám phá thêm" strip** linking to `/kham-pha/*` interest pages relevant to whatever entity types are present (e.g. if products exist → "Mua sắm & OCOP"; if tourism exists → "Thiên nhiên"), using `INTEREST_META` already defined in useConstants. Cheap, reuses data, gives the page an "exit ramp" instead of dead-ending at a facilities list.

Responsive posture: unchanged 2-col→1-col collapse at 840px is fine. The neighbor-strip scroller becomes horizontal-swipe on mobile (same pattern as any existing chip-scroller elsewhere in the codebase — reuse, don't invent a new component).

---

## 4. TYPOGRAPHY

- `h1` (ward name): keep Fraunces editorial serif, but nudge scale up slightly on desktop (`clamp(1.9rem, 5vw, 2.6rem)` vs current capped 2.2rem) — a place name deserves to be the loudest thing on its own page; right now it's throttled to roughly the same size as a card title elsewhere.
- **NEW old-name line**: `font-style: italic; font-family: var(--font-editorial); font-size: var(--text-sm); opacity: .78` — quiet, small-caps-adjacent, sits like a museum wall-label subtitle under the h1.
- Summary/lede: already correctly promoted to editorial serif at `clamp(1.02rem,...,1.15rem)` in the CE3 pass — good, keep, but raise `line-height` slightly (`var(--leading-relaxed)` → confirm it's ≥1.6) since this is now doing "lede" duty, not "caption" duty.
- Section heads (Tham quan/Lưu trú/Đặc sản): keep the sediment-tick + serif treatment already shipped (CE3) — this is correct and reusable, no change.
- Sidebar card headers (`h3`): currently sans-serif `--weight-semibold` at `--text-base` — fine as-is, sidebar is utility, keep it sans to visually separate "editorial voice" (story) from "directory voice" (facts), which is actually a *feature*, not an inconsistency, if intentional. Make the distinction explicit in code comments so a future pass doesn't "fix" it into sameness.
- Neighbor-strip chip labels: sans-serif, `--text-sm`, `--weight-medium` — these are wayfinding UI, not narrative, keep them crisp/small.

---

## 5. SENSORY + MOTION + CURIOSITY

Restraint is a feature here — a directory/reference page saturated with motion reads as slop. Target: **2-3 deliberate motion moments, everything else static.**

1. **Hero cadastral-line reveal**: on load, the ward-outline SVG motif draws itself with a `stroke-dasharray` line-draw animation (0.9s ease-out-expo, once, respects `prefers-reduced-motion` → instant show). This is the single "wow, that's for THIS place" moment that justifies the whole per-ward-outline idea — worth the one animation budget line.
2. **Neighbor-strip chips**: gentle `translateY(-2px)` + shadow lift on hover/focus (reuse the existing `wp-card:hover` spring easing token already defined) — signals "these are doors, not labels."
3. **Existing `reveal` scroll-fade on Lưu trú/Sản phẩm sections** — keep exactly as-is (already correct, already gated by `useReveal()` + reduced-motion).
4. **Season-strip micro-pulse**: the single emoji marking "đang mùa" gets a very slow (3s, low-amplitude) opacity breathe — same visual language as the existing `.peak-dot` on EntityCard — reusing an established motif rather than inventing a new one.
5. **Sensory-through-copy, not motion**: since imagery is absent for most wards, curiosity has to come from *specificity of language* — see §9. A sentence like "chợ nổi họp lúc mờ sáng, tan trước khi nắng lên" does more sensory work than any parallax effect could, at zero engineering cost.

**Discovery devices** (what pulls you to the next click):
- Neighbor-strip (§3 layout) — lateral exploration ("what's next door")
- "Thuộc về" sidebar card — upward exploration (province-area hub)
- "Khám phá thêm" footer strip — thematic exploration (interest pages)
- Old-name line — a tiny "huh, TIL" hook that rewards reading the hero fully instead of skimming past it

---

## 6. UX FLOW

Entry point is almost always: danh bạ hành chính list, a search result, an entity's "địa điểm liên quan" link, or a QR/link shared for a specific commune (e.g. someone in that commune shares it on Zalo). Design for **scan-first, commit-second**:

1. Land → hero answers "am I in the right place, and does this place have a story" in under 2 seconds (name, area, season line, old-name if any).
2. Neighbor strip — silently registers "oh, this is part of something bigger," even if not clicked.
3. Lede — one more sentence of "why should I care."
4. Map — immediate concrete usefulness (where is this, what's around it) — this is already the highest-utility element on the page and correctly placed early.
5. Content sections — the "what can I do" payload.
6. Sidebar — the "who do I call / where do I report" payload, always visible via sticky, never buried.
7. Exit — either into an EntityCard (existing, unchanged flow) or into the neighbor-strip/area-hub/interest-strip (new lateral exits).

**Friction removal**: the emergency-contact card should stay pinned/sticky exactly as today (already correct — safety info shouldn't require scrolling on a civic page). No new friction added; every new element (neighbor strip, old-name line, belongs-to card, discover strip) is additive and skippable, never blocking.

**CTA discipline**: nothing on this page should imply booking — it already correctly limits itself to phone (`tel:`) links and internal navigation. Keep it that way; do not add a generic "Liên hệ" CTA button to the ward page itself (contact-with-whom? there's no single ward "owner") — the existing per-office phone links inside the facilities card are the right granularity and should remain the only contact affordances here.

---

## 7. PREMIUM CUES

- The unique-per-ward cadastral outline (§2) is itself the biggest premium cue: it silently proves "we know exactly which polygon this is" rather than reusing one of three generic hero patterns — precision reads as craft.
- Old-name line: attention to a detail (recent administrative renaming) that a generic tourism site would never bother with — signals local expertise, not a scraped directory.
- `AREA_META.blurb` surfaced in the sidebar (§3): reusing already-written, already-loaded editorial copy instead of leaving it dormant is a "we sweat the details, nothing is wasted" signal.
- Season-strip built from real entity `season` attributes (not decorative) — a data-honest premium cue: the site "knows" what's happening now, doesn't fake it.
- Facilities list retains its quiet, orderly directory typography (sans, tight rows, hover micro-lift) — premium civic infrastructure should feel like a well-run town office counter: calm, not gamified.
- Keep the existing hairline dividers / `.5px` borders / soft shadow-sm discipline throughout new elements — no new border-radius or shadow values, reuse tokens exactly.

---

## 8. CULTURAL AUTHENTICITY

- **Old-name line** is the single strongest authenticity device available for this unit — it directly engages the lived 2025 sáp nhập experience noted in project memory (16 wards renamed, 35p+89x=124), which is a live, emotionally real fact for residents, not decoration.
- **Season-strip** must draw only from real flood-month (`FLOOD_MONTHS = [8,9,10,11]`) / entity-season data already in the system (`useSeason` composable) — never invented text like generic "mùa du lịch" copy. If a ward has no seasonal entities, the strip simply doesn't render (silence over fabrication).
- **Ward-outline motif**: derived from the actual polygon/coordinate data already used for the map — this is authenticity via precision, not via decorative Mekong-cliché icons (no generic "palm tree + boat" silhouettes; the shape IS the place).
- **"Thuộc về" area blurb** already contains real cultural anchors per AREA_META (cam sành/gốm Mang Thít for Vĩnh Long, dừa/bưởi da xanh for Bến Tre, Khmer chùa/ao Bà Om/dừa sáp for Trà Vinh) — surfacing it here (currently unused!) threads the tri-province cultural identity down to the commune level, which is presently missing.
- **Facilities/office labels** (UBND, Công an, Trạm y tế, Tư pháp–Hộ tịch) are already correctly Vietnamese civic-administration-accurate — do not anglicize or "simplify" these; they are load-bearing local-government vocabulary residents actually use.
- Avoid AI-slop tells: no generic "Explore the beauty of X" phrasing anywhere, no stock sunset-over-river gradients beyond the existing tri-province brand gradient, no invented "must-see top 10" superlatives for wards that are genuinely ordinary — ordinary is the honest register for most of these 124 pages, and that honesty is itself culturally authentic (not every commune is a tourist spectacle, and pretending otherwise would ring false to any local reader).

---

## 9. COPY VOICE

Voice: **plainspoken, warm, specific — a knowledgeable neighbor giving you the real picture, not a brochure.** Short sentences. Concrete nouns (a lò gốm, a chợ, a con rạch) over abstract ones (a "region," a "destination"). Never oversell.

Example lines (illustrative — actual copy must be verified against real per-ward data, not invented wholesale for production; these are voice models):

- Old-name subtitle: *"Trước 2025: xã Hòa Ninh"* — flat, factual, no explanation needed, locals will recognize it instantly.
- Season strip: *"Đang mùa nước nổi trên sông Cổ Chiên · Cam sành đang vào vụ."*
- Lede voice model (for a small, mostly-residential ward with little tourism data): *"Không có điểm check-in nổi tiếng, nhưng đây là nơi ba thế hệ một nhà vẫn còn nấu cơm bằng bếp củi ven sông. Ghé qua chợ sáng, hỏi thăm cô bán rau — biết đâu cô kể cho nghe chuyện xưa của xóm."*
- Empty-state reframe (replacing the current flat "Trang đang được xây dựng"): *"Chưa có địa điểm nào được ghi lại ở đây — không phải vì phường không có gì, mà vì tụi mình chưa kịp tới. Xem các phường lân cận, hoặc góp thông tin nếu bạn ở đây."* (turns an apology into an invitation + a soft UGC hook for later).
- "Thuộc về" sidebar card lede: reuse `AREA_META[area].blurb` verbatim (already-approved copy) — do not paraphrase.

Tone guardrails: never claim a ward "phải ghé" (must visit) if it has zero tourism entities — that's exactly the kind of AI-generated overclaim that breaks trust the moment a reader visits and finds nothing. Confidence must scale with actual data richness.

---

## 10. SIGNATURE MOMENT

**The self-drawing cadastral outline of the ward, paired with its pre-2025 name whispered beneath the title.**

In one glance: a shape that belongs to no other page on the entire site, animating in as if a hand were tracing the commune's border on a land ledger — and underneath, in quiet italics, the name this place was called before the world redrew the map. That pairing (unique geometry + acknowledged history) is what makes a commune with zero photos and zero "attractions" still feel unmistakably like *itself* — the one thing every single one of the 124 ward pages can have, that a stock template never could.

---

## 11. COMPONENTS + FEASIBILITY

All items are CSS-tokens/SVG/Vue-only, no new backend fields required except where noted; images remain AI-gen-only and are NOT required by this concept (by design, since most wards have none).

**New/changed components:**
1. **`WardOutlineMotif` (new, small)** — generates an SVG `<path>` line-art trace from the ward's polygon/boundary data if available in `data.place` (check whether `attributes.boundary_geojson` or similar exists in the DB export; if not yet modeled, this becomes a Track-backlog data task, and hero falls back to the existing MOTIFS pattern unchanged — **do not block this concept's other 10 dimensions on this one data dependency**). If only a center-point `coordinates` exists (current confirmed data), a feasible v1 fallback is a **generative seeded blob-outline** keyed by ward `id` (same deterministic-seed technique already used in `useCategoryPlaceholder.ts` for entity cards) — still unique-per-ward, still zero new backend work, just not geometrically true to the real boundary. Recommend starting with the seeded-blob v1 now, upgrading to true polygon tracing later if boundary data becomes available.
2. **`WardNeighborStrip` (new, small)** — horizontal chip-scroller, needs an API addition: `overview` endpoint to include `neighbors: {id, name, level}[]` for same-area wards (backend: trivial query, same table, filter by `area` + exclude self, limit 6). If backend change is out-of-scope for this pass, ship a client-side fallback using an already-fetched directory list (`/danh-ba`) filtered by area — slightly heavier client fetch, but zero backend change required. Flag as backlog item either way.
3. **Old-name subtitle** — needs `attributes.old_name` (or similar) surfaced from DB; check whether the 16-wards-merged migration already recorded prior names (per project memory: "16 phường mới ĐÃ MIGRATE"). If the field exists, this is a pure template change (one new conditional `<p>` under `h1`). If it doesn't exist yet, flag as a data-backlog item — do not fabricate names.
4. **Season strip** — pure frontend, reuses `useSeason` composable + `data.tourism`/`data.products` already fetched — zero backend change, ship immediately.
5. **"Thuộc về" sidebar card** — pure frontend, reuses `AREA_META[area].blurb` already imported — zero backend change, ship immediately, highest-ROI/lowest-effort item in this whole concept.
6. **"Khám phá thêm" footer strip** — pure frontend, reuses `INTEREST_META`, filtered by which entity types are present in `data.tourism`/`data.products` — zero backend change, ship immediately.
7. **Empty-state copy rewrite** — pure copy change to existing `.wp-empty-card` — zero backend change, ship immediately (route through `viet-content-optimizer` skill for tone-correct final Vietnamese, not the illustrative line above verbatim).

**Reusable across other pages:**
- The seeded-blob/outline motif technique generalizes to province-area pages (`khu-vuc/[area].vue`) and could eventually replace the 3 static MOTIFS entries with per-area generative variants too.
- `WardNeighborStrip` pattern (lateral chip-scroller sourced from a filtered sibling list) is directly reusable on entity detail pages (`dia-diem/[id].vue`) as "địa điểm gần đây trong cùng xã/phường" — closes a navigation gap noted in the broader UX audit (entity pages currently dead-end without lateral discovery).
- "Thuộc về" sidebar pattern (surfacing a parent-scope's already-written blurb) generalizes to any child-of-hierarchy page (entity → ward → area).
- Season-strip composable logic is already shared with EntityCard; no duplication risk.

**Feasibility guardrails respected:** CSS-tokens only (no Tailwind), no new paid services, dark-mode parity required for every new element (outline motif needs a `.dark` stroke-color variant; season-strip needs `.dark` text-opacity check; sidebar card reuses existing `.wp-card` dark rules already correct), `prefers-reduced-motion` must gate the line-draw animation and the season-pulse breathe (both trivial `@media` additions matching the existing pattern at the bottom of the current `<style>` block), CTA remains contact-only (no new booking-adjacent affordance introduced anywhere in this concept).
