> STATUS: complete (2026-09-19)

# Homepage UI Decluttering & Modern Refinement (Part 9) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tiếp tục hoàn thiện trang chủ Vĩnh Long 360 theo hướng tinh gọn, hiện đại và loại bỏ chi tiết thừa trên các phân đoạn Folio I, Folio II và Folio III.

**Architecture:** Tinh chỉnh trực tiếp các thẻ component ([HomeCuratedShowcase.vue](web-nuxt/components/home/HomeCuratedShowcase.vue), [HomeCulinaryTrail.vue](web-nuxt/components/home/HomeCulinaryTrail.vue), [HomeRiversideStays.vue](web-nuxt/components/home/HomeRiversideStays.vue)), loại bỏ khối tips rườm rà, cô đọng nhãn nút bấm hành động. Không bổ sung thư viện hay component mới để bảo vệ ngân sách CSS R30.7.

**Tech Stack:** Nuxt 3, Vue 3, Scoped CSS, Vitest, Happy-DOM, Python AST pre-commit checks.

**Spec:** Triết lý "Sâu hơn, đơn giản, không thêm" từ user prompt và Tiêu chuẩn trải nghiệm vi mô R30.

## Global Constraints

- Không thêm bất kỳ component mới hay section cấp cao mới (Zero Scope Inflation).
- Duy trì 5 section cấp cao: `['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation']`.
- Giữ vững ngân sách CSS nén R30.7: trần cứng $\le 194.560\text{ bytes}$ gzipped ($190\text{ kB}$).
- TDD bắt buộc: Viết failing test trước khi sửa mã nguồn; chạy test pass mới commit.
- 0 vi phạm giọng văn R50.2 (`check_content_voice.py`).

---

### Task 1: Tinh Gọn Thẻ Lead Di Sản (Folio I - HomeCuratedShowcase)

**Files:**
- Modify: `web-nuxt/components/home/HomeCuratedShowcase.vue`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

- [x] **Step 1: Write the failing test**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Lược bỏ khối .home-curated-lead__tips và CSS mồ côi**
- [x] **Step 4: Run test to verify it passes**

---

### Task 2: Hiện Đại Hóa Nhãn Nút Bấm Ẩm Thực (Folio II - HomeCulinaryTrail)

**Files:**
- Modify: `web-nuxt/components/home/HomeCulinaryTrail.vue`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

- [x] **Step 1: Write the failing test**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Rút gọn nhãn nút thành "Vị trí & Chỉ đường"**
- [x] **Step 4: Run test to verify it passes**

---

### Task 3: Tinh Gọn Nút Bấm & Perks Thẻ Homestay (Folio III - HomeRiversideStays)

**Files:**
- Modify: `web-nuxt/components/home/HomeRiversideStays.vue`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

- [x] **Step 1: Write the failing test**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Rút gọn nhãn nút thành "Liên hệ & Đặt phòng" và tối ưu độ thoáng cho perks**
- [x] **Step 4: Run test to verify it passes**

---

### Task 4: Toàn Diện Hóa Kiểm Thử & Xác Minh Ngân Sách CSS R30.7

- [x] **Step 1: Run 24 bộ kiểm thử trang chủ (240+ tests pass)**
- [x] **Step 2: Nuxt build & kiểm tra ngân sách CSS gzipped <= 194.560 bytes**
- [x] **Step 3: python scripts/checks/run_hard.py --all sạch 100%**
