import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(import.meta.dirname, '../..')

describe('Adaptive Nocturne theme contract', () => {
  it('uses an explicit Nocturne default and normalizes the old automatic preference', async () => {
    const nuxtConfig = await readFile(resolve(root, 'web-nuxt/nuxt.config.ts'), 'utf8')
    expect(nuxtConfig).toContain("preference: 'dark'")
    expect(nuxtConfig).toContain("fallback: 'dark'")
    expect(nuxtConfig).not.toContain("preference: 'system'")
    expect(nuxtConfig).toContain("var k='vl360-color-mode'")
    expect(nuxtConfig).toContain('localStorage.getItem(k)')
    expect(nuxtConfig).toContain("localStorage.setItem(k,'dark')")
    expect(nuxtConfig.indexOf("var k='vl360-color-mode'")).toBeLessThan(
      nuxtConfig.indexOf("document.documentElement.classList.add('js')"),
    )
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
    expect(variables).toMatch(/\.light\s*\{[\s\S]*--color-source-verified:\s*var\(--orchard-600\)/)
    expect(variables).toMatch(/\.light\s*\{[\s\S]*--color-source-community:\s*var\(--mekong-muted\)/)
    expect(variables).toMatch(/\.light\s*\{[\s\S]*--color-focus:\s*var\(--river-600\)/)
    expect(variables).toMatch(/\.dark\s*\{[\s\S]*--color-source-verified:\s*var\(--night-leaf\)/)
    expect(variables).toMatch(/\.dark\s*\{[\s\S]*--color-source-community:\s*var\(--night-muted\)/)
    expect(variables).toMatch(/\.dark\s*\{[\s\S]*--color-focus:\s*var\(--night-amber\)/)
    expect(variables).toMatch(/@supports \(color: oklch\(0% 0 0\)\)\s*\{\s*\.dark\s*\{[\s\S]*--color-focus:\s*var\(--night-amber\)/)
  })
})
