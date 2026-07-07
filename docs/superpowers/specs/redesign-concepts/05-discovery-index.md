# Discovery Listings — `dia-diem/index.vue` ("Danh bạ địa điểm") + `kham-pha/[interest].vue` ("Khám phá theo chủ đề")

> **STATUS (2026-07-07): concept Ý TƯỞNG — KHÔNG thực thi nguyên văn.** Viết TRƯỚC declutter 3 đợt (ship 2026-07-07) và TRƯỚC chốt định vị 2026-07-06. Khi xung đột: code hiện tại + CLAUDE.md thắng. Trước khi thực thi bất kỳ mục nào: (1) dẹp mọi copy "miền Tây / ba tỉnh" — dùng khung tỉnh-Vĩnh-Long-mới; (2) KHÔNG dùng địa danh ngoài tỉnh (Cái Bè, Lai Vung… thuộc Đồng Tháp); (3) KHÔNG claim "đã xác minh"/quy mô đội ngũ; (4) re-ground line-number trên code hiện tại. Cảnh báo đầy đủ: 00-narrative-system.md. **LƯU Ý RIÊNG:** empty-state "thử Bến Tre" (mô hình 3 tỉnh) và "quán ăn miền Tây" (:122) là copy CẤM dùng.


> Prior grades: dia-diem/index.vue **6.0** · kham-pha/[interest].vue **6.5**
> Diagnosis: these are the two broadest browse surfaces on the site — and they currently read as **database screens with a nice hero glued on top**. The CE (cinematic-editorial) language stops at `.catalog-hero`; everything below (filter rows, grid, "Xem thêm") is bare utility. Filters are redundant across the two pages (type × area appears twice, worded differently). The grid unit (EntityCard) is undifferentiated — every card in Vĩnh Long looks like every card in Trà Vinh, whether it's a 400-year-old chùa Khmer or a bag of dried longan. **The job of this redesign is to make the act of browsing itself feel like wandering a market street or drifting down a kênh — full of small surprising turns — rather than paging through a spreadsheet with pretty chips.**

---

## 1. STORY ANGLE

These two pages are not "all the listings" and "listings filtered by topic." They are **the two natural doors a real visitor uses to start a trip**:

- **`dia-diem` = the almanac.** The exhaustive, ledger-like confidence of "everything is here, verified, current." Its story is **completeness and trust** — like the old wooden signboard at a bến đò (ferry landing) listing every stop downriver. The narrative angle: *"Không sót một nơi nào" (nothing left out)* — but told as a living almanac, not a spreadsheet. Every number (1.500+ điểm đến, 124 xã/phường) should feel like a boast, not a stat.
- **`kham-pha/[interest]`** = the curated mood. Someone arrives already leaning toward a craving — hungry, wanting nature, wanting culture, wanting to shop for gifts. Its story is **"someone who knows this land already sorted it for you."** Each interest (Ẩm thực, Thiên nhiên, Văn hoá, Làng nghề, Mua sắm & OCOP) is a *lens*, not a filter value — and should feel authored, like a chuyên mục (a magazine section) with its own editor's voice, its own palette accent, its own opening paragraph that a human clearly wrote (even if data-assembled).

**The reframe for both:** stop presenting "a list of entities" and start presenting **"a shelf of stories you can pull down."** The interaction model — chips, search, grid, load more — can stay (it's sound, fast, accessible IA). What must change is what happens in the eye and the hand *between* clicks: texture, motif, motion, language, and above all the **card itself**, which both pages share and neither has yet earned.

## 2. CINEMATIC HERO / THESIS

### `dia-diem` — "Cuốn sổ tay của cả miền Tây" (The almanac's opening page)
Keep the existing `.catalog-hero.cat-directory` structure (it's sound IA) but re-skin it as an **open-ledger / bến đò signboard** rather than a generic gradient banner:

- Replace the flat gradient background with the **phù-sa sediment signature** used elsewhere in CE, but horizontal here: a soft horizon-line gradient — sand at top, a thin river-tone band at 60% height, suggesting a riverbank horizon — with a faint **hand-drawn dashed route line** (SVG, static, decorative) meandering left-to-right behind the headline, like a river or a road on an old map. This is the single motif that ties "danh bạ" = *the map of everywhere*.
- The `📍` emoji icon becomes a **small compass rose glyph** (inline SVG, single-color, matches `--clay-600`) — more editorial, less emoji-app.
- Headline stays `Danh bạ địa điểm` but the subhead becomes a **counting voice**: *"1.532 điểm đến đã xác minh, từ cù lao giữa sông đến quầy hàng trong hẻm nhỏ — Vĩnh Long, Bến Tre, Trà Vinh, không sót nơi nào."* — the specificity ("quầy hàng trong hẻm nhỏ") is the curiosity hook; generic tourism copy would just say "many destinations."
- Stats row (`CountUp`) keeps its count-up animation but each stat gets a **one-word poetic gloss** beneath the number on hover/focus — e.g. hovering "1.532 địa điểm" reveals a second line in italic serif: *"từ chợ nổi đến chùa cổ."* Tiny, no layout shift (absolute-positioned tooltip-style reveal), respects reduced-motion.

### `kham-pha/[interest]` — "Một góc nhìn, một người kể" (A lens, a narrator)
The interest hero is already tinted per-interest (SIGNATURE 1) — good bones. Push it further into feeling **authored**:

- Add a **one-line editorial byline** under the description, styled as a dateline eyebrow (small caps, wide tracking, hairline rule before it) — e.g. *"BIÊN TẬP THEO MÙA · CẬP NHẬT THÁNG 7"* — signals a human curated this, not a query.
- The hero icon (`🍲`, `🌿`, `🛕`, `🏺`, `🛍️`) is upgraded from a bare emoji to the **same per-category motif glyph system** already built for `CatalogSpotlight`/`EntityCard` placeholders (`generateCategoryIcon`) — reuse it here so the interest icon and the card icons visually rhyme. Wrap it in the existing halo (`.int-hero-icon::before`) but make the halo shape subtly different per interest (circle for thiên nhiên, hex for làng nghề, arch for văn hoá) via a CSS `clip-path` variant — cheap, CSS-only, reinforces "this lens has its own shape."
- The `int-intro` curated-collection sentence (SIGNATURE 2, already good) becomes the **thesis statement of the whole page** — enlarge it slightly, set it in `--font-editorial` italic at `--text-lg`, and let it run full-width above the filter controls as a **standalone editorial dek**, not a boxed card. It is the single sentence a visitor should screenshot.

## 3. LAYOUT + RHYTHM

Both pages currently follow: hero → (extras) → flat filter row → flat grid → load more. Restructure into **editorial "sections with names,"** each with a clear head, consistent with how the homepage/itinerary pages already work:

**`dia-diem` flow (revised):**
1. Almanac hero (re-skinned, above)
2. `CatalogSpotlight` — keep, it's the one moment of magazine-grade real estate already working
3. **"Khám phá theo khu vực"** — region picker, reframed as **3 clay-thumbnail "province stamps"** (see §7) instead of plain quick-pick buttons — this is the biggest single visual upgrade available with zero new data
4. **"Duyệt theo loại hình"** — type picker, kept as horizontal scroll-row but re-skinned as a **"contact-sheet" filmstrip** (see §4/§7)
5. Interstitial fact banner — keep, it's a good rhythm break
6. Editorial paragraph — trim to 1 short paragraph max (currently 2; the second is procedural "báo sai dữ liệu" housekeeping that dilutes the story — move that line to page footer/EntityDetail instead, not here)
7. **Merged search+filter bar** — collapse the redundant type/area FilterChips rows (currently 3 separate filter UIs: quick-pick regions, scroll-row types, then FilterChips type AND FilterChips area again) into **one persistent, sticky-on-scroll "refine bar"**: search input + a single "Lọc" disclosure that expands both type and area chips together. This removes ~40% of the visual noise below the fold and gives the grid room to breathe.
8. The grid, now the "shelf" (see EntityCard rework, §7)
9. Load more

**`kham-pha/[interest]` flow (revised):**
1. Lens hero (re-skinned)
2. Editorial dek (enlarged intro sentence)
3. Interest-switcher chip row (keep — it's good cross-nav)
4. Area + type refine (collapse into the same sticky refine-bar pattern as `dia-diem`, for consistency — currently two separate `chip-row` blocks stacked, fine but visually generic; give the "Theo loại" row **live counts as visual weight** — larger chip for the type with the most items, e.g. a subtle `flex-grow` or font-size bump, so the row itself communicates "this is where the depth is")
5. Grid ("the shelf")
6. Cross-links ("Khám phá thêm") — keep, but reframe copy as **"đi tiếp"** wayfinding rather than a generic link list (see §6)

**Grid rhythm for both:** break the monotone `repeat(auto-fill, minmax(240px,1fr))` grid every **8–10 cards** with a **thin full-bleed textural divider** — not another card, not another CTA block, just a one-line typographic interruption (a short fact, a place-name in serif, or a subtle sediment-tick hairline) so scrolling through 24+ cards doesn't feel like an infinite database dump. This is cheap (CSS `grid-column: 1/-1` row insert) and is the single highest-leverage "make browsing feel like discovery" move for a long grid page.

## 4. TYPOGRAPHY

- Hero `h1` already uses `--font-editorial` (Fraunces) at `clamp(1.7rem,4.4vw,2.6rem)` — keep, it's correct CE.
- **New: the editorial dek/thesis line** (both pages) — `--font-editorial` italic, `--text-lg`, `line-height: var(--leading-relaxed)`, color `var(--ink)` not `--muted` (it should read as important prose, not metadata).
- **Section heads** ("Khám phá theo khu vực," "Duyệt theo loại hình") — apply the sediment-tick signature already used elsewhere in CE (vertical river→amber→clay tick before the heading) so these utility section heads visually join the CE family instead of reading as leftover catalog-page defaults.
- **Card name** (`h3.card-name` in EntityCard) — currently inherits base body font. Upgrade to `--font-editorial` at `--text-base/lg` weight 600. This alone makes every card on both pages instantly feel more premium — it's a single global CSS change with maximum reuse leverage (EntityCard is used everywhere).
- **Region "stamp" labels** (§7) — small caps, `--tracking-caps`, sans, to contrast against the serif place name — classic editorial pairing (label sans + headline serif).
- Numerals in stats/counts: tabular-nums where supported, so CountUp digits don't jiggle the layout as they animate.

## 5. SENSORY + MOTION + CURIOSITY

Both pages currently rely on generic `.reveal` fade-ins and hover-lift on cards. Keep those (they're correct, restrained CE motion) but layer in a few **discovery devices** that specifically serve *browsing* pages:

- **Contact-sheet filmstrip for type-picker** (`dia-diem` "Duyệt theo loại hình" and the interest "Theo loại" row): each chip gets a **thin category-color underline** that only draws in on hover/focus (a 2px line animating left→right, `transform: scaleX()`, GPU-cheap) — evokes flipping through indexed photo negatives, reinforces "each type is its own visual world" without new images.
- **Province stamp hover**: region picker cards (§7) tilt very slightly (`rotate(-1deg)` to `rotate(0)`) on hover like a photograph being picked up off a table — respects `prefers-reduced-motion`.
- **Card image crossfade on carousel arrows** (EntityCard already has multi-image dot/arrow nav) — currently instant swap via `:key`; add a 150ms opacity crossfade so multi-photo cards feel like flipping a small photo stack, not a jump-cut.
- **"Vừa thêm" pulse**: the existing `isNew` badge (< 14 days) currently is a static pill. Give it a **single slow pulse ring** (one iteration only, on mount, not looping — avoid AI-slop "everything breathes forever") so genuinely new listings catch the eye once, then settle.
- **Scroll-linked river-tick progress**: on `dia-diem` only (the almanac, longest page), a **very thin fixed-position tick** in the page gutter (desktop only, opt-out on mobile/reduced-motion) that fills river→amber→clay as the visitor scrolls the grid — a subtle "how much of the almanac have I seen" wayfinding cue, echoing the phù-sa signature already used for section dividers elsewhere, repurposed as a scroll indicator. This is the closest thing to a "next things to explore" progress device without adding gamified clutter.
- **Empty-state and load-more copy** get a curiosity rewrite (§9) instead of generic "no results" utility text.
- Avoid: parallax on the grid itself (motion-sick risk at high card density), autoplay carousels, looping shimmer/glow — these are the AI-slop tells the brief explicitly warns against.

## 6. UX FLOW

**Information scent chain:** hero (confidence/mood) → spotlight or thesis (this is worth reading) → region/type pickers (narrow by instinct, not form-filling) → grid (the payoff) → card → detail page → contact CTA. The redesign's job is to shorten the distance between "I feel curious" and "I'm looking at one specific real thing."

Concrete flow fixes:

- **Collapse triple-redundant filtering on `dia-diem`.** Today a visitor can set "type" via the quick-pick region cards' sibling type scroll-row, AND via `FilterChips` type row, AND area via both region quick-picks and `FilterChips` area row — four controls doing two jobs. Consolidate to: (a) the two discovery sections above the fold stay as *inspiration entry points* (clicking one scrolls to grid + sets filter, as today), (b) below the editorial paragraph, one **single sticky refine bar** with search + an expandable "Lọc" panel holding both type and area as the *only* other place to change filters. This removes visual redundancy without removing any capability.
- **Make "Xem thêm" feel like continuing a story, not paging a table.** Change the button label from a bare count (`Xem thêm (còn 41)`) to a **teaser of what's next**: sample the next hidden card's type/area and surface it, e.g. `Xem thêm — 41 nơi nữa, kể cả làng nghề Mang Thít →`. Cheap (client already has the next page's data pre-fetched or fetchable), high curiosity payoff, still honest (no fabrication — only real upcoming item names).
- **Cross-links section on `kham-pha`** ("Khám phá thêm") currently reads as a generic footer nav grid. Reframe as **"đi tiếp"** (where to next) with each card phrased as a next *chapter*, not a menu item — e.g. instead of "Bản đồ / Xem trên bản đồ," use "Xem trên bản đồ — vị trí thật của từng nơi trong chuyên mục này." Ties the cross-link back to the specific interest just browsed.
- **Search → grid anchor** on `dia-diem` (`gridAnchor`/`scrollToGrid`) already smooth-scrolls correctly — keep.
- **Zero-result state**: currently generic "Không tìm thấy địa điểm." Make it *helpful and warm*, e.g. surface 2–3 nearby-type suggestions as clickable chips inline in the empty state ("Không có 'quán cà phê' ở Trà Vinh — thử Bến Tre? hoặc xem tất cả quán ăn?") rather than only a bare "Xoá bộ lọc" button.

## 7. PREMIUM CUES

- **EntityCard is the single highest-leverage component on both pages** (repeated 20–500+ times) and currently reads as a stock e-commerce card (image, tag pill, title, meta row, badges). Concrete upgrades, all CSS/markup-level, no new data required:
  - Serif card title (see §4).
  - Cover-tag pill (`.cover-tag`, currently a flat rounded label) gets a **hairline top border in the category accent color** instead of solid fill background — reads as a museum-label / spec-tag rather than an app badge.
  - For **generated-placeholder cards** (the ~97% without real photos) — the biggest imagery-ceiling problem — add a **very subtle grain/paper texture overlay** (inline SVG noise filter, already used elsewhere per the anti-AI-slop playbook) at ~4% opacity on top of the gradient, so placeholder cards read as "designed illustration" rather than "no photo available." This is the single most important visual-credibility fix on both pages, since the vast majority of grid cards are placeholders.
  - OCOP star badge (`.badge.ocop-5`) already has a nice gradient treatment — extend the same "foil" gradient treatment to the **season "Đang mùa" badge**, since peak-season is itself a premium signal ("this is the moment to go") and currently looks like a plain pill.
  - Rating stars (`.cr-stars`) currently plain `★`; add `text-shadow` micro-glow consistent with the accent token for 5.0-only ratings, so a perfect score visually stands out from a 4.2.
- **Region "province stamp" cards** (replacing plain `quick-pick` buttons in `dia-diem`'s "Khám phá theo khu vực"): each becomes a small **postcard-stamp shaped card** — rounded-rect with a serrated/torn top edge (CSS `clip-path` zigzag, decorative only), the province emoji as a corner mark, province name in serif, and the existing `blurb` copy (already excellent — "Miệt vườn cam sành, khoai lang, bưởi Năm Roi và làng gốm Mang Thít") set as the stamp's "caption." This single change turns a generic pill-button row into something that feels *collected*, like postage stamps from each place — directly serves the "story" thesis with zero new copy needed (the blurbs already exist in `AREA_META`).
- **Sticky refine bar** should have the same soft `--shadow-sm` + top hairline treatment used on the site's header, so it reads as a deliberate control surface, not a bolted-on utility strip.
- **Focus states**: both pages already have solid `:focus-visible` rings — keep and extend to any new interactive elements (stamp cards, filmstrip chips).
- **Dark mode**: every new visual device above must have an explicit `.dark` counterpart (grain overlay opacity down, stamp shadow softened, tick colors shifted to the existing dark-mode accent variables) — no exceptions, matching site-wide parity mandate.

## 8. CULTURAL AUTHENTICITY

- The area blurbs already in code are the strongest authenticity asset on either page (`AREA_META`: cam sành/khoai lang/bưởi Năm Roi/gốm Mang Thít for Vĩnh Long; kẹo dừa/mật hoa dừa/bưởi da xanh for Bến Tre; ao Bà Om/chùa cổ/dừa sáp Cầu Kè/bún nước lèo for Trà Vinh; Khmer chùa culture for văn-hoá interest) — the redesign's job is to **stop hiding this copy in a small button label** and instead make it load-bearing: it becomes the stamp caption, the intro dek seed text, and a rotating "did you know" line in the interstitial.
- Avoid generic tourism iconography: no palm-tree/beach/passport-stamp clip-art motifs (a classic AI-slop/generic-travel-blog tell). Use instead: **ghe/xuồng (boat) silhouette**, **cầu khỉ (monkey bridge)** line motif, **lá dừa (coconut-frond) weave pattern** as a background texture option for the "mua-sam/OCOP" interest tint, **Khmer temple roofline silhouette** for "van-hoa" — all as thin single-color line motifs consistent with the existing `generateCategoryIcon` glyph system, not photographic clipart.
- The "Trong chuyên mục này" narrative sentence (SIGNATURE 2, already in code) is a good anti-generic device — extend the same real-data-only narrative pattern to `dia-diem`'s stats hover-glosses (§2) so no invented facts creep in; every poetic line must trace to real counts/attributes already in the DB (Track-H / anti-hallucination discipline).
- Reject: sunset-beach hero clichés, "khám phá miền Tây" as filler headline text without specificity, generic map-pin icons where a real motif (compass rose, ghe, cầu khỉ) can carry more meaning.

## 9. COPY VOICE

Voice: warm, specific, a little proud — like a local person naming their own hometown's best-kept things, not a tourism-board brochure. Short sentences. Concrete nouns (bến đò, cù lao, gốm Mang Thít) over abstract ones ("trải nghiệm độc đáo").

Example lines:

- `dia-diem` hero subhead (replacing current generic line): *"1.532 điểm đến đã xác minh, từ cù lao giữa sông đến quầy hàng trong hẻm nhỏ — Vĩnh Long, Bến Tre, Trà Vinh, không sót nơi nào."*
- `dia-diem` stat hover-gloss (under "1.532 địa điểm"): *"từ chợ nổi đến chùa cổ."*
- `kham-pha/lang-nghe` editorial dek (in place of generic description-only line): *"Đất phù sa nặn nên gốm, dừa già kéo thành kẹo, lác xanh dệt thành chiếu — mỗi làng nghề ở đây đều bắt đầu từ một cái cây, một dòng kênh."*
- Load-more teaser: *"Xem thêm — 41 nơi nữa, kể cả làng nghề gốm Mang Thít →"*
- Empty state (no generic "not found"): *"Chưa có 'quán cà phê' ở Trà Vinh trong danh bạ — thử Bến Tre, hoặc xem tất cả quán ăn miền Tây?"*
- Cross-link reframe ("Khám phá thêm" → map card): *"Xem trên bản đồ — biết chính xác nơi này cách bến đò gần nhất bao xa."*

## 10. SIGNATURE MOMENT

**The "province stamp" region picker on `dia-diem`.** A row of three (plus "liên vùng") postage-stamp-shaped cards — serrated edge, serif province name, corner emoji mark, and the existing rich `AREA_META` blurb as caption — replacing what is today three plain rounded buttons. It costs no new data, reuses copy already written, needs only CSS (`clip-path`, typography, a hover tilt), and single-handedly turns the least-designed part of the page into the most collectible-feeling one. It is also **directly reusable** as the "region" visual language anywhere else on the site that surfaces the three provinces (homepage, footer, map page), giving it outsized leverage for a small build cost.

Runner-up signature: the **grain-texture placeholder cards** — because ~97% of every grid on the whole site is a placeholder card, fixing its "flat gradient with a glyph" feel into "designed illustration with paper texture" quietly upgrades far more surface area than any hero change could.

## 11. COMPONENTS + FEASIBILITY

All CSS-tokens (no Tailwind), images AI-gen only (no new images required for any device above — everything is CSS/SVG/typography), CTA remains contact-only (no changes to CTA model needed on these pages — they are browse surfaces, not detail pages), full dark-mode pairs required, `prefers-reduced-motion` guards on every animation.

**New/modified components (reusable across the app, not just these two pages):**
- `EntityCard.vue` — serif title, hairline cover-tag, grain-texture overlay on generated placeholders, foil-gradient season-peak badge, glow on perfect ratings, crossfade on carousel image swap. **Highest-reuse item** — used on nearly every listing surface site-wide (homepage, dia-diem, kham-pha, du-lich, ocop, tim-kiem, saved, etc.), so this single component change upgrades the whole site's grid feel, not just these two pages.
- New `ProvinceStamp.vue` (or inline markup in `dia-diem/index.vue`) — replaces plain `.quick-pick.region-pick` buttons. Reusable on homepage region-nav and footer if desired.
- `CatalogRefineBar.vue` (new, shared) — sticky search+filter disclosure consolidating the currently-duplicated type/area FilterChips rows. Reusable on any future catalog page (du-lich, ocop, san-pham if they exist) to kill the same redundant-filter pattern elsewhere.
- Section-divider partial (`GridDivider.vue` or a simple `<div class="grid-divider reveal">…</div>` pattern) — inserted every 8–10 EntityCards via a computed `chunk()` helper in the template `v-for`.
- CSS additions to `catalog.css`: `.almanac-hero-motif` (dashed route SVG background), `.province-stamp` block, `.filmstrip-chip` underline-draw hover, `.grid-divider`, `.card-name` font override, `.cover-generated::after` grain overlay, `.badge.peak` foil gradient, scroll-tick indicator (`.almanac-progress-tick`, desktop + non-reduced-motion only).
- No backend/API changes needed — every device above is presentation-layer only, consuming data already returned by `/api/entities` (`AREA_META`, `attributes.ocop`, `attributes.rating`, `season`, `updatedAt`, `relationship_total` are all already in the payload per current code).
- Feasibility note on the load-more teaser (§6): requires the client to know the *next* hidden item's label before the user clicks — either (a) already-fetched `extra`/next-page data client-side prediction (cheap, since `PAGE=24` and total is known, could prefetch page N+1 quietly), or (b) simpler MVP: just teaser using the *last item currently loaded*'s type as a "kể cả…" hook without prefetching ahead — ships without any new network behavior.
