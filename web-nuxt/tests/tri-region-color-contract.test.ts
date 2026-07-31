import { execFile } from 'node:child_process'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { promisify } from 'node:util'
import { describe, expect, it } from 'vitest'

const root = resolve(import.meta.dirname, '../..')
const execFileAsync = promisify(execFile)

describe('Tri-Region color contract', () => {
  it('maps action, brand, trust, status and material roles without province themes', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/variables.css'), 'utf8')

    expect(css).toMatch(/--color-action:\s*var\(--river-600\)/)
    expect(css).toMatch(/--color-brand:\s*var\(--mangthit-600\)/)
    expect(css).toMatch(/--color-source-official:\s*var\(--river-600\)/)
    expect(css).toMatch(/--color-source-verified:\s*var\(--orchard-600\)/)
    expect(css).toMatch(/--color-source-community:\s*var\(--mekong-muted\)/)
    expect(css).toMatch(/--color-warning:\s*var\(--harvest-700\)/)
    expect(css).toContain('--color-material-clay')
    expect(css).toContain('--color-material-leaf')
    expect(css).toContain('--color-material-river')
    expect(css).toContain('--color-material-amber')
    expect(css).toContain('--color-material-neutral')
    expect(css).not.toContain('--color-material-coir')
    expect(css).not.toContain('--color-material-khmer-ochre')
  })

  it('keeps semantic meaning stable between Nocturne and Parchment', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/variables.css'), 'utf8')

    expect(css).toMatch(/\.light\s*\{[\s\S]*--color-source-verified:\s*var\(--orchard-600\)/)
    expect(css).toMatch(/\.light\s*\{[\s\S]*--color-focus:\s*var\(--river-600\)/)
    expect(css).toMatch(/\.light\s*\{[\s\S]*--color-on-action:\s*var\(--surface-white\)/)
    expect(css).toMatch(/\.dark\s*\{[\s\S]*--color-source-verified:\s*var\(--night-leaf\)/)
    expect(css).toMatch(/\.dark\s*\{[\s\S]*--color-source-community:\s*var\(--night-muted\)/)
    expect(css).toMatch(/\.dark\s*\{[\s\S]*--color-focus:\s*var\(--night-amber\)/)
    expect(css).toMatch(/\.dark\s*\{[\s\S]*--color-on-action:\s*var\(--night-canvas\)/)
  })

  it('scopes compatibility aliases and recipes to tri-region pages only', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/tri-region-color.css'), 'utf8')
    const config = await readFile(resolve(root, 'web-nuxt/nuxt.config.ts'), 'utf8')

    expect(css).toContain('[data-color-system="tri-region-v1"]')
    expect(css).toMatch(/\[data-color-system="tri-region-v1"\][\s\S]*--primary:\s*var\(--color-action\)/)
    expect(css).toContain('[data-page-recipe="homepage"]')
    expect(css).toContain('[data-page-recipe="discovery"]')
    expect(css).toContain('[data-page-recipe="search"]')
    expect(css).toContain('[data-page-recipe="detail"]')
    expect(css).toContain('@media (forced-colors: active)')
    expect(css).toContain('@media (prefers-contrast: more)')
    expect(css).not.toMatch(/#[0-9a-f]{3,8}\b/i)
    expect(config.indexOf("'~/assets/css/tri-region-color.css'")).toBeGreaterThan(
      config.indexOf("'~/assets/css/catalog.css'"),
    )
  })

  it('lets a nested neutral material reset an inherited page accent', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/tri-region-color.css'), 'utf8')

    expect(css).toMatch(
      /\[data-color-system="tri-region-v1"\]\[data-material-accent="neutral"\],[\s\S]*\[data-color-system="tri-region-v1"\] \[data-material-accent="neutral"\]\s*\{[\s\S]*--tri-region-material-accent:\s*var\(--color-material-neutral\)/,
    )
  })

  it('covers canonical root material accents in forced-colors mode', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/tri-region-color.css'), 'utf8')
    const forcedColors = css.slice(css.indexOf('@media (forced-colors: active)'))

    expect(forcedColors).toContain('[data-color-system="tri-region-v1"][data-material-accent]')
    expect(forcedColors).toContain('[data-color-system="tri-region-v1"] [data-material-accent]')
  })

  it('executes control-border contrast checks for sRGB and OKLCH branches', async () => {
    const { stdout } = await execFileAsync(process.execPath, ['scripts/check-tri-region-contrast.mjs'], {
      cwd: resolve(root, 'web-nuxt'),
    })

    for (const name of [
      'control-border-light-srgb',
      'control-border-dark-srgb',
      'control-border-light-oklch',
      'control-border-dark-oklch',
    ]) {
      const match = new RegExp(`^${name}\\s+(\\d+\\.\\d+)\\s+3\\.0$`, 'm').exec(stdout)
      expect(match, `missing executable audit output for ${name}`).not.toBeNull()
      expect(Number(match![1])).toBeGreaterThanOrEqual(3)
    }
  })
})
