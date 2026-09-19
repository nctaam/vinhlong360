# Homepage UI Deepening & Simplification (Part 5) Implementation Plan

> STATUS: completed (2026-09-19) — Homepage tactile polish and radius control unification completed.
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện sâu hơn các chi tiết xúc giác (tactile micro-interactions), đồng bộ hóa 100% bo góc nút bấm tiêu chuẩn và tạo điểm tựa thị giác cho các thẻ hành trình tiếp nối ở chân trang chủ theo triết lý "sâu hơn, đơn giản, không thêm".

**Architecture:** Sử dụng trực tiếp hệ thống token chuẩn (`--radius-control: 8px`, `--border-liquid-glass`, `--alluvial-gold`, `tabular-nums lining-nums`). Không thêm bất kỳ component, thẻ HTML hay thư viện ngoài nào nhằm bảo vệ nghiêm ngặt ngân sách R30.7 CSS.

**Tech Stack:** Nuxt 3, Vue 3, CSS Tokens (Tri-Region Design System), Vitest, Happy-DOM, Python AST check gates.

**Spec:** Triết lý "Sâu hơn, đơn giản, không thêm" từ user prompt và Tiêu chuẩn thiết kế giao diện di sản R30.

## Global Constraints

- Không thêm bất kỳ component mới hay section cấp cao mới (Zero Scope Inflation).
- Duy trì 5 section cấp cao: `['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation']`.
- Giữ vững ngân sách CSS nén R30.7: trần cứng $\le 194.560\text{ bytes}$ gzipped ($190\text{ kB}$).
- Đồng bộ hóa triệt để bo góc nút bấm: Mọi action button/CTA phải dùng `border-radius: var(--radius-control);` (8px). Các tag/badge/stamp tiếp tục dùng `var(--radius-pill);`.
- TDD bắt buộc: Viết failing test trước khi sửa mã nguồn; chạy test pass mới commit.
- 0 vi phạm giọng văn R50.2 (`check_content_voice.py`).

---

### Task 1: Unify Catalog AEO Plaque CTA Button Radius

**Files:**
- Modify: `web-nuxt/components/CatalogAeoPlaque.vue:224`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: CSS token `var(--radius-control)` (8px)
- Produces: Nhất quán thị giác 100% giữa CTA button của Folio IV và hệ thống nút bấm `.btn` trên toàn site.

- [ ] **Step 1: Write the failing test**

Thêm test `Task 16` vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 16: Catalog AEO Plaque CTA button enforces unified border-radius control token', () => {
    const aeoVue = readFileSync(resolve(__dirname, '../components/CatalogAeoPlaque.vue'), 'utf8')
    expect(aeoVue).toMatch(/\.catalog-aeo-plaque__cta\s*\{[^}]*border-radius:\s*var\(--radius-control\);/)
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix web-nuxt test tests/home-deep-simplify.test.ts`
Expected: FAIL với assertion lỗi vì `CatalogAeoPlaque.vue` đang dùng `var(--radius-pill)`.

- [ ] **Step 3: Implement minimal code**

Tại [CatalogAeoPlaque.vue](web-nuxt/components/CatalogAeoPlaque.vue):
Thay:
```css
  border-radius: var(--radius-pill);
```
Bằng:
```css
  border-radius: var(--radius-control);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix web-nuxt test tests/home-deep-simplify.test.ts`
Expected: PASS (16/16 tests pass).

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/CatalogAeoPlaque.vue web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "style(home): unify border-radius control token on catalog AEO plaque CTA button"
```

---

### Task 2: Ground Folio V Continuation Links into Tactile Field Cards with Alluvial Accent

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css:1025-1045`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: CSS tokens `var(--color-canvas)`, `var(--border-liquid-glass)`, `var(--radius-control)`, `var(--alluvial-gold)`.
- Produces: 3 liên kết mở rộng hành trình ở chân trang có khung card thực địa vững chãi, bo góc 8px đồng bộ, và viền phù sa điểm nhấn cho lối vào danh mục toàn diện.

- [ ] **Step 1: Write the failing test**

Thêm test `Task 17` vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 17: Folio V Continuation waypoints structured as tactile cards with unified control radius and featured accent', () => {
    const freshNocturneCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
    expect(freshNocturneCss).toMatch(/\.home-continuation__links\s+a\s*\{[^}]*border-radius:\s*var\(--radius-control\);/)
    expect(freshNocturneCss).toMatch(/\.home-continuation__links\s+a\s*\{[^}]*background:\s*var\(--color-canvas\);/)
    expect(freshNocturneCss).toMatch(/\.home-continuation__link--featured\s*\{[^}]*border-left:\s*3px\s+solid\s+var\(--alluvial-gold/)
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix web-nuxt test tests/home-deep-simplify.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implement minimal code**

Tại [home-nocturne.css](web-nuxt/assets/css/home-nocturne.css):
Cập nhật `.home-continuation__links a`:
```css
[data-home-pilot="nocturne-b1"] .home-continuation__links a {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 54px;
  padding: var(--space-3) var(--space-4);
  color: var(--color-text);
  text-decoration: none;
  background: var(--color-canvas);
  border: 1px solid var(--border-liquid-glass, var(--color-border));
  border-radius: var(--radius-control);
  box-shadow: 0 1px 3px rgba(var(--black-rgb), 0.03);
  transition: transform .2s, color .2s, background .2s, border-color .2s, box-shadow .2s;
}

[data-home-pilot="nocturne-b1"] .home-continuation__links a:hover {
  color: var(--color-brand);
  background: color-mix(in srgb, var(--mangthit-600) 6%, var(--color-surface));
  border-color: color-mix(in srgb, var(--color-brand) 30%, var(--color-border));
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(var(--black-rgb), 0.06);
}

[data-home-pilot="nocturne-b1"] .home-continuation__link--featured {
  border-left: 3px solid var(--alluvial-gold, var(--color-brand));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix web-nuxt test tests/home-deep-simplify.test.ts`
Expected: PASS (17/17 tests pass).

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "style(home): ground folio V continuation waypoints as tactile cards with alluvial accent"
```

---

### Task 3: Expand Tabular Numerics to Timeline Stops and Schedule Durations

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css:60`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: CSS property `font-variant-numeric: tabular-nums lining-nums`
- Produces: Căn chỉnh số học đều đặn, chuẩn nhịp điệu thực địa cho các số thứ tự chặng (`1`, `2`, `3`) và mốc giờ (`07:30`, `11:30`) của lịch trình.

- [ ] **Step 1: Write the failing test**

Thêm test `Task 18` vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 18: Tabular numerics applied to itinerary stop numbers and schedule timings', () => {
    const freshNocturneCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
    expect(freshNocturneCss).toMatch(/tabular-nums[\s\S]*?\.home-planner-stop__number/)
    expect(freshNocturneCss).toMatch(/tabular-nums[\s\S]*?\.home-planner-stop__time/)
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix web-nuxt test tests/home-deep-simplify.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implement minimal code**

Tại [home-nocturne.css](web-nuxt/assets/css/home-nocturne.css):
Cập nhật danh sách selector:
Thêm `.home-planner-stop__number, .home-planner-stop__time, .home-planner-tab-btn__badge` và loại bỏ class thừa `.home-hotline-btn__num`.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix web-nuxt test tests/home-deep-simplify.test.ts`
Expected: PASS (18/18 tests pass).

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "style(home): expand tabular numerics to itinerary stop numbers and schedule timings"
```

---

### Task 4: Full Verification Suite & Strict R30.7 CSS Budget Ratchet

**Files:**
- Run all test suites across homepage
- Measure and verify CSS bundle budget

- [ ] **Step 1: Run full homepage test suite**
Run: `npm --prefix web-nuxt test tests/home-deep-simplify.test.ts tests/home-editorial-e2e.test.ts tests/challenger-homepage-stress.test.ts tests/home-curated-showcase.test.ts tests/home-hero-dossier-polish.test.ts tests/home-decision-category.test.ts tests/home-layout-asymmetry.test.ts`
Expected: 120+ tests pass 100%.

- [ ] **Step 2: Run voice & documentation checks**
Run: `python -m scripts.checks.check_content_voice` (0 vi phạm)
Run: `python -m scripts.checks.check_doc_status` (0 vi phạm)

- [ ] **Step 3: Build & verify bundle budget (R30.7)**
Run: `npm --prefix web-nuxt run build`
Run: `$env:PYTHONIOENCODING="utf-8"; python -m scripts.checks.check_bundle`
Expected: `✓ R30.7 bundle budget: đạt` (CSS total $\le 190\text{ kB}$ gz).

- [ ] **Step 4: Update Walkthrough & Push**
Update `walkthrough.md`.
Run: `git push origin codex/correction-case-pilot`
