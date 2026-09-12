# Platform UI & Stitch Anti-Slop Editorial Perfection Implementation Plan

> STATUS (2026-09-12): Proposed implementation plan for platform-wide UI refinement, independent evaluation, anti-AI-slop craftsmanship, and Stitch cloud integration.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Elevate Vinh Long 360's entire platform experience (Homepage, Interactive Map, OCOP Gold Book, Community Dispatches, Platform Typography & Ergonomics) into a world-class cultural editorial benchmark (Rijksmuseum, National Geographic, Visit Oslo, Monocle), resolving all visual defects, eradicating AI slop, ensuring WCAG 2.2 AAA accessibility, and synchronizing to Google Stitch MCP.

**Architecture:** A multi-layered design refinement that enforces balanced editorial grid rhythms, enhances responsive layout containers, polishes tactile micro-interactions with hardware-accelerated transitions, establishes authentic artisanal textures (Guilloche security borders, terracotta kiln badges), and unifies typography across all routes with Lora serif while eliminating legacy fallbacks.

**Tech Stack:** Nuxt 3, Vue 3, TypeScript, CSS Variables & Container Queries, Google Fonts (Lora, Fraunces, Newsreader), Leaflet/Map, Vitest, Google Stitch MCP.

**Spec:** [docs/superpowers/specs/2026-09-12-stitch-anti-slop-design-constitution.md](../specs/2026-09-12-stitch-anti-slop-design-constitution.md)

## Global Constraints
- Preserve 100% of existing tests: 74 home tests (`tests/home-*.test.ts`) and 78 tri-region color contract tests (`tests/tri-region-color-contract.test.ts`).
- Maintain the 5 fixed homepage sections order: `context` -> `editorial-lead` -> `quick-decisions` -> `signals` -> `journey-continuation`.
- Strict anti-AI-slop rules: zero emojis in structural controls, zero purple/cyan SaaS neon gradients, zero gray mush box-shadows, zero stranded single cards in grid rows.
- Minimum touch target >= 44x44px for all interactive controls (WCAG 2.2 AAA).
- Pre-commit check compliance: R60.1 status blockquote in first 10 lines, R60.4 relative link resolution.

---

### Task 1: Balanced Desktop Category Exploration Grid (`HomeCategoryIndex.vue` & `home-nocturne.css`)

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css:490-530`, `2400-2415`
- Modify: `web-nuxt/components/home/HomeCategoryIndex.vue:10-39`
- Test: `web-nuxt/tests/home-category-balance.test.ts`

**Interfaces:**
- Consumes: `HomeCategoryGroups` from `utils/homeNocturnePresentation.ts`
- Produces: Seamless 4-column balanced desktop grid (`repeat(4, minmax(0, 1fr))`) and 2x2 tablet grid with zero dangling or stranded cards on subsequent rows, while maintaining `.home-category-index__card--lead` asymmetric rule for layout tests.

- [ ] **Step 1: Write the failing test**

```typescript
// web-nuxt/tests/home-category-balance.test.ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Home Category Index Balanced Editorial Layout', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const catVue = readFileSync(resolve(__dirname, '../components/home/HomeCategoryIndex.vue'), 'utf8')

  it('preserves lead card class while enforcing balanced desktop grid rules', () => {
    expect(catVue).toContain('home-category-index__card--lead')
    expect(homeCss).toContain('.home-category-index__card--lead')
    expect(homeCss).toMatch(/\.home-category-index__card--lead\s*\{[^}]*grid-column:\s*span\s*2/)
  })

  it('guarantees balanced 4-column desktop display without empty grid holes', () => {
    expect(homeCss).toContain('BALANCED 4-COLUMN DESKTOP CATEGORY ROW')
    expect(homeCss).toMatch(/@media\s*\(\s*min-width:\s*960px\s*\)[^{]*\{[\s\S]*?\.home-category-index__primary\s*\{[\s\S]*?grid-template-columns:\s*repeat\(\s*4\s*,\s*minmax\(0\s*,\s*1fr\)\s*\)/)
  })

  it('has smooth micro-transitions and elevated shadow on card hover', () => {
    expect(homeCss).toMatch(/\.home-category-index__primary-link:hover[\s\S]*?transform:\s*translateY\(-3px\)/)
    expect(homeCss).toMatch(/\.home-category-index__primary-link:hover\s+\.home-category-index__media-img[\s\S]*?scale\(1\.06\)/)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/home-category-balance.test.ts`
Expected: FAIL (file not found or assertions missing).

- [ ] **Step 3: Implement minimal code to pass test**

Update `web-nuxt/assets/css/home-nocturne.css` to refine the desktop media query ensuring `.home-category-index__primary` has `grid-template-columns: repeat(4, minmax(0, 1fr))`, `gap: var(--space-4)`, and overrides lead span on >= 960px to preserve the 4-card single-row rhythm while keeping the base definition `grid-column: span 2` intact for container/narrow queries.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run tests/home-category-balance.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/home-category-balance.test.ts assets/css/home-nocturne.css components/home/HomeCategoryIndex.vue
git commit -m "fix(home): balance primary category grid to eliminate dangling card on desktop"
```

---

### Task 2: Elevate Community Dispatches into Traveler's Field Notes (`HomeCommunityFeed.vue` & `home-nocturne.css`)

**Files:**
- Modify: `web-nuxt/components/home/HomeCommunityFeed.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css:2100-2250`
- Test: `web-nuxt/tests/home-community-editorial.test.ts`

**Interfaces:**
- Consumes: Post items from `useCommunity()` composable
- Produces: High-craftsmanship "Sổ tay lữ khách & Cảm hứng bản địa" cards with serif quote typography, contributor badge tier, and verified location pill.

- [ ] **Step 1: Write the failing test**

```typescript
// web-nuxt/tests/home-community-editorial.test.ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Community Feed Editorial Field Notes Craft', () => {
  const commVue = readFileSync(resolve(__dirname, '../components/home/HomeCommunityFeed.vue'), 'utf8')
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')

  it('incorporates authentic traveler dispatches and local contributor badges', () => {
    expect(commVue).toContain('cộng đồng')
    expect(commVue).toContain('line-icon')
  })

  it('prohibits AI emojis in community section and enforces vector iconography', () => {
    expect(commVue).not.toMatch(/[\u{1F300}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u)
  })

  it('applies editorial serif styling and subtle terracotta borders for dispatches', () => {
    expect(homeCss).toContain('.home-community-dispatches')
    expect(homeCss).toMatch(/--font-editorial/)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/home-community-editorial.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implement minimal code to pass test**

In `web-nuxt/components/home/HomeCommunityFeed.vue` and `web-nuxt/assets/css/home-nocturne.css`, wrap community posts in `.home-community-dispatches` with refined typography, `--font-editorial` quote styling, contributor authority pills ("Người bản địa", "Nhiếp ảnh gia", "Lữ khách"), and zero raw emoji.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run tests/home-community-editorial.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/home-community-editorial.test.ts components/home/HomeCommunityFeed.vue assets/css/home-nocturne.css
git commit -m "feat(community): transform feed into editorial traveler field notes with author badges"
```

---

### Task 3: Interactive Heritage Map Ergonomics & Outdoor Contrast (`pages/ban-do.vue` & `assets/css/catalog.css`)

**Files:**
- Modify: `web-nuxt/pages/ban-do.vue:20-75`
- Modify: `web-nuxt/assets/css/catalog.css:1400-1550`
- Test: `web-nuxt/tests/map-terroir-ergonomics.test.ts`

**Interfaces:**
- Consumes: Map pins and water presets from `ban-do.vue`
- Produces: High outdoor contrast toggle (`outdoorContrast`) with tactile feedback and verified Mekong waterway presets (Kinh Thầy Cai, Sông Tiền, Sông Cổ Chiên).

- [ ] **Step 1: Write the failing test**

```typescript
// web-nuxt/tests/map-terroir-ergonomics.test.ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Interactive Heritage Map Ergonomics & Terroir Utility', () => {
  const mapVue = readFileSync(resolve(__dirname, '../pages/ban-do.vue'), 'utf8')
  const catalogCss = readFileSync(resolve(__dirname, '../assets/css/catalog.css'), 'utf8')

  it('includes outdoor contrast toggle button with accessible aria-pressed state', () => {
    expect(mapVue).toContain('map-contrast-toggle')
    expect(mapVue).toContain('aria-pressed="outdoorContrast"')
    expect(mapVue).toContain('Tương phản ngoài trời')
  })

  it('contains quick water presets with vector icons and terracotta active styling', () => {
    expect(mapVue).toContain('map-quick-presets')
    expect(mapVue).toContain('activeWaterPreset')
    expect(catalogCss).toContain('.map-quick-preset-btn')
    expect(catalogCss).toContain('.map-contrast-toggle')
  })

  it('enforces min 44px touch target on map controls for mobile ergonomics', () => {
    expect(catalogCss).toMatch(/\.map-quick-preset-btn[\s\S]*?min-height:\s*(?:44px|2\.75rem)/)
    expect(catalogCss).toMatch(/\.map-contrast-toggle[\s\S]*?min-height:\s*(?:44px|2\.75rem)/)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/map-terroir-ergonomics.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implement minimal code to pass test**

In `web-nuxt/assets/css/catalog.css`, ensure `.map-quick-preset-btn` and `.map-contrast-toggle` have `min-height: 44px; min-width: 44px;`, tactile pressed styling, and crisp outdoor contrast tokens.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run tests/map-terroir-ergonomics.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/map-terroir-ergonomics.test.ts pages/ban-do.vue assets/css/catalog.css
git commit -m "feat(map): enhance map ergonomics with 44px touch targets and outdoor contrast support"
```

---

### Task 4: National OCOP Gold Book Craft & Guilloche Certificate Texture (`pages/ocop.vue` & `assets/css/catalog.css`)

**Files:**
- Modify: `web-nuxt/pages/ocop.vue:1-60`
- Modify: `web-nuxt/assets/css/catalog.css:1200-1350`
- Test: `web-nuxt/tests/ocop-gold-book-craft.test.ts`

**Interfaces:**
- Consumes: OCOP star levels (3, 4, 5) and product data
- Produces: Official national registry certification styling with Guilloche background texture and terracotta seal.

- [ ] **Step 1: Write the failing test**

```typescript
// web-nuxt/tests/ocop-gold-book-craft.test.ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('National OCOP Gold Book Craft & Security Texture', () => {
  const ocopVue = readFileSync(resolve(__dirname, '../pages/ocop.vue'), 'utf8')
  const catalogCss = readFileSync(resolve(__dirname, '../assets/css/catalog.css'), 'utf8')

  it('incorporates guilloche security texture and wax seal for official certification', () => {
    expect(ocopVue).toContain('guilloche-texture')
    expect(ocopVue).toContain('wax-seal')
    expect(catalogCss).toContain('.guilloche-texture')
    expect(catalogCss).toContain('.wax-seal')
  })

  it('features star-jump navigation with tactile 44px buttons', () => {
    expect(ocopVue).toContain('star-jump')
    expect(catalogCss).toMatch(/\.star-jump-btn[\s\S]*?min-height:\s*(?:44px|2\.75rem)/)
  })

  it('strictly prohibits raw star emojis and uses SVG vector stars', () => {
    expect(ocopVue).toContain('<IconLine v-for="n in s.stars" :key="n" name="star" />')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/ocop-gold-book-craft.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implement minimal code to pass test**

In `web-nuxt/assets/css/catalog.css`, define `.guilloche-texture` with subtle mathematical curvilinear waves (`radial-gradient` / `repeating-linear-gradient` with opacity 0.04), style `.wax-seal` with Mang Thít terracotta tone, and ensure `.star-jump-btn` has `min-height: 44px`.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run tests/ocop-gold-book-craft.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/ocop-gold-book-craft.test.ts pages/ocop.vue assets/css/catalog.css
git commit -m "feat(ocop): style national gold book with guilloche certificate texture and 44px controls"
```

---

### Task 5: Platform-Wide Editorial Typography & Zero Legacy Fallback (`assets/css/`)

**Files:**
- Modify: `web-nuxt/assets/css/base.css`
- Modify: `web-nuxt/assets/css/catalog.css`
- Modify: `web-nuxt/assets/css/shell.css`
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/platform-typography-anti-slop.test.ts`

**Interfaces:**
- Consumes: Google Fonts (`Lora`, `Fraunces`, `Newsreader`)
- Produces: 100% eradication of `Times New Roman` across all stylesheets and ubiquitous `--font-editorial` application.

- [ ] **Step 1: Write the failing test**

```typescript
// web-nuxt/tests/platform-typography-anti-slop.test.ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Platform-Wide Typography Anti-Slop Discipline', () => {
  const filesToCheck = [
    '../assets/css/variables.css',
    '../assets/css/base.css',
    '../assets/css/catalog.css',
    '../assets/css/shell.css',
    '../assets/css/home-nocturne.css',
  ]

  it('bans Times New Roman fallback across every stylesheet in the project', () => {
    for (const relPath of filesToCheck) {
      const content = readFileSync(resolve(__dirname, relPath), 'utf8')
      expect(content, `File ${relPath} still contains Times New Roman fallback!`).not.toContain('Times New Roman')
    }
  })

  it('ensures Lora serif is prioritized in editorial font stacks', () => {
    const vars = readFileSync(resolve(__dirname, '../assets/css/variables.css'), 'utf8')
    expect(vars).toMatch(/--font-editorial:\s*'Lora'/)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/platform-typography-anti-slop.test.ts`
Expected: FAIL (if any stylesheet references Times New Roman).

- [ ] **Step 3: Implement minimal code to pass test**

Clean any occurrences of `Times New Roman` from all listed stylesheets, ensuring they cleanly fall back to `'Lora', 'Fraunces', 'Newsreader', serif`.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run tests/platform-typography-anti-slop.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/platform-typography-anti-slop.test.ts assets/css/
git commit -m "feat(typography): enforce Lora editorial font and eliminate Times New Roman platform-wide"
```

---

### Task 6: Google Stitch MCP Cloud Synchronization, Full Test Suite & Live VPS Deployment

**Files:**
- Synchronize: Google Stitch MCP Project `14916181929760067680`
- Verify: Full test suites, typecheck, pre-commit checks
- Deploy: Live VPS `66.42.57.202`

- [ ] **Step 1: Run comprehensive local test suites**

Run:
```bash
npx vitest run tests/home-
npx vitest run tests/tri-region-color-contract.test.ts
npm run typecheck
python ../scripts/checks/run_hard.py --all
```
Expected: 100% tests pass, 0 type errors, 0 hard violations.

- [ ] **Step 2: Build production Nitro bundle**

Run: `npm run build`
Expected: Succeeded with Nitro output size ~6.4MB.

- [ ] **Step 3: Synchronize updated Design System to Stitch MCP**

Invoke Stitch MCP tools `upload_design_md` and `create_design_system_from_design_md` on project `14916181929760067680`.

- [ ] **Step 4: Deploy to VPS 66.42.57.202 and verify live**

Package and transfer `.output` and source updates to VPS, execute atomic swap script, restart `vl-nuxt`, and verify HTTP 200 on `https://vinhlong360.vn`.

- [ ] **Step 5: Commit and push**

```bash
git push origin codex/correction-case-pilot
```
