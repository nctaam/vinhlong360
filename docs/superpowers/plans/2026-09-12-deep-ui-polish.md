# Deep UI Polish & Tactile Refinement Implementation Plan

> STATUS (2026-09-12): in_progress — Kế hoạch nâng cấp và hoàn thiện sâu giao diện hiện hữu theo chỉ đạo chủ dự án.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện sâu tính thẩm mỹ, chiều sâu thị giác (surface elevation, tactile micro-interactions) và tính công thái học của các bề mặt giao diện cốt lõi hiện có trên `web-nuxt`, thu hẹp triệt để khoảng cách giữa nguyên mẫu thiết kế và trải nghiệm thực tế mà **tuyệt đối không thêm tính năng mới, không sửa schema, không thêm dịch vụ/chi phí**.

**Architecture:** Giữ nguyên 100% kiến trúc frontend gốc: Nuxt 4 SSR, **CSS thuần + Token hệ 3 vùng (Tri-Region)**, phong cách Editorial Woodcut Nam Bộ và bộ chữ **Be Vietnam Pro**. Tinh chỉnh trực tiếp các tầng token (`variables.css`, `dark-overrides.css`), lớp shell (`shell.css`), trang chủ (`home-nocturne.css`, `pages/index.vue`), thẻ thực thể (`cards.css`) và các subcomponent giao diện hiện có.

**Tech Stack:** Nuxt 4, Vue 3.5 SFC, Pure CSS Tokens (3 tầng: primitive → semantic → component), Vitest 4, Playwright/Axe a11y runner.

**Spec:** `docs/ROADMAP.md` §19–32, `docs/HANDOFF.md`, Bất biến §2 `CLAUDE.md`.

---

## Global Constraints

- **KHÔNG Tailwind:** Tuyệt đối giữ kiến trúc CSS thuần + token hệ 3 vùng (`CLAUDE.md` §1.5, `docs/HANDOFF.md` §1).
- **KHÔNG thêm tính năng mới:** Không tạo route mới, không thêm endpoint API, không sửa schema database.
- **Bảo toàn tiếp cận WCAG 2.2 AAA:** Mọi giá trị màu sắc, độ tương phản văn bản và viền điều khiển phải đạt tối thiểu 4.5:1 (AA) và hướng tới 7:1 (AAA) ở cả 2 chế độ `Parchment` (nền sáng) và `Nocturne` (nền tối).
- **Bảo toàn trần số dòng (Line Ceilings):** Mọi file SFC Vue không vượt quá trần 950–1050 dòng; nếu CSS nở rộng phải tách/stream vào file CSS chuyên trách (`home-nocturne.css`, `cards.css`, `shell.css`).
- **Bất biến B6 về hình ảnh:** Giữ nguyên 100% cơ chế ảnh AI nội bộ (`scripts/gen_image.py`), tem kiểm chứng `SourceMark` và khung giải trình `ImageDisclosure`. Không dùng ảnh stock bên ngoài.
- **1 task = 1 commit độc lập có verify:** Không gộp commit big-bang; mỗi task kết thúc với bộ test xanh (`vitest run`).

---

## Danh Mục Files Tác Động

| File | Vai trò | Trách nhiệm chính |
|---|---|---|
| `web-nuxt/assets/css/variables.css` | [MODIFY] | Bổ sung token chiều sâu (ambient shadows, elevated surfaces, border-radius mềm hơn) |
| `web-nuxt/assets/css/dark-overrides.css` | [MODIFY] | Đồng bộ bóng đổ phát quang êm (subtle glow) và tương phản ban đêm cho Nocturne |
| `web-nuxt/assets/css/shell.css` | [MODIFY] | Tinh chỉnh Public Shell Header, glass blur backdrop, gradient logo badge |
| `web-nuxt/layouts/default.vue` | [MODIFY] | Hoàn thiện vi tương tác trên nút đăng nhập, bộ chuyển theme và thanh điều hướng |
| `web-nuxt/assets/css/home-nocturne.css` | [MODIFY] | Tinh chỉnh Hero search box, timeline nhịp sống, lưới danh mục 4 cột, khung OCOP |
| `web-nuxt/pages/index.vue` | [MODIFY] | Giữ cấu trúc, chuẩn hóa layout grid, loại bỏ padding thừa, gắn kết chặt chẽ các section |
| `web-nuxt/components/home/HomeFeatureDossier.vue` | [MODIFY] | Làm mềm viền ảnh, xử lý vignette chuyển tiếp, tối ưu vị trí tem nguồn & nút hành động |
| `web-nuxt/components/home/HomeDecisionLedger.vue` | [MODIFY] | Điểm nút timeline (sediment tick line) với hiệu ứng trượt nhẹ và số liệu tabular chuẩn xác |
| `web-nuxt/components/home/HomeCategoryIndex.vue` | [MODIFY] | Lưới danh mục 4 cột với hiệu ứng nhấc thẻ (`translateY(-2px)`), icon vector nổi bật |
| `web-nuxt/components/home/HomeOcopLedger.vue` | [MODIFY] | Khung chứng nhận kép tinh tế, ánh sao vàng/hổ phách chân thực cho sao OCOP 3–4–5 sao |
| `web-nuxt/components/catalog/CatalogAeoPlaque.vue` | [MODIFY] | Bảng giải đáp nhanh AEO màu hổ phách, padding thoáng, phân tách câu hỏi - trả lời dễ đọc |
| `web-nuxt/assets/css/cards.css` | [MODIFY] | Đồng bộ bo góc, bóng đổ mềm khi hover và bố cục metadata cho `EntityCard` |
| `web-nuxt/components/EntityCard.vue` | [MODIFY] | Căn chỉnh huy hiệu OCOP, khoảng cách, nhãn nguồn không che khuất hình ảnh |

---

## Chi Tiết Các Tác Vụ (Bite-Sized Tasks)

### Task 1: Hệ thống Token Chiều sâu & Tầng bề mặt đa lớp (Multi-layer Surface Elevation)

**Files:**
- Modify: `web-nuxt/assets/css/variables.css`
- Modify: `web-nuxt/assets/css/dark-overrides.css`
- Test: `web-nuxt/tests/ui-tokens-elevation.test.ts` [NEW]

**Interfaces:**
- Consumes: Thang màu primitive sRGB Tây Nam Bộ (`--alluvial-paper`, `--surface-white`, `--night-canvas`, `--night-surface`).
- Produces: 
  - `--shadow-card-ambient`: Bóng đổ êm dịu đa tầng không làm đục màu card.
  - `--shadow-card-hover`: Hiệu ứng nổi nhẹ khi di chuột.
  - `--radius-surface-refined`: Chuẩn hóa 14px (thay vì 12px gắt) giúp thẻ mềm mại, hiện đại.
  - `--radius-control-refined`: Chuẩn hóa 10px (thay vì 8px) cho input và button.
  - `--glass-frosted-nav`: Độ mờ kính cho header / bottom dock.

- [ ] **Step 1: Viết test kiểm tra tính sẵn sàng của bộ token chiều sâu mới**

```typescript
// web-nuxt/tests/ui-tokens-elevation.test.ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('UI Tokens - Elevation & Tactile Depth', () => {
  const css = readFileSync(resolve(__dirname, '../assets/css/variables.css'), 'utf8')
  const darkCss = readFileSync(resolve(__dirname, '../assets/css/dark-overrides.css'), 'utf8')

  it('defines ambient shadow and elevation tokens in variables.css', () => {
    expect(css).toContain('--shadow-card-ambient:')
    expect(css).toContain('--shadow-card-hover:')
    expect(css).toContain('--radius-surface-refined:')
    expect(css).toContain('--radius-control-refined:')
  })

  it('provides dark mode ambient glow / depth equivalents in dark-overrides.css', () => {
    expect(darkCss).toContain('--shadow-card-ambient:')
    expect(darkCss).toContain('--shadow-card-hover:')
  })
})
```

- [ ] **Step 2: Chạy test để xác nhận test thất bại (RED)**
  - Lệnh: `npx vitest run tests/ui-tokens-elevation.test.ts`
  - Kết quả mong đợi: FAIL do chưa khai báo các token mới.

- [ ] **Step 3: Khai báo token trong `variables.css` và `dark-overrides.css`**
  - Trong `variables.css`:
    ```css
    --radius-control-refined: 10px;
    --radius-surface-refined: 14px;
    --shadow-card-ambient: 0 2px 10px -2px rgba(var(--mekong-ink-rgb, 8, 26, 22), 0.05), 0 1px 3px rgba(0, 0, 0, 0.03);
    --shadow-card-hover: 0 8px 24px -4px rgba(var(--mekong-ink-rgb, 8, 26, 22), 0.09), 0 2px 6px -1px rgba(0, 0, 0, 0.04);
    --glass-frosted-nav: saturate(180%) blur(16px);
    ```
  - Trong `dark-overrides.css`:
    ```css
    --shadow-card-ambient: 0 2px 12px -2px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.06);
    --shadow-card-hover: 0 8px 28px -4px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.12);
    ```

- [ ] **Step 4: Chạy lại test để xác nhận test vượt qua (GREEN)**
  - Lệnh: `npx vitest run tests/ui-tokens-elevation.test.ts`
  - Kết quả: PASS.

- [ ] **Step 5: Commit task 1**
  - `git add web-nuxt/assets/css/variables.css web-nuxt/assets/css/dark-overrides.css web-nuxt/tests/ui-tokens-elevation.test.ts`
  - `git commit -m "feat(ui): Task 1 - introduce ambient elevation and tactile radius tokens"`

---

### Task 2: Hoàn thiện Thanh Điều Hướng Công Cộng (Public Shell Chrome)

**Files:**
- Modify: `web-nuxt/assets/css/shell.css`
- Modify: `web-nuxt/layouts/default.vue`
- Test: `web-nuxt/tests/shell-chrome-polish.test.ts` [NEW]

**Interfaces:**
- Consumes: `--glass-frosted-nav`, `--radius-control-refined`, `--sediment-tick`.
- Produces: Thanh Public Shell Header trang nhã, kính mờ chống chói, huy hiệu logo 360 nổi bật, các nút tác vụ có vi tương tác bấm nảy.

- [ ] **Step 1: Viết test kiểm tra hợp đồng giao diện thanh Public Shell**

```typescript
// web-nuxt/tests/shell-chrome-polish.test.ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Public Shell Polish', () => {
  const shellCss = readFileSync(resolve(__dirname, '../assets/css/shell.css'), 'utf8')

  it('implements frosted glass backdrop and refined brand mark', () => {
    expect(shellCss).toContain('backdrop-filter:')
    expect(shellCss).toContain('--sediment-tick')
  })
})
```

- [ ] **Step 2: Chạy test để xác nhận thất bại (RED)**
  - Lệnh: `npx vitest run tests/shell-chrome-polish.test.ts`

- [ ] **Step 3: Cập nhật CSS và template thanh Shell**
  - Trong `shell.css`: Áp dụng `--glass-frosted-nav` cho `.public-shell-chrome.scrolled` và `.public-shell-header`.
  - Tinh chỉnh logo `.brand`: Thêm khung nền nhẹ với gradient viền `--sediment-tick` bao quanh cụm số `360`, tăng độ sắc sảo nhận diện thương hiệu bản địa.
  - Cải tiến nút `.auth-btn` và `.public-shell-catalog-button`: Bo góc 10px (`--radius-control-refined`), padding thoáng `8px 14px`, hiệu ứng hover `transform: translateY(-1px)`.

- [ ] **Step 4: Chạy test xác nhận vượt qua (GREEN)**
  - Lệnh: `npx vitest run tests/shell-chrome-polish.test.ts`

- [ ] **Step 5: Commit task 2**
  - `git add web-nuxt/assets/css/shell.css web-nuxt/layouts/default.vue web-nuxt/tests/shell-chrome-polish.test.ts`
  - `git commit -m "feat(shell): Task 2 - polish public shell chrome, tactile actions and frosted glass navigation"`

---

### Task 3: Hoàn thiện Sâu Khối Hero & Thẻ Dossier Biên Tập

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Modify: `web-nuxt/components/home/HomeFeatureDossier.vue`
- Modify: `web-nuxt/pages/index.vue`
- Test: `web-nuxt/tests/home-hero-dossier-polish.test.ts` [NEW]

**Interfaces:**
- Consumes: `HomeFeatureDossier` props (`heroFeature`, `heroFeatureReason`, `heroFeatureDescriptor`).
- Produces: Khối Hero cân đối, ô tìm kiếm nổi bật có viền lấy nét tinh tế, thẻ ảnh dossier có chiều sâu chuyển tiếp lớp vignette, nút "Khám phá" và "Thêm lịch trình" đạt chuẩn tương phản AAA.

- [ ] **Step 1: Viết test kiểm tra hợp đồng hiển thị của Hero và Dossier**

```typescript
// web-nuxt/tests/home-hero-dossier-polish.test.ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Home Hero & Feature Dossier Polish', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const dossierVue = readFileSync(resolve(__dirname, '../components/home/HomeFeatureDossier.vue'), 'utf8')

  it('enforces refined search shadow and dossier container styling', () => {
    expect(homeCss).toContain('--shadow-card-ambient')
    expect(dossierVue).toContain('home-feature-dossier')
  })
})
```

- [ ] **Step 2: Chạy test xác nhận (RED)**
  - Lệnh: `npx vitest run tests/home-hero-dossier-polish.test.ts`

- [ ] **Step 3: Tinh chỉnh CSS Hero & Component HomeFeatureDossier**
  - Trong `home-nocturne.css`:
    - Tinh chỉnh `.hero-search`: Bo góc `12px`, padding thoáng, viền focus `2px solid var(--color-action)`, đổ bóng mềm `--shadow-card-ambient`.
    - Tinh chỉnh `.hero-nearby`: Cân bằng icon pin, padding `6px 12px`, hover mượt mà với gạch chân nổi.
    - Cải tiến `.home-feature-dossier`: Áp dụng `--radius-surface-refined` (14px), đổ bóng đa tầng, tách biệt rõ ràng giữa hình ảnh và phần thông tin biên tập.
  - Trong `HomeFeatureDossier.vue`:
    - Tối ưu kích thước nhãn nguồn `SourceMark` nhỏ gọn nhưng sắc nét.
    - Chỉnh khoảng cách giữa 2 nút hành động (Chi tiết / Thêm lịch trình) để touch target luôn đạt tối thiểu 44px theo WCAG.

- [ ] **Step 4: Chạy test xác nhận (GREEN)**
  - Lệnh: `npx vitest run tests/home-hero-dossier-polish.test.ts`

- [ ] **Step 5: Commit task 3**
  - `git add web-nuxt/assets/css/home-nocturne.css web-nuxt/components/home/HomeFeatureDossier.vue web-nuxt/pages/index.vue web-nuxt/tests/home-hero-dossier-polish.test.ts`
  - `git commit -m "feat(home): Task 3 - polish hero search enclosure and feature dossier framing"`

---

### Task 4: Hoàn thiện Sổ Tay Quyết Định & Lưới Danh Mục 4 Cột

**Files:**
- Modify: `web-nuxt/components/home/HomeDecisionLedger.vue`
- Modify: `web-nuxt/components/home/HomeCategoryIndex.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-decision-category.test.ts` [NEW]

**Interfaces:**
- Consumes: `decisionEntries`, `categoryGroups` từ `useHomePresentation`.
- Produces: Trục thời gian nhịp sống trực quan, số liệu dạng số tabular không bị giật dòng, thẻ danh mục 4 cột có hiệu ứng nhấc thẻ (`translateY(-2px)`) kèm viền sáng theo màu vùng.

- [ ] **Step 1: Viết test cho hiệu ứng hover và tính toàn vẹn của Sổ tay Quyết định**

```typescript
// web-nuxt/tests/home-decision-category.test.ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Home Decision Ledger and Category Index', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')

  it('contains category hover micro-lift and decision ledger active styles', () => {
    expect(homeCss).toContain('.home-decision-ledger__link:hover')
    expect(homeCss).toContain('.home-category-index__primary-link:hover')
  })
})
```

- [ ] **Step 2: Chạy test kiểm tra (RED)**
  - Lệnh: `npx vitest run tests/home-decision-category.test.ts`

- [ ] **Step 3: Nâng cấp trải nghiệm tương tác trong CSS và components**
  - `home-nocturne.css`:
    - `.home-decision-ledger__row`: Tinh chỉnh chấm tròn chỉ dẫn nhịp sống (sediment marker) đồng màu thương hiệu, hover dòng có nền nhấn nhẹ (`var(--color-action-surface)`).
    - `.home-category-index__primary-link`: Thêm `transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease`, hover nhấc nhẹ 2px kèm bóng `--shadow-card-hover`.
    - Icon vector trong danh mục: Nền tròn mềm mại, màu sắc chuẩn xác theo 3 sắc thái (Đất sét Mang Thít / Hổ phách mật ong / Sông Cổ Chiên).

- [ ] **Step 4: Chạy test xác nhận (GREEN)**
  - Lệnh: `npx vitest run tests/home-decision-category.test.ts`

- [ ] **Step 5: Commit task 4**
  - `git add web-nuxt/components/home/HomeDecisionLedger.vue web-nuxt/components/home/HomeCategoryIndex.vue web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-decision-category.test.ts`
  - `git commit -m "feat(home): Task 4 - refine decision ledger rhythm and category index tactile lift"`

---

### Task 5: Hoàn thiện Khung Vinh Danh OCOP & Bảng Tra Cứu AEO

**Files:**
- Modify: `web-nuxt/components/home/HomeOcopLedger.vue`
- Modify: `web-nuxt/components/catalog/CatalogAeoPlaque.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Modify: `web-nuxt/assets/css/catalog.css`
- Test: `web-nuxt/tests/home-ocop-aeo-polish.test.ts` [NEW]

**Interfaces:**
- Consumes: Dữ liệu hạng sao OCOP 3–4–5 sao, các câu hỏi tra cứu nhanh AEO bản địa.
- Produces: Khung bằng khen vinh danh OCOP trang trọng, ngôi sao lấp lánh có chiều sâu, bảng AEO màu hổ phách dễ tra cứu.

- [ ] **Step 1: Viết test cho component OcopLedger và AeoPlaque**

```typescript
// web-nuxt/tests/home-ocop-aeo-polish.test.ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('OCOP Ledger & AEO Plaque Visual Polish', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const catalogCss = readFileSync(resolve(__dirname, '../assets/css/catalog.css'), 'utf8')

  it('contains enhanced star glow and plaque card elevation', () => {
    expect(homeCss).toContain('home-ocop__frame')
    expect(catalogCss).toContain('catalog-aeo-plaque')
  })
})
```

- [ ] **Step 2: Chạy test kiểm tra (RED)**
  - Lệnh: `npx vitest run tests/home-ocop-aeo-polish.test.ts`

- [ ] **Step 3: Tinh chỉnh thẩm mỹ Ocop Ledger và AEO Plaque**
  - `HomeOcopLedger.vue` & `home-nocturne.css`:
    - Khung `.home-ocop__frame`: Bo góc `16px`, viền đôi sắc nét (`border: 2px solid var(--color-border); box-shadow: 0 0 0 4px var(--color-surface), var(--shadow-card-ambient)`).
    - Ngôi sao 5 sao: Ở chế độ tối có ánh sáng vàng dịu (`filter: drop-shadow(0 2px 8px rgba(232, 163, 61, 0.45))`), ở chế độ sáng dùng màu vàng óng hổ phách (`var(--harvest-600)`).
  - `CatalogAeoPlaque.vue` & `catalog.css`:
    - Khối AEO: Thẻ nền hổ phách dịu (`background: var(--color-surface)` kèm dải viền trái hổ phách 4px), giãn cách dòng thoáng đãng, phân cấp câu trả lời rõ ràng.

- [ ] **Step 4: Chạy test xác nhận (GREEN)**
  - Lệnh: `npx vitest run tests/home-ocop-aeo-polish.test.ts`

- [ ] **Step 5: Commit task 5**
  - `git add web-nuxt/components/home/HomeOcopLedger.vue web-nuxt/components/catalog/CatalogAeoPlaque.vue web-nuxt/assets/css/home-nocturne.css web-nuxt/assets/css/catalog.css web-nuxt/tests/home-ocop-aeo-polish.test.ts`
  - `git commit -m "feat(catalog): Task 5 - polish OCOP ledger certificate frame and AEO answer plaque"`

---

### Task 6: Hoàn thiện Thẻ Thực Thể Chung (`EntityCard.vue` & `cards.css`)

**Files:**
- Modify: `web-nuxt/components/EntityCard.vue`
- Modify: `web-nuxt/assets/css/cards.css`
- Test: `web-nuxt/tests/entity-card-polish.test.ts` [NEW]

**Interfaces:**
- Consumes: Entity props (id, name, summary, image, tags, rating, ocop, price).
- Produces: Thẻ thực thể thống nhất toàn site (từ trang chủ, danh mục, tìm kiếm, lưu trữ), ảnh sắc nét không vỡ tỷ lệ, nhãn badge không chồng lấn, hiệu ứng hover mượt mà.

- [ ] **Step 1: Viết test cho EntityCard**

```typescript
// web-nuxt/tests/entity-card-polish.test.ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('EntityCard Polish', () => {
  const cardsCss = readFileSync(resolve(__dirname, '../assets/css/cards.css'), 'utf8')

  it('applies refined radius and hover shadow to entity cards', () => {
    expect(cardsCss).toContain('--radius-surface-refined')
    expect(cardsCss).toContain('--shadow-card-hover')
  })
})
```

- [ ] **Step 2: Chạy test kiểm tra (RED)**
  - Lệnh: `npx vitest run tests/entity-card-polish.test.ts`

- [ ] **Step 3: Cập nhật `cards.css` và `EntityCard.vue`**
  - `.entity-card`: Áp dụng bo góc `--radius-surface-refined` (14px), viền mỏng 1px, nền card sạch sẽ.
  - Ảnh cover: Tỷ lệ 16:9 hoặc 4:3 chuẩn, overflow hidden, `transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1)`. Khi hover thẻ, ảnh phóng nhẹ 1.03x bên trong khung crop.
  - Huy hiệu (OCOP star, Giá tiền, Xã/Phường): Bố trí thành hàng linh hoạt phía dưới tiêu đề, không đè che khuất ảnh đại diện.

- [ ] **Step 4: Chạy test xác nhận (GREEN)**
  - Lệnh: `npx vitest run tests/entity-card-polish.test.ts`

- [ ] **Step 5: Commit task 6**
  - `git add web-nuxt/components/EntityCard.vue web-nuxt/assets/css/cards.css web-nuxt/tests/entity-card-polish.test.ts`
  - `git commit -m "feat(ui): Task 6 - standardize entity card elevation, image transitions, and badge hierarchy"`

---

### Task 7: Toàn Diện Kiểm Thử, A11y & Kiểm Tra Trần Dòng (Full Verification Gate)

**Files:**
- Test: Toàn bộ suite test Vitest hiện hành
- Test: Script kiểm tra khả năng tiếp cận WCAG
- Test: Kiểm tra trần số dòng (`line-ceilings`) cho các file đã sửa đổi

- [ ] **Step 1: Chạy toàn bộ 8 bài test chuyên biệt của trang chủ**
  - Lệnh: `npx vitest run tests/home-*.test.ts`
  - Kết quả mong đợi: 100% tests PASS.

- [ ] **Step 2: Chạy bộ kiểm tra accessibility công cộng**
  - Lệnh: `npm run check:public-accessibility`
  - Kết quả mong đợi: Không có vi phạm WCAG AA/AAA.

- [ ] **Step 3: Kiểm tra trần số dòng trên toàn bộ các file sửa đổi**
  - Kiểm tra các file: `pages/index.vue`, `HomeFeatureDossier.vue`, `HomeDecisionLedger.vue`, `HomeCategoryIndex.vue`, `HomeOcopLedger.vue`, `EntityCard.vue`.
  - Tiêu chí: Tất cả phải nằm dưới trần quy định (< 950 - 1050 dòng/file).

- [ ] **Step 4: Chạy toàn bộ Vitest suite của `web-nuxt`**
  - Lệnh: `npm run test`
  - Kết quả mong đợi: Toàn bộ các test suite đều xanh.

- [ ] **Step 5: Commit nghiệm thu hoàn thiện giao diện**
  - `git commit --allow-empty -m "chore(release): Task 7 - verify full frontend suite, a11y compliance, and line ceilings"`

---

## Kế Hoạch Xác Minh (Verification Plan)

### Automated Tests
1. **Kiểm tra Unit & Snapshot UI:**
   `npx vitest run tests/ui-tokens-elevation.test.ts tests/shell-chrome-polish.test.ts tests/home-hero-dossier-polish.test.ts tests/home-decision-category.test.ts tests/home-ocop-aeo-polish.test.ts tests/entity-card-polish.test.ts`
2. **Kiểm tra Toàn bộ Trang chủ:**
   `npx vitest run tests/home-*.test.ts`
3. **Kiểm tra Tiếp cận & Tương phản:**
   `npm run check:public-accessibility`
4. **Kiểm tra Trần số dòng:**
   `pwsh -NoProfile -Command "Get-Content web-nuxt/pages/index.vue | Measure-Object -Line"` (Phải < 950 dòng)

### Manual Verification
1. Mở trình duyệt ở chế độ **Parchment (Nền sáng)**: Kiểm tra độ nổi của thẻ, phân cấp rõ ràng giữa nền canvas `#F9F7F1` và thẻ card, không còn cảm giác phẳng lì.
2. Mở trình duyệt ở chế độ **Nocturne (Nền tối)**: Kiểm tra viền phản quang nhẹ, hiệu ứng ánh sao OCOP và độ êm của bóng đổ ban đêm.
3. Kiểm tra thanh điều hướng khi cuộn trang: Hiệu ứng kính mờ (frosted blur) làm mờ nội dung lướt qua bên dưới mượt mà.
