> STATUS: active (2026-09-17)

# Homepage Exquisite Editorial Depth & Tactile Polish (Phase 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng tầm và hoàn thiện toàn bộ các phân hệ còn lại của Trang Chủ Vĩnh Long 360 (`HomeCulinaryTrail.vue`, `HomeRiversideStays.vue`, `HomeTravelPlanner.vue`, `HomeCommunityFeed.vue`, `HomeFeatureDossier.vue` và `assets/css/home-nocturne.css`) đạt đến sự đồng bộ tinh xảo tuyệt đối về xúc giác (tactile micro-interactions), phản hồi vật lý lò xo, và chuẩn tiếp cận WCAG 2.2 AAA kép.

**Architecture:** Mở rộng và chuẩn hóa hệ thống phản hồi xúc giác (`:active scale(0.98)` / `:active scale(0.96)`), double-ring focus indicators (`outline: 2px solid var(--color-focus); outline-offset: 2px/3px`), viền bắt sáng Liquid Glass (`var(--border-liquid-glass)`), và gia tốc chuyển động mượt mà `cubic-bezier(0.16, 1, 0.3, 1)` trên toàn bộ các thẻ ẩm thực, homestay, chặng lộ trình, bài viết cộng đồng và khối dẫn nhập thực địa.

**Tech Stack:** Nuxt 4 (SSR), Vue 3, PostCSS, Vitest 4, CSS Design Tokens (`variables.css`, `home-nocturne.css`), Python 3.12 (`run_hard.py`).

**Spec:** `docs/superpowers/plans/2026-09-17-homepage-exquisite-editorial-depth-phase3.md`

## Global Constraints

- **Bất biến B1, B6, B7 (CLAUDE.md):** `agent/data/vinhlong360.db` (SHA-256 `a777d4f6d83558925935efa411b2bbcb64896ed6c0af603bd41f2910209dfdc6`) và `web/data.json` (SHA-256 `598fc674fca491cf8bea32bbfd072050e2ed1f370c01ed64d17c9ec27e920cae`) bảo toàn nguyên vẹn 100% bit-for-bit.
- **Nợ Token Màu Sắc (check-tri-region-color-debt.mjs):** Giữ vững `semantic: 0, z-index: 0`. Tuyệt đối không dùng mã màu raw hex `#...` ngoài palette token.
- **Quy Chuẩn Tương Phản (check-tri-region-contrast.mjs):** 100% tuân thủ WCAG 2.2 AAA. Tuyệt đối KHÔNG sử dụng các class trong `protectedConsumerClasses` (`hero-sub`, `hero-nearby`, `hero-search`, `hero-action--soft`, `home-feature-dossier__action`, `home-feature-dossier__action--secondary`, `ec-date`, `ec-countdown`, `ec-today`) làm selector CSS độc lập mới.
- **Chuẩn Tiếp Cận WCAG 2.2 AAA:** Mọi phần tử tương tác (nút bấm, thẻ, liên kết, chặng dừng) phải có touch target $\ge 44\times 44\text{px}$ và double-ring `:focus-visible`.
- **An Toàn Phóng:** `python ../scripts/checks/run_hard.py --all` đạt `hard=0, ratchet không tăng`. `npm run typecheck` đạt 0 errors.

---

### Task 1: Nâng Tầm Mỹ Thuật & Công Thái Học Ký Sự Ẩm Thực Phù Sa (`HomeCulinaryTrail.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeCulinaryTrail.vue:220-464`
- Test: `web-nuxt/tests/challenger-m3-empirical-stress.test.ts`

**Interfaces:**
- Consumes: `.home-culinary-card`, `.home-culinary-card__btn`, `.home-culinary-card__venue-pill`.
- Produces: Double-ring `:focus-visible` trên thẻ món ăn, phản hồi nhún `:active scale(0.98)` trên nút xem chi tiết món, và vi tương tác hover trên huy hiệu điểm bán.

- [ ] **Step 1: Viết test failing cho focus-visible và active states của thẻ và nút ẩm thực**

Bổ sung assertions trong `web-nuxt/tests/challenger-m3-empirical-stress.test.ts`:
```typescript
it('verifies HomeCulinaryTrail cards and actions have focus-visible rings and active states', () => {
  expect(culinaryContent).toMatch(/\.home-culinary-card:focus-visible/)
  expect(culinaryContent).toMatch(/\.home-culinary-card__btn:active/)
  expect(culinaryContent).toMatch(/\.home-culinary-card__venue-pill[\s\S]*?transition/)
})
```

- [ ] **Step 2: Chạy test để xác nhận trạng thái RED**

Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-m3-empirical-stress.test.ts -t "HomeCulinaryTrail cards and actions"`
Expected: FAIL.

- [ ] **Step 3: Cập nhật CSS trong `web-nuxt/components/home/HomeCulinaryTrail.vue`**

Thêm các quy tắc CSS:
```css
.home-culinary-card:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
  border-radius: var(--radius-surface);
}

.home-culinary-card__btn:active {
  transform: scale(0.98);
}

.home-culinary-card__venue-pill {
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.home-culinary-card:hover .home-culinary-card__venue-pill {
  transform: translateY(-1px);
  border-color: var(--alluvial-gold);
}
```

- [ ] **Step 4: Chạy test để xác nhận trạng thái GREEN**

Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-m3-empirical-stress.test.ts`
Expected: PASS 100%.

- [ ] **Step 5: Kiểm tra nợ màu và tương phản**

Run: `node scripts/check-tri-region-color-debt.mjs && node scripts/check-tri-region-contrast.mjs`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web-nuxt/tests/challenger-m3-empirical-stress.test.ts web-nuxt/components/home/HomeCulinaryTrail.vue
git commit -m "feat(home): add focus-visible rings and tactile feedback to culinary trail cards and actions"
```

---

### Task 2: Nâng Tầm Công Thái Học Thẻ Nghỉ Dưỡng & Khám Phá Dân Gian (`HomeRiversideStays.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeRiversideStays.vue:265-635`
- Test: `web-nuxt/tests/challenger-m3-empirical-stress.test.ts`

**Interfaces:**
- Consumes: `.home-stay-card`, `.home-exp-card`.
- Produces: Double-ring `:focus-visible` trên thẻ homestay và phản hồi nhún xúc giác `:active scale(0.98)` trên thẻ trải nghiệm dân gian.

- [ ] **Step 1: Viết test failing cho focus-visible của homestay card và active state của folk experience card**

Bổ sung assertions trong `web-nuxt/tests/challenger-m3-empirical-stress.test.ts`:
```typescript
it('verifies HomeRiversideStays cards and folk experiences have focus-visible rings and active tactile feedback', () => {
  expect(staysContent).toMatch(/\.home-stay-card:focus-visible/)
  expect(staysContent).toMatch(/\.home-exp-card:active/)
})
```

- [ ] **Step 2: Chạy test để xác nhận trạng thái RED**

Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-m3-empirical-stress.test.ts -t "HomeRiversideStays cards and folk experiences"`
Expected: FAIL.

- [ ] **Step 3: Cập nhật CSS trong `web-nuxt/components/home/HomeRiversideStays.vue`**

Thêm các quy tắc CSS:
```css
.home-stay-card:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
  border-radius: var(--radius-surface);
}

.home-exp-card:active {
  transform: scale(0.98);
}
```

- [ ] **Step 4: Chạy test để xác nhận trạng thái GREEN**

Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-m3-empirical-stress.test.ts`
Expected: PASS 100%.

- [ ] **Step 5: Kiểm tra nợ màu và tương phản**

Run: `node scripts/check-tri-region-color-debt.mjs && node scripts/check-tri-region-contrast.mjs`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web-nuxt/tests/challenger-m3-empirical-stress.test.ts web-nuxt/components/home/HomeRiversideStays.vue
git commit -m "feat(home): add focus-visible rings and tactile active feedback to riverside stays and folk experiences"
```

---

### Task 3: Tinh Tế Hóa Sổ Tay Hành Trình Điền Dã (`HomeTravelPlanner.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeTravelPlanner.vue:425-485`
- Test: `web-nuxt/tests/challenger-homepage-stress.test.ts`

**Interfaces:**
- Consumes: `.home-planner-stop`, `.home-planner-stop__marker`.
- Produces: Phản hồi nhún `:active scale(0.98)` trên chặng dừng chân và micro-motion trên số thứ tự chặng khi hover.

- [ ] **Step 1: Viết test failing cho HomeTravelPlanner stop micro-motion và active states**

Bổ sung assertions trong `web-nuxt/tests/challenger-homepage-stress.test.ts`:
```typescript
it('verifies HomeTravelPlanner timeline stops have tactile active feedback and marker micro-motion', () => {
  const plannerContent = readFileSync(resolve(webNuxt, 'components/home/HomeTravelPlanner.vue'), 'utf8')
  expect(plannerContent).toMatch(/\.home-planner-stop:active/)
  expect(plannerContent).toMatch(/\.home-planner-stop:hover\s+\.home-planner-stop__marker/)
})
```

- [ ] **Step 2: Chạy test để xác nhận trạng thái RED**

Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-homepage-stress.test.ts -t "HomeTravelPlanner timeline stops"`
Expected: FAIL.

- [ ] **Step 3: Cập nhật CSS trong `web-nuxt/components/home/HomeTravelPlanner.vue`**

Thêm các quy tắc CSS:
```css
.home-planner-stop:active {
  transform: scale(0.98);
}

.home-planner-stop__marker {
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), background-color 0.2s ease;
}

.home-planner-stop:hover .home-planner-stop__marker {
  transform: scale(1.08);
}
```

- [ ] **Step 4: Chạy test để xác nhận trạng thái GREEN**

Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-homepage-stress.test.ts -t "HomeTravelPlanner timeline stops"`
Expected: PASS 100%.

- [ ] **Step 5: Kiểm tra nợ màu và tương phản**

Run: `node scripts/check-tri-region-color-debt.mjs && node scripts/check-tri-region-contrast.mjs`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web-nuxt/tests/challenger-homepage-stress.test.ts web-nuxt/components/home/HomeTravelPlanner.vue
git commit -m "feat(home): add tactile active feedback and marker micro-motion to travel planner timeline stops"
```

---

### Task 4: Nâng Tầm Ký Sự Điền Dã & Cộng Đồng Lữ Khách (`HomeCommunityFeed.vue`)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css:2900-2930`
- Test: `web-nuxt/tests/home-community-editorial.test.ts`

**Interfaces:**
- Consumes: `.home-community-dispatches .cm-card`.
- Produces: Double-ring `:focus-visible` bo góc `var(--radius-surface)` trên thẻ bài viết cộng đồng điền dã.

- [ ] **Step 1: Viết test failing cho focus-visible của cm-card trong home-nocturne.css**

Bổ sung assertions trong `web-nuxt/tests/home-community-editorial.test.ts`:
```typescript
it('enforces double-ring focus-visible indicator on community cards', () => {
  expect(homeCss).toMatch(/\.home-community-dispatches\s+\.cm-card:focus-visible\s*\{[\s\S]*?outline:\s*2px solid var\(--color-focus\)/)
})
```

- [ ] **Step 2: Chạy test để xác nhận trạng thái RED**

Run: `node ./node_modules/vitest/vitest.mjs run tests/home-community-editorial.test.ts`
Expected: FAIL.

- [ ] **Step 3: Cập nhật CSS trong `web-nuxt/assets/css/home-nocturne.css`**

Thêm quy tắc CSS trong khối `EDITORIAL TRAVELER FIELD NOTES & DISPATCHES`:
```css
.home-community-dispatches .cm-card:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
  border-radius: var(--radius-surface);
}
```

- [ ] **Step 4: Chạy test để xác nhận trạng thái GREEN**

Run: `node ./node_modules/vitest/vitest.mjs run tests/home-community-editorial.test.ts`
Expected: PASS 100%.

- [ ] **Step 5: Kiểm tra nợ màu và tương phản**

Run: `node scripts/check-tri-region-color-debt.mjs && node scripts/check-tri-region-contrast.mjs`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web-nuxt/tests/home-community-editorial.test.ts web-nuxt/assets/css/home-nocturne.css
git commit -m "feat(home): add double-ring focus-visible indicators to community dispatch cards"
```

---

### Task 5: Khối Dẫn Nhập Hero Dossier & Tọa Độ Thực Địa (`HomeFeatureDossier.vue` & `home-nocturne.css`)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css:380-450`
- Test: `web-nuxt/tests/home-hero-dossier-polish.test.ts`

**Interfaces:**
- Consumes: `.home-feature-dossier__media`, `.home-feature-dossier__coords--link`.
- Produces: Double-ring `:focus-visible` và `:active scale(0.99)` trên media plate, `:active scale(0.96)` trên nút tọa độ GPS thực địa.

- [ ] **Step 1: Viết test failing cho focus-visible của media plate và active state của coords link**

Bổ sung assertions trong `web-nuxt/tests/home-hero-dossier-polish.test.ts`:
```typescript
it('enforces focus-visible and active states on hero feature media plate and coords link', () => {
  expect(homeCss).toMatch(/\[data-home-pilot="nocturne-b1"\]\s+\.home-feature-dossier__media:focus-visible/)
  expect(homeCss).toMatch(/\[data-home-pilot="nocturne-b1"\]\s+\.home-feature-dossier__coords--link:active/)
})
```

- [ ] **Step 2: Chạy test để xác nhận trạng thái RED**

Run: `node ./node_modules/vitest/vitest.mjs run tests/home-hero-dossier-polish.test.ts`
Expected: FAIL.

- [ ] **Step 3: Cập nhật CSS trong `web-nuxt/assets/css/home-nocturne.css`**

Thêm các quy tắc CSS:
```css
[data-home-pilot="nocturne-b1"] .home-feature-dossier__media:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
  border-radius: var(--radius-surface);
}

[data-home-pilot="nocturne-b1"] .home-feature-dossier__media:active {
  transform: scale(0.99);
}

[data-home-pilot="nocturne-b1"] .home-feature-dossier__coords--link:active {
  transform: scale(0.96);
}
```

- [ ] **Step 4: Chạy test để xác nhận trạng thái GREEN**

Run: `node ./node_modules/vitest/vitest.mjs run tests/home-hero-dossier-polish.test.ts`
Expected: PASS 100%.

- [ ] **Step 5: Kiểm tra nợ màu và tương phản**

Run: `node scripts/check-tri-region-color-debt.mjs && node scripts/check-tri-region-contrast.mjs`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web-nuxt/tests/home-hero-dossier-polish.test.ts web-nuxt/assets/css/home-nocturne.css
git commit -m "feat(home): add focus-visible rings and active feedback to hero dossier media plate and coords link"
```

---

### Task 6: Toàn Diện Kiểm Thử, Build Nitro & Triển Khai VPS `66.42.57.202`

**Files:**
- Output: `.output`, `dist_output.tar.gz`
- Verification: toàn bộ test suite, typecheck, run_hard, curl live site

- [ ] **Step 1: Kiểm toán nợ token màu sắc**
  Run: `node scripts/check-tri-region-color-debt.mjs`
  Expected: `semantic 0, z-index 0` (PASS).

- [ ] **Step 2: Kiểm toán quy chuẩn tương phản**
  Run: `node scripts/check-tri-region-contrast.mjs`
  Expected: PASS 100%.

- [ ] **Step 3: Chạy toàn bộ 24 test suites Trang Chủ**
  Run: `node ./node_modules/vitest/vitest.mjs run tests/home- tests/challenger-m3-empirical-stress.test.ts tests/challenger-homepage-stress.test.ts`
  Expected: 24/24 files passed, 100% tests passed.

- [ ] **Step 4: Kiểm tra kiểu dữ liệu Nuxt/Vue**
  Run: `npm run typecheck`
  Expected: exit code 0 (0 errors).

- [ ] **Step 5: Kiểm tra cổng an toàn cứng**
  Run: `python ../scripts/checks/run_hard.py --all`
  Expected: `hard=0, ratchet không tăng`.

- [ ] **Step 6: Xác nhận bất biến mã băm SHA-256 cơ sở dữ liệu**
  Run: `python -c "import hashlib; print('db:', hashlib.sha256(open('../agent/data/vinhlong360.db','rb').read()).hexdigest()); print('data.json:', hashlib.sha256(open('../web/data.json','rb').read()).hexdigest())"`
  Expected:
  - `vinhlong360.db`: `a777d4f6d83558925935efa411b2bbcb64896ed6c0af603bd41f2910209dfdc6`
  - `web/data.json`: `598fc674fca491cf8bea32bbfd072050e2ed1f370c01ed64d17c9ec27e920cae`

- [ ] **Step 7: Biên dịch sản xuất Nitro**
  Run: `npm run build`
  Expected: Nitro build sạch sẽ không lỗi.

- [ ] **Step 8: Đóng gói và triển khai lên máy chủ VPS `66.42.57.202`**
  - Run: `tar.exe -czf dist_output.tar.gz -C web-nuxt .output`
  - Run: `scp.exe dist_output.tar.gz root@66.42.57.202:/tmp/dist_output.tar.gz`
  - Run: `ssh.exe root@66.42.57.202 "tar -xzf /tmp/dist_output.tar.gz -C /opt/vinhlong360/web-nuxt && rm /tmp/dist_output.tar.gz && systemctl restart vl-nuxt.service && systemctl status vl-nuxt.service --no-pager"`

- [ ] **Step 9: Xác nhận trực tuyến HTTP 200**
  Run: `curl.exe -Is https://vinhlong360.vn`
  Expected: `HTTP/1.1 200 OK`.

- [ ] **Step 10: Đồng bộ mã nguồn Git**
  Run: `git push origin codex/correction-case-pilot`
  Expected: Sync thành công.
