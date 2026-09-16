> STATUS: active (2026-09-16)

# Kế Hoạch Hiện Thực Hóa: Nâng Tầm Mỹ Thuật Biên Tập Trang Chủ Vĩnh Long 360 (Homepage Editorial Masterpiece Plan)

> STATUS: complete
> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:teamwork_preview` or `superpowers:subagent-driven-development` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nghiên cứu, phản biện, tái cấu trúc và nâng tầm mỹ thuật biên tập di sản toàn diện cho Trang chủ (`pages/index.vue`, `components/home/*`, `assets/css/home-nocturne.css`), triệt tiêu 100% AI slop, thống nhất một ngôn ngữ thiết kế độc bản với toàn bộ các phân hệ đã hoàn thiện, đồng bộ Google Stitch Project `14916181929760067680`, và bảo toàn 100% kiểm định pháp y.

**Architecture:** Áp dụng triết lý 4 chuẩn mực quốc tế (*Rijksmuseum* - Tôn nghiêm di sản; *National Geographic* - Cinematic Lead & Bố cục dẫn chuyện; *Visit Oslo* - Công thái học thực địa & thời tiết bản địa; *Monocle* - Ấn loát biên tập tỷ lệ vàng). Trang chủ đóng vai trò mỏ neo thiết kế (Anchor & Pinnacle) kết nối hài hòa giữa Khám phá Danh mục, Bản đồ Terroir, Sổ vàng OCOP, Ký sự Lễ hội, Sổ Hành trình Du ký và Niên giám Danh bạ.

**Tech Stack:** Nuxt 3, Vue 3 Composition API, Vitest, Modern CSS (oklch, liquid glass, container queries, CSS variables), Google Stitch MCP.

**Spec:** `web-nuxt/DESIGN.md` (Hiến pháp Thiết kế Vĩnh Long 360).

---

## Global Constraints

1. **Hiến pháp Dữ liệu Trung thực (`CLAUDE.md §1.7`):** Tuyệt đối không sinh dữ liệu giả mạo, không dùng chuỗi fallback mô phỏng khi API lỗi; tôn trọng điều kiện `reading.status !== 'unavailable'`.
2. **Quy chuẩn Token Bán kính (Ratchet R30.8):** Cấm triệt để scale cũ `--radius-xs/sm/md/lg/xl`. Bắt buộc dùng semantic radius tokens: `--radius-control` (8px), `--radius-surface` (12px), `--radius-sheet` (20px), `--radius-full` (9999px), `--radius-pill` (999px).
3. **Công thái học & Tiếp cận (WCAG 2.2 AAA):** 100% phần tử tương tác đạt diện tích chạm cảm ứng $\ge 44\times 44\text{px}$; độ tương phản $\ge 7:1$ tiêu đề và $\ge 4.5:1$ văn bản.
4. **Bảo toàn Bất biến Cơ sở dữ liệu (Invariants B1, B6, B7):** `agent/data/vinhlong360.db` và `web/data.json` là read-only, tuyệt đối 0 diff.
5. **Bảo toàn 100% Kiểm thử:** Tất cả 81 tests trang chủ hiện có (`npx vitest run tests/home-*.test.ts`) và 2.797+ tests toàn hệ thống phải tiếp tục pass 100%, `npm run typecheck` 0 lỗi, `python ../scripts/checks/run_hard.py --all` 0 hard violations / 0 ratchet increase, token debt = 0 (`check-tri-region-color-debt.mjs`).

---

## Task Breakdown

### Task 1: Nâng Tầm Khối Dẫn Nhập Hero & Chứng Thư Thực Địa (Hero Cinematic & Fieldwork Dossier)

**Files:**
- Modify: `web-nuxt/pages/index.vue:11-67`
- Modify: `web-nuxt/components/home/HomeFeatureDossier.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css` (khu vực `.hero`, `.hero-inner`, `.hero-main`, `.hero-feature`, `.home-feature-dossier`)
- Test: `web-nuxt/tests/home-hero-dossier-polish.test.ts`, `web-nuxt/tests/home-nocturne-page.test.ts`

**Interfaces:**
- Consumes: `heroFeature` từ `apiFetch('/api/homepage')`, `seasonalTagline`, `HERO_TERROIR_CHIPS`.
- Produces: Hero section với gradient sương sớm sông nước Cổ Chiên không chói lóa, khối tiêu đề Lora thanh lịch, và thẻ `HomeFeatureDossier` viền Liquid Glass với tọa độ GPS thực tế.

- [ ] **Step 1: Viết test kiểm tra tính tinh tế và công thái học của Hero**
  Bổ sung assertions trong `tests/home-hero-dossier-polish.test.ts`:
  - Khối chữ `hero-sub` kế thừa ánh xạ màu và độ rộng đọc tối ưu.
  - Thẻ `HomeFeatureDossier` có viền Liquid Glass `oklch(100% 0 0 / 0.12)`, bóng than củi hữu cơ đa tầng, và touch target $\ge 44\times 44\text{px}$ cho cả hai nút Khám phá và Thêm vào lịch trình.
  - Các chip `hero-terroir-chips` đạt touch target $\ge 44\times 44\text{px}$.

- [ ] **Step 2: Chạy test để xác nhận trạng thái ban đầu**
  Run: `npx vitest run tests/home-hero-dossier-polish.test.ts`

- [ ] **Step 3: Hiện thực hóa cải tiến giao diện Hero**
  - Tinh chỉnh gradient scrim trong `.hero-cinematic` chuyển tiếp êm ái sang `--color-canvas`.
  - Nâng cấp `HomeFeatureDossier.vue`: Bổ sung viền bắt sáng `border: 1px solid var(--border-liquid-glass, oklch(100% 0 0 / 0.12))`, tem di sản Mang Thít viền vàng Phù Sa, và focus ring rõ nét.
  - Chuẩn hóa touch target cho các chip gợi ý nhanh `hero-terroir-chip` $\ge 44\times 44\text{px}$.

- [ ] **Step 4: Chạy test để xác nhận hoàn tất**
  Run: `npx vitest run tests/home-hero-dossier-polish.test.ts tests/home-nocturne-page.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): elevate hero cinematic and fieldwork dossier with liquid glass and ergonomic terroir chips"`

---

### Task 2: Thanh Lọc & Hoàn Thiện Ký Sự Thổ Nhưỡng (Native Stories Overhaul)

**Files:**
- Modify: `web-nuxt/components/home/HomeNativeStories.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css` (khu vực `.home-native-stories`, `.home-story-card`, `.home-story-callout`)
- Test: `web-nuxt/tests/home-world-class-editorial.test.ts`, `web-nuxt/tests/home-anti-slop-craft.test.ts`

**Interfaces:**
- Consumes: Dữ liệu ký sự bản địa Vĩnh Long.
- Produces: Khối câu chuyện bản địa với tiêu đề thuần Việt trang nhã, thẻ câu chuyện so le bất đối xứng, trích dẫn Lora in nghiêng.

- [ ] **Step 1: Viết test chống tiếng Anh lạc điệu và đảm bảo tỷ lệ vàng biên tập**
  Trong `tests/home-world-class-editorial.test.ts`:
  - Khẳng định không còn chuỗi tiếng Anh lạc điệu "The Soul of the Mekong" trong `HomeNativeStories.vue`.
  - Khẳng định tiêu đề phụ mang bản sắc sông nước Cửu Long: `Ký sự thổ nhưỡng · Hồn cốt phù sa`.
  - Khẳng định thẻ chuyện chính có tỷ lệ vàng biên tập và viền Liquid Glass.

- [ ] **Step 2: Chạy test xác nhận kiểm tra**
  Run: `npx vitest run tests/home-world-class-editorial.test.ts`

- [ ] **Step 3: Cập nhật HomeNativeStories.vue & CSS**
  - Thay thế "The Soul of the Mekong" bằng "Ký sự thổ nhưỡng · Hồn cốt phù sa".
  - Bổ sung trích dẫn ký sự Lora cổ điển kèm `<cite>`.
  - Thêm viền Liquid Glass và bóng than củi hữu cơ đa tầng cho `.home-story-card`.

- [ ] **Step 4: Chạy test kiểm chứng**
  Run: `npx vitest run tests/home-world-class-editorial.test.ts tests/home-anti-slop-craft.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): elevate native stories into Monocle editorial chronicle and purge english tagline"`

---

### Task 3: Đồng Bộ Mỹ Thuật & Công Thái Học Quick Decisions & Category Index

**Files:**
- Modify: `web-nuxt/components/home/HomeDecisionLedger.vue`
- Modify: `web-nuxt/components/home/HomeCategoryIndex.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css` (khu vực `.home-quick-decisions`, `.home-decision-ledger`, `.home-category-index`)
- Test: `web-nuxt/tests/home-decision-category.test.ts`, `web-nuxt/tests/home-category-balance.test.ts`

**Interfaces:**
- Consumes: `HomeDecisionEntry[]`, `HomeCategoryGroups`.
- Produces: Lưới chỉ mục danh mục và lối rẽ nhanh phong cách Monocle với viền gốm Mang Thít, touch target $\ge 44\times 44\text{px}$.

- [ ] **Step 1: Bổ sung kiểm thử độ nảy xúc giác và touch target**
  Trong `tests/home-decision-category.test.ts`:
  - Khẳng định mọi liên kết trong `HomeDecisionLedger` và `HomeCategoryIndex` đều đạt `min-height: var(--touch-min)` ($\ge 44\text{px}$).
  - Khẳng định hiệu ứng hover/active tuân thủ gia tốc lò xo `cubic-bezier(0.16, 1, 0.3, 1)` và `:active scale(0.98)`.

- [ ] **Step 2: Chạy test kiểm tra**
  Run: `npx vitest run tests/home-decision-category.test.ts`

- [ ] **Step 3: Cập nhật component và CSS**
  - Tinh chỉnh spacing, typography và viền Liquid Glass cho thẻ danh mục.
  - Đảm bảo độ tương phản của nhãn và số đếm đạt chuẩn WCAG 2.2 AAA.

- [ ] **Step 4: Chạy test xác nhận**
  Run: `npx vitest run tests/home-decision-category.test.ts tests/home-category-balance.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): unify quick decisions and category index with tactile haptics and AAA ergonomics"`

---

### Task 4: Nâng Cấp Tín Hiệu Thực Địa & Nhịp Con Nước (Local Briefing & Seasonal Signals)

**Files:**
- Modify: `web-nuxt/components/home/HomeLocalBriefing.vue`
- Modify: `web-nuxt/pages/index.vue:121-244`
- Modify: `web-nuxt/assets/css/home-nocturne.css` (khu vực `.home-signals`, `.home-local-briefing`, `.event-mini`, `.home-season-row`)
- Test: `web-nuxt/tests/home-smart-terroir.test.ts`, `web-nuxt/tests/home-terroir-resilience.test.ts`, `web-nuxt/tests/home-nocturne-color-cascade.test.ts`

**Interfaces:**
- Consumes: `reading` từ `useWeather()`, `tidePhase` từ `useLunar()`, `upcomingEventList`, `seasonalList`.
- Produces: Bản tin thực địa thời tiết và nhịp triều thiên văn chuẩn *Visit Oslo*, thẻ sự kiện mini và đặc sản theo mùa định dạng Monocle.

- [ ] **Step 1: Viết test cho nhịp triều thiên văn và tính chân thực thực địa**
  Trong `tests/home-smart-terroir.test.ts`:
  - Xác nhận nhịp triều hiển thị chu kỳ nước rong/kém theo tuần trăng chính xác.
  - Xác nhận thẻ sự kiện mini có phân cấp ngày tháng rõ nét, con dấu `SourceMark` minh bạch và vạch tươi mới `FreshnessLine`.

- [ ] **Step 2: Chạy test kiểm tra**
  Run: `npx vitest run tests/home-smart-terroir.test.ts`

- [ ] **Step 3: Cập nhật HomeLocalBriefing.vue & trang chủ**
  - Đồng bộ thiết kế thẻ nhịp triều sông Cửu Long với phong cách `MekongWaterBadge`.
  - Nâng cấp typography tiêu đề sự kiện và mùa vụ bằng kiểu chữ Lora trang nhã.
  - Đảm bảo tuân thủ tuyệt đối `CLAUDE.md §1.7` (ẩn hoàn toàn khi API unavailable).

- [ ] **Step 4: Chạy test xác nhận**
  Run: `npx vitest run tests/home-smart-terroir.test.ts tests/home-terroir-resilience.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): enrich local briefing and seasonal signals with astronomical tide rhythms and monocle typography"`

---

### Task 5: Hoàn Thiện Sổ Vàng OCOP, Ký Sự Cộng Đồng & Tiếp Nối Hành Trình

**Files:**
- Modify: `web-nuxt/components/home/HomeOcopLedger.vue`
- Modify: `web-nuxt/components/home/HomeCommunityFeed.vue`
- Modify: `web-nuxt/components/home/HomeContinuation.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css` (khu vực `.home-ocop`, `.home-community-feed`, `.home-continuation`)
- Test: `web-nuxt/tests/home-ocop-ledger.test.ts`, `web-nuxt/tests/home-ocop-aeo-polish.test.ts`, `web-nuxt/tests/home-community-editorial.test.ts`

**Interfaces:**
- Consumes: `TIERS` OCOP, `communityPosts`, `communityStats`, `homeJourneyActions`.
- Produces: Chứng thư Sổ vàng OCOP quốc gia chuẩn *Rijksmuseum*, Ký sự cộng đồng điền dã và Thanh điều hướng tiếp nối.

- [ ] **Step 1: Bổ sung test chứng thư OCOP và ký sự cộng đồng**
  Trong `tests/home-ocop-aeo-polish.test.ts` & `tests/home-community-editorial.test.ts`:
  - Khẳng định khung Sổ vàng OCOP có hoa văn bảo an Guilloche trang trọng, con dấu đỏ nung Mang Thít, và không sinh sản phẩm giả.
  - Khẳng định thẻ bài viết cộng đồng có viền Liquid Glass và liên kết bục vinh danh.

- [ ] **Step 2: Chạy test kiểm tra**
  Run: `npx vitest run tests/home-ocop-ledger.test.ts tests/home-community-editorial.test.ts`

- [ ] **Step 3: Cập nhật components & CSS**
  - Thêm hoa văn bảo an Guilloche SVG tinh tế vào nền `.home-ocop__frame`.
  - Tinh chỉnh thẻ ký sự cộng đồng `cm-card` theo phong cách nhật ký điền dã.
  - Chuẩn hóa touch target của `home-ocop__cta` $\ge 44\times 44\text{px}$.

- [ ] **Step 4: Chạy test xác nhận**
  Run: `npx vitest run tests/home-ocop-ledger.test.ts tests/home-community-editorial.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): elevate national OCOP ledger with guilloche security motifs and community field notes"`

---

### Task 6: Mở Rộng Master DESIGN.md & Đồng Bộ Google Stitch Project 14916181929760067680

**Files:**
- Modify: `web-nuxt/DESIGN.md` (Mục 6.12: Homepage Masterpiece Constitution)
- Google Stitch Project: `14916181929760067680`
- Test: `web-nuxt/tests/tri-region-color-contract.test.ts`

**Interfaces:**
- Consumes: Thiết kế hoàn thiện của Trang chủ.
- Produces: Tài liệu `DESIGN.md` mở rộng và bản thiết kế màn hình tương tác trên Google Stitch Cloud.

- [ ] **Step 1: Cập nhật DESIGN.md**
  Bổ sung mục 6.12 quy định chi tiết cấu trúc, tỷ lệ thị giác, màu sắc và công thái học của Trang chủ kiệt tác biên tập di sản.

- [ ] **Step 2: Đồng bộ hóa screen blueprint lên Google Stitch Project 14916181929760067680**
  Sử dụng công cụ `generate_screen_from_text` hoặc `upload_design_md` của Stitch MCP để cập nhật bản thiết kế Trang chủ hoàn hảo.

- [ ] **Step 3: Chạy test hợp đồng màu sắc Tam Vùng**
  Run: `npx vitest run tests/tri-region-color-contract.test.ts`
  Expected: PASS 100% (78/78 tests).

- [ ] **Step 4: Commit**
  `git commit -m "docs(design): expand DESIGN.md with homepage masterpiece constitution and sync Google Stitch MCP"`

---

### Task 7: Cổng Kiểm Định Pháp Y Toàn Diện (Forensic Verification Gate) & Triển Khai Sản Xuất

- [ ] Chạy toàn bộ 81 bài test trang chủ: `npx vitest run home-` (81/81 tests pass).
- [ ] Chạy kiểm tra hợp đồng màu Tam Vùng: `npx vitest run tests/tri-region-color-contract.test.ts` (78/78 tests pass).
- [ ] Chạy kiểm tra nợ token: `node scripts/check-tri-region-color-debt.mjs` (Token debt = 0).
- [ ] Chạy kiểm tra kiểu dữ liệu Nuxt: `npm run typecheck` (0 errors).
- [ ] Chạy kiểm tra an toàn phóng: `python ../scripts/checks/run_hard.py --all` (0 hard violations, 0 ratchet increase).
- [ ] Chạy toàn bộ kho kiểm thử hệ thống: `npx vitest run` (2.797+ tests pass 100%).
- [ ] Biên dịch sản xuất Nitro: `npm run build` (Tạo gói sản xuất sạch sẽ).
- [ ] Đẩy commit lên GitHub `origin/codex/correction-case-pilot`.
- [ ] Đóng gói và triển khai atomic swap lên VPS `66.42.57.202`, kiểm tra HTTP 200 tại `https://vinhlong360.vn`.
- [ ] Cập nhật `walkthrough.md` báo cáo hoàn tất cho người dùng.
