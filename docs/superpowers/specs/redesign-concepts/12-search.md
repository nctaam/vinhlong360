# tim-kiem.vue — Search: "Cửa Ngõ Tò Mò" (The Curiosity Gate)

*Prior grade: 6.0 · Current state: functional SERP-style search (input + autocomplete + result grid + AI-assist + zero-state links) with zero cinematic-editorial (CE) treatment. Emoji icons everywhere, generic `catalog-hero`, link-soup empty state.*

**Context note honored:** Curiosity-critical. This concept treats "no query yet" not as an empty box to fill but as the single best real-estate on the page for seduction — a doorway that shows you the province is already telling stories, before you've typed a letter.

---

## 1. Story Angle

Search is not a utility on this platform — it is **the moment of a question forming**. Every other page answers a category ("du lịch", "sản phẩm"); only search answers a *person's* half-formed curiosity: "bánh xèo ở đâu ngon", "chỗ ngắm hoàng hôn", "trái cây tháng 8". The story angle: **the search page is a người dẫn đường (a local guide) leaning in and asking "Anh/chị đang muốn tìm gì vậy?"** — not a database query box.

Two acts:
- **Act I — Trước khi gõ (before you type):** the page itself performs curiosity. It surfaces what *others just searched*, what *is in season right this week*, what you *recently touched* — proof the province has a pulse. This is the page's real hero moment, more important than the input field itself.
- **Act II — Sau khi gõ (after you type):** the result set is reframed from "SERP list" to "đây là những gì phù sa mang tới cho câu hỏi của bạn" — results feel curated by a guide, not spat out by an index, via type-breakdown storytelling, AI assist as a **whispered aside** (not a bot widget), and next-step rails that continue the conversation.

## 2. Cinematic Hero / Thesis

Replace `catalog-hero.cat-search` (icon + h1 + p, identical to every other catalog page) with a **living, non-static hero specific to search**: a full-width band, sand ground, with the masthead serif treatment (dateline eyebrow + Fraunces h1), but the subhead position is occupied by a **rotating ticker of real, current search-worthy questions** pulled from trending queries + in-season entities — e.g. cross-fading every 4s through:

> "bún nước lèo ở đâu chuẩn vị Khmer?" → "mùa nào ăn bưởi năm roi ngon nhất?" → "homestay ngủ đêm giữa vườn dừa?" → "chợ nổi còn họp không?"

The search input itself becomes the hero's focal object — oversized, centered, sitting on a hairline underline (not a boxed input), with the phù-sa sediment tick (river→amber→clay) as a **vertical accent to the left of the input**, echoing the section-head signature used elsewhere. Placeholder text itself rotates through the same ticker phrases when idle (typewriter-style, respecting reduced-motion by freezing on one phrase).

This turns "an empty search box" into a page that is *already mid-conversation* — curiosity modeled for the visitor before they've done anything.

## 3. Layout + Rhythm

Single-column editorial spine (matches CE `--measure-read` discipline for text blocks; grid widens for card rows), four rhythm states:

1. **Masthead band** (full-bleed sand, dateline eyebrow "TÌM KIẾM · VĨNH LONG · BẾN TRE · TRÀ VINH", Fraunces h1 "Bạn đang tò mò điều gì?", rotating ticker subhead, hero-scale input).
2. **Zero-query state ("Trước khi gõ")** — this is the redesign's center of gravity. Replaces the current flat "quick-picks grid + recent + cross-links" stack with a **tiered discovery cascade**:
   - Row A: *Đang được tìm nhiều* (trending queries, horizontal scroll-chips, live-feeling)
   - Row B: *Đúng mùa này* (2-3 EntityCards for in-season items — reuses `useSeason`, gives search a temporal hook)
   - Row C: *Bạn đã xem* (recentItems, kept, but restyled as a "tiếp tục hành trình" filmstrip, not a plain grid)
   - Row D: *Khám phá theo chủ đề* (existing quick-picks, restyled — see §4/§7)
   - Row E: cross-links footer (kept, restyled)
   Each row gets a CE `section-head` with sediment tick + serif label, so scrolling down feels like turning pages of a guide, not scanning a sitemap.
3. **Query state ("Sau khi gõ")** — result-summary reframed as an editorial strap line, not a SERP meta line; AI assist recast as "Lời khuyên từ người local" aside card; results grid unchanged structurally (EntityCard reused) but framed with a one-line curatorial intro sentence generated from the type breakdown (e.g. *"Phù sa mang về cho bạn 4 món ăn, 3 điểm đến và 1 lễ hội."*).
4. **Zero-result recovery** — reframed as "chưa tìm thấy, nhưng đây là..." with the JourneyActionRail doing more visual work (see §6).

Responsive: on mobile, ticker/ input hero collapses to two lines max; discovery cascade rows become horizontal swipe-strips (already a strong mobile pattern for Row A/C); quick-picks stay grid but 2-column.

## 4. Typography

- Masthead h1: `var(--font-editorial)` (Fraunces), weight 600, negative tracking, large fluid clamp (matches area-hero treatment) — "Bạn đang tò mò điều gì?"
- Dateline eyebrow: existing wide-tracked caps + hairline convention, small caps `TÌM KIẾM`.
- Rotating ticker subhead: **not** serif — use `--font-sans` italic-styled via letter-spacing/opacity fade, smaller, muted-ink, to read as a "murmur" distinct from the authoritative h1.
- Search input text: bump to `--text-xl`/`--text-2xl`, serif-adjacent numerals stay sans (input is a tool, not prose) — but placeholder copy in a light-italic sans to feel conversational.
- Section-head labels in the discovery cascade (`Đang được tìm nhiều`, `Đúng mùa này`, etc.): reuse the serif `section-head h2` styling already established site-wide (do not invent new h2 style — pure reuse per feasibility note).
- Result curatorial strap-line (Act II): serif, italic, `--text-lg`, to visually mark it as "narrator's voice" distinct from raw data (the count badges stay sans/mono-ish for scanability).

## 5. Sensory + Motion + Curiosity (Discovery Devices)

Curiosity ignition without over-animating:

- **Ticker cross-fade** (hero subhead + input placeholder): 4s interval, opacity+4px translate, `--ease-out`, pure CSS `@keyframes` driven by a small JS index-cycle (cheap, no library). Freezes at first phrase under `prefers-reduced-motion`.
- **Trending chips (Row A)**: each chip has a subtle "pulse" dot (like the existing `peak-dot` on EntityCard) that indicates "hot right now" — reuses an existing visual token instead of inventing a new one.
- **Season row (Row B)**: Ken Burns-style slow zoom on card cover images already exists sitewide for hero imagery; here apply the *existing* subtle image hover-scale from EntityCard (no new motion system).
- **Filmstrip for "recent"**: horizontal scroll-snap strip with soft edge-fade masks (`mask-image: linear-gradient(...)`) hinting more content off-screen — a pure-CSS discovery device that invites a swipe.
- **Autocomplete suggestions**: keep existing dropdown mechanics (proven, accessible with roving `aria-activedescendant`), but restyle the suggestion row for entity type to show the **category color hue strip** (leaf/clay/river/amber per TYPE_META cat) as a 3px left-border accent — turns the dropdown into a tiny preview of the tri-province palette, reinforcing brand without new components.
- **Sensory language woven into copy**, not decorative icons: trending-chip labels and the strap-line use sensory verbs ("thưởng thức", "ướp", "chín rộ", "ghé bến") instead of generic "xem thêm."
- Avoid: no confetti, no bouncing emoji, no auto-playing video — keeps it premium, not slop.

## 6. UX Flow

- **Zero-friction re-entry**: input keeps focus ring treatment; Enter/typeahead unchanged (already solid a11y — keep as-is, it is a strength not a weakness).
- **Before typing**: cascade rows are all *one tap away* from a fresh search or an entity page — every trending chip and quick-pick is a live link, no dead ends.
2 clear jobs for the zero-query state: (a) *inspire a query* (trending, seasonal), (b) *resume a journey* (recently viewed). This dual-job framing is what turns "link-soup" into "discovery."
- **After typing, with results**: curatorial strap-line → grid → (optional) AI aside → JourneyActionRail "Bước tiếp theo" — reduce the current stacked-sections feel by tightening vertical rhythm between result grid and people/posts sections (currently three separate `.search-section` blocks with equal weight — rebalance so entity results are visually primary, people/posts are a secondary "cũng có trong cộng đồng" strip beneath, collapsed by default if >0 but small, to avoid diluting the primary intent).
- **After typing, zero results**: this is a recovery moment, not a dead end — EmptyState kept, but paired immediately with 2-3 *close alternative* EntityCards (using existing `fetchEntitySuggestions`/typeahead infra or a loose text-similarity fallback) titled "Có phải bạn muốn tìm…" before falling to generic category CTAs. This directly targets the biggest curiosity-killer: a wall of "no results" text.
- **Contact-only compliance**: no change needed — search has no transactional CTA today and none is introduced; JourneyActionRail continues to route to entity/contact surfaces, never a booking form.

## 7. Premium Cues

- Sediment-tick accent reused consistently: on the hero input, on every cascade section-head, and as the new type-color strip in autocomplete rows — one motif, three placements, feels intentional rather than decorative.
- Quick-pick tiles: replace raw emoji-in-a-box (🌿🍊🏡⭐🎊🗓️) with the **same per-category SVG glyph system already built for EntityCard placeholders** (`generateCategoryIcon`) at small size — instant visual coherence with the rest of the site instead of looking like a different, older UI generation. This is a pure reuse win: zero new asset cost, immediate premium bump.
- Trending chips carry a tiny live/hot indicator (reused peak-dot token) rather than a static "🔥" emoji.
- Micro-typographic care: query echo in Act II uses curly quotes „…" or proper Vietnamese-style guillemets/quotes consistently (currently plain `"` ASCII quotes) — small but visible craft signal.
- Empty-state and error-state icons currently emoji (⚠️🔍) — swap for the same restrained line-icon/SVG glyph treatment as the rest of CE surfaces (no new icon library needed — inline SVG, single color, matches ink/muted tokens).

## 8. Cultural Authenticity

- Trending/ticker copy pool should be seeded with genuinely regional phrasing and specificities: "chợ nổi Cái Bè còn họp giờ nào", "bưởi Năm Roi chính vụ", "dừa xiêm Bến Tre uống tại vườn", "chùa Khmer Trà Vinh lễ hội Ok Om Bok", "đờn ca tài tử ở đâu nghe được", "cù lao nào yên tĩnh nhất" — avoid generic "top 10 địa điểm" tourism-clickbait phrasing.
- Seasonal row (Row B) is the direct expression of "miệt vườn" logic — chín rộ theo mùa, không phải catalog tĩnh; label copy should name the fruit/season, not just say "Sản phẩm nổi bật."
- The three-province autocomplete color strip (leaf VL / river-ish BT / amber-clay TV per established palette mapping) quietly reinforces regional identity without a heavy-handed "chọn tỉnh" selector — search stays unified (post-merger, no province splitting per memory note) while still whispering provenance.
- AI assist card copy reframed from a bot-voice disclaimer box to "Lời khuyên từ người local" with a small quieter disclaimer line — keeps compliance (still labeled AI-generated) but voice-matches a guide, not a chatbot vendor.

## 9. Copy Voice

Editorial, warm, second-person, unhurried — a local friend, not a search engine.

- Masthead h1: **"Bạn đang tò mò điều gì?"**
- Ticker/placeholder rotation examples: *"bún nước lèo ở đâu chuẩn vị Khmer?"* · *"mùa này bưởi Năm Roi ngọt chưa?"* · *"ngủ đêm giữa vườn dừa, ở đâu?"*
- Row A label: **"Đang được hỏi nhiều"** (not "Trending searches")
- Row B label: **"Chín rộ đúng mùa này"**
- Row C label: **"Tiếp tục nơi bạn dừng lại"**
- Result strap-line example: *"Phù sa mang về cho bạn 4 món ăn, 3 điểm đến và 1 lễ hội quanh câu hỏi này."*
- Zero-result reframing: *"Chưa thấy đúng ý bạn — nhưng biết đâu những gợi ý này lại hợp."*

## 10. Signature Moment

**The rotating "câu hỏi đang được hỏi" ticker living inside the search input itself** — the search box that seems to already know what Vĩnh Long is thinking about right now, cycling real regional questions before you've typed anything. It converts the single most boring UI element on the internet (a search box) into the page's most alive, most re-visitable detail — and it's the answer to the brief's context note: zero-query stops being link-soup and becomes the moment the province leans in first.

## 11. Components + Feasibility

**New (small, CSS-token-only, no new deps):**
- `SearchTicker` — tiny composable/component cycling a copy array via `setInterval` + CSS crossfade; pauses on `prefers-reduced-motion`; array can start as a static curated list (no backend needed for v1), later swap to real trending-query telemetry already captured via `trackSearch`/`useUserEvents` (reuse existing analytics pipeline — no new tracking infra).
- `SearchDiscoveryRow` — thin wrapper applying the shared `section-head` + horizontal scroll-snap-with-edge-mask pattern; reusable for Row A/B/C and **also reusable on other catalog pages** (e.g. `du-lich.vue`, `san-pham.vue` "recently viewed" strips) — flagged explicitly as cross-page reusable.
- Autocomplete row category-color left-border strip — a 2-line CSS addition to existing `.sug-item`, no new component.
- Quick-pick glyph swap — replace emoji spans with `generateCategoryIcon(cat)` `v-html`, already exists in `useCategoryPlaceholder` composable, zero new asset work.

**Reused as-is (feasibility win — most of the page's bones are fine):**
- `EntityCard` for all result/seasonal/recent grids (already scheduled for its own CE-ification elsewhere per audit — this page just consumes it).
- `AISearchAssist` component logic untouched — only its container framing/copy (§8) changes, no behavior change, still opt-in click-to-load (respects LLM-cost discipline, §B8).
- `JourneyActionRail`, `EmptyState`, `SkeletonGrid`, autocomplete keyboard/aria logic — all kept verbatim, they are already accessible and solid.
- `useReveal()` scroll-reveal — apply to the new discovery rows exactly as already applied to `.reveal` blocks elsewhere; no new animation system.

**CSS-only additions:** hero ticker crossfade keyframes, edge-fade scroll mask, category-color border-left utility class, sediment-tick reuse on hero input (already a shared class from area-hero — confirm shared selector rather than duplicating). All within `--space-*`, `--text-*`, existing color tokens (`--river`/`--leaf`/`--amber`/`--clay` if defined as such, else map via `TYPE_META[cat]` to existing `cat-*` badge color classes already used in `EntityCard`/`cover-tag`).

**Dark-mode + reduced-motion:** ticker freeze-on-reduced-motion (already specified); edge-fade masks use existing dark surface tokens (`--card`/`--bg-alt`) so no separate dark override needed beyond what `.dark` selectors already cover on reused components.

**Explicitly NOT built:** no live "trending now" backend ranking system for v1 (curated static array is enough to prove the moment; wiring to real `trackSearch` aggregates is a fast-follow, not blocking); no AI-generated ticker text (curated human copy only, per B8 LLM-cost discipline — this is presentation, not a live LLM call).
