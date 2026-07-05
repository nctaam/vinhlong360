# Events + Festivals — `su-kien.vue` (6.5) + `le-hoi.vue` (7.0)

> Unit verdict up front: **merge into one page, two registers.** Today these are ~90%-identical shells (same `/api/events`, same `.event-row`/`.cal-*` CSS, same controls, same cross-links) wearing two icons (🎪 vs 🎋). Maintaining two near-duplicate catalog pages is itself an anti-pattern for a solo dev, and it also *dilutes* the one genuinely strong asset the unit has: `le-hoi.vue`'s cultural-authenticity writing (Kinh–Khmer–Hoa, Ok Om Bok, Lễ Nghinh Ông). The redesign below proposes **one route, `/su-kien`, with an internal `Lễ hội truyền thống` vs `Sự kiện & hội chợ` toggle** (URL-addressable via `?loai=le-hoi`), so the two content classes live side by side instead of forking the codebase. Everything below is written against that merged model, with a fallback note on how to apply the same ideas if the two pages must stay physically separate.

---

## 1. Story angle

An events/festivals page is not "a database of things happening on dates." It is **the calendar of the sông nước living its year out loud.** Every entry on this page is a moment when the ordinary daily rhythm of the Delta — the tide, the moon, the harvest, the market — breaks into something communal and visible. The story this page tells is: *the land here keeps its own clock, count by moon not by month, and if you show up on the right day you get let in on it.*

Two registers, one story:
- **Lễ hội (festival) entries** are the *ceremonial register* — inherited time. Lễ Kỳ Yên at the đình, Ok Om Bok's ghe ngo racing the Maspéro, Nghinh Ông honoring the whale-spirit, giỗ Cụ Phan Thanh Giản. These are dated by âm lịch (lunar calendar) and by ancestry, not by a marketing calendar. The story is **inheritance** — three peoples (Kinh, Khmer, Hoa) each keeping their own count, overlapping on the same soil.
- **Sự kiện (event) entries** are the *contemporary register* — hội chợ nông sản, food festivals, marathons, OCOP fairs. The story is **the Delta showing up now**, on the modern calendar, still smelling like phù sa but wearing a race bib.

The page's real job: make a visitor who has never heard of Ok Om Bok feel, within one scroll, that they are looking at a living ceremonial calendar they can actually catch — not a listings database with a calendar-view toggle bolted on.

## 2. Cinematic hero / thesis

**"Đất này giữ lịch riêng."** ("This land keeps its own calendar.")

Replace the current generic `.catalog-hero` (icon emoji + h1/subtitle + stat chips — identical shell as every other catalog page) with a **living calendar-strip hero**:

- Full-bleed masthead in `var(--font-editorial)`, dateline eyebrow above it reading the *lunar* date alongside the Gregorian one, e.g.:
  `HÔM NAY · 05.07.2026 · ÂM LỊCH 21 THÁNG 5` — small caps, wide-tracked, hairline rule beneath, exactly the CE dateline-eyebrow pattern already established elsewhere.
- Headline: **"Lịch không chỉ đếm bằng ngày dương."** / sub-dek: "Cúng Trăng, Kỳ Yên, Nghinh Ông, hội chợ trái cây — mỗi tháng miền Tây có một nhịp lễ hội riêng. Đây là lịch sống của ba tỉnh."
- **The signature interactive beat**: a horizontal **moon-phase / lunar ribbon** across the top of the hero — a thin strip showing the current lunar day as a small moon glyph (waxing/waning silhouette rendered as a simple CSS/SVG crescent, not a photo), with the next 3 upcoming lễ hội pinned to their lunar positions on the ribbon as small ticks. This single device does more cultural-authenticity work than any stock imagery could: it visually proves "this calendar is lunar-first," which is the entire cultural thesis of the page.
- If there is a festival happening **today or within 3 days**, the hero gets a live urgency treatment (see §5/§10 — "Đang diễn ra" ceremonial pulse) replacing the generic stat-chip row with a single "**Đang diễn ra: Ok Om Bok — Trà Vinh, còn 2 ngày**" banner in the amber/clay accent, so the hero itself becomes time-aware rather than static.
- Retain the `--space-*`/phù-sa vertical tick as the section-head signature (already established), but let the hero's **background scrim shift hue by register**: leaf-tinted for lễ hội (agrarian, ancestral — leaf #2E7D5B), amber-tinted for sự kiện (market, contemporary — amber #E8A33D). This becomes the visual language that distinguishes the two registers throughout, replacing today's near-invisible `cat-event` vs `cat-festival` gradient tint difference.

## 3. Layout + rhythm

Single merged page, in this order:

1. **Hero** (above) — lunar ribbon + time-aware headline.
2. **"Đang diễn ra / sắp diễn ra" ledger** — NOT a generic horizontal scroll-row of cards. A **vertical ceremonial ledger**: each upcoming entry is a full-width row with a large lunar+solar date badge on the left (redesigned, see §7), name, place, and a status word in small caps (ĐANG DIỄN RA / SẮP KHAI MẠC / MÙA TỚI), ordered strictly by nearness in time. This is the "journey timeline" energy from the itinerary page, borrowed here because a calendar of upcoming ritual time deserves the same narrative weight as a travel route.
3. **Register toggle** — a large, tactile two-way switch (not small filter chips): "🎋 Lễ hội truyền thống" | "🎪 Sự kiện & hội chợ" — styled as two adjoining tabs with the leaf/amber hue-shift from the hero, `aria-pressed`, syncs to `?loai=`. This replaces the current soft cross-link ("Tìm lễ hội truyền thống? Xem trang Lễ hội →") which under-sells the second register.
4. **Editorial core** (le-hoi.vue's strongest asset, kept and *elevated*, applied to whichever register is active) — three short essay blocks with pull-quote treatment on the strongest lines ("Ok Om Bok... đua ghe ngo trên sông Maspéro" deserves a full-width serif pull-quote, not paragraph body text buried in prose).
5. **Region quick-picks** — kept, but re-skinned as a **map-shaped chip cluster** rather than a row of pill buttons: three soft blob shapes positioned roughly per real geography (Vĩnh Long inland / Bến Tre coastal-east / Trà Vinh coastal-south), each showing count. Cheap CSS `border-radius` blob shapes, no real map tiles needed — just enough geographic gesture to feel grounded rather than generic.
6. **Interstitial fact band** — kept (already good), but content-branch per register.
7. **Divider → full browse** (search + status/area chips + list/calendar view toggle) — this is the "catalog" tier and should stay utilitarian; do not over-cinema-tize the working tool. But EntityCard/event-row itself gets the keystone redesign below (§11).
8. **Calendar view** — keep, but layer the **lunar-day sub-label already present** (`cal-lunar`) more prominently; this is a genuinely distinctive feature (nobody else's tourism calendar shows âm lịch) and is currently a tiny 10px afterthought under the day number.
9. **Cross-links** — kept.

Responsive posture: on mobile, the ledger (step 2) becomes the single most important element — collapse the hero stat-chip clutter entirely on small screens in favor of the lunar ribbon + one live/next banner, so a phone user sees "what's happening now" within one thumb-flick, not a wall of stat numbers.

## 4. Typography

- Display: `var(--font-editorial)` (Fraunces) for h1 and the pull-quotes — festivals deserve serif ceremony, not the sans-serif catalog voice.
- The **date badge numerals** (edb-day) get a small typographic upgrade: switch the day number to Fraunces at a large fluid size with old-style figure treatment if available, echoing carved temple-stone numerals rather than a generic UI badge digit. Month abbreviation stays small-caps sans for contrast (display/utility pairing inside one badge).
- Lunar date labels (`event-lunar`, `cal-lunar`) — currently italic sans. Upgrade to a **slightly warmer, smaller serif italic** (still `--font-editorial` at `--text-2xs`), consistently applied everywhere a lunar date appears (hero ribbon, ledger, list rows, calendar cells) so "lunar" reads as one deliberate typographic voice across the whole page, not a scattered italic afterthought.
- Status words (ĐANG DIỄN RA / SẮP KHAI MẠC) — wide-tracked small caps sans, matching the dateline-eyebrow pattern, not the current pill-badge treatment which reads like a generic SaaS status chip.

## 5. Sensory + motion + curiosity

- **Lunar ribbon micro-interaction**: hovering (desktop) / tapping (mobile) a tick on the ribbon reveals a small tooltip card with the festival name + one-line hook, before the user commits to scrolling further — an information-scent device specific to this page.
- **Ceremonial pulse, restrained**: the existing `lehoi-status-pulse` keyframe (box-shadow breathing on "đang diễn ra") is good and should be the ONLY ambient animation on the page — kept exactly, respecting `prefers-reduced-motion`. Resist the urge to add more; the current audit-supplied warning about over-animation reading as AI-slop is well-heeded by le-hoi.vue already — extend this restraint, don't multiply it.
- **Scroll-reveal**: sections reveal via the existing `useReveal()` composable — keep as-is, no new motion library.
- **Sound/water gestures through design, not literal media**: the phù-sa vertical tick (river→amber→clay) on section heads already evokes the water-to-land gradient; extend it as the divider between "Lễ hội" register content and "Sự kiện" register content when the toggle switches, so switching registers is itself a small ritual (the tick color washes from leaf to amber over ~250ms) — a discovery device that rewards playing with the toggle.
- **Calendar-cell hover**: cells with events get a subtle lift + the lunar sub-label brightens on hover, inviting exploration of "what else is this month" — turns the calendar from a static grid into a thing worth panning through.
- **Curiosity device**: the "off-season note" (`lehoi-offseason`, currently only in le-hoi.vue: "Lễ hội sẽ trở lại mùa sau") is a genuinely nice touch — extend it into a **"mùa lễ hội" mini-preview**: instead of just an apology text, show a compact preview strip of the next 2-3 festivals by season name ("Mùa Ok Om Bok — tháng 10 âm lịch còn tới"), so even an off-season visit still whets appetite rather than dead-ending.

## 6. UX flow

Information scent path: **hero (what's the calendar telling me right now) → ledger (concrete near-term things I could actually go to) → register toggle (do I want ancestral or contemporary) → editorial (why this matters / how to behave respectfully) → quick-picks (narrow by my region) → full browse (search/filter for a specific thing) → calendar (plan around dates) → cross-links (where to go next: itinerary, map, du-lich)**.

Reduce friction to the two real actions on this page:
1. **Explore** an entry → tap through to entity page (`entityPath`). Every row/card is the full tap target already — keep.
2. **Save/remember** → the `.ics` calendar download button is the standout existing feature (undersold — currently a tiny 📅 icon that only appears on hover, invisible on first pass, and mobile has no hover state at all). **Fix**: make the ical button always-visible on mobile (no hover-gate), and add a **one-tap "Thêm tất cả lễ hội sắp tới vào lịch"** bulk action near the ledger — batch-subscribe to an .ics feed of upcoming festivals. This is the single highest-leverage UX fix in this unit: it converts passive browsing into a concrete calendar commitment, which is the realistic "conversion" for a contact-only, no-booking site.
3. Contact-only CTA: entries with a manager/organizer contact (rare for festivals, more likely for OCOP hội chợ) route to the entity page's existing Zalo/phone CTA — no CTA changes needed on the catalog page itself.

## 7. Premium cues

- Date badges with the carved-numeral serif treatment (§4) instead of a generic rounded-rect UI chip.
- Lunar labels consistently placed and typographically distinct everywhere (not just italicized inline text).
- The moon-phase ribbon rendered as clean minimal SVG geometry (a handful of arcs), not a borrowed icon font — signals bespoke craft.
- Micro-copy precision: "còn 2 ngày" / "còn 6 giờ" countdown granularity on the live/next banner (compute from `date_start_iso`), rather than a static date string — small detail, disproportionate trust signal ("this site is actually current").
- Consistent hue-coding (leaf = ancestral, amber = contemporary) applied without exception across badge, ribbon tick, toggle tab, and divider — visual systems consistency is itself a premium tell.

## 8. Cultural authenticity

- Keep and *foreground* (don't bury in prose) le-hoi.vue's existing specificity: Lễ Kỳ Yên (đình, đầu năm âm lịch, cầu mưa thuận gió hoà), Ok Om Bok (Khmer Trà Vinh, rằm tháng 10 âm lịch, đua ghe ngo sông Maspéro), Lễ Nghinh Ông (ven biển, cá Ông = thần bảo hộ ngư dân), giỗ Thủ khoa Bùi Hữu Nghĩa, giỗ Phan Thanh Giản, Hội trái cây ngon, Lễ hội bánh dân gian Nam Bộ. Promote the strongest 1-2 sentences of each into pull-quote treatment rather than dense paragraph.
- The lunar-first hero device (§2) is itself the biggest cultural-authenticity move: most Vietnamese tourism sites treat lễ hội as "an event with a date" — showing the âm lịch as the *primary* clock, with Gregorian as secondary, is a specific and correct framing of how these festivals are actually reckoned.
- Etiquette block ("Đi lễ hội — cần biết gì?" — bỏ giày dép ở chùa Khmer, tránh chạm đầu người khác, trang phục lịch sự ở chánh điện) is excellent and rare among competitor sites — keep verbatim, but give it a distinct visual treatment (a bordered "cần biết" aside box) so it doesn't read as just another paragraph; travelers actually reference this before/during a visit.
- Explicitly separate-but-adjacent Kinh/Khmer/Hoa registers in the quick-picks or editorial structure (e.g., a small "ba dòng lễ hội" — three-strand mini-legend: đình Kinh / chùa Khmer / hội quán Hoa) makes the tri-ethnic framing visible at a glance, not just discoverable by reading the essay.
- Avoid generic tourism-clichés: no "lễ hội rực rỡ sắc màu" boilerplate; keep the specific, slightly restrained tone le-hoi.vue already uses ("sợi dây kết nối cộng đồng qua nhiều thế hệ" is a good line — more like that, nothing generic).

## 9. Copy voice

Editorial, warm, precise — never touristic hype. Dateline/eyebrow register is clipped and factual; body prose is measured, specific, slightly literary; etiquette copy is plain and practical.

Example lines (Vietnamese):

- Hero dek: **"Ba tỉnh, ba cách đếm ngày lễ — Kinh theo đình làng, Khmer theo trăng tròn, Hoa theo phường hội. Xem lịch nào sắp tới."**
- Live-now banner: **"Đang diễn ra: Ok Om Bok, Trà Vinh — ghe ngo đang xuống nước trên sông Maspéro."** (concrete sensory detail instead of "sự kiện đang diễn ra")
- Off-season teaser: **"Mùa lễ hội sẽ quay lại — Cúng Trăng còn đợi tới rằm tháng Mười."**
- Pull-quote treatment for existing line: **"Từ đình miếu Kinh ven sông đến chùa Khmer tháp nhọn, từ hội quán Hoa rực đèn lồng đến giỗ kỵ danh nhân — lễ hội ở đây là sợi dây nối cộng đồng qua nhiều thế hệ."**
- ical bulk-action microcopy: **"Thêm cả mùa lễ hội vào lịch của bạn — một chạm, khỏi quên ngày nào."**

## 10. Signature moment

**The lunar ribbon in the hero** — a thin, quiet strip that shows the moon's actual current phase and ticks off the next festivals by their position in the lunar month, with a live "đang diễn ra" banner that supersedes it when something is happening right now. It is the one thing on this page that could not be copy-pasted from a generic "events" template: it visibly proves the page's central claim (this calendar runs on the moon, not the marketing quarter) in a single glance, and it's the thing a visitor would screenshot or describe to a friend ("this site literally shows you what phase the moon's in and which festival that means").

## 11. Components + feasibility

Concrete, CSS-tokens only, AI-gen images only (none required for this build — this unit is copy/layout/motion-driven, no new photography needed), contact-only CTA unaffected, dark parity + reduced-motion required on every new element.

**New components (this unit):**
- `LunarRibbon.vue` — SVG crescent (pure geometry, `currentColor`/CSS var fill, ~8 lines of path data for 4-5 phase states) + tick marks computed from upcoming festival lunar dates via the existing `useLunar` composable (`lunarLabel`, `isLunarFirstDay`, `isLunarFull` already exist — reuse, don't reinvent). Reusable on: homepage (small version, "lễ hội tháng này"), entity detail pages for festival-type entities.
- `EventLedgerRow.vue` — the vertical ceremonial ledger row (date badge + name + status + place), refactor of the current `.event-row` markup into a named component so su-kien/le-hoi (and future homepage widgets) share one implementation instead of duplicated template blocks — directly fixes the ~90% duplication problem named in the brief.
- `RegisterToggle.vue` — the leaf/amber two-tab switch, syncs to `?loai=`, reusable pattern for any future "two lenses on one dataset" page.
- `IcalBulkButton.vue` — "add all upcoming to calendar," generates a combined `.ics` VCALENDAR client-side from the already-fetched `allEvents` list (no backend change needed — same data, multiple VEVENT blocks concatenated).

**CSS-only changes:**
- Numeral treatment on `.edb-day` → `font-family: var(--font-editorial)`, tabular/old-style figures if available.
- `.event-lunar`/`.cal-lunar` → unify to one `.lunar-label` utility class, serif italic, `--text-2xs`, consistent color token (e.g., `var(--leaf)` if a leaf accent token exists, else `var(--secondary)`).
- Hue-shift hero scrim per register — two CSS custom-property sets swapped via a class toggle (`.register-le-hoi` / `.register-su-kien`) driven by `RegisterToggle`, transitioning `background` over `.25s` (respect reduced-motion → instant swap, no transition).
- Etiquette aside → bordered callout box (`border-left: 3px solid var(--accent)`, `background: var(--surface)`), reusing the existing `.lehoi-offseason` visual pattern already in the codebase (same border-left recipe, different content).
- Blob-shaped region quick-picks → `border-radius` irregular values per region chip (cheap, no image assets).

**Backend/data — none required.** Everything above reads existing `/api/events` fields (`attributes.category`/`category_array`, `date_start_iso`, `lunar_date`, `place_name`). The register split already exists as a client-side filter (`category !== 'le-hoi'` vs `.includes('le-hoi')`) — merging the pages means keeping both filters and switching which is "active," not new data plumbing.

**Migration note if pages must stay physically separate** (e.g., SEO wants two indexable URLs): keep `/su-kien` and `/le-hoi` as distinct routes for canonical/SEO purposes, but extract `LunarRibbon`, `EventLedgerRow`, `IcalBulkButton` as shared components so the *visual and interaction* unification happens even if the URL split remains — this captures ~80% of the benefit without an information-architecture decision that's outside this unit's scope (flag for roadmap: "merge or formally split su-kien/le-hoi" — a product decision, not a design one).

**Reusable across the rest of the site:**
- `LunarRibbon` (small variant) → homepage "this month" widget, festival-type entity detail pages.
- `EventLedgerRow` → homepage "sắp diễn ra" teaser, itinerary page if it ever surfaces dated events.
- The leaf/amber ancestral-vs-contemporary hue convention → could extend to how OCOP (contemporary/commerce) vs di-tich/temple (ancestral) entity types are color-coded sitewide, if that convention doesn't already exist.
