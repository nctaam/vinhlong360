Audit xong — toàn bộ anchor đã grep trên code hiện tại (nhánh `feat/declutter-dot2`, sau Đợt 1+2). Dưới đây là bản nháp implementation-plan Đợt 3.

---

# Declutter Đợt 3 — Cấu trúc: Implementation Plan
> STATUS (2026-07-10): done — plan đã thực thi & ship.


> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (đang thực thi inline).

**Goal:** Cắt+gộp cấu trúc theo spec Tầng B/C + A3c/A8-thật — 17 task, 3 nhóm rủi-ro tăng dần, homepage + detail làm cuối.
**Grounding:** workflow 7-agent 2026-07-07 — 13 hiệu chỉnh spec (D1-D13: 6 NO-OP, 2 BÁC, D5 KBYG-golden 0%% data, D12 Báo-sai fallback, D13 tile-7 cần ảnh AI-gen).

- **Ngày audit:** 2026-07-07 · **Nhánh:** `feat/declutter-dot2` (sau `32f910b`) · **Spec:** `docs/superpowers/specs/2026-07-06-ui-declutter-design.md` §5-Đợt-3 (Tầng B + C + phần hoãn Tầng A)
- **Trạng thái:** NHÁP — mọi line-number là số **đã xác nhận hôm nay** trên code hiện tại (spec đã lệch sau 22 commit Đợt 1+2); mỗi step kèm anchor-string thật để chống lệch tiếp.
- **Bất-khả-xâm-phạm (nhắc lại):** byline `.entity-byline` + đích `#ban-bien-tap`; trust-card + **luôn còn ≥1 kênh "Báo sai"**; nhãn AI; motif phù-sa (sediment-head/divider/tick); breadcrumb; skip-link; legal text; StorySpread + decision-cards (đề xuất cắt ĐÃ BỊ BÁC §6).
- **Quyết định chủ đã chốt:** `nguoi-dung/[id]` collapse **CẢ heatmap LẪN achievement-showcase** (thu gọn sau toggle, KHÔNG bỏ); homepage giữ StorySpread + decision-cards.

## Giao thức verify chung (bài học Đợt 1+2 — bắt buộc)

- SSR fetch: `PYTHONIOENCODING=utf-8 python -c "import urllib.request as u;print(u.urlopen('http://localhost:3000/<path>').read().decode('utf-8'))"` → grep anchor **cắt-mất = 0** / **giữ-còn ≥ 1**.
- **GOTCHA SWR:** Nitro SWR cache theo PATH, query-string KHÔNG bust → sau mỗi task đụng trang có route-rule SWR phải **restart dev server** rồi mới fetch verify.
- Phần tử trong `<ClientOnly>` KHÔNG có trong SSR HTML (community section homepage, related-posts bai-viet, heatmap/showcase nguoi-dung, transport-mode lich-trinh) → verify bằng `preview_eval`/đọc source, không grep SSR.
- Không tin screenshot (frame trắng đã gặp) — style verify bằng `getComputedStyle`; dev scoped-CSS cần Ctrl+Shift+R.
- Xoá template ⇒ grep class/computed/import mồ côi, dọn **trong cùng commit**. FE vitest harness hỏng (đã biết) — `tests/smoke.test.ts` là source-string test, sửa assertion cùng commit khi cắt UI mà test đang mã hoá.

## ⚠️ SPEC SAI / ĐÃ LỖI THỜI so với code hiện tại (audit hôm nay)

| # | Spec nói | Code thật (đã grep/đo) | Hệ quả |
|---|---|---|---|
| D1 | B1-2 "dời section Đang diễn ra xuống sau category grid" | Thứ tự hiện tại ĐÃ là hero → decision → rail → cat-grid (`index.vue:90`) → Đang diễn ra (`:102`) | Reorder = **NO-OP**; chỉ còn việc bỏ event-hero |
| D2 | B1-9 decision cards "compact 2×2 thay 2-column shell card-grid" | Đã redesign thành **editorial numbered index** không box (`index.vue:990-1051`, comment "the old uniform card-grid read as generic/AI-slop"), index đã là 2×2 (`:993-998`) | **NO-OP** — spec chụp UI cũ |
| D3 | B1-3 seasonalList khử firstSeasonal | Đã có + fallback edge-case (`index.vue:548-551`), `trending` đã xoá Đợt 1 | **NO-OP** |
| D4 | A8b "Giờ mở cửa render 2 lần: highlights vs **KBYG**" | KnowBeforeYouGo.vue **không render hours** ở bất kỳ đâu; dup thật = highlights (`[id].vue:99`) vs facts-card "Tham quan" (`:313-317`) — 2 vai khác nhau (quick-scan vs bảng tham chiếu) | Đề xuất **NO-OP hours**; A8 thật chỉ còn amenities |
| D5 | A8a "gộp 3 golden-hours subitem thành grid 2 cột" | **Data-audit (đã chạy lại hôm nay, data.json 1730e + DB local 1782e):** `golden_hours`/`peak_days`/`crowd_level`/`kbyg_tips`/`checklist`/`amenity_badges` = **0%**; amenities 3.5%; KBYG thực tế chỉ render checklist fallback theo type + wifi (20e) | Khối golden **không bao giờ render** trên data thật → CSS-tweak vô nghĩa, **HOÃN** |
| D6 | B6d bỏ `.mobile-discovery` cong-dong, "sidebar collapse full-width mobile đã cover — verify CSS trước" | Verify **FAIL**: `.threads-sidebar { display: none; }` ở mobile (`cong-dong.vue:1805`) — sidebar bị ẨN hẳn, strip là nguồn **duy nhất** trending/leaderboard trên mobile | **BÁC** — cắt = mất chức năng mobile |
| D7 | B6f sidebar leaderboard "→ compact list không podium-preview" | Đã là compact `<ol class="leaderboard-list">` + `lb-row` (`cong-dong.vue:404-413`), không có podium | **NO-OP** |
| D8 | B9b [unverified] bỏ Full grid khu-vuc "type sections đã là catalog đầy đủ" | Thẩm định **FAIL**: `typeSections` chỉ lặp `CARD_TYPES` (9 type, `useConstants.ts:69`) — **restaurant (188e), cafe (56e), place (125e), facility (58e)** chỉ xuất hiện trong Full grid (`[area].vue:112-119`) | **BÁC** — cắt = ẩn gần 430 entity khỏi trang vùng |
| D9 | B5 xa-phuong "wp-stats không hiện stat Địa điểm lẻ loi" | `hasStats = !!(area_km2 \|\| population)` (`[id].vue:206`) đã guard — "Địa điểm" không bao giờ đứng một mình | **NO-OP** |
| D10 | B2 san-pham "bỏ OCOP teaser strip" | Teaser đã tự hạ cấp thành **signpost 1 dòng** `ocop-teaser-strip` (`san-pham.vue:52-60`), không còn strip card | Đề xuất **GIỮ** (mục tiêu hạ-cấp đã đạt); chỉ còn việc spotlight/shelf |
| D11 | B5 lich-trinh "Báo cáo hạ btn-sm" | Đã là `btn-ghost btn-sm` (`lich-trinh/[id].vue:42`) | Partial NO-OP; chỉ còn route-total |
| D12 | B5c gộp 2 nút Báo sai "cùng reportUrl" | Đúng còn 2 nút (`trust-report`:402, `quality-report`:407) NHƯNG trust-card có `v-if="trustVisible"` (`:383`) = chỉ hiện khi có `source_url` (`:840`) — xoá trắng quality-report sẽ làm entity **không nguồn mất kênh Báo sai** (vi phạm bất-khả-xâm-phạm) | Gộp phải bằng `v-if="!trustVisible"` chứ không xoá |
| D13 | B1-4 tile Lịch trình thứ 7 vào cat-grid | Grid desktop `repeat(6,1fr)` / mobile `repeat(3,1fr)` (`index.vue:1056-1059`); mỗi tile cần ảnh `--tile-img` (`:1088-1093`) — **chưa có `/img/cat-lich-trinh.webp`**, policy ảnh CHỈ AI-gen | Cần gen ảnh + xử lý layout 7-tile (xem T16) |

---

## NHÓM 1 — Trang lẻ, rủi ro THẤP (S)

### Task 1 — C-legal: thống nhất hero 2 trang pháp lý về brand-masthead

**Files:** `web-nuxt/pages/chinh-sach-bao-mat.vue`, `web-nuxt/pages/dieu-khoan-su-dung.vue`, `web-nuxt/assets/css/legal.css`

**Steps:**
1. Cả 2 file, anchor `<section class="catalog-hero cat-org legal-hero">` (`:5` mỗi file) → thay bằng pattern brand-masthead của `gioi-thieu.vue:6-11` (`bm-inner` / `bm-eyebrow` + `bm-tick` / `h1` / `bm-sub`); giữ nguyên `{{ doc.title }}` + `{{ doc.seo_description }}`; eyebrow dùng chữ sẵn có "Hồ sơ pháp lý" (dòng `dateline-eyebrow`:15 giữ nguyên hoặc gộp lên eyebrow — quyết tại thực thi, không đổi nội dung).
2. Xoá rule `.legal-hero { margin-bottom: var(--space-6); }` (`legal.css:11`) sau khi không còn ai dùng (grep `legal-hero` = 0).
3. KHÔNG đụng: `legal-toc` (`chinh-sach-bao-mat.vue:20-24`), nội dung sections, breadcrumb.

**Verify:** SSR `/chinh-sach-bao-mat` + `/dieu-khoan-su-dung`: `legal-hero` = 0, `brand-masthead` ≥ 1, `legal-toc` ≥ 1, title đúng. `getComputedStyle` masthead 2 trang ≍ gioi-thieu.

**Commit:** `refactor(declutter-3): legal ×2 — hero về brand-masthead dùng chung, xoá .legal-hero riêng`

### Task 2 — B5-xa-phuong: wp-contact chỉ render khi có số thật

**Files:** `web-nuxt/pages/xa-phuong/[id].vue`

**Steps:**
1. Anchor `<h3>📞 Liên hệ khẩn cấp</h3>` (`:117`): thêm `v-if="attrs.police_phone"` lên `<div class="wp-card">` (`:116`); xoá nhánh `<span v-else class="wp-phone-na">Đang cập nhật</span>` (`:122`).
2. Orphan: xoá CSS `.wp-phone-na` (`:508`) nếu không còn ai dùng (grep).
3. wp-stats (`:40-53`): **NO-OP** (D9) — ghi vào plan-result, không sửa.

**Verify:** SSR 1 xã KHÔNG có `police_phone`: `Liên hệ khẩn cấp` = 0, `Đang cập nhật` = 0; 1 xã CÓ (nếu tồn tại — grep data trước, nếu 0% toàn bộ thì card biến mất toàn cục, chấp nhận: đúng tinh thần "hết mơ hồ").

**Commit:** `refactor(declutter-3): xa-phuong — wp-contact chỉ hiện khi có số thật (hết "Đang cập nhật" mơ hồ)`

### Task 3 — B5-bai-viet: related posts 4→2 + chống CLS

**Files:** `web-nuxt/pages/bai-viet/[id].vue`

**Steps:**
1. Anchor `const params = new URLSearchParams({ limit: '4' })` (`:395`) → `'2'`.
2. Chống CLS: khối trong `<ClientOnly>` (`:130-131`) — thêm skeleton 2 card (pattern `.detail-skeleton` như `dia-diem/[id].vue:228`) render khi đang fetch, hoặc `min-height` reserve trên `.related-section` (`:640`); chọn phương án rẻ nhất tại thực thi.
3. Giữ nguyên `.related-grid` 2 cột (`:642`) — 2 post = 1 hàng.

**Verify:** `preview_eval` trên 1 bài viết có related: `document.querySelectorAll('.related-card').length <= 2`; reload đo không có layout-shift thô (so offsetTop phần comment trước/sau fetch).

**Commit:** `refactor(declutter-3): bai-viet — related 4→2 + skeleton chống CLS (giữ engagement driver)`

### Task 4 — B5-lich-trinh/[id]: route-total dời xuống heading bản đồ

**Files:** `web-nuxt/pages/lich-trinh/[id].vue`

**Steps:**
1. Anchor `<div v-if="routeResult" class="route-total">` (`:54`) + 2 biến thể loading/error (`:57-58`): dời cả cụm ra khỏi panel `transport-mode-spaced` (`:49-59`), đặt ngay sau `<h3>Bản đồ lộ trình</h3>` (`:105`) trong `route-map-section` (cùng `<ClientOnly>`, cùng điều kiện `stopsWithCoords.length >= 2` — không đổi logic).
2. CSS `.route-total { margin-left: auto; … }` (`:701-712`): bỏ `margin-left: auto` (không còn pin-right trong flex panel); giữ badge style.
3. `itin-actions` (`:38-45`): **NO-OP phần lớn** (D11) — Báo cáo đã btn-sm; tuỳ chọn nâng "Tự tạo lịch trình" (`:44`) `btn-outline`→`btn-primary` theo spec (1 dòng, quyết tại thực thi).

**Verify:** `preview_eval` 1 lịch trình ≥2 stop: `.transport-mode .route-total` = 0, `.route-map-section .route-total` = 1; nút Báo cáo còn (`aria-label="Báo cáo lịch trình"`).

**Commit:** `refactor(declutter-3): lich-trinh/[id] — route-total về dưới heading bản đồ, hết tranh chỗ transport-mode`

### Task 5 — B7-tai-khoan: bỏ cp-workspace 6 card + pill unread

**Files:** `web-nuxt/pages/tai-khoan.vue`, `web-nuxt/tests/smoke.test.ts` (nếu đụng)

**Steps:**
1. Xoá section anchor `<section class="cp-workspace" aria-label="Không gian làm việc">` (`:97`, hết `</section>` tương ứng) — GIỮ `.cp-side-panel` "Dữ liệu của bạn" (`:145-160+`) làm nguồn count duy nhất *(chốt tại spec-review)*.
2. Orphan: xoá computed `workspaceLinks` (`:243-249`); CSS `.cp-workspace` (`:408`, `:432`, media `:461`, `:468`) + `.cp-card*` (`:433-438`) — grep `cp-card` toàn repo trước, chỉ xoá nếu mồ côi.
3. Xoá pill anchor `<span v-if="counts.unread_notifications" class="cp-pill warn">` (`:25`) — count đã có ở NotificationBell (nav) + side-panel row "Thông báo chưa đọc" (`:152-155`). GIỮ 2 pill account-health (`:23-24`).
4. Check `smoke.test.ts:74-89`: không assert `cp-workspace`/`workspaceLinks` (đã xác nhận) — assertion `cp-summary-grid` (`:84`) trỏ khối khác, GIỮ khối đó.

**Verify:** SSR `/tai-khoan` (trang auth-gated — verify qua source + `preview_eval` khi login): `cp-workspace` = 0, `cp-side-panel` = 1, `cp-summary-grid` = 1, 2 pill health còn. Build + vitest-source-check thủ công (harness hỏng): grep assertion pass.

**Commit:** `refactor(declutter-3): tai-khoan — bỏ cp-workspace 6 card (trùng side-panel + nav) + pill unread (trùng badge chuông)`

### Task 6 — B6-nguoi-dung: collapse showcase + heatmap, bỏ profile-analytics *(chủ đã duyệt 2026-07-06)*

**Files:** `web-nuxt/pages/nguoi-dung/[id].vue`

**Steps:**
1. **Showcase** — anchor `<details v-if="isSelf && achievements.length" class="badge-showcase" open>` (`:73`): chỉ **xoá attribute `open`** — `<summary>` sẵn có "Thành tích ({{ achievementsEarned }}/{{ achievements.length }})" (`:74`) chính là CTA "Xem N thành tích" spec yêu cầu. GIỮ XP bar (`:64-69`) nguyên trạng.
2. **Heatmap** — anchor `<section v-if="!profile.is_private && heatmap.length" class="heatmap-section">` (`:176-185`): bọc `<details class="heatmap-section">` (KHÔNG `open`), `<summary>` = nguyên văn `Bản đồ con nước · {{ heatmapTotal }} đóng góp trong 1 năm qua` (giữ branding phù-sa; grid + title giữ nguyên khi mở). CSS: style summary từ `.heatmap-title` (`:1211`), thêm cursor/marker.
3. **Analytics** — xoá anchor `<div v-if="isSelf && Object.keys(userStats).length" class="profile-analytics card reveal">` (`:146-170`); orphan: grep `userStats` — nếu chỉ khối này dùng thì xoá luôn fetch + ref; xoá CSS `.profile-analytics` (`:1192`) + `.pa-*`.
4. KHÔNG đụng: `hairline-phusa` (`:94`), profile-stats, streak-chip, profile-completion.

**Verify:** `preview_eval` hồ sơ của mình: `details.badge-showcase` tồn tại + `!details.open`; click summary → mở, `.bs-grid` render; heatmap tương tự (`.hm-cell` chỉ có sau khi mở); `.profile-analytics` = 0. Hồ sơ người khác: heatmap collapse hiển thị, showcase không render (isSelf).

**Commit:** 2 commit — `refactor(declutter-3): nguoi-dung — collapse achievement-showcase + heatmap sau toggle (giữ nguyên tính năng, chủ duyệt)` và `refactor(declutter-3): nguoi-dung — bỏ profile-analytics 5-stat không actionable`

---

## NHÓM 2 — Trang lẻ đặc thù + catalog, rủi ro VỪA (M)

### Task 7 — C-huong-dan: phím tắt, CTA band, gộp TOC (3 commit)

**Files:** `web-nuxt/pages/huong-dan.vue`

**Steps:**
1. **Phím tắt:** xoá section anchor `<section id="phim-tat" class="guide-section reveal sediment-head">` (`:191-~206`) + mảng `const shortcuts = [` (`:909+`) + 2 link TOC `href="#phim-tat"` (`:16`, `:47`) + `'phim-tat'` trong ids IntersectionObserver (`:277`) + CSS `.shortcut-table*` (`:1170-1179`). **Giữ 3-4 shortcut trọng yếu inline** vào section liên quan: Esc/←→ lightbox vào section ảnh, "/" focus tìm kiếm vào section tìm kiếm (1-2 câu mỗi chỗ, không bảng).
2. **CTA band:** xoá anchor `<section class="guide-cta reveal">` (`:241-~248`) → thay 1 dòng `<p>` "Cần thêm giúp đỡ? <NuxtLink to="/lien-he">Liên hệ hỗ trợ</NuxtLink>." (lưu ý Đợt 1 để lại `.guide-cta` CSS đúng như plan-result ghi — xoá `:1182-1189` + dark `:1194` + print ref `:1215` cùng commit).
3. **Gộp TOC (additive-first):** hiện 3 bộ = sidebar-desktop (search `:6-8` + nav `:9-18`) + mobile-toc details (`:42-50`) + mobile-search (`:53-55`), 2 input cùng bind `search`. Hợp nhất thành **1 search + 1 nav**: giữ markup sidebar làm nguồn duy nhất, CSS responsive biến nó thành `<details>`-like ở mobile (hoặc giữ `details` bọc chung); build mới → verify cả 2 viewport → xoá `mobile-toc` + `mobile-search` + CSS + print ref (`:1215`).

**Verify:** SSR `/huong-dan`: `id="phim-tat"` = 0, `guide-cta` = 0, `Liên hệ hỗ trợ` = 1, chỉ còn **1** `input[type="search"]` trong source; mobile viewport (preview_resize 375px): TOC mở/đóng được, search hoạt động; desktop sticky còn.

**Commit:** 3 commit theo 3 bước, prefix `refactor(declutter-3): huong-dan — …`

### Task 8 — C-gioi-thieu: province-band + Ban biên tập compact **[touches_protected]**

**Files:** `web-nuxt/pages/gioi-thieu.vue`

**Steps:**
1. **Province-band** — anchor `<section class="province-band reveal" aria-labelledby="province-band-heading">` (`:68-86`): thay bằng sediment-divider sẵn có + 1 dòng narrative; đề xuất giữ nguyên văn tagline đắt nhất `Sáp nhập trên bản đồ. Chưa từng sáp nhập trong lòng người.` (`:85`) làm dòng narrative + gộp 3 mệnh đề tỉnh thành 1 câu trong intro. Xoá CSS `province-band`/`pb-*` mồ côi. (Motif phù-sa GIỮ qua sediment-divider — đúng ranh giới protected.)
2. **Ban biên tập** — anchor `<article id="ban-bien-tap" class="legal-section about-section reveal sediment-head tint-alt">` (`:54-65`): **GIỮ 100% nội dung 4 đoạn + GIỮ `id="ban-bien-tap"`** (đích của mọi `.entity-byline` site-wide — `dia-diem/[id].vue:380` link `/gioi-thieu#ban-bien-tap`); chỉ đổi trình bày: bỏ `about-section-num` full-height numbered (`:55`), chuyển thành aside/infobox compact (nền `--bg-warm`, padding gọn).

**Verify:** SSR `/gioi-thieu`: `province-band` = 0, `Sáp nhập trên bản đồ` = 1, `id="ban-bien-tap"` = 1, nguyên văn "Ban biên tập vinhlong360 tổng hợp" còn; click byline từ 1 trang entity → scroll đúng anchor.

**Commit:** 2 commit — `refactor(declutter-3): gioi-thieu — province-band → sediment-divider + 1 dòng narrative (giữ motif)` và `refactor(declutter-3): gioi-thieu — Ban biên tập numbered-section → infobox compact (giữ nguyên nội dung + #ban-bien-tap)`

### Task 9 — B2-ocop: bỏ CatalogSpotlight + hạ token star-jump

**Files:** `web-nuxt/pages/ocop.vue`

**Steps:**
1. Xoá anchor `<CatalogSpotlight :items="allOcop" />` (`:39`) — 3 star-band honor-roll (`:69`, `:74+`, `:91`) đã là "what's great" signal đặc trưng. `allOcop` còn dùng nhiều nơi — GIỮ.
2. Star-jump (`:42-53`) GIỮ (có count summary), hạ token-tier trong CSS `.star-jump-btn` (`:646-657`): `font-size: var(--text-sm)` → `--text-xs`, padding `var(--space-2) var(--space-4)` → gọn 1 nấc.
3. Ghi chú: interstitial trang này đã inline Đợt 2 (`:100-101`) — không đụng.

**Verify:** SSR `/ocop` (restart server): đếm `CatalogSpotlight` render marker = 0, `honor-roll` ≥ 1, `star-jump` = 1; `getComputedStyle` star-jump-btn fontSize ≈ 12px.

**Commit:** `refactor(declutter-3): ocop — bỏ CatalogSpotlight (honor-roll đã là signal) + hạ token star-jump`

### Task 10 — B2-san-pham: 1 khối tease trước grid

**Files:** `web-nuxt/pages/san-pham.vue`

**Steps:**
1. Xoá anchor `<CatalogSpotlight :items="allEntities" />` (`:34`) — giữ seasonal shelf `market-shelf` (`:37-49`) làm khối tease duy nhất *(chốt tại spec-review: shelf thay vai spotlight)*.
2. `seasonalHighlights` anchor `.slice(0, 8)` (`:237`) → `.slice(0, 4)`.
3. **OCOP teaser (`:52-60`): GIỮ** — D10, đã tự hạ cấp thành signpost 1 dòng từ trước; chip `Chỉ sản phẩm OCOP` đã có trong controls (`:118-123`). Ghi vào plan-result là spec-lỗi-thời, không sửa.

**Verify:** SSR `/san-pham` (restart): spotlight marker = 0, `market-shelf` = 1, đếm `market-card` ≤ 4, `ocop-teaser-strip` = 1.

**Commit:** `refactor(declutter-3): san-pham — bỏ CatalogSpotlight, shelf mùa vụ 8→4 làm khối tease duy nhất trước grid`

### Task 11 — B2-luu-tru: booking-note inline + stay-triad hạ cấp

**Files:** `web-nuxt/pages/luu-tru.vue`

**Steps:**
1. Anchor `<aside class="booking-note">` (`:94-97`): chuyển nội dung thành 1-2 câu có `<strong>` (cao điểm Tết/lễ/hè, liên hệ Zalo trực tiếp) nối vào đoạn editorial ngay trên (`:88-90`); xoá CSS `.booking-note*`.
2. Stay-triad — anchor `<div class="stay-triad">` (`:41-50`): spec duyệt "3 bullet đậm trong editorial hoặc grid 2 cột". **Lưu ý thực thi:** triad hiện là decision-device có motif/persona/price (không phải 3 card lặp thuần như audit tả) — chọn phương án **grid 2 cột editorial giữ đủ kicker/persona/price**, đừng flatten thành bullet mất thông tin; nếu khi làm thấy mất nhiều hơn được → SKIP có giải trình (nguyên tắc plan > spec chi tiết).
3. Section "Chọn thức dậy ở đâu" region-windows (`:54-72`): NGOÀI phạm vi (đường filter khu vực duy nhất của trang — Đợt 2 đã xác nhận `areaFilterOptions` hợp lệ).

**Verify:** SSR `/luu-tru` (restart): `booking-note` = 0, chữ "Tết Nguyên đán" còn (đã inline); `stay-tile` còn đủ 3 (nếu chọn grid 2 cột) hoặc = 0 (nếu bullet) — theo phương án chốt; `region-windows` = 1.

**Commit:** `refactor(declutter-3): luu-tru — booking-note inline vào editorial + stay-triad hạ cấp (giữ persona/giá)`

### Task 12 — B9: khu-vuc/[area] + kham-pha/[interest] (phần còn hiệu lực)

**Files:** `web-nuxt/pages/khu-vuc/[area].vue`, `web-nuxt/pages/kham-pha/[interest].vue`

**Steps — khu-vuc:**
1. Featured 6→4: anchor `const featured = computed(() => entityGroups.value.withImages.slice(0, 6))` (`:236`) → `slice(0, 4)` (Option A ít rủi ro nhất, spec chốt).
2. Xoá catalog-divider anchor `<span class="catalog-divider-text">Tất cả {{ entities.length }} mục</span>` (`:107-109`).
3. **Full grid (`:112-119`): KHÔNG cắt** — D8 (restaurant/cafe/place/facility ~430e chỉ có ở đây). Ghi plan-result.
4. **Wards chip row (`:96-104`): [SEO-caution]** — spec duyệt bỏ (danh-ba phục vụ use-case), NHƯNG đây là internal-link hub tới 124 trang `/xa-phuong/*` từ trang vùng (kiến trúc SEO hub-spoke đã đầu tư). Phương án đề xuất: **thu gọn thành `<details>` collapse** ("Xã / phường (N) ▾") thay vì xoá — giữ link trong DOM cho crawler, giảm nhiễu thị giác. Nếu chủ muốn bỏ hẳn → hỏi lại trước.

**Steps — kham-pha:**
5. Xoá int-intro anchor `<div v-if="data && filtered.length" class="int-intro reveal">` (`:28-33`) — hero đã nói cùng nội dung; orphan: `collectionNarrative` computed + CSS `int-intro*`.
6. Gộp 2 hàng filter (`Khu vực`:48-58 + `Theo loại`:64-76) thành 1 panel thị giác: bỏ 2 `control-label` rời, đưa 2 nhóm chip vào 1 khối `.controls` có divider mảnh — **giữ nguyên 2 ref `areaFilter`/`typeFilter` và toàn bộ hành vi** (chỉ đổi trình bày). **GIỮ interest-nav** (`:35-43`) — điều hướng, protected theo §6.

**Verify:** SSR `/khu-vuc/vinh-long` (restart): đếm card trong `honor-roll` ≤ 4, `catalog-divider` = 0, `.grid` full còn, wards links vẫn có trong HTML (nếu chọn details); `/kham-pha/am-thuc`: `int-intro` = 0, `interest-nav` = 1, cả 2 nhóm chip còn hoạt động (preview_click 1 chip khu vực → `result-meta` đổi).

**Commit:** 3 commit nhỏ (khu-vuc trim / wards collapse / kham-pha), prefix `refactor(declutter-3): …`

### Task 13 — B8-theo-mua: month-grid fallback (CÓ ĐIỀU KIỆN a11y)

**Files:** `web-nuxt/pages/theo-mua.vue`

**Steps:**
1. **Điều kiện tiên quyết (spec yêu cầu test tap-target trước):** ring-notch mobile hiện **22×22px** (`:725`) — DƯỚI chuẩn 44px. Trước khi bỏ month-grid (`:66-72`, heading "Chọn tháng" `:63`), phải nới hit-area notch (padding/pseudo-element trong suốt ≥ 44px, giữ tick visual nhỏ) và test tap trên 320px.
2. Nếu đạt: xoá month-grid section + CSS `.month-grid*` (`:452-456`, `:709-710`, `:728-729`); season-ring (`:21-32`) là month-picker duy nhất.
3. Nếu KHÔNG đạt sau 2 lần thử: **GIỮ month-grid**, ghi giải trình (điều kiện dừng §4 spec-nội-bộ) — month-grid khi đó là fallback a11y, không phải noise.
4. Full grid "Tất cả đang mùa" (`:201-205+`): **KHÔNG đụng** — Đợt 1 đã bác có chủ đích (listing đầy đủ duy nhất, fail deletion-test).

**Verify:** preview_resize 320×568: tap từng notch chọn đúng tháng (12/12), `getComputedStyle` hit-area ≥ 44px; SSR: `month-grid` = 0 (nếu cắt), `season-ring` = 1, URL `?mua=9` vẫn hoạt động (`monthFromQuery` — smoke.test `:157` đang assert, giữ).

**Commit:** `refactor(declutter-3): theo-mua — season-ring là month-picker duy nhất (nới tap-target ≥44px), bỏ month-grid fallback`

---

## NHÓM 3 — Hệ thống + homepage + detail, rủi ro CAO (L) — làm CUỐI

### Task 14 — A3c: JourneyBar + ReportModal global → page-level

**Files:** `web-nuxt/layouts/default.vue:67-68`, `web-nuxt/pages/nguoi-dung/[id].vue`, `web-nuxt/pages/lich-trinh/[id].vue`, các trang planning (danh sách dưới)

**Steps:**
1. **Build analysis trước (spec yêu cầu):** `npm run build` ghi size chunk `JourneyBar`/`ReportModal`; xác nhận 2 component là chunk riêng (Lazy).
2. **ReportModal** — consumer thật (đã grep): `openReport` chỉ ở `nguoi-dung/[id].vue:908` + `lich-trinh/[id].vue:42` (`bai-viet`/`cong-dong` dùng `reportPost` POST thẳng, không cần modal; `danh-ba` có `openReport` **local riêng** `:245` — không liên quan). → Thêm `<LazyReportModal />` (bọc ClientOnly) vào 2 trang đó, xoá anchor `<LazyReportModal />` khỏi `layouts/default.vue:68`. State `useState('report-modal')` dùng chung — hành vi không đổi.
3. **JourneyBar** (fixed-bottom "N đã lưu", render khi `count > 0`) — thêm vào các trang thuộc luồng lập-kế-hoạch: 4 catalog (`du-lich`, `san-pham`, `ocop`, `luu-tru`) + `theo-mua` + `khu-vuc/[area]` + `kham-pha/[interest]` + `dia-diem/index` + `tim-kiem` + `lich-trinh/index`; **KHÔNG** đặt ở `dia-diem/[id]` (đụng `sticky-cta-bar` cùng fixed-bottom — khử luôn 1 xung đột hiện hữu), account/legal/social. Xoá anchor `<LazyJourneyBar />` khỏi `layouts/default.vue:67`. Danh sách chốt cuối tại thực thi, ghi vào commit.
4. `smoke.test.ts:181-206` KHÔNG assert 2 component này trong layout (đã xác nhận) — không phải sửa test.

**Verify:** build xanh; `preview_eval` sau khi lưu 1 mục: `.journey-bar` xuất hiện trên `/du-lich`, KHÔNG xuất hiện trên `/tai-khoan` + `/dia-diem/<id>`; mở Báo cáo trên `/lich-trinh/<id>` → modal mở; `/bai-viet/<id>` báo cáo post vẫn hoạt động (reportPost).

**Commit:** 2 commit — `refactor(declutter-3): ReportModal global→page-level (2 trang consumer thật)` và `refactor(declutter-3): JourneyBar global→page-level (chỉ luồng lập kế hoạch, hết đè sticky-cta detail)`

### Task 15 — B2-du-lich: category 7→4+1, 8→5 card, editorial 4→2 H2

**Files:** `web-nuxt/pages/du-lich.vue`

**Steps:**
1. **Category rows** — computed `categories` (`:327-341`) hiện map thẳng `TOURISM_TYPES` (7 type: experience, attraction, accommodation, craft_village, dish, nature, history — `useConstants.ts:70`). Đổi thành mảng section cấu hình: 4 hero (EXPERIENCE / ATTRACTION / CRAFT_VILLAGE / DISH) + 1 section gộp "Tâm linh, lịch sử & thiên nhiên" (NATURE + HISTORY, items concat, seasonNote tính trên cụm). **ACCOMMODATION rơi khỏi rows theo spec** — ghi rõ trong commit: đã có trang `/luu-tru` + chip trong FilterChips grid (`:130-136` vẫn đủ 7 loại) + mode-dial hero. Lưu ý `see-all` mỗi section đang `typeFilter = cat.type` (`:71`) — section gộp cần xử lý (2 nút count hoặc filter đầu tiên; quyết tại thực thi, giữ hành vi từng type).
2. **8→5 card/row** — anchor `cat.items.slice(0, 8)` (`:76`) → `slice(0, 5)` (~56 → ~30 card trước grid).
3. **Editorial 4 H2 → 2** — trong `page-article` (`:82-110`): GIỮ "Vì sao chọn Vĩnh Long, Bến Tre, Trà Vinh?" (`:83`) + "Làng nghề trăm năm" (`:101`); XOÁ "Trải nghiệm theo mùa" (`:96-99` — trùng mode-dial + season-note badge) và "Di chuyển và lưu ý" (`:106-109` — thay bằng 1 câu inline có link `/ban-do` cuối đoạn "Vì sao chọn"). CatalogInterstitial inline (`:89-94`) GIỮ (Đợt 2). Khối `v-once` — sửa tĩnh an toàn.
4. Life-quad "Bốn cách sống trong ngày" (`:40-51`) + CatalogSpotlight (`:54`) + Featured (`:57-64`): **ngoài phạm vi Đợt 3** (spec không duyệt cắt trên trang này — spotlight chỉ bị duyệt bỏ ở san-pham/ocop).

**Verify:** SSR `/du-lich` (restart): đếm section category = 5, mỗi scroll-row ≤ 5 card; `Trải nghiệm theo mùa` (H2) = 0 nhưng `season-note` badge còn; `Di chuyển và lưu ý` = 0, link `/ban-do` inline = 1; FilterChips còn đủ 7 loại; smoke.test import du-lich (`:605-607`) pass.

**Commit:** 2 commit — `refactor(declutter-3): du-lich — category rows 7→4+1 gộp, 8→5 card/row (~56→~30 card trước grid)` và `refactor(declutter-3): du-lich — editorial 4 H2→2 (mùa đã có mode-dial; di chuyển → inline link bản đồ)`

### Task 16 — B1 homepage diet (4 commit nhỏ, LCP-sensitive)

**Files:** `web-nuxt/pages/index.vue` (+ ảnh mới nếu chọn phương án tile)

**Steps:**
1. **(B1-2) Bỏ event-hero** — anchor `<NuxtLink :to="entityPath(upcomingEvents[0].id)" class="event-hero">` (`:112-126`): xoá card lớn; GIỮ decision card "Có lịch gần nhất" (`:556-564`) + 3 mini `upcomingEvents.slice(1, 4)` (`:128`) + seasonal row (`:143-148`). Sau khi bỏ hero, cân nhắc mini `slice(1, 4)` giữ nguyên (event #1 đã có ở decision card — không lặp). Orphan CSS: `.event-hero`, `.eh-*` (formatEventDay/Month GIỮ — mini còn dùng); wrapper `happening-feature` chỉnh layout. D1: reorder = NO-OP.
2. **(B1-5) Bỏ EntityFeature #2 OCOP** — anchor `<section class="block reveal" aria-label="Đặc sản nổi bật">` (`:222-231`); orphan: `FEATURE_OCOP` (`:370-376`), `ocopThumbs` (`:544-545`). GIỮ EntityFeature #1 (`:152-162`) với `:priority="true"` — **check LCP sau commit**.
3. **(B1-4) Lịch trình → tile cat-grid** — xoá section anchor `<section v-if="itineraries.length" class="block block-compact reveal band" aria-label="Lịch trình gợi ý">` (`:234-248`); thêm tile thứ 7 vào `CATEGORY_LINKS` (`:468-475`) `{ label: 'Lịch trình', to: '/lich-trinh', key: 'lich-trinh', … }`. **D13:** cần (a) ảnh AI-gen mới `/img/cat-lich-trinh.webp` (qua `scripts/gen_image.py` — policy CHỈ AI-gen) + rule `.ct-lich-trinh { --tile-img: … }` cạnh `:1088-1093`; (b) layout 7 tile: desktop `repeat(6,1fr)` → phương án ưu tiên tile cuối `grid-column: span` hoặc đổi `repeat(4)` (4+3) — quyết bằng mắt tại thực thi; mobile 3 cols → 7 = 3+3+1, nếu xấu dùng fallback spec: **dời section lịch-trình lên sau decision cards thay vì tile** (vẫn -0 khối nhưng ít rủi ro — khi đó ghi deviation). Orphan nếu tile: `ItineraryCard` usage, `itineraries` GIỮ trong `hasHomeContent` (`:615`) để logic degraded không đổi.
4. **(B1-6 + B1-7 + B1-8) Community gọn + for-you gating + map-fallback:**
   - Leaderboard chips — anchor `<div v-if="topMembers.length" class="home-leaders">` (`:273-281`): hạ thành 1 link teaser "Xem thành viên tích cực →" tới `/bang-xep-hang` (link `:280` sẵn); GIỮ stats-line (`:264-268`) + trending-tags (`:269-272`) + feed + community-join.
   - For-you — anchor `<section v-if="forYou.length" class="block block-compact reveal" :aria-label=…>` (`:321`): đổi `v-if="hasPersonalSignal && forYou.length"`; xoá nhánh heading `v-else` "Gợi ý khám phá" (`:325`) + label fallback (`:326`); **GIỮ chuỗi `Dành cho bạn` + `for-you-row`** (smoke.test `:177-178` assert). Tuỳ chọn: gate luôn fetch `contextualRec` khi anon (perf).
   - Map-fallback decision card — khối `if (cards.length < 4)` push card `tone: 'map'` (`:593-603`): hero-nearby (`:14`) render vô điều kiện → xoá khối push map-card (spec B1-8 suppress khi hero-nearby có). Lưu ý: khi thiếu event/seasonal/dish, decision-index có thể còn 1-2 card — section đã có `v-if="homeDecisionCards.length"` (`:37`), chấp nhận.
5. **B1-9 decision compact: NO-OP** (D2) — ghi plan-result.

**Verify (restart server mỗi commit vì `/` SWR):** SSR `/`: `event-hero` = 0, `event-mini` ≤ 3, `aria-label="Đặc sản nổi bật"` = 0, `aria-label="Trải nghiệm nổi bật"` = 1 (+ `priority`/fetchpriority trên ảnh feature #1 — **check LCP image còn preload**), `aria-label="Lịch trình gợi ý"` = 0, tile `Lịch trình` = 1; community/for-you trong ClientOnly → `preview_eval`: `.home-leaders` chip = 0 + teaser link = 1; anon: for-you section = 0; user có favorites: section hiện "Dành cho bạn". Đếm khối top-level: **~10** (hero, decision, rail, cat-grid, events, feature#1, tinh-hoa, StorySpread, community, for-you-khi-login).

**Commit:** 4 commit theo 4 bước, prefix `refactor(declutter-3): home — …`

### Task 17 — B5-dia-diem/[id] + A8 thực-chất **[touches_protected — giữ trust-card]** (làm CUỐI CÙNG)

**Files:** `web-nuxt/pages/dia-diem/[id].vue`, `web-nuxt/components/KnowBeforeYouGo.vue` (nếu đụng)

**Steps:**
1. **(B5c) Gộp 2 nút Báo sai** — GIỮ `trust-report` trong trust-card (`:402`); nút `quality-report` (`:407`) KHÔNG xoá trắng mà đổi thành `v-if="!trustVisible"` (D12 — entity không nguồn vẫn còn đúng 1 kênh Báo sai). Kết quả: mọi trang luôn có **đúng 1** kênh.
2. **(B5e) Claim-cta dời vào next-steps** — anchor `<NuxtLink :to="claimUrl" class="ns-action claim-cta">` (`:405`): di chuyển xuống trong khối `<div class="next-steps">` (`:416-427`), đặt cuối danh sách ns-action. Di chuyển, KHÔNG bỏ.
3. **(B5d) Hero dc-actions** — anchor `<div class="dc-actions">` (`:40-59`): GIỮ Đã đến/Muốn đến (hoặc "Sẽ đi" event) + Theo dõi trong hero; **dời SaveButton (`:42`) + ShareButton (`:45`)** — additive-first: (i) thêm Save/Share vào sidebar (cạnh ContactWidget `:260`) cho desktop + vào `sticky-cta-bar` (`:434-439`) cho mobile, (ii) verify cả 2 viewport hoạt động (SaveButton state sync qua useFavorites — cùng composable, an toàn), (iii) mới xoá khỏi hero. Lưu ý sticky-cta-bar có logic `hasStickyContact` fallback (`:438`) — đừng phá.
4. **(A8 thực-chất, scope đã thu theo data-audit D5):** chỉ làm amenities single-source — xoá nhánh `if (a.amenities)` trong computed `practicalTips` (`:782-785`); GIỮ facts-card "Tiện ích" (`:366-370`, bảng tham chiếu) + KBYG badges (data-key khác `amenity_badges`, hiện 0%). Hours-dedup: **NO-OP** (D4 — spec premise sai; highlights vs facts-card là 2 vai). KHÔNG đụng cấu trúc KnowBeforeYouGo.vue (golden 0% data — §6 đã bác bỏ/flatten KBYG).
5. KHÔNG đụng: `.entity-byline` (`:380`), trust-card nội dung (`:383-403`), nhãn `dc-nophoto-note` (`:77`), best-time callout (`:151-157` — Đợt 1 đã chốt 1 chỗ).

**Verify (restart server; chọn 2 URL: 1 entity có `source_freshness.source_url`, 1 không — check qua `/api/entity/<id>`):** SSR: entity có nguồn → `trust-report` = 1 và `quality-report` = 0; entity không nguồn → `quality-report` = 1; tổng kênh Báo sai mỗi trang = **đúng 1**. `claim-cta` nằm trong `next-steps`. Hero: đếm nút trong `dc-actions` ≤ 3-4; `preview_eval` desktop: SaveButton trong sidebar hoạt động (toggle → count JourneyBar/favorites đổi); mobile 375px: sticky-cta có Save/Share, không tràn. `practical-tips` không còn dòng Tiện ích khi entity có `amenities` (tìm entity trong 60e có amenities để verify).

**Commit:** 3 commit — `refactor(declutter-3): dia-diem — 1 kênh Báo sai duy nhất/trang (trust-card ưu tiên, fallback khi không nguồn)`, `refactor(declutter-3): dia-diem — claim-cta về next-steps (di chuyển, không bỏ)`, `refactor(declutter-3): dia-diem — hero 6 nút→4, Save/Share về sidebar+sticky-bar; amenities 1 nguồn (A8 thu-scope theo data-audit)`

---

## HOÃN / NO-OP / BÁC trong Đợt 3 (kèm lý do)

| Mục | Quyết định | Lý do |
|---|---|---|
| A8a golden-hours grid 2 cột (KnowBeforeYouGo.vue) | **HOÃN vô hạn** | D5: golden_hours/kbyg_tips/checklist/amenity_badges = 0% trên cả data.json lẫn DB local — khối không bao giờ render; sửa CSS cho khối vô hình là công vô ích. Nếu sau này pipeline content đổ data → mở lại. |
| A8b hours-dedup | **NO-OP** | D4: KBYG không render hours; highlights vs facts-card là quick-scan vs reference — pass duplication-test theo vai. |
| B6d mobile-discovery cong-dong | **BÁC** | D6: `.threads-sidebar{display:none}` mobile (`cong-dong.vue:1805`) — strip là nguồn duy nhất trending/leaderboard mobile; điều kiện verify của chính spec fail. |
| B6f sidebar-leaderboard compact | **NO-OP** | D7: đã compact list, không podium. |
| B9b full-grid khu-vuc | **BÁC** | D8: restaurant/cafe/place/facility (~430 entity) chỉ có ở full grid — CARD_TYPES không phủ. |
| B5 xa-phuong wp-stats | **NO-OP** | D9: `hasStats` đã guard. |
| B2 san-pham OCOP teaser | **GIỮ** | D10: đã tự hạ cấp thành signpost 1 dòng. |
| B1-9 decision cards compact | **NO-OP** | D2: đã redesign editorial numbered index. |
| B8 theo-mua full-grid "Tất cả đang mùa" | **KHÔNG mở lại** | Đợt 1 bác có chủ đích (listing đầy đủ duy nhất). |
| A4 mở rộng ẩn ChatWidget sang detail khác (lich-trinh/xa-phuong/bai-viet) | **HOÃN** | Đợt 2 chốt scope dia-diem/[id] (nơi có AI inline); các detail khác không có AI thay thế — cắt FAB = mất kênh hỏi. Đo chat-DAU rồi quyết (backlog "đo rồi mới cắt"). |
| kham-pha interest-nav | **GIỮ** | §6: chỉ bỏ sau khi header có interest-picker (chưa có). |
| A3b footer prod DB (`footer.columns` PG) | **Vận hành lúc deploy** | Điều kiện dừng §4 CLAUDE.md — Đợt 2 đã ship default+seed. |
| khu-vuc wards row bỏ hẳn | **Đổi thành collapse, hỏi chủ nếu muốn bỏ** | Internal-link hub tới 124 trang xã/phường (SEO hub-spoke đã đầu tư) — xoá khỏi DOM cần chủ duyệt riêng. |

## Kết-đợt (bắt buộc trước khi báo hoàn thành)

1. `cd web-nuxt && npm run build` — xanh (chạy lại 1 lần nếu fail transient như Đợt 2).
2. `python -m pytest -q` (từ repo root/agent) — không đỏ thêm ngoài 6 fail `TestPhase14PgIndexes` pre-existing (thiếu Postgres).
3. **SSR-sweep 14 URL trên server RESTART** (SWR cache theo path — không tin query-bust): `/`, `/du-lich`, `/san-pham`, `/ocop`, `/luu-tru`, `/theo-mua`, `/khu-vuc/vinh-long`, `/kham-pha/am-thuc`, `/gioi-thieu`, `/huong-dan`, `/chinh-sach-bao-mat`, `/dia-diem/<id có nguồn>`, `/dia-diem/<id không nguồn>`, `/lich-trinh/<id>` — 200 + mọi anchor-cắt = 0 + anchor-giữ ≥ 1 theo bảng verify từng task.
4. **Protected-sweep:** grep SSR xác nhận còn nguyên: `.entity-byline`, `#ban-bien-tap`, trust-card, đúng-1 kênh Báo sai/trang, `dc-nophoto-note` (nhãn honesty), breadcrumb, skip-link, StorySpread, decision-index, sediment-head/divider.
5. **LCP check** (sau T16): EntityFeature #1 vẫn giữ `priority` — ảnh `trai-nghiem.webp` có `fetchpriority="high"`/preload trong HTML `/`.
6. `preview_eval` các phần ClientOnly: JourneyBar policy (T14), for-you gating, collapse nguoi-dung, Save/Share sidebar+sticky.
7. Grep orphan cuối: `FEATURE_OCOP`, `ocopThumbs`, `workspaceLinks`, `shortcuts`, `collectionNarrative`, `province-band`, `pb-glyph`, `.legal-hero`, `.month-grid`, `.booking-note`, `.cp-workspace`, `.profile-analytics`, `.event-hero`, `.guide-cta` — 0 mồ côi ngoài comment giải thích.
8. Ghi mục "KẾT QUẢ THỰC THI ĐỢT 3" vào plan file; việc phát sinh (pipeline data KBYG, đo chat-DAU/interstitial-CTR, wards-row bỏ hẳn) → "Backlog phát sinh" trong `docs/ROADMAP.md`, KHÔNG tự làm (§3.6).

**Đường dẫn liên quan:** spec `C:\Code\vinhlong360\docs\superpowers\specs\2026-07-06-ui-declutter-design.md` · plan-result đợt trước `C:\Code\vinhlong360\docs\superpowers\plans\2026-07-06-declutter-dot1-trim.md`, `C:\Code\vinhlong360\docs\superpowers\plans\2026-07-07-declutter-dot2-shared.md` · file plan Đợt 3 đề xuất: `docs/superpowers/plans/2026-07-07-declutter-dot3-structural.md` (tạo khi thực thi).

---

## KẾT QUẢ THỰC THI ĐỢT 3 (2026-07-07, hoàn tất)

**17/17 task xử lý — 12 commit trên `feat/declutter-dot2`** (nối tiếp 8 commit Đợt 2 cùng nhánh).

### Task-by-task
| Task | Kết quả |
|---|---|
| T1 legal masthead | ✅ 2 trang → brand-masthead (copy CSS per-page vì chưa có file chung) |
| T2 xa-phuong khẩn cấp | ✅ gate `v-if=police_phone`, bỏ nhánh "Đang cập nhật" |
| T3 bai-viet related 4→2 | ✅ (skeleton SKIP — YAGNI, block cuối trang) |
| T4 lich-trinh route-total | ✅ dời xuống sau h3 "Bản đồ lộ trình" (trong ClientOnly — verify browser: total đứng ngay sau heading, transport panel sạch) |
| T5 tai-khoan workspace | ✅ xoá section + computed + CSS (kể cả reduced-motion) |
| T6 nguoi-dung collapse | ✅ showcase bỏ `open`; heatmap bọc `<details>` (verify browser: đóng mặc định, click mở, grid render); profile-analytics xoá |
| T7 huong-dan | ✅ phím-tắt → mẹo-nhanh inline; CTA band → 1 dòng; mobile-search vào details TOC |
| T8 gioi-thieu | ✅ province-band → sediment-divider + tagline; ban-bien-tap → editors-infobox (nội dung + id giữ 100%) |
| T9 ocop | ✅ bỏ CatalogSpotlight + hạ token star-jump (xs, padding gọn) |
| T10 san-pham | ✅ bỏ CatalogSpotlight + shelf slice 8→4 |
| T11 luu-tru | ✅ booking-note inline vào editorial; **stay-triad SKIP có giải trình** (decision-device 3 kiểu ở distinct — pass deletion-test; 2-cột tạo orphan, bullet mất scanability) |
| T12 khu-vuc + kham-pha | ✅ featured 6→4, bỏ catalog-divider, wards → `<details>` GIỮ 124 link DOM; int-intro xoá + 2 hàng filter → 1 panel divider mảnh (verify click: 336→126→51) |
| T13 theo-mua | **GIỮ month-grid** — precheck a11y FAIL bằng đo thực nghiệm: nới notch 44px trên vòng 76px → 11/12 tap trúng SAI tháng (tâm kề nhau ~15px; wedge clip-path cũng chỉ đạt ~19.7px). Cần phóng vòng ≥170px = redesign hero, ngoài scope → month-grid là fallback a11y chính danh. Ghi backlog. |
| T14 A3c | ✅ ReportModal page-level — **DEVIATION: 4 trang consumer thật** (grounding cũ sai: `reportPost` cũng mở modal → thêm cong-dong + bai-viet/[id], thiếu là hỏng kênh báo cáo NĐ147); JourneyBar → 10 trang planning, bỏ layout (verify: hiện /du-lich khi có mục lưu, vắng /tai-khoan + /dia-diem/[id] — khử xung đột sticky-cta) |
| T15 du-lich | ✅ 7→4+1 gộp "Tâm linh, lịch sử & thiên nhiên" (2 nút jump giữ hành vi từng type), 8→5 card/row, editorial 4 H2→2 (mùa → mode-dial/season-note; di chuyển → 1 câu inline + link /ban-do) |
| T16 homepage | ✅ 4 commit: (B1-2) event-hero bỏ — minis thành hàng 3 cột; (B1-5) EntityFeature OCOP bỏ, #1 giữ priority; (B1-4) strip lịch-trình → tile 7 cat-grid, **ảnh AI-gen mới `/img/cat-lich-trinh.webp`**, desktop repeat(4)+span2 = 2×4 khít (đo rects), mobile 3+3+full; (B1-6/7/8) leaderboard → teaser, for-you gate `hasPersonalSignal` (verify 2 nhánh), bỏ card độn bản đồ. B1-9 NO-OP (D2), reorder NO-OP (D1). |
| T17 dia-diem | ✅ 2 commit: (B5c/D12) đúng-1-kênh Báo sai — `quality-report` v-if=!trustVisible (verify SSR 2 URL: có-nguồn 1/0, không-nguồn 0/1); (B5e) claim-cta → next-steps; (B5d) hero 6 nút→3, Save/Share → `.aside-actions` sidebar — **DEVIATION: không chèn sticky-cta-bar** (bar bị ẩn <768px vì ContactWidget có bottom-bar mobile riêng; chỉ sống 768–840px) — sidebar stack dưới article nên phủ mọi viewport (verify 375px + toggle + localStorage); (A8/D5) amenities 1 nguồn = facts-card (verify entity có amenities: tips hết dòng Tiện ích) |

### Kết đợt
1. **Build**: `npm run build` XANH (exit 0).
2. **pytest**: 5304 passed / 31 skipped / 68 deselected / 1 xfailed. 10 fail = 6 TestPhase14PgIndexes (pre-existing, thiếu Postgres) + **4 fail KHÔNG do đợt này — đỏ y hệt trên main** (chứng minh bằng worktree main sạch):
   - 3× `test_cost_tracker.py::TestBudgetManagerCheckBudget` — bug testcode: test dùng `datetime.now()` (local), module đã chuyển UTC (commit 180a1fd) → chỉ đỏ trong cửa sổ 00:00–07:00 VN khi 2 ngày lệch nhau (lúc chạy: local 07-07 06:55 / UTC 07-06 23:55).
   - 1× `test_seo.py::test_sitemap_includes_all_public...` — test lỗi thời sau P0-1 cổng index: mock entity mỏng bị `is_index_worthy` loại khỏi sitemap (hành vi mới CHỦ ĐÍCH).
   - Cả 4 cần sửa TEST theo hành vi mới → báo chủ dự án quyết (không tự sửa yếu assertion, §3.4).
3. **SSR-sweep 14 URL (server restart)**: 12/14 pass thẳng; 6 flag còn lại đều false-positive/hợp lệ: san-pham `CatalogSpotlight` chỉ là `<link stylesheet>` dev-graph (template=0); ocop `honor-roll` gate `fiveStarHighlights.length` — data local không có 5 sao (star-jump vẫn 3); `aside-actions` + lich-trinh `route-total`/"Bản đồ lộ trình" nằm trong ClientOnly → verify browser pass.
4. **Protected-sweep**: entity-byline=1 (2 URL), #ban-bien-tap=1, trust-card còn, đúng-1 kênh Báo sai/trang, breadcrumb, skip-link=3, StorySpread=1, decision-index=5 card ref, sediment-divider/merge-tagline=1, dc-nophoto-note nguyên source (gate !hasEntityImages đúng).
5. **LCP**: preload hero ×2 (mobile/desktop) + fetchpriority=high ×2 + feature #1 trai-nghiem giữ priority.
6. **ClientOnly evals**: JourneyBar policy ✅, for-you 2 nhánh ✅, Save/Share sidebar ✅ (desktop+375px), heatmap/showcase collapse ✅, ReportModal mở /lich-trinh + vắng /du-lich ✅, kham-pha 2 nhóm chip hoạt động ✅.
7. **Orphan-grep 20 pattern**: 0 mồ côi (month-grid = giữ chủ đích T13; home-leaders = class teaser mới; shortcuts = admin ngoài scope).

### Gotcha ghi nhận thêm (bổ sung memory)
- Nitro SWR dev: restart XONG vẫn thấy HTML cũ trên browser → đó là **browser HTTP-cache**, không phải server; verify SSR bằng python urllib, đừng tin `location.href` reload.
- Đo `getComputedStyle` ngay sau khi đổi style trong CÙNG eval = giá trị cũ (transition `all` chưa tick frame) — đo sau `setTimeout`.
- Cảnh báo dev "`does not have a single root node`" xuất hiện khi HMR page component — kiểm template thật trước khi tin (cả index.vue lẫn du-lich.vue đều 1 root).

### Backlog phát sinh → đã ghi `docs/ROADMAP.md` (mục Declutter Đợt 3 2026-07-07)
KBYG data-pipeline · đo chat-DAU/interstitial-CTR · wards-row bỏ-hẳn cần chủ duyệt · season-ring 44px cần redesign hero · (mới) sửa 4 test đỏ-trên-main (cost_tracker UTC-date + test_seo sau cổng index).
