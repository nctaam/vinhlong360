# San-pham.vue (Đặc sản) + Ocop.vue — Deep Redesign Concept

*Unit 06 — Products + OCOP · prior grades: san-pham.vue 7.0, ocop.vue 7.5*

> Grounding note: both pages currently share one hero skeleton (`.catalog-hero`), one grid unit (`EntityCard`), one spotlight (`CatalogSpotlight`), one interstitial (`CatalogInterstitial`) and near-identical `<script>` logic (filters, sort, pagination). CE (cinematic-editorial) currently exists only as a serif `<h1>` inside `.catalog-hero` — everything below the fold is still catalog-tier. This concept keeps the shared plumbing (DO NOT fork the filter/sort/pagination logic) but gives each page its own **CE-grade narrative skin**, and — critically — resolves the "twin motif collision": san-pham.vue and ocop.vue currently look like the same page with a different H1, and product/dish already share `cat-product`/`cat-dish` visual language in `EntityCard`. The fix is structural (see §1, §3, §11), not cosmetic.

---

## 1. STORY ANGLE

**The collision to solve first:** today, "sản phẩm" (raw catalog of all products) and "OCOP" (the subset that's certified) read as the same page twice. That's not just a design flaw — it undersells OCOP's actual meaning. OCOP is not "sản phẩm nhưng có sao" — it is **provenance, verified**. It's the difference between a market stall and a stall whose owner can show you the paper trail.

So the two pages get **two different stories**:

- **san-pham.vue → "Chợ phiên miệt vườn" (The orchard's roving market).** The story is *abundance and season* — a living market with a rhythm the seasons dictate. The controlling idea: *"Đất này, mùa nào thức nấy."* Every product here is introduced through **who grows/makes it and when it's at its peak**, not through a spec sheet. A product card is not "bưởi Năm Roi — 45.000đ/kg" — it's "Bưởi Năm Roi vừa vào mùa ở Bình Minh, ngọt nhất tháng 8-10."

- **ocop.vue → "Sổ vàng OCOP" (The OCOP ledger / hall of provenance).** The story is *trust made visible* — a hand-inspected honor roll, not a shop shelf. Controlling idea: *"Mỗi ngôi sao là một lần kiểm chứng."* The star rating stops being a badge in the corner of a card and becomes the spine of the whole page's structure — a **ledger you can leaf through by rank**, the way you'd browse a guild's registry of certified makers.

**The universal product narrative (applies to both, expressed at different volumes):** every entry answers three human questions in this order — *Ai làm ra nó? Ở đâu? Mùa nào ngon nhất?* (Who makes it? Where? When is it best?) — before it answers "bao nhiêu tiền." Price is a footnote; provenance is the headline. This is what separates an editorial catalog from an e-commerce grid, and it's fully compatible with contact-only CTAs (Zalo/phone to ask, not "add to cart").

---

## 2. CINEMATIC HERO / THESIS

### san-pham.vue — "Phiên chợ đang họp" (The market is open, right now)
Replace the flat `.catalog-hero cat-product` icon-+-stat-bar block with a **live-market hero**:
- Background: a warm gradient wash using the existing sediment palette (amber→leaf, since produce/fruit skews leaf+amber, not clay) with a **subtle basket-weave or woven-reed texture** rendered as a tiled SVG at ~4% opacity (culturally specific — the round *cần xé*/*thúng* baskets used at Delta floating and roadside markets — NOT generic dot-grid).
- Kicker (editorial dateline, wide caps + hairline, same voice as CE mastheads elsewhere): **"PHIÊN CHỢ · THÁNG {N}"** — ties the whole page to *today's* month, immediately.
- Masthead `h1` in `--font-editorial`: *"Chợ phiên miệt vườn"* (page still carries `pc('hero_title')` from admin-editable content — but the concept's copy target is this line).
- Dek: one live, specific sentence naming what's in season *this month* pulled from `seasonalHighlights` count — e.g. *"Tháng {N}, {count} loại đặc sản đang chính vụ — ngon nhất, rẻ nhất, đúng lúc."* This makes the hero feel alive/different every visit (discovery device #1).
- A **thin animated "market pulse" strip** under the dek: 3-4 tiny woven-basket glyphs, each holding one seasonal-highlight thumbnail-color-swatch (not photo — color only, from the entity's placeholder gradient), pulsing gently once on load — a preview-tease of what's below, encouraging scroll. Reduced-motion: static, no pulse.
- Stats row stays (kept — it's useful information scent) but restyled onto the sediment-tick section-head language instead of generic `.stat-item` boxes.

### ocop.vue — "Sổ vàng" (The ledger opens)
This hero must look **structurally different** from san-pham's to kill the collision:
- Background: NOT a market texture — a **certificate/ledger texture**: a faint guilloché-pattern (the fine wavy-line engraving used on certificates/currency) rendered in clay+amber at low opacity, echoing "official seal" without using a literal seal clipart (avoids AI-slop generic-badge look).
- Kicker: **"CHỨNG NHẬN QUỐC GIA · MỖI XÃ MỘT SẢN PHẨM"**.
- Masthead: *"Sổ vàng OCOP"*.
- The existing `.hero-creds` trust-signal row (🏅/✓/📊) is GOOD — keep it, but re-skin as an actual **wax-seal / ribbon motif**: a small circular emblem built in CSS (radial-gradient disc + notched border, no image asset needed) sitting to the left of the masthead, with the highest star-count visible inside it (e.g. "★5" for the top tier) — this is the signature visual anchor unique to this page (see §10).
- Dek: *"{count} sản phẩm, từ 3 đến 5 sao — mỗi ngôi sao là một vòng kiểm định đã qua."*
- No market/basket texture, no seasonal pulse strip here — OCOP's hero is calmer, more formal, more "registry," reinforcing the story split.

**Feasibility:** both textures are inline SVG `background-image` (data-URI or `<svg>` pattern), zero new image assets, styled entirely with existing CSS custom properties (`--clay-600`, `--amber-600`, `--leaf-600`, `--river-600`). No new fonts.

---

## 3. LAYOUT + RHYTHM

Keep the proven scroll skeleton (hero → spotlight → highlight rail → interstitial → editorial → divider → filterable grid → cross-links) — audits show this rhythm works — but **retune the pacing per page** so they don't scroll identically:

**san-pham.vue rhythm — "seasonal cadence":**
1. Market hero
2. `CatalogSpotlight` (kept, dùng-chung)
3. **"Đang vào mùa" rail** — promote this above OCOP spotlight (season is this page's spine); restyle the scroll-row as a **"chợ phiên" horizontal shelf** with a subtle wood-grain/market-stall backdrop band (CSS gradient, not image) rather than a plain `.band` background.
4. OCOP spotlight rail — but **reframed as a teaser**, not a full section: a slim single-row "cũng có hàng OCOP ở đây" strip with ONE strong CTA to `/ocop` (avoid duplicating the ledger experience inline — send people to the dedicated page instead of re-running its content).
5. Interstitial (kept)
6. Editorial copy — restyle with `drop-cap` + `pull-quote` treatments from `editorial.css` (currently plain `<h2>/<p>`, no CE typographic texture at all — quick, high-leverage upgrade)
7. Divider → filterable grid (this is the actual "market stalls" — see §4/§6 for the reframing)
8. Cross-links

**ocop.vue rhythm — "ledger cadence" (more vertical, more deliberate, slower reveal):**
1. Ledger hero
2. `CatalogSpotlight` (kept)
3. **Star-rank ledger** — this is the structural centerpiece. Replace the current flat `.quick-picks` star buttons with a **descending 3-tier ledger layout**: a full-width "5 sao" honor band (visually heaviest, gold-adjacent, largest cards) sitting above a lighter "4 sao" band above a lightest "3 sao" band — literal visual hierarchy = trust hierarchy. Each band is its own `scroll-row` of `EntityCard`s but with band-specific framing (border weight + glow decreasing 5→3).
4. Region quick-picks (kept, but visually quieter — subordinate to the star ledger, not equal rank)
5. Interstitial
6. Editorial copy (drop-cap + pull-quote here too, pulling the "khi bạn thấy nhãn OCOP..." line into a `pull-quote` — it's the page's thesis sentence, currently buried mid-paragraph)
7. Divider → filterable grid (framed as "toàn bộ sổ", i.e. "browse the whole ledger" — filters lead with star-rank, not season, reflecting the ocop.vue script's own filter order priority: star → area → season, already correct in the DOM order — good, keep)
8. Cross-links

**Grid responsive posture (shared, unchanged mechanics):** CSS grid auto-fill with existing `--card` sizing; `list-view`/`grid` toggle stays; mobile collapses star-bands to stacked single-column sections with a horizontal scroll-row per band (same pattern as `seasonalHighlights`).

---

## 4. TYPOGRAPHY

- Display: `--font-editorial` (Fraunces) for `h1`/`h2`/masthead — already tokenized, no change needed, just apply consistently to section heads that currently use system sans (`.section-head h2` in catalog.css — verify it inherits `--font-editorial`; if not, add it here so both pages' section heads match the CE mastheads elsewhere).
- Body/editorial prose: apply `.editorial-body` class (from `editorial.css`) to the `.page-article` sections on both pages instead of bare `<p>` — gives `--measure-read` max-width and the correct `--leading-relaxed`, currently missing (these editorial blocks currently run full-width, hurting readability — an easy, invisible-effort win).
- **Drop cap** on the first paragraph of each page's editorial section (`Đồng bằng sông Cửu Long là vựa trái cây…` / `OCOP (One Commune One Product…`) — instant premium signal, zero new CSS (class already exists).
- **Pull-quote** treatment for the single most quotable sentence per page:
  - san-pham.vue: *"Mỗi sản phẩm gắn liền với một vùng đất, một mùa vụ và một câu chuyện sản xuất riêng."*
  - ocop.vue: *"Khi bạn thấy nhãn OCOP trên sản phẩm, bạn biết sản phẩm đó đã qua quy trình đánh giá nghiêm ngặt, có nguồn gốc rõ ràng và chất lượng được kiểm chứng."*
- Numerals: OCOP star-counts and stats should use tabular/lining figures already handled by `CountUp` — no change, just make sure the ledger bands' large numerals inherit `--font-editorial` at a bigger clamp (e.g. `clamp(2.5rem, 2rem+3vw, 4rem)`) for the "5 sao" band specifically, so the top tier reads as literally larger typographically, not just visually bordered.

---

## 5. SENSORY + MOTION + CURIOSITY

Both pages currently over-rely on generic scroll-reveal (`.reveal`) with no page-specific texture. Add restrained, reduced-motion-safe, CULTURALLY GROUNDED motion:

**san-pham.vue (sensory = taste/season/market bustle):**
- The "market pulse" hero strip (§2) — one-shot gentle scale pulse on load, then still. Reduced-motion: renders static.
- Seasonal banner icon already animates (`season-fire-pulse` — keep, it's good and already RM-gated).
- **Hover micro-interaction on EntityCard within the seasonal rail only** (scoped class, not global): a very subtle "ripple" shadow (like a droplet on water) using `box-shadow` transition — evokes sông nước without literal water GIFs. Reduced-motion: no transform, keep color transition only.
- Discovery device: month-picker chip row (`seasonFilterOptions`) — add a tiny **"⟲ tháng này"** quick-reset chip that's visually distinct (amber ring) so users exploring other months always have a one-tap way back to "what's fresh now" — turns a filter UI into a curiosity loop ("what was in season in Tết?" → tap around → tap back to now).

**ocop.vue (sensory = trust/ceremony/weight):**
- Star-rank bands reveal **top-down, staggered** (5-star band reveals first/fastest, 4-star slightly delayed, 3-star last) — reinforces "descending through a registry" rather than "same-weight list." Achieved via existing `useReveal()` + a stagger data-attribute, no new JS engine.
- The wax-seal emblem in the hero can have a **very slow, single, one-time "stamp" micro-animation** on first paint (scale 0.9→1 with a soft settle, 400ms, NOT looping) — the one moment of ceremony on the page. Everything else here should feel calm/settled, not busy — OCOP's sensory register is "gravitas," not "bustle."
- Discovery device: clicking a star-band's "Xem tất cả →" scroll-to-grid already exists (`scrollToGrid` + `starFilter`) — keep, but add a brief highlight-flash on the grid's star filter chip after landing, so the user's eye is guided to *where* the filter changed (closes the loop between "I clicked 5-star" and "I see why the grid changed").

**Both — sound/texture without literal SFX (this is a visual site, no audio):** lean on **word choice + motif** to evoke Delta sensory register rather than motion-heavy tricks — see §9 copy.

---

## 6. UX FLOW

Both pages share the same functional skeleton, so the flow fix is about **information scent per story**, not new mechanics:

**san-pham.vue flow:** Hero (this month's abundance) → visually strongest pull is toward *seasonal* content first → OCOP is a soft signpost outward (not a competing deep-dive) → editorial context (why season matters) → full market grid defaults to **current month pre-filtered** (already does: `seasonFilter = ref(String(currentMonth))` — good, keep) → contact via EntityCard → detail page.

**ocop.vue flow:** Hero (the registry exists, trust is the point) → star-rank IS the primary nav axis (region and season are secondary refinements, already reflected in filter panel order) → editorial context explains *why* stars matter (placed to pay off curiosity right after they've seen the star ledger visually) → full ledger grid, default unfiltered (browsing "everyone who's certified" is the point, unlike san-pham's month-default) → contact via EntityCard.

**Cross-page handoff (currently the weakest link — both pages just have a generic 4-icon cross-link band that's identical on both pages):**
- Make san-pham.vue's OCOP cross-link card carry a **live number** ("⭐ {ocopCount} sản phẩm OCOP") instead of static "Sản phẩm đạt chuẩn" — turns a nav tile into an information-scent teaser.
- Make ocop.vue's "Tất cả sản phẩm" cross-link explicitly reframe san-pham as *"còn {allEntitiesCount - ocopCount} đặc sản khác chưa có sao"* — this explicitly resolves user confusion about why two pages exist ("this page is the subset, that page is everything").

**Friction reduction to contact:** EntityCard's `cardMeta` already surfaces price/hours for `product` type inline on the card (👍 already good) — no new friction to remove there; the redesign's job is upstream (making people want to open the detail page), not touching the existing contact-only CTA pattern on the detail page itself (out of scope for this unit, but flag it as reusable: EntityCard's price surfacing pattern should stay consistent between both pages, which it already is since they share the component).

---

## 7. PREMIUM CUES

- **Provenance-first copy hierarchy on cards is a premium cue on its own** — see §11 for the concrete EntityCard-subtitle change (maker/place before price).
- Sediment-tick section heads (river→amber→clay vertical tick, already built site-wide in `index.vue`/`khu-vuc/[area].vue`) — apply to `.section-head h2` on both pages consistently; right now these pages' section heads are plain, breaking continuity with the rest of the CE site.
- Hairline dividers (`.catalog-divider`) already exist — keep, but ensure they use the `.5px` hairline weight used elsewhere (verify against `--line` token — audit if it's currently a full 1px rule, which would look heavier/cheaper than the rest of the site).
- OCOP wax-seal emblem (§2/§10) is the single richest premium cue to add — built from CSS only (radial gradient + notched clip-path + inset shadow), no image dependency, degrades gracefully.
- Micro-typographic discipline: tabular numerals for stats, `text-wrap: balance` on all headings (already used elsewhere — apply here), consistent `--tracking-caps` on all kicker/eyebrow text.
- Empty states already have good copy/tone (`EmptyState` component) — no change needed, already premium-adjacent.

---

## 8. CULTURAL AUTHENTICITY

- **San-pham.vue market texture**: woven *cần xé*/*thúng* basket pattern (round reed baskets used at Delta roadside and floating markets to carry fruit) — specific, not generic wicker/rattan clipart. If SVG generation is a concern, a simple repeating hexagonal-weave line pattern reads as "woven basket" without needing to be literal.
- **Seasonal seasonal copy already correctly cites real Delta calendar knowledge** (sầu riêng/măng cụt T5-7, bưởi/cam + mùa nước nổi T8-10, dưa hấu Tết T12-2, dừa quanh năm) — keep this, it's accurate and specific; just typographically elevate it (drop cap, pull-quote) rather than rewriting content.
- **Ocop.vue ledger/guild framing** is itself culturally apt: OCOP is a real Vietnamese state program (không phải khái niệm phương Tây du nhập) — treating it as a formal "sổ vàng" (honor ledger) matches how Vietnamese institutions actually present certification (bằng khen, sổ vàng truyền thống) rather than borrowing a Western "verified seller" badge aesthetic (which would read as e-commerce/AliExpress-slop).
- **Regional specificity already present and correct** in the OCOP editorial copy (Bến Tre dừa, Vĩnh Long bưởi Năm Roi/nem Lai Vung/gạch gốm Mang Thít, Trà Vinh Khmer bánh tét lá cẩm/dừa sáp) — the region quick-picks' taglines (`Miệt vườn cam sành`, `Xứ dừa ngọt lành`, `Đặc sản dừa sáp`) are good, keep as-is; consider surfacing one of these taglines as a hero sub-line when a region filter is active (reinforces specificity at the moment of filtering, not just in a static list).
- **Avoid generic tourism/e-commerce clichés:** no shopping-cart iconography, no "★★★★★ (128 reviews)" Amazon-style review stacks, no "Best Seller" ribbons — OCOP stars are a *government-issued quality rank*, not a customer-satisfaction score; keep that distinction sharp in copy and iconography (don't let the star glyph get confused with review-rating stars used elsewhere in `EntityCard.ratingDisplay`).

---

## 9. COPY VOICE

Voice: warm, specific, second-person-adjacent but not pushy; short declarative sentences; leads with a person/place/season, not a spec. Never oversells; never uses transaction language ("mua ngay", "đặt hàng", "giao hàng tận nơi" — contact-only site).

**San-pham.vue example lines:**
- Hero dek: *"Tháng {N}, hơn {count} loại đặc sản đang chính vụ — ngọt nhất, rẻ nhất, đúng lúc để nếm thử."*
- Seasonal rail intro (replacing the flatter current copy): *"Chợ phiên tháng này: trái chín đúng độ, người vườn vừa hái, chưa kịp nguội hơi đất."*
- OCOP teaser strip CTA: *"Trong {count} đặc sản này, {ocopCount} món đã có sao OCOP — xem sổ vàng →"*

**Ocop.vue example lines:**
- Hero dek: *"{count} sản phẩm, từ 3 đến 5 sao — mỗi ngôi sao là một vòng kiểm định đã qua, không phải tự phong."*
- Star-band 5-sao intro: *"Bậc cao nhất, hiếm nhất — sản phẩm đã chứng minh được cả chất lượng lẫn khả năng vươn xa."*
- Pull-quote (elevated from existing body copy, verbatim, just re-set in `pull-quote` styling): *"Khi bạn thấy nhãn OCOP trên sản phẩm, bạn biết sản phẩm đó đã qua quy trình đánh giá nghiêm ngặt, có nguồn gốc rõ ràng và chất lượng được kiểm chứng."*

---

## 10. SIGNATURE MOMENT

**The one thing each page is remembered by:**

- **san-pham.vue** → the **month-alive hero**: the page visibly, numerically changes its own headline copy depending on the calendar date ("Tháng 8, 14 loại đặc sản đang chính vụ") — a subtle but real "this site is watching the season with you" feeling. No other catalog page on the internet that a Mekong Delta visitor has seen does this with this specificity.

- **ocop.vue** → the **wax-seal emblem + descending star-ledger bands**: a single CSS-built circular seal in the hero, and a page structure that gets visually *lighter and smaller* as you scroll from 5-star to 3-star — you feel the hierarchy of trust through layout weight before you read a single word. That's the memorable, ownable idea unique to this page (and it directly resolves the "twin motif collision" — nobody will confuse this with the market page again).

---

## 11. COMPONENTS + FEASIBILITY

**New, page-scoped (do NOT touch shared component files' default behavior — extend via scoped classes/props):**

1. `MarketPulseStrip` (san-pham.vue only, small inline component or scoped markup) — renders up to 4 color-swatch "baskets" from `seasonalHighlights`, CSS-only pulse-once animation, RM-gated. Pure CSS/HTML, no image.
2. `.woven-texture` background utility (scoped CSS in san-pham.vue's `<style scoped>`) — inline SVG pattern, tiled, ~4% opacity over the amber/leaf gradient wash.
3. `.guilloche-texture` background utility (scoped CSS in ocop.vue's `<style scoped>`) — inline SVG fine-line pattern, clay/amber, ~4% opacity.
4. `WaxSealEmblem` (ocop.vue only) — pure CSS: circular div, `radial-gradient` fill in `--secondary`/amber tones, `clip-path: polygon(...)` notch pattern for the "wax seal edge," inset `box-shadow` for depth, containing the top star-tier count as large `--font-editorial` numerals. One-time `@keyframes seal-stamp` (scale .9→1), RM: static.
5. Star-rank band wrapper (ocop.vue) — a scoped `.ocop-band` class family (`.ocop-band--5`, `--4`, `--3`) applied around each `scroll-row`, varying border-weight/glow/heading-size per tier; reuses existing `EntityCard` unchanged.
6. `.editorial-body` + `.drop-cap` + `.pull-quote` classes — **already exist in `editorial.css`**; this unit's work is *applying* them to `.page-article` on both pages (import `editorial.css` into these two routes if not already globally available — check `nuxt.config`/route CSS scoping before adding an import).
7. Sediment-tick section heads — **already built** (reference implementation in `pages/khu-vuc/[area].vue:342` and `pages/index.vue:1143`) — reuse that exact CSS block via the shared `catalog.css` `.section-head h2` selector so both pages inherit it without duplicating the gradient-tick code a third time. **Recommend promoting this tick mixin out of page-scoped CSS into `catalog.css` or a shared partial**, since it's now needed on 4+ pages — flag as a refactor opportunity, not to be done as page-specific inline duplication again.

**EntityCard change (shared component — HIGH IMPACT, used everywhere, needs care):**
- Currently `.card-type` is `display:none` and `placeName` renders below the summary with no visual priority over price. Per §1's "who/where/when before price" thesis, promote **maker/place** to render *above* the summary line (not just below it) when `entity.type === 'product'`, styled as a small caption line (e.g. `"— Cô Ba, Vườn bưởi Bình Minh"` if a maker/place attribute exists; falls back gracefully to just place name, or hides entirely if neither exists — additive, no schema change required, purely a template reorder gated on existing `placeName` computed). This is the single highest-leverage, lowest-risk change in this whole concept because it improves EVERY page that renders product cards, not just these two — but it must be done carefully since EntityCard is the site's most-reused unit (per the assignment brief, it's the #1 keystone never yet CE-ified). Recommend doing this as its own small, separately-tested change with a visual diff check across san-pham/ocop/du-lich/index before merging.

**Explicitly reusable across other units:**
- Sediment-tick section-head CSS (once promoted to shared partial) — usable by any catalog page (du-lich, su-kien, etc.)
- `.editorial-body`/`.drop-cap`/`.pull-quote` application pattern — same recipe applies to any page with a `.page-article` block (likely most catalog pages have one).
- The "band-weight-signals-rank" pattern (ocop star bands) is conceptually reusable for any future ranked-listing page (e.g. a future "top di tích lịch sử" or "hạng sao khách sạn" page), even though the CSS itself is OCOP-specific here.

**Constraints honored:** no Tailwind, tokens-only CSS; no new images (textures are inline SVG/CSS gradients); CTA untouched (still contact-only via existing EntityCard → detail page → sticky CTA bar); dark-mode — all new colors must be re-expressed via existing `.dark` overrides pattern seen in both files' current `<style scoped>` blocks (e.g. `.dark .hero-cred-seal`, `.dark .honor-banner`) — every new class in this concept needs a paired `.dark` rule before shipping; reduced-motion — every new `@keyframes` here is listed with its RM fallback in the relevant section above and must get a `@media (prefers-reduced-motion: reduce)` rule mirroring the existing pattern at the bottom of both files' `<style>` blocks.
