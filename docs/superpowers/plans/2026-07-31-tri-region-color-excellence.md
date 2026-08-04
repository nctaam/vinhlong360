# Tri-Region Color Excellence Implementation Plan

> STATUS (2026-08-04): complete — implementation and QA evidence recorded.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Triển khai hệ màu Tri-Region Color Excellence cho Homepage B1, Discovery, Search và Entity Detail, giữ Nocturne mặc định, Daylight Parchment do người dùng chủ động chọn, đồng thời tách rõ action, brand, trust, status, category và material accent.

**Architecture:** Mở rộng token semantic hiện có trong `variables.css`, sau đó đặt một compatibility bridge có phạm vi dưới `data-color-system="tri-region-v1"` để không đổi màu các trang ngoài wave. Màu ngữ cảnh chỉ đi qua resolver TypeScript tĩnh; page/component biểu đạt vai trò bằng `data-page-recipe`, `data-material-accent`, `data-color-role` và các primitive trust/freshness có nhãn nhìn thấy được. Behavior-level tests chứng minh nội dung người dùng thấy; CSS contract, contrast audit, debt ratchet và browser screenshots là lớp bằng chứng bổ sung.

**Tech Stack:** Nuxt 4, Vue 3, TypeScript, CSS custom properties, OKLCH với sRGB fallback, `@nuxt/test-utils`, `@vue/test-utils`, Vitest, Node.js scripts, browser-based responsive visual QA.

## Global Constraints

- Baseline triển khai bắt buộc chứa cả commit Homepage B1 `5d1363da` và đặc tả màu `f228a92c`; không triển khai trực tiếp trên một nhánh chỉ chứa một trong hai commit.
- Phạm vi wave này chỉ gồm `/`, `/du-lich`, `/tim-kiem`, `/dia-diem/[id]` và các component trực tiếp phục vụ bốn trang; AdminCP, partner, moderation, map/chart adapter toàn hệ thống và các public page family khác chưa đổi giao diện trong wave này.
- Nocturne là mặc định; Daylight Parchment chỉ đổi bằng lựa chọn rõ ràng của người dùng. Không tự đổi theme hoặc accent theo IP, GPS, giờ, mùa, profile, hành vi hoặc dominant color của ảnh.
- Primary action dùng River; brand/current context dùng Mang Thít Clay; focus dùng Aged Brass trên Nocturne và River đã kiểm tra trên Parchment; Official dùng River + shield + chữ; Verified dùng Orchard + check + chữ; Community dùng neutral/leaf-muted + user icon + chữ; Warning dùng Amber; Error/Danger dùng Coral.
- Không tạo theme theo tỉnh và không dùng mô hình “một tỉnh = một màu”. Resolver chỉ dùng content type/category/material key đã duyệt, không đọc mô tả tự do, địa bàn người dùng hoặc metadata ảnh.
- Mang Thít Clay được phép dùng production. Coconut Leaf dùng lại Orchard trong wave này. Không tạo primitive Coir Umber hoặc Khmer Ochre trước khi Regional Color Evidence Book được duyệt.
- Campaign Capsule, map palette và chart palette không được mở rộng trong wave này; chúng là follow-up riêng sau khi bốn page recipe đạt gate, và không được mượn token trust/status/brand để triển khai tạm.
- Ảnh không điều khiển semantic UI; không dominant-color extraction, không brand tint toàn ảnh và không dùng màu provenance để ám chỉ ảnh AI đã được chứng nhận.
- Accent mạnh mục tiêu: Homepage 8–10%, Discovery/Search 4–6%, Entity Detail 6–8%; mỗi viewport chỉ có một material accent nổi bật. Muốn thêm một accent mạnh phải hạ hoặc bỏ accent mạnh đang có.
- Body text mục tiêu 7:1 và không thấp hơn 4.5:1; metadata quan trọng tối thiểu 4.5:1; control, icon, border truyền cấu trúc và focus indicator tối thiểu 3:1; WCAG 2.2 AA là release gate.
- Màu không bao giờ là kênh duy nhất truyền source tier, freshness, warning, danger, selected hoặc disabled state. Mọi trust tier đều phải có icon và nhãn tiếng Việt nhìn thấy được.
- Behavior-level tests là bằng chứng chính: mount component/page, điều khiển API/state và kiểm tra nội dung, hành động, nhãn trust và state người dùng thực sự thấy. Source-string/CSS assertions chỉ bổ sung cho behavior test.
- `catalog.css` và `detail.css` là compatibility debt dùng chung ngoài wave; không rewrite toàn bộ hai file trong kế hoạch này. Tri-region scoped bridge phải làm đúng semantic trên bốn trang, còn debt ratchet ngăn số raw hex và legacy `--primary*` tăng lên.
- Không thêm dependency runtime hoặc test dependency mới. Không tạo JavaScript palette generator, CSS-in-JS color engine, WebGL, glass, glow hoặc gradient đa sắc mới.
- Mỗi task dùng fresh implementer, sau đó có một vòng review độc lập về spec compliance và một vòng review độc lập về code quality. Mỗi task phải lưu RED/GREEN output, stage đúng file khai báo và tạo một commit có thể revert độc lập.
- Không sửa hoặc stage các thay đổi song song đã biết: `design-system/vinhlong360/pages/home.md`, `.superpowers/`, `agent/knowledge.db-*`, `design-system/vinhlong360/concepts/`, `docs/page-inventory-design-scope-2026-07-27.md` và các artifact NP-0 đang untracked.

## Execution Baseline

- [ ] **Step 1: Tạo worktree triển khai riêng bằng skill bắt buộc**

Invoke `superpowers:using-git-worktrees`, sau đó chạy từ repository root:

```powershell
git worktree add .worktrees/tri-region-color -b codex/tri-region-color f228a92c
Set-Location .worktrees/tri-region-color
git merge --no-ff codex/homepage-b1-nocturne -m "merge: include homepage B1 color baseline"
```

Expected: merge sạch; worktree mới có commit merge với hai parent chứa `f228a92c` và `5d1363da`.

- [ ] **Step 2: Chứng minh baseline và giữ sạch phạm vi song song**

```powershell
git merge-base --is-ancestor f228a92c HEAD
git merge-base --is-ancestor 5d1363da HEAD
git status --short
Set-Location web-nuxt
npm test -- tests/nocturne-theme-contract.test.ts tests/theme-mode-control.test.ts tests/home-nocturne-presentation.test.ts tests/home-nocturne-components.test.ts tests/home-nocturne-page.test.ts
```

Expected: hai lệnh `merge-base` exit `0`; các suite baseline PASS; `git status --short` chỉ phản ánh merge baseline hoặc sạch, không chứa file song song bị copy sang worktree.

## File Structure

- Modify `web-nuxt/assets/css/variables.css`: thêm semantic color pairs, material tokens, source/status surfaces, sRGB RGB channels và sửa Verified/Community mapping.
- Create `web-nuxt/assets/css/tri-region-color.css`: compatibility bridge và page/component recipes chỉ hoạt động dưới `[data-color-system="tri-region-v1"]`.
- Modify `web-nuxt/nuxt.config.ts`: load `tri-region-color.css` sau `catalog.css` để scoped recipe có quyền ưu tiên mà không ảnh hưởng trang ngoài wave.
- Create `web-nuxt/utils/regionalColor.ts`: resolver thuần, đồng bộ, typed cho material accent, source tier và freshness status.
- Modify `web-nuxt/types/index.ts`: dùng lại union trust/freshness chính thức ở entity types mà không đổi API payload.
- Create `web-nuxt/components/SourceMark.vue`: source tier có icon + nhãn, không suy trust từ URL.
- Create `web-nuxt/components/FreshnessLine.vue`: freshness có clock + nhãn cập nhật, tách khỏi SourceMark.
- Create `web-nuxt/components/EntityTrustPanel.vue`: anatomy trust cho Entity Detail, kết hợp source, freshness, source link, note và report action.
- Modify Homepage B1 files: `web-nuxt/pages/index.vue`, `web-nuxt/assets/css/home-nocturne.css`, `web-nuxt/utils/homeNocturnePresentation.ts`, `web-nuxt/components/home/HomeFeatureDossier.vue`, `web-nuxt/components/home/HomeDecisionLedger.vue`, `web-nuxt/components/home/HomeCategoryIndex.vue`.
- Modify Discovery/Search shared files: `web-nuxt/pages/du-lich.vue`, `web-nuxt/pages/tim-kiem.vue`, `web-nuxt/components/EntityCard.vue`, `web-nuxt/components/CatalogSpotlight.vue`, `web-nuxt/components/CatalogInterstitial.vue`.
- Modify Detail files: `web-nuxt/pages/dia-diem/[id].vue`, `web-nuxt/components/ContactWidget.vue`, `web-nuxt/components/ImageDisclosure.vue`, `web-nuxt/components/EntityHeroPlaceholder.vue`.
- Create behavior/contract tests: `web-nuxt/tests/tri-region-color-contract.test.ts`, `web-nuxt/tests/regional-color.test.ts`, `web-nuxt/tests/source-freshness-mark.test.ts`, `web-nuxt/tests/discovery-tri-region-color.test.ts`, `web-nuxt/tests/search-tri-region-color.test.ts`, `web-nuxt/tests/detail-tri-region-color.test.ts`, `web-nuxt/tests/tri-region-color-ratchet.test.ts`.
- Create quality scripts/config: `web-nuxt/scripts/check-tri-region-contrast.mjs`, `web-nuxt/scripts/check-tri-region-color-debt.mjs`, `web-nuxt/config/tri-region-color-debt.json`.
- Create QA evidence: `docs/superpowers/qa/2026-07-31-tri-region-color/report.md` và mười sáu screenshot canonical cho hai theme, desktop/mobile, bốn page recipe trong wave.

---

### Task 1: Thiết Lập Semantic Token Và Scoped Theme Contract

**Files:**
- Modify: `web-nuxt/assets/css/variables.css`
- Create: `web-nuxt/assets/css/tri-region-color.css`
- Modify: `web-nuxt/nuxt.config.ts`
- Create: `web-nuxt/tests/tri-region-color-contract.test.ts`
- Modify: `web-nuxt/tests/nocturne-theme-contract.test.ts`
- Create: `web-nuxt/scripts/check-tri-region-contrast.mjs`

**Interfaces:**
- Consumes: primitive Nocturne/Parchment hiện có và class `.dark`/`.light` do `@nuxtjs/color-mode` quản lý.
- Produces: `--color-action`, `--color-action-hover`, `--color-action-surface`, `--color-action-border`, `--color-on-action`, `--color-brand`, `--color-brand-surface`, `--color-focus`, `--color-success`, `--color-warning`, `--color-error`, `--color-source-official`, `--color-source-verified`, `--color-source-community`, ba source surface token và năm `--color-material-*` token; scoped root contract `data-color-system="tri-region-v1"`.

- [ ] **Step 1: Viết contract test RED cho token và scoped bridge**

Create `web-nuxt/tests/tri-region-color-contract.test.ts`:

```ts
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(import.meta.dirname, '../..')

describe('Tri-Region color contract', () => {
  it('maps action, brand, trust, status and material roles without province themes', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/variables.css'), 'utf8')

    expect(css).toMatch(/--color-action:\s*var\(--river-600\)/)
    expect(css).toMatch(/--color-brand:\s*var\(--mangthit-600\)/)
    expect(css).toMatch(/--color-source-official:\s*var\(--river-600\)/)
    expect(css).toMatch(/--color-source-verified:\s*var\(--orchard-600\)/)
    expect(css).toMatch(/--color-source-community:\s*var\(--mekong-muted\)/)
    expect(css).toMatch(/--color-warning:\s*var\(--harvest-700\)/)
    expect(css).toContain('--color-material-clay')
    expect(css).toContain('--color-material-leaf')
    expect(css).toContain('--color-material-river')
    expect(css).toContain('--color-material-amber')
    expect(css).toContain('--color-material-neutral')
    expect(css).not.toContain('--color-material-coir')
    expect(css).not.toContain('--color-material-khmer-ochre')
  })

  it('keeps semantic meaning stable between Nocturne and Parchment', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/variables.css'), 'utf8')

    expect(css).toMatch(/\.light\s*\{[\s\S]*--color-source-verified:\s*var\(--orchard-600\)/)
    expect(css).toMatch(/\.light\s*\{[\s\S]*--color-focus:\s*var\(--river-600\)/)
    expect(css).toMatch(/\.light\s*\{[\s\S]*--color-on-action:\s*var\(--surface-white\)/)
    expect(css).toMatch(/\.dark\s*\{[\s\S]*--color-source-verified:\s*var\(--night-leaf\)/)
    expect(css).toMatch(/\.dark\s*\{[\s\S]*--color-source-community:\s*var\(--night-muted\)/)
    expect(css).toMatch(/\.dark\s*\{[\s\S]*--color-focus:\s*var\(--night-amber\)/)
    expect(css).toMatch(/\.dark\s*\{[\s\S]*--color-on-action:\s*var\(--night-canvas\)/)
  })

  it('scopes compatibility aliases and recipes to tri-region pages only', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/tri-region-color.css'), 'utf8')
    const config = await readFile(resolve(root, 'web-nuxt/nuxt.config.ts'), 'utf8')

    expect(css).toContain('[data-color-system="tri-region-v1"]')
    expect(css).toMatch(/\[data-color-system="tri-region-v1"\][\s\S]*--primary:\s*var\(--color-action\)/)
    expect(css).toContain('[data-page-recipe="homepage"]')
    expect(css).toContain('[data-page-recipe="discovery"]')
    expect(css).toContain('[data-page-recipe="search"]')
    expect(css).toContain('[data-page-recipe="detail"]')
    expect(css).toContain('@media (forced-colors: active)')
    expect(css).toContain('@media (prefers-contrast: more)')
    expect(css).not.toMatch(/#[0-9a-f]{3,8}\b/i)
    expect(config.indexOf("'~/assets/css/tri-region-color.css'")).toBeGreaterThan(
      config.indexOf("'~/assets/css/catalog.css'"),
    )
  })
})
```

Extend `web-nuxt/tests/nocturne-theme-contract.test.ts` with exact assertions for Verified = Orchard, Community = neutral, Nocturne focus = Brass and Parchment focus = River.

- [ ] **Step 2: Chạy contract test và xác nhận RED**

```powershell
npm test -- tests/tri-region-color-contract.test.ts tests/nocturne-theme-contract.test.ts
```

Expected: FAIL vì `tri-region-color.css`, `--harvest-700`, material/source surface tokens chưa tồn tại và Verified vẫn đang map sang Clay.

- [ ] **Step 3: Thêm primitive/semantic pair chính xác**

Trong `variables.css`, giữ raw color chỉ ở primitive layer và thêm/sửa đúng contract sau:

```css
:root {
  --harvest-700: #855A16;
  --night-river-hover: #9BC2CB;
  --mask-opaque: #000000;
  --color-action-rgb: 3, 90, 105;
  --color-brand-rgb: 149, 64, 43;
  --color-success-rgb: 37, 93, 52;
  --color-warning-rgb: 133, 90, 22;
  --color-error-rgb: 189, 65, 63;
  --color-mask-opaque: var(--mask-opaque);

  --color-action: var(--river-600);
  --color-action-hover: var(--river-700);
  --color-action-surface: color-mix(in srgb, var(--color-action) 10%, transparent);
  --color-action-surface-hover: color-mix(in srgb, var(--color-action) 16%, transparent);
  --color-action-border: color-mix(in srgb, var(--color-action) 36%, transparent);
  --color-on-action: var(--surface-white);
  --color-brand: var(--mangthit-600);
  --color-brand-surface: color-mix(in srgb, var(--color-brand) 10%, transparent);
  --color-success: var(--orchard-600);
  --color-warning: var(--harvest-700);
  --color-error: var(--coral-error);
  --color-source-official: var(--river-600);
  --color-source-verified: var(--orchard-600);
  --color-source-community: var(--mekong-muted);
  --color-source-official-surface: color-mix(in srgb, var(--color-source-official) 10%, transparent);
  --color-source-verified-surface: color-mix(in srgb, var(--color-source-verified) 10%, transparent);
  --color-source-community-surface: color-mix(in srgb, var(--color-source-community) 10%, transparent);
  --color-material-clay: var(--mangthit-600);
  --color-material-leaf: var(--orchard-600);
  --color-material-river: var(--river-600);
  --color-material-amber: var(--harvest-600);
  --color-material-neutral: var(--mekong-muted);
}

@supports (color: oklch(0% 0 0)) {
  :root {
    --harvest-700: oklch(48% 0.1 75);
    --night-river-hover: oklch(80% 0.045 215);
  }
}

/* Adaptive Nocturne root is the SSR/default state before color-mode hydration. */
:root {
  --color-action-rgb: 125, 174, 186;
  --color-brand-rgb: 199, 133, 117;
  --color-success-rgb: 124, 164, 131;
  --color-warning-rgb: 206, 167, 112;
  --color-error-rgb: 223, 127, 120;
  --color-action-hover: var(--night-river-hover);
  --color-on-action: var(--night-canvas);
  --color-success: var(--night-leaf);
  --color-warning: var(--night-amber);
  --color-error: var(--night-error);
  --color-source-official: var(--night-river);
  --color-source-verified: var(--night-leaf);
  --color-source-community: var(--night-muted);
  --color-material-clay: var(--night-clay);
  --color-material-leaf: var(--night-leaf);
  --color-material-river: var(--night-river);
  --color-material-amber: var(--night-amber);
  --color-material-neutral: var(--night-muted);
}

.light {
  --color-action-rgb: 3, 90, 105;
  --color-brand-rgb: 149, 64, 43;
  --color-success-rgb: 37, 93, 52;
  --color-warning-rgb: 133, 90, 22;
  --color-error-rgb: 189, 65, 63;
  --color-action-hover: var(--river-700);
  --color-focus: var(--river-600);
  --color-on-action: var(--surface-white);
  --color-success: var(--orchard-600);
  --color-warning: var(--harvest-700);
  --color-error: var(--coral-error);
  --color-source-official: var(--river-600);
  --color-source-verified: var(--orchard-600);
  --color-source-community: var(--mekong-muted);
  --color-material-clay: var(--mangthit-600);
  --color-material-leaf: var(--orchard-600);
  --color-material-river: var(--river-600);
  --color-material-amber: var(--harvest-600);
  --color-material-neutral: var(--mekong-muted);
}

.dark {
  --color-action-rgb: 125, 174, 186;
  --color-brand-rgb: 199, 133, 117;
  --color-success-rgb: 124, 164, 131;
  --color-warning-rgb: 206, 167, 112;
  --color-error-rgb: 223, 127, 120;
  --color-focus: var(--night-amber);
  --color-action-hover: var(--night-river-hover);
  --color-on-action: var(--night-canvas);
  --color-source-official: var(--night-river);
  --color-source-verified: var(--night-leaf);
  --color-source-community: var(--night-muted);
  --color-material-clay: var(--night-clay);
  --color-material-leaf: var(--night-leaf);
  --color-material-river: var(--night-river);
  --color-material-amber: var(--night-amber);
  --color-material-neutral: var(--night-muted);
}
```

Giữ `--primary: var(--color-brand)` ở global legacy layer để không đổi trang ngoài wave; chỉ scoped bridge mới chuyển legacy primary sang action.

- [ ] **Step 4: Tạo scoped compatibility bridge và recipe base**

Create `web-nuxt/assets/css/tri-region-color.css` với nội dung nền tảng sau; các selector page-specific được bổ sung ở Task 3–6:

```css
[data-color-system="tri-region-v1"] {
  --primary: var(--color-action);
  --primary-dark: var(--color-action-hover);
  --primary-fg: var(--color-action);
  --primary-fg-strong: var(--color-action-hover);
  --primary-rgb: var(--color-action-rgb);
  --focus-outline: var(--color-focus);
  --tri-region-material-accent: var(--color-material-neutral);
  background: var(--color-canvas);
  color: var(--color-text);
}

[data-color-system="tri-region-v1"][data-material-accent="clay"],
[data-color-system="tri-region-v1"] [data-material-accent="clay"] {
  --tri-region-material-accent: var(--color-material-clay);
}

[data-color-system="tri-region-v1"][data-material-accent="leaf"],
[data-color-system="tri-region-v1"] [data-material-accent="leaf"] {
  --tri-region-material-accent: var(--color-material-leaf);
}

[data-color-system="tri-region-v1"][data-material-accent="river"],
[data-color-system="tri-region-v1"] [data-material-accent="river"] {
  --tri-region-material-accent: var(--color-material-river);
}

[data-color-system="tri-region-v1"][data-material-accent="amber"],
[data-color-system="tri-region-v1"] [data-material-accent="amber"] {
  --tri-region-material-accent: var(--color-material-amber);
}

[data-color-system="tri-region-v1"] [data-color-role="action-primary"] {
  border-color: var(--color-action);
  background: var(--color-action);
  color: var(--color-on-action);
}

[data-color-system="tri-region-v1"] [data-color-role="action-secondary"] {
  border-color: var(--color-action-border);
  background: var(--color-action-surface);
  color: var(--color-action);
}

[data-color-system="tri-region-v1"] :is(a, button, input, select, textarea):focus-visible {
  outline-color: var(--color-focus);
}

@media (prefers-contrast: more) {
  [data-color-system="tri-region-v1"] {
    --color-border: currentColor;
    --color-action-border: currentColor;
  }
}

@media (forced-colors: active) {
  [data-color-system="tri-region-v1"] [data-material-accent] {
    --tri-region-material-accent: CanvasText;
  }

  [data-color-system="tri-region-v1"] :is(a, button, input, select, textarea):focus-visible {
    outline-color: Highlight;
  }
}
```

Add `~/assets/css/tri-region-color.css` immediately after `~/assets/css/catalog.css` in `nuxt.config.ts`.

- [ ] **Step 5: Thêm contrast audit không phụ thuộc package ngoài**

Create `web-nuxt/scripts/check-tri-region-contrast.mjs` với toàn bộ implementation sau:

```js
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const css = readFileSync(resolve(process.cwd(), 'assets/css/variables.css'), 'utf8')
const pairs = [
  ['body-light', 'mekong-ink', 'alluvial-paper', 7],
  ['muted-light', 'mekong-muted', 'alluvial-paper', 4.5],
  ['action-light', 'river-600', 'alluvial-paper', 4.5],
  ['on-action-light', 'surface-white', 'river-600', 4.5],
  ['brand-light', 'mangthit-600', 'alluvial-paper', 4.5],
  ['verified-light', 'orchard-600', 'alluvial-paper', 4.5],
  ['warning-light', 'harvest-700', 'alluvial-paper', 4.5],
  ['error-light', 'coral-error', 'alluvial-paper', 4.5],
  ['body-dark', 'night-text', 'night-canvas', 7],
  ['action-dark', 'night-river', 'night-canvas', 4.5],
  ['on-action-dark', 'night-canvas', 'night-river', 4.5],
  ['brand-dark', 'night-clay', 'night-canvas', 4.5],
  ['verified-dark', 'night-leaf', 'night-canvas', 4.5],
  ['warning-dark', 'night-amber', 'night-canvas', 4.5],
  ['error-dark', 'night-error', 'night-canvas', 4.5],
]

function readHexToken(name) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = new RegExp(`--${escaped}:\\s*(#[0-9a-f]{6})\\s*;`, 'i').exec(css)
  if (!match) throw new Error(`Missing sRGB fallback for --${name}`)
  return match[1]
}

function hexToRgb(hex) {
  const value = Number.parseInt(hex.slice(1), 16)
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
}

function relativeLuminance(hex) {
  const channels = hexToRgb(hex).map((channel) => {
    const value = channel / 255
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

function contrastRatio(foreground, background) {
  const a = relativeLuminance(foreground)
  const b = relativeLuminance(background)
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)
}

let failed = false
for (const [name, foregroundToken, backgroundToken, threshold] of pairs) {
  const ratio = contrastRatio(readHexToken(foregroundToken), readHexToken(backgroundToken))
  console.log(`${name} ${ratio.toFixed(2)} ${threshold.toFixed(1)}`)
  if (ratio < threshold) failed = true
}

if (failed) process.exitCode = 1
```

- [ ] **Step 6: Chạy GREEN và commit Task 1**

```powershell
node scripts/check-tri-region-contrast.mjs
npm test -- tests/tri-region-color-contract.test.ts tests/nocturne-theme-contract.test.ts tests/theme-mode-control.test.ts
npm run typecheck
git add assets/css/variables.css assets/css/tri-region-color.css nuxt.config.ts tests/tri-region-color-contract.test.ts tests/nocturne-theme-contract.test.ts scripts/check-tri-region-contrast.mjs
git commit -m "feat(ui): add tri-region semantic color foundation"
```

Expected: contrast script in đủ 15 pair và exit `0`; tests PASS; typecheck PASS; commit chỉ chứa file Task 1.

---

### Task 2: Tạo Typed Accent, SourceMark Và FreshnessLine

**Files:**
- Create: `web-nuxt/utils/regionalColor.ts`
- Modify: `web-nuxt/types/index.ts`
- Create: `web-nuxt/components/SourceMark.vue`
- Create: `web-nuxt/components/FreshnessLine.vue`
- Create: `web-nuxt/tests/regional-color.test.ts`
- Create: `web-nuxt/tests/source-freshness-mark.test.ts`

**Interfaces:**
- Produces: `RegionalAccent = 'clay' | 'leaf' | 'river' | 'amber' | 'neutral'`.
- Produces: `SourceTier = 'official' | 'verified' | 'community' | 'unknown'`.
- Produces: `FreshnessStatus = 'fresh' | 'aging' | 'stale' | 'unknown'`.
- Produces: `resolveRegionalAccent(category?: string | null): RegionalAccent`, `resolveSourceTier(sourceTier?: unknown): SourceTier`, `resolveFreshnessStatus(status?: unknown): FreshnessStatus`.
- `SourceMark` consumes `{ tier: SourceTier; compact?: boolean }`; `FreshnessLine` consumes `{ status: FreshnessStatus; updatedLabel: string }`.

- [ ] **Step 1: Viết resolver và mounted component tests RED**

Create `web-nuxt/tests/regional-color.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { resolveFreshnessStatus, resolveRegionalAccent, resolveSourceTier } from '../utils/regionalColor'

describe('regional color resolver', () => {
  it.each([
    ['craft_village', 'clay'],
    ['pottery', 'clay'],
    ['product', 'clay'],
    ['nature', 'leaf'],
    ['agriculture', 'leaf'],
    ['experience', 'river'],
    ['accommodation', 'river'],
    ['dish', 'amber'],
    ['event', 'amber'],
    ['directory', 'neutral'],
    ['free community text', 'neutral'],
    [undefined, 'neutral'],
  ] as const)('maps %s to %s without location or image input', (input, expected) => {
    expect(resolveRegionalAccent(input)).toBe(expected)
  })

  it('normalizes only approved source-tier aliases', () => {
    expect(resolveSourceTier('official')).toBe('official')
    expect(resolveSourceTier('government')).toBe('official')
    expect(resolveSourceTier('partner')).toBe('verified')
    expect(resolveSourceTier('ugc')).toBe('community')
    expect(resolveSourceTier('gold')).toBe('unknown')
    expect(resolveSourceTier('https://gov.vn')).toBe('unknown')
  })

  it('normalizes freshness without inventing recency', () => {
    expect(resolveFreshnessStatus('fresh')).toBe('fresh')
    expect(resolveFreshnessStatus('aging')).toBe('aging')
    expect(resolveFreshnessStatus('stale')).toBe('stale')
    expect(resolveFreshnessStatus('yesterday')).toBe('unknown')
  })
})
```

Create `web-nuxt/tests/source-freshness-mark.test.ts` with mounted assertions:

```ts
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, it } from 'vitest'
import FreshnessLine from '../components/FreshnessLine.vue'
import SourceMark from '../components/SourceMark.vue'

describe('source and freshness primitives', () => {
  it.each([
    ['official', 'Chính thức', 'shield'],
    ['verified', 'Đã xác minh', 'check'],
    ['community', 'Cộng đồng', 'user'],
    ['unknown', 'Chưa rõ nguồn', 'info'],
  ] as const)('shows icon and visible label for %s', async (tier, label, icon) => {
    const wrapper = await mountSuspended(SourceMark, {
      props: { tier },
      global: { stubs: { IconLine: { props: ['name'], template: '<i :data-icon="name" />' } } },
    })

    expect(wrapper.get('[data-source-mark]').attributes('data-source-tier')).toBe(tier)
    expect(wrapper.get('[data-source-mark]').text()).toContain(label)
    expect(wrapper.get(`[data-icon="${icon}"]`)).toBeTruthy()
  })

  it('keeps freshness separate from provenance', async () => {
    const wrapper = await mountSuspended(FreshnessLine, {
      props: { status: 'stale', updatedLabel: '12/07/2026' },
      global: { stubs: { IconLine: true } },
    })

    expect(wrapper.get('[data-freshness-line]').attributes('data-freshness-status')).toBe('stale')
    expect(wrapper.text()).toContain('Có thể đã cũ')
    expect(wrapper.text()).toContain('12/07/2026')
    expect(wrapper.find('[data-source-mark]').exists()).toBe(false)
  })
})
```

- [ ] **Step 2: Chạy tests và xác nhận RED**

```powershell
npm test -- tests/regional-color.test.ts tests/source-freshness-mark.test.ts
```

Expected: FAIL vì utility và hai component chưa tồn tại.

- [ ] **Step 3: Implement resolver thuần, không có runtime color engine**

Create `web-nuxt/utils/regionalColor.ts`:

```ts
export type RegionalAccent = 'clay' | 'leaf' | 'river' | 'amber' | 'neutral'
export type SourceTier = 'official' | 'verified' | 'community' | 'unknown'
export type FreshnessStatus = 'fresh' | 'aging' | 'stale' | 'unknown'

const REGIONAL_ACCENT_BY_CATEGORY: Readonly<Record<string, RegionalAccent>> = Object.freeze({
  craft: 'clay',
  craft_village: 'clay',
  pottery: 'clay',
  product: 'clay',
  nature: 'leaf',
  agriculture: 'leaf',
  orchard: 'leaf',
  experience: 'river',
  accommodation: 'river',
  transport: 'river',
  river: 'river',
  dish: 'amber',
  food: 'amber',
  event: 'amber',
  festival: 'amber',
  season: 'amber',
})

const SOURCE_TIER_ALIASES: Readonly<Record<string, SourceTier>> = Object.freeze({
  official: 'official',
  government: 'official',
  gov: 'official',
  verified: 'verified',
  partner: 'verified',
  community: 'community',
  ugc: 'community',
})

export function resolveRegionalAccent(category?: string | null): RegionalAccent {
  if (typeof category !== 'string') return 'neutral'
  return REGIONAL_ACCENT_BY_CATEGORY[category.trim().toLowerCase()] || 'neutral'
}

export function resolveSourceTier(sourceTier?: unknown): SourceTier {
  if (typeof sourceTier !== 'string') return 'unknown'
  return SOURCE_TIER_ALIASES[sourceTier.trim().toLowerCase()] || 'unknown'
}

export function resolveFreshnessStatus(status?: unknown): FreshnessStatus {
  return status === 'fresh' || status === 'aging' || status === 'stale' ? status : 'unknown'
}
```

Trong `types/index.ts`, import type `FreshnessStatus` và đổi `freshness_status` thành `FreshnessStatus | string`; giữ `source_tier?: string` để không phá payload legacy.

- [ ] **Step 4: Implement SourceMark và FreshnessLine có nhãn nhìn thấy được**

`SourceMark.vue` dùng lookup bất biến:

```ts
const SOURCE_META = {
  official: { label: 'Chính thức', icon: 'shield' },
  verified: { label: 'Đã xác minh', icon: 'check' },
  community: { label: 'Cộng đồng', icon: 'user' },
  unknown: { label: 'Chưa rõ nguồn', icon: 'info' },
} as const
```

Template root bắt buộc là:

```vue
<span
  class="source-mark"
  data-source-mark
  data-color-role="trust"
  :data-source-tier="tier"
  :class="{ 'source-mark--compact': compact }"
>
  <IconLine :name="meta.icon" aria-hidden="true" />
  <span>{{ meta.label }}</span>
</span>
```

`FreshnessLine.vue` map `fresh → Mới cập nhật`, `aging → Cần kiểm tra định kỳ`, `stale → Có thể đã cũ`, `unknown → Chưa rõ thời điểm cập nhật`; root có `data-freshness-line`, `data-color-role="status"`, `data-freshness-status`, icon `clock` và luôn hiển thị `updatedLabel` khi chuỗi không rỗng.

Style hai component chỉ dùng semantic tokens: Official River, Verified Orchard, Community neutral, stale/error Coral, aging Amber; không raw hex, không gradient và không màu-only state.

- [ ] **Step 5: Chạy GREEN và commit Task 2**

```powershell
npm test -- tests/regional-color.test.ts tests/source-freshness-mark.test.ts
npm run typecheck
git add utils/regionalColor.ts types/index.ts components/SourceMark.vue components/FreshnessLine.vue tests/regional-color.test.ts tests/source-freshness-mark.test.ts
git commit -m "feat(ui): add regional accent and trust primitives"
```

Expected: tests PASS; typecheck PASS; resolver không import Vue, browser API, storage, network, clock hoặc location.

---

### Task 3: Áp Dụng Homepage B1 Color Recipe

**Files:**
- Modify: `web-nuxt/pages/index.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Modify: `web-nuxt/utils/homeNocturnePresentation.ts`
- Modify: `web-nuxt/components/home/HomeFeatureDossier.vue`
- Modify: `web-nuxt/components/home/HomeDecisionLedger.vue`
- Modify: `web-nuxt/components/home/HomeCategoryIndex.vue`
- Modify: `web-nuxt/tests/home-nocturne-presentation.test.ts`
- Modify: `web-nuxt/tests/home-nocturne-components.test.ts`
- Modify: `web-nuxt/tests/home-nocturne-page.test.ts`

**Interfaces:**
- Consumes: `RegionalAccent`, `resolveRegionalAccent`, `resolveSourceTier`, `SourceMark` và scoped CSS contract từ Task 1–2.
- Produces: Homepage root `data-color-system="tri-region-v1"`, `data-page-recipe="homepage"`, `data-material-accent="clay"`; typed `HomeCategoryLink.accent: RegionalAccent`; visible SourceMark trên hero feature; action/source/material attributes cho QA và CSS.

- [ ] **Step 1: Viết behavior tests RED cho root, action và trust**

Append hai test sau vào `web-nuxt/tests/home-nocturne-page.test.ts`, dùng trực tiếp `homeFixture`, `apiFetchMock`, `pageStubs`, `wrappers` và `flushUi` đã được định nghĩa trong file:

```ts
it('renders the homepage recipe with River action, Clay context and visible source tier', async () => {
  const fixture = homeFixture()
  fixture.experiences[0]!.quality = { source_tier: 'official' }
  apiFetchMock.mockImplementation((url: unknown) => {
    const path = String(url)
    if (path === '/api/homepage') return Promise.resolve(fixture)
    if (path === '/api/feed?limit=10') return Promise.resolve({ posts: [] })
    if (path === '/api/community/stats') return Promise.resolve(null)
    if (path === '/api/community/leaderboard?limit=3') return Promise.resolve({ leaders: [] })
    if (path === '/api/community/trending-tags?limit=8') return Promise.resolve({ tags: [] })
    if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
    return Promise.resolve({})
  })

  const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs } })
  wrappers.push(wrapper)
  await flushUi()

  const root = wrapper.get('[data-color-system="tri-region-v1"]')
  expect(root.attributes('data-page-recipe')).toBe('homepage')
  expect(root.attributes('data-material-accent')).toBe('clay')
  expect(wrapper.get('[data-home-search]').attributes('data-color-role')).toBe('action-primary')
  expect(wrapper.get('[data-source-mark]').text()).toContain('Chính thức')
  expect(wrapper.get('[data-source-mark]').attributes('data-source-tier')).toBe('official')
})

it('shows an honest unknown source label instead of inventing verification', async () => {
  apiFetchMock.mockImplementation((url: unknown) => {
    const path = String(url)
    if (path === '/api/homepage') return Promise.resolve(homeFixture())
    if (path === '/api/feed?limit=10') return Promise.resolve({ posts: [] })
    if (path === '/api/community/stats') return Promise.resolve(null)
    if (path === '/api/community/leaderboard?limit=3') return Promise.resolve({ leaders: [] })
    if (path === '/api/community/trending-tags?limit=8') return Promise.resolve({ tags: [] })
    if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
    return Promise.resolve({})
  })
  const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs } })
  wrappers.push(wrapper)
  await flushUi()

  expect(wrapper.get('[data-source-mark]').text()).toContain('Chưa rõ nguồn')
  expect(wrapper.text()).not.toContain('Đã xác minh')
})
```

Update presentation test để expected accent order là `leaf`, `amber`, `clay`, `amber`, `river`, `river`, `river`; update component test để mỗi category link có `data-material-accent` hợp lệ và feature dossier hiển thị đúng SourceMark.

- [ ] **Step 2: Chạy homepage tests và xác nhận RED**

```powershell
npm test -- tests/home-nocturne-presentation.test.ts tests/home-nocturne-components.test.ts tests/home-nocturne-page.test.ts
```

Expected: FAIL vì root/role attributes và SourceMark chưa được tích hợp; `HomeCategoryLink.accent` vẫn là `string` và festival/accommodation/planner mapping chưa đúng recipe.

- [ ] **Step 3: Type hóa accent và tích hợp SourceMark không bịa trust**

Trong `homeNocturnePresentation.ts`:

```ts
import type { RegionalAccent } from '~/utils/regionalColor'

export type HomeCategoryLink = {
  key: string
  label: string
  hint: string
  to: string
  icon: string
  accent: RegionalAccent
  countLabel?: string
}
```

Giữ mapping tĩnh đã duyệt: Du lịch `leaf`, Ẩm thực `amber`, OCOP `clay`, Lễ hội `amber`, Lưu trú `river`, Lịch trình `river`, Bản đồ `river`.

`HomeFeatureDossier.vue` nhận prop `sourceTier: SourceTier`, render `<SourceMark :tier="sourceTier" compact />` trong dossier metadata và không đọc URL để suy source tier. `index.vue` truyền `resolveSourceTier(feature?.quality?.source_tier)`.

`HomeDecisionLedger.vue` đặt `:data-material-accent="resolveRegionalAccent(entry.tone)"`; `HomeCategoryIndex.vue` đổi `data-accent` cũ thành `data-material-accent` và giữ cùng DOM order.

- [ ] **Step 4: Gắn root/page/action roles và migrate màu cục bộ**

Root Homepage B1 trở thành:

```vue
<div
  class="home"
  data-home-pilot="nocturne-b1"
  data-color-system="tri-region-v1"
  data-page-recipe="homepage"
  data-material-accent="clay"
>
```

Gắn `data-color-role="action-primary"` vào SearchAutocomplete wrapper/prop passthrough, `action-secondary` cho hero detail/planner actions, `brand` cho chapter marker và `trust` chỉ cho SourceMark.

Trong `index.vue` scoped style, thay toàn bộ legacy `var(--primary*)` và raw hex màu bằng semantic token tương ứng. Quy tắc bắt buộc:

```text
focus outline -> --color-focus
interactive text/border -> --color-action / --color-action-border
event date and food/season markers -> --color-material-amber
community avatar -> --color-source-community + --color-source-community-surface
dark leaf/river literals -> --color-material-leaf / --color-material-river
mask #000 -> --color-mask-opaque
homepage atmospheric tint -> color-mix(... var(--color-material-clay) ...)
```

`home-nocturne.css` giữ geometry B1, bổ sung solid material hairline và SourceMark spacing; không thêm gradient đa sắc. Homepage page/component files sau task phải có `0` raw hex và `0` `var(--primary*)`.

- [ ] **Step 5: Chạy GREEN, regression và commit Task 3**

```powershell
npm test -- tests/home-nocturne-presentation.test.ts tests/home-nocturne-components.test.ts tests/home-nocturne-page.test.ts tests/ugc-image-classification.test.ts tests/theme-mode-control.test.ts
npm run typecheck
git add pages/index.vue assets/css/home-nocturne.css utils/homeNocturnePresentation.ts components/home/HomeFeatureDossier.vue components/home/HomeDecisionLedger.vue components/home/HomeCategoryIndex.vue tests/home-nocturne-presentation.test.ts tests/home-nocturne-components.test.ts tests/home-nocturne-page.test.ts
git commit -m "feat(home): apply tri-region color recipe"
```

Expected: tất cả PASS; section order, API request, disclosure, image policy, retry/community isolation và category routes của Homepage B1 không đổi.

---

### Task 4: Áp Dụng Discovery Recipe Cho `/du-lich`

**Files:**
- Modify: `web-nuxt/pages/du-lich.vue`
- Modify: `web-nuxt/components/EntityCard.vue`
- Modify: `web-nuxt/components/CatalogSpotlight.vue`
- Modify: `web-nuxt/components/CatalogInterstitial.vue`
- Modify: `web-nuxt/assets/css/tri-region-color.css`
- Create: `web-nuxt/tests/discovery-tri-region-color.test.ts`
- Modify: `web-nuxt/tests/entity-card-disclosure.test.ts`

**Interfaces:**
- `EntityCard` adds optional `colorRecipe?: 'tri-region-v1'`; when enabled it emits `data-color-recipe`, `data-material-accent` and one `SourceMark` from explicit `entity.quality.source_tier`.
- `CatalogSpotlight` adds optional `colorRecipe?: 'tri-region-v1'`; selected entity accent comes from `resolveRegionalAccent(entity.type)`.
- `CatalogInterstitial` adds optional `materialAccent?: RegionalAccent`, default `neutral`.
- `/du-lich` root material accent follows the user-selected hero mode only: trải nghiệm `leaf`, ẩm thực `amber`, làng nghề `clay`, lưu trú `river`.

- [ ] **Step 1: Viết mounted discovery test RED**

Create `web-nuxt/tests/discovery-tri-region-color.test.ts` với setup đầy đủ sau; giữ real `EntityCard`, `CatalogSpotlight`, `CatalogInterstitial`, `SourceMark`:

```ts
import { clearNuxtData } from '#app'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TourismPage from '../pages/du-lich.vue'

const apiFetchMock = vi.hoisted(() => vi.fn())
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))

const wrappers: Array<{ unmount: () => void }> = []
const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: String, alt: String },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})
const stubs = {
  NuxtImg: NuxtImgStub,
  Breadcrumb: true,
  CountUp: { props: ['value'], template: '<span>{{ value }}</span>' },
  FilterChips: true,
  EmptyState: true,
  SkeletonGrid: true,
  SaveButton: true,
  ImageDisclosure: true,
  JourneyBar: true,
  IconLine: { props: ['name'], template: '<i :data-icon="name" />' },
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

beforeEach(() => apiFetchMock.mockReset())
afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  await clearNuxtData()
})
```

Sau setup, thêm hai behavior tests:

```ts
it('changes one approved material accent when the user changes discovery mode', async () => {
  apiFetchMock.mockResolvedValue({
    entities: [
      { id: 'craft-1', type: 'craft_village', name: 'Làng gốm', quality: { source_tier: 'official' } },
      { id: 'stay-1', type: 'accommodation', name: 'Nhà vườn', quality: { source_tier: 'verified' } },
    ],
    total: 2,
  })

  const wrapper = await mountSuspended(TourismPage, { global: { stubs } })
  wrappers.push(wrapper)
  await flushUi()

  const root = wrapper.get('[data-page-recipe="discovery"]')
  expect(root.attributes('data-material-accent')).toBe('leaf')
  expect(wrapper.text()).toContain('Chính thức')
  expect(wrapper.text()).toContain('Đã xác minh')

  const craftMode = wrapper.findAll('.mode-pill').find(button => button.text().includes('Làng nghề'))
  expect(craftMode).toBeTruthy()
  await craftMode!.trigger('click')
  expect(root.attributes('data-material-accent')).toBe('clay')
  expect(wrapper.findAll('[data-material-accent="clay"]').length).toBeGreaterThan(0)
})

it('keeps filter selection understandable without relying on color', async () => {
  const wrapper = await mountSuspended(TourismPage, { global: { stubs } })
  wrappers.push(wrapper)
  await flushUi()

  const selected = wrapper.get('.mode-pill[aria-pressed="true"]')
  expect(selected.text()).toContain('Trải nghiệm')
  expect(selected.classes()).toContain('active')
})
```

- [ ] **Step 2: Chạy discovery tests và xác nhận RED**

```powershell
npm test -- tests/discovery-tri-region-color.test.ts tests/entity-card-disclosure.test.ts
```

Expected: FAIL vì page root, dynamic material accent, `colorRecipe` props và SourceMark chưa tồn tại.

- [ ] **Step 3: Tích hợp page recipe và shared card trust**

Đổi root `/du-lich`:

```vue
<div
  class="page"
  data-color-system="tri-region-v1"
  data-page-recipe="discovery"
  :data-material-accent="activeMode.accent"
>
```

Mỗi `heroModes` thêm typed `accent`; pass `color-recipe="tri-region-v1"` cho mọi `EntityCard` và `CatalogSpotlight`; pass `material-accent="amber"` cho interstitial fact.

`EntityCard` chỉ render SourceMark khi `colorRecipe === 'tri-region-v1'`; tier lấy bằng `resolveSourceTier(entity.quality?.source_tier)`, vì vậy unknown vẫn hiện nhãn trung thực thay vì giả verified. Card rule trở thành solid `var(--tri-region-material-accent)`; image disclosure giữ neutral và không mượn source color.

- [ ] **Step 4: Bổ sung Discovery scoped CSS và loại multi-accent prominence**

Trong `tri-region-color.css`, thêm selector dưới `[data-page-recipe="discovery"]` để:

```css
[data-color-system="tri-region-v1"][data-page-recipe="discovery"] .mode-pill[aria-pressed="true"] {
  border-color: var(--color-brand);
  background: var(--color-brand-surface);
  color: var(--color-text);
  box-shadow: inset 3px 0 0 var(--color-brand);
}

[data-color-system="tri-region-v1"][data-page-recipe="discovery"] :is(.card-rule, .cspot-rule, .catalog-interstitial-rule) {
  background: var(--tri-region-material-accent);
}

[data-color-system="tri-region-v1"][data-page-recipe="discovery"] :is(.atlas-hero, .card, .cspot, .catalog-interstitial) {
  box-shadow: none;
}
```

Migrate toàn bộ `var(--primary*)` trong `du-lich.vue`, `EntityCard.vue`, `CatalogSpotlight.vue`, `CatalogInterstitial.vue` sang `--color-action`, `--color-focus`, `--color-brand`, source/status/material token theo nghĩa thật. Bốn file component/page này phải có `0` raw hex và `0` legacy `var(--primary*)` sau task; không rewrite `catalog.css`.

- [ ] **Step 5: Chạy GREEN, regression và commit Task 4**

```powershell
npm test -- tests/discovery-tri-region-color.test.ts tests/entity-card-disclosure.test.ts tests/entity-image-detail.test.ts tests/tri-region-color-contract.test.ts
npm run typecheck
git add pages/du-lich.vue components/EntityCard.vue components/CatalogSpotlight.vue components/CatalogInterstitial.vue assets/css/tri-region-color.css tests/discovery-tri-region-color.test.ts tests/entity-card-disclosure.test.ts
git commit -m "feat(discovery): apply tri-region color recipe"
```

Expected: page behavior PASS, image disclosure regression PASS, active mode vẫn có text + `aria-pressed`, không có theme/location automation mới.

---

### Task 5: Áp Dụng Search Recipe Cho `/tim-kiem`

**Files:**
- Modify: `web-nuxt/pages/tim-kiem.vue`
- Modify: `web-nuxt/assets/css/tri-region-color.css`
- Create: `web-nuxt/tests/search-tri-region-color.test.ts`

**Interfaces:**
- Consumes `EntityCard colorRecipe="tri-region-v1"` từ Task 4.
- Produces Search root `data-page-recipe="search"`, material accent mặc định `neutral`, River search/focus actions, Clay là một editorial tick duy nhất và trust labels trên entity results.

- [ ] **Step 1: Viết mounted search behavior test RED**

Create `web-nuxt/tests/search-tri-region-color.test.ts` với setup cụ thể:

```ts
import { clearNuxtData } from '#app'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import SearchPage from '../pages/tim-kiem.vue'

const searchAllMock = vi.hoisted(() => vi.fn())
const fetchSuggestionsMock = vi.hoisted(() => vi.fn().mockResolvedValue([]))
vi.mock('../composables/useUnifiedSearch', () => ({
  useUnifiedSearch: () => ({
    searchAll: searchAllMock,
    fetchEntitySuggestions: fetchSuggestionsMock,
  }),
}))

const wrappers: Array<{ unmount: () => void }> = []
const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: String, alt: String },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})
const stubs = {
  NuxtImg: NuxtImgStub,
  Breadcrumb: true,
  EmptyState: { props: ['title', 'message'], template: '<div data-empty-state><strong>{{ title }}</strong><span>{{ message }}</span><slot name="actions" /></div>' },
  SkeletonGrid: true,
  SaveButton: true,
  ImageDisclosure: true,
  SmartRecommendations: true,
  JourneyActionRail: true,
  IconLine: { props: ['name'], template: '<i :data-icon="name" />' },
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

beforeEach(() => {
  searchAllMock.mockReset()
  fetchSuggestionsMock.mockClear()
  localStorage.clear()
})
afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  await clearNuxtData()
})
```

Sau setup, thêm hai behavior tests; test đầu để `searchAll('gốm')` trả entity `craft_village` source tier `official`:

```ts
it('shows semantic search state and source labels for real results', async () => {
  searchAllMock.mockResolvedValue({
    entities: [{ id: 'craft-1', type: 'craft_village', name: 'Gốm đỏ Mang Thít', quality: { source_tier: 'official' } }],
    posts: [],
    users: [],
    totals: { entities: 1, posts: 0, users: 0 },
  })

  const wrapper = await mountSuspended(SearchPage, {
    route: '/tim-kiem?q=g%E1%BB%91m',
    global: { stubs },
  })
  wrappers.push(wrapper)
  await flushUi()

  const root = wrapper.get('[data-page-recipe="search"]')
  expect(root.attributes('data-material-accent')).toBe('neutral')
  expect(wrapper.get('input[type="search"]').element.value).toBe('gốm')
  expect(wrapper.get('[data-color-role="action-primary"]')).toBeTruthy()
  expect(wrapper.get('[data-source-mark]').text()).toContain('Chính thức')
  expect(wrapper.get('[data-material-accent="clay"]').text()).toContain('Gốm đỏ Mang Thít')
})

it('keeps an error visible in text and aria, not only Coral', async () => {
  searchAllMock.mockRejectedValue(new Error('search unavailable'))
  const wrapper = await mountSuspended(SearchPage, {
    route: '/tim-kiem?q=g%E1%BB%91m',
    global: { stubs },
  })
  wrappers.push(wrapper)
  await flushUi()

  expect(wrapper.get('[role="alert"]').text()).toContain('Không thể tìm kiếm')
  expect(wrapper.get('input[type="search"]').attributes('aria-invalid')).toBe('true')
})
```

- [ ] **Step 2: Chạy search test và xác nhận RED**

```powershell
npm test -- tests/search-tri-region-color.test.ts
```

Expected: FAIL vì root/role attributes chưa có, EntityCard chưa nhận recipe và error hiện tại chưa có `role="alert"` contract.

- [ ] **Step 3: Tích hợp Search recipe và migrate màu cục bộ**

Root page:

```vue
<div
  class="page"
  data-color-system="tri-region-v1"
  data-page-recipe="search"
  data-material-accent="neutral"
>
```

Gắn `data-color-role="action-primary"` cho submit/search affordance; `data-color-role="status-error"` và `role="alert"` cho error panel; pass `color-recipe="tri-region-v1"` cho result EntityCard.

Thay sediment tri-color line bằng một Clay editorial tick; River chỉ dùng search, hover và clickable affordance, focus dùng token theme, còn selected suggestion dùng Clay marker cộng `aria-selected`/active structure. Migrate toàn bộ raw hex và `var(--primary*)` trong `tim-kiem.vue` sang semantic token; file phải có `0` raw hex và `0` legacy primary sau task.

- [ ] **Step 4: Bổ sung scoped Search CSS**

Trong `tri-region-color.css`, thêm:

```css
[data-color-system="tri-region-v1"][data-page-recipe="search"] .search-row-hero::before {
  background: var(--color-material-clay);
}

[data-color-system="tri-region-v1"][data-page-recipe="search"] :is(.trending-chip, .quick-pick, .recent-card):hover {
  border-color: var(--color-action);
  background: var(--color-action-surface);
}

[data-color-system="tri-region-v1"][data-page-recipe="search"] [role="alert"] {
  border-color: var(--color-error);
  color: var(--color-error);
}
```

Không đổi search API, suggestions keyboard behavior, recent searches, result ordering hoặc JourneyAction logic.

- [ ] **Step 5: Chạy GREEN, regression và commit Task 5**

```powershell
npm test -- tests/search-tri-region-color.test.ts tests/entity-card-disclosure.test.ts tests/tri-region-color-contract.test.ts
npm run typecheck
git add pages/tim-kiem.vue assets/css/tri-region-color.css tests/search-tri-region-color.test.ts
git commit -m "feat(search): apply tri-region color recipe"
```

Expected: tests PASS; keyboard combobox, retry, zero-result actions và route query behavior không đổi.

---

### Task 6: Áp Dụng Entity Detail Trust, Media Và Action Recipe

**Files:**
- Create: `web-nuxt/components/EntityTrustPanel.vue`
- Modify: `web-nuxt/pages/dia-diem/[id].vue`
- Modify: `web-nuxt/components/ContactWidget.vue`
- Modify: `web-nuxt/components/ImageDisclosure.vue`
- Modify: `web-nuxt/components/EntityHeroPlaceholder.vue`
- Modify: `web-nuxt/assets/css/tri-region-color.css`
- Create: `web-nuxt/tests/detail-tri-region-color.test.ts`
- Modify: `web-nuxt/tests/entity-image-detail.test.ts`

**Interfaces:**
- `EntityTrustPanel` consumes `{ tier: SourceTier; sourceTitle: string; sourceUrl?: string; freshnessStatus: FreshnessStatus; updatedLabel: string; note: string; reportTo: string }`.
- Entity Detail root uses `resolveRegionalAccent(entity.type)`; contact actions keep direct-contact model: Zalo primary River, phone/map secondary River, no booking/payment loop.
- ImageDisclosure remains neutral and independent from SourceMark; EntityHeroPlaceholder only emits material context derived from entity type/category, never from generated image color.

- [ ] **Step 1: Viết mounted detail behavior tests RED**

Create `web-nuxt/tests/detail-tri-region-color.test.ts`:

```ts
import { clearNuxtData } from '#app'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ContactWidget from '../components/ContactWidget.vue'
import EntityTrustPanel from '../components/EntityTrustPanel.vue'
import EntityDetailPage from '../pages/dia-diem/[id].vue'

const apiFetchMock = vi.hoisted(() => vi.fn())
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))

const wrappers: Array<{ unmount: () => void }> = []
const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: String, alt: String },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  apiFetchMock.mockReset()
  await clearNuxtData()
})

describe('entity detail tri-region behavior', () => {
  it('separates official provenance, stale severity and report action', async () => {
    const wrapper = await mountSuspended(EntityTrustPanel, {
      props: {
        tier: 'official',
        sourceTitle: 'Cổng thông tin tỉnh Vĩnh Long',
        sourceUrl: 'https://example.gov.vn/source',
        freshnessStatus: 'stale',
        updatedLabel: '12/07/2026',
        note: 'Thông tin có thể đã cũ; hãy kiểm tra trước khi đi.',
        reportTo: '/cong-dong?report=entity-1',
      },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[data-source-mark]').text()).toContain('Chính thức')
    expect(wrapper.get('[data-freshness-line]').text()).toContain('Có thể đã cũ')
    expect(wrapper.get('[data-source-link]').text()).toContain('Cổng thông tin tỉnh Vĩnh Long')
    expect(wrapper.get('[data-report-action]').attributes('href')).toBe('/cong-dong?report=entity-1')
  })

  it('keeps the direct-contact model and semantic action order', async () => {
    const wrapper = await mountSuspended(ContactWidget, {
      props: {
        entity: {
          id: 'entity-1',
          name: 'Nhà vườn ven sông',
          attributes: { zalo: '0900000000', phone: '0900000000' },
        },
      },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    const actions = wrapper.findAll('.cw-btn')
    expect(actions.map(action => action.text())).toEqual(['Nhắn Zalo', 'Gọi điện'])
    expect(actions[0]!.attributes('data-color-role')).toBe('action-primary')
    expect(actions[1]!.attributes('data-color-role')).toBe('action-secondary')
    expect(wrapper.text()).not.toContain('Đặt ngay')
    expect(wrapper.text()).not.toContain('Thanh toán')
  })
})
```

Append mounted page test sau vào cùng file:

```ts
it('mounts detail data and keeps material, trust and image disclosure as separate layers', async () => {
  const entity = {
    id: 'entity-1',
    type: 'craft_village',
    name: 'Làng gốm Mang Thít',
    summary: 'Không gian nghề gốm ven sông.',
    description: 'Một làng nghề lâu đời bên dòng Cổ Chiên.',
    place_name: 'Mang Thít',
    attributes: { phone: '0900000000', address: 'Mang Thít, Vĩnh Long' },
    quality: {
      source_tier: 'official',
      source_title: 'Cổng thông tin tỉnh Vĩnh Long',
      source_url: 'https://example.gov.vn/source',
    },
    source_freshness: {
      source_title: 'Cổng thông tin tỉnh Vĩnh Long',
      source_url: 'https://example.gov.vn/source',
      freshness_status: 'fresh',
      updated_at: '2026-07-30T00:00:00Z',
    },
  }
  apiFetchMock.mockImplementation((url: unknown) => {
    const path = String(url)
    if (path === '/api/entities/entity-1') return Promise.resolve(entity)
    if (path === '/api/entities/entity-1/gallery') return Promise.resolve({ images: [] })
    if (path === '/seo/jsonld/entity-1') return Promise.resolve(null)
    if (path.startsWith('/api/entities/entity-1/relationships')) return Promise.resolve({ relationships: [], total: 0 })
    return Promise.resolve({})
  })

  const wrapper = await mountSuspended(EntityDetailPage, {
    route: '/dia-diem/entity-1',
    global: {
      stubs: {
        NuxtImg: NuxtImgStub,
        Breadcrumb: true,
        SaveButton: true,
        ShareButton: true,
        IconLine: { props: ['name'], template: '<i :data-icon="name" />' },
        EntityMap: true,
        EntityFeed: true,
        ReviewSection: true,
        JourneyBar: true,
        AIBestTime: true,
        ContactWidget: true,
        LazyContactWidget: true,
      },
    },
  })
  wrappers.push(wrapper)
  await flushUi()

  const root = wrapper.get('[data-page-recipe="detail"]')
  expect(root.attributes('data-material-accent')).toBe('clay')
  expect(wrapper.get('[data-source-mark]').text()).toContain('Chính thức')
  expect(wrapper.get('[data-freshness-line]').text()).toContain('Mới cập nhật')
  expect(wrapper.get('[data-image-disclosure]').text()).not.toContain('Chính thức')
  expect(wrapper.get('[data-entity-trust-panel]').text()).not.toContain('Ảnh minh họa')
})
```

- [ ] **Step 2: Chạy detail tests và xác nhận RED**

```powershell
npm test -- tests/detail-tri-region-color.test.ts tests/entity-image-detail.test.ts
```

Expected: FAIL vì EntityTrustPanel và semantic action roles chưa tồn tại; detail page vẫn inline trust card.

- [ ] **Step 3: Tách EntityTrustPanel và dùng explicit source/freshness resolver**

`EntityTrustPanel.vue` anatomy bắt buộc:

```vue
<section class="entity-trust-panel" data-entity-trust-panel aria-labelledby="entity-trust-title">
  <div class="entity-trust-panel__head">
    <h2 id="entity-trust-title">Độ tin cậy dữ liệu</h2>
    <SourceMark :tier="tier" />
  </div>
  <FreshnessLine :status="freshnessStatus" :updated-label="updatedLabel" />
  <a v-if="sourceUrl" data-source-link :href="sourceUrl" target="_blank" rel="noopener nofollow">{{ sourceTitle }}</a>
  <span v-else data-source-label>{{ sourceTitle }}</span>
  <p>{{ note }}</p>
  <NuxtLink data-report-action :to="reportTo">Báo sai hoặc bổ sung nguồn</NuxtLink>
</section>
```

Trong detail page, thay trust markup cũ bằng component và truyền:

```ts
const trustTier = computed(() => resolveSourceTier(entity.value?.quality?.source_tier))
const trustFreshnessStatus = computed(() => resolveFreshnessStatus(sourceFreshness.value?.freshness_status))
const detailMaterialAccent = computed(() => resolveRegionalAccent(entity.value?.type))
```

Không suy Official từ domain và không suy Verified từ `verified_at`; `verified_at` chỉ ảnh hưởng freshness/byline. Nếu không có source tier, SourceMark hiển thị `Chưa rõ nguồn`. Nếu không có source URL, giữ đúng một report action và không tạo link nguồn giả.

- [ ] **Step 4: Gắn Detail root, action roles và media neutrality**

Root success state có:

```vue
<section
  v-if="entity"
  class="page entity-detail"
  data-color-system="tri-region-v1"
  data-page-recipe="detail"
  :data-material-accent="detailMaterialAccent"
>
```

`ContactWidget` gắn Zalo `data-color-role="action-primary"`, phone/map `action-secondary`; thay toàn bộ `var(--primary*)`, raw dark River literal và tri-color divider bằng semantic/action/material token. `ImageDisclosure` gắn `data-color-role="disclosure"` và chỉ dùng neutral surface/text/border. `EntityHeroPlaceholder` nhận optional `materialAccent` hoặc resolve từ `cat`, emit `data-material-accent`, không đọc descriptor URL/color.

Trong detail page scoped style thay `var(--primary*)` bằng action/focus token. Không rewrite `detail.css`; scoped bridge từ Task 1 làm legacy selectors bên trong detail page nhận River action.

- [ ] **Step 5: Bổ sung Detail scoped CSS**

Trong `tri-region-color.css`:

```css
[data-color-system="tri-region-v1"][data-page-recipe="detail"] .detail-cover::after {
  border-block-end: 3px solid var(--tri-region-material-accent);
}

[data-color-system="tri-region-v1"][data-page-recipe="detail"] :is(.facts-card, .entity-trust-panel) {
  border-color: var(--color-border);
  background: var(--color-surface);
  box-shadow: none;
}

[data-color-system="tri-region-v1"][data-page-recipe="detail"] :is(.scta-phone, .scta-plan, .cw-btn-primary) {
  background: var(--color-action);
  color: var(--color-on-action);
}

[data-color-system="tri-region-v1"][data-page-recipe="detail"] .image-disclosure {
  border-color: var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-muted);
}
```

Detail page, ContactWidget, ImageDisclosure, EntityHeroPlaceholder và EntityTrustPanel phải có `0` raw hex và `0` legacy `var(--primary*)`; compatibility debt còn lại chỉ nằm trong `detail.css`.

- [ ] **Step 6: Chạy GREEN, regression và commit Task 6**

```powershell
npm test -- tests/detail-tri-region-color.test.ts tests/entity-image-detail.test.ts tests/gallery-disclosure.test.ts tests/image-metadata-disclosure.test.ts tests/tri-region-color-contract.test.ts
npm run typecheck
git add components/EntityTrustPanel.vue pages/dia-diem/[id].vue components/ContactWidget.vue components/ImageDisclosure.vue components/EntityHeroPlaceholder.vue assets/css/tri-region-color.css tests/detail-tri-region-color.test.ts tests/entity-image-detail.test.ts
git commit -m "feat(detail): apply tri-region color and trust recipe"
```

Expected: tests PASS; direct contact, gallery, AI disclosure, source/freshness separation, report action và launch-safety behavior không regress.

---

### Task 7: Khóa Color Debt, Contrast, Visual Matrix Và Closure Evidence

**Files:**
- Create: `web-nuxt/config/tri-region-color-debt.json`
- Create: `web-nuxt/scripts/check-tri-region-color-debt.mjs`
- Create: `web-nuxt/tests/tri-region-color-ratchet.test.ts`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/report.md`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/home-nocturne-desktop-1440.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/home-nocturne-mobile-390.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/home-parchment-desktop-1440.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/home-parchment-mobile-390.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/discovery-nocturne-desktop-1440.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/discovery-nocturne-mobile-390.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/discovery-parchment-desktop-1440.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/discovery-parchment-mobile-390.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/search-nocturne-desktop-1440.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/search-nocturne-mobile-390.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/search-parchment-desktop-1440.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/search-parchment-mobile-390.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/detail-nocturne-desktop-1440.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/detail-nocturne-mobile-390.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/detail-parchment-desktop-1440.webp`
- Create: `docs/superpowers/qa/2026-07-31-tri-region-color/detail-parchment-mobile-390.webp`
- Modify: `docs/superpowers/specs/2026-07-31-tri-region-color-excellence-design.md`
- Modify: `docs/superpowers/plans/2026-07-31-tri-region-color-excellence.md`

**Interfaces:**
- Debt checker reads exact per-file budgets and exits non-zero when raw hex hoặc `var(--primary*)` vượt ngân sách.
- QA report records route, viewport, theme, source fixture, accent budget, contrast result, grayscale/color-vision/forced-colors observations and screenshot filename.

- [ ] **Step 1: Viết ratchet test RED**

Create `web-nuxt/tests/tri-region-color-ratchet.test.ts`:

```ts
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('tri-region color debt ratchet', () => {
  it('keeps scoped wave files semantic and shared compatibility debt non-increasing', () => {
    const output = execFileSync(process.execPath, ['scripts/check-tri-region-color-debt.mjs'], {
      cwd: resolve(import.meta.dirname, '..'),
      encoding: 'utf8',
    })
    expect(output).toContain('tri-region color debt: PASS')
  })
})
```

- [ ] **Step 2: Chạy ratchet test và xác nhận RED**

```powershell
npm test -- tests/tri-region-color-ratchet.test.ts
```

Expected: FAIL vì config và script chưa tồn tại.

- [ ] **Step 3: Tạo debt manifest và checker chính xác**

Create `web-nuxt/config/tri-region-color-debt.json`:

```json
{
  "pages/index.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "assets/css/home-nocturne.css": { "rawHex": 0, "legacyPrimary": 0 },
  "pages/du-lich.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "pages/tim-kiem.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "pages/dia-diem/[id].vue": { "rawHex": 0, "legacyPrimary": 0 },
  "components/home/HomeFeatureDossier.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "components/home/HomeDecisionLedger.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "components/home/HomeCategoryIndex.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "components/SourceMark.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "components/FreshnessLine.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "components/EntityTrustPanel.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "components/EntityCard.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "components/CatalogSpotlight.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "components/CatalogInterstitial.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "components/ContactWidget.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "components/ImageDisclosure.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "components/EntityHeroPlaceholder.vue": { "rawHex": 0, "legacyPrimary": 0 },
  "assets/css/tri-region-color.css": { "rawHex": 0, "legacyPrimary": 0 },
  "assets/css/catalog.css": { "rawHex": 5, "legacyPrimary": 58 },
  "assets/css/detail.css": { "rawHex": 20, "legacyPrimary": 45 }
}
```

Checker phải đếm `var(--primary...)` usages riêng, không đếm custom-property declarations `--primary:`; vì scoped bridge chỉ khai báo alias bằng semantic token nên budget usage của `tri-region-color.css` là `0`.

Create `web-nuxt/scripts/check-tri-region-color-debt.mjs` với implementation đầy đủ:

```js
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()
const budgets = JSON.parse(readFileSync(resolve(root, 'config/tri-region-color-debt.json'), 'utf8'))
const rawHexPattern = /(?<![&\w-])#[0-9a-f]{3,8}\b/gi
const legacyPrimaryPattern = /var\(--primary(?:-[\w-]+)?/g

let failed = false
let sharedRawHex = 0
let sharedLegacyPrimary = 0

for (const [path, budget] of Object.entries(budgets)) {
  let source = ''
  try {
    source = readFileSync(resolve(root, path), 'utf8')
  } catch {
    console.error(`${path} missing`)
    failed = true
    continue
  }

  const rawHex = source.match(rawHexPattern)?.length || 0
  const legacyPrimary = source.match(legacyPrimaryPattern)?.length || 0
  console.log(`${path} rawHex=${rawHex}/${budget.rawHex} legacyPrimary=${legacyPrimary}/${budget.legacyPrimary}`)
  if (rawHex > budget.rawHex || legacyPrimary > budget.legacyPrimary) failed = true

  if (path === 'assets/css/catalog.css' || path === 'assets/css/detail.css') {
    sharedRawHex += rawHex
    sharedLegacyPrimary += legacyPrimary
  }
}

if (sharedRawHex > 25 || sharedLegacyPrimary > 103) {
  console.error(`shared debt rawHex=${sharedRawHex}/25 legacyPrimary=${sharedLegacyPrimary}/103`)
  failed = true
}

if (failed) {
  process.exitCode = 1
} else {
  console.log('tri-region color debt: PASS')
}
```

- [ ] **Step 4: Chạy toàn bộ automated quality gate**

```powershell
node scripts/check-tri-region-contrast.mjs
node scripts/check-tri-region-color-debt.mjs
npm test -- tests/tri-region-color-contract.test.ts tests/regional-color.test.ts tests/source-freshness-mark.test.ts tests/home-nocturne-presentation.test.ts tests/home-nocturne-components.test.ts tests/home-nocturne-page.test.ts tests/discovery-tri-region-color.test.ts tests/search-tri-region-color.test.ts tests/detail-tri-region-color.test.ts tests/tri-region-color-ratchet.test.ts tests/entity-card-disclosure.test.ts tests/entity-image-detail.test.ts tests/gallery-disclosure.test.ts tests/image-metadata-disclosure.test.ts tests/theme-mode-control.test.ts tests/ugc-image-classification.test.ts
npm run typecheck
npm run build
```

Expected: tất cả PASS; Nuxt build hoàn tất; không có raw hex mới hoặc legacy primary debt tăng.

- [ ] **Step 5: Chạy browser visual matrix và lưu evidence**

Start app trên port riêng không trùng session khác:

```powershell
npm run dev -- --host 127.0.0.1 --port 3189
```

Chụp đúng mười sáu screenshot đã khai báo: mỗi route có Nocturne desktop/mobile và Parchment desktop/mobile. Desktop dùng `1440x1000`; mobile dùng `390x844`. Với mỗi route, kiểm tra:

```text
Nocturne + Parchment semantic meaning không đổi
River action nhận ra trong 3 giây
Clay chỉ là brand/context, không giả CTA
Official/Verified/Community/Unknown có icon + nhãn
Warning/Error không lẫn source tier
chỉ một material accent nổi bật trong viewport
text trên ảnh có plate/scrim đủ đọc
200% zoom không clip
keyboard focus rõ
hover, selected, disabled và error vẫn phân biệt bằng structure/label
forced colors giữ structure/action
prefers-contrast tăng boundary
reduced motion không che final state
grayscale vẫn phân biệt selected/trust/status bằng structure và label
protanopia/deuteranopia/tritanopia không làm mất nghĩa
sRGB fallback trong webview cũ giữ đúng semantic
màn hình ngoài trời vẫn đọc được action/body text
OLED độ sáng thấp không làm mất border, muted text hoặc focus
```

Report phải ghi accent estimate: Homepage `8–10%`, Discovery/Search `4–6%`, Detail `6–8%`; nếu vượt, giảm accent trước khi chụp lại, không ghi “accepted deviation”.

- [ ] **Step 6: Cập nhật closure status và commit Task 7**

Trong spec đổi status thành `implemented — automated and visual gates passed`; trong plan đổi status thành `complete — implementation and QA evidence recorded`. Report phải liệt kê commit từng task và exact command output summary.

```powershell
git add config/tri-region-color-debt.json scripts/check-tri-region-color-debt.mjs tests/tri-region-color-ratchet.test.ts ../docs/superpowers/qa/2026-07-31-tri-region-color ../docs/superpowers/specs/2026-07-31-tri-region-color-excellence-design.md ../docs/superpowers/plans/2026-07-31-tri-region-color-excellence.md
git commit -m "test(ui): close tri-region color quality gates"
git status --short
git log --oneline --decorate -8
```

Expected: commit chỉ chứa debt checker, QA evidence và closure docs; `git status --short` sạch trong worktree triển khai.

## Final Acceptance Matrix

- Homepage, Discovery/Search và Entity Detail cùng nhận ra là Adaptive Nocturne Heritage nhưng có chromatic rhythm riêng.
- Nocturne và Daylight Parchment giữ cùng DOM order, action, trust/status meaning và material mapping.
- River là action; Clay là brand/context; Verified không còn dùng Clay; Community không dùng success như chứng nhận.
- Mọi source tier hiển thị icon + nhãn; freshness tách khỏi provenance; warning/danger tách khỏi source.
- Không có province theme, location-driven recolor, dominant-color extraction, runtime palette engine, Coir Umber hoặc Khmer Ochre primitive mới.
- Map/chart adapter và Campaign Capsule vẫn được ghi rõ là deferred follow-up; wave này không âm thầm đổi màu các hệ đó qua global selector.
- Homepage B1 routes/API/disclosure/recovery/community isolation vẫn đúng; Discovery filters và Search keyboard behavior không regress; Detail giữ direct contact, gallery disclosure và launch safety.
- Scoped wave files đạt raw-hex/legacy-primary budget; shared `catalog.css` + `detail.css` debt không tăng.
- Contrast script, behavior tests, typecheck, build và mười sáu browser screenshots đều hoàn tất trước khi closure status được đổi.
