import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(import.meta.dirname, '../..')

function readCssBlock(source: string, marker: string, fromIndex = 0) {
  const start = source.indexOf(marker, fromIndex)
  if (start < 0) throw new Error(`Missing CSS block: ${marker}`)
  const open = source.indexOf('{', start)
  if (open < 0) throw new Error(`Missing opening brace: ${marker}`)

  let depth = 0
  for (let index = open; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1
    if (source[index] === '}') depth -= 1
    if (depth === 0) return source.slice(open + 1, index)
  }

  throw new Error(`Missing closing brace: ${marker}`)
}

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
    const adaptiveStart = variables.indexOf('ADAPTIVE NOCTURNE')
    const adaptiveRoot = readCssBlock(variables, ':root {', adaptiveStart)
    const light = readCssBlock(variables, '\n.light {', adaptiveStart)
    const dark = readCssBlock(variables, '\n.dark {', adaptiveStart)
    const finalOklch = variables.lastIndexOf('@supports (color: oklch(0% 0 0))')
    const darkOklch = readCssBlock(variables, '\n  .dark {', finalOklch)

    expect(adaptiveRoot).toMatch(/--theme-public-default:\s*nocturne/)
    expect(adaptiveRoot).toContain('--font-interface-heading')
    expect(adaptiveRoot).toContain('--font-body')
    expect(adaptiveRoot).toContain('--font-editorial-display')
    expect(adaptiveRoot).toContain('--framed-dossier-border')
    expect(adaptiveRoot).toContain('color-scheme: dark')
    expect(light).toMatch(/--theme-public-default:\s*parchment/)
    expect(light).toContain('color-scheme: light')
    expect(light).toMatch(/--color-source-verified:\s*var\(--orchard-600\)/)
    expect(light).toMatch(/--color-source-community:\s*var\(--mekong-muted\)/)
    expect(light).toMatch(/--color-focus:\s*var\(--river-600\)/)
    expect(dark).toMatch(/--color-source-verified:\s*var\(--night-leaf\)/)
    expect(dark).toMatch(/--color-source-community:\s*var\(--night-muted\)/)
    expect(dark).toMatch(/--color-focus:\s*var\(--night-amber\)/)
    expect(darkOklch).toMatch(/--color-focus:\s*var\(--night-amber\)/)
  })
})
