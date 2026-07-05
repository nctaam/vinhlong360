# Entity Detail Page — `dia-diem/[id].vue` (flagship redesign)

> Prior grade: **7.0**. Current file: `web-nuxt/pages/dia-diem/[id].vue` (1216 lines) + `web-nuxt/assets/css/detail.css` + `KnowBeforeYouGo.vue`, `ContactWidget.vue`, `PhotoGallery.vue`, `JourneyActionRail.vue`.
> This is the single highest-leverage page in the product: every one of the ~1730 entities (destination, dish, product, craft village, accommodation, experience, event, organization) resolves here. It is also the page where the platform's central promise — **"every place is a story"** — is currently least true. Today it reads as a well-organized *spec sheet* (facts card, tips list, season strip) with a photo bolted on top. The redesign turns it into a **short film / cover story**: the entity as a character with a season, a maker, a ritual, and a reason you must go now.

---

## 0. Ground truth from the source (what exists today)

- **Hero**: `.detail-cover` — full-bleed image (real photo when `entity.images[0]` exists) OR a flat static JPG fallback `/img/cat/{cat}.jpg` (~96% of visits, since only ~60/1730 entities have real photos). Overlay + vignette on top, type chip + OCOP chip, `<h1>`, place link, action row (Save/Share/Visited/Want/Follow), 4-thumb strip, lightbox trigger.
- **Body**: two-column `.detail-body` = `.detail-main` (highlights row → lead → highlight blockquote → rich description with h2/h3 → extra sections → practical tips → best-time callout → KnowBeforeYouGo → food specialties → month/season strip → relationships list → NearbyEntities → Reviews → Community Feed → AI Travel Tips → Smart Recommendations) + `.detail-aside` (ContactWidget, OCOP stars, rating stars, a dense `.facts-card` with 4 fact-groups, trust/data-quality card, contact-row CTAs, claim CTA, AI Best Time, next-steps action list).
- **Mobile**: sticky bottom CTA bar (call/Zalo/map/plan) whenever ContactWidget isn't rendering its own.
- **CE tokens already in `variables.css`** (proven, reusable): `--font-editorial` (Fraunces stack), `--grain` (SVG noise data-URI), `--scrim-hero` (cinematic gradient), `--ease-cinematic`, `--dur-kenburns: 20s`, `--space-editorial`, `--measure-read: 68ch`, tri-province RGB triples (`--primary-rgb` clay, `--accent-rgb` amber, `--secondary-rgb` leaf, `--river-rgb`). The "sediment tick" (river→amber→clay vertical bar on section heads) is established on `xa-phuong/[id].vue` and `khu-vuc/[area].vue` via `.wp-sec h2::before`-style treatment.
- **No-photo reality**: `EntityCard.vue` already solves this at *card* scale with `useCategoryPlaceholder.ts` — a deterministic per-entity SVG (hash-seeded hue/angle gradient + category glyph). The detail page hero does **not** use this; it falls back to a shared static per-category JPG, which is the flattest, least "this specific place" moment on the entire site. This is the single biggest opportunity on this page.
- **CTA discipline**: contact-only is already correctly enforced (📞 Gọi / 💬 Zalo / 🗺️ Bản đồ / claim listing) — no booking, no cart. Keep exactly as-is; the redesign is about narrative and hierarchy, not funnel mechanics.

---

## 1. STORY ANGLE

Reframe the page's implicit question from **"what are the facts about X?"** to **"why must I go taste/see/meet this, and who will I meet when I do?"**

Every entity type gets a **narrative spine** — a fixed sequence of story beats that the existing data attributes already contain, just scattered and under-signaled:

| Entity type | Story spine (in order the page tells it) |
|---|---|
| `dish` (món ăn) | The ritual of eating it (when, with whom, what it's served alongside) → who makes it best nearby → the season it peaks → what a first-timer must order → the sensory cue (mùi, vị, độ giòn/béo) |
| `product` (OCOP) | The maker/hộ dân or hợp tác xã behind it → the process (thủ công vs máy) → what makes *this* one different from the same product elsewhere → how to verify it's the real OCOP-rated one |
| `craft_village` (làng nghề) | The generational thread (mấy đời làm nghề) → the sound/smell of the village at work → best time of day to see the craft happen, not just the shop |
| `attraction`/`experience` | The single most cinematic moment (bình minh trên sông, mùa nước nổi, đờn ca tài tử buổi tối) → who narrates it locally → what a visitor does there hour-by-hour |
| `accommodation` (lưu trú) | Wake-up view, not floor plan — what you see/hear the first morning |
| `event` (lễ hội) | The community behind it (đình, chùa Khmer, hợp tác xã) → the specific ritual moment (rước, thả đèn, đua ghe) → why *this year* / *this date* matters |
| `organization`/`place` | Kept closer to directory-factual (lowest narrative lift; still gets the masthead treatment for consistency) |

Concretely: the existing `attributes.significance`, `atmosphere`, `famous_for`, `must_order`, `signature_dish`, `booking_note`, `best_time` fields already carry this content — they're currently rendered as a flat bulleted "extra content" list and a "practical tips" `<ul>`. The redesign **does not require new backend fields for MVP** — it re-choreographs existing attributes into a story sequence and elevates 1–2 of them (the `highlight` quote, `atmosphere`, or `famous_for`) into large-type "pull quote" moments instead of small-print bullets.

Where a genuinely new field would help most (flagged for backlog, not required for this pass): a single `hook` sentence per entity — one-line reason-to-go distinct from `summary` — and a `maker_name`/`maker_story` field for product/craft_village. Until then, the design derives the hook from `highlight` → `famous_for` → first sentence of `description` in that priority order (graceful fallback chain, no new schema needed to ship v1).

---

## 2. CINEMATIC HERO / THESIS

**The hero becomes a "title card," not a banner.** Three concrete states, all built from data that exists today:

### A. Has real photo (~4% today, growing)
Full-bleed image, Ken Burns (`--dur-kenburns: 20s`, subtle 1.0→1.06 scale, respects `prefers-reduced-motion`), `--scrim-hero` gradient for text legibility (already a token — reuse verbatim). On top, in this exact stacked order:
1. **Dateline eyebrow** (matches xa-phuong/index CE pattern): wide-tracked caps, hairline rule — `{TYPE LABEL} · {AREA NAME} · {SEASON if peak}` e.g. `MÓN ĂN · CỒN CHIM · ĐANG RỘ MÙA`
2. **Fraunces `<h1>`** at `--text-3xl`+ scale (bigger than current — this is the biggest text on the page, full editorial weight)
3. **The hook line** (one italic serif sentence, ~12–16 words) sitting directly under the h1 — this is new visual real estate, the "cover-story dek." Pulled from the fallback chain above.
4. Action row (Save/Share/Visited/Want/Follow) — kept, but visually quieter (ghost/glass pills on the scrim, not competing with the h1).

### B. No real photo (~96% today) — the core fix
Do **not** fall back to the shared static category JPG. Instead, **promote the per-entity SVG placeholder system from EntityCard to full-bleed hero scale**, upgraded for hero duty:
- Same deterministic hash-seeded gradient (id → same look forever) but rendered large, with the category glyph as a **soft oversized watermark motif** bleeding off one edge (not centered — asymmetric, editorial, like a masthead illustration) rather than a small centered icon.
- Layer the existing `--grain` SVG noise token over the gradient at low opacity — turns a flat CSS gradient into something with tactile, printed-paper texture (the anti-AI-slop move: flat gradients read cheap, grain reads intentional).
- Add a thin **"phù sa" sediment wash** at the base of the hero: a horizontal band using the river→amber→clay tri-tone (same RGB tokens as the sediment tick, just laid horizontal and softly blurred) evoking silty water — a consistent brand signature for every "no photo" entity so the *absence* of a photo becomes a deliberate design moment, not a degraded one.
- Same eyebrow/h1/hook/actions stack on top, but ink-dark text directly on the gradient (no scrim needed since there's no photo to protect legibility from — gradient is tuned light enough at the text zone via the existing hue/lightness hash logic).
- Small honest microcopy, bottom-right, low-key: *"Ảnh minh hoạ theo màu đặc trưng — chưa có ảnh thật"* (1 line, `--text-2xs`, muted) — turns a limitation into transparency rather than pretending. This single line is the difference between "broken" and "designed."

### C. Signature interactive hero beat (works in both A and B)
A **"1 câu vì sao nên đến" (one-line why-now) chip** floats at the hero's lower edge, tied to `season.peak` / `attributes.peak_event` / `attributes.best_time` when present — e.g. `🌾 Đang mùa — chỉ còn 3 tuần nữa`. This is the curiosity trigger: urgency + specificity, using data the page already has (season months/peak) but currently buries in a small strip far below the fold.

---

## 3. LAYOUT + RHYTHM

Keep the proven two-column shell (`.detail-main` / `.detail-aside`) — it works and rebuilding it wholesale risks regression on a heavily-integrated page (reviews, feed, AI panels, relationships all key off it). The redesign is **rhythm and hierarchy inside that shell**, not a structural rewrite:

1. **Masthead** (hero, full-bleed, edge-to-edge — breaks the container like xa-phuong's `.wp-hero`)
2. **Highlights strip** — kept, but restyled as quiet utility (not competing with the story)
3. **Cover-story lead** — `lead` paragraph gets promoted to `--font-editorial` at `--text-lg`/`--text-xl`, first-letter drop-cap treatment (CSS-only `::first-letter`, Fraunces at 3-line height) for entities with rich `description` — the single cheapest "this is edited content, not a database row" signal.
4. **Pull-quote break** — the `attributes.highlight` blockquote, currently plain, becomes a full-width (breaks out of `--measure-read`) statement typographically distinct: large serif italic, sediment-tick accent on the left edge, generous whitespace above/below (`--space-editorial`). This is the "you feel something" beat mid-scroll.
5. **Story sections** (rich description h2/h3, extra-content, practical tips, food specialties, KnowBeforeYouGo) — re-sequenced per the narrative spine in §1, each section head gets the sediment-tick treatment already proven on xa-phuong (`h2::before` vertical river→amber→clay bar), consistent editorial rhythm (`--space-editorial` between major beats instead of the current tighter utility spacing).
6. **Season/month strip** — visually elevated (see §5) since it's the strongest existing "curiosity device" already in the data.
7. **Relationships / Nearby / Reviews / Feed / AI panels** — kept in current position/order (these are working, tested integrations — no reason to disturb), but each gets a small CE polish pass: heading in `--font-editorial`, sediment tick, consistent `--space-editorial` rhythm so they don't feel like a different, colder page glued to the bottom of a warm one (this is the exact "CE stops at the hero" critique from the prior audit — the fix is to let the section *headings* carry CE all the way down even though the interactive guts of Reviews/Feed/AI stay as-is).
8. **Sidebar** — kept sticky, but visually quieted (smaller type, more whitespace, ContactWidget gets top billing as the one "loud" element — it's the CTA, it should look different from the facts list beneath it).

**Responsive posture**: on mobile, hero height drops to ~62vh (from current implicit taller), hook line clamps to 2 lines, sediment wash band becomes thinner. Sticky CTA bar unchanged (already solid pattern).

---

## 4. TYPOGRAPHY

- **Display**: Fraunces (`--font-editorial`) for h1 (masthead), hook/dek line (italic optical size if available), pull-quote, and every section `<h2>`/`<h3>` — matching the established CE voice exactly, not inventing a new one.
- **Body**: keep system sans (`--font-sans`) for facts, tips, reviews, AI panels — the contrast between serif-story and sans-utility *is* the hierarchy signal (story sections feel written; utility sections feel referenced).
- **Scale moves specific to this page**:
  - `h1`: bump from current implicit size to `--text-3xl` (currently likely smaller/inherited) — it must be the single largest text on the page, larger than any card grid title site-wide, because this is the terminal/flagship view.
  - **Drop-cap** on the lead paragraph's first letter when `description` is rich (`hasRichDescription`): 3-line-height Fraunces initial, clay-colored, CSS-only (`::first-letter`).
  - **Hook/dek line**: italic Fraunces, `--text-lg`, `--ink-700`/muted-but-warm, max 2 lines with ellipsis fallback.
  - **Eyebrow/dateline**: `--text-2xs`, `--tracking-caps` (existing token), uppercase, hairline rule below — exact pattern reused from xa-phuong, not reinvented.
- **Numerals**: OCOP stars / rating / month-strip numerals stay tabular sans for scannability — do not serif-ify data.

---

## 5. SENSORY + MOTION + CURIOSITY

Curiosity devices, ranked by leverage, all CSS/light-JS, all `prefers-reduced-motion`-safe:

1. **Season/month strip → "living calendar."** Currently a flat row of 12 small cells. Upgrade: the peak months get a subtle pulsing amber glow (2.5s ease, opacity 0.85↔1, **paused entirely under reduced-motion**), and the current real-world month (via `new Date()`) gets a thin ink outline ring — "you are here" on the calendar. This single visual instantly answers "should I come now?" without reading text.
2. **Ken Burns hero** (real-photo case) — already tokenized (`--dur-kenburns`), just needs adoption on this page; currently the hero is static.
3. **Sediment-tick scroll accumulation** — as the reader scrolls through story sections, each section head's vertical tick (river→amber→clay) is already a static 3-stop gradient; on scroll-reveal (existing `useReveal()` composable, already imported) the tick can **grow from 0 to full height** on entry (150ms stagger after text fades in) — reads as "the river is following you down the page," a literal phù-sa motif, cheap to implement (it's a `scaleY` transform on an existing pseudo-element, gated by the same IntersectionObserver already driving `.reveal` classes elsewhere on this file).
4. **Pull-quote entrance** — text does a soft opacity+4px-rise reveal (already the site's standard `.reveal` treatment) but slightly slower/more deliberate (600ms vs standard 400ms) — pull-quotes should feel like a beat, not a bullet.
5. **Photo lightbox thumbs** — keep as-is (already good: arrows, dots, +N overflow).
6. **Micro-interaction on the "why-now" chip** (§2C) — a barely-there breathing scale (1.0↔1.02, 3s, paused on reduced-motion) so it reads as alive/urgent without being loud.
7. **Sensory word-choice as a design device, not just copy**: section icons for food specialties / practical tips (`🍽️ Nên thử`, `🎣`, `🌾`) are kept but given slightly larger scale + a warm circular chip background (already present in KnowBeforeYouGo pattern) so they read as tactile "stamps" rather than inline emoji.

**Explicitly avoided** (anti-AI-slop guardrails): no parallax-on-everything, no auto-playing video, no cursor-follow effects, no more than one "living" element visible in the viewport at a time (the month-strip glow and the why-now chip breathe at different rhythms so they never compete), no gratuitous stagger-animate-every-card (prior audit flagged over-animation risk).

---

## 6. UX FLOW

Information scent, front to back:

1. **Land on hero** → immediately know: what type of thing this is, where it is, whether it's in-season *right now*, and the one-line reason to care. (Today: you get type/place/name but must scroll to find "why.")
2. **Scroll past highlights** (quick-scan utility: call/zalo/map/hours/price/address) — kept exactly, this is a proven, tested, high-utility row; do not touch its function, only its visual quietness relative to the story below.
3. **Read the cover-story lead + pull-quote** → emotional hook lands before facts do.
4. **Move through story-spine sections** (per entity type in §1) → this is where curiosity compounds: each section should end with either a fact that begs the next question (season → "when exactly is peak?" → month-strip) or a related-entity link (maker's other products, nearby craft villages).
5. **Hit the season/month strip** → the "should I go now" answer, visually loud enough to not be missed.
6. **Relationships / Nearby** → "what else is near this" — exploration branch, kept as-is structurally.
7. **Reviews / Community Feed / AI Tips / Recommendations** → social proof + AI-assisted extension, kept as-is.
8. **Sidebar / sticky mobile bar**: the contact CTA is *always* one thumb-reach away throughout the scroll (already solid via ContactWidget + sticky-cta-bar) — the redesign doesn't touch this mechanic, only makes the *content above it* worth reading first.

**Friction removed**: currently the facts-card sidebar front-loads structured data that competes with the story for attention on first viewport (on desktop, side-by-side). Fix: sidebar's facts-card gets a lower visual weight (smaller type scale, `--text-sm` throughout instead of mixed sizes, no bold section labels louder than body headings) so eyes default to the main column's story first, facts-card second (facts-card is *reference*, not *narrative* — it should look retrievable, not attention-grabbing).

---

## 7. PREMIUM CUES

- **Consistent sediment-tick vocabulary** reused verbatim from xa-phuong/khu-vuc — a visitor who's seen those pages recognizes this page as "the same considered publication," not a different app bolted on.
- **Drop-cap + pull-quote** are classic editorial-magazine signals (Condé Nast / National Geographic register) — cheap CSS, high perceived craft.
- **Honest no-photo microcopy** (§2B) — admitting a placeholder, with intention, reads as *more* trustworthy than a generic stock fallback trying to hide the gap.
- **Trust/data-quality card** (already exists — `fresh`/`aging`/`stale` status) — keep, but restyle its status pill with the same rounded/hairline vocabulary as elsewhere; this quiet honesty-about-data-freshness is already a premium cue most competitor sites don't have — don't bury it, give it a touch more visual confidence (currently looks like an afterthought disclaimer; it should look like a badge of rigor).
- **Copy-to-clipboard micro-affordances on phone/address** — already implemented (`fact-copy` buttons) — keep, they're a nice touch already.
- **Restraint in iconography** — replace the current dense mix of raw emoji-as-bullet (📞💬🗺️🕒💰📍 inline) with the emoji kept only as *glyphs inside a designed chip* (circular/soft-square background), never bare inline emoji floating in serif body text — bare emoji next to Fraunces reads cheap; emoji-in-a-chip reads designed.

---

## 8. CULTURAL AUTHENTICITY

- **Phù sa sediment wash** (§2B) is the literal visual translation of "miền Tây sông nước" onto the one part of the page guaranteed to render for 96% of visits (the no-photo hero) — this is not decorative, it is the cultural signature doing double duty as the placeholder-image solution.
- **Season/month "living calendar"** maps directly to the lived Mekong Delta rhythm of mùa nước nổi / mùa trái cây / mùa lễ hội — Delta life is organized by season far more than by clock-time; making that legible visually (not just as 12 grey cells) honors that.
- **Narrative spine per type** (§1) is built around actually-Delta specifics: craft villages (làng nghề) framed by generational thread and the sound/work of the village, not "gift shop hours"; dishes framed by ritual/season, not a restaurant-review star rating; events framed by the community institution behind them (đình, chùa Khmer, hợp tác xã) rather than generic "festival, don't miss it!" tourism copy.
- **Avoid clichés explicitly**: no "hidden gem," "must-see," "paradise," "off the beaten path" stock phrases in any example copy (see §9) — Delta specificity (cồn, miệt vườn, chợ nổi, đờn ca tài tử, Khmer-Kinh-Hoa plurality) replaces generic travel-blog language everywhere the design references copy.
- **Khmer/Hoa representation**: when `attributes` or `description` signal a Khmer pagoda/festival or Hoa-community entity, the eyebrow dateline should surface that identity plainly (e.g. `LỄ HỘI · CỘNG ĐỒNG KHMER · TRÀ VINH`) rather than flattening all entities into one generic "Vĩnh Long" voice — specificity of community is itself a premium/authenticity cue, not just a content nicety.

---

## 9. COPY VOICE

Tone: **warm, specific, second-person-optional, sensory before superlative.** Never breathless; confidence comes from detail, not adjectives. Short sentences allowed to stand alone for rhythm.

**Example — dish entity (hook/dek line under h1), for "Bún nước lèo":**
> *Nước lèo phải nấu từ mắm bò hóc để dậy mùi — không phải tô bún nào ở miền Tây cũng làm được vậy.*

**Example — craft village pull-quote (attributes.highlight), for a chiếu (mat-weaving) village:**
> "Nghề này ông bà để lại, giờ tới đời thứ ba. Sáng sớm ra bến sông là nghe tiếng khung dệt rồi."

**Example — "why now" chip, seasonal fruit entity:**
> 🌾 Đang rộ mùa — chôm chôm ngọt nhất tháng này, còn khoảng 3 tuần.

**Example — event entity eyebrow/dateline:**
> LỄ HỘI · CHÙA KHMER · TRÀ VINH · CÒN 12 NGÀY

**Example — no-photo hero honesty microcopy:**
> Ảnh minh hoạ theo tông màu đặc trưng của {loại hình} — vinhlong360 chưa có ảnh thật cho địa điểm này.

---

## 10. SIGNATURE MOMENT

**The "phù sa hero" — every entity without a real photo gets a large, deliberate, hash-unique gradient-plus-grain masthead with an oversized asymmetric category motif and a horizontal river→amber→clay sediment wash at its base, instead of a generic stock-category fallback image.** This is the one thing a visitor remembers: *even the placeholder feels like it belongs to this specific place*, and it turns the platform's biggest content gap (no photos for 96% of entities) into a recognizable, on-brand visual signature rather than a degraded experience. Paired with the honest one-line disclosure, it reads as intentional design rather than missing content — which is the entire reframe this page needs.

Runner-up signature: the **living month-strip** (peak-month glow + "you are here" ring) — the single visual that answers "should I go now?" without reading a word.

---

## 11. COMPONENTS + FEASIBILITY

All CSS-tokens (no Tailwind), images AI-gen-only or existing per-entity SVG placeholder (no new image asset pipeline required for v1), CTA remains contact-only (no changes to that logic), full dark-mode parity required on every new visual (gradients/wash/grain must have dark-mode variants using existing dark token overrides), `prefers-reduced-motion` must disable all new motion (Ken Burns, tick-grow, glow-pulse, chip-breathe) per existing site convention.

**New/modified components:**

1. **`EntityHeroPlaceholder.vue`** (new, small) — extracts + upgrades `useCategoryPlaceholder.ts`'s gradient logic to hero scale: large asymmetric motif placement, `--grain` overlay, horizontal sediment-wash band (`linear-gradient` using `--river-rgb`/`--accent-rgb`/`--primary-rgb` at low opacity, `filter: blur()`), honest microcopy slot. **Reusable**: any future entity-adjacent hero (e.g. a "collection"/itinerary cover) can reuse this component instead of re-deriving placeholder logic.
2. **`detail.css` additions**: `.dc-eyebrow` (dateline), `.dc-hook` (dek line, italic Fraunces), `.dc-h1` size bump, `.lead::first-letter` drop-cap rule (scoped to `.rich-desc .lead` or similar guard so short/plain summaries don't get an orphaned single-letter drop-cap), `.entity-highlight` pull-quote restyle (full-bleed variant + sediment-tick left edge), `.section-subtitle::before` sediment-tick (copy exact pattern from `xa-phuong` CE CSS — do not reinvent).
3. **Month-strip**: add `.ms-cell.peak` glow keyframe + `.ms-cell.current-month` ring class computed from `new Date().getMonth()+1` compared against nothing new in the schema — pure client-side date math already available.
4. **"Why now" chip**: small new template block in the hero, computed from existing `entity.season.peak` / `attributes.peak_event` / `attributes.best_time` fallback chain — **no backend change required**.
5. **Section-head sediment tick rollout**: apply the existing xa-phuong `h2::before` CSS pattern to every `<h2 class="section-subtitle">` and the relationships/rating headings already in this file — pure CSS class/selector reuse, zero new JS.
6. **`useReveal()`**: already imported and used (`class="reveal"` on several blocks) — extend usage to pull-quote and remaining un-revealed sections (facts-card, trust-card) for consistent rhythm; no new composable needed.

**Explicitly reusable across other pages** (flag for the other unit owners): `EntityHeroPlaceholder.vue` (any hero-scale no-photo context), the dek/hook fallback-chain pattern (`highlight → famous_for → first sentence of description`), the sediment-tick section-head CSS (already shared, just needs adoption here), and the "living calendar" peak-glow + current-month-ring treatment (reusable on itinerary/season-index pages).

**Not touched / explicitly out of scope for this pass**: ContactWidget internals, Reviews/Feed/AI panel internals, relationships pagination logic, JSON-LD/SEO logic, the sticky mobile CTA bar mechanics — all functionally solid, redesign only reaches their *headings/typography* for rhythm consistency.
