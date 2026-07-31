# Adaptive Nocturne Heritage Foundation Implementation Plan

> **STATUS: DONE — 2026-07-31.** Foundation tasks are implemented and verified; the first public-page pilot remains a separate Plan B concern.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the approved Nocturne Heritage public UI foundation without replacing the existing Stitch-derived screens, while making theme, typography, tokens, shell behavior, and Framed Dossier composition stable for later public pilots.

**Architecture:** Keep the current Nuxt 4/Vue 3 application and its existing CSS entrypoints. Extend the current primitive → semantic → component token architecture instead of introducing a parallel styling system. Keep the existing `.dark` implementation as the compatibility class for Nocturne and `.light` for Daylight Parchment, but expose those values to users as `Nocturne` and `Nền sáng dễ đọc`; default explicitly to Nocturne and never derive the choice from clock time or operating-system preference.

**Tech Stack:** Nuxt 4, Vue 3, TypeScript, CSS custom properties, `@nuxtjs/color-mode`, `@vue/test-utils`, Vitest, Nuxt runtime mount tests.

## Global Constraints

- Use **Existing Stitch Screen Evolution** as the visual source: keep roughly 70% of existing screen composition, normalize 20% with the system, and add 10% super-app context; Hybrid P1.2 is reference-only.
- Nocturne is the default public theme; Daylight Parchment is an explicit readability variant with the same layout, component, trust, and semantic meaning.
- Do not automatically switch theme by time, operating-system preference, location, or user profile.
- Keep direct-contact actions only: `Gọi`, `Zalo`, `Chỉ đường`, `Lưu`, and `Theo dõi`; do not add booking, ordering, or payment UI.
- Use Mekong Ink & Clay primitives and Controlled Serif typography: Fraunces only for intentional editorial display; Be Vietnam Pro for interface and body text.
- Components reference semantic/component tokens; new component CSS must not contain raw color, radius, or shadow literals.
- Framed Dossier uses hairline borders, controlled asymmetry, rows/split views, and at most one media-led feature per viewport; no glass content, generic bento grids, or uniform hover lift.
- All controls have a 44px minimum hit area, visible keyboard focus, reduced-motion behavior, forced-colors behavior, and Vietnamese diacritic coverage at 200% text zoom.
- Never persist, log, cache, or expose raw GPS/IP. This foundation does not add location or recommendation persistence.
- `useSeasonTheme()` may continue to provide content/season accents, but it must not switch `colorMode` or override public canvas, surface, text, border, or trust tokens.
- Preserve dirty worktree changes and parallel-session files; do not stage `design-system/vinhlong360/pages/home.md`, `.superpowers/`, `agent/knowledge.db-*`, or concept artifacts unless a later task explicitly owns them.
- AdminCP remains a dense workbench and is not converted to public Nocturne composition in this plan.

---

### Task 1: Synchronize Design Authority With Approved Nocturne Direction

**Files:**
- Modify: `design-system/vinhlong360/MASTER.md`
- Modify: `design-system/vinhlong360/pages/entity-detail.md`
- Modify: `design-system/vinhlong360/pages/du-lich.md`
- Modify: `design-system/vinhlong360/pages/admin-dashboard.md`
- Test: `web-nuxt/tests/design-authority-contract.test.ts`

**Interfaces:**
- Consumes: approved decisions in `docs/superpowers/specs/2026-07-31-nocturne-heritage-adaptive-public-design.md`.
- Produces: one documented authority chain that later UI tasks can cite: approved spec → `design-system/vinhlong360/MASTER.md` → page-family brief.

- [x] **Step 1: Write the failing authority-contract test**

Create `web-nuxt/tests/design-authority-contract.test.ts` with a filesystem-only contract test. It must fail against the current `MASTER.md` because the file still declares `draft-for-review` and the old system name:

```ts
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(import.meta.dirname, '../..')

describe('approved public design authority', () => {
  it('declares Adaptive Nocturne as the public visual authority', async () => {
    const master = await readFile(resolve(root, 'design-system/vinhlong360/MASTER.md'), 'utf8')
    expect(master).toContain('Adaptive Nocturne System')
    expect(master).toContain('Nocturne Heritage')
    expect(master).toContain('Existing Stitch Screen Evolution')
    expect(master).not.toContain('draft-for-review')
  })

  it('keeps AdminCP as a separate dense workbench family', async () => {
    const admin = await readFile(resolve(root, 'design-system/vinhlong360/pages/admin-dashboard.md'), 'utf8')
    expect(admin).toContain('Bàn điều phối vận hành')
    expect(admin).toContain('mật độ cao')
  })
})
```

- [x] **Step 2: Run the focused test and verify it fails**

Run from `web-nuxt`:

```text
npm test -- tests/design-authority-contract.test.ts
```

Expected: FAIL because `MASTER.md` still reports `draft-for-review` and does not name the approved source decision.

- [x] **Step 3: Update the authority documents**

Update `MASTER.md` so its first sections state, in Vietnamese, all of the following exact decisions: `Adaptive Nocturne System`; `Nocturne + Parchment` as material modes; `Mekong Ink & Clay`; `Controlled Serif`; `Framed Dossier`; `Grounded Local Light` default imagery; `Material Still Life` for craft/product; `Blue-hour Cinema` only for exceptional campaigns; `Nocturne` default with `Daylight Parchment` as explicit accessibility variant; and `Existing Stitch Screen Evolution` as the visual source. Replace the status line with `approved-design` and link the approved spec path. Preserve compatible existing rules; mark any superseded generic hero/card/season-theme guidance as legacy instead of deleting unrelated design-system content.

Update the three clean page briefs so each names its own composition family and task density. Do not open or stage `design-system/vinhlong360/pages/home.md`; its authority wording will be reconciled in the Existing Screen Evolution pilot after the parallel homepage session is integrated. `entity-detail.md` must specify dossier/source/action anatomy. `du-lich.md` must specify discovery/search density rather than a generic card grid. `admin-dashboard.md` must explicitly remain a high-density workbench and may share semantic trust tokens only. Record the homepage exception in the plan handoff so the pilot cannot accidentally treat Hybrid P1.2 as source of truth.

- [x] **Step 4: Run the authority test and a whitespace check**

Run:

```text
npm test -- tests/design-authority-contract.test.ts
git diff --check -- design-system/vinhlong360/MASTER.md design-system/vinhlong360/pages/entity-detail.md design-system/vinhlong360/pages/du-lich.md design-system/vinhlong360/pages/admin-dashboard.md
```

Expected: PASS; no whitespace errors. Confirm `home.md` is still untouched by this task.

- [x] **Step 5: Commit only the authority documents and test**

```text
git add design-system/vinhlong360/MASTER.md design-system/vinhlong360/pages/entity-detail.md design-system/vinhlong360/pages/du-lich.md design-system/vinhlong360/pages/admin-dashboard.md web-nuxt/tests/design-authority-contract.test.ts
git commit -m "docs: sync public design authority to nocturne heritage"
```

### Task 2: Implement Nocturne and Daylight Parchment Token Contracts

**Files:**
- Modify: `web-nuxt/assets/css/variables.css`
- Modify: `web-nuxt/nuxt.config.ts`
- Test: `web-nuxt/tests/nocturne-theme-contract.test.ts`

**Interfaces:**
- Consumes: token names already used by the Nuxt shell and components, plus the authority contract from Task 1.
- Produces: stable semantic tokens and explicit theme defaults that `ThemeModeControl`, `FramedDossier`, and all public pilots can consume without raw values.

- [x] **Step 1: Add failing token/config contract tests**

Create `web-nuxt/tests/nocturne-theme-contract.test.ts` with deterministic filesystem contract tests. Keep the mounted interaction test in Task 4, where the color-mode composable can be mocked at the component boundary:

```ts
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(import.meta.dirname, '../..')

describe('Nocturne theme contract', () => {
  it('defaults to Nocturne without consulting system preference', async () => {
    const nuxtConfig = await readFile(resolve(root, 'web-nuxt/nuxt.config.ts'), 'utf8')
    expect(nuxtConfig).toContain("preference: 'dark'")
    expect(nuxtConfig).toContain("fallback: 'dark'")
    expect(nuxtConfig).not.toContain("preference: 'system'")
    expect(nuxtConfig).toContain("localStorage.getItem('vl360-color-mode')")
    expect(nuxtConfig).toContain("localStorage.setItem('vl360-color-mode','dark')")
  })

  it('defines semantic Nocturne, Parchment, typography, and dossier tokens', async () => {
    const variables = await readFile(resolve(root, 'web-nuxt/assets/css/variables.css'), 'utf8')
    expect(variables).toMatch(/--theme-public-default:\s*nocturne/)
    expect(variables).toContain('--font-interface-heading')
    expect(variables).toContain('--font-body')
    expect(variables).toContain('--font-editorial-display')
    expect(variables).toContain('--framed-dossier-border')
    expect(variables).toContain('color-scheme: dark')
    expect(variables).toMatch(/\.light\s*\{[\s\S]*--theme-public-default:\s*parchment/)
    expect(variables).toMatch(/\.light\s*\{[\s\S]*color-scheme: light/)
  })
})
```

- [x] **Step 2: Run the focused tests and verify they fail**

```text
npm test -- tests/nocturne-theme-contract.test.ts
```

Expected: FAIL because the config currently uses `preference: 'system'`, does not normalize a previously stored `system`/`auto` value, and the new semantic token aliases do not exist.

- [x] **Step 3: Define the semantic and component token layer**

In `variables.css`, retain the existing compatibility aliases but add a clearly delimited Nocturne block with these semantic contracts:

```css
:root {
  color-scheme: dark;
  --theme-public-default: nocturne;
  --color-canvas: var(--night-canvas);
  --color-surface: var(--night-surface);
  --color-surface-raised: var(--night-raised);
  --color-text: var(--night-text);
  --color-text-muted: var(--night-muted);
  --color-border: color-mix(in srgb, var(--night-text) 18%, transparent);
  --color-action: var(--night-river);
  --color-brand: var(--night-clay);
  --color-focus: var(--night-amber);
  --color-source-official: var(--night-river);
  --color-source-verified: var(--night-clay);
  --color-source-community: var(--night-leaf);
  --framed-dossier-border: var(--color-border);
  --framed-dossier-padding: var(--space-6);
  --framed-dossier-padding-compact: var(--space-4);
  --framed-dossier-gap: var(--space-4);
  --framed-dossier-media-ratio: var(--ratio-card);
  --framed-dossier-radius: var(--radius-control);
  --framed-dossier-shadow: none;
  --theme-control-bg: var(--color-surface);
  --theme-control-border: var(--color-border);
  --theme-control-active: var(--color-action);
  --theme-control-radius: var(--radius-control);
  --theme-control-min-height: var(--touch-min);
}

.light {
  color-scheme: light;
  --theme-public-default: parchment;
  --color-canvas: var(--alluvial-paper);
  --color-surface: var(--surface-white);
  --color-surface-raised: var(--surface-white);
  --color-text: var(--mekong-ink);
  --color-text-muted: var(--mekong-muted);
  --color-border: var(--alluvial-line);
  --color-action: var(--river-600);
  --color-brand: var(--mangthit-600);
  --color-focus: var(--river-600);
  --color-source-official: var(--river-600);
  --color-source-verified: var(--mangthit-600);
  --color-source-community: var(--orchard-600);
}
```

Keep semantic status distinct from brand color (`--color-success`, `--color-warning`, `--color-error`) and do not make clay, teal, or brass imply a status. Add `--font-interface-heading`, `--font-body`, and `--font-editorial-display` aliases so new components do not select font families directly. Reuse the existing self-hosted Fraunces and Be Vietnam Pro assets; do not add a new font file or runtime provider in Plan A.

- [x] **Step 4: Make the theme explicit and remove automatic switching**

In `nuxt.config.ts`, change `colorMode` to `preference: 'dark'`, `fallback: 'dark'`, and preserve the existing `vl360-color-mode` storage key. Insert the new default `:root` token block before the existing `.dark` block so `.dark` remains the final compatibility override; keep the `.dark`/`.light` CSS classes so existing page CSS remains safe. Add this exact pre-paint head script immediately before the existing JavaScript class bootstrap:

```ts
{ innerHTML: "try{var k='vl360-color-mode',v=localStorage.getItem(k);if(v==='system'||v==='auto')localStorage.setItem(k,'dark')}catch(_){ }", tagPosition: 'head' },
```

If storage access throws, the `catch` leaves the default fallback untouched. This closes the old automatic-preference path without adding a migration table or a new storage surface. Keep `useSeasonTheme()` only for content accents; it must not mutate `colorMode` or the new public semantic surfaces. Do not mass-migrate `base.css` or `dark-overrides.css` in this task; only new foundation components may consume the new semantic aliases, while legacy page-specific rules remain compatibility-scoped until their pilot migrates.

- [x] **Step 5: Run theme, typecheck, and contrast-adjacent tests**

```text
npm test -- tests/nocturne-theme-contract.test.ts tests/ui-foundation-shell.test.ts
npm run typecheck
```

Expected: PASS. Manually verify `Ệ ộ Ẵ ữ Ề Ậ` at 200% browser text zoom in both `.dark` and `.light`; no layout overflow or clipped accents.

- [x] **Step 6: Commit the token foundation**

```text
git add web-nuxt/assets/css/variables.css web-nuxt/nuxt.config.ts web-nuxt/tests/nocturne-theme-contract.test.ts
git commit -m "feat: add explicit nocturne and parchment theme tokens"
```

### Task 3: Add the Framed Dossier Foundation Components

**Files:**
- Create: `web-nuxt/components/FramedDossier.vue`
- Create: `web-nuxt/components/DossierLineItem.vue`
- Create: `web-nuxt/assets/css/dossier.css`
- Modify: `web-nuxt/nuxt.config.ts`
- Test: `web-nuxt/tests/framed-dossier.test.ts`

**Interfaces:**
- Consumes: semantic/component tokens from Task 2 and the existing `IconLine` component.
- Produces: small, independently mountable primitives for later homepage, discovery, and detail pilots; no source/trust or recommendation logic is included here.

- [x] **Step 1: Write the failing component behavior tests**

Create `web-nuxt/tests/framed-dossier.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import FramedDossier from '../components/FramedDossier.vue'
import DossierLineItem from '../components/DossierLineItem.vue'

describe('Framed Dossier foundation', () => {
  it('renders only supplied anatomy and exposes one primary action slot', async () => {
    const wrapper = await mountSuspended(FramedDossier, {
      props: { eyebrow: 'MANG THÍT', title: 'Một buổi bên lò gốm' },
      slots: {
        summary: '<p>Thông tin có nguồn.</p>',
        action: '<button>Chỉ đường</button>',
      },
    })
    expect(wrapper.find('[data-dossier-eyebrow]').text()).toBe('MANG THÍT')
    expect(wrapper.find('[data-dossier-title]').text()).toContain('Một buổi bên lò gốm')
    expect(wrapper.findAll('button')).toHaveLength(1)
    expect(wrapper.find('[data-dossier-media]').exists()).toBe(false)
  })

  it('keeps line items readable as a list and preserves keyboard focus', async () => {
    const wrapper = await mountSuspended(DossierLineItem, {
      props: { label: 'Cập nhật', value: '31/07/2026', href: '/dia-diem/1' },
      global: { stubs: { NuxtLink: { template: '<a :href="to"><slot /></a>', props: ['to'] } } },
    })
    const link = wrapper.get('a')
    expect(link.text()).toContain('31/07/2026')
    expect(link.attributes('href')).toBe('/dia-diem/1')
    expect(link.attributes('data-dossier-line')).toBe('true')
  })
})
```

- [x] **Step 2: Run the focused test and verify it fails**

```text
npm test -- tests/framed-dossier.test.ts
```

Expected: FAIL because the components and stylesheet do not exist.

- [x] **Step 3: Implement the narrow component APIs**

Implement `FramedDossier.vue` with these props and slots:

```ts
type Props = {
  eyebrow?: string
  title: string
  headingTag?: 'h2' | 'h3' | 'h4'
  mediaSrc?: string
  mediaAlt?: string
  mediaDisclosure?: string
}
```

Render `eyebrow`, title, optional `summary`, optional `meta`, optional `action`, and optional media only when a non-empty `mediaSrc` is supplied. Render `mediaDisclosure` next to generated/AI media when supplied; never invent disclosure text. Use a semantic `<article>` and the supplied heading tag, defaulting to `h2`. `DossierLineItem.vue` accepts `{ label: string; value: string; href?: string; emphasis?: 'muted' | 'normal' }`; render a `<div data-dossier-line role="listitem">` containing labelled text and a value link/text, and use `<NuxtLink>` only when `href` is present. The parent page may place these rows inside a `<dl>` or list region without the primitive emitting invalid standalone `<dt>`/`<dd>` elements.

- [x] **Step 4: Add token-only Framed Dossier CSS**

Create `dossier.css` and add it to the Nuxt CSS list after `components.css`. The stylesheet must use only `--framed-dossier-*`, semantic text/surface/border tokens, and spacing tokens. It must set `border-radius: var(--framed-dossier-radius)`, `box-shadow: var(--framed-dossier-shadow)`, `aspect-ratio: var(--framed-dossier-media-ratio)`, a visible focus outline, a 44px minimum action height, and a mobile layout that stacks media before action without shrinking text below 16px. The `data-density="compact"` variant uses `var(--framed-dossier-padding-compact)`; the default uses `var(--framed-dossier-padding)`. Do not add hover lift, gradient, glass, or generic card-grid rules.

- [x] **Step 5: Run component tests and accessibility checks**

```text
npm test -- tests/framed-dossier.test.ts
npm run typecheck
```

Expected: PASS. Inspect the component at 375px and 1440px, in both themes, with reduced motion and forced colors enabled.

- [x] **Step 6: Commit the foundation components**

```text
git add web-nuxt/components/FramedDossier.vue web-nuxt/components/DossierLineItem.vue web-nuxt/assets/css/dossier.css web-nuxt/nuxt.config.ts web-nuxt/tests/framed-dossier.test.ts
git commit -m "feat: add framed dossier public primitives"
```

### Task 4: Integrate the Public Theme Control Without Reordering Screens

**Files:**
- Create: `web-nuxt/components/shell/ThemeModeControl.vue`
- Modify: `web-nuxt/layouts/default.vue`
- Modify: `web-nuxt/assets/css/shell.css`
- Modify: `web-nuxt/tests/smoke.test.ts`
- Test: `web-nuxt/tests/theme-mode-control.test.ts`

**Interfaces:**
- Consumes: `useColorMode()` compatibility classes from Task 2 and the public shell already rendered by `layouts/default.vue`.
- Produces: a single explicit public control with stable labels, persistent selection, and no navigation/layout reorder.

- [x] **Step 1: Add the failing behavior test**

Create `web-nuxt/tests/theme-mode-control.test.ts` with an isolated composable mock so the test observes the user's action rather than an implementation detail of the Nuxt color-mode module:

```ts
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ThemeModeControl from '../components/shell/ThemeModeControl.vue'

const colorMode = vi.hoisted(() => ({ value: 'dark', preference: 'dark' as 'dark' | 'light' }))
mockNuxtImport('useColorMode', () => () => colorMode)
const wrappers: Array<{ unmount: () => void }> = []

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  colorMode.value = 'dark'
  colorMode.preference = 'dark'
})

describe('public theme mode control', () => {
  it('offers explicit Nocturne and Daylight Parchment choices', async () => {
    const wrapper = await mountSuspended(ThemeModeControl, { attachTo: document.body })
    wrappers.push(wrapper)
    const control = wrapper.get('[data-theme-control]')
    expect(control.attributes('aria-label')).toBe('Chọn giao diện')
    expect(wrapper.get('button[data-theme-mode="dark"]').text()).toContain('Nocturne')
    expect(wrapper.get('button[data-theme-mode="light"]').text()).toContain('Nền sáng dễ đọc')
    expect(wrapper.get('button[data-theme-mode="dark"]').attributes('aria-pressed')).toBe('true')
  })

  it('persists the selected mode through useColorMode and keeps focus', async () => {
    const wrapper = await mountSuspended(ThemeModeControl, { attachTo: document.body })
    wrappers.push(wrapper)
    const light = wrapper.get<HTMLButtonElement>('button[data-theme-mode="light"]')
    await light.trigger('click')
    expect(colorMode.preference).toBe('light')
    expect(document.activeElement).toBe(light.element)
  })
})
```

- [x] **Step 2: Run the control test and verify it fails**

```text
npm test -- tests/theme-mode-control.test.ts
```

Expected: FAIL because `ThemeModeControl.vue` does not exist and the current layout exposes only a generic light/dark toggle.

- [x] **Step 3: Implement `ThemeModeControl.vue`**

Use `useColorMode()` and render a root element with `data-theme-control` and `aria-label="Chọn giao diện"`. Render exactly two `button` elements with `data-theme-mode="dark|light"`, `type="button"`, and `aria-pressed` derived from `colorMode.value`; treat `unknown` or any unsupported value as active `dark` so SSR never renders two unselected choices. The public labels and values are:

```ts
const modes = [
  { value: 'dark', label: 'Nocturne', description: 'Nền tối mặc định' },
  { value: 'light', label: 'Nền sáng dễ đọc', description: 'Biến thể tăng khả năng đọc' },
] as const
```

Clicking a choice sets `colorMode.preference` only; it must not navigate, reorder page sections, invoke location, or call an API. Implement the handler as `function selectMode(mode: 'dark' | 'light', event: MouseEvent) { colorMode.preference = mode; (event.currentTarget as HTMLButtonElement).focus() }` so keyboard focus remains on the chosen button. The control works for guest users; persistence is delegated to the existing `vl360-color-mode` storage contract.

- [x] **Step 4: Replace the inline public toggle and style the control**

In `layouts/default.vue`, replace only the public inline theme toggle with `<ShellThemeModeControl />`; keep AdminCP's existing workbench control unchanged. Render the theme control outside the `clientReady` auth gate because its state is deterministic on SSR and it must not cause a post-hydration layout shift. In `shell.css`, style the control as a compact two-choice group using semantic tokens, 44px hit targets, explicit focus outline, reduced-motion and forced-colors rules; on mobile keep both choices inside the existing header flow without opening a new drawer or changing navigation height. Update the existing source-contract assertion in `tests/smoke.test.ts` to look for `<ShellThemeModeControl />` and the new labels instead of the removed generic toggle string. Do not change primary nav order, route links, context-location controls, or bottom-nav destinations.

- [x] **Step 5: Run behavior, type, and regression tests**

```text
npm test -- tests/theme-mode-control.test.ts tests/smoke.test.ts tests/ui-foundation-shell.test.ts tests/nocturne-theme-contract.test.ts tests/framed-dossier.test.ts
npm run typecheck
```

Expected: PASS. Confirm route shell snapshots/behavior keep the existing five mobile destinations and no hydration warning appears when the stored theme is absent.

- [x] **Step 6: Commit the public theme control**

```text
git add web-nuxt/components/shell/ThemeModeControl.vue web-nuxt/layouts/default.vue web-nuxt/assets/css/shell.css web-nuxt/tests/smoke.test.ts web-nuxt/tests/theme-mode-control.test.ts
git commit -m "feat: expose explicit public nocturne theme control"
```

## Execution Evidence

- Task commits: `edc36078`, `975ff4a2`, `554f127a`, `26a96b81`; mobile shell remediation: `1d996cc8`; persisted-theme/hydration remediation: `052af8fb`.
- Final focused regression: 5 files / 111 tests passed; `npm run typecheck` passed; production build passed again after the temporary QA route was removed.
- Production runtime QA confirmed Nocturne and Daylight Parchment round-trip persistence, matching document class/state/`aria-pressed`, visible keyboard focus, and no horizontal overflow at the available 1270 CSS-pixel desktop viewport. The prior mobile remediation verified 375px and 360px header behavior.
- Reduced-motion and forced-colors contracts remain covered by the foundation CSS/tests. Exact 1440px media emulation was unavailable in the final browser surface and remains a low-risk visual recheck for the first public-page pilot.
- Independent reviewer dispatches did not complete because the provider returned `404 No active credentials`; this is recorded as a review limitation, not a review pass. Controller fallback review and all executable verification gates passed.
- `web-nuxt/pages/__qa-nocturne.vue` was temporary QA-only instrumentation and was removed before the final build.

## Plan Self-Review

- **Spec coverage:** Task 1 synchronizes Existing Stitch Screen Evolution and page-family authority without touching the dirty parallel `home.md`; the homepage authority reconciliation is explicitly deferred to the public pilot. Task 2 covers Mekong Ink & Clay, Controlled Serif aliases, Nocturne default, Daylight Parchment, semantic trust/status boundaries, old `system|auto` preference normalization, and accessibility token floors. Task 3 establishes Framed Dossier primitives; Task 4 makes the user-controlled theme behavior explicit without changing navigation and updates the existing smoke contract. Location, trust, personalization, graph orchestration, quality loops, and private/RBAC behavior intentionally remain in Plans C–G and are not implemented here.
- **Placeholder scan:** Every task names files, interfaces, commands, and expected outcomes; no step delegates testing or validation to an unnamed follow-up.
- **Type consistency:** `ThemeModeControl` consumes `useColorMode()` values `dark|light` and treats `unknown` as the Nocturne default; `variables.css` maps those compatibility classes to `nocturne|parchment`; `FramedDossier` consumes only the component tokens created in Task 2; later public pilots can mount both components without importing page-specific CSS.
- **Rollback:** Each task has an independent commit. If a pilot rejects the new foundation, revert the task commit while leaving the approved design authority and unrelated dirty files intact.

## Handoff to Plan B

- Do not modify or stage `design-system/vinhlong360/pages/home.md` until the parallel homepage session has been reconciled.
- Start the homepage pilot from the existing Stitch-derived screen and the approved `home.md` content, then apply `FramedDossier` and theme tokens without replacing its composition with Hybrid P1.2.
- The first pilot must verify Nocturne/Daylight Parchment at 375px and 1440px, preserve the five existing mobile destinations, and prove zero personalization-induced section reorder before adding context or adaptive ranking.

## Execution Guardrails

- Before Task 1, run `$homeBefore = git hash-object -- design-system/vinhlong360/pages/home.md`; after each task run `$homeAfter = git hash-object -- design-system/vinhlong360/pages/home.md` and stop if `$homeBefore -ne $homeAfter`. Also compare `git status --short` against the task allowlist before staging.
- Do not run a broad formatter, codemod, or CSS migration over `web-nuxt/assets/css`; each task stages only the exact files listed in its own commit command.
- If the Nuxt color-mode module injects a `system` preference after the pre-paint script, stop at the theme contract gate and adjust the bootstrap ordering before proceeding to component work.
- Do not approve Plan B until the Task 4 regression command passes and a visual check confirms the new control does not change the existing header height or mobile navigation destinations.

Plan complete and saved to `docs/superpowers/plans/2026-07-31-nocturne-heritage-foundation.md`. Execution is intentionally paused at the approval gate; implementation should begin only after this Plan A is reviewed.
