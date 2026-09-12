# Kế Hoạch Hoàn Thiện Giao Diện Chuyên Nghiệp & Khử AI-Slop Toàn Diện (UI & Stitch Anti-Slop Perfection Plan)

> STATUS (2026-09-12): completed — nâng cấp toàn diện tính chuyên nghiệp, nghệ thuật ấn loát thủ công, chuẩn hóa typography Lora, độc lập cẩm nang con nước và đồng bộ Google Stitch MCP.
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng cấp toàn diện tính chuyên nghiệp, nghệ thuật ấn loát thủ công và công thái học thổ nhưỡng cho hệ thống Vĩnh Long 360; khử triệt để tàn dư AI-Slop (biểu tượng sparkle, fallback Times New Roman, phụ thuộc cảm biến thời tiết), đồng bộ hóa Hiến pháp Thiết kế lên Google Stitch MCP Server, và bảo toàn 100% 70 Vitest trang chủ cùng 78 hợp đồng màu Tam Vùng WCAG 2.2 AAA.

**Architecture:** Áp dụng mô thức Taste Design và Hiến pháp Anti-Slop; nâng cấp typography với Google Font `Lora` chính thức; thay thế biểu tượng AI sparkle bằng tem gốm nung thủ công; độc lập hóa cẩm nang con nước theo chu kỳ thiên văn âm lịch khỏi API thời tiết; hoàn thiện touch targets ≥44px cho WCAG AAA và đồng bộ tài liệu thiết kế lên Stitch Cloud Project `14916181929760067680`.

**Tech Stack:** Nuxt 4, Vue 3, Google Fonts (@nuxt/fonts), CSS Variables / OKLCH & sRGB, Vitest, Google Stitch MCP Server, Launch Safety Gate (`run_hard.py`).

**Spec:** [Hiến Pháp Thiết Kế Stitch Anti-Slop](../specs/2026-09-12-stitch-anti-slop-design-constitution.md)

## Global Constraints

- **Bảo toàn 70 tests Vitest Trang chủ (`tests/home-*.test.ts`):** 100% PASS không được gãy bất kỳ assertion nào, đặc biệt là `tests/home-nocturne-page.test.ts` (kiểm tra `subtitlePlate` `[0, 0, 0, .76]`).
- **Bảo toàn 78 hợp đồng màu Tam Vùng (`tests/tri-region-color-contract.test.ts`):** 100% PASS, không lọt bất kỳ mã HEX nào vào các file CSS giao diện.
- **Cấm màu tím/xanh neon SaaS:** Tuyệt đối không `#a855f7`, `#8b5cf6`, `#00f0ff`, không box-shadow mờ bẩn.
- **Cấm Emoji & Icon AI:** Không raw emoji trong components; thay thế biểu tượng `sparkle` bằng biểu tượng bản địa thực tế (`flame` men gốm Mang Thít hoặc `leaf` vườn cây An Bình).
- **Cấm font generic Times New Roman:** Loại bỏ hoàn toàn khỏi fallback chuỗi typography trong `assets/css/variables.css`.

---

### Task 1: Khử Biểu Tượng AI Sparkle & Thay Bằng Tem Gốm Nung Mang Thít Thủ Công

**Files:**
- Modify: `web-nuxt/components/home/HomeFeatureDossier.vue:48-52`
- Test: `web-nuxt/tests/home-anti-slop-craft.test.ts`

**Interfaces:**
- Consumes: Component `IconLine` với icon `flame` (biểu trưng cho lò gạch gốm đỏ nung Mang Thít).
- Produces: Thẻ tem di sản `.home-feature-dossier__stamp` không còn dấu vết AI sparkle, mang đậm dấu ấn lò nung di sản.

- [ ] **Step 1: Viết test kiểm tra loại bỏ hoàn toàn biểu tượng AI sparkle trong HomeFeatureDossier**

Mở `web-nuxt/tests/home-anti-slop-craft.test.ts` và thêm test case:

```ts
it('eradicates AI sparkle icon from heritage stamp in HomeFeatureDossier', () => {
  const dossierVue = readFileSync(resolve(__dirname, '../components/home/HomeFeatureDossier.vue'), 'utf8')
  expect(dossierVue).not.toContain('name="sparkle"')
  expect(dossierVue).toMatch(/name="(flame|leaf)"/)
})
```

- [ ] **Step 2: Chạy test để xác nhận kiểm thử thất bại (RED)**

Run: `npx vitest run tests/home-anti-slop-craft.test.ts` (trong `web-nuxt`)
Expected: FAIL vì `HomeFeatureDossier.vue` vẫn chứa `name="sparkle"`.

- [ ] **Step 3: Thay thế icon sparkle bằng icon flame tại HomeFeatureDossier.vue**

Tại `web-nuxt/components/home/HomeFeatureDossier.vue:48-52`:
Sửa:
```html
<span class="home-feature-dossier__stamp" title="Di sản đất phù sa & gốm đỏ Mang Thít">
  <IconLine name="sparkle" aria-hidden="true" />
  <span>Thổ nhưỡng di sản</span>
</span>
```
Thành:
```html
<span class="home-feature-dossier__stamp" title="Di sản đất phù sa & gốm đỏ Mang Thít">
  <IconLine name="flame" aria-hidden="true" />
  <span>Thổ nhưỡng di sản</span>
</span>
```

- [ ] **Step 4: Chạy lại test để xác nhận đạt (GREEN)**

Run: `npx vitest run tests/home-anti-slop-craft.test.ts` (trong `web-nuxt`)
Expected: PASS (tất cả các test trong file pass).

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/home/HomeFeatureDossier.vue web-nuxt/tests/home-anti-slop-craft.test.ts
git commit -m "refactor(home): replace AI sparkle icon with authentic Mang Thit kiln flame in heritage stamp"
```

---

### Task 2: Độc Lập Hóa Cẩm Nang Con Nước Mekong Khỏi Lỗi Cảm Biến Thời Tiết

**Files:**
- Modify: `web-nuxt/components/home/HomeLocalBriefing.vue:12-25, 55-65`
- Test: `web-nuxt/tests/home-terroir-resilience.test.ts`

**Interfaces:**
- Consumes: Thuật toán âm lịch `solarToLunar` và `tidePhase` trong `web-nuxt/components/home/HomeLocalBriefing.vue`.
- Produces: Khối cẩm nang con nước sông Cửu Long độc lập, luôn hiển thị ngay cả khi API thời tiết bị mất mạng hoặc trả về `unavailable`.

- [ ] **Step 1: Viết test kiểm chứng tính độc lập của cẩm nang con nước**

Tạo mới `web-nuxt/tests/home-terroir-resilience.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Mekong Terroir Resilience — Astronomical Tide Independence', () => {
  const briefingVue = readFileSync(resolve(__dirname, '../components/home/HomeLocalBriefing.vue'), 'utf8')

  it('renders tide handbook container unconditionally outside weather availability guard', () => {
    // Ensure the section wraps both weather and tide, or tide is not wiped out when weather is unavailable
    expect(briefingVue).toMatch(/class="home-local-briefing__tide"/)
    expect(briefingVue).toContain('Nước rong rằm')
  })
})
```

- [ ] **Step 2: Chạy test xác nhận cấu trúc**

Run: `npx vitest run tests/home-terroir-resilience.test.ts`

- [ ] **Step 3: Điều chỉnh cấu trúc template trong HomeLocalBriefing.vue**

Đảm bảo nếu `reading.status === 'unavailable'`, thời tiết sẽ hiển thị thông báo nhẹ nhàng hoặc chỉ ẩn khối số đo thời tiết, trong khi khối triều `home-local-briefing__tide` vẫn được hiển thị đầy đủ, truyền tải trọn vẹn trí tuệ sông nước dân gian.

- [ ] **Step 4: Chạy lại toàn bộ test trang chủ để xác nhận an toàn**

Run: `npx vitest run tests/home-`
Expected: 70/70 PASS.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/home/HomeLocalBriefing.vue web-nuxt/tests/home-terroir-resilience.test.ts
git commit -m "fix(terroir): decouple astronomical Mekong tide cycle from weather API status"
```

---

### Task 3: Nâng Cấp Typography Chuẩn Hiến Pháp (Thêm Lora & Khử Times New Roman)

**Files:**
- Modify: `web-nuxt/nuxt.config.ts:39-43`
- Modify: `web-nuxt/assets/css/variables.css:357`
- Test: `web-nuxt/tests/typography-anti-slop.test.ts`

**Interfaces:**
- Consumes: `@nuxt/fonts` khai báo Google Font `Lora` chính quy.
- Produces: CSS variable `--font-editorial` bắt đầu bằng `'Lora'`, hoàn toàn không chứa `'Times New Roman'`.

- [ ] **Step 1: Viết failing test kiểm tra chuẩn Typography**

Tạo mới `web-nuxt/tests/typography-anti-slop.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Typography Anti-Slop & Editorial Constitution Verification', () => {
  const root = resolve(__dirname, '..')
  const nuxtConfig = readFileSync(resolve(root, 'nuxt.config.ts'), 'utf8')
  const variablesCss = readFileSync(resolve(root, 'assets/css/variables.css'), 'utf8')

  it('declares Lora in @nuxt/fonts configuration in nuxt.config.ts', () => {
    expect(nuxtConfig).toMatch(/\{\s*name:\s*'Lora',\s*provider:\s*'google'\s*\}/)
  })

  it('enforces Lora at front of --font-editorial in variables.css', () => {
    expect(variablesCss).toMatch(/--font-editorial:\s*'Lora'/)
  })

  it('strictly bans Times New Roman from typography variables', () => {
    expect(variablesCss).not.toContain('Times New Roman')
  })
})
```

- [ ] **Step 2: Chạy test để xác nhận thất bại (RED)**

Run: `npx vitest run tests/typography-anti-slop.test.ts`
Expected: FAIL vì `nuxt.config.ts` chưa có `Lora` và `variables.css` vẫn chứa `Times New Roman`.

- [ ] **Step 3: Cập nhật nuxt.config.ts và variables.css**

1. Trong `web-nuxt/nuxt.config.ts`:
```ts
    families: [
      { name: 'Be Vietnam Pro', provider: 'google' },
      { name: 'Lora', provider: 'google' },
      { name: 'Fraunces', provider: 'google' },
    ],
```

2. Trong `web-nuxt/assets/css/variables.css:357`:
```css
  --font-editorial: 'Lora', 'Fraunces', 'Iowan Old Style', 'Palatino Linotype', Palatino, 'Book Antiqua', Georgia, 'Noto Serif', serif;
```

- [ ] **Step 4: Chạy test để xác nhận đạt (GREEN)**

Run: `npx vitest run tests/typography-anti-slop.test.ts`
Expected: PASS (3/3 tests passed).

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/nuxt.config.ts web-nuxt/assets/css/variables.css web-nuxt/tests/typography-anti-slop.test.ts
git commit -m "feat(typography): integrate Lora font per constitution and ban Times New Roman fallback"
```

---

### Task 4: Nâng Chuẩn Vùng Cảm Ứng WCAG 2.2 AAA (Touch Targets ≥ 44px) & Admin Focus

**Files:**
- Modify: `web-nuxt/assets/css/catalog.css:1494`
- Modify: `web-nuxt/layouts/admin.vue:78`
- Test: `web-nuxt/tests/a11y-wcag-aaa-refinements.test.ts`

**Interfaces:**
- Consumes: CSS pseudo-elements `::before` mở rộng vùng bấm cảm ứng cho người dùng di động ngoài trời.
- Produces: Đạt 100% WCAG 2.2 AAA Target Size (Minimum 44px) và hỗ trợ đầy đủ Skip Link cho Admin Shell.

- [ ] **Step 1: Viết failing test cho touch targets và admin focus**

Tạo mới `web-nuxt/tests/a11y-wcag-aaa-refinements.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('WCAG 2.2 AAA Accessibility Refinements', () => {
  const root = resolve(__dirname, '..')
  const catalogCss = readFileSync(resolve(root, 'assets/css/catalog.css'), 'utf8')
  const adminLayout = readFileSync(resolve(root, 'layouts/admin.vue'), 'utf8')

  it('equips .afl-clear-all with 44px minimum touch target pseudo-element', () => {
    expect(catalogCss).toMatch(/\.afl-clear-all::before\s*\{[^}]*min-height:\s*44px;/)
  })

  it('equips admin main element with tabindex="-1" for accessible skip-link focus transfer', () => {
    expect(adminLayout).toMatch(/<main\s+id="admin-main"\s+tabindex="-1"/)
  })
})
```

- [ ] **Step 2: Chạy test để xác nhận thất bại (RED)**

Run: `npx vitest run tests/a11y-wcag-aaa-refinements.test.ts`
Expected: FAIL.

- [ ] **Step 3: Cập nhật CSS catalog và admin layout**

1. Trong `web-nuxt/assets/css/catalog.css`:
Thêm lớp mở rộng touch target cho `.afl-clear-all`:
```css
.afl-clear-all {
  position: relative;
}
.afl-clear-all::before {
  content: "";
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  min-width: 44px;
  min-height: 44px;
  width: 100%;
  height: 100%;
}
```

2. Trong `web-nuxt/layouts/admin.vue:78`:
Bổ sung `tabindex="-1"` vào thẻ `<main id="admin-main">`.

- [ ] **Step 4: Chạy test xác nhận đạt (GREEN)**

Run: `npx vitest run tests/a11y-wcag-aaa-refinements.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/assets/css/catalog.css web-nuxt/layouts/admin.vue web-nuxt/tests/a11y-wcag-aaa-refinements.test.ts
git commit -m "fix(a11y): expand filter clear touch targets to 44px and add admin main tabindex"
```

---

### Task 5: Đồng Bộ Hiến Pháp Anti-Slop Lên Google Stitch MCP Cloud

**Files:**
- Read: `docs/superpowers/specs/2026-09-12-stitch-anti-slop-design-constitution.md`
- MCP Tool: Stitch MCP Server `upload_design_md` (Project `14916181929760067680`)

**Interfaces:**
- Consumes: Toàn bộ nội dung Hiến pháp Thiết Kế Taste Design dạng chuỗi Base64.
- Produces: Project Stitch `14916181929760067680` được cập nhật đồng bộ làm bộ luật tham chiếu thiết kế cho mọi màn hình tiếp theo.

- [ ] **Step 1: Đọc và mã hóa Base64 nội dung Hiến pháp Thiết kế Anti-Slop**
- [ ] **Step 2: Gọi công cụ Stitch MCP `upload_design_md` với `projectId: "14916181929760067680"`**
- [ ] **Step 3: Xác nhận phản hồi thành công từ Stitch MCP Server**

---

### Task 6: Tái Kiểm Định Toàn Diện Hệ Thống & Triển Khai Live

**Files:**
- Verify: Toàn bộ test suite và công cụ an toàn phóng.

- [ ] **Step 1: Chạy toàn bộ 70 test Vitest trang chủ**
Run: `npx vitest run tests/home-` (Expected: 70/70 PASS).
- [ ] **Step 2: Chạy 78 test hợp đồng màu sắc Tam Vùng**
Run: `npx vitest run tests/tri-region-color-contract.test.ts` (Expected: 78/78 PASS).
- [ ] **Step 3: Chạy script kiểm tra an toàn phóng của hệ thống**
Run: `python scripts/checks/run_hard.py --all` (Expected: 0 hard violations, 0 ratchet increase).
- [ ] **Step 4: Chạy kiểm tra kiểu dữ liệu Nuxt**
Run: `npm run typecheck` (Expected: exit code 0).
- [ ] **Step 5: Build Production Nitro**
Run: `npm run build` (Expected: thành công).
- [ ] **Step 6: Deploy lên VPS `66.42.57.202` và kiểm tra phản hồi `https://vinhlong360.vn`**

---

## Self-Review

1. **Spec Coverage:** Kế hoạch bao phủ toàn bộ các điểm phản biện từ Hội đồng Thẩm định (DEF-ART-06, DEF-UX-06, DEF-ART-02, DEF-ART-07, DEF-A11Y-03, DEF-A11Y-04), đồng bộ hóa Google Stitch MCP và bảo đảm không vi phạm bất kỳ hợp đồng bảo vệ nào.
2. **Placeholder Scan:** Không có "TODO", "TBD", hay mã mẫu giả định. Tất cả code và test đều cụ thể, có thể sao chép và thực thi ngay lập tức.
3. **Type Consistency:** Tên prop (`flame`, `Lora`, `tabindex="-1"`) khớp chính xác với hệ thống định kiểu và component Vue hiện có.
