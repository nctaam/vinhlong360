> STATUS: complete (2026-09-20)

# Homepage UI Decluttering & Modern Refinement (Part 10) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tiếp tục hoàn thiện trang chủ Vĩnh Long 360 theo hướng tinh gọn, hiện đại và loại bỏ chi tiết thừa trên Folio II, Folio III, Folio IV và phân đoạn khép lại Hành trình tiếp nối.

**Architecture:** Tinh chỉnh trực tiếp các thẻ component ([HomeRiversideStays.vue](web-nuxt/components/home/HomeRiversideStays.vue), [HomeCulinaryTrail.vue](web-nuxt/components/home/HomeCulinaryTrail.vue), [CatalogAeoPlaque.vue](web-nuxt/components/CatalogAeoPlaque.vue), [index.vue](web-nuxt/pages/index.vue), [HomeContinuation.vue](web-nuxt/components/home/HomeContinuation.vue)), loại bỏ khối pill highlight ban công thừa, hiện đại hóa tương tác nút và cô đọng nhãn điều hướng.

**Tech Stack:** Nuxt 3, Vue 3, Scoped CSS, Vitest, Happy-DOM, Python AST pre-commit checks.

**Spec:** Triết lý "Sâu hơn, đơn giản, không thêm" từ user prompt và Tiêu chuẩn trải nghiệm vi mô R30.

## Global Constraints

- Không thêm bất kỳ component mới hay section cấp cao mới (Zero Scope Inflation).
- Duy trì 5 section cấp cao: `['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation']`.
- Giữ vững ngân sách CSS nén R30.7: trần cứng $\le 194.560\text{ bytes}$ gzipped ($190\text{ kB}$).
- TDD bắt buộc: Viết failing test trước khi sửa mã nguồn; chạy test pass mới commit.
- 0 vi phạm giọng văn R50.2 (`check_content_voice.py`).

---

### Task 1: Tinh Gọn Thẻ Homestay Sông Nước (Folio III - HomeRiversideStays)

**Files:**
- Modify: `web-nuxt/components/home/HomeRiversideStays.vue`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

- [x] **Step 1: Write the failing test**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Lược bỏ khối .home-stay-card__balcony-pill và CSS mồ côi liên quan**
- [x] **Step 4: Run test to verify it passes**

---

### Task 2: Hiện Đại Hóa Tương Tác Thẻ Món Ăn (Folio II - HomeCulinaryTrail)

**Files:**
- Modify: `web-nuxt/components/home/HomeCulinaryTrail.vue`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

- [x] **Step 1: Write the failing test**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Bỏ text-decoration underline trên hover của nút hành động**
- [x] **Step 4: Run test to verify it passes**

---

### Task 3: Đồng Bộ Nhãn Nút Cẩm Nang & Tiêu Đề Điều Hướng (Folio IV & Closing)

**Files:**
- Modify: `web-nuxt/pages/index.vue`
- Modify: `web-nuxt/components/home/HomeContinuation.vue`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

- [x] **Step 1: Write the failing test**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Cập nhật cta-label trên index.vue và tiêu đề thẻ 3 trên HomeContinuation.vue**
- [x] **Step 4: Run test to verify it passes**

---

### Task 4: Toàn Diện Hóa Kiểm Thử & Xác Minh Ngân Sách CSS R30.7

- [x] **Step 1: Run 24 bộ kiểm thử trang chủ (241+ tests pass)**
- [x] **Step 2: Nuxt build & kiểm tra ngân sách CSS gzipped <= 194.560 bytes**
- [x] **Step 3: python scripts/checks/run_hard.py --all sạch 100%**
