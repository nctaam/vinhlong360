# theo-mua.vue · tuyen-duong.vue · danh-ba.vue — Seasonal · Routes · Directory

> **STATUS (2026-07-07): concept Ý TƯỞNG — KHÔNG thực thi nguyên văn.** Viết TRƯỚC declutter 3 đợt (ship 2026-07-07) và TRƯỚC chốt định vị 2026-07-06. Khi xung đột: code hiện tại + CLAUDE.md thắng. Trước khi thực thi bất kỳ mục nào: (1) dẹp mọi copy "miền Tây / ba tỉnh" — dùng khung tỉnh-Vĩnh-Long-mới; (2) KHÔNG dùng địa danh ngoài tỉnh (Cái Bè, Lai Vung… thuộc Đồng Tháp); (3) KHÔNG claim "đã xác minh"/quy mô đội ngũ; (4) re-ground line-number trên code hiện tại. Cảnh báo đầy đủ: 00-narrative-system.md.


*A deep redesign concept for the "when / how / who-do-I-call" trio — the three utility spines that carry a visitor from curiosity to a real trip. Prior grades: theo-mùa 8.5 (has the season-ring, the site's best signature visual), tuyến-đường 7.0, danh-bạ 7.0 (strongest unmet market gap per user research).*

---

## 0. The thesis for this unit

These three pages are not really "seasonal listings," "a route catalog," and "a phone book." They are **three different clocks**: the clock of *when* (mùa), the clock of *the road* (tuyến đường — a day unfolding stop by stop), and the clock of *civic reliability* (danh bạ — the number that answers at 7am when a traveler is stuck). Right now they're built to the same catalog template with different heroes bolted on. The redesign's job is to let each page keep its own *temporal shape* — a ring, a road, a directory card index — while sharing one visual grammar (CE) and one component spine (EntityCard, CatalogInterstitial, CatalogSpotlight).

The season-ring is the proof of concept: it's the one place on the whole site where the *interface itself performs the content* (a wheel, not a list, telling you where in the year you stand). This concept propagates that idea — "make the structure of the page embody the structure of the information" — to routes (a road, not a stack of cards) and to the directory (a civic index, not an admin form).

---

## 1. theo-mua.vue — "Lịch mùa" (the living almanac)

### 1.1 STORY ANGLE
Not "products filtered by season" — it's **the year itself, breathing**. Miền Tây doesn't have four seasons; it has a wet/dry pulse and, layered on top, a flood pulse (mùa nước nổi) that is the region's most singular temporal event — water arriving not as disaster but as gift, carrying phù sa, cá linh, bông điên điển for ten weeks and then receding. The story is: *you are standing at a specific point on a wheel that has been turning here for centuries, and right now, specific things are at their peak — taste them before the wheel turns again.* Every card under "Cao điểm" is not a listing, it's an expiring invitation.

### 1.2 CINEMATIC HERO / THESIS
Keep and deepen the season-ring — it's the keystone. Today it's a small conic-gradient badge beside the headline. Elevate it to the actual **navigational device**: a large annular calendar (a full 12-notch ring, not just a colored disc) that sits center-hero, with the current month notch lit and the other 11 dimmed. Clicking any notch on the ring *is* the month picker — retire the separate 12-button `.month-grid` grid entirely (or keep it as a compact secondary/mobile fallback below the fold) so the ring becomes both the hero visual and the primary control, collapsing decoration and function into one object — the strongest "signature moment → propagate" move available.

Behind the ring: a full-bleed Ken-Burns photo (or, honestly, the AI-gen seasonal SVG texture given imagery scarcity) that **retints itself per quarter** — cool river-teal wash for mùa nước nổi, warm amber for cao điểm mùa hè, leaf-green for mùa xuân miệt vườn — so scrubbing the ring changes the entire hero's color temperature, not just an emoji. This is the single most "wow, the page responds to time" moment on the site.

### 1.3 LAYOUT + RHYTHM
- Hero: full ring + retinting backdrop + one-line seasonal verdict ("Tháng 9 — nước đang lên, cá linh vào mùa").
- Directly below the ring: the existing stat trio (đang mùa / cao điểm / per-type counts) as a slim ticker, not boxed cards — feels like a live readout, not a KPI dashboard.
- CatalogSpotlight stays as the "hero item" — but retitle its section eyebrow to lean into narrative ("Món/mùa đáng thử nhất tháng này" vs generic "nổi bật").
- Peak honor row keeps its horizontal scroll-row — this is correct, it's a "shelf," browsable and finite.
- Type sections (trải nghiệm / nông sản / ẩm thực) stay separated with the sediment divider — good, keep.
- NEW: a **"Dòng thời gian mùa vụ"** (season timeline) band before the full grid — a single horizontal bar spanning Jan→Dec with colored zones (mùa khô / đầu mùa mưa / cao điểm trái cây / mùa nước nổi) and the current month as a marker on it. This turns the closing "Lịch mùa vụ tóm tắt" paragraph (currently plain prose) into a visual instrument that echoes the ring's logic in linear form — reinforcing rather than repeating.
- Full grid stays paginated ("Xem thêm") — correct restraint, don't infinite-scroll a finite dataset.

### 1.4 TYPOGRAPHY
- Hero headline "Tháng 9 — đi đâu, ăn gì?" in `--font-editorial` (Fraunces) at a large display size, italicized on the verdict clause ("*nước đang lên*") the way the homepage does with its dateline emphasis.
- Month names on the ring rendered in small-caps sans, not the giant serif — the ring is a diagram, not a headline; mixing scripts (serif verdict + sans diagram labels) reinforces the "instrument panel vs. editorial voice" split intentionally.
- Section eyebrows keep the wide-tracked uppercase (`--tracking-caps`) already established — good, don't touch.

### 1.5 SENSORY + MOTION + CURIOSITY
- Ring notch hover: the notch's wedge brightens and a tooltip-card previews that month's top 1 item image + count, so scanning the ring becomes browsing without clicking — pure discovery device.
- Retint transition on month change: 400–600ms cross-fade of hero backdrop hue, no pop.
- Keep the existing seasonal-bob emoji animation but tone it down to the ring only (currently also on hero icon — one bob per screen, not two, avoids the "everything wiggles" AI-slop tell).
- Sensory copy: lean on texture words already in the editorial block (bông điên điển vàng rực, cá linh non kho mía) — pull 1–2 of these into the hero subtitle dynamically per quarter rather than leaving them buried in the bottom essay.
- Reduced-motion: ring retint becomes instant swap, no cross-fade; notch hover tooltip still works (it's not decorative motion, it's information).

### 1.6 UX FLOW
Ring (see the year) → verdict line (know what's peaking) → spotlight (one hero pick) → peak shelf (honor row, low commitment horizontal scroll) → type sections (organized deep dive) → timeline band (recall the whole year, jump months) → full grid (exhaustive) → B2B contact callout → editorial essay (context for the curious) → cross-links. Friction reducer: the ring is *itself* the "change month" affordance, so users never need to scroll to a distant control — the primary interaction sits in the hero, always reachable via sticky mini-ring in nav if scrolled past (optional stretch).

### 1.7 PREMIUM CUES
- Ring uses real conic-gradient + inset shadow (already present) — keep, but add a fine tick mark per month on the ring's outer edge (12 hairline ticks) so it reads as a precision instrument, not a colored donut.
- Peak badge gradient + pulse-on-hover (already present) is a good premium detail — keep.
- Micro-detail: the "mục đang mùa" pill number should count up (CountUp already used) — extend CountUp to the ring's center readout too.

### 1.8 CULTURAL AUTHENTICITY
Mùa nước nổi is the crown jewel here — already well written in the essay. Make sure the ring's flood-quarter wedge visually reads as water (river-teal, subtle wave-texture fill via SVG pattern, not a flat gradient) so a visitor immediately intuits "this quarter = water season" before reading a word. Avoid generic "4 seasons" language (spring/summer/autumn/winter icons like ❄️🍂) — the site already correctly avoids this; keep the quarter labels as-is (mùa xuân miệt vườn / đầu mùa nắng / cao điểm mùa hè / mùa thu hoạch / mùa nước nổi).

### 1.9 COPY VOICE
Present-tense, urgent-but-warm, second person implied not stated. Examples:
- Hero verdict: *"Tháng 9 — nước đang lên. Cá linh non, bông điên điển đang vào mùa ngon nhất năm."*
- Peak banner: *"Cao điểm tháng 9 — những thứ này chỉ ngon nhất đúng lúc này, đừng để lỡ."*
- Timeline caption: *"Mười hai tháng, một nhịp sông. Cuộn để xem tháng nào có gì."*

### 1.10 SIGNATURE MOMENT
**The retinting season-ring-as-navigation**: scrub the ring, the whole hero recolors and the verdict line rewrites itself — the page becomes a working almanac instrument instead of a filtered list with a badge.

### 1.11 COMPONENTS + FEASIBILITY
- `SeasonRing.vue` (new, extracted from inline `.season-ring` markup) — props: `month`, `quarter`, `onSelect`; emits month clicks; pure CSS conic-gradient + SVG tick overlay, no canvas/WebGL needed. **Reusable**: entity detail pages that show "mùa: T5–T7" could embed a mini read-only version of this ring instead of plain text — propagate the keystone site-wide as recommended.
- `SeasonTimeline.vue` (new) — horizontal CSS grid bar, 12 fixed-width cells, colored via the same quarter token map as the ring (single source of truth — extract `QUARTER_META` into `useSeason.ts` composable so ring + timeline + any future usage share one palette definition).
- Hero backdrop retint: CSS custom property `--season-hue` set inline per quarter, background using `color-mix`/gradient referencing it — no JS-driven style recalculation beyond one class swap.
- All new pieces respect dark mode (ring already does) and `prefers-reduced-motion` (already has a block to extend).

---

## 2. tuyen-duong.vue — "Tuyến đường" (the road as the unit, not the card)

### 2.1 STORY ANGLE
This is not "6 routes in a grid" — it's **6 days you could have**. Each route is a promise of a specific Saturday: waking up early, the ferry to Cù lao An Bình, fruit dripping down your wrist, lunch under a garden canopy. The story angle is *the itinerary as a lived morning-to-evening arc*, not a list of stops with bullet notes. Right now `route-stops` renders as a plain `<ol>` — functionally fine, narratively flat. The redesign should make each route feel like a **hand-drawn day**, stop by stop, with a sense of pacing (departure time feel, midday rest, golden-hour return) even though we don't have literal clock times.

### 2.2 CINEMATIC HERO / THESIS
Hero keeps the `🛤️` icon + stat count, but the real cinematic move belongs one level down: replace the flat `route-grid` of stacked cards with a **map-vignette hero strip** — a thin abstracted "river & road" line-art SVG banner (phù sa clay/leaf/river gradient, following the actual tri-province shape loosely) that runs the width of the page just under the hero, with 6 small pins marking where each route lives. This gives spatial orientation before the list — "oh, these are spread across 3 areas" — which the area filter chips currently communicate only as text labels.

### 2.3 LAYOUT + RHYTHM
- Replace the plain header/body stacked route-card with a **two-column "day-strip" card**: left rail is a vertical mini-path (a dotted line with numbered stop-dots, echoing a paper map route line) using the accent color per area (clay/leaf/river already mapped via `.area-vinh-long/.area-ben-tre/.area-tra-vinh`); right column holds description + tips + CTA. On mobile this collapses to the rail sitting inline above each stop (a "breadcrumb of the day"), not disappearing.
- Keep chip-row area filter, but restyle chips to match the route's own color-coding (a clay chip, a leaf chip, a river chip) so the filter *previews* the route palette before you even click into a card — visual consistency between filter and content.
- Section rhythm: Hero → area filter (with color-matched chips) → editorial framing (self-drive practicalities) → interstitial → route list (day-strip cards) → cross-links. This is close to current — the win is entirely inside the card, not the page skeleton.
- Route count/duration/distance move from a subhead line into a **small stat trio** per card (like the hero's CountUp stats, scaled down) — "6 điểm dừng · 1 ngày · ~40 km" as three inline mini-stats, giving route cards the same premium-stat treatment the hero already uses elsewhere on the site.

### 2.4 TYPOGRAPHY
- Route name in `--font-editorial` italic for the poetic ones ("Vòng mùa nước nổi") — small but distinctive, matches CE mastheads.
- Stop names stay sans-serif, bold, left-aligned along the rail — these are wayfinding text, should read fast, not editorialized.
- Tips block ("💡 Mẹo") gets a slightly larger, warmer treatment — this is where the page's personal voice lives; consider dropping the emoji-as-label pattern for a small caps "MẸO ĐI ĐƯỜNG" eyebrow instead, consistent with the site's eyebrow convention elsewhere.

### 2.5 SENSORY + MOTION + CURIOSITY
- The rail's stop-dots reveal in sequence on scroll-into-view (stagger already exists via `stopFadeIn` — good, keep, just re-home it onto rail dots instead of list-item text so the "path drawing itself" feeling is literal).
- Hover a stop-dot → its note callout expands slightly (already essentially works via `route-stops li:hover`) — extend so hovering a dot also nudges the connecting line color, reinforcing "this is a path," not "this is a list."
- Discovery device: a **"Tuyến này hợp mùa nào?"** micro-tag pulled from the route's implicit season cues (e.g. "Vòng mùa nước nổi" → auto-tag T8–T11 using the same `QUARTER_META` as theo-mùa) linking directly to `/theo-mua?mua=9` — this is the single highest-leverage cross-link on the whole site: it ties the almanac to the road, letting a user go from "it's flood season" → "here's the flood-season route" or vice versa. Currently these two pages don't reference each other at all despite being thematically inseparable.
- Reduced motion: rail dot stagger becomes an instant reveal; hover nudge removed, color-only state change retained (non-motion, allowed).

### 2.6 UX FLOW
Filter by area (optional) → skim day-strip cards (rail gives instant "how much is this route" read without needing to read prose) → tips give trust/practicality → two low-friction exits per card: "📍 area hub" (contextual explore-more) and a NEW **"📞 Hỏi HTX/homestay dọc tuyến"** contact-only CTA that routes to `/lien-he` prefilled with the route name — right now routes dead-end at "xem bản đồ," with zero path to actually contacting anyone about the trip, which is a missed conversion for a page whose entire premise is "go do this." (Contact-only per constraints — no booking.)

### 2.7 PREMIUM CUES
- Numbered stop-dots (1, 2, 3…) rather than a bare bullet `<ol>` — small detail, signals "this was designed as a journey," not autogenerated from a JSON array (even though it is).
- Distance/duration stat trio styled identically to the hero's `CountUp` stats — visual rhyme between hero and card signals a considered system, not ad hoc components.
- Area-color-coded left rail bleeds subtly into the card's ambient shadow tint on hover (a hint of clay/leaf/river glow) — matches the existing `.route-card:hover` glow treatment, just anchor its hue to `r.area` instead of always `--primary-rgb`.

### 2.8 CULTURAL AUTHENTICITY
Keep the routes' existing specificity (Cù lao An Bình, Mang Thít gạch gốm, chùa Khmer Trà Vinh, dừa sáp Cầu Kè) — this is already strong, resist the urge to generify stop names. The rail motif itself should nod to the **phù sa sediment signature** already established site-wide (vertical river→amber→clay tick) — literally reuse that gradient as the rail's line color when a route crosses multiple areas (the ẩm thực tour spans all 3), visually saying "this is a cross-province journey" without a legend.

### 2.9 COPY VOICE
Practical-warm, second person imperative, a co-pilot's voice:
- *"Xuất phát sớm, để nắng chiều dành cho vườn bưởi."*
- *"6 điểm dừng, một ngày, không cần tour — chỉ cần một bình xăng đầy và một cái bụng đói."*
- Tip eyebrow: *"MẸO ĐI ĐƯỜNG"* instead of "💡 Mẹo:".

### 2.10 SIGNATURE MOMENT
**The day-strip rail** — a route stops being a card with a bullet list and becomes a small drawn path you scroll down, stop by stop, dot by dot, in the route's own color.

### 2.11 COMPONENTS + FEASIBILITY
- `RouteDayStrip.vue` (new) — replaces the inline `route-stops` `<ol>`; renders a CSS-only vertical rail (`::before` line + absolutely positioned numbered dots), takes `stops[]` + `area` color token. No new JS dependency.
- `RouteSeasonTag.vue` (new, tiny) — cross-references route id/name against `QUARTER_META` keywords (or an explicit `season` field added to `RouteDef` in `routesContent.ts` — additive field, backward compatible per B2) and renders a pill linking to `/theo-mua?mua=N`.
- Contact CTA reuses existing `/lien-he` pattern already used by the B2B callout on theo-mùa — **fully reusable**, just parametrize the prefilled subject.
- Map-vignette hero strip: static inline SVG (hand-drawn line art, tri-province silhouette), no map library, no tiles, no cost — respects budget constraint.
- All new visuals dark-mode aware (color tokens, not hardcoded hex) and motion gated by `prefers-reduced-motion`.

---

## 3. danh-ba.vue — "Danh bạ" (civic trust, given the weight it deserves)

### 3.1 STORY ANGLE
The research finding is blunt: **danh bạ hành chính is the strongest unmet market gap** on the entire site — nobody else is doing this well for the merged province. The story isn't "a directory," it's **"the number that works when you actually need it"** — a flat tire at 6am, a lost ID card, a question about a construction permit, a tourist needing a police report for insurance. This page should stop apologizing for being "just a directory" and lean into being the **most trustworthy civic utility in the region** — verified-source badges, freshness timestamps, and a correction loop are already present in the code; the design should make trust *visible at a glance*, not buried in a footer line.

### 3.2 CINEMATIC HERO / THESIS
Not cinematic in the travel-photography sense — this page's "hero moment" is **clarity and authority**. Replace the generic `🏛️` emoji-hero with a **live coverage map-strip**: a simple horizontal bar segmented into the 3 areas (Vĩnh Long / Bến Tre / Trà Vinh) with each segment's fill-percentage showing "124/124 xã phường covered" as a literal filled bar — this single glance answers "does this directory actually cover my area?" before a user commits to picking a ward. It's the danh-bạ equivalent of the season-ring: a diagram that *is* the content, not a decoration next to it.

### 3.3 LAYOUT + RHYTHM
- Hero → coverage bar (new) → region quick-picks (existing, keep) → editorial framing (existing, shorten slightly, it's currently doing double duty explaining both the *service* and the *administrative merger caveat* — split those into two shorter blocks so the merger-caveat reads as a dedicated trust note, not buried mid-paragraph) → ward picker → **trust bar** (new, see below) → facility list → cross-links.
- The current facility `<li class="fac">` cards are functionally solid (kind badge, address/phone/hours rows, source+verified check, report-wrong-info link) — keep the content model, upgrade the visual hierarchy: promote the phone number to the most visually dominant element on the card (largest, boldest, one-tap `tel:` — it already is a tap target, just needs to look like the single most important thing on the card, since "call this number" is the entire point of the page).
- NEW: a **trust bar** directly above the facility list — a slim strip stating "✓ X nguồn chính thống · cập nhật gần nhất Y ngày trước · Báo sai → phản hồi trong 48h" (or similar honest framing) so the credibility signals currently scattered per-card (small ✓ mark, relative-time footer) get one aggregate, confident statement up front. This is the single highest-leverage move for elevating "civic utility" into "the site you trust most" — it's a strategic reframe, not just a visual tweak.

### 3.4 TYPOGRAPHY
- This page should be the **least serif-heavy** page in CE — civic/utility content wants clarity and speed-of-scan, not editorial mood. Keep `--font-editorial` confined to the H1 only (for brand consistency with other CE pages) and let everything below — ward names, facility names, phone numbers — sit in `--font-sans` at slightly larger-than-body sizes for scanability, especially the phone number itself (treat it like a price on an e-commerce page: big, bold, unmissable).
- Facility name: bump from current implicit body-bold to a true `h4`-equivalent scale — right now `.fac-head strong` likely sits close to body size; visually these cards should read like directory entries in a well-typeset paper phone book, not chat bubbles.

### 3.5 SENSORY + MOTION + CURIOSITY
- This is the one page in the trio that should be **motion-quiet** — visitors here are often in a hurry or slightly stressed (lost, need a permit, need a police contact). Keep the existing hover-lift on `.fac` cards (subtle, fine) but do NOT add new decorative motion. The "discovery device" here isn't animation, it's **information scent**: the ward-hub-link ("Xem trang đầy đủ xã/phường này →") is already present and correctly placed — strengthen it visually (it currently reads as a plain text link) into a small pill/button so users notice they can pivot from "just the phone numbers" to "the whole story of this xã/phường" (tourism, sản vật, etc.) — this is the bridge from utility to the rest of the site's narrative content, and it's currently underweighted relative to its strategic importance.
- Micro-interaction: selecting a ward from the dropdown could cross-fade in a tiny one-line "ward fact" (population/area type badge, or simply the area name + emoji) above the facility list, giving a beat of orientation before the list loads — small, calm, not showy.

### 3.6 UX FLOW
Region quick-pick (broad orientation) → ward select (narrow) → trust bar (confidence before reading) → facility cards, phone-forward (fastest path to the actual need: calling someone) → ward-hub pivot (upsell into narrative content) → report-wrong-info (closes the trust loop, already well-built — keep exactly as is, it's a rare "user as verifier" pattern done right) → cross-links. The one friction point worth removing: right now there's no way to jump straight to "my ward" without scrolling past the full quick-pick grid if a user already knows their ward name — consider adding a lightweight type-ahead/search input above or beside the `<select>` for the 124-ward list (a plain `<select>` with optgroups is serviceable but slow for a long list on mobile).

### 3.7 PREMIUM CUES
- Verified-source checkmark (already present, `✓` in a circle) — good, but make it slightly more prominent: a filled badge with "Nguồn chính thống" as a tooltip/label rather than a bare tiny circle, so first-time users understand what the checkmark *means* without hunting for the title attribute.
- Freshness timestamp ("cập nhật 3 ngày trước") — keep, this is already a strong trust signal; consider color-coding it subtly (green-ish if <30 days, neutral if older) so staleness is legible at a glance without reading the number.
- The empty-hint state (before a ward is picked) is already well-designed (halo icon, clear CTA framing) — keep as is, it's one of the better empty states on the site.

### 3.8 CULTURAL AUTHENTICITY
This page's authenticity is **civic**, not scenic — it earns trust through precision (real UBND/công an contacts), not through Mekong imagery. The one place to keep cultural warmth alive: the editorial framing paragraph, which already correctly explains *why* this matters to a traveler (xin xác nhận tạm trú, hỏi quy hoạch, liên hệ công an) — keep this human framing, don't let the page become sterile bureaucratic UI. The administrative-merger caveat (16 xã→phường, 124 total) is handled honestly already — preserve that transparency, it's a differentiator versus any AI-hallucinated competitor directory.

### 3.9 COPY VOICE
Plain, respectful, zero cuteness — this is the one page where editorial flourish would read as tone-deaf (nobody wants a poetic sentence while trying to find the công an number). Examples:
- Trust bar: *"Dữ liệu từ cổng thông tin chính thống · cập nhật thường xuyên · báo sai, chúng tôi kiểm tra trong 48 giờ."*
- Ward-hub pivot button: *"Xem đầy đủ xã/phường này — du lịch, đặc sản, lưu trú →"*
- Empty hint (unchanged, already good): *"Chọn khu vực rồi chọn xã/phường ở trên để xem danh bạ cơ quan hành chính."*

### 3.10 SIGNATURE MOMENT
**The coverage bar + trust bar pairing** — in two glances (before picking a ward, and again just above the results) the visitor sees "yes, this covers my area" and "yes, this is verified and current" — turning a civic utility page into the most confidence-inspiring piece of UI on the site, which is exactly the strategic opportunity the research flagged.

### 3.11 COMPONENTS + FEASIBILITY
- `CoverageBar.vue` (new) — 3-segment horizontal bar, width proportional to `wardGroups[i].wards.length`, using the same `AREA_RGB` map already defined inline in the page (promote it to `useConstants.ts` alongside `AREA_META` — it's currently duplicated ad hoc in `danh-ba.vue`; centralizing lets tuyến-đường's route header colors, and any future page, reference the same values — direct reuse win).
- `TrustBar.vue` (new, small) — computes aggregate verified-source count + most-recent update across `facilities.value`, pure derived state, no new API calls.
- `WardTypeahead.vue` (new, optional/stretch) — a filterable combobox over the existing `wardGroups` data; if scoped out for budget, a simple `<input>` client-side filter over the existing `<select>` options achieves 80% of the value with near-zero code.
- Ward-hub pivot button: pure CSS restyle of the existing `.ward-hub-link` anchor into a `.btn btn-outline`-class pill — no new component needed, just apply the existing button system already used elsewhere (`btn-outline`, `btn-ghost` classes already imported site-wide).
- All new elements respect dark mode via existing token set (`--primary-rgb`, `--secondary-rgb`, `--river-rgb` per `AREA_RGB`) and add no motion requiring a `prefers-reduced-motion` override beyond what already exists.

---

## 4. Cross-cutting reuse map

| Piece | Built for | Reusable elsewhere |
|---|---|---|
| `SeasonRing.vue` | theo-mua hero | Entity detail pages (mini read-only ring next to "Mùa: T5–T7" text), homepage seasonal teaser |
| `QUARTER_META` (extracted to `useSeason.ts`) | ring + timeline | `RouteSeasonTag`, any future seasonal badge |
| `RouteSeasonTag.vue` | tuyen-duong cards | Could appear on itinerary (`lich-trinh`) pages too |
| `AREA_RGB` / `AREA_META` (centralized in `useConstants.ts`) | danh-ba coverage bar | tuyen-duong route header colors (already using a parallel but separately-defined mapping — this is a natural dedupe) |
| Contact-CTA pattern (prefilled `/lien-he`) | tuyen-duong route contact | theo-mua B2B callout already does this — literally the same pattern, just add a route-specific variant |
| `.btn btn-outline` ward-hub pivot | danh-ba | Nothing new — proves the existing button system already covers this need |

## 5. Constraints honored throughout
- No booking/checkout anywhere — all new CTAs route to `/lien-he` (contact-only) or internal cross-links.
- All new visuals (ring, timeline, day-strip rail, coverage bar, trust bar, map-vignette) are CSS/SVG only — no canvas, no map tiles, no paid APIs, no new JS dependencies.
- Every new component ships with a `.dark` variant using existing CSS custom properties, and a `@media (prefers-reduced-motion: reduce)` block disabling any transition/animation introduced.
- Imagery: hero backdrops for theo-mua and tuyen-duong may eventually use AI-gen photography (cx/gpt-5.5-image) per the site's imagery policy, but every concept here degrades gracefully to the existing SVG/gradient placeholder system — nothing here is blocked on new photography.
