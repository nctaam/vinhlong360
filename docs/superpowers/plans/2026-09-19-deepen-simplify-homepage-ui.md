> STATUS: active (2026-09-19)

# Kế Hoạch Hoàn Thiện Giao Diện Trang Chủ: Chiều Sâu Thực Địa & Tinh Giản Tối Đa (Deepen & Simplify Homepage UI Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng cao chiều sâu văn hóa bản địa (tọa độ thực địa cù lao, vi mô địa lý ẩm thực & homestay chuẩn ASEAN, chuẩn hóa tabular-nums) và tinh giản triệt để nhận thức thị giác trên trang chủ Vĩnh Long 360 mà tuyệt đối không thêm section mới, không thêm thư viện ngoài, bảo toàn nghiêm ngặt ngân sách CSS nén gzipped $\le 190$ kB (trần $\le 194.560$ bytes).

**Architecture:** Giữ nguyên vẹn hợp đồng cấu trúc 5 section (`context`, `editorial-lead`, `quick-decisions`, `signals`, `journey-continuation`). Tinh chế vi mô địa lý bằng cách tích hợp tọa độ thực địa (`coordinates`) kèm biểu tượng la bàn (`compass`) vào `HomeCulinaryTrail` và `HomeRiversideStays`; tinh giản câu chữ Hero thành lời đề từ di sản đọng vị; tối ưu khoảng đệm và gradient scrim để 100% hình ảnh macro nổi bật; tinh gọn CSS để duy trì gzipped bytes $\le 194.560$ bytes.

**Tech Stack:** Nuxt 4, Vue 3 (Composition API, `<script setup lang="ts">`), CSS Tokens Tam Vùng, Vitest, `@nuxt/test-utils`.

**Spec:** `docs/standards/bundle-budget.json` (R30.7), `scripts/checks/check_content_voice.py` (R50.2), `tests/public-discovery-composition.test.ts`.

## Global Constraints

- **Section Anatomy Contract:** Giữ nguyên danh sách 5 section hợp đồng: `['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation']`. Không tạo thêm bất kỳ section cấp cao nào.
- **R30.7 CSS Bundle Budget:** Tổng dung lượng CSS gzipped BẮT BUỘC $\le 190$ kB (ngưỡng trần cứng $\le 194.560$ bytes theo `bundle-budget.json`).
- **R50.2 Content Voice:** Tuyệt đối không sử dụng từ ngữ sáo rỗng bị cấm: *"miền Tây"*, *"sông nước hữu tình"*, *"thiên đường"*, *"hidden gem"*, *"must-see"*, *"không thể bỏ lỡ"*, *"đắm chìm"*, *"hòa mình vào"*, *"điểm đến lý tưởng"*.
- **R60.1 Document Status:** Mọi tệp tài liệu trong `docs/` bắt buộc có dòng `> STATUS: active (YYYY-MM-DD)` trong 10 dòng đầu tiên.
- **Tương phản & Tiếp cận (WCAG 2.2 AAA):** Mọi nút tương tác $\ge 44\times 44\text{px}$, độ tương phản chữ $\ge 7:1$ cho tiêu đề và $\ge 4.5:1$ cho văn bản thường. Focus outline rõ ràng.
- **Tabular Numerics:** Toàn bộ số liệu giá tiền, thứ tự (#01, #02), và tọa độ thực địa phải sử dụng `font-variant-numeric: tabular-nums`.

---

## Tasks

### Task 1: Tinh Luyện Khí Chất Hero & Chuẩn Hóa Lời Đề Từ Di Sản

**Files:**
- Modify: `web-nuxt/pages/index.vue:28-68`
- Modify: `web-nuxt/assets/css/home-nocturne.css:50-80`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: `pages/index.vue`, `assets/css/home-nocturne.css`
- Produces: Lời đề từ di sản đọng vị, chips "Rẽ lối lẹ" tinh tế, chuẩn hóa tabular-nums cho toàn bộ nhãn số liệu Hero.

- [ ] **Step 1: Viết bài kiểm thử cho Task 1 trong test suite mới**

```typescript
// web-nuxt/tests/home-deep-simplify.test.ts
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Deep & Simple Homepage UI Refinements', () => {
  const indexVue = readFileSync(resolve(__dirname, '../pages/index.vue'), 'utf8')
  const nocturneCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')

  it('Task 1: Hero subtitle uses authentic poetic heritage phrasing without filler words', () => {
    expect(indexVue).toContain('Hành trình di sản cù lao, làng gốm trăm năm và vị ngọt cây trái giữa đôi bờ Cổ Chiên.')
    expect(indexVue).not.toContain('Tìm điểm đến, món ngon, lễ hội và lịch trình phù hợp cho chuyến về xứ cù lao Vĩnh Long hôm nay.')
    // Verify absence of banned voice words
    expect(indexVue).not.toMatch(/miền Tây|sông nước hữu tình|thiên đường|hidden gem|must-see|không thể bỏ lỡ|đắm chìm|hòa mình vào|điểm đến lý tưởng/)
  })

  it('Task 1: Hero terroir chips and cognitive chips enforce tabular-nums numeric styling', () => {
    expect(nocturneCss).toMatch(/\.hero-cognitive-chip[^{]*\{[^}]*font-variant-numeric:\s*tabular-nums/)
  })
})
```

- [ ] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: FAIL với assertion lỗi vì subtitle cũ vẫn đang tồn tại.

- [ ] **Step 3: Cập nhật `pages/index.vue` và `assets/css/home-nocturne.css`**

Trong `web-nuxt/pages/index.vue`, cập nhật dòng 30:
```html
<p class="hero-sub">{{ ss('homepage.hero_subtitle', 'Hành trình di sản cù lao, làng gốm trăm năm và vị ngọt cây trái giữa đôi bờ Cổ Chiên.') }}</p>
```

Trong `web-nuxt/assets/css/home-nocturne.css`, mở rộng nhóm selector `tabular-nums` tại dòng 60:
```css
[data-home-pilot="nocturne-b1"] :is(.home-feature-dossier__coords, .home-context-line__time, [data-geo-coordinates], .hero-cognitive-chip, .cm-stat, .hero-terroir-chip) {
  font-variant-numeric: tabular-nums;
}
```

- [ ] **Step 4: Chạy kiểm thử để xác nhận thành công**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: PASS

- [ ] **Step 5: Commit Task 1**

```bash
git add web-nuxt/pages/index.vue web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "feat(home): refine hero editorial tagline and enforce tabular numerics"
```

---

### Task 2: Khảo Cứu Thực Địa & Chuẩn Hóa Số Liệu trên Folio Ẩm Thực (`HomeCulinaryTrail.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeCulinaryTrail.vue:40-140`
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: `CulinaryDish` interface trong `HomeCulinaryTrail.vue`
- Produces: Thẻ món ăn có tọa độ thực địa cù lao/bến sông kèm icon `compass`, tabular-nums cho giá tiền và số thứ tự, giảm chiều cao text overlay $\le 25\%$ để ảnh chiếm vị trí chủ đạo.

- [ ] **Step 1: Viết test cho tọa độ thực địa và tabular-nums ẩm thực**

Bổ sung vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 2: Culinary trail dishes display field coordinates and tabular prices', () => {
    const culinaryVue = readFileSync(resolve(__dirname, '../components/home/HomeCulinaryTrail.vue'), 'utf8')
    expect(culinaryVue).toContain('10°17\'N · 105°59\'E') // Cù lao An Bình
    expect(culinaryVue).toContain('10°07\'N · 106°11\'E') // Cù lao Dài
    expect(culinaryVue).toContain('home-culinary-card__coords')
    expect(culinaryVue).toContain('home-culinary-card__price-badge')
    // Check tabular numeric styling in CSS
    expect(nocturneCss).toMatch(/\.home-culinary-card__price-badge[^{]*\{[^}]*font-variant-numeric:\s*tabular-nums/)
  })
```

- [ ] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: FAIL vì `HomeCulinaryTrail.vue` chưa có `home-culinary-card__coords`.

- [ ] **Step 3: Cập nhật `HomeCulinaryTrail.vue` và `home-nocturne.css`**

Trong `web-nuxt/components/home/HomeCulinaryTrail.vue`:
1. Mở rộng interface:
```typescript
interface CulinaryDish {
  readonly id: string
  readonly name: string
  readonly terroir: string
  readonly badge: string
  readonly origin: string
  readonly guide: string
  readonly reputableVenue: string
  readonly venues: string
  readonly priceRange: string
  readonly coverSrc: string
  readonly to: string
  readonly mapTo: string
  readonly coordinates: string
}
```
2. Thêm thuộc tính `coordinates` cho từng món trong `SIGNATURE_DISHES`:
- Cá tai tượng chiên xù: `coordinates: "10°17'N · 105°59'E"`
- Bánh xèo hến Cổ Chiên: `coordinates: "10°07'N · 106°11'E"`
- Khoai lang Bình Tân: `coordinates: "10°05'N · 105°49'E"`
- Lẩu cua đồng cù lao: `coordinates: "10°16'N · 105°58'E"`
- Cam sành Tam Bình: `coordinates: "10°03'N · 106°01'E"`
3. Hiển thị tọa độ trong template:
```html
<div class="home-culinary-card__venue-pill">
  <IconLine name="pin" aria-hidden="true" />
  <span>{{ dish.reputableVenue || dish.venues }}</span>
  <span v-if="dish.coordinates" class="home-culinary-card__coords" :title="`Tọa độ thực địa: ${dish.coordinates}`">
    <span class="home-culinary-card__coords-sep" aria-hidden="true">·</span>
    <IconLine name="compass" aria-hidden="true" />
    <span>{{ dish.coordinates }}</span>
  </span>
</div>
```

Trong `web-nuxt/assets/css/home-nocturne.css`:
```css
[data-home-pilot="nocturne-b1"] :is(.home-culinary-card__price-badge, .home-culinary-card__rank, .home-culinary-card__coords) {
  font-variant-numeric: tabular-nums;
}
.home-culinary-card__coords {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 0.72rem;
  opacity: 0.85;
}
.home-culinary-card__coords-sep {
  margin: 0 4px;
  opacity: 0.5;
}
```

- [ ] **Step 4: Chạy kiểm thử để xác nhận thành công**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: PASS

- [ ] **Step 5: Commit Task 2**

```bash
git add web-nuxt/components/home/HomeCulinaryTrail.vue web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "feat(home): add authentic fieldwork coordinates and tabular pricing to culinary trail"
```

---

### Task 3: Tinh Tế Hóa & Tinh Giản Chi Tiết trên Folio Lưu Trú Ven Sông (`HomeRiversideStays.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeRiversideStays.vue:60-190`
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: `CuratedHomestay` interface trong `HomeRiversideStays.vue`
- Produces: Thẻ homestay hiển thị tọa độ ven sông cù lao, tiện ích (perks) sắp xếp inline thanh thoát, giá phòng định dạng tabular-nums.

- [ ] **Step 1: Viết test cho tọa độ homestay và tối ưu layout**

Bổ sung vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 3: Riverside homestays display field coordinates and streamlined metadata', () => {
    const staysVue = readFileSync(resolve(__dirname, '../components/home/HomeRiversideStays.vue'), 'utf8')
    expect(staysVue).toContain('10°17\'N · 105°59\'E') // Út Trinh
    expect(staysVue).toContain('10°05\'N · 105°49\'E') // Bình Minh
    expect(staysVue).toContain('10°16\'N · 105°59\'E') // Ba Linh
    expect(staysVue).toContain('home-stay-card__coords')
    // Check tabular numeric styling in CSS
    expect(nocturneCss).toMatch(/\.home-stay-card__price[^{]*\{[^}]*font-variant-numeric:\s*tabular-nums/)
  })
```

- [ ] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: FAIL vì `HomeRiversideStays.vue` chưa có `home-stay-card__coords`.

- [ ] **Step 3: Cập nhật `HomeRiversideStays.vue` và `home-nocturne.css`**

Trong `web-nuxt/components/home/HomeRiversideStays.vue`:
1. Mở rộng interface `CuratedHomestay` bổ sung `readonly coordinates: string`.
2. Bổ sung tọa độ cho `CURATED_HOMESTAYS`:
- Út Trinh: `coordinates: "10°17'N · 105°59'E"`
- Mekong Riverside: `coordinates: "10°05'N · 105°49'E"`
- Ba Linh: `coordinates: "10°16'N · 105°59'E"`
3. Cập nhật template `.home-stay-card__meta`:
```html
<div class="home-stay-card__meta">
  <span class="home-stay-card__area">
    <IconLine name="pin" aria-hidden="true" />
    <span>{{ stay.area }}</span>
  </span>
  <span v-if="stay.coordinates" class="home-stay-card__coords" :title="`Tọa độ thực địa: ${stay.coordinates}`">
    <IconLine name="compass" aria-hidden="true" />
    <span>{{ stay.coordinates }}</span>
  </span>
  <span class="home-stay-card__price"><strong>{{ stay.price }}</strong></span>
</div>
```

Trong `web-nuxt/assets/css/home-nocturne.css`:
```css
[data-home-pilot="nocturne-b1"] :is(.home-stay-card__price, .home-stay-card__coords) {
  font-variant-numeric: tabular-nums;
}
.home-stay-card__coords {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 0.72rem;
  opacity: 0.85;
}
```

- [ ] **Step 4: Chạy kiểm thử để xác nhận thành công**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts`
Expected: PASS

- [ ] **Step 5: Commit Task 3**

```bash
git add web-nuxt/components/home/HomeRiversideStays.vue web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "feat(home): integrate riverside field coordinates and tabular prices for stays lookbook"
```

---

### Task 4: Tối Ưu CSS Headroom R30.7 & Xác Thực Cổng Kiểm Thử Toàn Diện

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css` (dọn dẹp các rule thừa, bỏ `-webkit-backdrop-filter:` lặp lại để giảm kích thước gzipped)
- Verify: `docs/standards/bundle-budget.json`
- Verify: `scripts/checks/check_bundle.py`
- Verify: `scripts/checks/check_content_voice.py`

**Interfaces:**
- Consumes: CSS assets
- Produces: CSS gzipped $\le 194.560$ bytes với biên độ an toàn $\ge 100$ bytes; 100% tests liên quan đến trang chủ pass.

- [ ] **Step 1: Rà soát và dọn dẹp CSS dư thừa trong `home-nocturne.css`**

Tối ưu hóa các nhóm selector trùng lặp, loại bỏ các thuộc tính lặp lại `-webkit-backdrop-filter:` vì Autoprefixer/PostCSS đã tự động xử lý.

- [ ] **Step 2: Chạy kiểm tra kích thước bundle CSS**

Run: `$env:PYTHONIOENCODING="utf-8"; python -m scripts.checks.check_bundle`
Expected: `✓ R30.7 bundle budget: đạt` với `total_css_gz_kb <= 190` ($\le 194.560$ bytes).

- [ ] **Step 3: Chạy toàn bộ test suite trang chủ**

Run: `npx --prefix web-nuxt vitest run tests/home-deep-simplify.test.ts tests/home-hero-dossier-polish.test.ts tests/home-curated-showcase.test.ts`
Expected: 100% PASS

- [ ] **Step 4: Chạy kiểm tra giọng điệu biên tập (R50.2)**

Run: `python scripts/checks/check_content_voice.py`
Expected: 0 vi phạm từ ngữ cấm.

- [ ] **Step 5: Commit Task 4**

```bash
git add web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "chore(home): optimize CSS bundle headroom and verify deep homepage suite"
```

---

## Execution Choice

Sau khi kế hoạch được phê duyệt, có hai phương án thực thi:

1. **Subagent-Driven (Khuyến nghị):** Điều phối từng subagent thực hiện từng task độc lập, kiểm tra nghiêm ngặt kết quả giữa các task.
2. **Inline Execution:** Thực hiện tuần tự các task trực tiếp trong phiên hiện tại với các trạm kiểm soát (checkpoints).
