# Tourism Hub + Lodging — `du-lich.vue` (umbrella magazine) + `luu-tru.vue` ("wake up on the river")

> Prior grades: du-lich 7.5/10 (umbrella hub), luu-tru 7.0/10.
> Both are currently **catalog-tier**: `.catalog-hero` banner → `CatalogSpotlight` → horizontal `EntityCard` rows → editorial text block → filterable grid. Cinematic-editorial (CE) language exists only as a design *system* (tokens, fonts, phù-sa motif) — neither page's hero nor body actually wears it yet. This concept brings CE all the way through both pages and treats `EntityCard` as the keystone fix that lifts every catalog page at once.

---

## 0. Reading the two pages together

`du-lich.vue` is the **table of contents for the whole province** — it doesn't sell one thing, it sells the *idea that there is a whole world here*: experiences, attractions, craft villages, dishes, and (cross-linked) lodging, sliced by category and by month. Its job is orientation + seduction into the deeper catalog.

`luu-tru.vue` is the **one page on the site where the visitor imagines their own body in the place** — lying in a hammock, hearing a rooster, smelling bưởi blossom through a window. Every other catalog page is "look at this." Lodging is "picture yourself here at 6am." That's the emotional unlock this page currently misses entirely — it reads as an accommodation directory (area chips, type pills, price ranges in prose) rather than an invitation to sleep by the water.

Both share the exact same component skeleton today (`catalog-hero` → `CatalogSpotlight` → featured row → interstitial → editorial → grid → cross-links), which is good for engineering economy — the redesign keeps that shared skeleton but re-skins/re-sequences it so du-lich reads as an atlas and luu-tru reads as an overnight promise.

---

## 1. STORY ANGLE

**du-lich.vue — "Đây không phải một danh sách. Đây là một tấm bản đồ sống."**
The story is: *the Delta has more textures than a tourist expects, and each one has its own rhythm of the year.* Not "200 attractions" but "five ways to spend a day here, each tied to what the land and water are doing this month." The page's job is to make the visitor think *"I didn't know you could do THAT here"* at least three times before they hit the grid.

**luu-tru.vue — "Bạn sẽ thức dậy ở đâu?"**
The story is not "where to sleep" but *what you wake up to*. A homestay nhà vườn in An Bình is not a room, it's a specific sensory promise: fruit dropping in the yard at dawn, a ferry engine on the Cổ Chiên, breakfast cooked by the person whose garden you're sleeping in. The page should sell **the morning**, not the mattress — because that's the one thing a hotel booking site can never promise and vinhlong360 can, because it knows these homestays personally (contact-only, no OTA gloss).

---

## 2. CINEMATIC HERO / THESIS

### du-lich.vue — "Living Atlas" hero
Replace `.catalog-hero` (emoji + h1/p + stat pills) with a full-bleed CE masthead:
- **Background**: a slow, barely-perceptible Ken-Burns cross-fade cycling through 4–5 real hero images (best available per category — experience/attraction/craft) OR, where real photos are absent, the category SVG-motif system rendered LARGE and slow-panned (the motif becomes a design feature, not an apology) with the phù-sa gradient tick behind it.
- **Eyebrow** (editorial dateline style, matches the deployed CE pages): `ĐỒNG BẰNG SÔNG CỬU LONG · VĨNH LONG — BẾN TRE — TRÀ VINH` in wide-tracked caps over a hairline.
- **Headline** in Fraunces, sized `--text-5xl`, NOT the current plain `pc('hero_title')` string treatment — break it into two lines with differential weight, e.g.:
  *"Ba tỉnh, một nhịp sông."* (large, serif, clay) / *"Khám phá theo mùa nước, theo mùa trái, theo mùa lễ."* (smaller, sand-on-dark, sans)
- **Thesis interaction**: a horizontal "**mode dial**" beneath the headline — 3–4 pill toggles that are NOT filters (don't touch the grid below), but instead swap the hero's background image + one line of copy: `Trải nghiệm` / `Ẩm thực` / `Làng nghề` / `Lưu trú`. This is the curiosity igniter — clicking "Ẩm thực" cross-fades the hero photo to a dish shot and the subhead to a food-specific line, before the visitor has scrolled at all. Costs nothing extra (data already fetched), teaches the visitor the page has range, in 2 seconds.
- Stat pills (`CountUp`) survive but move to a slim glass strip anchored to the bottom edge of the hero (M3 `--glass-medium` blur), not floating in the flow — reads as a "dashboard" ribbon under the cinematic image, à la the homepage bento hero.

### luu-tru.vue — "Wake-up" hero
This is the flagship moment for the whole unit. Replace the accommodation-directory hero with a **first-person morning vignette**:
- Full-bleed hero photo (best real accommodation photo available; motif fallback styled as a "window view" — soft dawn gradient with a leaf/river motif silhouette, framed like looking out a window, using `--cat-accommodation` gradient (#5B6CC4→#8B9AF0 — a cooler, dawn-blue departure from the other pages' warm clay, intentionally, because lodging = rest = cool/calm register)).
- **Headline**: not "Lưu trú" as a category label but a sensory line set in Fraunces italic-weight feel:
  *"Thức dậy giữa vườn, nghe chim trước khi nghe chuông báo thức."*
  subhead (sans, muted): *Homestay nhà vườn, resort ven sông, khách sạn phố — chọn nơi bạn muốn mở mắt vào buổi sáng ở miền Tây.*
- **Signature micro-interaction**: a thin animated horizon line across the hero — a CSS gradient sweep that very slowly (18–20s, `--dur-kenburns`-scale, respecting reduced-motion) shifts from night-blue to dawn-amber to day-sand, literally showing "sunrise" over the hero without any JS, using the existing `--season-*` gradient token pattern. This is the single moving element — restrained, not busy.
- Stats (nơi lưu trú / theo khu vực) become a **"chọn thức dậy ở đâu"** micro-nav directly under the hero: not stat pills but three photographic "region windows" (Cù lao An Bình · Chợ Lách · Cồn Phụng — whichever areas actually have supply), each a small round-cornered image/motif tile that acts as both a stat AND a jump-link, replacing the current plain quick-pick buttons below.

---

## 3. LAYOUT + RHYTHM

**du-lich.vue** keeps its five-act structure but re-paces it as a magazine, not a list of sections:
1. Hero (atlas thesis, mode dial)
2. **"Bốn cách sống trong ngày"** — NEW: a large 2×2 or asymmetric editorial grid (not a scroll-row) introducing the four experience *registers* (sông nước / miệt vườn / làng nghề / tâm linh-di tích) each with one striking image/motif + one sentence, each linking to a pre-filtered grid view. This replaces the flat CatalogSpotlight-then-featured-row redundancy (today spotlight + featured are two different UI patterns showing overlapping content — collapse them).
3. Category sections — keep scroll-rows (they work, they're the site's Netflix-row pattern) but reorder so **season is the connective tissue**: each category row gets a small "đang đúng mùa" contextual note when applicable (data already exists via `inSeason`/`relevanceScore`), so the rhythm becomes "here's what's good to do, and here's why now."
4. Interstitial (keep, it's a good pacing breath)
5. Editorial long-read — restyle into true CE reading column (`--measure-read: 68ch`, drop-cap first paragraph, phù-sa tick beside each `<h2>`) instead of the current plain prose block
6. Grid (full catalog) — keep, it's necessary utility, but re-skin controls bar per §11
7. Cross-links — keep, add hover-lift + directional micro-copy

**luu-tru.vue** restructure — the season/category logic isn't the organizing idea here, geography + morning-experience is:
1. Hero (wake-up thesis + region windows)
2. **"Ba kiểu qua đêm"** — NEW editorial triad (homestay nhà vườn / resort sinh thái / khách sạn phố) replacing the prose-only "Các loại hình lưu trú" section — each gets an image/motif card + price band + one-line sensory description + a "phù hợp nếu bạn muốn…" micro-persona tag (romantic getaway / gia đình / phượt bụi). This is UX-load-bearing: it's the decision tree visitors actually have in their head, made visible.
3. Region quick-picks (upgraded, see §2)
4. Featured carousel (keep scroll-row, it's proven)
5. Interstitial (keep)
6. Editorial — booking advice, restyled as a compact "sổ tay đặt phòng" sidebar-style callout box (peak dates / how to contact / group deals) rather than a full prose section — this content is *reference*, not *narrative*, so give it reference-styling (a small card, not H2 paragraphs) to keep the page's editorial rhythm from getting bogged in logistics.
7. Grid — but reconsidered layout: because lodging benefits from *comparison*, default to a slightly denser card with visible amenity icons/price already surfaced (EntityCard already computes `cardMeta.price` — just needs to render for accommodation type, see §11)
8. Cross-links

**Responsive posture (both):** hero mode-dial / region-windows collapse to a horizontal swipeable strip on mobile (same touch pattern as `scroll-row`, already proven on the site). Editorial triad/quad grids collapse to single column, image-on-top card. Sticky filter bar keeps `position: sticky` but shrinks its padding under 600px (already partially handled).

---

## 4. TYPOGRAPHY

- **Display**: `var(--font-editorial)` (Fraunces stack) for all hero headlines, section H2s and the "Bốn cách sống" / "Ba kiểu qua đêm" triad card titles — currently these are all plain `--font-sans` on both pages. This is the single highest-leverage typographic change: it immediately signals "magazine," not "directory."
- **Scale**: hero H1 at `--text-5xl` with `--tracking-tighter`; section H2s at `--text-2xl`/`--text-3xl` with the phù-sa vertical tick device (already established on other CE pages — reuse the exact CSS, don't invent a new one) to the left of each heading.
- **Body**: keep `--font-sans` (Inter) for UI chrome (chips, buttons, card metadata) — the CE/sans split should map exactly to "story voice vs. interface voice," consistent with the rest of the site.
- **Editorial long-read section**: apply `--measure-read` (68ch) column constraint (currently `.page-article` likely runs the full content width — verify and clamp), drop-cap first letter of the opening paragraph in Fraunces at ~3.2em line-height-matched, per the established CE pattern.
- **luu-tru specific**: the wake-up headline should be allowed a slightly larger, looser leading (`--leading-snug` off, custom 1.2) to read like a caption under a photograph rather than a page title — it's a *line*, not a *label*.

---

## 5. SENSORY + MOTION + CURIOSITY

- **Hero mode-dial (du-lich)**: cross-fade transition on background-image swap using `--ease-cinematic`, 600ms — deliberately slower than a UI toggle so it reads as "the scene changes" not "the filter changes."
- **Sunrise sweep (luu-tru)**: pure CSS gradient animation on a `::before` pseudo-element over the hero scrim, 18–20s single loop-or-settle (not looping forever — settle on "day" state after one cycle so it doesn't nag), respects `prefers-reduced-motion` (freeze on the day-state gradient immediately).
- **Card image Ken Burns**: on the "Bốn cách sống"/"Ba kiểu qua đêm" editorial tiles specifically (not on every EntityCard — that would be too busy across a full grid) — a slow 1.0→1.06 scale over 20s on hover/in-view, `--img-hover-scale` already exists as a token, extend its duration for these hero-adjacent tiles only.
- **Scroll-reveal**: already global via `useReveal()` — extend it to the new editorial triad/quad sections (they must ship with `.reveal` class from day one, this is a known gap pattern per CLAUDE.md's history of reveal-invisibility bugs — verify against the "harden scroll-reveal" fix already shipped).
- **Discovery devices**:
  - du-lich: the "đang đúng mùa" contextual note on category rows (see §3) is itself a discovery device — it changes month to month, giving returning visitors a reason to check back ("what's in season now?").
  - luu-tru: the region-window micro-nav doubles as a discovery device — hovering a region window on desktop could (optionally, cheap) swap a tiny caption under it with a fact ("Cù lao An Bình — 40+ homestay, đa số có xe đạp miễn phí") sourced from data already loaded, no extra fetch.
- **Sensory-through-design, not decoration**: avoid literal water-ripple/parallax gimmicks (reads as slop). Instead: the color register itself carries sensation — river-blue cool wash on luu-tru's hero vs. warm clay/amber on du-lich's — so the *palette* is doing the sensory work, which is cheap (CSS only) and durable (no motion-fatigue, no accessibility conflict).
- **Micro-interactions**: chip/pill hover already has spring-easing tokens (`--ease-spring-gentle`) site-wide — apply consistently to the new triad cards and region-windows so they feel like the same hand touched them.

---

## 6. UX FLOW

**du-lich.vue**: Orientation → Curiosity → Category depth → Grid utility → Cross-sell.
- The mode-dial hero front-loads orientation ("this page has range") in the first viewport, which the current plain hero doesn't do — today a visitor has to scroll through 4+ sections before understanding the taxonomy.
- The "Bốn cách sống" quad is the *information scent* layer — a visitor who doesn't want to browse a grid gets a direct path to a filtered subset in one click, reducing the current pattern where the only real navigation is either scroll-rows (browse) or the giant grid (search). This closes the "mid-funnel" gap.
- Season-aware category notes give a *reason to act now* ("mùa nước nổi đang tới" style copy) which is the paper-thin difference between "read as a database" and "read as a magazine that knows what week it is."
- Grid remains the honest fallback for power users — sticky controls, search, filter chips, sort — unchanged in mechanics, only re-skinned.
- Every path terminates at entity detail pages or `/lich-trinh` (itinerary) or `/luu-tru` — the cross-links section is the exit ramp to contact-oriented conversion (booking a homestay, contacting a craft village).

**luu-tru.vue**: Emotional hook → Decision-tree → Region-narrowing → Comparison grid → Contact.
- The wake-up hero does emotional work first (unusual for a directory page — most accommodation pages open with filters). This is deliberate: get the visitor to *want* a Delta morning before showing them a decision matrix.
- The "Ba kiểu qua đêm" triad IS the decision tree made visible — most visitors to a lodging page are actually choosing "what kind of stay" before "which specific one," and the current page buries that choice inside two paragraphs of prose (§77-79 today). Surfacing it as three clickable filterable tiles collapses a read into a decision in 3 seconds.
- Region quick-picks narrow geographically for visitors who already know they're staying near a specific attraction (a common real behavior — "I'm visiting Cồn Phụng, where do I sleep near there").
- Grid is comparison-mode: price/amenity visible per card (currently gated to product/dish/experience types only in EntityCard — extend to accommodation, see §11) so visitors can compare without opening five detail pages.
- Every card and every CTA terminates in a **contact-only** action (Zalo/phone via the entity detail page's contact widget) — no friction added, no booking flow implied anywhere in copy (audit the "Lời khuyên đặt phòng" section's language — "đặt phòng" as a concept is fine, "đặt trước qua Zalo/điện thoại" is the correct framing, never a form).

---

## 7. PREMIUM CUES

- Consistent phù-sa tick beside every H2 — small detail, but its *presence* across du-lich/luu-tru (currently absent) is what will make them feel like they belong to the same premium family as the 4 pages that already have it.
- Editorial drop-cap on the long-read intro paragraph — a classic print-magazine cue that AI-slop sites never bother with.
- Hairline dividers (`.5px` borders, already a token pattern site-wide) between hero and next section instead of hard section breaks.
- The region-window / triad tiles use real typographic hierarchy (kicker + serif title + one sentence) instead of icon+label+count pills — icon-label-count reads as "app," kicker+serif+sentence reads as "magazine."
- Grain texture (`--grain` token, already defined, unused on these two pages) applied at very low opacity (2–4%) as a background wash on the hero scrim — the exact "antidote to flat AI-gradient look" the token comment describes. Cheap, already built, just needs `background-image: var(--grain)` blended in on the hero overlay.
- Season-aware micro-copy (data-driven, not fabricated) signals the page is *alive*, which reads as more crafted than a static directory even though it's cheap to compute from already-loaded data.
- Restraint: ONE moving element per hero (mode-dial cross-fade OR sunrise sweep), not both stacked — over-animation is the single fastest way to read as AI-slop per the anti-slop research; this concept deliberately caps motion count.

---

## 8. CULTURAL AUTHENTICITY

- Copy must ground every generic tourism noun in Delta-specific texture: not "trải nghiệm bản địa" alone but "chèo xuồng qua rạch dừa nước," "tát mương bắt cá," "đạp xe đường làng," "ngồi võng nghe chim" — these phrases already exist in the current editorial block (`du-lich.vue` lines 58-68) and should be preserved/extended, not replaced with generic travel-blog language.
- The four "cách sống" categories on du-lich should map to real cultural registers already present in the data/taxonomy: sông nước (chèo xuồng, chợ nổi, cù lao), miệt vườn (vườn trái cây, homestay nhà vườn), làng nghề (gốm Mang Thít, kẹo dừa, chiếu Định Yên, bánh tráng Mỹ Lồng), and — currently missing from the page entirely — a nod to Khmer/Hoa cultural layer (chùa Khmer, lễ hội Ok Om Bok/Chol Chnam Thmay if entities exist for Trà Vinh's Khmer heritage) since the tri-province merge folded Trà Vinh's strong Khmer character into the umbrella and the current du-lich page copy doesn't mention it once.
- luu-tru's "Ba kiểu qua đêm" copy should specifically evoke what makes Delta homestay different from a generic homestay: sleeping literally inside someone's orchard, being woken by fruit falling, reaching a stay by đò/xuồng not just road — the current prose already has some of this ("phải đi đò hoặc xuồng mới tới") — extract and elevate it to headline-level copy rather than burying it in paragraph three.
- OCOP tie-in: du-lich's craft-village row should visually nod to the OCOP star system already rendered on cards (`ocop-5`/`ocop-4` badge styling exists) — treat a 5-star OCOP craft product/village as an implicit "trust and quality" signal worth surfacing in the "Bốn cách sống" làng nghề tile specifically.
- Avoid generic-tourism clichés: no "hidden gem," no "paradise," no stock beach/hammock imagery vibe — keep language specific and sensory (smell of bưởi blossom, sound of a xuồng máy, taste of cá linh non) rather than abstract superlatives.

---

## 9. COPY VOICE

Tone: warm, unhurried, second-person-adjacent but not pushy — a knowledgeable local friend describing mornings, not a sales page. Short declarative sentences mixed with one longer sensory sentence per section. Miền Tây/Nam Bộ vocabulary preferred over formal Northern-standard tourism-board phrasing where natural.

**du-lich.vue hero headline (example):**
> **Ba tỉnh, một nhịp sông.**
> Miệt vườn, cù lao, làng nghề trăm năm — khám phá theo mùa nước, mùa trái, mùa lễ hội.

**du-lich.vue "Bốn cách sống" kicker + tile line (sông nước example):**
> SÔNG NƯỚC
> *Chèo xuồng qua rạch dừa nước lúc sáng sớm, khi sương còn chưa tan trên mặt kênh.*

**luu-tru.vue hero headline (example):**
> **Thức dậy giữa vườn, nghe chim trước khi nghe chuông báo thức.**
> Homestay nhà vườn, resort ven sông, khách sạn phố — chọn nơi bạn muốn mở mắt vào buổi sáng ở miền Tây.

**luu-tru.vue "Ba kiểu qua đêm" tile line (homestay example):**
> **Homestay nhà vườn** — phù hợp nếu bạn muốn ngủ giữa cây trái, ăn cơm chủ nhà nấu, và không phiền vì phải đi thêm một đoạn đò.

---

## 10. SIGNATURE MOMENT

**du-lich.vue**: the **hero mode-dial cross-fade** — the single interaction where clicking "Ẩm thực"/"Làng nghề"/"Trải nghiệm" swaps the entire cinematic scene (image + headline + subhead) in one smooth motion before any scrolling happens. This is the moment a visitor realizes the page has range and craft, in the first three seconds, with zero extra data cost.

**luu-tru.vue**: the **sunrise-sweep hero** — a hairline horizon gradient silently shifting from night-blue to dawn-amber to day-sand across the hero banner on load, paired with the "thức dậy" headline. It is the one moving thing on the page, it costs nothing (pure CSS), it respects reduced-motion, and it is the most literal possible expression of the page's entire thesis: *this page is about what you wake up to.*

---

## 11. COMPONENTS + FEASIBILITY

All CSS-tokens only (no Tailwind), images AI-gen or motif-SVG only, CTA remains contact-only throughout (no new booking-shaped UI), dark-mode parity required on every new class, `prefers-reduced-motion` guards on every new animation.

**New components (both reusable beyond this unit):**
- `CinematicCatalogHero.vue` — replaces `.catalog-hero` on both pages (and is a candidate to eventually replace it on `san-pham.vue`, `le-hoi.vue` etc. too). Props: `heroImages[]` (or motif fallback), `eyebrow`, `title`, `subtitle`, optional `modes[]` (for du-lich's dial) or `sunrise: boolean` (for luu-tru's sweep). Internally: Ken-Burns background layer, scrim (`--scrim-hero`), `--grain` overlay at low opacity, glass stat strip anchored bottom.
- `EditorialTileGrid.vue` — generic 2×2/asymmetric tile grid used for du-lich's "Bốn cách sống" and luu-tru's "Ba kiểu qua đêm." Props: `tiles[]` with `{kicker, title, body, image/motif, to, badge?}`. Reusable on any future hub page needing a "categories as story, not as chips" section.
- `RegionWindowNav.vue` — luu-tru's region micro-nav (image/motif tile + count + jump-link). Could generalize to `ban-do.vue` or `san-pham.vue` region browsing later.

**EntityCard.vue changes (keystone, benefits ALL catalog pages, not just this unit — flag as the highest-leverage single fix in the whole redesign program):**
- Extend `cardMeta` to include `type === 'accommodation'` so price renders on lodging cards (currently gated to `product|dish|experience` at line 110 of `EntityCard.vue` — `luu-tru.vue`'s grid never shows price today, a real UX gap for a comparison-shopping page).
- Apply Fraunces to `.card-name` — currently plain sans; this alone CE-ifies the repeated grid unit across the entire site with a one-line CSS change.
- Consider surfacing `amenity_badges` visually on hover (`.card-amenities` is currently `display:none` — dead code) for accommodation type specifically, since amenities (wifi, air-con, kid-friendly) are genuine lodging decision factors.

**du-lich.vue edits:**
- Replace `.catalog-hero` markup with `<CinematicCatalogHero>` in mode-dial configuration; feed it 4 category images/motifs already available via `featured`/`categories` computed data (no new fetch).
- Insert `<EditorialTileGrid>` between hero and existing `CatalogSpotlight`/featured row — and collapse `CatalogSpotlight` + featured row into one (they currently show overlapping "best of" content twice in a row; pick one pattern, likely keep the scroll-row featured and let the new tile grid absorb spotlight's "one big pick" role, OR keep CatalogSpotlight as the "editor's single pick" directly under the tile grid — sequence-test both, but do not ship both AND a third featured row un-merged).
- Add season-aware one-line note to each category `section-head` (data already computed via `inSeason`/`relevanceScore` from `useSeason.ts` — no new logic, just a rendered string).
- Clamp `.page-article` to `--measure-read`, add drop-cap CSS to first `<p>` of first `<h2>` block.

**luu-tru.vue edits:**
- Replace `.catalog-hero` with `<CinematicCatalogHero sunrise>`; feed it best available accommodation photo(s) with river-blue (`--cat-accommodation`) motif fallback.
- Replace the "Các loại hình lưu trú" prose section (lines 77-79 today) with `<EditorialTileGrid>` for the three stay-types, extracting the sensory phrases already written in prose into tile copy (no new research needed — the existing copy already has the raw material, it just needs re-formatting from paragraph to card).
- Replace `.quick-picks` button row with `<RegionWindowNav>`.
- Restyle "Lời khuyên đặt phòng" into a compact bordered callout/sidebar card (`--card-outlined-*` tokens already exist) rather than full-width H2 prose, to visually separate "story" from "logistics."
- Extend grid to two-column-aware EntityCard price display per the EntityCard change above.

**Feasibility notes:** every visual idea above maps to either (a) an existing token/pattern already in `variables.css` (grain, scrim-hero, ease-cinematic, season gradients, glass tokens, spring easing) or (b) already-loaded data (no new API calls, no new backend work) — this is a front-end-only, CSS/Vue-template redesign executable by a solo dev without touching `agent/`.
