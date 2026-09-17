> STATUS: active (2026-09-17)

# Header Editorial De-clutter & Sublime Refinement Plan (Phase 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Triệt tiêu hoàn toàn cảm giác rối rắm, vụn vặt và tàn tích "AI slop" (hàng loạt nút bấm đóng hộp hình pill chắp vá, ô tìm kiếm cồng kềnh 620px chèn ép điều hướng, và các yếu tố thừa thãi); kiến tạo một thanh điều hướng biên tập di sản đỉnh cao, thanh thoát, thông minh và tinh tế theo chuẩn mực ấn loát quốc tế (*Monocle*, *Rijksmuseum*, *National Geographic*).

**Architecture:**
1. **Thu gọn & Tinh tế hóa Tìm kiếm (`SearchAutocomplete.vue`, `shell.css`):** Chuyển ô tìm kiếm desktop từ kích thước quá khổ 620px thành một Search Capsule tinh gọn (210px ở trạng thái nghỉ, mở rộng êm ái lên 280px khi focus), đồng bộ chiều cao 32px chuẩn xác với toàn bộ hàng điều lệnh, tích hợp kbd hint `/` trang nhã.
2. **Thanh lọc Thẩm mỹ Điều hướng Chính (`shell.css`, `default.vue`):** Xóa bỏ viền hộp thô của nút `Danh mục ▾`, đưa nút danh mục về cùng kiểu typographic thanh lịch như các liên kết `Khám phá`, `Gần bạn`, `Cộng đồng`, `Lịch trình`. Mở rộng khoảng cách thở (`gap: var(--space-3)` 12px) cho toàn hàng điều hướng.
3. **Thanh lọc Cụm Tiện ích Bên phải (`DisplaySettingsPopover.vue`, `shell.css`):** Chuyển nút "Trợ năng" sang dạng icon-first (biểu tượng la bàn điền dã `field-compass` 32×32px, text đưa vào `.sr-only` trên desktop chuẩn), chuyển nút đăng nhập sang phong cách ghost button tinh tế, trang bị vách ngăn quang học siêu mảnh (`.header-divider`) phân tách nhịp nhàng các cụm tính năng.
4. **Tinh gọn Folio Khảo cứu `PublicContextBar` (`PublicContextBar.vue`, `shell.css`):** Đưa thanh ngữ cảnh di sản về phong cách một dòng folio xuất bản mỏng mảnh 24px, bộ chọn khu vực dạng text link tự nhiên không viền hộp, trượt ẩn êm đềm khi cuộn trang.

**Tech Stack:** Nuxt 4, Vue 3, CSS Semantic Tokens (`variables.css`, `shell.css`), Vitest, WCAG 2.2 AAA.

**Spec:** Chuẩn mực ấn phẩm biên tập di sản Cửu Long; triệt tiêu 100% AI slop; tuân thủ Hiến pháp `CLAUDE.md §1.7`.

## Global Constraints

- **Màu sắc & Token:** 100% tuân thủ bảng màu Tam Vùng, 0 nợ token (`node scripts/check-tri-region-color-debt.mjs` $\rightarrow$ `semantic: 0, z-index: 0`).
- **Tương phản & Tiếp cận:** Đạt chuẩn WCAG 2.2 AAA kép (`node scripts/check-tri-region-contrast.mjs`), touch target mọi nút tương tác $\ge 44\times 44\text{px}$, double-ring focus indicator (`outline: 2px solid var(--color-focus); outline-offset: 2px`).
- **Bảo toàn kiểm thử:** Giữ vững 100% pass toàn bộ các bộ kiểm thử shell (`ui-foundation-shell.test.ts`, `theme-mode-control.test.ts`, `shell-chrome-polish.test.ts`, `header-smart-editorial-refinement.test.ts`) và 183+ test trang chủ.
- **Bất biến cơ sở dữ liệu:** Bảo toàn 100% bit-for-bit SHA-256 của `agent/data/vinhlong360.db` và `web/data.json` theo Hiến pháp `CLAUDE.md §1.7`.
- **Cổng an toàn cứng:** `python scripts/checks/run_hard.py --all` đạt `hard=0, ratchet không tăng`.

---

## Tasks

### Task 1: Tinh gọn ô tìm kiếm `SearchAutocomplete` thành Compact Editorial Capsule (32px, Adaptive Width, Kbd Hint)

**Files:**
- Modify: `web-nuxt/components/SearchAutocomplete.vue`
- Modify: `web-nuxt/assets/css/shell.css:216-266`
- Test: `web-nuxt/tests/header-editorial-declutter.test.ts`

**Interfaces:**
- Consumes: `SearchAutocomplete.vue`, `assets/css/shell.css`
- Produces: Ô tìm kiếm desktop 32px cao, 210px rộng (mở rộng 280px khi focus), có phím tắt hint `/`

- [ ] **Step 1: Viết bài kiểm thử cho Compact Editorial Search Capsule**

```typescript
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, it } from 'vitest'
import SearchAutocomplete from '../components/SearchAutocomplete.vue'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Header Editorial De-clutter - Task 1: Compact Search Capsule', () => {
  it('renders search autocomplete with refined compact proportions and kbd hint', async () => {
    const wrapper = await mountSuspended(SearchAutocomplete)
    expect(wrapper.find('input[type="search"]').exists()).toBe(true)
    expect(wrapper.find('.search-kbd-hint').exists()).toBe(true)
    expect(wrapper.find('.search-kbd-hint').text()).toBe('/')
  })

  it('enforces 32px height and compact adaptive width in shell.css', () => {
    const css = readFileSync(resolve(__dirname, '../assets/css/shell.css'), 'utf8')
    expect(css).toMatch(/\.public-shell-search\s*input\s*\{[^}]*height:\s*32px;/)
    expect(css).toMatch(/\.public-shell-search\s*\{[^}]*max-width:\s*220px;/)
  })
})
```

- [ ] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx vitest run tests/header-editorial-declutter.test.ts`
Expected: FAIL do chưa có `.search-kbd-hint` và CSS chưa cập nhật 32px.

- [ ] **Step 3: Cập nhật `SearchAutocomplete.vue` và `assets/css/shell.css`**

Trong `SearchAutocomplete.vue`:
- Bổ sung `<kbd class="search-kbd-hint" aria-hidden="true">/</kbd>` bên trong wrapper form khi chưa có query.

Trong `assets/css/shell.css`:
- Cập nhật `.public-shell-search`:
  - `flex: 0 1 220px; max-width: 220px;`
  - `input`: `height: 32px; min-height: 32px; font-size: 0.78rem; padding: 0 28px 0 32px;`
  - Khi `focus-within`: `max-width: 280px; flex-basis: 280px;`
  - Định dạng `.search-kbd-hint`: font-size 10px, viền mờ, hiển thị ở mép phải.

- [ ] **Step 4: Chạy kiểm thử xác nhận thành công**

Run: `npx vitest run tests/header-editorial-declutter.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/SearchAutocomplete.vue web-nuxt/assets/css/shell.css web-nuxt/tests/header-editorial-declutter.test.ts
git commit -m "feat(shell): refine search autocomplete into sleek 32px compact editorial capsule"
```

---

### Task 2: Tinh chỉnh điều hướng biên tập & Thống nhất nút "Danh mục"

**Files:**
- Modify: `web-nuxt/assets/css/shell.css:746-865`
- Test: `web-nuxt/tests/header-editorial-declutter.test.ts`

**Interfaces:**
- Consumes: `.public-shell-inline-nav`, `.public-shell-catalog-button`
- Produces: Thanh điều hướng thoáng đãng `gap: var(--space-3)`, nút danh mục có phong cách typographic đồng bộ, loại bỏ viền hộp cồng kềnh.

- [ ] **Step 1: Viết bài kiểm thử cho Unified Nav Typography**

```typescript
describe('Header Editorial De-clutter - Task 2: Seamless Editorial Navigation', () => {
  it('unifies catalog button typography with nav links and removes heavy boxed container', () => {
    const css = readFileSync(resolve(__dirname, '../assets/css/shell.css'), 'utf8')
    expect(css).toMatch(/\.public-shell-inline-nav\s*\{[^}]*gap:\s*var\(--space-3\);/)
    expect(css).toContain('--radius-control-refined')
  })
})
```

- [ ] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx vitest run tests/header-editorial-declutter.test.ts`
Expected: FAIL vì `gap` vẫn đang là `var(--space-1)`.

- [ ] **Step 3: Cập nhật CSS thanh điều hướng trong `assets/css/shell.css`**

- Cập nhật `.public-shell-inline-nav`: `gap: var(--space-3);`
- Cập nhật `.public-shell-catalog-button`:
  - `background: transparent; border: 1px solid transparent;`
  - Khi hover / active: màu nền nhẹ `color-mix(in srgb, var(--color-surface-subtle) 70%, transparent)`, viền trong suốt hoặc bắt sáng nhẹ.
  - Icon chevron 12px chuyển động mượt mà khi xoay.
  - Giữ nguyên token `--radius-control-refined` và kích thước touch target `::before >= 44x44px`.

- [ ] **Step 4: Chạy kiểm thử xác nhận thành công**

Run: `npx vitest run tests/header-editorial-declutter.test.ts tests/shell-chrome-polish.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/assets/css/shell.css web-nuxt/tests/header-editorial-declutter.test.ts
git commit -m "feat(shell): harmonize catalog dropdown trigger with editorial nav typography"
```

---

### Task 3: Tinh giản cụm tiện ích bên phải thành Ultra-Refined Quiet Utility Cluster

**Files:**
- Modify: `web-nuxt/components/shell/DisplaySettingsPopover.vue`
- Modify: `web-nuxt/assets/css/shell.css:267-350`
- Modify: `web-nuxt/layouts/default.vue:47-71`
- Test: `web-nuxt/tests/header-editorial-declutter.test.ts`

**Interfaces:**
- Consumes: `.auth-area`, `DisplaySettingsPopover.vue`, `.auth-btn`
- Produces: Cụm tiện ích 32px thanh lịch, icon-first Trợ năng, ghost button Đăng nhập, vách ngăn quang học `.header-divider`.

- [ ] **Step 1: Viết bài kiểm thử cho Quiet Utility Cluster**

```typescript
describe('Header Editorial De-clutter - Task 3: Quiet Utility Cluster', () => {
  it('renders display settings as a clean icon-first control with accessible label', async () => {
    const wrapper = await mountSuspended(DisplaySettingsPopover)
    const trigger = wrapper.find('.display-settings-trigger')
    expect(trigger.exists()).toBe(true)
    expect(trigger.attributes('aria-label')).toContain('Tùy chọn hiển thị và trợ năng')
    expect(trigger.find('.display-settings-trigger-text').classes()).toContain('sr-only-md-down')
  })

  it('equips auth area with optical divider and ghost login button in shell.css', () => {
    const css = readFileSync(resolve(__dirname, '../assets/css/shell.css'), 'utf8')
    expect(css).toMatch(/\.header-divider\s*\{[^}]*width:\s*1px;/)
  })
})
```

- [ ] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx vitest run tests/header-editorial-declutter.test.ts`
Expected: FAIL

- [ ] **Step 3: Cập nhật `DisplaySettingsPopover.vue`, `default.vue` và `shell.css`**

Trong `DisplaySettingsPopover.vue`:
- Bọc nhãn "Trợ năng" với class `.display-settings-trigger-text.sr-only-md-down` (ẩn text trên desktop để thành nút icon thanh nhã, giữ nhãn cho màn hình rộng và screen readers).
- Hiển thị chấm `amber-dot` nhỏ gọn khi có chế độ đang bật (`hasActiveMode`).

Trong `layouts/default.vue`:
- Bổ sung `<span class="header-divider" aria-hidden="true" />` trước `.auth-btn`.

Trong `assets/css/shell.css`:
- `.header-divider`: `width: 1px; height: 18px; background: color-mix(in srgb, var(--color-border) 45%, transparent); margin-inline: var(--space-1);`
- Cập nhật `.auth-btn`: tinh chỉnh sang phong cách ghost button cao cấp, viền `1px solid color-mix(in srgb, var(--color-border) 70%, transparent)`, nền trong suốt, hover sáng dịu.

- [ ] **Step 4: Chạy kiểm thử xác nhận thành công**

Run: `npx vitest run tests/header-editorial-declutter.test.ts tests/header-smart-editorial-refinement.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/shell/DisplaySettingsPopover.vue web-nuxt/layouts/default.vue web-nuxt/assets/css/shell.css web-nuxt/tests/header-editorial-declutter.test.ts
git commit -m "feat(shell): distill right utility cluster into serene icon-first controls with optical divider"
```

---

### Task 4: Tinh gọn Folio Khảo cứu `PublicContextBar` thành Whisper-Quiet Editorial Folio

**Files:**
- Modify: `web-nuxt/components/shell/PublicContextBar.vue`
- Modify: `web-nuxt/assets/css/shell.css:28-170`
- Test: `web-nuxt/tests/header-editorial-declutter.test.ts`

**Interfaces:**
- Consumes: `PublicContextBar.vue`, `.public-context-bar`
- Produces: Đường folio di sản mỏng 24px, bộ chọn ghost button không viền hộp, bảo toàn 100% hợp đồng dữ liệu vùng.

- [ ] **Step 1: Viết bài kiểm thử cho Minimalist Regional Folio**

```typescript
describe('Header Editorial De-clutter - Task 4: Minimalist Regional Folio', () => {
  it('renders public context bar with muted editorial pulse and clean borderless select', async () => {
    const wrapper = await mountSuspended(PublicContextBar)
    expect(wrapper.find('[data-public-context-line]').exists()).toBe(true)
    expect(wrapper.find('.public-context-pulse').exists()).toBe(true)
    expect(wrapper.find('select').exists()).toBe(true)
  })

  it('keeps public context bar whisper quiet in shell.css', () => {
    const css = readFileSync(resolve(__dirname, '../assets/css/shell.css'), 'utf8')
    expect(css).toMatch(/\.public-context-bar\s*\{[^}]*max-height:\s*24px;/)
  })
})
```

- [ ] **Step 2: Chạy kiểm thử để xác nhận thất bại**

Run: `npx vitest run tests/header-editorial-declutter.test.ts`
Expected: FAIL vì `max-height` hiện là 26px.

- [ ] **Step 3: Cập nhật `PublicContextBar.vue` và `assets/css/shell.css`**

- Tinh giản màu sắc của `.public-context-pulse` thành sắc màu phù sa Cù Lao dịu nhẹ.
- Đặt `max-height: 24px` cho `.public-context-bar`.
- Loại bỏ hoàn toàn viền hộp của `.public-context-control`: `background: transparent; border: 0;`.
- Giữ vững toàn bộ các thuộc tính tiếp cận WCAG 2.2 AAA (`aria-label`, touch target `::before` 44px).

- [ ] **Step 4: Chạy kiểm thử xác nhận thành công**

Run: `npx vitest run tests/header-editorial-declutter.test.ts tests/ui-foundation-shell.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/shell/PublicContextBar.vue web-nuxt/assets/css/shell.css web-nuxt/tests/header-editorial-declutter.test.ts
git commit -m "feat(shell): refine public context bar into whisper-quiet 24px editorial folio"
```

---

### Task 5: Kiểm thử toàn diện & Triển khai Production VPS `66.42.57.202`

**Files:**
- Test: Toàn bộ test suites Shell và Home
- Production Deploy: VPS `66.42.57.202`

- [ ] **Step 1: Chạy kiểm toán nợ màu Tam Vùng**

Run: `node scripts/check-tri-region-color-debt.mjs`
Expected: `tri-region color debt: PASS` (semantic: 0, z-index: 0).

- [ ] **Step 2: Chạy kiểm toán tương phản WCAG AAA**

Run: `node scripts/check-tri-region-contrast.mjs`
Expected: 100% compliant.

- [ ] **Step 3: Chạy toàn bộ test suites shell & home**

Run: `npx vitest run tests/header-*.test.ts tests/ui-foundation-shell.test.ts tests/theme-mode-control.test.ts tests/shell-chrome-polish.test.ts tests/home`
Expected: 100% passed.

- [ ] **Step 4: Kiểm tra TypeScript**

Run: `npm run typecheck`
Expected: Exit code 0 (0 errors).

- [ ] **Step 5: Kiểm tra an toàn cứng**

Run: `python ../scripts/checks/run_hard.py --all`
Expected: `hard=0, ratchet không tăng`.

- [ ] **Step 6: Xác nhận bất biến cơ sở dữ liệu (B1, B6, B7)**

Run: `Get-FileHash agent\data\vinhlong360.db, web\data.json`
Expected: Khớp 100% SHA-256 gốc.

- [ ] **Step 7: Biên dịch Nitro & Triển khai VPS `66.42.57.202`**

Run:
```bash
npm run build
tar.exe -czf dist_output.tar.gz -C web-nuxt .output
scp.exe dist_output.tar.gz root@66.42.57.202:/tmp/dist_output.tar.gz
ssh.exe root@66.42.57.202 "tar -xzf /tmp/dist_output.tar.gz -C /opt/vinhlong360/web-nuxt && rm /tmp/dist_output.tar.gz && systemctl restart vl-nuxt.service && systemctl status vl-nuxt.service --no-pager"
curl.exe -Is https://vinhlong360.vn
Remove-Item -Force dist_output.tar.gz
git push origin codex/correction-case-pilot
```
Expected: `vl-nuxt.service` active running, HTTP 200 OK, git push sạch sẽ.
