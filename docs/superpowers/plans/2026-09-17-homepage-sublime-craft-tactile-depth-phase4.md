> STATUS: active (2026-09-17)

# Homepage Sublime Craft & Tactile Depth (Phase 4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện sâu sắc và tinh tế hơn nữa công thái học xúc giác tự nhiên (`:active scale`, hover lift micro-motion) và chuẩn mực tiếp cận WCAG 2.2 AAA kép (double-ring `:focus-visible`) cho các phân hệ Trang Chủ còn lại của Vĩnh Long 360 (`HomeCuratedShowcase.vue`, `HomeProductLead.vue`, `HomeLocalBriefing.vue`, `JourneyActionRail.vue`, `pages/index.vue` event-mini và `home-nocturne.css`).

**Architecture:** Áp dụng triết lý biên tập di sản Cửu Long độc bản kết hợp bộ kỹ năng UI cao cấp (`frontend-design`, `ui-ux-pro-max`, `impeccable`), trang bị phản hồi xúc giác lò xo vật lý nhún đàn hồi `cubic-bezier(0.16, 1, 0.3, 1)`, bảo đảm 100% không layout shifts, không nợ token màu sắc Tam Vùng, tuân thủ nghiêm ngặt quy tắc AST contrast và bảo toàn bit-for-bit cơ sở dữ liệu.

**Tech Stack:** Nuxt 4 (SSR/Nitro), Vue 3 Composition API, Vanilla Modern CSS với CSS Custom Properties (Tri-Region Tokens), Vitest, PostCSS AST Validator.

**Spec:** `web-nuxt/DESIGN.md`, `CLAUDE.md §1.7`, `docs/superpowers/plans/2026-09-17-homepage-sublime-craft-tactile-depth-phase4.md`.

## Global Constraints

- Không sử dụng audio, video hay autoplay.
- Tuyệt đối không thêm class thuộc `protectedConsumerClasses` (`hero-sub`, `hero-nearby`, `hero-search`, `hero-action--soft`, `home-feature-dossier__action`, `home-feature-dossier__action--secondary`, `ec-date`, `ec-countdown`, `ec-today`) vào selector mới.
- Bảo toàn 100% bit-for-bit SHA-256 cơ sở dữ liệu `agent/data/vinhlong360.db` và `web/data.json`.
- Mọi thành phần tương tác phải đạt touch target tối thiểu 44x44px.
- Mọi file markdown trong `docs/` bắt buộc có dòng đầu `> STATUS: active (YYYY-MM-DD)`.

---

### Task 1: Nâng tầm mỹ thuật & công thái học Toàn diện cho Top Điểm Đến Phải Đến (`HomeCuratedShowcase.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeCuratedShowcase.vue`
- Test: `web-nuxt/tests/challenger-m3-empirical-stress.test.ts`

**Interfaces:**
- Consumes: Design tokens `--color-focus`, `--radius-surface`, `--shadow-card-ambient` từ `variables.css`.
- Produces: CSS selectors `.home-curated-lead:focus-visible`, `.home-curated-lead:active`, `.home-curated-satellite:focus-visible`, `.home-curated-satellite__link:active`, `.home-curated-satellite__terroir-badge` hover transition.

- [ ] **Step 1: Write the failing test**
Thêm assertion trong `web-nuxt/tests/challenger-m3-empirical-stress.test.ts`:
```ts
    it('verifies HomeCuratedShowcase lead and satellite cards have focus-visible rings and active tactile feedback', () => {
      expect(showcaseContent).toMatch(/\.home-curated-lead:focus-visible/)
      expect(showcaseContent).toMatch(/\.home-curated-lead:active/)
      expect(showcaseContent).toMatch(/\.home-curated-satellite:focus-visible/)
      expect(showcaseContent).toMatch(/\.home-curated-satellite__link:active/)
    })
```

- [ ] **Step 2: Run test to verify it fails**
Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-m3-empirical-stress.test.ts`
Expected: FAIL with `AssertionError: expected showcaseContent to match /\.home-curated-lead:focus-visible/`.

- [ ] **Step 3: Write minimal implementation**
Trong `web-nuxt/components/home/HomeCuratedShowcase.vue`:
```css
.home-curated-lead:active {
  transform: scale(0.99);
}

.home-curated-lead:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
  border-radius: var(--radius-surface);
}

.home-curated-satellite:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
  border-radius: var(--radius-surface);
}

.home-curated-satellite__link:active {
  transform: scale(0.96);
}

.home-curated-satellite__terroir-badge {
  padding: 3px 8px;
  background: rgba(var(--black-rgb), 0.78);
  color: var(--alluvial-gold);
  border: 1px solid var(--border-liquid-glass);
  border-radius: var(--radius-pill, 9999px);
  font-size: 11px;
  font-weight: var(--weight-semibold);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  box-shadow: var(--shadow-card-ambient);
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), background-color 0.2s ease;
}

.home-curated-satellite:hover .home-curated-satellite__terroir-badge {
  transform: translateY(-1px);
}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-m3-empirical-stress.test.ts`
Expected: PASS (33/33 tests).

- [ ] **Step 5: Commit**
```bash
git add web-nuxt/components/home/HomeCuratedShowcase.vue web-nuxt/tests/challenger-m3-empirical-stress.test.ts
git commit -m "feat(home): add focus-visible rings and tactile active feedback to curated showcase cards and actions"
```

---

### Task 2: Hoàn thiện Đặc sản Vĩnh Long — Tin chính (`HomeProductLead.vue` & `home-nocturne.css`)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-layout-asymmetry.test.ts`

**Interfaces:**
- Consumes: `home-product-lead__media` và `home-product-lead__dept` từ `home-nocturne.css`.
- Produces: CSS selectors `[data-home-pilot="nocturne-b1"] .home-product-lead__media:active`.

- [ ] **Step 1: Write the failing test**
Thêm assertion trong `web-nuxt/tests/home-layout-asymmetry.test.ts`:
```ts
  it('enforces tactile active micro-interactions on product lead media plate', () => {
    expect(homeCss).toMatch(/\.home-product-lead__media:active\s*\{[\s\S]*?transform:\s*scale\(0\.99\)/)
  })
```

- [ ] **Step 2: Run test to verify it fails**
Run: `node ./node_modules/vitest/vitest.mjs run tests/home-layout-asymmetry.test.ts`
Expected: FAIL with `AssertionError: expected homeCss to match ...`.

- [ ] **Step 3: Write minimal implementation**
Trong `web-nuxt/assets/css/home-nocturne.css` quanh dòng 1518:
```css
[data-home-pilot="nocturne-b1"] .home-product-lead__media:active {
  transform: scale(0.99);
}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `node ./node_modules/vitest/vitest.mjs run tests/home-layout-asymmetry.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-layout-asymmetry.test.ts
git commit -m "feat(home): add active tactile scale to product lead media plate"
```

---

### Task 3: Nâng tầm Tín hiệu Địa phương & Nhịp Con Nước (`HomeLocalBriefing.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeLocalBriefing.vue`
- Test: `web-nuxt/tests/home-local-briefing.test.ts`

**Interfaces:**
- Consumes: `.home-local-briefing__tide-badge` trong `HomeLocalBriefing.vue`.
- Produces: CSS selectors `.home-local-briefing__tide-badge:hover`, `.home-local-briefing__tide-badge:active`.

- [ ] **Step 1: Write the failing test**
Thêm assertion trong `web-nuxt/tests/home-local-briefing.test.ts`:
```ts
  it('enforces tactile feedback and elevation on tide badge', () => {
    const briefingContent = readFileSync(resolve(__dirname, '../components/home/HomeLocalBriefing.vue'), 'utf8')
    expect(briefingContent).toMatch(/\.home-local-briefing__tide-badge:hover/)
    expect(briefingContent).toMatch(/\.home-local-briefing__tide-badge:active/)
  })
```

- [ ] **Step 2: Run test to verify it fails**
Run: `node ./node_modules/vitest/vitest.mjs run tests/home-local-briefing.test.ts`
Expected: FAIL with `AssertionError: expected briefingContent to match ...`.

- [ ] **Step 3: Write minimal implementation**
Trong `web-nuxt/components/home/HomeLocalBriefing.vue` quanh dòng 318:
```css
.home-local-briefing__tide-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px var(--space-2);
  border-radius: var(--radius-control);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  letter-spacing: .02em;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease, border-color 0.2s ease;
}

.home-local-briefing__tide-badge:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-xs);
}

.home-local-briefing__tide-badge:active {
  transform: scale(0.96);
}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `node ./node_modules/vitest/vitest.mjs run tests/home-local-briefing.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add web-nuxt/components/home/HomeLocalBriefing.vue web-nuxt/tests/home-local-briefing.test.ts
git commit -m "feat(home): add tactile active feedback and elevation to tide badge in local briefing"
```

---

### Task 4: Tinh tế hóa Ký sự Sự kiện & Mùa vụ Điền dã (`pages/index.vue` & `home-nocturne.css`)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/challenger-homepage-stress.test.ts`

**Interfaces:**
- Consumes: `.event-mini` trong `home-nocturne.css`.
- Produces: CSS selectors `.event-mini:active`, `.event-mini:focus-visible`.

- [ ] **Step 1: Write the failing test**
Thêm assertion trong `web-nuxt/tests/challenger-homepage-stress.test.ts`:
```ts
  describe('Adversarial Test 8: Event Mini Tactile Active & Focus Ring', () => {
    it('enforces active tactile scale and double-ring focus indicator on event mini cards', () => {
      expect(homeNocturneCss).toMatch(/\.event-mini:active\s*\{[\s\S]*?transform:\s*scale\(0\.98\)/)
      expect(homeNocturneCss).toMatch(/\.event-mini:focus-visible\s*\{[\s\S]*?outline:\s*2px\s+solid\s+var\(--color-focus\)/)
    })
  })
```

- [ ] **Step 2: Run test to verify it fails**
Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-homepage-stress.test.ts`
Expected: FAIL with `AssertionError: expected homeNocturneCss to match ...`.

- [ ] **Step 3: Write minimal implementation**
Trong `web-nuxt/assets/css/home-nocturne.css` quanh dòng 2135:
```css
.event-mini:active {
  transform: scale(0.98);
}

.event-mini:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-homepage-stress.test.ts`
Expected: PASS (28/28 tests).

- [ ] **Step 5: Commit**
```bash
git add web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/challenger-homepage-stress.test.ts
git commit -m "feat(home): add active tactile scale and focus-visible ring to mini event cards"
```

---

### Task 5: Nâng tầm Thanh Tiếp Nối Hành Trình & Bước Tiếp Theo (`JourneyActionRail.vue`)

**Files:**
- Modify: `web-nuxt/components/JourneyActionRail.vue`
- Test: `web-nuxt/tests/challenger-homepage-stress.test.ts`

**Interfaces:**
- Consumes: `.journey-action` trong `JourneyActionRail.vue`.
- Produces: CSS selector `.journey-action:active`.

- [ ] **Step 1: Write the failing test**
Thêm assertion trong `web-nuxt/tests/challenger-homepage-stress.test.ts`:
```ts
  describe('Adversarial Test 9: Journey Action Rail Active Tactile Response', () => {
    it('enforces active tactile scale on journey action buttons', () => {
      const railContent = readFileSync(resolve(webNuxt, 'components/JourneyActionRail.vue'), 'utf8')
      expect(railContent).toMatch(/\.journey-action:active\s*\{[\s\S]*?transform:\s*scale\(0\.98\)/)
    })
  })
```

- [ ] **Step 2: Run test to verify it fails**
Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-homepage-stress.test.ts`
Expected: FAIL with `AssertionError: expected railContent to match ...`.

- [ ] **Step 3: Write minimal implementation**
Trong `web-nuxt/components/JourneyActionRail.vue` quanh dòng 80:
```css
.journey-action:active {
  transform: scale(0.98);
}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-homepage-stress.test.ts`
Expected: PASS (29/29 tests).

- [ ] **Step 5: Commit**
```bash
git add web-nuxt/components/JourneyActionRail.vue web-nuxt/tests/challenger-homepage-stress.test.ts
git commit -m "feat(home): add active tactile scale to journey action rail buttons"
```

---

### Task 6: Kiểm thử toàn diện, biên dịch Nitro & Triển khai VPS `66.42.57.202` (Production Live)

**Files:**
- Toàn bộ codebase sản xuất

- [ ] **Step 1: Kiểm toán nợ màu sắc Tam Vùng**
Run: `node scripts/check-tri-region-color-debt.mjs`
Expected: PASS với `semantic: 0, z-index: 0`.

- [ ] **Step 2: Kiểm toán quy chuẩn tương phản WCAG 2.2 AAA**
Run: `node scripts/check-tri-region-contrast.mjs`
Expected: PASS (100% compliant, không vi phạm protectedConsumerClasses).

- [ ] **Step 3: Chạy toàn bộ các bộ kiểm thử Vitest Trang Chủ**
Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-*.test.ts tests/home-*.test.ts tests/tri-region-color-contract.test.ts`
Expected: PASS 100% tất cả các bài tests.

- [ ] **Step 4: Kiểm tra kiểu dữ liệu TypeScript**
Run: `npm run typecheck`
Expected: Exit code 0 (0 errors).

- [ ] **Step 5: Chạy bộ kiểm tra cổng an toàn cứng**
Run: `python ../scripts/checks/run_hard.py --all`
Expected: `hard=0, ratchet không tăng`.

- [ ] **Step 6: Xác nhận bất biến bit-for-bit SHA-256**
Run: `Get-FileHash -Algorithm SHA256 agent\data\vinhlong360.db, web\data.json | Format-List`
Expected:
- `vinhlong360.db`: `A777D4F6D83558925935EFA411B2BBCB64896ED6C0AF603BD41F2910209DFDC6`
- `web/data.json`: `598FC674FCA491CF8BEA32BBFD072050E2ED1F370C01ED64D17C9EC27E920CAE`

- [ ] **Step 7: Biên dịch sản xuất Nitro**
Run: `npm run build`
Expected: Build complete không lỗi, thư mục `.output` sẵn sàng.

- [ ] **Step 8: Đóng gói và triển khai VPS**
Run:
```powershell
tar.exe -czf dist_output.tar.gz -C web-nuxt .output
scp.exe dist_output.tar.gz root@66.42.57.202:/tmp/dist_output.tar.gz
ssh.exe root@66.42.57.202 "tar -xzf /tmp/dist_output.tar.gz -C /opt/vinhlong360/web-nuxt && rm /tmp/dist_output.tar.gz && systemctl restart vl-nuxt.service && systemctl status vl-nuxt.service --no-pager"
```
Expected: `vl-nuxt.service` active running.

- [ ] **Step 9: Kiểm tra HTTP trực tuyến và dọn dẹp**
Run:
```powershell
curl.exe -Is https://vinhlong360.vn
Remove-Item -Force dist_output.tar.gz
git push origin codex/correction-case-pilot
```
Expected: HTTP/1.1 200 OK.
