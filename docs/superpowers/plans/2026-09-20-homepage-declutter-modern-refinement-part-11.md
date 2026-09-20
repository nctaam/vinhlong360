> STATUS: complete (2026-09-20)

# Homepage UI Decluttering & Modern Refinement (Part 11) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tiếp tục hoàn thiện trang chủ Vĩnh Long 360 theo hướng tinh gọn, hiện đại và loại bỏ chi tiết thừa: hiện đại hóa liên kết thẻ vệ tinh Folio I, loại bỏ dữ liệu mồ côi và trùng lặp trên Folios I-III, và tinh gọn nhãn chips thực địa Hero.

**Architecture:** Tinh chỉnh trực tiếp các component ([HomeCuratedShowcase.vue](web-nuxt/components/home/HomeCuratedShowcase.vue), [HomeCulinaryTrail.vue](web-nuxt/components/home/HomeCulinaryTrail.vue), [HomeRiversideStays.vue](web-nuxt/components/home/HomeRiversideStays.vue), [index.vue](web-nuxt/pages/index.vue)), loại bỏ các trường dữ liệu thừa/mồ côi, bỏ gạch chân liên kết thẻ vệ tinh và xóa dấu phân cách thừa trên nhãn gợi ý.

**Tech Stack:** Nuxt 3, Vue 3, Scoped CSS, Vitest, Happy-DOM, Python AST pre-commit checks.

**Spec:** Triết lý "Sâu hơn, đơn giản, không thêm" từ user prompt và Tiêu chuẩn trải nghiệm vi mô R30.

## Global Constraints

- Không thêm bất kỳ component mới hay section cấp cao mới (Zero Scope Inflation).
- Duy trì 5 section cấp cao: `['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation']`.
- Giữ vững ngân sách CSS nén R30.7: trần cứng $\le 194.560\text{ bytes}$ gzipped ($190\text{ kB}$).
- TDD bắt buộc: Viết failing test trước khi sửa mã nguồn; chạy test pass mới commit.
- 0 vi phạm giọng văn R50.2 (`check_content_voice.py`).

---

### Task 1: Hiện Đại Hóa Liên Kết Thẻ Vệ Tinh & Dọn Dẹp Dữ Liệu Thừa (Folio I - HomeCuratedShowcase)

**Files:**
- Modify: `web-nuxt/components/home/HomeCuratedShowcase.vue`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

- [x] **Step 1: Write the failing test**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Bỏ text-decoration underline trên .home-curated-satellite__link và dọn bestTime, highlight trong leadItem**
- [x] **Step 4: Run test to verify it passes**

---

### Task 2: Tinh Gọn Trường Dữ Liệu Thẻ Ẩm Thực (Folio II - HomeCulinaryTrail)

**Files:**
- Modify: `web-nuxt/components/home/HomeCulinaryTrail.vue`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

- [x] **Step 1: Write the failing test**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Lược bỏ guide, venues trùng lặp và chuyển template sang dùng trực tiếp reputableVenue**
- [x] **Step 4: Run test to verify it passes**

---

### Task 3: Dọn Dẹp Dữ Liệu Mồ Côi Thẻ Homestay (Folio III - HomeRiversideStays)

**Files:**
- Modify: `web-nuxt/components/home/HomeRiversideStays.vue`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

- [x] **Step 1: Write the failing test**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Lược bỏ balconyHighlight khỏi CuratedHomestay interface và CURATED_HOMESTAYS**
- [x] **Step 4: Run test to verify it passes**

---

### Task 4: Tinh Gọn Nhãn Chips Thực Địa Hero (Hero Gateway - index.vue)

**Files:**
- Modify: `web-nuxt/pages/index.vue`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

- [x] **Step 1: Write the failing test**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Chuyển "Rẽ lối lẹ:" thành "Rẽ lối lẹ"**
- [x] **Step 4: Run test to verify it passes**

---

### Task 5: Toàn Diện Hóa Kiểm Thử & Xác Minh Ngân Sách CSS R30.7

- [x] **Step 1: Run 24 bộ kiểm thử trang chủ (243 tests pass)**
- [x] **Step 2: Nuxt build & kiểm tra ngân sách CSS gzipped <= 194.560 bytes**
- [x] **Step 3: python scripts/checks/run_hard.py --all sạch 100%**
