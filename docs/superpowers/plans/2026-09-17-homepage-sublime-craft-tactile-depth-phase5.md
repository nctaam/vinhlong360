> STATUS: active (2026-09-17)

# Homepage Sublime Craft & Tactile Depth (Phase 5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện toàn diện mỹ thuật biên tập di sản Cửu Long độc bản sâu hơn, tinh tế hơn cho toàn bộ các phân hệ Trang Chủ Vĩnh Long 360 (`HomeLocalBriefing.vue`, `pages/index.vue`, `home-nocturne.css`, `JourneyActionRail.vue`, `HomeCommunityFeed.vue`, `.fy-chip` và `.hero-cognitive-chip`), bảo đảm 100% công thái học xúc giác tự nhiên (`:active scale`, hover elevation), vòng nét đôi kép WCAG 2.2 AAA (`:focus-visible`), 0 nợ token màu sắc và bảo toàn bit-for-bit dữ liệu.

**Architecture:** Kết hợp sức mạnh của các kỹ năng UI chuyên sâu (`frontend-design`, `ui-ux-pro-max`, `impeccable`, `taste-design`, `checklist-design`), áp dụng nhịp đàn hồi lò xo vật lý `cubic-bezier(0.16, 1, 0.3, 1)`, bề mặt bắt sáng Liquid Glass `oklch(100% 0 0 / 0.12)`, chiều sâu thị giác phân tầng tự nhiên không layout shift và tuân thủ tuyệt đối AST contrast validator.

**Tech Stack:** Nuxt 4 (SSR / Nitro), Vue 3 Composition API, Modern CSS với Tri-Region Design Tokens (`variables.css`), Vitest (TDD Harness), PostCSS AST Validator.

**Spec:** `web-nuxt/DESIGN.md`, `CLAUDE.md §1.7`, `docs/superpowers/plans/2026-09-17-homepage-sublime-craft-tactile-depth-phase4.md`.

## Global Constraints

- Tuyệt đối không sử dụng âm thanh (audio), video hay autoplay.
- Tuyệt đối không thêm class thuộc `protectedConsumerClasses` (`hero-sub`, `hero-nearby`, `hero-search`, `hero-action--soft`, `home-feature-dossier__action`, `home-feature-dossier__action--secondary`, `ec-date`, `ec-countdown`, `ec-today`) vào selector CSS mới để tránh vi phạm AST contrast validator.
- Bảo toàn 100% bit-for-bit SHA-256 hai tệp dữ liệu gốc:
  - `agent/data/vinhlong360.db`: `A777D4F6D83558925935EFA411B2BBCB64896ED6C0AF603BD41F2910209DFDC6`
  - `web/data.json`: `598FC674FCA491CF8BEA32BBFD072050E2ED1F370C01ED64D17C9EC27E920CAE`
- Mọi thành phần tương tác phải đạt kích thước vùng chạm cảm ứng tối thiểu $44\times 44\text{px}$.
- Dòng đầu tiên của tệp kế hoạch trong `docs/` bắt buộc phải là `> STATUS: active (YYYY-MM-DD)`.

---

### Task 1: Nâng tầm Tín hiệu Địa phương & Nhịp Con Nước (`HomeLocalBriefing.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeLocalBriefing.vue`
- Test: `web-nuxt/tests/home-local-briefing.test.ts`

**Interfaces:**
- Consumes: `.home-local-briefing__tide-badge` trong `HomeLocalBriefing.vue`.
- Produces: CSS selectors `.home-local-briefing__tide-badge:hover`, `.home-local-briefing__tide-badge:active`.

- [ ] **Step 1: Write the failing test**
Đã bổ sung trong `web-nuxt/tests/home-local-briefing.test.ts`:
```ts
  describe('Adverse Scenario 5: Tactile ergonomics on tide badge', () => {
    it('enforces tactile feedback and elevation on tide badge', () => {
      const briefingContent = readFileSync(resolve(__dirname, '../components/home/HomeLocalBriefing.vue'), 'utf8')
      expect(briefingContent).toMatch(/\.home-local-briefing__tide-badge:hover/)
      expect(briefingContent).toMatch(/\.home-local-briefing__tide-badge:active/)
    })
  })
```

- [ ] **Step 2: Run test to verify it fails**
Run: `node ./node_modules/vitest/vitest.mjs run tests/home-local-briefing.test.ts`
Expected: FAIL with `AssertionError: expected briefingContent to match /\.home-local-briefing__tide-badge:hover/`.

- [ ] **Step 3: Write minimal implementation**
Cập nhật trong `web-nuxt/components/home/HomeLocalBriefing.vue` quanh dòng 318:
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
Expected: PASS (8/8 tests).

- [ ] **Step 5: Commit**
```bash
git add web-nuxt/components/home/HomeLocalBriefing.vue web-nuxt/tests/home-local-briefing.test.ts
git commit -m "feat(home): add tactile active feedback and elevation to tide badge in local briefing"
```

---

### Task 2: Tinh tế hóa Ký sự Sự kiện & Mùa vụ Điền dã (`pages/index.vue` & `home-nocturne.css`)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/challenger-homepage-stress.test.ts`

**Interfaces:**
- Consumes: `.event-mini` và `.home-season-row` trong `pages/index.vue` và `home-nocturne.css`.
- Produces: CSS selectors `.event-mini:active`, `.event-mini:focus-visible`, `.home-season-row:active`, `.home-season-row:focus-visible`.

- [ ] **Step 1: Write the failing test**
Thêm assertion trong `web-nuxt/tests/challenger-homepage-stress.test.ts`:
```ts
  describe('Adversarial Test 8: Event Mini & Seasonal Signal Tactile Ergonomics', () => {
    it('enforces active tactile scale and double-ring focus indicator on event mini cards', () => {
      expect(homeNocturneCss).toMatch(/\.event-mini:active\s*\{[\s\S]*?transform:\s*scale\(0\.98\)/)
      expect(homeNocturneCss).toMatch(/\.event-mini:focus-visible\s*\{[\s\S]*?outline:\s*2px\s+solid\s+var\(--color-focus\)/)
    })

    it('enforces active tactile scale and double-ring focus indicator on seasonal signal rows', () => {
      expect(homeNocturneCss).toMatch(/\.home-season-row:active\s*\{[\s\S]*?transform:\s*scale\(0\.98\)/)
      expect(homeNocturneCss).toMatch(/\.home-season-row:focus-visible\s*\{[\s\S]*?outline:\s*2px\s+solid\s+var\(--color-focus\)/)
    })
  })
```

- [ ] **Step 2: Run test to verify it fails**
Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-homepage-stress.test.ts`
Expected: FAIL with `AssertionError: expected homeNocturneCss to match /\.event-mini:active/`.

- [ ] **Step 3: Write minimal implementation**
Cập nhật trong `web-nuxt/assets/css/home-nocturne.css` quanh dòng 2135 và dòng 820:
```css
.event-mini:active {
  transform: scale(0.98);
}

.event-mini:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}

.home-season-row:active {
  transform: scale(0.98);
}

.home-season-row:focus-visible {
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
git commit -m "feat(home): add active tactile scale and focus-visible ring to mini events and seasonal signals"
```

---

### Task 3: Nâng tầm Thanh Tiếp Nối Hành Trình & Bước Tiếp Theo (`JourneyActionRail.vue`)

**Files:**
- Modify: `web-nuxt/components/JourneyActionRail.vue`
- Test: `web-nuxt/tests/challenger-homepage-stress.test.ts`

**Interfaces:**
- Consumes: `.journey-action` trong `JourneyActionRail.vue`.
- Produces: CSS selectors `.journey-action:active`, `.journey-action:focus-visible`.

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
Expected: FAIL with `AssertionError: expected railContent to match /\.journey-action:active/`.

- [ ] **Step 3: Write minimal implementation**
Cập nhật trong `web-nuxt/components/JourneyActionRail.vue` quanh dòng 80:
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

### Task 4: Nâng tầm Vi Tương Tác & Thẻ Cộng Đồng (`HomeCommunityFeed.vue` & `home-nocturne.css`)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-community-editorial.test.ts`

**Interfaces:**
- Consumes: `.tt-chip`, `.community-seed-card`, `.cm-content-link` trong `home-nocturne.css`.
- Produces: CSS selectors `.tt-chip:active`, `.tt-chip:focus-visible`, `.community-seed-card:active`, `.community-seed-card:focus-visible`.

- [ ] **Step 1: Write the failing test**
Thêm assertion trong `web-nuxt/tests/home-community-editorial.test.ts`:
```ts
  it('enforces tactile active scale and focus visible on community trending tags and seed cards', () => {
    expect(homeCss).toMatch(/\.tt-chip:active\s*\{[\s\S]*?transform:\s*scale\(0\.96\)/)
    expect(homeCss).toMatch(/\.tt-chip:focus-visible\s*\{[\s\S]*?outline:\s*2px\s+solid\s+var\(--color-focus\)/)
    expect(homeCss).toMatch(/\.community-seed-card:active\s*\{[\s\S]*?transform:\s*scale\(0\.98\)/)
    expect(homeCss).toMatch(/\.community-seed-card:focus-visible\s*\{[\s\S]*?outline:\s*2px\s+solid\s+var\(--color-focus\)/)
  })
```

- [ ] **Step 2: Run test to verify it fails**
Run: `node ./node_modules/vitest/vitest.mjs run tests/home-community-editorial.test.ts`
Expected: FAIL with `AssertionError: expected homeCss to match /\.tt-chip:active/`.

- [ ] **Step 3: Write minimal implementation**
Cập nhật trong `web-nuxt/assets/css/home-nocturne.css`:
```css
.tt-chip:active {
  transform: scale(0.96);
}

.tt-chip:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-pill, 9999px);
}

.community-seed-card:active {
  transform: scale(0.98);
}

.community-seed-card:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-surface);
}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `node ./node_modules/vitest/vitest.mjs run tests/home-community-editorial.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-community-editorial.test.ts
git commit -m "feat(home): add active tactile scale and focus-visible rings to community chips and seed cards"
```

---

### Task 5: Hoàn thiện Dải Cá Nhân Hóa "Dành Cho Bạn" (`pages/index.vue` & `home-nocturne.css`)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/challenger-homepage-stress.test.ts`

**Interfaces:**
- Consumes: `.fy-chip` và `.fy-thumb` trong `home-nocturne.css`.
- Produces: CSS selectors `.fy-chip:active`, `.fy-chip:focus-visible`, `.fy-chip:hover .fy-thumb img`.

- [ ] **Step 1: Write the failing test**
Thêm assertion trong `web-nuxt/tests/challenger-homepage-stress.test.ts`:
```ts
  describe('Adversarial Test 10: For-You Personalized Strip Ergonomics', () => {
    it('enforces active tactile scale and double-ring focus indicator on for-you chips', () => {
      expect(homeNocturneCss).toMatch(/\.fy-chip:active\s*\{[\s\S]*?transform:\s*scale\(0\.98\)/)
      expect(homeNocturneCss).toMatch(/\.fy-chip:focus-visible\s*\{[\s\S]*?outline:\s*2px\s+solid\s+var\(--color-focus\)/)
    })
  })
```

- [ ] **Step 2: Run test to verify it fails**
Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-homepage-stress.test.ts`
Expected: FAIL with `AssertionError: expected homeNocturneCss to match /\.fy-chip:active/`.

- [ ] **Step 3: Write minimal implementation**
Cập nhật trong `web-nuxt/assets/css/home-nocturne.css`:
```css
.fy-chip:active {
  transform: scale(0.98);
}

.fy-chip:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-surface);
}

.fy-chip:hover .fy-thumb img {
  transform: scale(1.06);
}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-homepage-stress.test.ts`
Expected: PASS (30/30 tests).

- [ ] **Step 5: Commit**
```bash
git add web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/challenger-homepage-stress.test.ts
git commit -m "feat(home): add active tactile scale and focus-visible ring to personalized for-you chips"
```

---

### Task 6: Tinh Tế Hóa Hero Cognitive Chip & Category Index Focus Offset (`home-nocturne.css`)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-smart-terroir.test.ts`

**Interfaces:**
- Consumes: `.hero-cognitive-chip` và `.home-category-index__primary-link:focus-visible`.
- Produces: CSS selector `.hero-cognitive-chip:active`, `.home-category-index__primary-link:focus-visible` offset chuẩn hóa.

- [ ] **Step 1: Write the failing test**
Thêm assertion trong `web-nuxt/tests/home-smart-terroir.test.ts`:
```ts
  it('enforces tactile active scale on hero cognitive chips', () => {
    expect(homeCss).toMatch(/\[data-home-pilot="nocturne-b1"\]\s+\.hero-cognitive-chip:active\s*\{[\s\S]*?transform:\s*scale\(0\.97\)/)
  })
```

- [ ] **Step 2: Run test to verify it fails**
Run: `node ./node_modules/vitest/vitest.mjs run tests/home-smart-terroir.test.ts`
Expected: FAIL with `AssertionError: expected homeCss to match /\.hero-cognitive-chip:active/`.

- [ ] **Step 3: Write minimal implementation**
Trong `web-nuxt/assets/css/home-nocturne.css`:
```css
[data-home-pilot="nocturne-b1"] .hero-cognitive-chip:active {
  transform: scale(0.97);
}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `node ./node_modules/vitest/vitest.mjs run tests/home-smart-terroir.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-smart-terroir.test.ts
git commit -m "feat(home): add active tactile scale to hero cognitive chips"
```

---

### Task 7: Kiểm Thử Toàn Diện, Biên Dịch Nitro & Triển Khai Production Live VPS `66.42.57.202`

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
Expected: PASS 100% tất cả các bài tests (hơn 180+ tests trang chủ).

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
