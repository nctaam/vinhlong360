> STATUS: active (2026-09-17)

# Kế Hoạch Hiện Thực Hóa: Tinh Tế Hóa Mỹ Thuật Biên Tập Trang Chủ Vĩnh Long 360 (Homepage Deep Editorial Craft Plan)


> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện giao diện Trang Chủ (`pages/index.vue`, `components/home/*`, `assets/css/home-nocturne.css`) sâu hơn và tinh tế hơn bằng việc áp dụng các kỹ năng chuyên sâu `impeccable`, `frontend-design`, `ui-ux-pro-max` và `checklist-design`: chuẩn hóa bề mặt trình duyệt (custom scrollbars, text selection, caret), bảo vệ ấn loát tiếng Việt chống rớt từ (text-wrap balance, widow/orphan prevention, tabular nums), nâng tầm dải cá nhân hóa "Dành Cho Bạn", hoàn thiện trạng thái phục hồi "Bến đò chờ con nước", bảo đảm 100% WCAG 2.2 AAA kép và 0 nợ token.

**Architecture:** Kết hợp mỹ học ấn loát tạp chí đương đại (*Monocle*, *Rijksmuseum*) với công thái học sông nước Cửu Long (*Visit Oslo*, *National Geographic*). Mọi chi tiết tương tác đều có xúc giác phản hồi vật lý, chiều sâu trường ảnh đa tầng qua viền bắt sáng *Liquid Glass* (`var(--border-liquid-glass)`), đổ bóng than củi hữu cơ (`var(--shadow-card-ambient)`), và chỉ báo tiếp cận kép cho người dùng bàn phím (`var(--color-focus)`).

**Tech Stack:** Nuxt 4 (SSR), Vue 3 Composition API, PostCSS / Modern CSS (oklch, liquid glass, custom properties, container queries), Vitest, TypeScript.

**Spec:** `web-nuxt/DESIGN.md` (Hiến pháp Thiết kế Vĩnh Long 360) & `CLAUDE.md`.

---

## Global Constraints

1. **Hiến pháp Dữ liệu Trung thực (`CLAUDE.md §1.7`):** Tuyệt đối không sinh dữ liệu giả mạo, không skeleton khi API lỗi, tôn trọng điều kiện `reading.status !== 'unavailable'`.
2. **Quy chuẩn Token Bán kính (Ratchet R30.8):** Cấm triệt để scale cũ `--radius-xs/sm/md/lg/xl`. Bắt buộc dùng semantic radius tokens: `--radius-control` (8px), `--radius-surface` (12px), `--radius-sheet` (20px), `--radius-full` (9999px), `--radius-pill` (999px).
3. **Công thái học & Tiếp cận (WCAG 2.2 AAA):** 100% phần tử tương tác đạt diện tích chạm cảm ứng $\ge 44\times 44\text{px}$; độ tương phản $\ge 7:1$ tiêu đề và $\ge 4.5:1$ văn bản; double-ring `:focus-visible` rõ ràng.
4. **Bảo toàn Bất biến Cơ sở dữ liệu (Invariants B1, B6, B7):** `agent/data/vinhlong360.db` và `web/data.json` là read-only, tuyệt đối 0 diff, giữ nguyên 100% mã băm SHA-256.
5. **Hợp đồng Màu sắc & Nợ Token:** `node scripts/check-tri-region-color-debt.mjs` phải đạt `semantic 0, z-index 0` (PASS); `node scripts/check-tri-region-contrast.mjs` đạt 100% PASS; không vi phạm allowlist `approvedConsumerTuples`.
6. **Bảo toàn 100% Kiểm thử:** Tất cả 169 tests trang chủ hiện có (`npx vitest run tests/home-`), 78 tests màu sắc (`tests/tri-region-color-contract.test.ts`), `npm run typecheck` 0 lỗi, và `python ../scripts/checks/run_hard.py --all` 0 hard violations / 0 ratchet increase.

---

## Task Breakdown

### Task 1: Chuẩn Hóa Bề Mặt Trình Duyệt Bản Địa (Custom Scrollbars, Text Selection & Caret Color)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-anti-slop-craft.test.ts`, `web-nuxt/tests/home-nocturne-page.test.ts`

**Interfaces:**
- Consumes: Bảng màu Tam Vùng (`--mangthit-600`, `--color-brand`, `--color-focus`, `--color-text`, `--color-border`).
- Produces: Hệ thống tùy biến bề mặt trình duyệt cho trang chủ (bôi đen chữ mang sắc phù sa Đất Nung, con trỏ gõ chữ màu thương hiệu, và thanh cuộn ngang mượt mà thanh lịch).

- [ ] **Step 1: Viết test kiểm tra bề mặt trình duyệt trang chủ**
  Bổ sung assertions trong `tests/home-anti-slop-craft.test.ts`:
  ```typescript
  it('defines refined browser surfaces for selection and scrollbars on homepage', () => {
    const css = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf-8')
    expect(css).toContain('[data-home-pilot="nocturne-b1"] ::selection')
    expect(css).toContain('scrollbar-width')
    expect(css).toContain('scrollbar-color')
  })
  ```

- [ ] **Step 2: Chạy test để xác nhận fail**
  Run: `npx vitest run tests/home-anti-slop-craft.test.ts`
  Expected: FAIL (chưa có quy tắc `::selection` và scrollbar trong `home-nocturne.css`).

- [ ] **Step 3: Hiện thực hóa quy tắc CSS cho bề mặt trình duyệt**
  Trong `web-nuxt/assets/css/home-nocturne.css`:
  ```css
  /* ═══════════════════════════════════════════════════
     BROWSER SURFACES: BESPOKE CRAFT (SELECTION & SCROLL)
     ═══════════════════════════════════════════════════ */
  [data-home-pilot="nocturne-b1"] ::selection {
    background: color-mix(in srgb, var(--mangthit-600) 28%, transparent);
    color: var(--color-text);
  }

  [data-home-pilot="nocturne-b1"] input,
  [data-home-pilot="nocturne-b1"] textarea {
    caret-color: var(--color-brand);
  }

  /* Tùy biến thanh cuộn ngang dải nội dung (.scroll-row) theo tông phù sa */
  [data-home-pilot="nocturne-b1"] .scroll-row {
    scrollbar-width: thin;
    scrollbar-color: color-mix(in srgb, var(--color-brand) 35%, transparent) transparent;
  }

  [data-home-pilot="nocturne-b1"] .scroll-row::-webkit-scrollbar {
    height: 6px;
  }

  [data-home-pilot="nocturne-b1"] .scroll-row::-webkit-scrollbar-track {
    background: transparent;
  }

  [data-home-pilot="nocturne-b1"] .scroll-row::-webkit-scrollbar-thumb {
    background: color-mix(in srgb, var(--color-brand) 30%, transparent);
    border-radius: var(--radius-full);
  }

  [data-home-pilot="nocturne-b1"] .scroll-row::-webkit-scrollbar-thumb:hover {
    background: color-mix(in srgb, var(--color-brand) 55%, transparent);
  }
  ```

- [ ] **Step 4: Chạy test để xác nhận pass**
  Run: `npx vitest run tests/home-anti-slop-craft.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): craft bespoke browser surfaces for text selection, caret, and scrollbars"`

---

### Task 2: Bảo Vệ Ấn Loát Tiếng Việt & Chống Rớt Từ (Typography Balance & Tabular Numerals)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-world-class-editorial.test.ts`

**Interfaces:**
- Consumes: Font tokens `var(--font-editorial-display)`, `var(--font-editorial)`, `var(--leading-snug)`.
- Produces: Quy chuẩn phân bố dòng chữ cho tiêu đề tiếng Việt chống rớt từ đơn chiếc (`text-wrap: balance` / `text-wrap: pretty`), giãn dòng an toàn cho dấu thanh tiếng Việt (`--leading-snug: 1.35`), và chữ số cố định (`tabular-nums`) cho tọa độ/số đếm.

- [ ] **Step 1: Viết test kiểm tra cân bằng ấn loát tiêu đề**
  Bổ sung assertions trong `tests/home-world-class-editorial.test.ts`:
  ```typescript
  it('enforces balanced text wrapping and tabular numerals across homepage headings', () => {
    const css = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf-8')
    expect(css).toMatch(/h1[\s\S]*?text-wrap:\s*balance/)
    expect(css).toMatch(/h2[\s\S]*?text-wrap:\s*balance/)
  })
  ```

- [ ] **Step 2: Chạy test để xác nhận trạng thái**
  Run: `npx vitest run tests/home-world-class-editorial.test.ts`

- [ ] **Step 3: Hiện thực hóa bảo vệ ấn loát trong CSS**
  Thêm vào `web-nuxt/assets/css/home-nocturne.css`:
  - Đảm bảo các tiêu đề chính (`.hero-main h1`, `.section-head h2`, `.home-curated-lead__title`, `.home-culinary-card__title`, `.home-product-lead__name`) có `text-wrap: balance;` và `text-wrap: pretty;`.
  - Giữ khoảng hở dấu thanh an toàn: `line-height: var(--leading-snug, 1.35)` trên các tiêu đề mang font Lora có dấu xếp tầng.
  - Áp dụng `font-variant-numeric: tabular-nums` cho toàn bộ hiển thị tọa độ GPS, thời gian và số liệu để tránh rung lắc bố cục khi hover.

- [ ] **Step 4: Chạy test kiểm chứng**
  Run: `npx vitest run tests/home-world-class-editorial.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): harden vietnamese typography balance, diacritic line heights, and tabular numerals"`

---

### Task 3: Nâng Tầm Mỹ Thuật Dải Cá Nhân Hóa "Dành Cho Bạn" (`for-you-row` & `fy-chip`)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Modify: `web-nuxt/pages/index.vue:350-366`
- Test: `web-nuxt/tests/home-nocturne-components.test.ts`

**Interfaces:**
- Consumes: Dữ liệu lịch sử đã xem / đã lưu (`forYou` items).
- Produces: Dải thẻ cá nhân hóa với viền bắt sáng Liquid Glass, độ sâu xúc giác, `:focus-visible` ring kép và tương tác nhún vật lý.

- [ ] **Step 1: Viết test kiểm tra thẻ cá nhân hóa .fy-chip**
  Trong `tests/home-nocturne-components.test.ts`:
  ```typescript
  it('styles for-you chip with liquid glass border, focus-visible, and touch ergonomics', () => {
    const css = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf-8')
    expect(css).toMatch(/\.fy-chip:focus-visible/)
    expect(css).toMatch(/\.fy-chip:active/)
  })
  ```

- [ ] **Step 2: Chạy test xác nhận fail**
  Run: `npx vitest run tests/home-nocturne-components.test.ts`

- [ ] **Step 3: Cập nhật CSS cho `.fy-chip`**
  Trong `web-nuxt/assets/css/home-nocturne.css`:
  ```css
  [data-home-pilot="nocturne-b1"] .fy-chip {
    display: inline-flex;
    align-items: center;
    gap: var(--space-3);
    min-height: var(--touch-min, 44px);
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--border-liquid-glass, var(--color-border));
    border-radius: var(--radius-control);
    background: var(--color-surface);
    color: var(--color-text);
    text-decoration: none;
    box-shadow: 0 1px 3px rgba(var(--black-rgb), 0.04);
    transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1),
                border-color 0.2s ease,
                box-shadow 0.2s ease;
  }

  [data-home-pilot="nocturne-b1"] .fy-chip:hover {
    transform: translateY(-2px);
    border-color: var(--color-brand);
    box-shadow: 0 4px 12px rgba(var(--black-rgb), 0.08);
  }

  [data-home-pilot="nocturne-b1"] .fy-chip:active {
    transform: scale(0.98);
  }

  [data-home-pilot="nocturne-b1"] .fy-chip:focus-visible {
    outline: 2px solid var(--color-focus);
    outline-offset: 2px;
  }
  ```

- [ ] **Step 4: Chạy test kiểm chứng**
  Run: `npx vitest run tests/home-nocturne-components.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): elevate for-you personalization chips with liquid glass, tactile elevation, and focus ring"`

---

### Task 4: Nâng Tầm Văn Hóa Cho Khối Phục Hồi "Bến Đò Chờ Con Nước" (Degraded / Empty State)

**Files:**
- Modify: `web-nuxt/pages/index.vue:131-139`
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-terroir-resilience.test.ts`

**Interfaces:**
- Consumes: `homeFailed`, `homeError`, hàm `refreshHome()`.
- Produces: Khối phục hồi khi mạng chậm mang đậm tinh thần văn hóa bản địa ("Bến đò chờ con nước"), nút bấm chạm chuẩn công thái học $\ge 44\times 44\text{px}$ và phản hồi nhún vật lý.

- [ ] **Step 1: Viết test cho khối phục hồi văn hóa**
  Trong `tests/home-terroir-resilience.test.ts`:
  - Khẳng định khi `homeFailed` hiển thị thông điệp văn hóa ấm áp, không dùng lỗi kỹ thuật khô cứng.
  - Nút thử lại có touch target $\ge 44\times 44\text{px}$ và `:focus-visible`.

- [ ] **Step 2: Chạy test kiểm tra trạng thái hiện tại**
  Run: `npx vitest run tests/home-terroir-resilience.test.ts`

- [ ] **Step 3: Cập nhật giao diện EmptyState trong `pages/index.vue` & CSS**
  - Tinh chỉnh tiêu đề và thông điệp:
    `title: "Bến đò chờ con nước · Đang kết nối lại"`
    `message: "Mạng chậm một chút rồi. Bạn thử tải lại để tiếp tục hải trình khám phá Vĩnh Long nhé!"`
  - Nút "Tải lại": bổ sung icon `refresh`, viền `var(--color-brand)`, phản hồi `:active scale(0.96)`, và `:focus-visible` ring kép.

- [ ] **Step 4: Chạy test xác nhận hoàn tất**
  Run: `npx vitest run tests/home-terroir-resilience.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): elevate degraded recovery state with cultural riverside motif and tactile retry control"`

---

### Task 5: Tinh Tế Hóa Đảo Tìm Kiếm & Huy Hiệu Nhận Thức Thời Tiết (Hero Search Island & Cognitive Weather Pulse)

**Files:**
- Modify: `web-nuxt/pages/index.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-smart-terroir.test.ts`, `web-nuxt/tests/challenger-homepage-stress.test.ts`

**Interfaces:**
- Consumes: `hero-cognitive-banner`, `hero-search-island`, `hero-terroir-chips`.
- Produces: Khối tìm kiếm lữ hành với viền bắt sáng Liquid Glass êm dịu, dòng gợi ý đạt tương phản chuẩn WCAG 2.2 AAA ($\ge 7:1$), và hiệu ứng phản hồi nhún nhẹ khi chạm vào terroir chips.

- [ ] **Step 1: Viết test kiểm tra tương phản và vi tương tác của Hero Search Island**
  Bổ sung assertions trong `tests/home-smart-terroir.test.ts`:
  - Khẳng định `.hero-search-island__hint` có độ tương phản đạt chuẩn.
  - Khẳng định `.hero-cognitive-banner` có viền Liquid Glass và bóng ambient.

- [ ] **Step 2: Chạy test xác nhận trạng thái**
  Run: `npx vitest run tests/home-smart-terroir.test.ts`

- [ ] **Step 3: Cập nhật CSS cho `.hero-cognitive-banner` và `.hero-search-island`**
  - Bổ sung hiệu ứng vi tương tác hover nhẹ cho `.hero-cognitive-banner`:
    `backdrop-filter: blur(20px) saturate(180%);`
    `border: 1px solid var(--border-liquid-glass);`
    `box-shadow: 0 4px 16px rgba(var(--black-rgb), 0.1);`
  - Chuẩn hóa màu chữ `.hero-search-island__hint` sang `rgba(var(--white-rgb), 0.88)` để bảo đảm tương phản tối ưu trên nền ảnh sông nước.

- [ ] **Step 4: Chạy test kiểm chứng**
  Run: `npx vitest run tests/home-smart-terroir.test.ts tests/challenger-homepage-stress.test.ts`
  Expected: PASS 100%.

- [ ] **Step 5: Commit**
  `git commit -m "feat(home): refine hero search island contrast and cognitive weather banner ambiance"`

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
  Run: `npx vitest run tests/tri-region-color-contract.test.ts`
  Expected: 78/78 tests passed.

- [ ] **Step 3: Chạy bộ kiểm thử trang chủ Vitest**
  Run: `npx vitest run tests/home-`
  Expected: 169/169 tests passed (22 test suites).

- [ ] **Step 4: Kiểm tra kiểu dữ liệu TypeScript**
  Run: `npm run typecheck`
  Expected: Exit code 0 (0 errors).

- [ ] **Step 5: Kiểm tra cổng an toàn cứng**
  Run: `python ../scripts/checks/run_hard.py --all`
  Expected: `hard=0, ratchet không tăng`.

- [ ] **Step 6: Xác thực tính bất biến cơ sở dữ liệu (B1, B6, B7)**
  Run: `python -c "import hashlib; print('DB SHA256:', hashlib.sha256(open('../agent/data/vinhlong360.db', 'rb').read()).hexdigest())"`
  Expected: Khớp 100% mã băm gốc.

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
