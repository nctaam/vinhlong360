import { readFile } from 'node:fs/promises'
import { spawnSync } from 'node:child_process'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import * as legalContent from '../utils/legalContent'
import { ABOUT_PAGE, mergeAboutDoc, mergeLegalDoc } from '../utils/legalContent'
import { countLegacyPrimaryUsages, scanSourceTokenDebt, scanTokenDebt, validateProductionRegistry } from '../scripts/check-tri-region-color-debt.mjs'

const root = resolve(import.meta.dirname, '../..')

describe('design-system and legal disclosure authority', () => {
  it('rejects raw semantic colors, unregistered z-index and missing policy history', async () => {
    const debt = scanTokenDebt()
    expect(debt).toMatchObject({ unregisteredSemanticColors: 0, rawZIndexOutsideAllowlist: 0 })

    expect(legalContent.privacy.policyVersion).toBeTruthy()
    expect(legalContent.privacy.updatedDate).toBeTruthy()
    expect(legalContent.privacy.owner).toBeTruthy()
    expect(legalContent.privacy.contact).toBeTruthy()
    expect(legalContent.privacy.changeHistory.length).toBeGreaterThan(0)
    expect(legalContent.privacy.cookieInventory.every(cookie => cookie.purpose && cookie.sameSite && cookie.secure && cookie.retention && cookie.consentControl)).toBe(true)
  })

  it('inventories issued cookies and accepted legacy aliases with their security attributes', async () => {
    const cookies = legalContent.privacy.cookieInventory
    expect(cookies.map(cookie => cookie.name)).toEqual([
      'vl360_token',
      'token',
      'session_token',
      'vl360_trusted',
      'vl360_chat_owner',
      'vl360_case_access',
      'vl360_case_csrf',
    ])
    expect(cookies.find(cookie => cookie.name === 'vl360_session')).toBeUndefined()
    expect(cookies.find(cookie => cookie.name === 'vl360_preferences')).toBeUndefined()

    const session = cookies.find(cookie => cookie.name === 'vl360_token')!
    expect(session).toMatchObject({ sameSite: 'Lax', secure: 'production-only', httpOnly: true })
    const trusted = cookies.find(cookie => cookie.name === 'vl360_trusted')!
    expect(trusted).toMatchObject({ expiry: '90 ngày', sameSite: 'Lax', secure: 'production-only', httpOnly: true })
    const chat = cookies.find(cookie => cookie.name === 'vl360_chat_owner')!
    expect(chat).toMatchObject({ expiry: '365 ngày', sameSite: 'Lax', secure: 'production-only', httpOnly: true })
    const access = cookies.find(cookie => cookie.name === 'vl360_case_access')!
    expect(access).toMatchObject({ expiry: '15 phút', sameSite: 'Lax', secure: 'production-only', httpOnly: true })
    const csrf = cookies.find(cookie => cookie.name === 'vl360_case_csrf')!
    expect(csrf).toMatchObject({ expiry: '15 phút', sameSite: 'Lax', secure: 'production-only', httpOnly: false })

    const [identitySource, chatSource, caseSource, caseSecuritySource] = await Promise.all([
      readFile(resolve(root, 'agent/identity/api.py'), 'utf8'),
      readFile(resolve(root, 'agent/chat_identity.py'), 'utf8'),
      readFile(resolve(root, 'agent/cases/public_api.py'), 'utf8'),
      readFile(resolve(root, 'agent/cases/security.py'), 'utf8'),
    ])
    expect(identitySource).toContain('SESSION_COOKIE_NAME = "vl360_token"')
    expect(identitySource).toContain('TRUSTED_DEVICE_COOKIE_NAME = "vl360_trusted"')
    expect(chatSource).toContain('CHAT_OWNER_COOKIE = "vl360_chat_owner"')
    expect(caseSource).toContain('ACCESS_COOKIE = "vl360_case_access"')
    expect(caseSource).toContain('CSRF_COOKIE = "vl360_case_csrf"')
    expect(caseSecuritySource).toContain('"samesite": "lax"')
  })

  it('derives scanner layers from the registry and catches non-hex semantic values', async () => {
    const registry = JSON.parse(await readFile(resolve(root, 'config/ui-token-registry.json'), 'utf8'))
    expect(scanSourceTokenDebt('x { z-index: 9999; }', 'components/fixture.vue', registry).rawZIndexOutsideAllowlist).toBe(1)
    expect(scanSourceTokenDebt(':root { --color-brand: hsl(10 20% 30%); --color-accent: oklch(60% .2 20); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(2)
    expect(scanSourceTokenDebt('.fixture { color: oklch(60% .2 20); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(1)
    expect(scanSourceTokenDebt(':root { --brand-primitive: #123456; --color-brand: var(--brand-primitive); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(0)
  })

  it('uses the 32px dense visual token inside 44px keyboard targets', async () => {
    const layout = await readFile(resolve(root, 'web-nuxt/layouts/admin.vue'), 'utf8')
    expect(layout).toContain('var(--admin-control-visual-height)')
    expect(layout).toContain('var(--admin-control-hit-area)')
    expect(layout).toMatch(/\.dense-workbench \.admin-actions button[\s\S]*?line-height:\s*var\(--admin-control-visual-height\)/)
    expect(layout).toMatch(/\.dense-workbench \.admin-pagination button[\s\S]*?line-height:\s*var\(--admin-control-visual-height\)/)
    expect(layout).toMatch(/\.dense-workbench \.admin-refresh[\s\S]*?line-height:\s*var\(--admin-control-visual-height\)/)
    expect(layout).toMatch(/\.dense-workbench \.admin-select-inline[\s\S]*?line-height:\s*var\(--admin-control-visual-height\)/)
  })

  it('keeps public legal masthead dates aligned with metadata', () => {
    expect(legalContent.LEGAL_PRIVACY.updated_date).toBe(legalContent.LEGAL_PRIVACY.updatedDate)
    expect(legalContent.LEGAL_TERMS.updated_date).toBe(legalContent.LEGAL_TERMS.updatedDate)
    expect(legalContent.LEGAL_PRIVACY.updated_date).toBe('02/09/2026')
    expect(legalContent.LEGAL_TERMS.updated_date).toBe('02/09/2026')
  })

  it('keeps the canonical semantic prefix, typed aliases, state consumers and layer order machine-readable', async () => {
    const registry = JSON.parse(await readFile(resolve(root, 'config/ui-token-registry.json'), 'utf8'))
    expect(registry.canonical_semantic_prefix).toBe('--color-')
    expect(registry.admin_density).toBe('dense-workbench')
    expect(registry.compatibility_aliases.every((alias: Record<string, unknown>) => alias.owner && alias.expiry && Array.isArray(alias.allowed_files))).toBe(true)
    expect(registry.state_tokens).toEqual(expect.objectContaining({ hover: expect.any(String), focus_visible: expect.any(String), pressed: expect.any(String), disabled: expect.any(String), loading: expect.any(String), error: expect.any(String) }))
    expect(registry.z_layers).toEqual(expect.objectContaining({ nav: expect.any(Number), command_palette: expect.any(Number), drawer: expect.any(Number), modal: expect.any(Number), lightbox: expect.any(Number), toast: expect.any(Number) }))
    expect(registry.z_layers).toEqual(expect.objectContaining({ modal_high: expect.any(Number) }))
    expect(registry.z_layers.modal_high).toBeGreaterThan(registry.z_layers.modal)
    const variables = await readFile(resolve(root, 'web-nuxt/assets/css/variables.css'), 'utf8')
    for (const match of variables.matchAll(/--z-([\w-]+)\s*:\s*(-?\d+)/g)) {
      const layerName = (match[1] || '').replaceAll('-', '_')
      expect(registry.z_layers?.[layerName]).toBe(Number(match[2]))
    }
    expect(registry.exemptions).toEqual(expect.arrayContaining(['semantic-ui', 'decorative-scene', 'media-scrim', 'SVG/data-uri', 'forced-colors', 'fallback']))
    for (const alias of registry.compatibility_aliases) {
      expect(alias.owner).toMatch(/\S/)
      expect(alias.expiry).toMatch(/^20\d\d-\d\d-\d\d$/)
      expect(alias.allowed_files.length).toBeGreaterThan(0)
      expect(alias.allowed_files.every((path: string) => path.startsWith('web-nuxt/'))).toBe(true)
    }
  })

  it('does not turn unapproved legal claims into guarantees', () => {
    const claims = legalContent.decisionRequired
    expect(claims).toEqual(expect.objectContaining({
      sla_24h_48h: expect.any(String),
      residency: expect.any(String),
      processors_subprocessors: expect.any(String),
      public_indexing: expect.any(String),
    }))
    expect(JSON.stringify(legalContent.LEGAL_TERMS)).toMatch(/decisionRequired|chưa được phê duyệt|đang chờ/i)
  })

  it('publishes legal metadata and the cookie inventory on both legal pages', async () => {
    const [privacy, terms] = await Promise.all([
      readFile(resolve(root, 'web-nuxt/pages/chinh-sach-bao-mat.vue'), 'utf8'),
      readFile(resolve(root, 'web-nuxt/pages/dieu-khoan-su-dung.vue'), 'utf8'),
    ])
    for (const page of [privacy, terms]) {
      expect(page).toContain('policyVersion')
      expect(page).toContain('cookieInventory')
      expect(page).toContain('changeHistory')
      expect(page).toContain('runtimeRole')
      expect(page).toContain('owner')
      expect(page).toContain('consentControl')
      expect(page).toContain('deletion')
      expect(page).toContain('expiryDecision')
      expect(page).toContain('Secure production')
    }
  })

  it('fails the CLI gate when computed token or z-index debt is present', async () => {
    const scanner = await readFile(resolve(root, 'web-nuxt/scripts/check-tri-region-color-debt.mjs'), 'utf8')
    expect(scanner).toContain('scanTokenDebt()')
    expect(scanner).toMatch(/rawZIndexOutsideAllowlist\s*>\s*0|unregisteredSemanticColors\s*>\s*0/)
    expect(scanner).toContain('tri-region color debt: FAIL')
    expect(scanner).toContain('includeDirect: true')
    const registry = JSON.parse(await readFile(resolve(root, 'config/ui-token-registry.json'), 'utf8'))
    expect(scanSourceTokenDebt('a { color: rgb(10, 20, 30); }', 'components/fixture.vue', registry, { includeDirect: true }).unregisteredSemanticColors).toBe(1)
    expect(scanTokenDebt()).toEqual({ unregisteredSemanticColors: 0, rawZIndexOutsideAllowlist: 0 })
  })

  it('classifies accepted legacy auth cookie aliases with deprecation and clear attributes', async () => {
    const cookies = legalContent.privacy.cookieInventory
    for (const name of ['token', 'session_token']) {
      const cookie = cookies.find(entry => entry.name === name)
      expect(cookie).toMatchObject({
        runtimeRole: 'accepted-legacy',
        owner: expect.any(String),
        purpose: expect.any(String),
        expiry: expect.any(String),
        sameSite: 'Lax',
        secure: 'production-only',
        httpOnly: true,
        retention: expect.any(String),
        deprecation: expect.any(String),
        expiryDecision: expect.any(String),
        deletion: { path: '/', sameSite: 'Lax', secure: 'production-only', httpOnly: true },
      })
    }
    const identitySource = await readFile(resolve(root, 'agent/identity/api.py'), 'utf8')
    expect(identitySource).toContain('for cookie_name in ("vl360_token", "token", "session_token")')
    expect(identitySource).toContain('for name in (SESSION_COOKIE_NAME, "token", "session_token")')
  })

  it('detects modern and shorthand raw colors plus unsafe computed z-index values', async () => {
    const registry = JSON.parse(await readFile(resolve(root, 'config/ui-token-registry.json'), 'utf8'))
    const probes = [
      'a { color: color(display-p3 1 0 0); }',
      'a { color: hwb(20 10% 10%); }',
      'a { color: rgb(10% 20% 30% / .5); }',
      'a { color: rgba(10 20 30 / .5); }',
      'a { border: 1px solid rgb(10 20 30); }',
      'a { outline: 2px solid hwb(20 10% 10%); }',
      'a { box-shadow: 0 0 2px color(display-p3 1 0 0); }',
      'a { caret-color: rgba(10 20 30 / .5); }',
    ]
    for (const source of probes) {
      expect(scanSourceTokenDebt(source, 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(1)
    }
    expect(scanSourceTokenDebt('a { color: var(--color-brand); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(0)
    expect(scanSourceTokenDebt('a { color: var(--evil, #fff); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(1)
    expect(scanSourceTokenDebt('a { z-index: calc(9999); }', 'components/fixture.vue', registry).rawZIndexOutsideAllowlist).toBe(1)
    expect(scanSourceTokenDebt('a { z-index: var(--z-evil, 9999); }', 'components/fixture.vue', registry).rawZIndexOutsideAllowlist).toBe(1)
    expect(scanSourceTokenDebt('a { z-index: var(--z-evil); }', 'components/fixture.vue', registry).rawZIndexOutsideAllowlist).toBe(1)
    expect(scanSourceTokenDebt('a { color: rgb(10, 20, 30); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(1)
    expect(scanSourceTokenDebt('a { color: rgba(10, 20, 30, .5); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(1)
  })

  it('rejects undeclared semantic variables but permits locally declared component tokens', async () => {
    const registry = JSON.parse(await readFile(resolve(root, 'config/ui-token-registry.json'), 'utf8'))
    expect(scanSourceTokenDebt('a { color: var(--evil); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(1)
    expect(scanSourceTokenDebt('a { color: var(--color-not-registered); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(1)
    expect(scanSourceTokenDebt(':root { --color-brand: var(--evil); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(1)
    expect(scanSourceTokenDebt('.component { --component-color: #123456; color: var(--component-color); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(0)
    expect(scanSourceTokenDebt(':root { --evil: #123456; } a { color: var(--evil); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(1)
  })

  it('uses canonical tokens for every previously unknown semantic variable', async () => {
    const [darkOverrides, events, calendar] = await Promise.all([
      readFile(resolve(root, 'web-nuxt/assets/css/dark-overrides.css'), 'utf8'),
      readFile(resolve(root, 'web-nuxt/assets/css/events.css'), 'utf8'),
      readFile(resolve(root, 'web-nuxt/pages/lich-van-nien.vue'), 'utf8'),
    ])
    expect(darkOverrides).not.toMatch(/--secondary-fg-strong|--error-light/)
    expect(events).not.toContain('--card-hover')
    expect(calendar).not.toContain('--card-hover')
    expect(darkOverrides).toContain('var(--secondary-fg)')
    expect(darkOverrides).toContain('var(--error)')
    expect(events).toContain('var(--state-hover)')
    expect(calendar).toContain('var(--state-hover)')
  })

  it('keeps scanner imports side-effect free while preserving direct CLI execution', () => {
    const result = spawnSync(process.execPath, ['--input-type=module', '-e', "import('./scripts/check-tri-region-color-debt.mjs').then(() => process.stdout.write('loaded'))"], {
      cwd: resolve(root, 'web-nuxt'),
      encoding: 'utf8',
    })
    expect(result.status).toBe(0)
    expect(result.stdout).toBe('loaded')
    expect(result.stderr).toBe('')
  })

  it('fails closed for malformed sections and Unicode-obfuscated legal claims', () => {
    const inherited = Object.create({ heading: 'Cam kết', body: 'Đã xác minh.' })
    const claimWithZeroWidth = 'Cam\u200B kết xử lý trong vòng 24 giờ.'
    const def = legalContent.LEGAL_TERMS
    expect(mergeLegalDoc({ intro: claimWithZeroWidth }, def).intro).toBe(def.intro)
    expect(mergeLegalDoc({ sections: [inherited] }, def).sections).toEqual(def.sections)
    expect(mergeLegalDoc({ sections: [{ heading: '', body: 'ok' }] }, def).sections).toEqual(def.sections)
    expect(mergeLegalDoc({ sections: [{ heading: 'ok', body: 42 }] }, def).sections).toEqual(def.sections)
    expect(mergeLegalDoc({ sections: [{ heading: 'ok', body: 'safe', extra: 'injected' }] }, def).sections).toEqual(def.sections)
  })

  it('allows only body edits under the exact canonical section heading contract', () => {
    const def = legalContent.LEGAL_TERMS
    const editable = def.sections.map(section => ({ ...section, body: `${section.body}\n\nBổ sung biên tập.` }))
    expect(mergeLegalDoc({ sections: editable }, def).sections).toEqual(editable)
    expect(mergeLegalDoc({ sections: editable.slice(1) }, def).sections).toEqual(def.sections)
    expect(mergeLegalDoc({ sections: [...editable, { heading: '7. Phụ lục', body: 'extra' }] }, def).sections).toEqual(def.sections)
    const reordered = [...editable].reverse()
    expect(mergeLegalDoc({ sections: reordered }, def).sections).toEqual(def.sections)
    const renamed = editable.map((section, index) => index === 0 ? { ...section, heading: '1. Tài khoản mới' } : section)
    expect(mergeLegalDoc({ sections: renamed }, def).sections).toEqual(def.sections)
  })

  it('rejects direct hex and named semantic colors while preserving typed decorative exemptions', async () => {
    const registry = JSON.parse(await readFile(resolve(root, 'config/ui-token-registry.json'), 'utf8'))
    for (const source of [
      'a { color: #fff; }',
      'a { background-color: #fff; }',
      'a { background: #fff; }',
      'a { color: red; }',
    ]) {
      expect(scanSourceTokenDebt(source, 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(1)
    }
    expect(scanSourceTokenDebt('a { background: linear-gradient(var(--color-brand), var(--color-canvas)); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(0)
    expect(scanSourceTokenDebt('a { background: #fff; color: red; border-color: #fff; }', 'assets/css/cards.css', registry).unregisteredSemanticColors).toBe(3)
    expect(scanSourceTokenDebt('a { background: linear-gradient(var(--color-brand), var(--color-canvas)); box-shadow: 0 0 2px rgba(255,255,255,.2); }', 'assets/css/cards.css', registry).unregisteredSemanticColors).toBe(0)
  })

  it('rejects important, shorthand, and named fallback semantic colors across all color properties', async () => {
    const registry = JSON.parse(await readFile(resolve(root, 'config/ui-token-registry.json'), 'utf8'))
    const probes = [
      'a { color: red !important; }',
      'a { background: white !important; }',
      'a { background-image: linear-gradient(red, var(--color-brand)) !important; }',
      'a { border-color: #fff !important; }',
      'a { border-top-color: red !important; }',
      'a { border-inline-color: var(--evil, red) !important; }',
      'a { text-decoration-color: red !important; }',
      'a { accent-color: red !important; }',
      'a { color: var(--evil,red)!important; }',
    ]
    for (const source of probes) {
      expect(scanSourceTokenDebt(source, 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(1)
    }
    expect(scanSourceTokenDebt(':root { --color-custom: red !important; }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(1)
    expect(scanSourceTokenDebt('a { background-image: linear-gradient(var(--color-brand), var(--color-canvas)) !important; }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(0)
    expect(scanSourceTokenDebt('a { background-image: url("data:image/svg+xml,<svg stroke=white/>"); }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(0)
  })

  it('rejects every unregistered z-index variable even with registered numeric fallbacks or calc terms', async () => {
    const registry = JSON.parse(await readFile(resolve(root, 'config/ui-token-registry.json'), 'utf8'))
    expect(scanSourceTokenDebt('a { z-index: var(--z-evil, 500); }', 'components/fixture.vue', registry).rawZIndexOutsideAllowlist).toBe(1)
    expect(scanSourceTokenDebt('a { z-index: calc(var(--z-evil) + 500); }', 'components/fixture.vue', registry).rawZIndexOutsideAllowlist).toBe(1)
    expect(scanSourceTokenDebt('a { z-index: var(--z-modal, 500); }', 'components/fixture.vue', registry).rawZIndexOutsideAllowlist).toBe(1)
    expect(scanSourceTokenDebt('a { z-index: var(--evil, 500); }', 'components/fixture.vue', registry).rawZIndexOutsideAllowlist).toBe(1)
    expect(scanSourceTokenDebt('a { z-index: calc(var(--evil) + 500); }', 'components/fixture.vue', registry).rawZIndexOutsideAllowlist).toBe(1)
  })

  it('does not let typed scene exemptions hide functional color regressions or unterminated tokens', async () => {
    const registry = JSON.parse(await readFile(resolve(root, 'config/ui-token-registry.json'), 'utf8'))
    for (const source of [
      'a { color: hsl(10 20% 30%); }',
      'a { background: rgb(10 20 30); }',
      'a { color: var(--evil, red); }',
    ]) {
      expect(scanSourceTokenDebt(source, 'assets/css/cards.css', registry).unregisteredSemanticColors).toBe(1)
    }
    for (const source of [
      'a { color: var(--evil); }',
      'a { background: var(--evil); }',
      'a { border-color: var(--evil); }',
    ]) {
      expect(scanSourceTokenDebt(source, 'assets/css/cards.css', registry).unregisteredSemanticColors).toBe(1)
    }
    expect(scanSourceTokenDebt(':root { --color-custom: hsl(10 20% 30%) }', 'components/fixture.vue', registry).unregisteredSemanticColors).toBe(1)
  })

  it('only accepts exact registered z-index values and path-scoped exemptions', async () => {
    const registry = JSON.parse(await readFile(resolve(root, 'config/ui-token-registry.json'), 'utf8'))
    expect(scanSourceTokenDebt('a { z-index: calc(var(--z-modal) + 1); }', 'components/fixture.vue', registry).rawZIndexOutsideAllowlist).toBe(1)
    expect(scanSourceTokenDebt('a { z-index: calc(var(--z-overlay)); }', 'components/fixture.vue', registry).rawZIndexOutsideAllowlist).toBe(1)
    expect(scanSourceTokenDebt('a { z-index: 30; }', 'components/fixture.vue', registry).rawZIndexOutsideAllowlist).toBe(0)
    expect(scanSourceTokenDebt('a { z-index: 30; }', 'outside/fixture.vue', registry).rawZIndexOutsideAllowlist).toBe(1)
  })

  it('fails closed for malformed, expired, or out-of-scope compatibility aliases', () => {
    const source = ':root { --catalog-legacy-primary: var(--primary); }'
    const base = {
      alias: '--catalog-legacy-primary',
      canonical: '--primary',
      owner: 'design-platform',
      expiry: '2027-03-31',
      allowed_files: ['web-nuxt/assets/css/tri-region-color.css'],
    }
    expect(countLegacyPrimaryUsages(source, 'assets/css/tri-region-color.css', { compatibility_aliases: [base] })).toBe(0)
    expect(countLegacyPrimaryUsages(source, 'assets/css/catalog.css', { compatibility_aliases: [base] })).toBe(1)
    expect(countLegacyPrimaryUsages(source, 'assets/css/tri-region-color.css', { compatibility_aliases: [{ ...base, owner: '' }] })).toBe(1)
    expect(countLegacyPrimaryUsages(source, 'assets/css/tri-region-color.css', { compatibility_aliases: [{ ...base, expiry: '2020-01-01' }] })).toBe(1)
    expect(countLegacyPrimaryUsages(source, 'assets/css/tri-region-color.css', { compatibility_aliases: [{ ...base, allowed_files: ['web-nuxt'] }] })).toBe(1)
    expect(validateProductionRegistry({ z_layers: {}, compatibility_aliases: [{ ...base, expiry: '2020-01-01' }] })).toContain('registry compatibility_aliases[0] is malformed')
    expect(validateProductionRegistry({ z_layers: {}, compatibility_aliases: [{ ...base, allowed_files: ['web-nuxt'] }], semantic_value_exemptions: [], z_index_exemptions: [] })).toContain('registry compatibility_aliases[0] is malformed')
    expect(validateProductionRegistry(null)).toEqual(['registry must be a plain object'])
  })

  it('rejects claim-bearing legal metadata fields from CMS overrides', () => {
    const merged = mergeLegalDoc({
      title: 'Guaranteed privacy within 24 hours',
      seo_title: 'Đã xác minh và được chứng nhận',
      seo_description: 'We guarantee compliance within 48 hours.',
    }, legalContent.LEGAL_PRIVACY)
    expect(merged.title).toBe(legalContent.LEGAL_PRIVACY.title)
    expect(merged.seo_title).toBe(legalContent.LEGAL_PRIVACY.seo_title)
    expect(merged.seo_description).toBe(legalContent.LEGAL_PRIVACY.seo_description)
  })

  it('requires a complete registry authority and ordered z-layer contract', async () => {
    const registry = JSON.parse(await readFile(resolve(root, 'config/ui-token-registry.json'), 'utf8'))
    expect(validateProductionRegistry({ ...registry, canonical_semantic_prefix: undefined })).toEqual(expect.arrayContaining([expect.stringMatching(/canonical_semantic_prefix/i)]))
    expect(validateProductionRegistry({ ...registry, z_layers: { ...registry.z_layers, modal: undefined } })).toEqual(expect.arrayContaining([expect.stringMatching(/z_layers/i)]))
    expect(validateProductionRegistry({ ...registry, z_layer_order: ['toast'] })).toEqual(expect.arrayContaining([expect.stringMatching(/z_layer_order/i)]))
  })

  it('rejects registry authority/path, alias graph, and exemption metadata bypasses', async () => {
    const registry = JSON.parse(await readFile(resolve(root, 'config/ui-token-registry.json'), 'utf8'))
    expect(validateProductionRegistry({ ...registry, semantic_authority: { ...registry.semantic_authority, source: 'outside.json' } })).toEqual(expect.arrayContaining([expect.stringMatching(/semantic_authority/i)]))
    expect(validateProductionRegistry({ ...registry, semantic_authority: { ...registry.semantic_authority, primitive_suffix: 'primitive' } })).toEqual(expect.arrayContaining([expect.stringMatching(/semantic_authority/i)]))
    const duplicate = { ...registry, compatibility_aliases: [...registry.compatibility_aliases, registry.compatibility_aliases[0]] }
    expect(validateProductionRegistry(duplicate)).toEqual(expect.arrayContaining([expect.stringMatching(/duplicates alias/i)]))
    const cycle = { ...registry, compatibility_aliases: [
      ...registry.compatibility_aliases,
      { ...registry.compatibility_aliases[0], alias: '--cycle-a', canonical: '--cycle-b' },
      { ...registry.compatibility_aliases[0], alias: '--cycle-b', canonical: '--cycle-a' },
    ] }
    expect(validateProductionRegistry(cycle)).toEqual(expect.arrayContaining([expect.stringMatching(/cycle/i)]))
    const missingTarget = { ...registry, compatibility_aliases: [{ ...registry.compatibility_aliases[0], canonical: '--does-not-exist' }] }
    expect(validateProductionRegistry(missingTarget)).toEqual(expect.arrayContaining([expect.stringMatching(/canonical target/i)]))
    const malformedExemption = { ...registry, semantic_value_exemptions: [{ path: 'assets/css/cards.css', type: 'unbounded', reason: '' }] }
    expect(validateProductionRegistry(malformedExemption)).toEqual(expect.arrayContaining([expect.stringMatching(/semantic_value_exemptions/i)]))
  })

  it('rejects claim-bearing legal CMS intro and sections while preserving canonical copy', () => {
    const merged = mergeLegalDoc({
      intro: 'Chúng tôi cam kết xử lý mọi yêu cầu trong vòng 24 giờ.',
      sections: [{ heading: 'Cam kết', body: 'Đã xác minh và bảo đảm tuân thủ hoàn toàn.' }],
    }, legalContent.LEGAL_TERMS)
    expect(merged.intro).toBe(legalContent.LEGAL_TERMS.intro)
    expect(merged.sections).toEqual(legalContent.LEGAL_TERMS.sections)
    expect(mergeLegalDoc({ intro: 'Yêu cầu được xử lý trong vòng 24 giờ.' }, legalContent.LEGAL_TERMS).intro).toBe(legalContent.LEGAL_TERMS.intro)
  })

  it('preserves the About page canonical date when CMS copy overrides are merged', () => {
    expect(ABOUT_PAGE.updated_date).toBe('20/06/2026')
    expect(ABOUT_PAGE.updatedDate).toBe('20/06/2026')
    const merged = mergeAboutDoc({ title: 'Edited', updatedDate: '01/01/2000', updated_date: '02/02/2001' }, ABOUT_PAGE)
    expect(merged.updated_date).toBe('20/06/2026')
    expect(merged.updatedDate).toBe('20/06/2026')
  })

  it('keeps canonical legal inventory and history when CMS overrides inject metadata', () => {
    const merged = mergeLegalDoc({
      title: 'Edited title',
      updatedDate: '01/01/2000',
      updated_date: '02/02/2001',
      policyVersion: 'injected',
      owner: 'injected owner',
      contact: 'injected contact',
      cookieInventory: [{ name: 'evil' }],
      changeHistory: [{ version: 'evil', date: '01/01/2000', summary: 'evil' }],
    }, legalContent.LEGAL_PRIVACY)
    expect(merged.title).toBe('Edited title')
    expect(merged.updatedDate).toBe(legalContent.LEGAL_PRIVACY.updatedDate)
    expect(merged.updated_date).toBe(legalContent.LEGAL_PRIVACY.updated_date)
    expect(merged.policyVersion).toBe(legalContent.LEGAL_PRIVACY.policyVersion)
    expect(merged.owner).toBe(legalContent.LEGAL_PRIVACY.owner)
    expect(merged.contact).toBe(legalContent.LEGAL_PRIVACY.contact)
    expect(merged.cookieInventory).toEqual(legalContent.LEGAL_PRIVACY.cookieInventory)
    expect(merged.changeHistory).toEqual(legalContent.LEGAL_PRIVACY.changeHistory)
  })

  it('documents deletion attributes for case cookies and matches creation security flags', async () => {
    const cookies = legalContent.privacy.cookieInventory
    expect(cookies.find(entry => entry.name === 'vl360_case_access')?.deletion).toEqual({ path: '/api/cases', sameSite: 'Lax', secure: 'production-only', httpOnly: true })
    expect(cookies.find(entry => entry.name === 'vl360_case_csrf')?.deletion).toEqual({ path: '/api/cases', sameSite: 'Lax', secure: 'production-only', httpOnly: false })
    const source = await readFile(resolve(root, 'agent/cases/public_api.py'), 'utf8')
    expect(source).toContain('secure=production')
    expect(source).toContain('httponly=httponly')
  })
})
