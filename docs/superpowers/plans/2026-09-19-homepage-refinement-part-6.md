# Homepage UI Deepening & Simplification (Part 6) Implementation Plan

> STATUS: completed (2026-09-19) — Homepage tactile arrow and button active press states completed.
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện sâu sắc và vi mô hóa 100% các phản hồi xúc giác (tactile arrow micro-interactions and active tap states) trên toàn bộ các thẻ và nút khám phá từ Folio I đến Folio V theo triết lý "sâu hơn, đơn giản, không thêm".

**Architecture:** Sử dụng trực tiếp các quy tắc micro-interaction nhẹ nhàng (`transform: translateX(3px)`, `transform: scale(0.98)`). Không bổ sung bất kỳ component hay thư viện ngoài nào để bảo đảm trần ngân sách R30.7 CSS nén.

**Tech Stack:** Nuxt 3, Vue 3, Scoped CSS, Vitest, Happy-DOM, Python AST pre-commit checks.

**Spec:** Triết lý "Sâu hơn, đơn giản, không thêm" từ user prompt và Tiêu chuẩn trải nghiệm vi mô R30.

## Global Constraints

- Không thêm bất kỳ component mới hay section cấp cao mới (Zero Scope Inflation).
- Duy trì 5 section cấp cao: `['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation']`.
- Giữ vững ngân sách CSS nén R30.7: trần cứng $\le 194.560\text{ bytes}$ gzipped ($190\text{ kB}$).
- Đảm bảo 100% các mũi tên định hướng (`arrow-right`) có vi mô chuyển động `translateX(3px)` đồng đều khi hover.
- Đảm bảo 100% các nút hành động/CTA có vi mô co nhẹ `:active { transform: scale(0.98); }` khi nhấn.
- TDD bắt buộc: Viết failing test trước khi sửa mã nguồn; chạy test pass mới commit.
- 0 vi phạm giọng văn R50.2 (`check_content_voice.py`).

---

### Task 1: Unify Directional Arrow Hover Transitions Across Folio I (Curated Lead & Satellites) and Folio III (Riverside Stays)

**Files:**
- Modify: `web-nuxt/components/home/HomeCuratedShowcase.vue:580, 810`
- Modify: `web-nuxt/components/home/HomeRiversideStays.vue:565`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: CSS transitions on directional arrow icons (`.line-icon:last-child`, `.home-curated-satellite__link .line-icon`).
- Produces: Phản hồi định hướng sống động, đồng bộ nhịp nhàng với Hero Feature Dossier, Culinary Trail và Continuation links.

- [ ] **Step 1: Write the failing test**

Thêm test `Task 19` vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 19: Curated showcase and riverside stays action buttons consistently animate directional arrows on hover', () => {
    const showcaseVue = readFileSync(resolve(__dirname, '../components/home/HomeCuratedShowcase.vue'), 'utf8')
    const staysVue = readFileSync(resolve(__dirname, '../components/home/HomeRiversideStays.vue'), 'utf8')

    // Folio I Lead button and Satellite link arrows
    expect(showcaseVue).toMatch(/\.home-curated-lead__actions\s+\.btn:hover\s+\.line-icon:last-child\s*\{[^}]*transform:\s*translateX\(3px\)/)
    expect(showcaseVue).toMatch(/\.home-curated-satellite__link:hover\s+\.line-icon\s*\{[^}]*transform:\s*translateX\(3px\)/)

    // Folio III Stay card action button arrow
    expect(staysVue).toMatch(/\.home-stay-card__action\s+\.btn:hover\s+\.line-icon:last-child\s*\{[^}]*transform:\s*translateX\(3px\)/)
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix web-nuxt test tests/home-deep-simplify.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implement minimal code**

1. Tại [HomeCuratedShowcase.vue](web-nuxt/components/home/HomeCuratedShowcase.vue):
   - Thêm vào `.home-curated-lead__actions .btn`:
     ```css
     .home-curated-lead__actions .btn .line-icon:last-child {
       transition: transform 0.2s ease;
     }

     .home-curated-lead__actions .btn:hover .line-icon:last-child {
       transform: translateX(3px);
     }
     ```
   - Thêm vào `.home-curated-satellite__link`:
     ```css
     .home-curated-satellite__link .line-icon {
       transition: transform 0.2s ease;
     }

     .home-curated-satellite:hover .home-curated-satellite__link .line-icon,
     .home-curated-satellite__link:hover .line-icon {
       transform: translateX(3px);
     }
     ```

2. Tại [HomeRiversideStays.vue](web-nuxt/components/home/HomeRiversideStays.vue):
   - Thêm vào `.home-stay-card__action .btn`:
     ```css
     .home-stay-card__action .btn .line-icon:last-child {
       transition: transform 0.2s ease;
     }

     .home-stay-card__action .btn:hover .line-icon:last-child {
       transform: translateX(3px);
     }
     ```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix web-nuxt test tests/home-deep-simplify.test.ts`
Expected: PASS (19/19 tests pass).

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/home/HomeCuratedShowcase.vue web-nuxt/components/home/HomeRiversideStays.vue web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "style(home): unify directional arrow hover micro-interactions across Folios I & III"
```

---

### Task 2: Unify Tactile Active/Press State for Catalog AEO Plaque CTA Button

**Files:**
- Modify: `web-nuxt/components/CatalogAeoPlaque.vue:235`
- Test: `web-nuxt/tests/home-deep-simplify.test.ts`

**Interfaces:**
- Consumes: CSS `:active` selector
- Produces: Phản hồi cảm giác xúc giác bấm nảy `transform: scale(0.98)` đồng bộ với tất cả các nút bấm khác trên trang chủ.

- [ ] **Step 1: Write the failing test**

Thêm test `Task 20` vào `web-nuxt/tests/home-deep-simplify.test.ts`:
```typescript
  it('Task 20: Catalog AEO Plaque CTA button enforces tactile active press scale', () => {
    const aeoVue = readFileSync(resolve(__dirname, '../components/CatalogAeoPlaque.vue'), 'utf8')
    expect(aeoVue).toMatch(/\.catalog-aeo-plaque__cta:active\s*\{[^}]*transform:\s*scale\(0\.98\);/)
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix web-nuxt test tests/home-deep-simplify.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implement minimal code**

Tại [CatalogAeoPlaque.vue](web-nuxt/components/CatalogAeoPlaque.vue):
Thêm:
```css
.catalog-aeo-plaque__cta:active {
  transform: scale(0.98);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix web-nuxt test tests/home-deep-simplify.test.ts`
Expected: PASS (20/20 tests pass).

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/CatalogAeoPlaque.vue web-nuxt/tests/home-deep-simplify.test.ts
git commit -m "style(home): add tactile active press feedback to catalog AEO plaque CTA button"
```

---

### Task 3: Full Verification Suite, Strict R30.7 CSS Budget Ratchet & Push

**Files:**
- Run all test suites across homepage
- Measure and verify CSS bundle budget

- [ ] **Step 1: Run full homepage test suite**
Run: `npm --prefix web-nuxt test tests/home-deep-simplify.test.ts tests/home-editorial-e2e.test.ts tests/challenger-homepage-stress.test.ts tests/home-curated-showcase.test.ts tests/home-hero-dossier-polish.test.ts tests/home-decision-category.test.ts tests/home-layout-asymmetry.test.ts`
Expected: 125+ tests pass 100%.

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
