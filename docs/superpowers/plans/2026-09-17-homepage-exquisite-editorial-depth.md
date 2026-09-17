> STATUS: active (2026-09-17)

# Kế Hoạch Hiện Thực Hóa: Nâng Tầm Chiều Sâu Mỹ Thuật & Công Thái Học Trang Chủ (Homepage Exquisite Editorial Depth Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện giao diện Trang Chủ (`pages/index.vue`, `components/home/*`, `assets/css/home-nocturne.css`) sâu hơn và tinh tế hơn bằng việc áp dụng các kỹ năng chuyên sâu `impeccable`, `frontend-design`, `ui-ux-pro-max`, `checklist-design` và `writing-plans`: chuẩn hóa vi tương tác xúc giác và double-ring focus cho Lối rẽ quyết định & Danh mục khám phá, hoàn thiện cẩm nang du khách & đường dây nóng thực địa, nâng tầm ký sự điền dã Monocle, gia cố con dấu sáp 3D Sổ vàng OCOP, tối ưu công thái học phím tắt lữ hành, bảo đảm 100% WCAG 2.2 AAA kép và 0 nợ token.

**Architecture:** Kết hợp mỹ học ấn loát tạp chí biên tập di sản (*Monocle*, *Rijksmuseum*) với công thái học sông nước Cửu Long (*Visit Oslo*, *National Geographic*). Mọi chi tiết tương tác đều sở hữu gia tốc nhún lò xo vật lý (`cubic-bezier(0.16, 1, 0.3, 1)`), chiều sâu trường ảnh đa tầng qua viền bắt sáng *Liquid Glass* (`var(--border-liquid-glass)`), đổ bóng than củi hữu cơ (`var(--shadow-card-ambient)`), và chỉ báo tiếp cận bàn phím kép chuẩn mực (`var(--color-focus)`).

**Tech Stack:** Nuxt 4 (SSR), Vue 3 Composition API, PostCSS / Modern CSS (oklch, liquid glass, custom properties, container queries), Vitest, TypeScript.

**Spec:** `web-nuxt/DESIGN.md` (Hiến pháp Thiết kế Vĩnh Long 360) & `CLAUDE.md`.

---

## Global Constraints

1. **Hiến pháp Dữ liệu Trung thực (`CLAUDE.md §1.7`):** Tuyệt đối không sinh dữ liệu giả mạo, không skeleton khi API lỗi, tôn trọng điều kiện `reading.status !== 'unavailable'`.
2. **Quy chuẩn Token Bán kính (Ratchet R30.8):** Cấm triệt để scale cũ `--radius-xs/sm/md/lg/xl`. Bắt buộc dùng semantic radius tokens: `--radius-control` (8px), `--radius-surface` (12px), `--radius-sheet` (20px), `--radius-full` (9999px), `--radius-pill` (999px).
3. **Công thái học & Tiếp cận (WCAG 2.2 AAA):** 100% phần tử tương tác đạt diện tích chạm cảm ứng $\ge 44\times 44\text{px}$ (riêng hotline $\ge 48\times 48\text{px}$); độ tương phản $\ge 7:1$ tiêu đề và $\ge 4.5:1$ văn bản; double-ring `:focus-visible` với `outline: 2px solid var(--color-focus); outline-offset: 2px;`.
4. **Bảo toàn Bất biến Cơ sở dữ liệu (Invariants B1, B6, B7):** `agent/data/vinhlong360.db` và `web/data.json` là read-only, tuyệt đối 0 diff, giữ nguyên 100% mã băm SHA-256.
5. **Hợp đồng Màu sắc & Nợ Token:** `node scripts/check-tri-region-color-debt.mjs` phải đạt `semantic 0, z-index 0` (PASS); `node scripts/check-tri-region-contrast.mjs` đạt 100% PASS; tuyệt đối không khai báo selector chứa trực tiếp các lớp trong `protectedConsumerClasses` (`hero-sub`, `hero-nearby`, `hero-search`, `hero-action--soft`, `home-feature-dossier__action`, `home-feature-dossier__action--secondary`, `ec-date`, `ec-countdown`, `ec-today`).
6. **Bảo toàn 100% Kiểm thử:** Tất cả các test suites Vitest hiện có, `npm run typecheck` 0 lỗi, và `python ../scripts/checks/run_hard.py --all` 0 hard violations / 0 ratchet increase.

---

## Task Breakdown

### Task 1: Nâng Tầm Mỹ Thuật Lối Rẽ Quyết Định & Dải Tiện Ích Danh Mục (`HomeDecisionLedger.vue` & `HomeCategoryIndex.vue`)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css:560-580, 2830-2870`
- Test: `web-nuxt/tests/home-decision-category.test.ts`

**Interfaces:**
- Consumes: Bảng màu Tam Vùng (`--color-brand`, `--color-focus`, `--border-liquid-glass`, `--shadow-card-ambient`).
- Produces: Vi tương tác xúc giác và double-ring `:focus-visible` cho từng hàng quyết định `[data-home-decision-entry]`, các thẻ danh mục chính `.home-category-index__card` và dải liên kết tiện ích `.home-category-index__utility-link`.

- [ ] **Step 1: Viết test kiểm tra focus-visible và tactile feedback cho Decision Ledger & Category Index**
  Bổ sung assertions trong `web-nuxt/tests/home-decision-category.test.ts`:
  ```typescript
  it('enforces focus-visible ring and tactile ergonomics on category cards and utility links', () => {
    const css = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf-8')
    expect(css).toMatch(/\.home-category-index__primary-link:focus-visible/)
    expect(css).toMatch(/\.home-category-index__utility-link:focus-visible/)
    expect(css).toMatch(/\.home-decision-ledger__link:focus-visible/)
  })
  ```

- [ ] **Step 2: Chạy test để xác nhận fail**
  Run: `node ./node_modules/vitest/vitest.mjs run tests/home-decision-category.test.ts`
  Expected: FAIL (thiếu `.home-category-index__primary-link:focus-visible` hoặc `.home-category-index__utility-link:focus-visible`).

- [ ] **Step 3: Cập nhật CSS trong `web-nuxt/assets/css/home-nocturne.css`**
  Thêm quy tắc focus-visible và xúc giác nhún:
  ```css
  [data-home-pilot="nocturne-b1"] .home-category-index__primary-link:focus-visible {
    outline: 2px solid var(--color-focus);
    outline-offset: 2px;
    border-radius: var(--radius-surface);
  }

  [data-home-pilot="nocturne-b1"] .home-category-index__utility-link:focus-visible {
    outline: 2px solid var(--color-focus) !important;
    outline-offset: 2px !important;
    border-radius: var(--radius-control) !important;
  }
  ```

- [ ] **Step 4: Chạy test để xác nhận pass**
  Run: `node ./node_modules/vitest/vitest.mjs run tests/home-decision-category.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): add double-ring focus indicator and tactile ergonomics to decision ledger and category index"`

---

### Task 2: Tinh Tế Hóa Cẩm Nang Du Khách & Đường Dây Nóng Khẩn Cấp (`HomeTravelCompanion.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeTravelCompanion.vue:555-583`
- Test: `web-nuxt/tests/challenger-m3-empirical-stress.test.ts`

**Interfaces:**
- Consumes: Hotline buttons (`.home-hotline-btn--quick`, `.home-companion-quick-utility`).
- Produces: Nút hotline nổi có phản hồi nén xúc giác `:active scale(0.96)` và double-ring `:focus-visible` đạt chuẩn WCAG 2.2 AAA.

- [ ] **Step 1: Viết test kiểm tra focus và active states cho quick hotlines**
  Bổ sung assertions trong `web-nuxt/tests/challenger-m3-empirical-stress.test.ts`:
  ```typescript
  it('verifies HomeTravelCompanion quick hotline buttons have focus-visible and active states', () => {
    const companionContent = readFileSync(resolve(webNuxt, 'components/home/HomeTravelCompanion.vue'), 'utf8')
    expect(companionContent).toMatch(/\.home-hotline-btn--quick:active/)
    expect(companionContent).toMatch(/\.home-hotline-btn--quick:focus-visible/)
  })
  ```

- [ ] **Step 2: Chạy test để xác nhận fail**
  Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-m3-empirical-stress.test.ts`
  Expected: FAIL.

- [ ] **Step 3: Cập nhật CSS trong `web-nuxt/components/home/HomeTravelCompanion.vue`**
  Thêm vào style block:
  ```css
  .home-hotline-btn--quick:active {
    transform: scale(0.96);
  }

  .home-hotline-btn--quick:focus-visible {
    outline: 2px solid var(--color-focus);
    outline-offset: 2px;
  }
  ```

- [ ] **Step 4: Chạy test để xác nhận pass**
  Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-m3-empirical-stress.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): add tactile active feedback and focus-visible rings to quick companion hotlines"`

---

### Task 3: Nâng Cấp Ký Sự Thổ Nhưỡng & Khảo Cứu Điền Dã (`HomeNativeStories.vue`)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css:2495-2510, 2635-2650`
- Test: `web-nuxt/tests/home-native-stories.test.ts`

**Interfaces:**
- Consumes: Story cards (`.home-story-card`, `.home-story-callout`).
- Produces: Thẻ ký sự di sản với chỉ báo tiếp cận `:focus-visible` ring kép bo góc `--radius-surface` và nút hành động khảo cứu có phản hồi nhún vật lý.

- [ ] **Step 1: Viết test kiểm tra focus-visible và tactile states cho native stories**
  Bổ sung assertions trong `web-nuxt/tests/home-native-stories.test.ts`:
  ```typescript
  it('enforces focus-visible rings and tactile elevation on native story cards and callout action', () => {
    const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
    expect(homeCss).toMatch(/\.home-story-card:focus-visible/)
    expect(homeCss).toMatch(/\.home-story-callout__action:focus-visible/)
  })
  ```

- [ ] **Step 2: Chạy test để xác nhận fail**
  Run: `node ./node_modules/vitest/vitest.mjs run tests/home-native-stories.test.ts`
  Expected: FAIL.

- [ ] **Step 3: Cập nhật CSS trong `web-nuxt/assets/css/home-nocturne.css`**
  Thêm:
  ```css
  [data-home-pilot="nocturne-b1"] .home-story-card:focus-visible {
    outline: 2px solid var(--color-focus);
    outline-offset: 3px;
    border-radius: var(--radius-surface);
  }

  [data-home-pilot="nocturne-b1"] .home-story-callout__action:focus-visible {
    outline: 2px solid var(--color-focus);
    outline-offset: 2px;
    border-radius: var(--radius-control);
  }

  [data-home-pilot="nocturne-b1"] .home-story-callout__action:active {
    transform: scale(0.98);
  }
  ```

- [ ] **Step 4: Chạy test để xác nhận pass**
  Run: `node ./node_modules/vitest/vitest.mjs run tests/home-native-stories.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): harden focus-visible rings and tactile responses on native stories and field notes"`

---

### Task 4: Hoàn Thiện Sổ Vàng OCOP & Con Dấu Sáp Di Sản (`HomeOcopLedger.vue`)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css:1775-1800, 1860-1880`
- Test: `web-nuxt/tests/home-ocop-aeo-polish.test.ts`

**Interfaces:**
- Consumes: Sổ vàng OCOP quốc gia (`.home-ocop__frame`, `.wax-seal`, `.home-ocop__tier`).
- Produces: Con dấu sáp đỏ nung Mang Thít có chuyển động xoay nhẹ khi rê chuột (`rotate(-3deg) scale(1.05)`), dải sao OCOP có hiệu ứng nhấc thẻ mượt mà.

- [ ] **Step 1: Viết test kiểm tra vi tương tác con dấu sáp và các tier OCOP**
  Bổ sung assertions trong `web-nuxt/tests/home-ocop-aeo-polish.test.ts`:
  ```typescript
  it('enforces rotational micro-tilt on wax seal and refined tier elevation', () => {
    expect(homeCss).toMatch(/\.wax-seal[\s\S]*?transform/)
    expect(homeCss).toMatch(/\.home-ocop__tier:hover[\s\S]*?transform/)
  })
  ```

- [ ] **Step 2: Chạy test để xác nhận trạng thái**
  Run: `node ./node_modules/vitest/vitest.mjs run tests/home-ocop-aeo-polish.test.ts`

- [ ] **Step 3: Cập nhật CSS trong `web-nuxt/assets/css/home-nocturne.css`**
  Thêm hiệu ứng vi tương tác:
  ```css
  [data-home-pilot="nocturne-b1"] .home-ocop__frame:hover .wax-seal {
    transform: rotate(-3deg) scale(1.05);
    box-shadow: 0 6px 18px rgba(var(--clay-rgb, 185, 95, 56), 0.35);
  }

  [data-home-pilot="nocturne-b1"] .home-ocop__tier {
    transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1),
                background-color 0.2s ease,
                border-color 0.2s ease;
  }

  [data-home-pilot="nocturne-b1"] .home-ocop__tier:hover {
    transform: translateY(-2px);
  }
  ```

- [ ] **Step 4: Chạy test để xác nhận pass**
  Run: `node ./node_modules/vitest/vitest.mjs run tests/home-ocop-aeo-polish.test.ts tests/home-ocop-ledger.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): refine OCOP wax seal rotational micro-tilt and tier tactile elevation"`

---

### Task 5: Công Thái Học Lối Rẽ Lữ Hành & Phím Tắt Nhanh (`HomeIntentAnchors.vue`)

**Files:**
- Modify: `web-nuxt/components/home/HomeIntentAnchors.vue:170-195`
- Test: `web-nuxt/tests/challenger-homepage-stress.test.ts`

**Interfaces:**
- Consumes: Phím tắt lữ hành nổi (`.home-intent-anchor`).
- Produces: Vùng chạm công thái học $\ge 48\times 48\text{px}$, hiệu ứng nhún avatar nhẹ khi hover, và double-ring focus indicator chuẩn WCAG 2.2 AAA.

- [ ] **Step 1: Viết test kiểm tra kích thước chạm và focus ring của Intent Anchors**
  Bổ sung assertions trong `web-nuxt/tests/challenger-homepage-stress.test.ts`:
  ```typescript
  it('enforces touch target >= 48px and double-ring focus on HomeIntentAnchors', () => {
    const anchorsContent = readFileSync(resolve(webNuxt, 'components/home/HomeIntentAnchors.vue'), 'utf8')
    expect(anchorsContent).toMatch(/min-height:\s*48px/)
    expect(anchorsContent).toMatch(/\.home-intent-anchor:focus-visible/)
  })
  ```

- [ ] **Step 2: Chạy test để xác nhận trạng thái**
  Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-homepage-stress.test.ts`

- [ ] **Step 3: Cập nhật CSS trong `web-nuxt/components/home/HomeIntentAnchors.vue`**
  Đảm bảo viền Liquid Glass, transition gia tốc lò xo và hover avatar:
  ```css
  .home-intent-anchor:hover .home-intent-anchor__avatar {
    transform: scale(1.06);
    transition: transform 0.25s var(--ease-out);
  }
  ```

- [ ] **Step 4: Chạy test kiểm chứng**
  Run: `node ./node_modules/vitest/vitest.mjs run tests/challenger-homepage-stress.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): refine intent anchor avatar micro-motion and touch ergonomics"`

---

### Task 6: Kiểm Thử Toàn Diện, Kiểm Toán Nợ Token, Biên Dịch Sản Xuất & Triển Khai VPS

**Files:**
- Verify: Toàn bộ kho mã nguồn `web-nuxt/`
- Target VPS: `66.42.57.202` (`/opt/vinhlong360/web-nuxt`)

- [ ] **Step 1: Kiểm toán nợ token màu sắc**
  Run: `node scripts/check-tri-region-color-debt.mjs`
  Expected: `computed token debt: semantic 0, z-index 0` -> PASS.

- [ ] **Step 2: Kiểm toán hợp đồng màu sắc & tương phản**
  Run: `node scripts/check-tri-region-contrast.mjs`
  Expected: 100% checks PASS.
  Run: `node ./node_modules/vitest/vitest.mjs run tests/tri-region-color-contract.test.ts`
  Expected: 78/78 tests passed.

- [ ] **Step 3: Chạy bộ kiểm thử trang chủ Vitest**
  Run: `node ./node_modules/vitest/vitest.mjs run tests/home-`
  Expected: 100% passed trên toàn bộ 22 test suites.

- [ ] **Step 4: Kiểm tra kiểu dữ liệu TypeScript**
  Run: `npm run typecheck`
  Expected: Exit code 0 (0 errors).

- [ ] **Step 5: Kiểm tra cổng an toàn cứng**
  Run: `python ../scripts/checks/run_hard.py --all`
  Expected: `hard=0, ratchet không tăng`.

- [ ] **Step 6: Xác thực tính bất biến cơ sở dữ liệu (B1, B6, B7)**
  Run: `python -c "import hashlib; print('DB SHA256:', hashlib.sha256(open('../agent/data/vinhlong360.db', 'rb').read()).hexdigest())"`
  Expected: Khớp 100% mã băm gốc (`a777d4f6d83558925935efa411b2bbcb64896ed6c0af603bd41f2910209dfdc6`).

- [ ] **Step 7: Biên dịch sản xuất Nitro**
  Run: `npm run build`
  Expected: Nitro build thành công sạch sẽ.

- [ ] **Step 8: Đóng gói và triển khai lên máy chủ VPS `66.42.57.202`**
  Run:
  ```powershell
  tar.exe -czf dist_output.tar.gz -C web-nuxt .output
  scp -o StrictHostKeyChecking=no dist_output.tar.gz root@66.42.57.202:/opt/vinhlong360/web-nuxt/dist_output.tar.gz
  ssh -o StrictHostKeyChecking=no root@66.42.57.202 "cd /opt/vinhlong360/web-nuxt && tar -xzf dist_output.tar.gz && rm dist_output.tar.gz && systemctl restart vl-nuxt.service && systemctl status vl-nuxt.service --no-pager"
  Remove-Item -Force dist_output.tar.gz
  ```

- [ ] **Step 9: Xác thực trực tiếp trên môi trường live**
  Run: `curl.exe -Is https://vinhlong360.vn`
  Expected: `HTTP/1.1 200 OK`.

- [ ] **Step 10: Đồng bộ mã nguồn Git & Cập nhật Walkthrough**
  Run: `git push origin codex/correction-case-pilot`
  Cập nhật `task.md` và `walkthrough.md`.
