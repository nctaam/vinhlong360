# Itineraries — Lịch trình

**Pages covered:** `lich-trinh/index.vue` (list, grade 6.0) · `lich-trinh/[id].vue` (detail, grade 7.0 — current best "journey" moment on the site) · `lich-trinh-chia-se/[id].vue` (shared plan, grade 3.0 — weakest page on the site)

**Thesis for this unit:** *A trip is a story with a shape.* An itinerary is not a checklist of stops with times attached — it is a **day unfolding**: morning light on the river, the heat of midday under a vườn canopy, the specific hush of a Khmer chùa at dusk. The list page should feel like a shelf of possible mornings-to-come; the detail page should read like a day already lived, waiting for you to step into it; and the shared-plan page — right now an unstyled orphan — is a stranger's postcard and must be dressed to represent the whole platform in a single, unbranded-feeling glance.

---

## 1. Story angle

Three different narrative distances, one throughline:

- **`lich-trinh/index.vue` (the shelf):** this is not "our itinerary database," it's **"những ngày đã được sắp sẵn cho bạn."** Frame each itinerary as a *day-shape* — a small silhouette of a day (morning→noon→evening) rather than a database row. The organizing metaphor: a shelf of **trip cards like postcards already written**, grouped by the rhythm of the day (short/half-day, full-day, multi-day) as much as by region.
- **`lich-trinh/[id].vue` (the day itself):** this is the site's one true "journey" artifact — a **timeline is a day happening**. Story angle: treat time-of-day as the hero variable. 6:00 chợ nổi sương sớm → 9:00 miệt vườn nắng lên → 12:00 cơm trưa dưới bóng dừa → 15:00 làng nghề → 17:30 hoàng hôn sông. The stop list becomes a **day arc**, not a bullet list — sun position, light quality, and pacing should be legible from the design itself, not just the `time` field text.
- **`lich-trinh-chia-se/[id].vue` (the postcard from a friend):** narrative distance changes completely — this is **received, not browsed**. A stranger clicked a Zalo link. Frame it as "ai đó vừa gửi bạn một ngày ở miền Tây" — warm, personal, low-friction, and unmistakably vinhlong360 (right now it could be any generic itinerary app; it must instead feel like *opening a gift someone wrapped for you*).

## 2. Cinematic hero / thesis

**List page:** Replace the flat `catalog-hero cat-itinerary` (emoji + h1 + stat pills) with a **"day-arc" cinematic band**: a thin horizontal gradient strip (river-dawn → sand-noon → clay-dusk, using existing tokens) sitting directly under the masthead, annotated with tiny sun/moon glyphs at 4 time marks (sáng sớm / trưa / chiều / hoàng hôn). This single graphic *is* the thesis — "chọn một hình dạng ngày phù hợp với bạn" — and doubles as a filter affordance later (see §6). Masthead: serif `Chọn một ngày ở miền Tây` (not "Lịch trình") as the display line, with "Tuyến tham quan có sẵn — chỉ cần chọn và đi" as the sans dek underneath, matching the CE eyebrow/dateline pattern used elsewhere.

**Detail page:** Keep and elevate the existing `catalog-hero` into a true CE cinematic hero: full-width photo band (area hero photo — Vĩnh Long/Bến Tre/Trà Vinh already exist as `/img/area-*.webp`) with `cine-title` serif headline set over a scrim, and — the signature new device — a **horizontal sun-arc progress rail** spanning the width of the hero bottom edge, plotting every stop as a dot positioned by its `time` value along a dawn→dusk gradient (reusing the day-arc strip from the list page, now populated with this itinerary's real stops). This rail is the "thesis visual": before you've read a single stop, you see the *shape* of the day — front-loaded morning, siesta gap at noon, golden-hour finish.

**Shared-plan page:** Currently has no hero at all — a bare `<h1>` in a boxed card. New thesis: a **compact cinematic strip** (shorter than the full catalog-hero, ~30vh) using the same area photo band + scrim, with a hand-off microcopy line as the emotional hook: *"{Tên người gửi} vừa chia sẻ một ngày ở miền Tây"* (fallback if no author: *"Một ngày ở miền Tây, đã được sắp sẵn"*). This single line does more brand work than anything currently on the page.

## 3. Layout + rhythm

**List page** — restructure section order to read as a narrative, not a filing cabinet:
1. Masthead + day-arc strip (hero)
2. Saved (unchanged position — logical for returning users)
3. **NEW: "Chọn theo nhịp ngày" (pace picker)** — Nửa ngày / Trọn ngày / Nhiều ngày chips, sitting *before* the region picker, because "how much time do you have" is a more human first question than "which province." Region picker follows immediately after as the second filter axis.
4. Editorial paragraph (kept, tightened)
5. Interstitial (kept)
6. Grid — but reorganized as **grouped shelves by pace** (Nửa ngày / Trọn ngày / Nhiều ngày sub-headers with their own small serif kicker) rather than one flat grid, so scanning feels like browsing "shelves of days" rather than a database table.
7. Cross-links (kept)

**Detail page** — the timeline is already the strongest artifact on the site; add rhythm rather than restructure:
1. Hero with sun-arc rail
2. Lead + actions (kept)
3. Transport mode panel (kept, visually quieted — it's utility chrome, shouldn't compete with the story)
4. **Timeline, now chaptered by time-of-day** — insert quiet section dividers (not full section breaks, just a hairline + small serif label: "Buổi sáng" / "Buổi trưa" / "Buổi chiều") when stops cross a time boundary (before 11:00 / 11:00–14:00 / after 14:00). This turns one long list into 2-3 legible "chapters of the day" — classic editorial pacing device, cheap to compute from existing `stop.time` strings.
5. Route map (kept — this is good; maybe promoted slightly earlier for wayfinding-minded visitors, tested via scroll-depth if analytics exist)
6. Related itineraries (kept)

**Shared-plan page** — currently single-column boxed card. Restructure to match detail-page conventions so it doesn't feel like a foreign template:
1. Compact cinematic strip hero (see §2)
2. Sender line + stop count as `cine-meta` row (reuse detail page's meta pattern)
3. Stops rendered as the **same `.timeline` component style** as the real detail page (numbered dot + spine), not the ad-hoc `.sp-stop` flex row — visual continuity signals "this is the real product," not a stripped export view
4. A clear, singular, warm CTA band at the end: "Thích ngày này? Tạo lịch trình của riêng bạn" — button + one secondary link back to `/lich-trinh`
5. Footer trust cue: small line "Từ vinhlong360.vn — lịch trình do cộng đồng chia sẻ" so the brand register is unambiguous even shared out of context via Zalo

**Responsive:** day-arc strip and sun-arc rail both collapse to a simple horizontal gradient bar with dots at mobile widths (no label text overlap — labels move to a legend row below). Timeline chapters collapse gracefully — chapter labels just become smaller sticky mini-headers on scroll (reuse `.chapter-sticky` from editorial.css).

## 4. Typography

- Serif `Fraunces` (`--font-editorial`) for: list-page masthead, detail-page `cine-title`, shared-plan hero line, and the new time-of-day chapter labels (small serif caps, not sans — this is what marks them as "editorial chapter," distinct from the UI chrome around them).
- Sans (`Inter`) stays for all UI chrome: chips, buttons, badges, meta rows, stop names in the timeline (these are proper nouns / entity names — sans is more legible at small sizes for scanning).
- New scale use: time-of-day chapter labels at `--text-2xs`, uppercase, `--tracking-caps`, colored `var(--muted)` — quiet enough not to compete with stop names, present enough to give rhythm.
- Shared-plan page currently uses raw hex-ish ad-hoc sizing (`1.5rem` h1, `.85rem` num) — replace entirely with token scale (`--text-3xl` / `--text-sm` etc.) to bring it into system compliance; this alone fixes half of its "undressed" feeling.

## 5. Sensory + motion + curiosity

- **Day-arc strip (list) / sun-arc rail (detail):** subtle, one-time draw-on animation on first reveal (a thin line drawing left-to-right, ~600ms, `ease-out`) — reinforces "a day unfolding" without being a gimmick. Gated behind `prefers-reduced-motion` (draws instantly, no animation, if reduced).
- **Timeline chapter transitions:** as a chapter's first stop scroll-reveals, its chapter label fades/slides in fractionally earlier than the stop card itself (50ms stagger) — barely perceptible but reinforces "chapter opening" pacing. Reuses existing `useReveal()` — no new JS infra needed.
- **Stop-card hover (existing):** already has emoji rotate + lift — good, keep as-is, don't over-add.
- **Discovery device — "peek the next stop":** on the detail page, add a small affordance at the bottom of each `.step-card` — a thin connector line with a ghost preview of the *next* stop's emoji + name (already partially present via `.route-leg`; extend the route-leg-info line to also whisper the upcoming stop name, e.g. "1.2km · 15 phút → tới Chợ nổi Cái Bè") so the route leg becomes a **narrative bridge**, not just a distance stat.
- **Sensory language, not sensory animation:** avoid adding gratuitous motion (this is exactly the AI-slop trap). Instead lean on *copy* to evoke senses — see §9 — and let the day-arc gradient (dawn cool tones → noon warm sand → dusk clay) do quiet ambient sensory work purely through color, which costs nothing in performance or dark-mode complexity.
- **Print stylesheet (existing `@media print` in detail.css):** keep and extend to shared-plan page — a printed/PDF'd itinerary is a real use case for a Mekong Delta trip (patchy signal); currently only the detail page has it.

## 6. UX flow

- **List page:** entry → day-arc visual sets expectation → pace chips (new primary filter) → region chips (secondary filter) → shelves → pick a card → done. The pace chips directly answer the first real visitor question ("do I have half a day or three days?") before region, which most visitors don't have a strong prior on yet.
- **Detail page:** land → sun-arc rail gives an at-a-glance day-shape in under 2 seconds → scroll into chaptered timeline → transport-mode + route map available but not blocking → save/share/contact-adjacent actions (`SaveButton`, `ShareButton`, report) stay exactly where they are — already well-placed above the fold-ish. **Add:** a small sticky mini progress indicator on scroll (reusing `.chapter-sticky`) showing "Buổi sáng · Buổi trưa · Buổi chiều" as a lightweight scrollspy, so long itineraries (7+ stops) don't feel like endless scroll with no sense of progress.
- **Shared-plan page — the friction to remove:** right now, a stranger clicking a shared link sees a boxed, unbranded card with zero visual continuity to the rest of the site, and the ONLY action is "Tạo lịch trình của bạn" — a cold ask before they've even understood what they're looking at. New flow: cinematic strip establishes context and warmth first → stops rendered in the recognizable timeline style (so it *reads* as "this is vinhlong360, a real thing," building trust) → THEN the CTA, now warmer ("Thích ngày này? Tạo lịch trình của riêng bạn") → secondary softer link to browse existing itineraries (lower-commitment alternative for someone not ready to build their own). Also: entity links inside stops (`s.id` → `entityPath`) should get small type badges (matching detail-page stop cards) so a curious stranger can click through to explore individual places — right now they're bare text links with no visual invitation.
- **Contact-only CTA discipline:** none of these three pages should ever gain a booking/checkout affordance — "Tạo lịch trình" / "Xem lịch trình gợi ý" / entity exploration are the only funnel destinations, consistent with platform CTA policy.

## 7. Premium cues

- Sun-arc rail with real per-stop time positioning (not decorative — actually computed from `stop.time`) signals genuine craft, not template filler.
- Chaptering the timeline by time-of-day costs nothing extra to build (data already has `stop.time`) but reads as thoughtful editorial curation rather than raw list dump.
- Route-leg narrative bridge ("1.2km · 15 phút → tới Chợ nổi Cái Bè") is a small, cheap detail that most competitor itinerary tools skip — GetYourGuide/Klook show distance/time but never narrate the handoff.
- Shared-plan page matching the real product's visual language (not a stripped-down export template) is itself a premium/trust cue — it tells a first-time visitor "this whole platform looks like this," which is exactly the moment that matters most for acquisition.
- Print stylesheet parity across all three pages (currently only on detail) — a small, quiet, "we thought of everything" touch for an area with patchy mobile signal.

## 8. Cultural authenticity

- Time-of-day framing (sáng sớm chợ nổi / trưa miệt vườn / chiều làng nghề / hoàng hôn sông) is drawn directly from real Mekong Delta trip rhythms — chợ nổi Cái Bè/Cái Răng genuinely operate at dawn and thin out by 9-10am; this is not generic tourism-copy, it's how these places actually behave, and structuring the page around it teaches the visitor something true and useful (when to actually go).
- Avoid the generic "digital nomad itinerary app" register (icons of suitcases, generic checkmark timelines, world-map globe imagery) — the day-arc gradient uses the established tri-province palette (river/leaf/amber/clay) rather than generic blue/teal travel-app gradients.
- Where itineraries cross Khmer cultural sites (chùa Khmer, lễ hội), the type badge and copy should keep respectful specific language (không gọi chung "temple," dùng "chùa Khmer" khi đúng loại) — this is a content-team concern more than layout, but the chaptered timeline design should have room for a respectful note/etiquette microcopy line (already supported via `stop.note` field — surface it more visually, e.g. small amber-tinted callout style, rather than plain gray text as now).
- Shared-plan hand-off copy ("ai đó vừa gửi bạn một ngày ở miền Tây") leans into the very real social behavior in Vietnam of sharing trip plans via Zalo among family/friend groups — this is the actual distribution channel for this page, design should honor that context rather than presenting a generic "shared itinerary" SaaS-template feel.

## 9. Copy voice

Editorial, warm, second-person-implicit (không xưng "bạn" dồn dập, để giọng văn tự nhiên như người quen kể lại), sensory-specific rather than promotional-generic.

- **List page masthead dek (replacing current "Tuyến tham quan Vĩnh Long, Bến Tre, Trà Vinh được thiết kế sẵn — chỉ cần chọn và đi."):**
  > "Có ngày chỉ cần nửa buổi ở miệt vườn, có ngày cần trọn ba hôm để đi hết một khúc sông. Chọn nhịp ngày phù hợp — phần còn lại, tụi mình đã sắp sẵn."

- **Detail page — pace/chapter framing example (as a quiet caption near the sun-arc rail):**
  > "6 giờ sương còn giăng mặt sông, 5 giờ chiều nắng đã ngả màu mật ong trên mái nhà — đây là hình dạng một ngày trọn vẹn ở {area_name}."

- **Shared-plan hand-off line:**
  > "{Tên người gửi} vừa gửi bạn một ngày ở miền Tây — mở ra xem, rồi tự sắp một ngày của riêng mình."

## 10. Signature moment

**The sun-arc rail / day-arc strip** — a single quiet horizontal gradient device (dawn-cool → noon-sand → dusk-clay) that appears at three altitudes (filter affordance on the list page, populated hero rail on the detail page, ambient hero mood on the shared-plan page) and literally **shows the shape of a day** before a single word is read. It is cheap to build (SVG/CSS gradient + positioned dot markers, no new JS dependency beyond existing scroll-reveal), reusable across all three pages, and is the one thing a visitor will remember: *"trang này cho tôi thấy hình dạng cả một ngày chỉ bằng một cái liếc mắt."*

## 11. Components + feasibility

**New components (reusable across all three pages):**
- `DayArcRail.vue` — props: `stops: {time, name}[]`, `mode: 'strip' | 'hero' | 'ambient'`. Renders an SVG/CSS gradient bar (dawn/noon/dusk tri-color, tokens: `--river-100`→`--amber-100`→`--clay-100` light backdrop with `--river-600`/`--amber-500`/`--clay-600` accent dots) with positioned dot markers computed from parsed `time` strings (fallback: even distribution if no times present). `mode="strip"` = list-page filter-adjacent decoration (no stops, just 4 fixed time-of-day markers with labels). `mode="hero"` = detail-page populated rail with real stop dots + tooltips. `mode="ambient"` = shared-plan compact decorative-only strip (no dots, just mood gradient behind the cinematic hero band).
- `PaceChips.vue` — Nửa ngày / Trọn ngày / Nhiều ngày filter chips, computed client-side from `itinerary.duration` string heuristics (or a new lightweight `pace` field if backend can add one — additive, non-breaking per B2).
- `TimelineChapter.vue` (or just a CSS/logic addition inside `[id].vue` and reused in `lich-trinh-chia-se/[id].vue`) — groups stops into Buổi sáng/trưa/chiều based on parsed `time`, renders a small serif chapter label + hairline divider before the first stop of each group, reusing the existing `.chapter-sticky` CSS from `editorial.css`.

**CSS additions (all token-based, dark-parity + reduced-motion required):**
- `.day-arc` family in a shared file (`editorial.css` or a new small `itinerary.css` route-scoped file) — gradient backdrop, dot markers, label row, mobile collapse rules.
- `.timeline-chapter` label styling — small serif caps, `--text-2xs`, `--tracking-caps`, `var(--muted)`, hairline divider using the same river→amber→clay "sediment" tick recipe already established in `xa-phuong/[id].vue` (`.ce-ward .wp-sec h2::before`: 4px wide, `border-radius: var(--radius-full)`, gradient background) — reuse that exact recipe for visual-language consistency across the site's CE-ified pages.
- Shared-plan page: replace ad-hoc hex/rem styling with token classes; reuse `.timeline`/`.step`/`.step-card` classes from `detail.css` instead of inventing `.sp-stop`/`.sp-num` — this is the single highest-leverage fix (near-zero new CSS, just swap markup to reuse existing, already-dark-mode-safe classes).
- Route-leg narrative bridge: extend existing `.route-leg-info` template string to interpolate next stop name (data already available client-side via `stopsWithCoords`).

**Feasibility notes:**
- Zero new paid services. Zero new JS dependencies (SVG/CSS + existing `useReveal`/`useRouting` composables suffice).
- All new visuals must render meaningfully with **zero real photos** — `DayArcRail` is pure gradient/CSS, doesn't depend on the ~60/1730 entities that have real imagery, so it works everywhere immediately (important given the imagery ceiling constraint).
- Dark-mode: gradient dot backdrop needs a `.dark` override tuned down in saturation (mirror the existing `.dark .catalog-hero .stat-item` pattern already in `lich-trinh/index.vue`'s scoped style block).
- Reduced-motion: rail draw-on animation and chapter stagger both must have a `@media (prefers-reduced-motion: reduce)` bailout (render final-state instantly), following the existing convention seen throughout `detail.css`'s scoped style block in `[id].vue`.
- Print: extend the existing `@media print` block (currently only in `[id].vue`) to also apply to `lich-trinh-chia-se/[id].vue` once its markup is unified with the timeline classes — near-free once the component reuse happens.
- Biggest ROI-to-effort win on the whole unit: **rewriting `lich-trinh-chia-se/[id].vue` to reuse the detail page's hero + timeline classes** rather than its own bespoke (and currently token-non-compliant) markup — this single change would likely move that page from 3.0 to competitive with the 7.0 detail page with the least net-new design work of anything in this concept.
