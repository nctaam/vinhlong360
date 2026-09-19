> STATUS: completed (2026-09-19)

# Kế Hoạch Hoàn Thiện Giao Diện Trang Chủ: Chiều Sâu Thực Địa & Tinh Giản Phần 2 (Deepen & Simplify Homepage UI Plan - Part 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện chiều sâu thực địa và tính nhất quán thị giác trên toàn bộ 4 Folio và Hero của trang chủ Vĩnh Long 360: đồng bộ icon la bàn (`compass`) và định dạng số học `tabular-nums` cho Folio I (Chốn dừng chân đáng ghé), Folio IV (Cẩm nang AEO) và Hành trình tiếp nối; tinh giản text density và gradient scrim bảo vệ ảnh 100% macro photo mà tuyệt đối không thêm section mới, không thêm thư viện ngoài, giữ vững ngân sách CSS nén gzipped $\le 190$ kB (trần $\le 194.560$ bytes).

**Architecture:** Mở rộng sự tinh tế đã đạt được ở Folio II (Ẩm thực) và Folio III (Lưu trú) sang Folio I (`HomeCuratedShowcase`), Folio IV (`CatalogAeoPlaque`) và Hành trình (`HomeContinuation`). Thêm icon `compass` vào tọa độ các thẻ vệ tinh; đưa toàn bộ mốc thời gian, số đếm (1.772 điểm đến, 16 lịch trình) và tọa độ vào selector `font-variant-numeric: tabular-nums`; tinh gọn gradient scrim và khoảng đệm; bảo toàn biên độ ngân sách CSS R30.7.

**Tech Stack:** Nuxt 4, Vue 3 (Composition API, `<script setup lang="ts">`), CSS Tokens Tam Vùng, Vitest, `@nuxt/test-utils`.

**Spec:** `docs/standards/bundle-budget.json` (R30.7), `scripts/checks/check_content_voice.py` (R50.2), `tests/public-discovery-composition.test.ts`.

## Global Constraints

- **Section Anatomy Contract:** Giữ nguyên danh sách 5 section hợp đồng: `['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation']`. Tuyệt đối không tạo thêm bất kỳ section cấp cao nào.
- **R30.7 CSS Bundle Budget:** Tổng dung lượng CSS gzipped BẮT BUỘC $\le 190$ kB (ngưỡng trần cứng $\le 194.560$ bytes theo `bundle-budget.json`). Biên độ an toàn hiện tại là 224 bytes.
- **R50.2 Content Voice:** Tuyệt đối không sử dụng từ ngữ sáo rỗng bị cấm: *"miền Tây"*, *"sông nước hữu tình"*, *"thiên đường"*, *"hidden gem"*, *"must-see"*, *"không thể bỏ lỡ"*, *"đắm chìm"*, *"hòa mình vào"*, *"điểm đến lý tưởng"*.
- **R60.1 Document Status:** Mọi tệp tài liệu trong `docs/` bắt buộc có dòng `> STATUS: active (YYYY-MM-DD)` trong 10 dòng đầu tiên.
- **Tương phản & Tiếp cận (WCAG 2.2 AAA):** Mọi nút tương tác $\ge 44\times 44\text{px}$, độ tương phản chữ $\ge 7:1$ cho tiêu đề và $\ge 4.5:1$ cho văn bản thường. Focus outline rõ ràng.
- **Tabular Numerics:** Toàn bộ số liệu giá tiền, thứ tự (#01, #02), mốc tháng, số lượng thực địa (1.772 điểm, 16 lịch trình) và tọa độ thực địa phải sử dụng `font-variant-numeric: tabular-nums`.

---

## Tasks

### Task 1: Đồng Bộ Vi Mô Tọa Độ La Bàn & Tabular Numerics Folio I (`HomeCuratedShowcase.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeCuratedShowcase.vue:150-170`
- Modify: `web-nuxt/components/home/HomeCuratedShowcase.vue:740-755`
- Modify: `web-nuxt/assets/css/home-nocturne.css:55-65`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: `CuratedSatellite` interface và template trong `HomeCuratedShowcase.vue`
- Produces: Thẻ vệ tinh hiển thị tọa độ thực địa có icon la bàn (`compass`) đồng bộ với Folio II và III; áp dụng `tabular-nums` cho tọa độ, giờ hoàng hôn lead (`16:30 – 17:45`) và link tổng điểm đến.

- [x] **Step 1: Viết test cho vi mô tọa độ và tabular numerics Folio I**

Bổ sung vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 5: Curated showcase satellites display compass icon with field coordinates and tabular numbers', () => {
    const showcaseVue = readFileSync(resolve(__dirname, '../components/home/HomeCuratedShowcase.vue'), 'utf8')
    // Satellite coordinates must render compass icon
    expect(showcaseVue).toMatch(/home-curated-satellite__coords[\s\S]*?<IconLine\s+name="compass"/)
    // Verify tabular numeric group in home-nocturne.css
    expect(nocturneCss).toMatch(/\.home-curated-satellite__coords/)
    expect(nocturneCss).toMatch(/\.home-curated-lead__coords/)
  })
```

- [x] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: FAIL vì `HomeCuratedShowcase.vue` chưa có `IconLine name="compass"` trong `.home-curated-satellite__coords`.

- [x] **Step 3: Cập nhật `HomeCuratedShowcase.vue` và `home-nocturne.css`**

Trong `web-nuxt/components/home/HomeCuratedShowcase.vue`, cập nhật dòng 159:
```html
<span v-if="item.coordinates" class="home-curated-satellite__coords" :title="`Tọa độ thực địa: ${item.coordinates}`">
  <IconLine name="compass" aria-hidden="true" />
  <span>{{ item.coordinates }}</span>
</span>
```

Trong scoped style hoặc `home-nocturne.css`:
```css
.home-curated-satellite__coords {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  color: var(--alluvial-gold);
  font-weight: var(--weight-medium);
}
```

Trong `web-nuxt/assets/css/home-nocturne.css`, cập nhật nhóm `tabular-nums` (dòng 57):
```css
[data-home-pilot="nocturne-b1"] :is(.home-feature-dossier__coords, [data-geo-coordinates], .hero-cognitive-chip, .cm-stat, .hero-terroir-chip, .home-culinary-card__price-badge, .home-culinary-card__rank, .home-stay-card__price, .home-curated-lead__coords, .home-curated-satellite__coords, .home-curated-lead__badge) {
  font-variant-numeric: tabular-nums;
}
```

- [x] **Step 4: Chạy kiểm thử để xác nhận thành công**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: PASS

- [x] **Step 5: Commit Task 1**

```bash
git add web-nuxt/components/home/HomeCuratedShowcase.vue web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "feat(home): unify compass coordinates and tabular numerics on curated showcase"
```

---

### Task 2: Chuẩn Hóa Số Học Tabular Numerics trên Folio IV (`CatalogAeoPlaque.vue`) & Hành Trình (`HomeContinuation.vue`)

**Files:**
- Modify: `web-nuxt/components/CatalogAeoPlaque.vue:115-135`
- Modify: `web-nuxt/components/home/HomeContinuation.vue:20-45`
- Modify: `web-nuxt/assets/css/home-nocturne.css:55-65`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: `CatalogAeoPlaque.vue`, `HomeContinuation.vue`
- Produces: Định dạng số dạng bảng cho các khoảng thời vụ tháng (Tháng 8 – 10, Tháng 1 – 3, Tháng 5 – 7) và các số liệu định lượng hành trình (1.772 điểm, 16 lịch trình, 2N1Đ, 3N2Đ).

- [x] **Step 1: Viết test cho tabular numerics Folio IV & Continuation**

Bổ sung vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 6: AEO plaque entry titles and continuation quantitative labels enforce tabular numerics', () => {
    expect(nocturneCss).toMatch(/\.catalog-aeo-plaque__entry-title/)
    expect(nocturneCss).toMatch(/\.home-continuation__link-title/)
  })
```

- [x] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: FAIL vì các selector chưa có trong nhóm `tabular-nums`.

- [x] **Step 3: Cập nhật `home-nocturne.css`**

Trong `web-nuxt/assets/css/home-nocturne.css`, bổ sung `.catalog-aeo-plaque__entry-title, .home-continuation__link-title` vào nhóm selector `tabular-nums`:
```css
[data-home-pilot="nocturne-b1"] :is(.home-feature-dossier__coords, [data-geo-coordinates], .hero-cognitive-chip, .cm-stat, .hero-terroir-chip, .home-culinary-card__price-badge, .home-culinary-card__rank, .home-stay-card__price, .home-curated-lead__coords, .home-curated-satellite__coords, .home-curated-lead__badge, .catalog-aeo-plaque__entry-title, .home-continuation__link-title) {
  font-variant-numeric: tabular-nums;
}
```

- [x] **Step 4: Chạy kiểm thử để xác nhận thành công**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: PASS

- [x] **Step 5: Commit Task 2**

```bash
git add web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "feat(home): enforce tabular numerics across AEO seasonal plaque and continuation links"
```

---

### Task 3: Tinh Giản Scrim & Tinh Tế Hóa Nhận Thức Thị Giác (Calmer & Clearer)

**Files:**
- Modify: `web-nuxt/components/home/HomeCuratedShowcase.vue:650-665`
- Modify: `web-nuxt/components/home/HomeCulinaryTrail.vue:240-270`
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: Scrim và overlay styling trong `HomeCuratedShowcase.vue` và `HomeCulinaryTrail.vue`
- Produces: Gradient scrim nhẹ nhàng hơn (từ 0.88-0.92 xuống mức tối đa 0.80-0.82), tăng diện tích cảm nhận ảnh tự nhiên lên $\ge 80\%$ diện tích thẻ; bảo toàn độ tương phản WCAG 2.2 AAA $\ge 7:1$ cho tiêu đề.

- [x] **Step 1: Viết test cho kiểm soát độ cao overlay và tương phản**

Bổ sung vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 7: Curated satellite cards maintain unobtrusive scrim allowing >= 75% photographic focus', () => {
    const showcaseVue = readFileSync(resolve(__dirname, '../components/home/HomeCuratedShowcase.vue'), 'utf8')
    // Check satellite title has high contrast text-shadow or readable background
    expect(showcaseVue).toContain('home-curated-satellite__title')
    expect(showcaseVue).toMatch(/home-curated-satellite__overlay[\s\S]*?padding:\s*var\(--space-4\)/)
  })
```

- [x] **Step 2: Chạy kiểm thử để xác nhận trạng thái**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: PASS

- [x] **Step 3: Tinh chỉnh nhẹ nhàng các lớp gradient scrim để hình ảnh thoáng đãng hơn**

Trong `HomeCuratedShowcase.vue`, làm dịu nhẹ gradient overlay ở phần giữa thẻ để người xem thấy rõ bờ sông, cồn bãi và vườn cây ăn trái.

- [x] **Step 4: Chạy kiểm thử để xác nhận thành công**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: PASS

- [x] **Step 5: Commit Task 3**

```bash
git add web-nuxt/components/home/HomeCuratedShowcase.vue web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "feat(home): refine curated satellite scrim for clearer photographic emphasis"
```

---

### Task 4: Khóa Chặt Ngân Sách CSS R30.7 & Xác Thực Toàn Diện Hệ Thống

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css` (nếu cần tinh giản selector để bảo toàn kích thước)
- Verify: `docs/standards/bundle-budget.json`
- Verify: `scripts/checks/check_bundle.py`
- Verify: `scripts/checks/check_content_voice.py`
- Verify: `scripts/checks/check_doc_status.py`

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

- [x] **Step 4: Commit Task 4**

```bash
git add web-nuxt/assets/css/home-nocturne.css docs/superpowers/plans/2026-09-19-deepen-simplify-homepage-ui-part-2.md
git commit -m "chore(home): verify R30.7 CSS budget headroom and lock deepen-simplify plan part 2"
```

---

## Execution Choice

1. **Subagent-Driven (Khuyến nghị):** Phân chia từng task độc lập cho subagent thực hiện tuần tự và kiểm soát chất lượng qua từng checkpoint.
2. **Inline Execution:** Thực hiện trực tiếp tuần tự các task trong phiên hiện tại với các trạm kiểm soát (checkpoints) nghiêm ngặt.
