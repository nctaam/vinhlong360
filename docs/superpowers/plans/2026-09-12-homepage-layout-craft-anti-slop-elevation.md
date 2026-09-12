# Kế Hoạch Triển Khai: Nâng Cấp Bố Cục Biên Tập Bất Đối Xứng, Tinh Tế & Triệt Tiêu AI Slop (Giai Đoạn 3)

> STATUS (2026-09-12): completed — hoàn thành xuất sắc nâng cấp bố cục phi đối xứng, dải phân cách dòng sông và biến thể Google Stitch.
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phát triển và tối ưu hóa sâu hơn trang chủ Vĩnh Long 360 về mặt kiến trúc bố cục (Layout Architecture), loại bỏ triệt để bố cục dạng lưới 4 cột bằng chằn chặn (Equal-Column Slop) để chuyển sang hệ lưới biên tập phi đối xứng (Editorial Asymmetric Layout), bổ sung dải phân cách dòng chảy sông Cổ Chiên (Mekong River Flow Divider), nâng cấp công thái học tín hiệu thời gian thực và đồng bộ với Google Stitch Cloud MCP (`14916181929760067680`).

**Architecture:** Sử dụng hệ thống Container Queries kết hợp CSS Grid biên tập phân cấp (Asymmetric Lead Tile), dải phân cách thổ nhưỡng hairline gradient phù sa, và kiểm chứng chặt chẽ bằng TDD Vitest cùng bộ kiểm định hợp đồng màu sắc Tam Vùng (78 tests) và kiểm định launch safety tự động.

**Tech Stack:** Nuxt 4, Vue 3, CSS Container Queries, CSS Grid, Vitest, Google Stitch MCP Server, Python Launch Safety Suite.

**Spec:** [Hiến Pháp Thiết Kế Stitch Anti-Slop](../specs/2026-09-12-stitch-anti-slop-design-constitution.md)

---

## Global Constraints

- **Zero New Dependencies:** Tuyệt đối không cài thêm thư viện bên ngoài.
- **Preserve 78 Color Contract Tests:** Không vi phạm các selector và token được bảo vệ trong `tri-region-color.css` và `scripts/check-tri-region-contrast.mjs`.
- **Preserve Section Order Invariant:** Không làm thay đổi thứ tự tương đối của 5 section cố định (`context`, `editorial-lead`, `quick-decisions`, `signals`, `journey-continuation`) theo `home-nocturne-page.test.ts`.
- **Data Integrity Invariants (§1.7 & B6):** Không bịa đặt số liệu thống kê, số sao giả, hay số đo thủy triều thực tế khi chưa có cảm biến.
- **Accessibility (WCAG 2.2 AAA):** Tương phản chữ trên nền tối thiểu 4.5:1 (thường) và 7:1 (tiêu đề lớn), touch target >= 44px, hỗ trợ `prefers-reduced-motion`.

---

## Task Structure

### Task 1: Viết Test TDD Cho Bố Cục Phi Đối Xứng & Dải Phân Cách Thổ Nhưỡng

**Files:**
- Create: `web-nuxt/tests/home-layout-asymmetry.test.ts`

**Interfaces:**
- Consumes: `web-nuxt/assets/css/home-nocturne.css`, `web-nuxt/components/home/HomeCategoryIndex.vue`
- Produces: 4 test assertions kiểm chứng:
  1. Thẻ tiêu điểm dẫn đầu (Lead Category Card) trong `HomeCategoryIndex.vue`.
  2. Bố cục lưới bất đối xứng cho `.home-category-index__primary` trên màn hình lớn.
  3. Dải phân cách dòng chảy sông Cổ Chiên `.home-river-divider`.
  4. Triệt tiêu hoàn toàn gradient tím neon và các bố cục lưới bằng chằn.

- [ ] **Step 1: Viết test failing (RED)**

Tạo file `web-nuxt/tests/home-layout-asymmetry.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Homepage Editorial Layout Asymmetry & Terroir Craft', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const catVue = readFileSync(resolve(__dirname, '../components/home/HomeCategoryIndex.vue'), 'utf8')

  it('incorporates lead feature tile styling for primary category index', () => {
    expect(catVue).toContain('home-category-index__card--lead')
  })

  it('enforces asymmetric editorial grid layout for category exploration', () => {
    expect(homeCss).toContain('.home-category-index__card--lead')
    expect(homeCss).toMatch(/\.home-category-index__card--lead\s*\{[^}]*grid-column:\s*span\s*2/)
  })

  it('incorporates Mekong river hairline flow divider with alluvial gradient', () => {
    expect(homeCss).toContain('home-river-divider')
    expect(homeCss).toMatch(/\.home-river-divider\s*\{[^}]*background:[^;]*linear-gradient/)
  })

  it('preserves clean token discipline without AI SaaS neon purples or cyan', () => {
    expect(homeCss).not.toMatch(/#a855f7|#8b5cf6|#00f0ff/i)
  })
})
```

- [ ] **Step 2: Chạy test để xác nhận trạng thái RED**

Run: `npm --prefix web-nuxt test -- tests/home-layout-asymmetry.test.ts`
Expected: FAIL (4/4 test assertions failed).

---

### Task 2: Nâng Cấp Bố Cục Bất Đối Xứng Cho Mục Lục Khám Phá (`HomeCategoryIndex.vue` & `home-nocturne.css`)

**Files:**
- Modify: `web-nuxt/components/home/HomeCategoryIndex.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css`

**Interfaces:**
- Consumes: Prop `groups.primary`, token `--color-border`, `--color-surface`, `--mangthit-500`
- Produces: Thẻ đầu tiên (Di sản làng nghề & Văn hóa sông nước) có class `home-category-index__card--lead` chiếm `grid-column: span 2` trên breakpoint rộng (> 56rem), tạo điểm neo thị giác mạnh mẽ, phá vỡ định kiến lưới 4 card đơn điệu.

- [ ] **Step 1: Cập nhật template trong `HomeCategoryIndex.vue`**

Gắn class modifier `:class="{ 'home-category-index__card--lead': index === 0 }"` cho thẻ đầu tiên:
```html
      <NuxtLink
        v-for="(link, index) in groups.primary"
        :key="link.key"
        :to="link.to"
        class="home-category-index__primary-link home-category-index__card"
        :class="{ 'home-category-index__card--lead': index === 0 }"
        :data-material-accent="link.accent"
        data-decision-route
      >
```

- [ ] **Step 2: Cập nhật CSS cho `.home-category-index__card--lead` trong `home-nocturne.css`**

Thêm rules:
```css
@container home-categories (min-width: 56rem) {
  [data-home-pilot="nocturne-b1"] .home-category-index__primary {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  [data-home-pilot="nocturne-b1"] .home-category-index__card--lead {
    grid-column: span 2;
  }
}
```

- [ ] **Step 3: Chạy test xác nhận chuyển GREEN cho 2 assertions đầu**

Run: `npm --prefix web-nuxt test -- tests/home-layout-asymmetry.test.ts`
Expected: 2/4 passed.

- [ ] **Step 4: Commit thay đổi Task 2**

```bash
git add web-nuxt/components/home/HomeCategoryIndex.vue web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-layout-asymmetry.test.ts
git commit -m "feat(home): introduce asymmetric editorial lead tile in category exploration index"
```

---

### Task 3: Bổ Sung Dải Phân Cách Dòng Chảy Sông Cổ Chiên (`index.vue` & `home-nocturne.css`)

**Files:**
- Modify: `web-nuxt/pages/index.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css`

**Interfaces:**
- Consumes: Token `--color-border`, `--color-material-clay`, `--color-canvas`
- Produces: Phần tử trang trí ngữ nghĩa `.home-river-divider` ngăn cách nhẹ nhàng giữa Hero và các khối dữ liệu, tạo chiều sâu thị giác sông nước mà không dùng hiệu ứng giả cầy.

- [ ] **Step 1: Cập nhật template trong `web-nuxt/pages/index.vue`**

Chèn `<div class="home-river-divider" aria-hidden="true" />` ngăn cách giữa các phân đoạn nội dung chính.

- [ ] **Step 2: Cập nhật styling trong `web-nuxt/assets/css/home-nocturne.css`**

```css
[data-home-pilot="nocturne-b1"] .home-river-divider {
  width: min(var(--maxw), calc(100% - var(--space-10)));
  height: 1px;
  margin-inline: auto;
  margin-block: var(--space-4);
  background: linear-gradient(
    90deg,
    transparent 0%,
    color-mix(in srgb, var(--color-material-clay) 24%, var(--color-border)) 25%,
    color-mix(in srgb, var(--color-brand) 32%, var(--color-border)) 50%,
    color-mix(in srgb, var(--color-material-clay) 24%, var(--color-border)) 75%,
    transparent 100%
  );
  border: 0;
}
```

- [ ] **Step 3: Chạy test xác nhận toàn bộ 4/4 assertions GREEN**

Run: `npm --prefix web-nuxt test -- tests/home-layout-asymmetry.test.ts`
Expected: 4/4 passed.

- [ ] **Step 4: Commit thay đổi Task 3**

```bash
git add web-nuxt/pages/index.vue web-nuxt/assets/css/home-nocturne.css
git commit -m "feat(home): add Mekong river hairline flow divider for atmospheric spatial depth"
```

---

### Task 4: Kết Nối Google Stitch Cloud MCP Khám Phá Biến Thể Bố Cục (`generate_variants`)

**Files:**
- MCP Interaction: `stitch` -> `generate_variants`

**Interfaces:**
- Consumes: `projectId: "14916181929760067680"`, `selectedScreenIds: ["bb6ad924554b4f1cb1e9d6311fc7e72b"]`
- Produces: 1 biến thể thiết kế bố cục mới trên Stitch Cloud, đối chiếu phân tích công thái học.

- [ ] **Step 1: Gọi tool Stitch MCP `generate_variants`**

Gọi `generate_variants` với:
```json
{
  "projectId": "14916181929760067680",
  "selectedScreenIds": ["bb6ad924554b4f1cb1e9d6311fc7e72b"],
  "prompt": "Mekong river heritage asymmetric editorial layout, Mang Thit terracotta accents, anti-AI-slop visual hierarchy",
  "variantOptions": {
    "aspects": ["LAYOUT"],
    "creativeRange": "REFINE",
    "variantCount": 1
  }
}
```

- [ ] **Step 2: Ghi nhận phân tích và đối chiếu kết quả sinh từ Stitch**

Đánh giá các giải pháp bố cục từ Stitch Cloud và cập nhật tài liệu tham chiếu.

---

### Task 5: Kiểm Định Toàn Diện Hệ Thống & Cổng An Toàn Ra Mắt

**Files:**
- Verification: toàn bộ test suite

- [ ] **Step 1: Chạy toàn bộ 13 homepage test files**

Run: `npm --prefix web-nuxt test -- tests/home-`
Expected: 13 passed (66/66 tests).

- [ ] **Step 2: Chạy 78 bài test hợp đồng màu sắc Tam Vùng**

Run: `npm --prefix web-nuxt test -- tests/tri-region-color-contract.test.ts`
Expected: 78 passed.

- [ ] **Step 3: Chạy TypeScript typecheck**

Run: `npm --prefix web-nuxt run typecheck`
Expected: 0 errors.

- [ ] **Step 4: Chạy cổng an toàn launch safety**

Run: `python scripts/checks/run_hard.py --all`
Expected: `sạch (hard=0, ratchet không tăng)`.

- [ ] **Step 5: Chạy production build**

Run: `npm --prefix web-nuxt run build`
Expected: Nitro build complete.

---

## Self-Review Checklist

- [x] **Spec coverage:** Kế hoạch bao phủ đầy đủ các yêu cầu về bố cục bất đối xứng, dải phân cách thổ nhưỡng, chống AI slop và tích hợp Stitch MCP.
- [x] **Placeholder scan:** Không có bất kỳ dòng "TBD", "TODO" hay code giả nào. Mọi đoạn code đều là code thực tế sẵn sàng thực thi.
- [x] **Type consistency:** Các class ngữ nghĩa, token CSS và tên component đồng nhất 100% với codebase hiện tại.
