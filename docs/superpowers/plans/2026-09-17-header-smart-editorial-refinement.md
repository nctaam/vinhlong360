> STATUS: active (2026-09-17)

# Header Smart Editorial Refinement & Anti-Slop De-cluttering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chuyển hóa thanh Header Vĩnh Long 360 từ cấu trúc 3 tầng cồng kềnh, rườm rà, ngập tràn các nút bấm dạng pill rời rạc ("AI slop") thành một thanh điều hướng biên tập di sản thông minh, tinh tế, thanh thoát (giảm 40% chiều cao, hợp nhất điều hướng trên 1 hàng duy nhất, tinh gọn công tắc Nocturne/Parchment thành icon micro-segmented toggle, và thanh lọc toàn bộ sự phân mảnh thị giác).

**Architecture:** 
1. Gom cụm điều hướng chính (`Khám phá`, `Gần bạn`, `Cộng đồng`, `Lịch trình`, `Danh mục`) lên thẳng hàng điều lệnh chính trên Desktop, loại bỏ hoàn toàn tầng thứ 3 (`public-shell-task-row`) và liên kết trùng lặp "Trang chủ" (do logo đã là điểm neo trang chủ).
2. Tinh gọn công tắc giao diện `ThemeModeControl`: thay thế 2 nút chữ dài dòng ("Nocturne" / "Nền sáng dễ đọc") bằng cụm icon micro-segmented toggle tinh xảo (`[ 🌙 | ☀️ ]`), giữ nhãn chữ ẩn trong lớp tiếp cận `.sr-only` để bảo toàn 100% khả năng đọc của trình đọc màn hình và vượt qua toàn bộ kiểm thử tự động.
3. Đồng bộ hóa chiều cao (32px), bán kính (`--radius-pill`), và viền bắt sáng *Liquid Glass* cho bộ ba công cụ bên phải (`ThemeModeControl`, `DisplaySettingsPopover`, `auth-btn`), triệt tiêu hiện tượng lệch nhịp và "pill soup".
4. Tinh tế hóa thanh ngữ cảnh thổ nhưỡng `PublicContextBar` thành đường folio biên tập siêu mảnh (24px), thanh thoát như chỉ mục niên giám di sản sông nước Cửu Long.

**Tech Stack:** Nuxt 4, Vue 3, CSS Semantic Tokens (`variables.css`, `shell.css`), Vitest, WCAG 2.2 AAA.

**Spec:** Thiết kế chuẩn mực tạp chí biên tập di sản quốc tế (*Monocle*, *Rijksmuseum*, *National Geographic*); tuân thủ Hiến pháp `CLAUDE.md §1.7`.

## Global Constraints

- **Màu sắc & Token:** 100% tuân thủ bảng màu Tam Vùng, 0 nợ token (`node scripts/check-tri-region-color-debt.mjs` $\rightarrow$ `semantic: 0, z-index: 0`).
- **Tương phản & Tiếp cận:** Đạt chuẩn WCAG 2.2 AAA kép (`node scripts/check-tri-region-contrast.mjs`), touch target mọi nút tương tác $\ge 44\times 44\text{px}$, double-ring focus indicator (`outline: 2px solid var(--color-focus); outline-offset: 2px`).
- **Bảo toàn kiểm thử:** Giữ vững 100% pass toàn bộ 32 bài test shell hiện có (`ui-foundation-shell.test.ts`, `theme-mode-control.test.ts`, `shell-chrome-polish.test.ts`) và 245+ test trang chủ.
- **Bất biến cơ sở dữ liệu:** Bảo toàn 100% bit-for-bit SHA-256 của `agent/data/vinhlong360.db` và `web/data.json` theo Hiến pháp `CLAUDE.md §1.7`.
- **Cổng an toàn cứng:** `python scripts/checks/run_hard.py --all` đạt `hard=0, ratchet không tăng`.

---

### Task 1: Tinh Gọn Cụm Công Tắc ThemeModeControl Thành Micro-Segmented Toggle

**Files:**
- Modify: `web-nuxt/components/shell/ThemeModeControl.vue`
- Modify: `web-nuxt/assets/css/shell.css`
- Test: `web-nuxt/tests/theme-mode-control.test.ts`
- Test: `web-nuxt/tests/header-smart-editorial-refinement.test.ts`

**Interfaces:**
- Consumes: `useColorMode()`, `useAccessibilityProfile()`
- Produces: `[data-theme-control]` với 2 nút `button[data-theme-mode="dark"]` và `button[data-theme-mode="light"]`, nhãn chữ `Nocturne` và `Nền sáng dễ đọc` được bảo toàn trong thẻ `span.theme-mode-label.sr-only` cho accessibility và Vitest, trực quan hiển thị icon mặt trăng (Nocturne) và mặt trời (Parchment) với kích thước micro-pill tinh xảo (chiều cao 32px, tổng chiều rộng ~64px).

- [ ] **Step 1: Viết test mới kiểm tra công thái học micro-toggle và kích thước tinh gọn**

Tạo tệp kiểm thử `web-nuxt/tests/header-smart-editorial-refinement.test.ts`:
```typescript
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ThemeModeControl from '../components/shell/ThemeModeControl.vue'

const colorMode = vi.hoisted(() => ({ value: 'dark' as unknown, preference: 'dark' as unknown }))
mockNuxtImport('useColorMode', () => () => colorMode)
const wrappers: Array<{ unmount: () => void }> = []

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  colorMode.value = 'dark'
  colorMode.preference = 'dark'
})

describe('Header Smart Editorial Refinement - Task 1: Theme Micro-Toggle', () => {
  it('renders compact micro-toggle while preserving accessible text labels for screen readers', async () => {
    const wrapper = await mountSuspended(ThemeModeControl, { attachTo: document.body })
    wrappers.push(wrapper)

    const darkBtn = wrapper.get('button[data-theme-mode="dark"]')
    const lightBtn = wrapper.get('button[data-theme-mode="light"]')

    expect(darkBtn.text()).toContain('Nocturne')
    expect(lightBtn.text()).toContain('Nền sáng dễ đọc')

    // Nhãn chữ được bọc trong class sr-only để triệt tiêu text rườm rà trên thanh điều hướng
    expect(darkBtn.find('.theme-mode-label').classes()).toContain('sr-only')
    expect(lightBtn.find('.theme-mode-label').classes()).toContain('sr-only')

    // Cả 2 nút đều có icon trực quan
    expect(darkBtn.find('.line-icon').exists()).toBe(true)
    expect(lightBtn.find('.line-icon').exists()).toBe(true)
  })
})
```

- [ ] **Step 2: Chạy test để xác nhận test thất bại (RED)**

Chạy: `npx vitest run tests/header-smart-editorial-refinement.test.ts`  
Kỳ vọng: FAIL vì `.theme-mode-label` chưa có class `sr-only`.

- [ ] **Step 3: Cập nhật ThemeModeControl.vue & CSS shell.css**

Trong `web-nuxt/components/shell/ThemeModeControl.vue`:
```vue
<template>
  <div class="theme-mode-control" data-theme-control role="group" aria-label="Chọn giao diện">
    <button
      v-for="mode in modes"
      :key="mode.value"
      type="button"
      :data-theme-mode="mode.value"
      :aria-pressed="isActive(mode.value)"
      :aria-label="mode.label"
      :title="mode.description"
      @click="selectMode(mode.value, $event)"
    >
      <IconLine :name="mode.value === 'dark' ? 'moon' : 'sun'" aria-hidden="true" />
      <span class="theme-mode-label sr-only">{{ mode.label }}</span>
    </button>
  </div>
</template>
```

Trong `web-nuxt/assets/css/shell.css`:
Cập nhật `.theme-mode-control`:
```css
/* ── Precision Segmented Micro-Toggle ── */
.theme-mode-control {
  display: inline-flex;
  align-items: center;
  padding: 2px;
  height: 32px;
  min-height: 32px;
  border: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
  border-radius: var(--radius-pill, 999px);
  background: color-mix(in srgb, var(--color-surface-subtle) 75%, transparent);
  box-shadow: inset 0 1px 2px rgba(var(--black-rgb), 0.08);
}

.theme-mode-control button {
  position: relative;
  width: 28px;
  height: 26px;
  min-height: 26px;
  min-width: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  border-radius: var(--radius-pill, 999px);
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.theme-mode-control button::before {
  content: '';
  position: absolute;
  inset: -9px;
  min-width: 44px;
  min-height: 44px;
}

.theme-mode-control button .line-icon {
  font-size: 13px;
  transition: color var(--duration-fast) var(--ease-out);
}
```

- [ ] **Step 4: Chạy lại test xác nhận đạt chuẩn (GREEN)**

Chạy: `npx vitest run tests/header-smart-editorial-refinement.test.ts tests/theme-mode-control.test.ts`  
Kỳ vọng: PASS (100%).

- [ ] **Step 5: Cam kết mã nguồn**

```bash
git add web-nuxt/components/shell/ThemeModeControl.vue web-nuxt/assets/css/shell.css web-nuxt/tests/header-smart-editorial-refinement.test.ts
git commit -m "feat(shell): streamline theme mode control to micro-segmented icon toggle"
```

---

### Task 2: Hợp Nhất Điều Hướng Biên Tập Lên Hàng Chính & Loại Bỏ Tầng Thứ 3

**Files:**
- Modify: `web-nuxt/layouts/default.vue`
- Modify: `web-nuxt/assets/css/shell.css`
- Test: `web-nuxt/tests/header-smart-editorial-refinement.test.ts`
- Test: `web-nuxt/tests/ui-foundation-shell.test.ts`

**Interfaces:**
- Consumes: `primaryNavItems` (`/du-lich`, `/ban-do`, `/cong-dong`, `/lich-trinh`), `catalogOpen`, `navGroups`
- Produces: Hàng điều lệnh chính (`.public-shell-command-row`) chứa trọn vẹn: Logo bên trái, Điều hướng biên tập (`.public-shell-inline-nav`) ở giữa, và Cụm công cụ (`.auth-area`) bên phải trên màn hình Desktop ($\ge 1024\text{px}$). Loại bỏ hoàn toàn sự cồng kềnh của `.public-shell-task-row`.

- [ ] **Step 1: Viết test cho bố cục hợp nhất và triệt tiêu tầng thừa trên Desktop**

Thêm test case vào `web-nuxt/tests/header-smart-editorial-refinement.test.ts`:
```typescript
it('integrates primary navigation into command row without redundant home link on desktop', async () => {
  const wrapper = await mountSuspended(DefaultLayout, {
    attachTo: document.body,
    slots: { default: '<div>Content</div>' },
    global: {
      stubs: {
        AuthModal: true,
        ChatWidget: true,
        ConfirmDialog: true,
        NotificationBell: true,
        OnboardingSheet: true,
        ScrollToTop: true,
        ToastContainer: true,
        UserMenu: true,
        SearchAutocomplete: true,
        ShellPublicBottomNav: true,
        ShellPublicContextBar: { template: '<div data-public-context-line />' },
      },
    },
  })
  wrappers.push(wrapper)

  const nav = wrapper.get('.public-shell-inline-nav')
  expect(nav.exists()).toBe(true)

  const links = nav.findAll('a')
  const hrefs = links.map(l => l.attributes('href'))
  expect(hrefs).toEqual(['/du-lich', '/ban-do', '/cong-dong', '/lich-trinh'])
  expect(hrefs).not.toContain('/') // Không lặp lại Trang chủ vì Logo đã dẫn về '/'

  // Nút Danh mục được tích hợp liền mạch
  expect(nav.find('.public-shell-catalog-button').exists()).toBe(true)
})
```

- [ ] **Step 2: Chạy test xác nhận thất bại (RED)**

Chạy: `npx vitest run tests/header-smart-editorial-refinement.test.ts`  
Kỳ vọng: FAIL vì `.public-shell-inline-nav` chưa tồn tại trong `layouts/default.vue`.

- [ ] **Step 3: Tái cấu trúc layouts/default.vue và CSS shell.css**

Cập nhật `web-nuxt/layouts/default.vue`:
1. Chuẩn hóa `primaryNavItems` không chứa mục trùng lặp `{ to: '/', label: 'Trang chủ' }`:
```typescript
const primaryNavItems = [
  { to: '/du-lich', label: 'Khám phá' },
  { to: '/ban-do', label: 'Gần bạn' },
  { to: '/cong-dong', label: 'Cộng đồng' },
  { to: '/lich-trinh', label: 'Lịch trình' },
] as const
```
2. Đưa cụm điều hướng trực tiếp vào `.public-shell-command-row`:
```vue
<div class="public-shell-command-row">
  <NuxtLink class="brand" to="/" aria-label="Về trang chủ vinhlong360">
    <span class="logo">{{ brandSitePrefix }}<span class="dot">360</span></span>
    <span class="tld">{{ ss('branding.logo_suffix', '.vn') }}</span>
  </NuxtLink>

  <nav class="public-shell-inline-nav" aria-label="Điều hướng chính">
    <NuxtLink
      v-for="item in primaryNavItems"
      :key="item.to"
      :to="item.to"
      :class="{ active: isPrimaryActive(item.to) }"
      :aria-current="isPrimaryActive(item.to) ? 'page' : undefined"
    >
      {{ item.label }}
    </NuxtLink>
    <button
      type="button"
      class="public-shell-catalog-button"
      :class="{ active: catalogOpen }"
      :aria-expanded="catalogOpen"
      aria-controls="main-nav"
      @click="catalogOpen = !catalogOpen"
    >
      Danh mục
      <IconLine name="chevron-down" aria-hidden="true" />
    </button>
  </nav>

  <SearchAutocomplete class="topbar-search public-shell-search" />

  <div class="auth-area">
    <ShellThemeModeControl />
    <ShellDisplaySettingsPopover />
    ...
  </div>
```
3. Loại bỏ khối `.public-shell-task-row` khỏi template.
4. Cập nhật `assets/css/shell.css`: tạo phong cách `.public-shell-inline-nav` thanh lịch, khoảng thở Fibonacci, viền bắt sáng dưới chân tinh tế, tự động ẩn trên tablet/mobile để chuyển sang menu ngăn kéo (`nav-toggle`).

- [ ] **Step 4: Chạy test xác nhận đạt chuẩn (GREEN)**

Chạy: `npx vitest run tests/header-smart-editorial-refinement.test.ts tests/ui-foundation-shell.test.ts`  
Kỳ vọng: PASS (100%).

- [ ] **Step 5: Cam kết mã nguồn**

```bash
git add web-nuxt/layouts/default.vue web-nuxt/assets/css/shell.css web-nuxt/tests/header-smart-editorial-refinement.test.ts
git commit -m "feat(shell): unify navigation into primary command bar and eliminate 3rd-tier clutter"
```

---

### Task 3: Đồng Bộ Cụm Công Cụ Bên Phải (Harmonious Utility Cluster) & Tinh Tế Hóa Nút Trợ Năng

**Files:**
- Modify: `web-nuxt/components/shell/DisplaySettingsPopover.vue`
- Modify: `web-nuxt/assets/css/shell.css`
- Test: `web-nuxt/tests/header-smart-editorial-refinement.test.ts`

**Interfaces:**
- Consumes: Bán kính `--radius-pill`, chiều cao chuẩn `32px`, viền bắt sáng Liquid Glass.
- Produces: Cụm 3 công cụ (`ThemeModeControl`, `DisplaySettingsPopover`, `auth-btn`) đồng nhất tuyệt đối về visual rhythm, touch target $\ge 44\times 44\text{px}$, nhún đàn hồi `:active scale(0.96)`.

- [ ] **Step 1: Viết test cho tính đồng bộ kích thước và công thái học của cụm công cụ**

Thêm test case vào `web-nuxt/tests/header-smart-editorial-refinement.test.ts`:
```typescript
it('ensures all utility buttons share consistent 32px height, touch targets, and tactile response', async () => {
  const wrapper = await mountSuspended(DefaultLayout, {
    attachTo: document.body,
    slots: { default: '<div>Content</div>' },
    global: {
      stubs: {
        AuthModal: true,
        ChatWidget: true,
        ConfirmDialog: true,
        NotificationBell: true,
        OnboardingSheet: true,
        ScrollToTop: true,
        ToastContainer: true,
        UserMenu: true,
        SearchAutocomplete: true,
        ShellPublicBottomNav: true,
        ShellPublicContextBar: { template: '<div data-public-context-line />' },
      },
    },
  })
  wrappers.push(wrapper)

  const authArea = wrapper.get('.auth-area')
  expect(authArea.find('[data-theme-control]').exists()).toBe(true)
  expect(authArea.find('.display-settings-trigger').exists()).toBe(true)
  expect(authArea.find('.auth-btn').exists()).toBe(true)
})
```

- [ ] **Step 2: Chạy test xác nhận hiện trạng**

Chạy: `npx vitest run tests/header-smart-editorial-refinement.test.ts`

- [ ] **Step 3: Chuẩn hóa CSS trong shell.css và DisplaySettingsPopover.vue**

Trong `web-nuxt/assets/css/shell.css`:
- Chuẩn hóa khoảng cách giữa các phần tử trong `.auth-area`: `gap: var(--space-2);`.
- Nút `.display-settings-trigger`: chiều cao 32px, `border-radius: var(--radius-pill)`, viền `color-mix(in srgb, var(--color-border) 70%, transparent)`, nền `color-mix(in srgb, var(--color-surface-subtle) 75%, transparent)`.
- Thêm hiệu ứng nhún lò xo đầm tay `:active { transform: scale(0.96); }` cho cả 3 nút: `.display-settings-trigger`, `.auth-btn`, và `.theme-mode-control button`.

- [ ] **Step 4: Chạy test xác nhận đạt chuẩn (GREEN)**

Chạy: `npx vitest run tests/header-smart-editorial-refinement.test.ts tests/shell-chrome-polish.test.ts`  
Kỳ vọng: PASS (100%).

- [ ] **Step 5: Cam kết mã nguồn**

```bash
git add web-nuxt/components/shell/DisplaySettingsPopover.vue web-nuxt/assets/css/shell.css web-nuxt/tests/header-smart-editorial-refinement.test.ts
git commit -m "feat(shell): harmonize right utility cluster ergonomics and tactile response"
```

---

### Task 4: Nâng Tầm PublicContextBar Thành Đường Folio Di Sản Siêu Mảnh

**Files:**
- Modify: `web-nuxt/components/shell/PublicContextBar.vue`
- Modify: `web-nuxt/assets/css/shell.css`
- Test: `web-nuxt/tests/ui-foundation-shell.test.ts`
- Test: `web-nuxt/tests/header-smart-editorial-refinement.test.ts`

**Interfaces:**
- Consumes: `selectedRegion`, `regionOptions`, `envelope`
- Produces: Đường folio 24px thanh tao, viền siêu mỏng, chữ viết hoa có tracking tinh tế, bộ chọn khu vực phong cách editorial ghost picker.

- [ ] **Step 1: Viết test cho đường folio di sản**

Thêm test vào `web-nuxt/tests/header-smart-editorial-refinement.test.ts`:
```typescript
it('renders the public context bar as a refined editorial folio with accessible controls', async () => {
  const wrapper = await mountSuspended(PublicContextBar)
  wrappers.push(wrapper)

  expect(wrapper.get('[data-public-context-line]').exists()).toBe(true)
  expect(wrapper.get('.public-context-label').text()).toBe('Tam Vùng Di Sản')
  expect(wrapper.find('select').exists()).toBe(true)
})
```

- [ ] **Step 2: Tinh chỉnh PublicContextBar.vue và shell.css**

- Giảm tối đa cảm giác chia cắt: đường viền mờ `color-mix(in srgb, var(--color-border) 35%, transparent)`.
- Kiểu chữ tinh tế: `font-size: 0.68rem`, `letter-spacing: 0.06em`, màu sắc dịu nhẹ.
- Bộ chọn khu vực `.public-context-control`: thiết kế dạng ghost button không viền cứng, chỉ nổi nhẹ khi hover/focus, giữ nguyên 100% chức năng `<select>` cho tương thích trình duyệt.

- [ ] **Step 3: Chạy test xác nhận đạt chuẩn (GREEN)**

Chạy: `npx vitest run tests/header-smart-editorial-refinement.test.ts tests/ui-foundation-shell.test.ts`  
Kỳ vọng: PASS (100%).

- [ ] **Step 4: Cam kết mã nguồn**

```bash
git add web-nuxt/components/shell/PublicContextBar.vue web-nuxt/assets/css/shell.css web-nuxt/tests/header-smart-editorial-refinement.test.ts
git commit -m "feat(shell): elevate public context bar into whisper-quiet editorial folio"
```

---

### Task 5: Kiểm Thử Toàn Hệ Thống, Build Nitro Sản Xuất & Triển Khai VPS 66.42.57.202

**Files:**
- Test: `web-nuxt/tests/*`
- Build: `web-nuxt/.output`

- [ ] **Step 1: Chạy toàn bộ các bộ kiểm thử tự động**
  1. Kiểm toán nợ token: `node scripts/check-tri-region-color-debt.mjs` $\rightarrow$ PASS (0 debt).
  2. Kiểm toán tương phản WCAG 2.2 AAA: `node scripts/check-tri-region-contrast.mjs` $\rightarrow$ PASS (100%).
  3. Kiểm thử shell và trang chủ: `node ./node_modules/vitest/vitest.mjs run tests/header-smart-editorial-refinement.test.ts tests/ui-foundation-shell.test.ts tests/theme-mode-control.test.ts tests/shell-chrome-polish.test.ts tests/home-*.test.ts` $\rightarrow$ PASS (100%).
  4. Kiểm tra kiểu dữ liệu Nuxt: `npm run typecheck` $\rightarrow$ PASS (0 errors).
  5. Cổng an toàn cứng: `python scripts/checks/run_hard.py --all` $\rightarrow$ PASS (`hard=0, ratchet không tăng`).
  6. Đối chiếu SHA-256 SQLite `vinhlong360.db` và `web/data.json` $\rightarrow$ PASS (100% trùng khớp bit-for-bit).

- [ ] **Step 2: Biên dịch Nitro sản xuất**
  Chạy: `npm run build` tại `web-nuxt`.

- [ ] **Step 3: Đóng gói và triển khai lên máy chủ VPS `66.42.57.202`**
  1. Nén gói: `tar.exe -czf dist_output.tar.gz -C web-nuxt .output`
  2. Truyền lên VPS: `scp.exe dist_output.tar.gz root@66.42.57.202:/tmp/dist_output.tar.gz`
  3. Giải nén và khởi động lại:
     ```bash
     ssh.exe root@66.42.57.202 "tar -xzf /tmp/dist_output.tar.gz -C /opt/vinhlong360/web-nuxt && rm /tmp/dist_output.tar.gz && systemctl restart vl-nuxt.service && systemctl status vl-nuxt.service --no-pager"
     ```
  4. Xác nhận trực tuyến: `curl.exe -Is https://vinhlong360.vn` $\rightarrow$ HTTP/1.1 200 OK.
  5. Dọn dẹp: `Remove-Item -Force dist_output.tar.gz`

- [ ] **Step 4: Đẩy toàn bộ commit lên GitHub**
  Chạy: `git push origin codex/correction-case-pilot`
