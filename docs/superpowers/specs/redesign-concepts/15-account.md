# Account + Settings — `tai-khoan.vue` (Trung tâm tài khoản) + `cai-dat.vue` (Cài đặt)

> **STATUS (2026-07-07): concept Ý TƯỞNG — KHÔNG thực thi nguyên văn.** Viết TRƯỚC declutter 3 đợt (ship 2026-07-07) và TRƯỚC chốt định vị 2026-07-06. Khi xung đột: code hiện tại + CLAUDE.md thắng. Trước khi thực thi bất kỳ mục nào: (1) dẹp mọi copy "miền Tây / ba tỉnh" — dùng khung tỉnh-Vĩnh-Long-mới; (2) KHÔNG dùng địa danh ngoài tỉnh (Cái Bè, Lai Vung… thuộc Đồng Tháp); (3) KHÔNG claim "đã xác minh"/quy mô đội ngũ; (4) re-ground line-number trên code hiện tại. Cảnh báo đầy đủ: 00-narrative-system.md.


> Prior grade: 5.0 / 5.0. Diagnosis: deep functionally, flattest visually in the whole product — hardcoded off-brand hex fallbacks (`#c0392b`, `#f5f5f5`, `#dc2626`), zero motion beyond a hover-lift on 6 icon tiles, zero editorial voice, and a reward surface (profile completion, "account score," achievements-adjacent copy like "sẵn sàng / đang tốt / cần hoàn thiện") that computes real signal but presents it as a beige progress bar. This is the one place in the product where a real person sees *their own* name, *their own* number of bài viết, *their own* streak — and the design treats it like a SaaS admin panel.

---

## 1. Story angle

Every other page in this redesign answers "why should a stranger care about this place/dish/product." This unit answers a different question: **"what is my relationship with Vĩnh Long 360 becoming?"** The account is not a settings form — it's the visitor's own **sổ tay hành trình** (travel journal / passport), the ledger of a running relationship with the delta: what they've tasted, saved, written, who they've met in Cộng đồng. Cài đặt, in turn, is not "preferences" — it's **quầy tiếp tân** (the front desk) where you keep the keys to that passport safe.

The narrative arc: `tài khoản` = the passport's open page (what you've done, what's next); `cài đặt` = the passport office (identity, security, who can see it, how to leave). Two rooms in the same house, not two unrelated CRUD screens.

This reframes the existing "profile completion / account score / journey actions" data — which is already computed in the Vue logic — as the emotional payload of the page instead of an administrative checklist.

## 2. Cinematic hero / thesis

**`tai-khoan.vue` hero — "Trang sổ tay" (the passport spread).**
Replace `.cp-hero`'s flat bordered box with a two-page-spread motif: a subtle center crease (a 1px hairline + soft shadow gradient down the vertical middle of the hero, visible only ≥768px) so the avatar + identity sit on the "left leaf" and the score sits on the "right leaf," like an open passport/journal. Background is not flat `--card` white — it's the sand ground (`--sand-50`) with the same fine grain-SVG texture used elsewhere in the CE language, plus a **very faint** watermark: a hand-drawn-style compass rose or the tri-color sediment tick, echoing wayfinding/travel-document iconography without being kitsch (no literal passport-stamp clipart — too on-the-nose/AI-slop).

The avatar gets a **ring-of-progress** treatment: the existing circular `cp-score` (currently a separate beige circle floating on the right) is retired as a standalone element. Instead, the account-completion percentage becomes a thin conic-gradient ring *around the avatar itself* (river → amber → clay, the sediment palette, sweeping clockwise as completion rises) — so the FIRST thing you see is your own face literally wrapped in the tri-province colors, not a disconnected score badge. Below the name: a serif (`--font-editorial`) display of the display name at `--text-2xl`+, not the current small `1.35–1.9rem` sans. The `cp-kicker` "Trung tâm tài khoản" becomes a proper CE dateline eyebrow: wide-tracked caps + hairline-before, matching the area/ward pages exactly (`.area-eyebrow` pattern) — e.g. `HỒ SƠ HÀNH TRÌNH · CẬP NHẬT HÔM NAY`.

**`cai-dat.vue` hero — no hero at all today (jumps straight to `<h1>Cài đặt</h1>` + a grid of beige stat boxes).** Give it a quiet, low-ceremony masthead: small serif h1, one-line dateline ("Quản lý hồ sơ, bảo mật và quyền riêng tư của bạn"), NO large photography (this is a utility room, not a destination — over-cinematizing settings would read as try-hard). The restraint here is intentional and mirrors real premium products (Apple's own Settings app is famously plain next to Photos/Maps). Signature restraint = one hairline + the sediment tick on the h1, nothing more.

## 3. Layout + rhythm

**`tai-khoan.vue`:**
- Hero spread (as above) → `JourneyActionRail` (kept, already good — becomes the page's "turn the page" prompt: "việc nên làm ngay") → **three-panel summary reframed as a single horizontal "trip ledger" strip** instead of three boxy cards: Hồ sơ / Bảo mật / Tiếp theo rendered as three columns separated by hairlines (not borders-as-boxes), echoing a boarding-pass stub layout — perforated-line divider (a repeating-linear-gradient dashed rule, CSS only) between each stub segment.
- Stats (`cp-stats`, 6 flat numbers) become a **horizontal "trail" of tabular-nums stat chips**, each with a tiny serif label and the sediment-tick accent on hover, not a plain grid of 6 identical boxes.
- Workspace tiles (`cp-workspace`, 6 icon cards) keep the grid but gain the CE card treatment: subtle top-edge gradient wash on hover (the same `::before` sediment-wash pattern used on `.wp-card` in xã/phường pages), replacing the generic `transform: translateY(-2px)`.
- Activity feed + "Dữ liệu của bạn" side panel keep their 2-column structure (it works) but the activity feed becomes a **vertical timeline** (thin connecting line + dot per entry, like the itinerary timeline — reuse that exact visual grammar since "activity over time" and "itinerary over time" are the same shape of information) instead of bordered chat-bubble rows.

**`cai-dat.vue`:**
- Keep the tab architecture (it's sound IA — 9 tabs is a lot but the lazy-load-per-tab pattern is correct). Restyle tabs from generic underline-nav to a **quiet vertical rail on desktop** (≥960px: tabs become a left-hand vertical list with icon + label, content panel to the right — like macOS System Settings / a real "back office"), collapsing to the existing horizontal scroller only on mobile. This alone fixes the "admin panel" feel by giving it a recognizable, premium settings-app anatomy instead of a generic top-tab-bar.
- The `settings-overview` 5-box grid at the top gets folded into the vertical rail as inline badges next to each tab label (e.g. a small dot/percentage next to "Hồ sơ" tab instead of a separate redundant grid above the tabs) — removes a whole duplicated section.

## 4. Typography

- Page h1s (`Cài đặt`, and the account name on `tài-khoản`) move to `var(--font-editorial)` at `--text-2xl`/`--text-3xl`, matching every other CE page's masthead. Currently both are plain system-sans at 1.5rem — the single biggest "flattest visually" tell.
- Section h2s inside settings cards (`Mật khẩu`, `Xác thực 2 bước`, `Phiên đăng nhập`, etc.) gain the sediment-tick `::before` treatment already used on `.section-head h2` / `.wp-sec h2` elsewhere — a 3px vertical river→amber→clay gradient bar to the left of each heading. Cheap, reusable, instantly stitches this page into the same visual language as the rest of the site.
- Body copy stays `--font-sans` (Inter) — settings forms should read efficiently, not cinematically. Serif is reserved for identity moments (name, section heads), not for form labels or hints.
- Numbers (stat values, score, counts) get `font-variant-numeric: tabular-nums` consistently (already present in a couple of spots, extend everywhere) + a slightly heavier weight to read as "real data," not decoration.

## 5. Sensory + motion + curiosity

- **Ring-of-progress fill animation**: on first load, the conic-gradient completion ring around the avatar sweeps from 0 to its value over ~800ms (`ease-out`), respecting `prefers-reduced-motion` (instant fill, no sweep, if reduced). This is the signature "reward" moment — currently the score just appears as static text with no sense of accrual.
- **Scroll-reveal** (already the site-wide pattern) applied lightly to the three ledger-stub panels and the workspace tiles — staggered ~60ms each, not the whole page fading in at once.
- **Micro-interaction on tab switch** (cài-đặt): panel content cross-fades + slides 8px on tab change (150ms), rather than the current instant `v-show` snap — makes the vertical-rail settings feel like a considered surface, not a raw toggle.
2FA QR reveal, recovery-codes reveal: give these a soft scale-in (they're currently just DOM pop-ins) since they're literally the moment of "your account is now safer" — worth a half-second of ceremony.
- **Discovery device**: the "Việc nên làm tiếp" (`nextActions`) list already exists as plain text links. Turn it into a **quest-like stub list** — each item gets a small progress-dot that fills when done, and completing the LAST item triggers a one-time confetti-free "Hồ sơ đã sẵn sàng" toast + the ring goes fully amber-to-leaf gold. This gives genuine payoff to a currently-invisible piece of logic (`accountScore`, `accountLevel`) that computes "sẵn sàng" but never celebrates it.
- Sensory grounding: since this page has no photography opportunity (it's the user's own private space, not a destination), the "sông nước" feeling is carried entirely through the sediment-gradient ring, the grain texture, and the boarding-pass/passport metaphor — motion and material, not imagery. This is the right page to prove the design system works without a hero photo.

## 6. UX flow

- `tài-khoản` remains the dashboard/landing; `cài-đặt` remains the deep-edit surface — that split is correct and shouldn't change. But cross-links get warmer: instead of bare `Cập nhật` / `Kiểm tra` text links on every ledger stub, use verbs that match the passport metaphor sparingly ("Hoàn thiện hồ sơ", "Xem lại bảo mật") — small copy tightening, not a gimmick throughout.
- Reduce the two redundant "profile completion" renderings: today `tài-khoản` computes its own `profileCompletion` AND `cài-đặt` computes `settingsProfileCompletion` from an overlapping-but-different checklist (tài-khoản counts posts/reviews; cài-đặt only counts hồ sơ fields). Recommend (flag as backlog, not silently changed) unifying this into one shared composable so the ring on tài-khoản and the tab-badge on cài-đặt always agree — right now a user could see "80%" in one place and a different number in the other, which undercuts the "trusted passport" feeling.
- Guest state (`cp-guest` / `settings-guest`) currently a bare card with an h1 + one line + a button. Give it the same quiet-masthead treatment as the signed-in state's `cài-đặt` masthead (serif h1, hairline, one warm sentence: "Đăng nhập để xem sổ tay hành trình của bạn.") — costs nothing, removes the jarring "prototype empty state" look.
- Danger zone (`nguy-hiem` tab) — keep visually separate (left red accent bar, already present) but soften the two destructive rows into a clearer two-tier hierarchy: "Tạm khoá" (reversible, low-key ghost button) vs "Xoá vĩnh viễn" (destructive, gets the danger-red treatment) — currently both buttons look identical in weight.

## 7. Premium cues

- Replace every hardcoded fallback color (`var(--danger, #c0392b)`, `var(--bg-warm, #f5f5f5)`, `var(--save-red, #dc2626)` used loosely, `#fff` literals) with resolved tokens only — small technical debt, big "someone actually finished this" signal, since fallback hex values are themselves a symptom of unfinished design-system adoption on exactly this page.
- Tabular-nums + consistent decimal/percent formatting on every stat.
- The recovery-codes grid (`recovery-list`) currently plain monospace in a 2-col grid — give it a subtle "printed card" treatment (dashed-border cells, like perforated ticket stubs) tying back to the passport/boarding-pass motif rather than looking like a raw JSON dump.
- Session/device list rows (`session-item`) get a small colored dot keyed to device type (mobile/desktop/unknown) instead of pure text — a tiny bit of visual encoding that reads as care.
- Focus states, hover states: already fairly solid (`:focus-visible` outlines present throughout) — keep, extend to the new vertical rail tabs.

## 8. Cultural authenticity

- **Passport / sổ tay hành trình** metaphor is native to the "cần thơ - Vĩnh Long is a place you journey through" framing without borrowing generic global-travel-app clichés (no globe icons, no "wanderlust" copy). It also literally matches how Vietnamese users think of "tài khoản du lịch" apps (VNeID-style sổ, hộ chiếu) — familiar, not foreign.
- Sediment ring (river→amber→clay) is the SAME palette as the rest of the site's phù-sa signature — reusing rather than inventing a new "gamification purple/gold" palette (a common generic-SaaS trope to avoid).
- Avoid: XP bars styled like video-game HUDs, confetti bursts, badge icons that look like generic Duolingo-style enamel pins. Keep the ceremony quiet and textural (grain, gradient sweep, dashed ticket lines) — matches "premium editorial," not "gamified app."
- Boarding-pass/perforated-ticket motif for recovery codes and session rows is a nod to travel documents without literal passport-stamp clip-art (avoids AI-slop travel iconography called out in the anti-slop playbook).

## 9. Copy voice

Tone: warm, second-person, low-key confident — the desk clerk who already knows your name, not a system notification. Short sentences. No exclamation-mark enthusiasm.

Examples:
- Hero eyebrow: **"HỒ SƠ HÀNH TRÌNH · CẬP NHẬT HÔM NAY"**
- Hero subline (replacing nothing today — currently absent): **"Đây là những gì bạn đã góp cho Vĩnh Long 360 — và những gì đang chờ bạn viết tiếp."**
- Empty activity state (replacing "Chưa có hoạt động nào."): **"Trang sổ còn trắng. Viết một dòng đầu tiên, hay cứ lưu lại một nơi bạn muốn quay lại."**
- Cài đặt masthead subline: **"Nơi giữ chìa khoá cho hồ sơ của bạn — đổi mật khẩu, bật bảo mật hai lớp, hoặc chọn ai được xem những gì bạn chia sẻ."**
- Danger zone framing (softened from clinical "Vô hiệu hóa tài khoản" heading tone): keep the heading factual, but the supporting line becomes: *"Tạm khoá không xoá gì cả — chỉ cần đăng nhập lại bằng OTP là hồ sơ trở lại y nguyên."*

## 10. Signature moment

**The avatar wrapped in a living sediment ring.** A single conic-gradient arc (river → amber → clay) traced around the user's own avatar on `tài-khoản`, filling in proportion to profile completeness, sweeping into place on load and glowing faintly warmer as it nears 100%. It's the one visual idea that (a) requires zero new imagery, (b) is unique to this page (no other page has a "your own portrait, quantified" moment), (c) directly repurposes an existing but currently-invisible data point (`profileCompletion`) into the page's most memorable pixel, and (d) is unmistakably built from the site's own palette rather than a generic progress-ring UI kit.

## 11. Components + feasibility

Concrete, CSS-tokens-only, no new paid services, dark-parity + reduced-motion required throughout:

- **`AccountAvatarRing`** (new, small wrapper around existing avatar markup): conic-gradient ring via `background: conic-gradient(from -90deg, var(--river-600), var(--amber-500) 50%, var(--clay-600) var(--pct), var(--line) var(--pct))` masked to a ring shape (padding-box trick or a pseudo-element mask), with a CSS custom property `--pct` set inline from `profileCompletion`. Animate via CSS `@property --pct` + transition, OR a simple `requestAnimationFrame`/watcher tween in Vue for broader browser support; instant snap under `prefers-reduced-motion`. **Reusable**: same ring could later wrap the public profile avatar (`nguoi-dung/[id].vue`) to show "hoàn thiện hồ sơ" publicly if desired (flag as future, not in this scope).
- **Sediment-tick section heads**: reuse the existing `.section-head h2::before` / `.wp-sec h2::before` CSS verbatim on `.settings-card h2` and `.cp-section-head h2` — zero new CSS invention, pure token reuse.
- **Dateline eyebrow**: reuse `.area-eyebrow` pattern verbatim for `cp-kicker` and a new `cd-kicker` on cài-đặt's masthead.
- **Ledger-stub divider**: `background-image: repeating-linear-gradient(...)` dashed vertical rule between the three `cp-summary-grid` panels on desktop — pure CSS, no new component.
- **Timeline activity feed**: reuse the itinerary-timeline CSS pattern (connecting line + dot) already established elsewhere in the codebase — audit `lich-trinh` page's timeline component and lift its connector/dot classes rather than reinventing.
- **Vertical settings rail**: CSS-only reflow of the existing `<nav role="tablist">` — `flex-direction: column` above 960px breakpoint, unchanged ARIA/keyboard logic (already correctly implemented with roving tabindex + arrow-key nav — do not touch the JS, only the CSS layout and the icon+label row treatment).
- **Tab-content cross-fade**: small `<Transition name="settings-panel">` wrapper around the `v-show`'d panels, CSS opacity+translateY only, `prefers-reduced-motion` guarded (project already has this guard pattern throughout `cai-dat.vue`'s `<style>` block — extend it).
- **Token cleanup**: remove all hardcoded hex fallbacks (`#c0392b`, `#f5f5f5`, `#dc2626`, raw `#fff`) in both files' `<style scoped>` blocks, replacing with the resolved tokens already defined in `variables.css` (`var(--danger)`, `var(--bg-warm)`, `var(--save-red)`, `var(--white)`/`var(--card)`) — this is pure debt paydown, no visual risk, and is the fastest win to stop this page reading as unfinished.
- **Dark-mode parity**: all new gradients/rings must have explicit `.dark` overrides exactly as the area/ward pages do for their sediment tick (`.dark .ce-area .section-head h2::before { ... }`) — copy that override pattern for every new sediment-derived element here.
- **Reduced motion**: every new transition (ring sweep, tab cross-fade, quest-dot fill, hover washes) added to the existing `@media (prefers-reduced-motion: reduce)` blocks already present at the bottom of both files' styles.
- **No new CTA/booking risk**: nothing here touches transaction flows — this unit is 100% first-party account management, no contact-CTA changes needed.
