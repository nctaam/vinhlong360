# Spec: Declutter giao diện — cắt + gộp trên 44 trang public

- **Ngày:** 2026-07-06 · **Nhánh:** `feat/dinh-vi-vinh-long` · **Trạng thái (cập nhật 2026-07-07): ĐÃ THỰC THI XONG cả 3 đợt + merge main.** Kết quả thực thi: `docs/superpowers/plans/2026-07-06-declutter-dot1-trim.md`, `2026-07-07-declutter-dot2-shared.md`, `2026-07-07-declutter-dot3-structural.md`. **Line-number trong spec đã LỖI THỜI so với code — KHÔNG thực thi lại.**
- **Nguồn bằng chứng:** workflow audit 36 agents trên trạng thái nhánh local — 92 finding (path:line), verify đối kháng: 24 confirmed/softened, 15 đề xuất bị BÁC (§6), 43 trim pass-through, 23 mục `[unverified]` phải thẩm định lại khi thực thi.

## Quyết định đã chốt với chủ dự án

| Quyết định | Giá trị |
|---|---|
| Mức cắt | **Trim + consolidate section** (không redesign tối giản) |
| Phạm vi | 44 trang public — bỏ 24 trang `/admin` (nội bộ) |
| Trình tự | **3 đợt** (§5): trim rủi-ro-thấp → hệ thống dùng chung → cấu trúc; mỗi đợt hệ thống chạy được (§B5), 1 việc/commit |
| Trang cá nhân | **Collapse CẢ heatmap "Bản đồ con nước" LẪN achievement showcase** (thu gọn sau toggle — không bỏ hẳn) |
| Bất khả xâm phạm | Danh sách §1 (byline, trust-card, nhãn AI/honesty, motif phù-sa, pháp lý, breadcrumb, skip-link…) |

**Tiêu chí thành công:** (1) trang chủ ~15 khối → ~10; (2) không còn phần tử trùng-chức-năng trên cùng trang (2 nút Báo sai, 2 bộ lọc khu vực, 2 khối count...); (3) 1 lớp interstitial duy nhất khi vào site; (4) build xanh + SSR verify khối-cắt-mất/khối-giữ-còn sau mỗi đợt; (5) không phần tử nào trong danh sách bất-khả-xâm-phạm bị mất.

---

## Kế hoạch chi tiết

Phạm vi: `web-nuxt/` (Nuxt 4 SSR). Mức đã chốt: **trim + consolidate section**. Mọi đề xuất bên dưới là CẮT hoặc GỘP — không thêm mới. Tuân thủ B5 (mỗi đợt kết thúc hệ thống chạy được), commit nhỏ 1 việc/commit.

---

## 1. Nguyên tắc cắt

Áp 3 test cho từng phần tử, theo đúng thứ tự:

1. **Deletion test** — bỏ đi, người dùng có mất khả năng quyết định/hành động trên trang này không? Không mất → thừa, cắt được.
2. **Duplication test** — có phần tử/section khác trên **cùng trang** làm cùng việc không? Có → gộp về 1 nguồn duy nhất (chọn cái dễ thấy hơn hoặc cái nằm gần hành động chính hơn).
3. **Noise test** — có tranh giành chú ý với nhiệm vụ chính của trang không? Có → hạ cấp (thu nhỏ / dời xuống / inline hoá) trước khi nghĩ tới bỏ.

**Quy tắc bổ sung:**
- Ưu tiên = (độ hiển thị với người dùng × mức giảm nhiễu) / effort. Homepage + 4 catalog + detail page đi trước; trang account/legal đi sau.
- Cắt template phải kèm **cắt CSS mồ côi** (grep class name sau khi xoá) — nhưng chỉ trong cùng commit, không dọn lan man.
- Mọi thay đổi logic filter/computed phải giữ hành vi cũ của phần **được giữ lại** (không "sửa cho xanh").
- Additive-first (B2) với thay đổi cấu trúc: gộp xong, verify SSR render đúng, rồi mới xoá khối cũ.

**Danh sách BẤT KHẢ XÂM PHẠM (không cắt, không đề xuất cắt):** byline "Ban biên tập vinhlong360" (`.entity-byline`); trust-card + link "Báo sai hoặc bổ sung nguồn"; nhãn "AI gợi ý" + disclaimer trên khối AI; nhãn honesty "chưa có ảnh thật"; motif phù-sa (tick / stratum / sediment-head / sediment-divider); text pháp lý/định vị ("không bán tour", disclaimer); breadcrumb; skip-link a11y; SaveButton/Share (chức năng); EmptyState illustration. Reveal-animation + Ken Burns là design-system có chủ đích — chỉ đụng khi lạm dụng cụ thể.

Các mục trong kế hoạch có chạm ranh giới này được đánh dấu **[touches_protected]** — chỉ được **di chuyển/thu gọn**, không được bỏ.

---

## 2. TẦNG A — Hệ thống dùng chung (sửa 1 chỗ, ăn nhiều trang)

| # | Việc làm | File | Impact | Effort |
|---|---|---|---|---|
| **A1** | **Cross-links catalog → computed `relatedCatalogs` 3 card/trang** (desktop 3, mobile 2 — CSS `catalog.css` đã có sẵn media rule). Bỏ hardcode 4 card giống hệt nhau ở cuối mỗi trang. | `pages/du-lich.vue:185-205`, `pages/san-pham.vue:163-183`, `pages/ocop.vue:222-242`, `pages/luu-tru.vue:144-164` | 4 trang catalog | **M** |
| **A2** | **Chính sách CatalogInterstitial**: không đứng thành section riêng nữa — inline vào khối editorial `.page-article` dưới dạng `<blockquote>`/`<aside>` callout, hoặc suppress trên trang ít nội dung. Sửa cách gọi ở từng trang, component giữ nguyên. | `components/CatalogInterstitial.vue` + điểm gọi: `pages/san-pham.vue:81-86`, `pages/du-lich.vue:81`, `pages/dia-diem/index.vue:77`… (10+ trang) | 10+ trang | **M** |
| **A3** | **Layout toàn cục — 3 việc:** (a) bỏ beta-banner 🚧 (`layouts/default.vue:55-63`) — OnboardingSheet đã truyền thông trạng thái beta, 2 interrupt liên tiếp là thừa; (b) footer cột "Khám phá" 7 link → cột "Gợi ý nhanh" 4 link curated (`layouts/default.vue:98-103`, data ở `174-201`); (c) JourneyBar + ReportModal chuyển từ global lazy (`layouts/default.vue:71-80`) sang import cấp trang chỉ nơi cần. | `layouts/default.vue` | **Mọi trang** | S / S / M |
| **A4** | **ChatWidget FAB render có điều kiện**: giữ trên catalog/search, ẩn trên detail page (nơi đã có AITravelTips + SmartRecommendations inline). Kèm A4b: bỏ section "Trợ lý AI" CTA cuối homepage (trùng FAB) — xem B1. | `components/ChatWidget.vue:1-40` + `layouts/default.vue` | Mọi trang (viewport mobile) | **M** |
| **A5** | **Quy tắc "1 đường filter khu vực / trang"**: hiện có 5+ trang render CẢ quick-picks blob CẢ FilterChips khu vực bind cùng 1 ref. Chốt 1 chuẩn thống nhất: **giữ quick-picks (đầu trang, cold-start), bỏ FilterChips khu vực trong controls** — áp đồng loạt le-hoi/su-kien; riêng lich-trinh làm ngược (giữ chip-row trong controls cạnh pace-chips, bỏ quick-picks) vì pace mới là trục chính. | `pages/le-hoi.vue:114-130 vs 181-187`, `pages/su-kien.vue:116-132 vs 159-165`, `pages/lich-trinh/index.vue:84-100 vs 127-136`, `pages/danh-ba.vue:31-49`, `pages/ocop.vue:98-116` | 5 trang | **M** |
| **A6** | **Ledger sự kiện filter-aware**: computed `upcoming` hiện bỏ qua statusFilter/areaFilter → ledger tĩnh trong khi list động (friction). Sửa 1 pattern áp 2 trang. | `pages/le-hoi.vue:373-382`, `pages/su-kien.vue` (computed tương ứng) | 2 trang | **S** |
| **A7** | **Chính sách JourneyActionRail**: chỉ render ở homepage + trong empty-state. Bỏ instance always-on ở da-luu (`pages/da-luu.vue:37-43`), tai-khoan (`pages/tai-khoan.vue:45-52` — trùng panel "Việc nên làm tiếp" line 89), tim-kiem (gộp 2 instance thành 1 — xem B4). Verify `useJourneyActions()` trước khi bỏ instance tai-khoan. | 3-4 trang | 3-4 trang | **S** |
| **A8** | **KnowBeforeYouGo tinh gọn + khử trùng lặp với detail page**: (a) gộp 3 golden-hours subitem thành grid 2 cột trong `.kbyg-golden` (`components/KnowBeforeYouGo.vue:20-40`); (b) khử "Giờ mở cửa" render 2 lần (highlights row `pages/dia-diem/[id].vue:99` vs KBYG); (c) amenities chỉ hiện 1 chỗ — giữ badge trong KBYG, bỏ khỏi practicalTips (`[id].vue:783-785`). **Điều kiện tiên quyết: audit data** — query entity thật xem tips/golden_hours/checklist populated bao nhiêu % trước khi cắt sâu hơn. | `components/KnowBeforeYouGo.vue`, `pages/dia-diem/[id].vue` | Mọi detail page (~1.6k entity) | **M–L** |

---

## 3. TẦNG B — Theo archetype

### B1. Homepage diet (`pages/index.vue`) — **~15 khối → ~10**

Trước → sau: `hero → decision cards → journey rail → category grid → events(hero+mini+seasonal) → EntityFeature#1 → tinh-hoa → StorySpread → EntityFeature#2(OCOP) → lịch trình → community(stats+tags+leaderboard+feed+storyland) → for-you → chatbot CTA` ⟶ `hero → decision cards → journey rail → category grid (+tile Lịch trình) → events gọn → EntityFeature#1 → tinh-hoa → StorySpread → community gọn → for-you (chỉ logged-in)`.

1. **Bỏ** section "Trợ lý AI" CTA (`index.vue:351-359`) — trùng ChatWidget FAB. *(trim, S)*
2. **Bỏ** event-hero card (`index.vue:111-126`), **giữ** decision card "Có lịch gần nhất" + 3 mini cards (`127-140`) + seasonal (`143-148`); dời cả section "Đang diễn ra" xuống sau category grid. *(consolidate, M)*
3. **Khử trùng seasonal**: `seasonalList` (`~572-575`) luôn filter `firstSeasonal` ra khỏi scroll-row (đã có decision card đại diện). Xoá dead code computed `trending` (`~487`). *(trim, S)*
4. **Gộp** section "Lịch trình gợi ý" (`233-248`) thành tile thứ 7 trong category grid (`CATEGORY_LINKS` ~492-499); fallback nếu grid khó nới: dời section lên ngay sau decision cards. *(consolidate, M)*
5. **Bỏ** EntityFeature #2 "Đặc sản OCOP" (`222-231`) — giữ 1 marquee editorial duy nhất (EntityFeature #1, `152-162`, đang giữ LCP priority); OCOP đã có tile ở category grid. *(trim, M)*
6. **Community section gọn** (`255-321`): giữ stats line + trending tags; leaderboard chips (`273-281`) hạ thành link teaser "Xem thành viên tích cực →" (link `280` đã có); bỏ storyland fallback card (`309-321`) → dùng EmptyState nhất quán (pattern `75-81`) + CTA "Tham gia cộng đồng" sẵn có (`305-307`). *(consolidate + trim, M)*
7. **For-you strip** (`326-348`): chỉ render khi `hasPersonalSignal` (logged-in có recent/favorites); bỏ fallback anon "Gợi ý khám phá" (trùng decision cards + category grid). *(consolidate, S)*
8. **Hero-nearby vs decision-card bản đồ** (`index.vue:14` vs `617-627`): giữ hero-nearby (cold-start mobile); suppress decision-card map-fallback khi hero-nearby render (thêm 1 v-if guard). *(consolidate, S)*
9. **Decision cards** (`37-58`): giữ nguyên nội dung, chỉ giảm trọng lượng thị giác (compact 2×2 thay 2-column shell, CSS `~998-1001`) — KHÔNG gộp vào category grid (chiến lược editorial theo-tháng). *(soften, S)*

### B2. Catalog archetype (du-lich / san-pham / ocop / luu-tru)

- **du-lich.vue**: (a) category rows (`68-78`) **7 loại → 4 hero + 1 gộp**: giữ EXPERIENCE/ATTRACTION/CRAFT_VILLAGE/DISH, gộp NATURE+HISTORY thành 1 section "Tâm linh, lịch sử & thiên nhiên", giảm 8→5 card/row (`slice(0,5)`) — từ ~56 card trước grid xuống ~30, grid FilterChips (`130-136`) vẫn đủ 7 loại; (b) editorial (`89-110`) **4 H2 → 2**: giữ "Vì sao chọn" + "Làng nghề", bỏ "Trải nghiệm theo mùa" (trùng hero mode-dial + season-note badge) và "Di chuyển" (thay bằng inline link /ban-do). *(consolidate, L + M)*
- **san-pham.vue**: (a) bỏ OCOP teaser strip (`52-60`) — tham chiếu OCOP thứ 3/8 section, bù bằng tăng trọng lượng chip OCOP trong FilterChips (`117-122`); (b) interstitial (`81-86`) inline vào editorial theo A2; (c) seasonal shelf (`37-49`) **thay vai** CatalogSpotlight: giữ shelf (đặc thù mùa vụ — khác biệt hơn spotlight generic) thu 8→4 card, bỏ CatalogSpotlight trên trang này — chỉ còn 1 khối tease trước grid. *(chốt tại spec-review)* *(trim/consolidate, M)*
- **ocop.vue**: (a) bỏ CatalogSpotlight (`39`) — 3 star-band honor-roll đã là "what's great" signal đặc trưng của trang; (b) bỏ region-picks (`98-116`) — lớp discovery thứ 4 trùng FilterChips khu vực trong grid (`166-173`); (c) star-jump nav (`42-53`) **giữ** (có count summary) nhưng hạ token-tier: font `--text-xs`, padding gọn. *(trim + soften, M)*
- **luu-tru.vue**: (a) `.booking-note` aside (`92-102`) inline thành 1-2 câu có `<strong>` trong đoạn editorial (`94-96`); (b) `.stay-triad` (`36-51`) 3 card template lặp → 3 bullet đậm trong editorial hoặc grid 2 cột. *(trim, S + M)*

### B3. Events archetype (le-hoi / su-kien)

- Áp A5: bỏ FilterChips khu vực (`le-hoi.vue:181-187`, `su-kien.vue:159-165`), giữ quick-picks blob — đồng bộ 2 trang thành 1 pattern.
- Áp A6: ledger "Sắp diễn ra" (`le-hoi.vue:66-92`, `su-kien.vue:73-101`) **giữ** nhưng sửa filter-aware; kèm trim mật độ ledger su-kien (bỏ `place_name` line 95 + lunar detail, giữ date/status/name/iCal).

### B4. Search (tim-kiem.vue)

- Bỏ Row E "Tìm theo khu vực" (`155-181`), giữ Row D categories — 2 grid quick-picks giống hệt nhau xếp chồng.
- Zero-result path (`94-111`): 1 SmartRecommendations + 1 JourneyActionRail duy nhất — bỏ lớp lồng trùng với lớp khi-có-kết-quả (`81-91`).

### B5. Detail pages (dia-diem/[id].vue, lich-trinh/[id].vue, xa-phuong/[id].vue, bai-viet/[id].vue)

- **dia-diem/[id].vue**: (a) bỏ `.contact-row` chết (`403-407` — desktop hidden bởi CSS `1255`, mobile bị ContactWidget che) — **verify ContactWidget cover đủ phone/zalo/buyContactUrl trước**; (b) fix double-render best_time (`149-155` vs practicalTips `780`) — chọn 1 chỗ duy nhất; (c) **[touches_protected]** gộp 2 nút "Báo sai" (trust-report `400` + quality-report `410`, cùng reportUrl) thành 1 nút — **giữ trust-card**, chỉ khử nút trùng bên trong; (d) hero `dc-actions` 6 nút (`40-59`): giữ Đã đến/Muốn đến/Sẽ đi + Theo dõi, dời Save+Share xuống sticky-cta-bar/sidebar; (e) claim-cta (`408`) dời vào khối next-steps (`419-427`) — di chuyển, không bỏ; (f) KBYG vs practicalTips theo A8.
- **lich-trinh/[id].vue**: itin-actions (`37-45`) phân cấp lại — Save+Share giữ, Báo cáo hạ btn-sm (protected, không bỏ), Tự tạo giữ primary; route-total badge (`48-60`) dời xuống dưới heading "Bản đồ lộ trình" (`105`) khỏi tranh chỗ với transport-mode.
- **xa-phuong/[id].vue**: (a) wp-contact "Liên hệ khẩn cấp" (`115-125`) chỉ render khi `attrs.police_phone` có giá trị thật — hết "Đang cập nhật" mơ hồ; (b) wp-stats (`40-54`) không hiện stat "Địa điểm" lẻ loi khi thiếu diện tích/dân số — điều kiện render đồng bộ.
- **bai-viet/[id].vue**: related-section (`129-144`) giảm 4→2 post + skeleton chống CLS (giữ tính năng, trim footprint).

### B6. Social archetype (cong-dong / nguoi-dung / bang-xep-hang / thong-bao)

- **cong-dong.vue**: (a) bỏ friend-activity section (`293-315`) — tab "Đang theo dõi" (`292`) đã làm việc này; (b) bỏ sidebar "Cách tham gia" (`481-502`) — composer + filter chips là affordance sống; (c) sidebar "Quy tắc cộng đồng" (`504-513`) → 1 link "Xem quy tắc →" tới /huong-dan-thanh-vien (đang duplicate nguyên văn — rủi ro maintenance); (d) bỏ `.mobile-discovery` strip (`241-268`) — sidebar collapse full-width ở mobile đã cover, **verify CSS breakpoint trước**; (e) bỏ empty-state onboard-follows (`367-380`), giữ sidebar "Gợi ý kết bạn" (`452-466`) làm nguồn duy nhất; (f) sidebar leaderboard (`436-450`) → compact list không podium-preview (podium là hero riêng của /bang-xep-hang).
- **nguoi-dung/[id].vue**: (a) bỏ profile-analytics card (`146-170`) — 5 stat không actionable; (b) achievement showcase (`73-93`) → collapse sau XP bar + CTA "Xem N thành tích" (giữ XP bar compact); (c) heatmap (`176-185`) → collapse sau toggle, giống showcase — **chủ dự án đã duyệt 2026-07-06: collapse CẢ showcase LẪN heatmap** (thu gọn, không bỏ hẳn; heatmap giữ branding phù-sa khi mở).
- **thong-bao.vue**: filter chips (`21-27`) giữ nguyên nếu scroll ngang mobile ổn — chỉ đụng khi test mobile fail.

### B7. Account archetype (tai-khoan / cai-dat / da-luu)

- **tai-khoan.vue**: (a) bỏ `.cp-workspace` 6 card (`112-119`), GIỮ `.cp-side-panel` (`160-177`) — cả hai show cùng 3 count; side-panel dày thông tin hơn và nav đã cover 6 đích đến *(chốt tại spec-review)*; (b) bỏ `.cp-stats` (`105-110`) — metrics đã có trên public profile (**verify trước**); (c) pill unread-notifications trong `.cp-status-row` (`23-26`) bỏ (đã có badge nav), giữ 2 pill account-health; (d) JourneyActionRail theo A7; (e) đổi robots `noindex,nofollow` → `noindex,follow` (`200-202`).
- **cai-dat.vue**: bỏ `.settings-overview` 5 card (`17-43`) — mỗi card tóm tắt đúng tab panel bên dưới.
- **da-luu.vue**: JourneyActionRail theo A7 (chỉ hiện ở empty-state).

### B8. Theo-mua.vue

- Bỏ month-grid fallback (`65-82`) — season-ring là month-picker duy nhất (signature device); test tap-target ring trên 320px trước khi commit.
- Bỏ full grid "Tất cả đang mùa" cuối trang (`205-231`) — nội dung đã hiện đủ ở shelves/flat-grid phía trên, đây là scroll đúp.
- Bỏ season-moment-pill (`38-41`) — catalog-stats ngay dưới show cùng count qua CountUp.

### B9. Khu-vuc / Kham-pha

- **khu-vuc/[area].vue**: (a) Featured (`65-93`) 6→4 item (Option A ít rủi ro nhất); (b) [unverified] bỏ Full grid (`112-119`) — type sections có toggle đã là catalog đầy đủ — **cần thẩm định lại khi thực thi**; (c) bỏ catalog-divider "Tất cả N mục" (`107-109`); (d) bỏ Wards chip row (`96-103`) — danh-ba.vue đã phục vụ use case này.
- **kham-pha/[interest].vue**: (a) bỏ int-intro (`28-33`) — hero đã nói cùng nội dung; (b) gộp 2 hàng filter khu-vực + theo-loại (`45-77`) thành 1 panel/tab control; **giữ interest-nav** (điều hướng, không phải filter) cho tới khi header có interest-picker.

---

## 4. TẦNG C — Trang lẻ đặc thù

| Trang | Việc | Ref | Effort |
|---|---|---|---|
| **huong-dan.vue** | Bỏ section Phím tắt (bảng 11 hàng, `191-208`) — nội dung rải sẵn trong 8 section; giữ 3-4 shortcut trọng yếu inline trong section liên quan. Bỏ CTA band (`240-248`) → 1 dòng "Cần thêm giúp đỡ? Liên hệ hỗ trợ". Gộp TOC: 1 search + 1 nav responsive thay vì sidebar-desktop + mobile-toc + mobile-search 3 bộ (`4-21`, `42-55`). | 3 việc | M |
| **gioi-thieu.vue** | Province-band (`68-86`) → dùng sediment-divider sẵn có + 1 dòng narrative trong section intro (giữ motif phù-sa, bỏ carousel 3-glyph riêng). **[touches_protected]** Section "Ban biên tập" (`54-65`): GIỮ toàn bộ nội dung byline, chỉ đổi trình bày từ numbered-section full-height → aside/infobox compact. | 2 việc | M |
| **chinh-sach-bao-mat.vue + dieu-khoan-su-dung.vue** | Thống nhất hero legal (`5-12` mỗi file) về template brand-masthead; xoá style `.legal-hero` riêng trong `legal.css`. | 1 pattern/2 trang | S |
| **lien-he.vue** | Bỏ section "Xem thêm" cross-links (`68-88`) — trùng footer; giữ 1 link contextual "Chính sách bảo mật" trong copy (`63`). | 1 việc | S |
| **danh-ba.vue** | Bỏ page-article editorial (`52-56`) — hero đã nói; dời caveat "đang cập nhật" thành footnote cạnh select. [unverified] Region quick-picks (`31-49`) → thẩm định khi làm A5. | 2 việc | S |
| **ban-do.vue** | Bỏ khối empty-state (`29-39`) — bản đồ trống + result-meta count là feedback đủ; message dời thành map overlay. | 1 việc | S |
| **huong-dan-thanh-vien.vue** | Bỏ CTA section cuối (`82-103` → cụ thể `96-103`). | 1 việc | S |
| **FilterChips active-state** (bug đi kèm, sửa nhân tiện) | `--surface-inverse` undefined → contrast fail trên `.fc-chip.active`. Define biến trong `variables.css` (fix CSS-only, cả 2 theme). | `components/FilterChips.vue:91-102` | S |

---

## 5. Trình tự thực thi (3 đợt — mỗi đợt kết thúc hệ thống chạy được, B5)

### Đợt 1 — Trim thuần, rủi ro thấp, ăn ngay (~1-2 ngày)
Chỉ xoá khối/dead code, không đổi logic dữ liệu:
1. A3a beta-banner · B1-1 chatbot CTA · B1-3 dead `trending` · B1-6 storyland fallback
2. B5a contact-row chết + B5b best-time double-render (dia-diem/[id])
3. B6 cong-dong: friend-activity, sidebar "Cách tham gia", "Quy tắc" → link, onboard-follows
4. B7: cp-stats, settings-overview, robots fix · C: lien-he cross-links, ban-do empty-state, huong-dan-thanh-vien CTA, danh-ba editorial
5. B8 theo-mua: season-moment-pill + full grid cuối
6. FilterChips `--surface-inverse` fix

Commit mẫu: `refactor(declutter-1): <trang> — bỏ <khối> (trùng <khối giữ lại>)`.

### Đợt 2 — Hệ thống dùng chung (~2-3 ngày)
1. A1 cross-links computed (4 catalog) → verify SSR từng trang rồi mới xoá 4 khối hardcode (B2)
2. A5 quy tắc 1-đường-filter-khu-vực (le-hoi, su-kien, lich-trinh, ocop) + A6 ledger filter-aware
3. A2 interstitial inline policy (bắt đầu san-pham, lan dần)
4. A7 JourneyActionRail policy · A3b footer column · A4 ChatWidget conditional
5. B4 tim-kiem (Row E + zero-result dedupe)

### Đợt 3 — Cấu trúc (structural, cần cân nhắc kỹ nhất, ~3-4 ngày)
1. B1 homepage: event-hero, EntityFeature #2, lịch-trình→tile, community gọn, for-you gating, reorder
2. B2 du-lich: category 7→4+1, 8→5 card, editorial 4→2
3. A8 KBYG (SAU KHI audit data entity) + B5 detail hero 6 nút + claim-cta reposition + gộp nút báo sai **[touches_protected — giữ trust-card]**
4. B9 khu-vuc/kham-pha · B8 month-grid · C gioi-thieu/huong-dan/legal hero
5. A3c JourneyBar/ReportModal page-level (kèm build analysis)

### Verify mỗi đợt (theo bài học preview-gotchas)
- `cd web-nuxt; npm run build` phải xanh.
- **SSR fetch** 1-2 URL đại diện/archetype, tuần tự: `PYTHONIOENCODING=utf-8 python -c "import urllib.request as u;print(u.urlopen('http://localhost:3000/<path>').read().decode('utf-8')[:60000])"` — grep xác nhận khối bị cắt **không còn** trong HTML và khối giữ lại **còn**.
- **Không tin screenshot** (frame trắng đã gặp) — verify style bằng `getComputedStyle` qua preview_eval/preview_inspect; dev scoped-CSS phải Ctrl+Shift+R.
- Grep class name đã xoá để dọn CSS mồ côi trong cùng commit.
- Sau đợt 3 (đụng homepage LCP): kiểm tra EntityFeature #1 vẫn giữ `priority` LCP image.

---

## 6. "KHÔNG cắt" — các đề xuất bị REJECT (kỷ luật phạm vi)

| Đề xuất bị bác | Lý do giữ nguyên |
|---|---|
| Bỏ/thu nhỏ **StorySpread** (`index.vue:213-219`) | Signature moment vừa được đầu tư có chủ đích (commit `75fa4fa`, `9752ff2` — ảnh đặc thù Vĩnh Long, motif phù-sa stratum). Ken Burns + full-bleed là design-system, không phải noise. Homepage sau diet đợt 3 còn ~10 khối — 1 palate cleanser là nhịp thở hợp lý. |
| Bỏ **⭐ Quán ngon nổi bật** (tinh-hoa) | Đã verify: 2 pattern khác nhau (temporal vs quality-ranked), nguồn dữ liệu riêng, không trùng nội dung. Layout 2 cột được thiết kế chủ đích cho case thiếu spotlight. |
| Cắt **badge stack EntityCard** | Đã verify: tối đa 4 badge, "Quanh năm"/"T3" là v-if/v-else loại trừ nhau, amenity icons đã `display:none`. Finding mô tả sai template — không có vấn đề để sửa. |
| Bỏ hẳn **KnowBeforeYouGo** hoặc flatten còn 2 section | KBYG là anchor design-system trên mọi detail page, chứa golden_hours/crowd_level không có ở đâu khác; amenity badges là facility summary duy nhất (EntityCard ẩn). Chỉ tinh gọn nội bộ + khử trùng lặp (A8), không phá. |
| Bỏ **decision cards** hoặc gộp vào category grid (`index.vue:37-58`) | Chiến lược editorial theo-tháng (funnel curated) — khác vai với nav tĩnh theo type. Chỉ giảm trọng lượng thị giác (B1-9). |
| Bỏ **hero-nearby** "Tìm quanh tôi" (`index.vue:14`) | Cold-start mobile expectation; xử lý phía decision-card fallback thay vì cắt quick-link intent cao. |
| Bỏ **heatmap "Bản đồ con nước"** + **achievement showcase** (nguoi-dung/[id]) | Feature vừa ship trong User System Deep Upgrade (4 wave), heatmap mang branding phù-sa. Cắt = phủ định đầu tư có chủ đích → chỉ đề xuất collapse (showcase), heatmap: **ĐÃ DUYỆT 2026-07-06 — collapse cả hai** (thu gọn sau toggle, không bỏ hẳn). |
| Bỏ **theme-toggle** khỏi topbar | Dark-mode toggle là expectation phổ biến; lợi ích 32px mobile không bù rủi ro khó tìm. Nếu topbar mobile vẫn chật sau đợt 1-2, xét lại. |
| Bỏ **mention-menu** composer (bai-viet/[id]) | Feature @-mention đã live (project MXH upgrades); vấn đề là layout mobile, không phải thừa — ngoài phạm vi trim. |
| Bỏ **ledger "Sắp diễn ra"** (le-hoi/su-kien) | Narrative momentum + nút iCal bulk. Fix đúng bệnh (filter-aware, A6) thay vì cắt. |
| Bỏ **interest-nav** (kham-pha/[interest]) | Affordance điều hướng duy nhất giữa các interest trên trang; chỉ được bỏ SAU KHI header có interest-picker (điều kiện tiên quyết chưa có). |
| Bỏ **related posts** (bai-viet/[id]) | Engagement driver; chỉ trim 4→2 + skeleton. |
| Bỏ **nút "Báo cáo"** trên lich-trinh/[id] | Kênh feedback thuộc nhóm protected-adjacent (trust) — chỉ hạ trọng lượng thị giác. |
| Bỏ **season-ring** thay vì month-grid (theo-mua) | Ring là signature device (quarter-coded + emoji); grid mới là fallback thừa. Cắt đúng chiều. |

**Ghi chú backlog (không tự làm — §3.6 CLAUDE.md):** các mục cần đo lường trước khi quyết (CTR interstitial, engagement sidebar-leaderboard, chat DAU, footer link clicks) ghi vào "Backlog phát sinh" trong `docs/ROADMAP.md` dưới dạng "đo rồi mới cắt", không chặn 3 đợt trên.