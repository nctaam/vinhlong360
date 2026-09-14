# Kế Hoạch Nâng Cấp & Hoàn Thiện Sâu Cửa Sổ Trang Chủ Hiện Tại (Anti-AI-Slop Deep Polish Plan)

> STATUS: active
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện sâu, nâng cấp vi phẫu thuật mỹ học (micro-typography, micro-spacing, content craftsmanship) trên duy nhất cửa sổ hiện tại (`113af35ecf1846e8b4dd7425c432f425` trên Google Stitch `14916181929760067680` và `pages/index.vue` trong `web-nuxt`), tuyệt đối không tạo thêm cửa sổ/màn hình mới, triệt tiêu 100% AI-slop cả về thị giác lẫn câu chữ.

**Architecture:** Áp dụng trường phái `editorial-grid-magazine` từ kỹ năng UI Pro Max kết hợp triết lý tạp chí văn hóa điền dã Nam Bộ (Sơn Nam / Vương Hồng Sển). Tinh chỉnh trực tiếp tại chỗ (in-place edit) qua API `edit_screens` của Stitch và đồng bộ vào các component Vue hiện hữu.

**Tech Stack:** Stitch MCP (`edit_screens`), Nuxt 3, Vue 3, Vitest, Vanilla CSS Tokens, UI Pro Max (`editorial-grid-magazine`).

**Spec:** `docs/superpowers/specs/2026-09-14-homepage-riverine-broadside-spec.md`

## Global Constraints

- **Scope:** CHỈ nâng cấp trên duy nhất màn hình hiện tại `113af35ecf1846e8b4dd7425c432f425`. CẤM gọi lệnh sinh tạo màn hình mới (`generate_screen_from_text`).
- **Không phát triển thêm:** Zero new routes, zero new components, zero new database models, payload < 200KB.
- **Triệt tiêu AI-Slop:** Cấm toàn bộ từ ngữ sáo rỗng, hoa mỹ giả tạo (tuân thủ `docs/claude-desktop/anti-ai-writing-style.md`).
- **Chất lượng thị giác:** Loại bỏ hoàn toàn viền răng cưa, khối bento đen, shadow mờ đục. Dùng đường gióng 1px hairline (`#E5DDD0`), nền giấy ngà (`#FAF8F5`), tỷ lệ khoảng thở $\ge 40\%$.
- **Độ tin cậy mã nguồn:** 100% (20/20 test files, 104+ tests) Vitest PASS, 0 color debt (WCAG 2.2 AAA PASS).

---

### Task 1: Thẩm Định Pháp Y Mỹ Học UI/UX Trên Màn Hình Hiện Tại

**Files:**
- Read: `C:\Users\NCTaam\.gemini\antigravity-ide\brain\71b606fa-723e-4a79-8a19-854bf74a7b8d\stitch_screen_riverine_masterpiece.html`
- Read: `C:\Users\NCTaam\.gemini\antigravity-ide\brain\71b606fa-723e-4a79-8a19-854bf74a7b8d\stitch_screen_riverine_masterpiece.png`
- Create: `docs/superpowers/specs/2026-09-14-ui-deep-polish-audit.md`

**Interfaces:**
- Consumes: Báo cáo thị giác màn hình `113af35ecf1846e8b4dd7425c432f425`.
- Produces: Bản danh mục các chi tiết vi phẫu thuật cần nâng cấp (typography, spacing, pull quotes, metadata provenance).

- [ ] **Step 1: Rà soát các điểm có thể hoàn thiện sâu hơn trên cửa sổ hiện tại**

Sử dụng checklist `editorial-grid-magazine` từ UI Pro Max:
1. *Chữ khởi đầu (Drop Cap):* Bổ sung chữ hoa đầu đoạn (drop cap) cổ điển cho bài ký sự mở đầu để gia tăng khí chất ấn phẩm.
2. *Trích dẫn văn học (Pull Quotes):* Tinh chỉnh font chữ Lora in nghiêng, viền trái vệt son gốm Măng Thít (`border-l-2 border-terracotta`), trích dẫn rõ nguồn sách (*Gia Định Thành Thông Chí*, *Hương Rừng Cà Mau*).
3. *Chỉ dẫn con nước (Tidal Advisory):* Chuyển đổi hộp thông báo con nước thành dải ruy-băng phù sa tinh tế, hài hòa tuyệt đối với chân trang.
4. *Khung tìm kiếm:* Tinh giản padding, thêm nhãn gợi ý thực địa tinh khôi.

- [ ] **Step 2: Viết tài liệu kiểm tra chất lượng `docs/superpowers/specs/2026-09-14-ui-deep-polish-audit.md`**

Đảm bảo file có header `> STATUS: active` trong 10 dòng đầu để tuân thủ Ratchet R60.1.

- [ ] **Step 3: Commit tài liệu audit**

```bash
git add docs/superpowers/specs/2026-09-14-ui-deep-polish-audit.md docs/superpowers/plans/2026-09-14-deep-polish-current-screen-anti-ai-slop.md
git commit -m "docs: add UI deep polish audit for current riverine screen"
```

---

### Task 2: Nâng Cấp Tại Chỗ (In-Place Edit) Trên Google Stitch Qua `edit_screens`

**Files:**
- Modify: Screen `113af35ecf1846e8b4dd7425c432f425` trên Google Stitch (`projects/14916181929760067680`)
- Update: `C:\Users\NCTaam\.gemini\antigravity-ide\brain\71b606fa-723e-4a79-8a19-854bf74a7b8d\stitch_screen_riverine_masterpiece.html`
- Update: `C:\Users\NCTaam\.gemini\antigravity-ide\brain\71b606fa-723e-4a79-8a19-854bf74a7b8d\stitch_screen_riverine_masterpiece.png`

**Interfaces:**
- Consumes: Screen ID `113af35ecf1846e8b4dd7425c432f425`, prompt chỉnh sửa sâu tại chỗ.
- Produces: Bản cập nhật hoàn thiện sâu của chính màn hình đó (KHÔNG TẠO SCREEN MỚI).

- [ ] **Step 1: Soạn prompt chỉnh sửa in-place chi tiết**

Yêu cầu giữ nguyên cấu trúc 4 màn xuất sắc, nâng cấp:
- Drop cap nghệ thuật cho bài mở đầu ký sự.
- Tinh chỉnh pull quote với đường chỉ son gốm đất nung.
- Tinh chỉnh tỷ lệ phân cách giữa 4 trụ cột văn hóa.

- [ ] **Step 2: Thực thi lệnh Stitch MCP `edit_screens`**

Gọi `edit_screens` với:
- `projectId`: `"14916181929760067680"`
- `selectedScreenIds`: `["113af35ecf1846e8b4dd7425c432f425"]`
- `deviceType`: `"DESKTOP"`

- [ ] **Step 3: Tải lại file HTML và ảnh render cập nhật**

Ghi đè trực tiếp lên `stitch_screen_riverine_masterpiece.html` và `stitch_screen_riverine_masterpiece.png`.

- [ ] **Step 4: Thẩm định trực quan ảnh render**

Xác nhận:
- Screen ID vẫn giữ nguyên là `113af35ecf1846e8b4dd7425c432f425`.
- Chất lượng mỹ học sâu sắc hơn, tinh tế hơn, sạch bóng AI-slop.

---

### Task 3: Đồng Bộ Hoàn Thiện Sâu Vào Mã Nguồn Nuxt Hiện Hữu (`web-nuxt`)

**Files:**
- Modify: `web-nuxt/components/home/HomeDecisionLedger.vue`
- Modify: `web-nuxt/components/home/HomeCategoryIndex.vue`
- Modify: `web-nuxt/pages/index.vue`
- Test: `web-nuxt/tests/home-decision-category.test.ts`
- Test: `web-nuxt/tests/home-world-class-editorial.test.ts`

**Interfaces:**
- Consumes: Thiết kế hoàn thiện sâu từ màn hình Stitch.
- Produces: Mã nguồn Nuxt sạch bóng xung đột tiêu đề và nhãn rác, bảo đảm 100% test pass.

- [ ] **Step 1: Viết test TDD kiểm tra tính nhất quán tiêu đề khám phá**

Cập nhật `tests/home-decision-category.test.ts` để assert tiêu đề thống nhất và kiểm tra không còn nhãn rác `Trải nghiệm phong phú`.

- [ ] **Step 2: Chạy test để xác nhận FAIL đỏ**

```bash
cd web-nuxt && npx vitest run tests/home-decision-category.test.ts
```

- [ ] **Step 3: Hợp nhất tiêu đề và dẹp bỏ nhãn rác trong `HomeDecisionLedger.vue` & `HomeCategoryIndex.vue`**

Hỗ trợ prop `compactHeader?: boolean`, loại bỏ chữ thừa.

- [ ] **Step 4: Chạy test để xác nhận PASS xanh**

```bash
cd web-nuxt && npx vitest run tests/home-decision-category.test.ts
```

- [ ] **Step 5: Commit mã nguồn**

```bash
git add web-nuxt/components/home/ web-nuxt/pages/index.vue web-nuxt/tests/
git commit -m "refactor(home): unify exploration section headers and eliminate legacy clutter"
```

---

### Task 4: Kiểm Chứng Toàn Diện & Nghiệm Thu (Full Verification)

**Files:**
- Modify: `visual_inspection_report.md`
- Modify: `.superpowers/sdd/2026-09-14-new-homepage-stitch-ground-truth/progress.md`

**Interfaces:**
- Consumes: Test suites và scripts audit.
- Produces: Hệ thống sạch nợ kỹ thuật, 100% test pass.

- [ ] **Step 1: Chạy toàn bộ 20 file test Vitest**

```bash
cd web-nuxt && npx vitest run tests/home-
```
Kỳ vọng: 20/20 test files, 104+ tests PASS 100%.

- [ ] **Step 2: Kiểm tra độ tương phản màu sắc WCAG AAA**

```bash
node scripts/check-tri-region-contrast.mjs
```
Kỳ vọng: Exit code 0, không có nợ màu sắc.

- [ ] **Step 3: Cập nhật tài liệu nghiệm thu**

Cập nhật `visual_inspection_report.md` và thông báo hoàn tất cho người dùng.
