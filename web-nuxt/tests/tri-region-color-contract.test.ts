import { execFile } from 'node:child_process'
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { promisify } from 'node:util'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

const root = resolve(import.meta.dirname, '../..')
const execFileAsync = promisify(execFile)
const semanticPairNames = [
  'body-light',
  'muted-light',
  'action-light',
  'on-action-light',
  'brand-light',
  'verified-light',
  'warning-light',
  'error-light',
  'body-dark',
  'action-dark',
  'on-action-dark',
  'brand-dark',
  'verified-dark',
  'warning-dark',
  'error-dark',
]

function readCssBlock(source: string, marker: string) {
  const start = source.indexOf(marker)
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

describe('Tri-Region color contract', () => {
  it('maps action, brand, trust, status and material roles without province themes', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/variables.css'), 'utf8')
    const fallbackRoot = readCssBlock(css, ':root {')

    expect(fallbackRoot).toMatch(/--color-action:\s*var\(--river-600\)/)
    expect(fallbackRoot).toMatch(/--color-brand:\s*var\(--mangthit-600\)/)
    expect(fallbackRoot).toMatch(/--color-source-official:\s*var\(--river-600\)/)
    expect(fallbackRoot).toMatch(/--color-source-verified:\s*var\(--orchard-600\)/)
    expect(fallbackRoot).toMatch(/--color-source-community:\s*var\(--mekong-muted\)/)
    expect(fallbackRoot).toMatch(/--color-warning:\s*var\(--harvest-700\)/)
    expect(fallbackRoot).toMatch(/--color-action-border:\s*color-mix\(in srgb, var\(--color-action\) 70%, transparent\)/)
    expect(fallbackRoot).toContain('--color-material-clay')
    expect(fallbackRoot).toContain('--color-material-leaf')
    expect(fallbackRoot).toContain('--color-material-river')
    expect(fallbackRoot).toContain('--color-material-amber')
    expect(fallbackRoot).toContain('--color-material-neutral')
    expect(css).not.toContain('--color-material-coir')
    expect(css).not.toContain('--color-material-khmer-ochre')
  })

  it('keeps semantic meaning stable between Nocturne and Parchment', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/variables.css'), 'utf8')
    const light = readCssBlock(css, '\n.light {')
    const dark = readCssBlock(css, '\n.dark {')

    expect(light).toMatch(/--color-source-verified:\s*var\(--orchard-600\)/)
    expect(light).toMatch(/--color-focus:\s*var\(--river-600\)/)
    expect(light).toMatch(/--color-on-action:\s*var\(--surface-white\)/)
    expect(dark).toMatch(/--color-source-verified:\s*var\(--night-leaf\)/)
    expect(dark).toMatch(/--color-source-community:\s*var\(--night-muted\)/)
    expect(dark).toMatch(/--color-focus:\s*var\(--night-amber\)/)
    expect(dark).toMatch(/--color-on-action:\s*var\(--night-canvas\)/)
  })

  it('scopes compatibility aliases and recipes to tri-region pages only', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/tri-region-color.css'), 'utf8')
    const config = await readFile(resolve(root, 'web-nuxt/nuxt.config.ts'), 'utf8')
    const scopedRoot = readCssBlock(css, '[data-color-system="tri-region-v1"] {')

    expect(css).toContain('[data-color-system="tri-region-v1"]')
    expect(scopedRoot).toMatch(/--primary:\s*var\(--color-action\)/)
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
    const neutral = readCssBlock(
      css,
      '[data-color-system="tri-region-v1"][data-material-accent="neutral"],',
    )

    expect(css).toContain('[data-color-system="tri-region-v1"] [data-material-accent="neutral"]')
    expect(neutral).toMatch(/--tri-region-material-accent:\s*var\(--color-material-neutral\)/)
  })

  it('covers canonical root material accents in forced-colors mode', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/tri-region-color.css'), 'utf8')
    const forcedColors = readCssBlock(css, '@media (forced-colors: active)')

    expect(forcedColors).toContain('[data-color-system="tri-region-v1"][data-material-accent]')
    expect(forcedColors).toContain('[data-color-system="tri-region-v1"] [data-material-accent]')
  })

  it('renders scoped legacy filled controls with the on-action foreground', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/tri-region-color.css'), 'utf8')
    const stylesheet = document.createElement('style')
    stylesheet.textContent = `
      [data-color-system="tri-region-v1"] { --color-on-action: rgb(7, 18, 16); }
      .btn-primary, .chip.active, .btn-outline:hover { color: rgb(255, 255, 255); }
      ${css}
    `
    document.head.append(stylesheet)

    const RepresentativeControls = defineComponent({
      setup: () => () => h('main', { 'data-color-system': 'tri-region-v1' }, [
        h('button', { class: 'btn btn-primary' }, 'Primary'),
        h('button', { class: 'chip active' }, 'Active chip'),
      ]),
    })
    const wrapper = await mountSuspended(RepresentativeControls, { attachTo: document.body })

    try {
      expect(getComputedStyle(wrapper.get('.btn-primary').element).color).toBe('rgb(7, 18, 16)')
      expect(getComputedStyle(wrapper.get('.chip.active').element).color).toBe('rgb(7, 18, 16)')
    } finally {
      wrapper.unmount()
      stylesheet.remove()
    }
  })

  it('wins real legacy direct-contact and focus cascades inside the scoped wave', async () => {
    const [components, detail, catalog, triRegion] = await Promise.all([
      readFile(resolve(root, 'web-nuxt/assets/css/components.css'), 'utf8'),
      readFile(resolve(root, 'web-nuxt/assets/css/detail-shared.css'), 'utf8'),
      readFile(resolve(root, 'web-nuxt/assets/css/catalog.css'), 'utf8'),
      readFile(resolve(root, 'web-nuxt/assets/css/tri-region-color.css'), 'utf8'),
    ])
    const stylesheet = document.createElement('style')
    stylesheet.textContent = `
      :root {
        --primary: rgb(3, 90, 105);
        --primary-dark: rgb(0, 67, 78);
        --primary-rgb: 3, 90, 105;
        --accent: rgb(232, 163, 61);
        --color-focus: rgb(3, 90, 105);
        --color-on-action: rgb(7, 18, 16);
        --text-on-dark: rgb(255, 255, 255);
      }
      ${components}
      ${detail}
      ${catalog}
      ${triRegion}
    `
    document.head.append(stylesheet)

    const RepresentativeCascade = defineComponent({
      setup: () => () => h('main', { 'data-color-system': 'tri-region-v1' }, [
        h('a', { class: 'hl', href: '#contact' }, 'Gọi trực tiếp'),
        h('button', { class: 'chip active' }, 'Đang chọn'),
        h('span', { class: 'star-rating' }, [h('button', { class: 'star' }, '★')]),
      ]),
    })
    const wrapper = await mountSuspended(RepresentativeCascade, { attachTo: document.body })

    try {
      const contact = wrapper.get<HTMLElement>('a.hl').element
      const chip = wrapper.get<HTMLElement>('.chip.active').element
      const star = wrapper.get<HTMLElement>('.star-rating .star').element

      expect(getComputedStyle(contact).color).toBe('rgb(7, 18, 16)')
      for (const control of [chip, star]) {
        control.focus()
        expect(document.activeElement).toBe(control)
        expect(getComputedStyle(control).outlineColor).toBe('rgb(3, 90, 105)')
      }
    } finally {
      wrapper.unmount()
      stylesheet.remove()
    }
  })

  it('executes the complete semantic and control contrast audit set', async () => {
    const { stdout } = await execFileAsync(process.execPath, ['scripts/check-tri-region-contrast.mjs'], {
      cwd: resolve(root, 'web-nuxt'),
    })
    const expectedNames = [
      ...semanticPairNames,
      ...semanticPairNames.map(name => `${name}-oklch`),
      ...['srgb', 'oklch'].flatMap(format =>
        ['light', 'dark'].flatMap(theme => [
          `filled-action-${theme}-${format}`,
          `direct-contact-zalo-${theme}-${format}`,
          ...['canvas', 'surface', 'subtle'].map(surface => `control-border-${theme}-${surface}-${format}`),
          ...['canvas', 'surface', 'subtle'].map(surface => `focus-${theme}-${surface}-${format}`),
          `homepage-amber-text-${theme}-${format}`,
          `homepage-focus-action-${theme}-${format}`,
          `homepage-focus-media-${theme}-${format}`,
          `homepage-today-text-${theme}-${format}`,
        ]),
      ),
    ]
    const outputNames = stdout.trim().split(/\r?\n/).map(line => line.split(/\s+/)[0])

    expect(outputNames).toEqual(expectedNames)
  })

  it('fails closed when an audited numeric token parses as non-finite', async () => {
    const source = await readFile(resolve(root, 'web-nuxt/assets/css/variables.css'), 'utf8')
    const homeSource = await readFile(resolve(root, 'web-nuxt/assets/css/home-nocturne.css'), 'utf8')
    const invalidWeight = '9'.repeat(400)
    const invalidCss = source.replace(
      /(--color-action-border:\s*color-mix\(in srgb, var\(--color-action\) )([0-9.]+)(%, transparent\);)/,
      (_, prefix, _weight, suffix) => `${prefix}${invalidWeight}${suffix}`,
    )
    const temp = await mkdtemp(join(tmpdir(), 'tri-region-contrast-'))
    await mkdir(resolve(temp, 'assets/css'), { recursive: true })
    await writeFile(resolve(temp, 'assets/css/variables.css'), invalidCss)
    await writeFile(resolve(temp, 'assets/css/home-nocturne.css'), homeSource)

    try {
      await expect(
        execFileAsync(process.execPath, [resolve(root, 'web-nuxt/scripts/check-tri-region-contrast.mjs')], {
          cwd: temp,
        }),
      ).rejects.toBeDefined()
    } finally {
      await rm(temp, { recursive: true, force: true })
    }
  })

  it('fails closed when a Homepage focus alias points at an unsupported semantic token', async () => {
    const source = await readFile(resolve(root, 'web-nuxt/assets/css/variables.css'), 'utf8')
    const homeSource = await readFile(resolve(root, 'web-nuxt/assets/css/home-nocturne.css'), 'utf8')
    const invalidHomeCss = homeSource.replace(
      /--home-color-focus-on-media:\s*var\(--color-focus\);/,
      '--home-color-focus-on-media: var(--color-brand);',
    )
    const temp = await mkdtemp(join(tmpdir(), 'tri-region-home-alias-'))
    await mkdir(resolve(temp, 'assets/css'), { recursive: true })
    await writeFile(resolve(temp, 'assets/css/variables.css'), source)
    await writeFile(resolve(temp, 'assets/css/home-nocturne.css'), invalidHomeCss)

    try {
      await expect(
        execFileAsync(process.execPath, [resolve(root, 'web-nuxt/scripts/check-tri-region-contrast.mjs')], {
          cwd: temp,
        }),
      ).rejects.toMatchObject({
        stderr: expect.stringContaining('Unsupported semantic alias'),
      })
    } finally {
      await rm(temp, { recursive: true, force: true })
    }
  })
})
