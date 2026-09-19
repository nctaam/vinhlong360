> STATUS: completed (2026-09-19)

# Kế Hoạch Hoàn Thiện Giao Diện Trang Chủ: Chiều Sâu Thực Địa & Tinh Giản Phần 3 (Deepen & Simplify Homepage UI Plan - Part 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện sự nhất quán 100% của biểu tượng la bàn (`compass`) cho tọa độ thực địa trên toàn bộ trang chủ (khối Hero Feature Dossier), mở rộng chuẩn số học `tabular-nums` cho toàn bộ các số liệu hotline và thời lượng lịch trình còn sót lại, làm dịu dải scrim trên Folio II (Ẩm thực) và Folio III (Lưu trú) để tăng tỷ lệ lộ ảnh tự nhiên lên $\ge 80\%$, tuyệt đối không thêm section mới, không thêm thư viện ngoài, giữ vững ngân sách CSS nén gzipped $\le 190$ kB (ngưỡng trần $\le 194.560$ bytes).

**Architecture:** 
- Thống nhất vi mô tọa độ: chuyển icon `pin` sang `compass` trên `HomeFeatureDossier.vue` để đồng bộ 100% với Folio I, Folio II, Folio III và Hành trình tiếp nối.
- Tabular numerics toàn diện: đưa `.home-culinary-card__coords`, `.home-stay-card__coords`, `.home-continuation__link-sub` và `.home-hotline-btn__num` vào nhóm selector `tabular-nums` trong `home-nocturne.css`, đồng thời dọn dẹp selector mồ côi `.home-product-lead__name`.
- Làm dịu scrim gradient trên `HomeCulinaryTrail.vue` và `HomeRiversideStays.vue` theo công thức quang học đã áp dụng thành công ở `HomeCuratedShowcase.vue`, giải phóng không gian ảnh món ăn và nhà vườn ven sông.
- Khóa chặt và kiểm định ngân sách R30.7 CSS và 100% test suites trang chủ.

**Tech Stack:** Nuxt 4, Vue 3 (Composition API, `<script setup lang="ts">`), CSS Tokens Tam Vùng, Vitest, `@nuxt/test-utils`.

**Spec:** `docs/standards/bundle-budget.json` (R30.7), `scripts/checks/check_content_voice.py` (R50.2), `scripts/checks/check_doc_status.py` (R60.1), `web-nuxt/tests/home-deep-simplify.test.ts`.

## Global Constraints

- **Section Anatomy Contract:** Giữ nguyên danh sách 5 section hợp đồng: `['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation']`. Tuyệt đối không tạo thêm bất kỳ section cấp cao nào.
- **R30.7 CSS Bundle Budget:** Tổng dung lượng CSS gzipped BẮT BUỘC $\le 190$ kB (ngưỡng trần cứng $\le 194.560$ bytes theo `bundle-budget.json`).
- **R50.2 Content Voice:** Tuyệt đối không sử dụng từ ngữ sáo rỗng bị cấm: *"miền Tây"*, *"sông nước hữu tình"*, *"thiên đường"*, *"hidden gem"*, *"must-see"*, *"không thể bỏ lỡ"*, *"đắm chìm"*, *"hòa mình vào"*, *"điểm đến lý tưởng"*.
- **R60.1 Document Status:** Mọi tệp tài liệu trong `docs/` bắt buộc có dòng `> STATUS: active (YYYY-MM-DD)` trong 10 dòng đầu tiên.
- **Tương phản & Tiếp cận (WCAG 2.2 AAA):** Mọi nút tương tác $\ge 44\times 44\text{px}$, độ tương phản chữ $\ge 7:1$ cho tiêu đề và $\ge 4.5:1$ cho văn bản thường. Focus outline rõ ràng.
- **Tabular Numerics:** Toàn bộ số liệu giá tiền, thứ tự (#01, #02), mốc tháng, số lượng thực địa (1.772 điểm, 16 lịch trình, 2N1Đ, 3N2Đ), số điện thoại hotline và tọa độ thực địa phải sử dụng `font-variant-numeric: tabular-nums`.

---

## Tasks

### Task 1: Thống Nhất Biểu Tượng La Bàn Cho Tọa Độ Thực Địa Hero Feature Dossier (`HomeFeatureDossier.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeFeatureDossier.vue:52-71`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: `HomeFeatureDossier.vue` template (tọa độ thực địa `10.254° N, 105.972° E`)
- Produces: Thay thế icon `pin` bằng icon `compass` cho tọa độ, hoàn tất sự nhất quán 100% của biểu tượng la bàn khám phá trên toàn bộ trang chủ.

- [x] **Step 1: Viết test cho biểu tượng la bàn trên Hero Feature Dossier**

Bổ sung vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 8: Hero Feature Dossier coordinates consistently render compass icon', () => {
    const dossierVue = readFileSync(resolve(__dirname, '../components/home/HomeFeatureDossier.vue'), 'utf8')
    expect(dossierVue).toMatch(/home-feature-dossier__coords[\s\S]*?<IconLine\s+name="compass"/)
  })
```

- [x] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: FAIL vì `HomeFeatureDossier.vue` vẫn đang dùng `name="pin"`.

- [x] **Step 3: Cập nhật `HomeFeatureDossier.vue`**

Trong `web-nuxt/components/home/HomeFeatureDossier.vue`, cập nhật dòng 59 và dòng 68:
```html
        <NuxtLink
          v-if="mapTo"
          :to="mapTo"
          class="home-feature-dossier__coords home-feature-dossier__coords--link"
          :data-geo-coordinates="coordinates || '10.254° N, 105.972° E'"
          :title="`Xem vị trí trên bản đồ (${coordinates || '10.254° N, 105.972° E'})`"
        >
          <IconLine name="compass" aria-hidden="true" />
          <span>{{ coordinates || '10.254° N, 105.972° E' }}</span>
        </NuxtLink>
        <span
          v-else
          class="home-feature-dossier__coords"
          :data-geo-coordinates="coordinates || '10.254° N, 105.972° E'"
          :title="`Tọa độ thực địa: ${coordinates || '10.254° N, 105.972° E'}`"
        >
          <IconLine name="compass" aria-hidden="true" />
          <span>{{ coordinates || '10.254° N, 105.972° E' }}</span>
        </span>
```

- [x] **Step 4: Chạy kiểm thử để xác nhận thành công**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: PASS

- [x] **Step 5: Commit Task 1**

```bash
git add web-nuxt/components/home/HomeFeatureDossier.vue web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "feat(home): unify compass icon for hero feature dossier coordinates"
```

---

### Task 2: Chuẩn Hóa Tabular Numerics Cho Số Hotline, Thời Lượng Lịch Trình & Tọa Độ Còn Lại

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css:50-65`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: `.home-culinary-card__coords`, `.home-stay-card__coords`, `.home-continuation__link-sub`, `.home-hotline-btn__num`
- Produces: Định dạng số dạng bảng `font-variant-numeric: tabular-nums` cho toàn bộ số điện thoại hotline, thời lượng lịch trình (2N1Đ, 3N2Đ) và tọa độ ẩm thực / lưu trú; prune selector mồ côi `.home-product-lead__name`.

- [x] **Step 1: Viết test cho tabular numerics mở rộng**

Bổ sung vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 9: Hotline numbers, itinerary durations, and remaining coordinates enforce tabular numerics', () => {
    expect(nocturneCss).toMatch(/\.home-hotline-btn__num/)
    expect(nocturneCss).toMatch(/\.home-continuation__link-sub/)
    expect(nocturneCss).toMatch(/\.home-culinary-card__coords/)
    expect(nocturneCss).toMatch(/\.home-stay-card__coords/)
    // Verify orphaned product lead name is pruned from heading balance group
    expect(nocturneCss).not.toMatch(/:is\([^)]*\.home-product-lead__name[^)]*\)/)
  })
```

- [x] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: FAIL

- [x] **Step 3: Cập nhật `home-nocturne.css`**

Trong `web-nuxt/assets/css/home-nocturne.css`:
1. Dòng 54: gỡ bỏ `.home-product-lead__name`:
```css
[data-home-pilot="nocturne-b1"] :is(h1, h2, h3, .section-head h2, .home-curated-lead__title, .home-culinary-card__title) {
  text-wrap: balance;
  text-wrap: pretty;
  line-height: var(--leading-snug, 1.35);
}
```
2. Dòng 60: bổ sung các selector vào nhóm `tabular-nums`:
```css
[data-home-pilot="nocturne-b1"] :is(.home-feature-dossier__coords, [data-geo-coordinates], .hero-cognitive-chip, .cm-stat, .hero-terroir-chip, .home-culinary-card__price-badge, .home-culinary-card__rank, .home-culinary-card__coords, .home-stay-card__price, .home-stay-card__coords, .home-curated-lead__coords, .home-curated-satellite__coords, .home-curated-lead__badge, .catalog-aeo-plaque__entry-title, .home-continuation__link-title, .home-continuation__link-sub, .home-hotline-btn__num) {
  font-variant-numeric: tabular-nums;
}
```

- [x] **Step 4: Chạy kiểm thử để xác nhận thành công**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: PASS

- [x] **Step 5: Commit Task 2**

```bash
git add web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "feat(home): expand tabular numerics to hotlines, itinerary duration, and card coordinates"
```

---

### Task 3: Làm Dịu Scrim Trên Folio II (Ẩm Thực) & Folio III (Lưu Trú)

**Files:**
- Modify: `web-nuxt/components/home/HomeCulinaryTrail.vue:280-295`
- Modify: `web-nuxt/components/home/HomeRiversideStays.vue:320-335`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: Scrim overlay trong `HomeCulinaryTrail.vue` và `HomeRiversideStays.vue`
- Produces: Gradient dịu nhẹ (từ mức che phủ đen 0.45 ở 45% giảm xuống transparent ở 28% và 0.35 ở 58%), giải phóng không gian ảnh cho món ăn và quang cảnh lưu trú $\ge 80\%$, giữ nguyên độ tương phản WCAG 2.2 AAA $\ge 7:1$ cho chân thẻ.

- [x] **Step 1: Viết test cho kiểm soát gradient scrim Folio II & III**

Bổ sung vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 10: Culinary trail and riverside stays employ calmed photographic scrims', () => {
    const culinaryVue = readFileSync(resolve(__dirname, '../components/home/HomeCulinaryTrail.vue'), 'utf8')
    const staysVue = readFileSync(resolve(__dirname, '../components/home/HomeRiversideStays.vue'), 'utf8')
    
    // Both must use relaxed transparent mid-stop
    expect(culinaryVue).toMatch(/home-culinary-card__scrim[\s\S]*?transparent 28%/)
    expect(staysVue).toMatch(/home-stay-card__scrim[\s\S]*?transparent 28%/)
  })
```

- [x] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: FAIL

- [x] **Step 3: Cập nhật scrim trong `HomeCulinaryTrail.vue` & `HomeRiversideStays.vue`**

Trong `web-nuxt/components/home/HomeCulinaryTrail.vue`:
```css
/* Bottom Gradient Scrim Overlay */
.home-culinary-card__scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(var(--black-rgb), 0.18) 0%,
    transparent 28%,
    rgba(var(--black-rgb), 0.35) 58%,
    rgba(var(--black-rgb), 0.72) 78%,
    rgba(var(--black-rgb), 0.88) 100%
  );
  pointer-events: none;
  z-index: 1;
}
```

Trong `web-nuxt/components/home/HomeRiversideStays.vue`:
```css
/* Gradient Scrim Overlay */
.home-stay-card__scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(var(--black-rgb), 0.18) 0%,
    transparent 28%,
    rgba(var(--black-rgb), 0.35) 58%,
    rgba(var(--black-rgb), 0.72) 78%,
    rgba(var(--black-rgb), 0.88) 100%
  );
  pointer-events: none;
  z-index: 1;
}
```

- [x] **Step 4: Chạy kiểm thử để xác nhận thành công**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: PASS

- [x] **Step 5: Commit Task 3**

```bash
git add web-nuxt/components/home/HomeCulinaryTrail.vue web-nuxt/components/home/HomeRiversideStays.vue web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "feat(home): calm photographic scrims across culinary trail and riverside stays"
```

---

### Task 4: Khóa Chặt Ngân Sách CSS R30.7 & Xác Thực Toàn Diện Hệ Thống

**Files:**
- Verify: `docs/standards/bundle-budget.json`
- Verify: `scripts/checks/check_bundle.py`
- Verify: `scripts/checks/check_content_voice.py`
- Verify: `scripts/checks/check_doc_status.py`
- Modify: `docs/superpowers/plans/2026-09-19-deepen-simplify-homepage-ui-part-3.md` (check off steps)

**Interfaces:**
- Consumes: Build output của Nuxt
- Produces: CSS gzipped BẮT BUỘC $\le 194.560$ bytes; 100% tests liên quan trang chủ PASS.

- [x] **Step 1: Chạy build và đo lường ngân sách CSS**

Run: `npm --prefix web-nuxt run build`
Run: `$env:PYTHONIOENCODING="utf-8"; python -m scripts.checks.check_bundle`
Expected: `✓ R30.7 bundle budget: đạt` với `total_css_gz_kb <= 190` ($\le 194.560$ bytes).

- [x] **Step 2: Chạy toàn bộ test suites trang chủ**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts tests/home-editorial-e2e.test.ts tests/challenger-homepage-stress.test.ts tests/home-curated-showcase.test.ts tests/home-hero-dossier-polish.test.ts tests/home-decision-category.test.ts`
Expected: 100% PASS

- [x] **Step 3: Kiểm tra giọng điệu biên tập (R50.2) & tình trạng tài liệu (R60.1)**

Run: `python -m scripts.checks.check_content_voice`
Run: `python -m scripts.checks.check_doc_status`
Expected: 0 vi phạm.

- [x] **Step 4: Hoàn tất tài liệu và Commit Task 4**

```bash
git add docs/superpowers/plans/2026-09-19-deepen-simplify-homepage-ui-part-3.md
git commit -m "chore(home): verify R30.7 CSS budget and lock deepen-simplify plan part 3"
```

---

## Execution Choice

1. **Subagent-Driven (Khuyến nghị):** Phân chia từng task độc lập cho subagent thực hiện tuần tự và kiểm soát chất lượng qua từng checkpoint.
2. **Inline Execution:** Thực hiện trực tiếp tuần tự các task trong phiên hiện tại với các trạm kiểm soát (checkpoints) nghiêm ngặt.
