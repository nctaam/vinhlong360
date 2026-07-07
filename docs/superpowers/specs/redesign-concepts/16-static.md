# Static / Info / Brand — Deep Redesign Concept

> **STATUS (2026-07-07): concept Ý TƯỞNG — KHÔNG thực thi nguyên văn.** Viết TRƯỚC declutter 3 đợt (ship 2026-07-07) và TRƯỚC chốt định vị 2026-07-06. Khi xung đột: code hiện tại + CLAUDE.md thắng. Trước khi thực thi bất kỳ mục nào: (1) dẹp mọi copy "miền Tây / ba tỉnh" — dùng khung tỉnh-Vĩnh-Long-mới; (2) KHÔNG dùng địa danh ngoài tỉnh (Cái Bè, Lai Vung… thuộc Đồng Tháp); (3) KHÔNG claim "đã xác minh"/quy mô đội ngũ; (4) re-ground line-number trên code hiện tại. Cảnh báo đầy đủ: 00-narrative-system.md. **LƯU Ý RIÊNG:** KHÔNG làm strip "đội ngũ 2 người" (§5 :51 — solo dev, byline cấp tổ chức); band 3-glyph §10 đã bị declutter T8 thay bằng sediment-divider; masthead "Miền Tây không thiếu chỗ để đi" (:122) là filler CẤM.


**Pages covered:** `gioi-thieu.vue` (Giới thiệu, 5.5) · `lien-he.vue` (Liên hệ, 7.0) · `huong-dan.vue` (Hướng dẫn sử dụng, 6.5) · `huong-dan-thanh-vien.vue` (Hướng dẫn thành viên, 6.0) · `chinh-sach-bao-mat.vue` (Chính sách bảo mật) · `dieu-khoan-su-dung.vue` (Điều khoản sử dụng, 5.5) · `error.vue` (404/500, 5.0)

**Framing:** these seven pages are currently treated as *utility* — the parts of the site nobody is supposed to look at for long. That is the bug. On every credible brand, the About page and the error page are two of the most disproportionately-visited, most disproportionately-quoted pages on the whole domain. They are where a stranger decides "do I trust these people." Right now vinhlong360 answers that question with a `.legal-page` wrapper, a lorem-ipsum-shaped `catalog-hero`, and a 🌾 emoji. This concept turns all seven into one coherent **brand register** — the calmest, most confident, most human voice on the site — sitting one layer *above* the cinematic-editorial (CE) entity pages, because these pages are not selling a place, they're introducing the people behind the lens.

---

## 1. STORY ANGLE

Every static page currently answers "what is this" (a definition). It should answer "who are we to you, right now" (a relationship). Reframe each page as a **moment in an ongoing relationship** with the visitor:

- **Giới thiệu** = the origin story. Not "vinhlong360.vn là một dự án..." (a Wikipedia sentence) but *why one person sat down and started cataloguing 1,700+ places in a province most of Vietnam can't find on a map*. The story angle: **"Miền Tây không thiếu nơi để đi. Nó thiếu người kể cho bạn nghe vì sao nên đi."** — the platform exists because the region's stories were scattered across gov PDFs, Zalo groups, and old newspaper clippings, and someone decided to gather them into one place, honestly, without selling bookings.
- **Liên hệ** = the story of *being heard*. Not a form graveyard — a page that says "a real small team reads this," with visible response-time promises and a face (even if stylised) behind the inbox.
- **Hướng dẫn sử dụng** = the story of *becoming a local*. Frame as a "cẩm nang" (field companion) a savvy local would hand a first-time visitor, not a software manual. Quickstart = "5 bước để đi như dân miền Tây thứ thiệt."
- **Hướng dẫn thành viên** = the story of *earning your place* in a community — gamified status reframed as a rite of passage (người mới → người quen → người có tiếng → đại sứ vùng), like the real social ladder of a Mekong Delta village where trust is earned by showing up.
- **Chính sách bảo mật / Điều khoản** = the story of *a promise in writing*. Legal pages are where trust goes to die on most Vietnamese sites (walls of Nghị định citations). Reframe: this is the one place the platform is *maximally plain-spoken* — "đây là những gì chúng tôi hứa, viết bằng tiếng Việt bình thường, không phải để né trách nhiệm mà để bạn hiểu thật."
- **404/500 (error.vue)** = the story of *a wrong turn on a real road*. Not "page not found" — a gentle, characterful "bạn đi lạc một khúc rồi" moment that still gets you home, styled after getting mildly, charmingly lost on a cù lao backroad — always ends with an actual invitation back into the site, never a dead end.

The unifying thread across all seven: **"vinhlong360 is made by people, for people, about a real place."** Every one of these pages should individually reinforce that this is not a scraped directory — it's curated, cared for, and accountable.

---

## 2. CINEMATIC HERO / THESIS

Currently every legal/static page reuses the generic `.catalog-hero` band (icon + h1 + p, institutional gradient) — visually indistinguishable from a catalog listing page. That's the core problem: **brand pages must not look like catalog pages.**

**New pattern — the "Masthead Strip":** a full-bleed but short (32–40vh) editorial band unique to this page-family, built entirely in CSS (no new photography needed):

- Background: the existing `--grain` SVG texture over a **duotone river→clay gradient wash** (`linear-gradient(120deg, var(--river-600) 0%, var(--sand-100) 55%, var(--clay-600) 120%)` at low opacity over `--bg`), evoking phù sa water meeting clay bank — the *only* place on the site this specific gradient appears, making it instantly recognizable as "you are in the brand zone."
- A **hairline dateline eyebrow** exactly like the homepage masthead (`· VỀ VINHLONG360 ·` / `· LIÊN HỆ ·` / `· CẨM NANG ·`), wide-tracked caps, small tick-mark before it.
- **Oversized serif headline** in `--font-editorial` (Fraunces), same scale discipline as the homepage h1 (`clamp(2.2rem, ..., 4.2rem)` — slightly smaller than homepage since this is a sub-brand moment, not the masthead).
- One-line serif sub-dek, not a meta-description dump.
- A **single hand-drawn-feeling SVG motif per page**, replacing the generic emoji icon: a thin-stroke line-art glyph in `--clay-400`, echoing the illustration language already established in `error.vue`'s SVG face (so the visual system already exists — we're extending it, not inventing it):
  - Giới thiệu → a simple line-art of a **sông nước** (river bend + a small boat silhouette + three dots for the three provinces merging)
  - Liên hệ → a **hand holding a phone**, minimal line strokes (echoes Zalo-first CTA culture)
  - Hướng dẫn → an **open cẩm nang (notebook) with a compass rose**
  - Hướng dẫn thành viên → a **huy hiệu (medal) ribbon**, line art not emoji
  - Legal pages → a **con dấu (stamp) circle**, softened, not corporate
  - 404/500 → keep + extend the existing `error.vue` sleepy-face SVG, but give it a **paper-boat companion drifting**, since it's already the site's best static illustration

This SVG motif becomes the shared "brand seal" — small, consistent, appears again as a watermark at 4% opacity behind the footer CTA on each of these pages, so the pages feel bound together as a set.

---

## 3. LAYOUT + RHYTHM

Currently: `max-width: 760px` centered column, uniform for all seven — actually a reasonable reading measure, KEEP IT for body copy, but break the monotony:

- **Giới thiệu**: convert the flat `.about-section` list into an **asymmetric editorial spread**. Section 1 (Mission) becomes a **pull-quote spread**: giant serif quote mark, quote pulled from the mission line, set in a 2-column grid on desktop (quote left 40%, supporting text right 60%). Sections 2+ return to single column but each gets a **full-bleed background-tint band alternation** (odd sections on `--bg`, even on `--bg-warm`) so scrolling feels like turning a page, not scrolling a wiki.
- **Liên hệ**: keep the strong existing card grid (it already tests well at 7.0) but add a **"real humans" strip** above the cards — 2-3 stylised avatar-initials chips ("Đội ngũ 2 người, trả lời trong 48h") to humanize before the grid of channels.
- **Hướng dẫn / Hướng dẫn thành viên**: keep sidebar TOC (works well, desktop-sticky) but re-skin the quickstart into a **horizontal "field-card" scroller** on mobile (5 numbered cards you swipe through, like a passport-stamp sequence) instead of a vertical `<ol>` — turns "read a manual" into "flip through a small deck."
- **Legal pages**: introduce a **two-column layout on desktop ≥1024px** — sticky mini-TOC left rail (auto-generated from `doc.sections`, reuses the sidebar-nav pattern from huong-dan.vue) + reading column right. This alone fixes the biggest legal-page complaint (no way to jump to the clause you need) while adding zero new content.
- **404/500**: break out of the centered-card box on desktop into a **split scene**: left 55% = the SVG illustration enlarged and given a very slow (18s, reduced-motion-off only) drifting-boat animation across a horizon line; right 45% = the message + search + links, vertically centered. On mobile, stack as today.

Scroll narrative for Giới thiệu specifically (the flagship of this unit): **Masthead → Pull-quote mission → "Vì sao tồn tại" (numbered story, alternating tint) → "Nguyên tắc không thương mại" (trust checklist, existing ✓ styling kept) → a closing full-width band: "Ba vùng đất, một câu chuyện" mini-map or 3-glyph strip (Vĩnh Long/Bến Tre/Trà Vinh) → contact CTA.**

---

## 4. TYPOGRAPHY

- Display: `--font-editorial` (Fraunces) at the same weight/tracking discipline as the homepage (`font-weight:600; letter-spacing:-.02em`) for all h1/masthead headlines across the seven pages — this alone is the single highest-leverage fix, since right now they use plain `--weight-bold` sans, which is why they read as "settings page" not "brand page."
- Pull-quotes (Giới thiệu mission, and a new one on Liên hệ: "Chúng tôi không bán tour. Chúng tôi giới thiệu vùng đất.") set in **Fraunces italic**, oversized (`clamp(1.6rem, 1.3rem+2vw, 2.6rem)`), left-bordered by the sediment tick.
- Section h2 across all seven adopt the **sediment-tick treatment** already proven on `khu-vuc/[area].vue` and `xa-phuong/[id].vue` (`::before` 4px gradient river→amber→clay tick, serif h2) — an easy, consistent, zero-new-CSS-variable extension.
- Body copy stays `--font-sans` (Inter) at `--text-sm`/`--text-base` for legibility and legal precision — editorial serif is for *voice* moments (headlines, quotes, ledes), not dense clause text. This mirrors the "drop-cap lede" pattern already built for `khu-vuc` intros: apply the same **drop-cap first paragraph** treatment to the Giới thiệu intro only (not legal pages — a drop cap on a privacy policy reads tone-deaf).
- Numbers (section badges "01, 02, 03", level badges "Cấp 1–4") switch to `font-variant-numeric: tabular-nums` in the editorial serif's numeral style where Fraunces' oldstyle figures are available — small craft detail, visually distinguishes this content from generic UI.

---

## 5. SENSORY + MOTION + CURIOSITY

Discipline first: these are trust pages, not showcase pages — **motion here must whisper, not perform.** No Ken Burns, no parallax on legal pages (jarring on a privacy policy). Motion budget spent only where it earns curiosity:

- **Giới thiệu masthead**: the SVG river-bend motif has a **single slow ripple** — a subtly animated `stroke-dashoffset` on one wave line, 12s loop, `prefers-reduced-motion` disables entirely (swap to static). This is the *one* animated brand touch — restraint is the premium cue here.
- **Reveal-on-scroll** (existing `useReveal()` infrastructure) applied to alternate-tint sections with a slightly longer stagger (120ms vs the default) so Giới thiệu feels like pages turning, not a checklist populating.
- **Liên hệ card hover**: keep the existing icon rotate/lift (already well-tuned at 7.0) — don't touch, it works.
- **Hướng dẫn field-card scroller**: snap-scroll (`scroll-snap-type: x mandatory`) horizontal cards with a **progress-dot rail** beneath (like a passport stamp counter: ● ● ○ ○ ○) — gives the quickstart a physical, game-like "flip through" feel that invites finishing all 5.
- **Huy hiệu (badges) grid** in huong-dan-thanh-vien: on hover/focus, badge icon does a small **coin-flip micro-rotate** (`rotateY(180deg)` over .4s revealing a "earned by X% of members" rarity micro-copy on the back) — turns a static grid into a small discovery moment without being gimmicky. Respect reduced-motion by just showing rarity as static caption text.
- **404 paper-boat**: the single most memorable motion moment in this unit — a small paper-boat SVG drifts left-to-right very slowly along a horizon line behind the message, using the same `--river-600` water-line motif as the Giới thiệu hero, tying the "lost" page back to the brand's water imagery instead of a generic empty-state illustration.
- **Sensory cues via copy + color, not extra animation**: Giới thiệu intro paragraph can gently name texture — phù sa, miệt vườn — and the section-tint alternation (sand-50/sand-100) itself reads as "sediment settling," reinforcing theme through restraint rather than more motion.

---

## 6. UX FLOW

- **Giới thiệu** exit paths: currently ends cold after the last highlight-badge section. Add a **closing band** with two calm CTAs: "Xem hành trình mẫu" (→ /tao-lich-trinh or a spotlighted itinerary) and "Liên hệ với chúng tôi" (→ /lien-he) — the About page should never dead-end; it should hand off to either exploration or conversation.
- **Liên hệ**: the claim-listing card (business owner path) and the general-contact path are visually equal weight today; keep the existing `card-claim` full-width promotion (correct), but ensure the "Xem thêm" cross-link band appears *before* the fold ends, not as an afterthought — move it up conceptually so users who came from a dead-end elsewhere immediately see they can continue exploring.
- **Hướng dẫn**: sidebar TOC + search already gives strong information scent (7/10 baseline correctly identified) — the missing UX piece is a **"bạn đang ở đâu" breadcrumb-in-sidebar** highlighting the active in-view section (already partially done via `activeId` — verify it's visually obvious, e.g., a left accent bar in `--clay-600` on the active `.snav-link`, not just a color change).
- **Hướng dẫn thành viên**: add a **"Điểm của bạn hiện tại"** inline module for logged-in users pulling their live reputation score into the levels grid (highlight their current tier card with a ring) — turns an abstract reference table into a personalized mirror. For logged-out users, show a calm "Đăng nhập để xem cấp bậc của bạn" prompt instead of nothing.
- **Legal pages**: the #1 UX sin of legal pages is "I can't find the one clause I need." The sticky mini-TOC (see §3) directly fixes this. Add a **"Tóm tắt nhanh" (tl;dr) callout box** at the top of both legal pages — 3-4 bullet plain-language summary before the full legal text (a pattern users trust, e.g., "Chúng tôi không bán dữ liệu của bạn. Bạn có thể xoá tài khoản bất cứ lúc nào. Chúng tôi không đăng nội dung bạn chưa đồng ý.").
- **404/500**: already has strong existing UX (search box + popular-link pills + retry) — the main gap is these live only in a centered card; nothing changes functionally, only the presentation per §3.

---

## 7. PREMIUM CUES

- Hairline dividers (`.5px solid var(--line)`) exactly matching the CE system elsewhere — never a heavy `2px` rule, which reads cheap.
- The **sediment-tick** on every h2 (river→amber→clay gradient) is itself a premium signature *because* it's consistent and restrained — a visitor who's seen it on the homepage or a region page will subconsciously register "same publication" when it reappears here.
- **Tabular-nums + oldstyle figures** in section numbering (§4) — a typographer's detail almost nobody consciously notices, but it separates "designed" from "default."
- Legal pages get a small **"Cập nhật lần cuối: [ngày]" + "Phiên bản trước"** version-history disclosure link (even if just a static note pointing to a changelog) — signals an institution that takes documentation seriously, not a copy-pasted template.
- Contact page: a **discreet response-time badge** ("Thường trả lời trong 24–48 giờ") sitting near the masthead, not buried in card copy — premium services always publish their SLA up front.
- Consistent favicon-style **brand seal SVG watermark** (§2) at ~4% opacity behind footer CTAs on all seven pages — the kind of detail that shows up in a screenshot and signals "somebody designed this as a system," not seven one-off pages.
- Print stylesheet consideration for legal pages (`@media print`): strip masthead gradient, keep only clean type — people genuinely print/export ToS and Privacy pages for compliance reasons; handling this gracefully is an invisible-but-real premium cue for B2G/partner audiences.

---

## 8. CULTURAL AUTHENTICITY

- Giới thiệu SVG motif (river bend + boat, §2) and the water-line horizon motif reused on 404 tie the *brand itself* to sông nước — visually claiming "we are of this water," not just "we write about it."
- Avoid generic tourism-brand clichés: no globe icons, no airplane/luggage iconography, no generic "smiling tourist" imagery anywhere in this unit (these read instantly as template/AI-slop and contradict the contact-only, non-commercial positioning).
- Copy must root abstractions in specific regional texture: "ba vùng đất" should visually/verbally acknowledge Vĩnh Long (miệt vườn, gạch gốm), Bến Tre (xứ dừa), Trà Vinh (chùa Khmer, đông đồng bào Khmer) as three *distinct* textures merging — a closing "Ba vùng, một câu chuyện" band (§3) with three small line-art glyphs (dừa lá, gốm/gạch, chùa Khmer stupa) rather than one homogenized "Mekong Delta generic" graphic.
- The huy hiệu (badge) system in huong-dan-thanh-vien should, where feasible, connect a few badge names/icons to regional cultural markers instead of generic gamification icons (e.g., a "Người kể chuyện miệt vườn" badge for prolific reviewers, alongside the existing generic ones) — small copy-level authenticity, no engineering cost.
- Tone throughout: miền Tây warmth — direct, unpretentious, a little wry, never corporate-legal-cold even on the ToS/Privacy pages. Avoid Northern-formal legalese cadence; keep sentences short and plainly spoken, as already partly achieved in the existing intro copy ("chúng tôi hứa," "bạn hiểu thật").

---

## 9. COPY VOICE

Voice: warm, plain-spoken, quietly confident, first-person-plural ("chúng tôi") but never corporate. Short sentences. No em-dash overuse, no marketing superlatives ("tốt nhất," "hàng đầu"). A trusted local telling you the truth, not a brand pitching you.

**Giới thiệu — masthead sub-dek:**
> "Miền Tây không thiếu chỗ để đi. Cái thiếu là người kể cho bạn nghe vì sao nên ghé."

**Giới thiệu — mission pull-quote:**
> "Chúng tôi không bán tour, không thu hoa hồng đặt phòng. Chúng tôi chỉ làm một việc: giúp bạn tìm ra nơi đáng ghé, và người thật ở đó để bạn liên hệ."

**Liên hệ — masthead sub-dek:**
> "Có gì thắc mắc, cứ nhắn. Chúng tôi vẫn còn đọc từng tin nhắn, không phải chatbot trả lời giùm."

**Hướng dẫn — quickstart intro:**
> "Lần đầu ghé vinhlong360? Năm bước sau, đi như dân miền Tây thứ thiệt — không cần tài khoản cũng dùng được ngay."

**404 message (replacing current generic line):**
> "Bạn quẹo lộn khúc sông rồi. 🌊 Để tụi tôi chèo bạn về lại bờ nhé."

**Legal tl;dr callout (Privacy):**
> "Nói ngắn gọn: chúng tôi không bán dữ liệu của bạn, bạn xoá tài khoản lúc nào cũng được, và mọi thứ bạn đăng vẫn là của bạn."

---

## 10. SIGNATURE MOMENT

**The "Ba vùng, một câu chuyện" closing band on Giới thiệu** — a full-width, quietly animated strip with three hand-drawn line-art glyphs (dừa lá cho Bến Tre · gạch gốm cho Vĩnh Long · chùa Khmer cho Trà Vinh) sitting on the river→clay gradient wash, each glyph brightening subtly on scroll-into-view, captioned by one line each, resolving into the tagline **"Sáp nhập trên bản đồ. Chưa từng sáp nhập trong lòng người."** This is the one moment on the whole static-page unit built to be screenshotted and shared — it visually and verbally answers "why should three provinces + one small team be trusted to tell this story," and it's the only place on the site where the tri-province merger itself becomes the emotional subject rather than a taxonomy footnote.

Runner-up signature: **the paper-boat 404** — turns the site's least-loved page into its most charming, and reuses zero new asset budget (extends the existing SVG illustration already in `error.vue`).

---

## 11. COMPONENTS + FEASIBILITY

All CSS-token-based, no new dependencies, no new photography required (pure SVG/CSS), dark-mode parity and `prefers-reduced-motion` handled explicitly per component.

**New shared components (reusable beyond this unit):**
- `<BrandMasthead>` — replaces `.catalog-hero` specifically for this page family: dateline eyebrow + serif h1 + serif sub-dek + slot for a page-specific inline SVG motif, over the river→clay grain wash. Props: `eyebrow`, `title`, `sub`, default slot for motif SVG. **Reusable** on any future "institutional voice" page (e.g., a future press/partners page).
- `<SedimentTick>` — tiny wrapper/utility class `.sediment-h2` applying the existing river→amber→clay `::before` gradient tick to any h2; currently duplicated inline in `khu-vuc/[area].vue` and `xa-phuong/[id].vue` — promote to a shared class in `base.css` (e.g. `.section-head-sediment h2::before {...}`) so all seven static pages (and future pages) pull one definition. **This is a refactor-and-reuse, not new CSS.**
- `<LegalTocRail>` — sticky left-rail mini-TOC generated from `doc.sections`, reusing the `sidebar-nav`/`snav-link` CSS already built for `huong-dan.vue`. Used by both legal pages; **directly reusable**, since the pattern (active-section highlight via IntersectionObserver, already exists as `activeId` logic in huong-dan.vue) just needs generalizing into a composable `useSectionScrollSpy()`.
- `<FieldCardScroller>` — horizontal snap-scroll card deck with progress-dot rail, for the Hướng dẫn quickstart. Built from existing `.qs-step` cards + CSS `scroll-snap`; no JS framework needed beyond scroll-position → active-dot binding (a few lines, mirrors patterns already in the codebase for carousels if any exist, otherwise trivial vanilla).
- `<TlDrCallout>` — a `.tldr-box` component (bulleted plain-language summary) usable on both legal pages and potentially the AdminCP-authored future policy pages.
- Badge coin-flip: pure CSS `transform-style: preserve-3d` flip card, guarded by `@media (prefers-reduced-motion: reduce)` fallback to static two-line caption (icon + rarity text) — no JS required beyond existing hover/focus states.
- 404 paper-boat: one more `<path>` in the existing `error.vue` inline SVG + a `@keyframes boat-drift` translateX loop, gated behind `prefers-reduced-motion`.

**CSS additions (all token-based, no new hex values beyond what's in `variables.css`):**
- `.brand-masthead` block (gradient wash + grain reuse + eyebrow + h1/sub) — extends existing `--grain`, `--river-600`, `--amber-500`, `--clay-600`, `--font-editorial` tokens only.
- `.tint-alt` section background alternation using existing `--bg` / `--bg-warm`.
- `@media print` block for legal pages (strip masthead, force `--ink`-on-white).

**Feasibility notes:**
- Zero new imagery needed — every visual idea here is CSS gradient + inline SVG line art, consistent with the "images are the ceiling, most entities have none" constraint; these are *brand* pages, not entity pages, so they should never depend on AI-gen photography anyway — reinforces brand-vs-catalog distinction architecturally.
- Zero new JS dependencies; scroll-spy, snap-scroll, and coin-flip are all native CSS/IntersectionObserver patterns already precedented elsewhere in the codebase.
- CTA stays contact-only throughout (mailto/Zalo links only) — no new forms introduced anywhere in this concept.
- Dark mode: gradient wash swaps to the lower-opacity dark variant already patterned in `about-page :deep(.catalog-hero.cat-org)` dark override; sediment-tick already has a documented dark-mode gradient swap to copy.
- Effort tier: About page + 404 are the two highest-value, lowest-effort wins (mostly copy + masthead swap + one new SVG each) — recommend sequencing them first; legal-page TOC rail and Hướng dẫn field-card scroller are next; badge coin-flip is the optional polish pass.
