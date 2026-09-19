> STATUS: completed (2026-09-19)

# Kế Hoạch Hoàn Thiện Giao Diện Trang Chủ: Chiều Sâu Thực Địa & Tinh Giản Phần 4 (Deepen & Simplify Homepage UI Plan - Part 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện 100% sự đồng bộ quang học của dải gradient scrim trên toàn bộ trang chủ bằng cách làm dịu thẻ lead di sản Lò gạch Mang Thít (`HomeCuratedShowcase.vue`), bổ sung vi mô định hướng la bàn/mũi tên cho liên kết hành động "Khám phá" (`HomeFeatureDossier.vue`), và tinh gọn các quy tắc CSS mồ côi (`home-nocturne.css`) để mở rộng biên độ an toàn cho ngân sách R30.7 CSS gzipped $\le 190$ kB (ngưỡng trần cứng $\le 194.560$ bytes), tuyệt đối giữ nguyên hợp đồng 5 section và không thêm bất kỳ thư viện ngoài nào.

**Architecture:** 
- Đồng bộ quang học scrim di sản: Cập nhật `.home-curated-lead__scrim` từ dải xám đen nặng nề (0.55 ở 50%, 0.78 ở 65%, 0.92 ở 85%) sang dải gradient êm dịu quang học (`transparent 28%`, `0.35 58%`, `0.72 78%`, `0.88 100%`). Giải phóng $\ge 75\%$ diện tích ảnh chụp vòm gốm đỏ Mang Thít nguyên bản dưới ánh chiều Cổ Chiên mà vẫn giữ vững độ tương phản WCAG 2.2 AAA $\ge 7:1$ cho chân thẻ.
- Vi mô định hướng hành trình: Bổ sung `<IconLine name="arrow-right" class="home-feature-dossier__action-arrow" aria-hidden="true" />` vào nút `Khám phá` trên `HomeFeatureDossier.vue`, tạo độ nhạy vi mô nhất quán với thẻ vệ tinh Folio I, thẻ ẩm thực Folio II, thẻ homestay Folio III và liên kết hành trình tiếp nối.
- Tinh giản CSS & Nới rộng ngân sách R30.7: Dọn dẹp các selector mồ côi của product lead trong `home-nocturne.css` (vốn không còn rendered trên `index.vue`), giữ lại quy tắc active micro-interaction cần thiết (`.home-product-lead__media:active { transform: scale(0.99); }`) để tiết kiệm hàng trăm bytes và gia tăng khoảng đệm an toàn dưới trần $194.560$ bytes.
- Khóa chặt và kiểm định 100% bộ kiểm thử trang chủ (118 tests) và cổng chất lượng R50.2 / R60.1.

**Tech Stack:** Nuxt 4, Vue 3 (Composition API, `<script setup lang="ts">`), CSS Tokens Tam Vùng, Vitest, `@nuxt/test-utils`.

**Spec:** `docs/standards/bundle-budget.json` (R30.7), `scripts/checks/check_content_voice.py` (R50.2), `scripts/checks/check_doc_status.py` (R60.1), `web-nuxt/tests/home-deep-simplify.test.ts`.

## Global Constraints

- **Section Anatomy Contract:** Duy trì nghiêm ngặt 5 section hợp đồng cấp cao: `['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation']`. Tuyệt đối không thêm section mới, không thêm component mồ côi.
- **R30.7 CSS Bundle Budget:** Tổng dung lượng CSS gzipped BẮT BUỘC $\le 190$ kB (ngưỡng trần cứng $\le 194.560$ bytes theo `bundle-budget.json`).
- **R50.2 Content Voice:** Tuyệt đối không sử dụng từ ngữ sáo rỗng bị cấm: *"miền Tây"*, *"sông nước hữu tình"*, *"thiên đường"*, *"hidden gem"*, *"must-see"*, *"không thể bỏ lỡ"*, *"đắm chìm"*, *"hòa mình vào"*, *"điểm đến lý tưởng"*.
- **R60.1 Document Status:** Mọi tệp tài liệu trong `docs/` bắt buộc có dòng `> STATUS: active (YYYY-MM-DD)` hoặc `> STATUS: completed (YYYY-MM-DD)` trong 10 dòng đầu tiên.
- **Tương phản & Tiếp cận (WCAG 2.2 AAA):** Mọi nút tương tác $\ge 44\times 44\text{px}$, độ tương phản chữ $\ge 7:1$ cho tiêu đề và $\ge 4.5:1$ cho văn bản thường. Focus outline rõ ràng $\ge 2\text{px}$.
- **Tabular Numerics:** Toàn bộ số liệu giá tiền, thứ tự (#01, #02), mốc tháng, số lượng thực địa, hotline và tọa độ thực địa phải sử dụng `font-variant-numeric: tabular-nums`.

---

## Tasks

### Task 1: Làm Dịu Scrim Gradient Trên Thẻ Di Sản Đầu Tàu (`HomeCuratedShowcase.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeCuratedShowcase.vue:386-399`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: Scrim overlay `.home-curated-lead__scrim` trong `HomeCuratedShowcase.vue`
- Produces: Gradient quang học êm dịu đồng nhất với các vệ tinh Folio I, Folio II và Folio III:
  `linear-gradient(180deg, rgba(var(--black-rgb), 0.20) 0%, transparent 28%, rgba(var(--black-rgb), 0.35) 58%, rgba(var(--black-rgb), 0.72) 78%, rgba(var(--black-rgb), 0.88) 100%)`.

- [x] **Step 1: Viết test cho kiểm soát gradient scrim của thẻ di sản đầu tàu**

Bổ sung vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 11: Curated lead heritage card employs calmed optical photographic scrim', () => {
    const showcaseVue = readFileSync(resolve(__dirname, '../components/home/HomeCuratedShowcase.vue'), 'utf8')
    // Must use relaxed transparent mid-stop instead of heavy 0.55 opacity at 50%
    expect(showcaseVue).toMatch(/home-curated-lead__scrim[\s\S]*?transparent 28%/)
    expect(showcaseVue).not.toMatch(/rgba\(var\(--black-rgb\),\s*0\.55\)\s*50%/)
  })
```

- [x] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: FAIL vì `HomeCuratedShowcase.vue` vẫn đang dùng `rgba(var(--black-rgb), 0.55) 50%`.

- [x] **Step 3: Cập nhật `.home-curated-lead__scrim` trong `HomeCuratedShowcase.vue`**

Thay thế khối scrim tại dòng 386-399 của `web-nuxt/components/home/HomeCuratedShowcase.vue`:
```css
.home-curated-lead__scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(var(--black-rgb), 0.20) 0%,
    transparent 28%,
    rgba(var(--black-rgb), 0.35) 58%,
    rgba(var(--black-rgb), 0.72) 78%,
    rgba(var(--black-rgb), 0.88) 100%
  );
  pointer-events: none;
}
```

- [x] **Step 4: Chạy kiểm thử để xác nhận thành công**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: PASS

- [x] **Step 5: Commit Task 1**

```bash
git add web-nuxt/components/home/HomeCuratedShowcase.vue web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "feat(home): calm optical photographic scrim on curated heritage lead showcase"
```

---

### Task 2: Đồng Bộ Biểu Tượng Định Hướng Cho Nút Khám Phá (`HomeFeatureDossier.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeFeatureDossier.vue:81-88`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: Thẻ `NuxtLink` nút "Khám phá" trong slot `#action` của `HomeFeatureDossier.vue`
- Produces: Bổ sung biểu tượng `<IconLine name="arrow-right" class="home-feature-dossier__action-arrow" aria-hidden="true" />` cho nút `Khám phá`, tạo affordance định hướng vi mô đồng nhất với các thẻ khác.

- [x] **Step 1: Viết test cho biểu tượng định hướng mũi tên trên nút Khám phá**

Bổ sung vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 12: Hero Feature Dossier action link consistently renders arrow-right icon', () => {
    const dossierVue = readFileSync(resolve(__dirname, '../components/home/HomeFeatureDossier.vue'), 'utf8')
    expect(dossierVue).toMatch(/home-feature-dossier__action[\s\S]*?Khám phá[\s\S]*?<IconLine\s+name="arrow-right"/)
  })
```

- [x] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: FAIL vì `HomeFeatureDossier.vue` chưa có `<IconLine name="arrow-right" />` bên cạnh chữ `Khám phá`.

- [x] **Step 3: Cập nhật template `HomeFeatureDossier.vue`**

Tại dòng 81-88 của `web-nuxt/components/home/HomeFeatureDossier.vue`:
```html
        <NuxtLink
          :to="detailTo"
          class="home-feature-dossier__action"
          data-home-feature-action
          data-color-role="action-secondary"
        >
          <span>Khám phá</span>
          <IconLine name="arrow-right" class="home-feature-dossier__action-arrow" aria-hidden="true" />
        </NuxtLink>
```

- [x] **Step 4: Chạy kiểm thử để xác nhận thành công**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: PASS

- [x] **Step 5: Commit Task 2**

```bash
git add web-nuxt/components/home/HomeFeatureDossier.vue web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "feat(home): unify directional arrow icon on hero feature dossier action"
```

---

### Task 3: Tinh Giản CSS Mồ Côi Trong `home-nocturne.css` Để Nới Rộng Headroom R30.7

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css:1415-1625`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: Các selector `[data-home-pilot="nocturne-b1"] .home-product-lead...` trong `home-nocturne.css`
- Produces: Loại bỏ các khối CSS thừa không còn phục vụ trang chủ (giữ lại rule active interaction `transform: scale(0.99)` theo hợp đồng `home-layout-asymmetry.test.ts`), thu hồi ~1 kB CSS thô và mở rộng khoảng đệm ngân sách R30.7.

- [x] **Step 1: Viết test xác nhận việc tinh giản dead CSS và bảo toàn rule active**

Bổ sung vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 13: Orphaned product lead layout rules pruned from home-nocturne.css while preserving required tactile scale', () => {
    // Media active scale rule is required by home-layout-asymmetry.test.ts
    expect(nocturneCss).toMatch(/\.home-product-lead__media:active\s*\{[\s\S]*?transform:\s*scale\(0\.99\)/)
    // Orphaned matte and grid body rules should be pruned to maintain strict CSS headroom
    expect(nocturneCss).not.toMatch(/\[data-home-pilot="nocturne-b1"\]\s+\.home-product-lead__matte\s*\{/)
  })
```

- [x] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: FAIL vì selector `.home-product-lead__matte` vẫn còn tồn tại trong `home-nocturne.css`.

- [x] **Step 3: Tinh giản selector trong `web-nuxt/assets/css/home-nocturne.css`**

Rút gọn khối `.home-product-lead` tại dòng 1415-1625, chỉ giữ lại các rule tối thiểu cần thiết cho tương thích test và component:
```css
/* Tối ưu hóa: Giữ lại micro-interaction tactile active cho test hợp đồng thị giác */
[data-home-pilot="nocturne-b1"] .home-product-lead__media:active {
  transform: scale(0.99);
}
```

- [x] **Step 4: Chạy kiểm thử để xác nhận thành công**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts tests/home-layout-asymmetry.test.ts`
Expected: PASS cả hai test suites!

- [x] **Step 5: Commit Task 3**

```bash
git add web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "chore(home): prune orphaned product lead CSS rules to expand R30.7 headroom"
```

---

### Task 4: Kiểm Định Toàn Diện Ngân Sách R30.7 CSS, Bộ Test Suite & Khóa Kế Hoạch Phần 4

**Files:**
- Verify: `docs/standards/bundle-budget.json`
- Verify: `scripts/checks/check_bundle.py`
- Verify: `scripts/checks/check_content_voice.py`
- Verify: `scripts/checks/check_doc_status.py`
- Modify: `docs/superpowers/plans/2026-09-19-deepen-simplify-homepage-ui-part-4.md` (check off steps)

**Interfaces:**
- Consumes: Nuxt production build
- Produces: CSS gzipped BẮT BUỘC $\le 194.560$ bytes (với headroom mở rộng $> 140$ bytes), 118/118 tests pass, 0 vi phạm giọng điệu R50.2, 0 vi phạm trạng thái tài liệu R60.1.

- [x] **Step 1: Chạy build Nuxt và đo lường ngân sách CSS**

Run: `npm --prefix web-nuxt run build`
Run: `$env:PYTHONIOENCODING="utf-8"; python -m scripts.checks.check_bundle`
Expected: `✓ R30.7 bundle budget: đạt` với `total_css_gz_kb <= 190` ($\le 194.560$ bytes).

- [x] **Step 2: Chạy toàn bộ test suites trang chủ**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts tests/home-editorial-e2e.test.ts tests/challenger-homepage-stress.test.ts tests/home-curated-showcase.test.ts tests/home-hero-dossier-polish.test.ts tests/home-decision-category.test.ts tests/home-layout-asymmetry.test.ts`
Expected: 100% PASS (118 tests).

- [x] **Step 3: Kiểm tra giọng điệu biên tập (R50.2) & tình trạng tài liệu (R60.1)**

Run: `$env:PYTHONIOENCODING="utf-8"; python -m scripts.checks.check_content_voice`
Run: `$env:PYTHONIOENCODING="utf-8"; python -m scripts.checks.check_doc_status`
Expected: 0 vi phạm.

- [x] **Step 4: Hoàn tất tài liệu và Commit Task 4**

```bash
git add docs/superpowers/plans/2026-09-19-deepen-simplify-homepage-ui-part-4.md
git commit -m "chore(home): verify R30.7 CSS budget and lock deepen-simplify plan part 4"
```
