import { execFile } from 'node:child_process'
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { promisify } from 'node:util'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

const root = resolve(import.meta.dirname, '../..')
const execFileAsync = promisify(execFile)
const contrastSubprocessTimeout = 30_000
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
  'action-dark-raised',
  'on-action-dark',
  'brand-dark',
  'brand-dark-surface',
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

type ContrastSourceOverrides = Record<string, string>

async function runContrastWithSources(overrides: ContrastSourceOverrides = {}) {
  const temp = await mkdtemp(join(tmpdir(), 'tri-region-home-alias-'))
  await Promise.all([
    cp(resolve(root, 'web-nuxt/assets/css'), resolve(temp, 'assets/css'), { recursive: true }),
    mkdir(resolve(temp, 'pages'), { recursive: true }),
    mkdir(resolve(temp, 'components'), { recursive: true }),
  ])
  await cp(resolve(root, 'web-nuxt/pages/index.vue'), resolve(temp, 'pages/index.vue'))
  await Promise.all(Object.entries(overrides).map(async ([path, source]) => {
    const target = resolve(temp, path)
    await mkdir(resolve(target, '..'), { recursive: true })
    await writeFile(target, source)
  }))

  try {
    return await execFileAsync(process.execPath, [resolve(root, 'web-nuxt/scripts/check-tri-region-contrast.mjs')], {
      cwd: temp,
    })
  }
  finally {
    await rm(temp, { recursive: true, force: true })
  }
}

async function runContrastWithHomeCss(homeCss: string) {
  return runContrastWithSources({ 'assets/css/home-nocturne.css': homeCss })
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

  it('binds the real today selector to semantic text, Coral surface and Coral boundary', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/home-nocturne.css'), 'utf8')
    const homeRoot = readCssBlock(css, '[data-home-pilot="nocturne-b1"] {')
    const today = readCssBlock(
      css,
      '[data-home-pilot="nocturne-b1"] .ec-countdown.ec-today[data-material-accent="amber"] {',
    )

    expect(homeRoot).toMatch(/--home-color-today-text:\s*var\(--color-text\)/)
    expect(homeRoot).toMatch(/--home-color-today-surface:\s*color-mix\(in srgb, var\(--color-error\) 14%, transparent\)/)
    expect(today).toMatch(/background:\s*var\(--home-color-today-surface\)/)
    expect(today).toMatch(/color:\s*var\(--home-color-today-text\)/)
    expect(today).toMatch(/box-shadow:\s*inset 0 0 0 1px var\(--color-error\)/)
  })

  it('binds the hero subtitle to semantic on-media text and an opaque local plate', async () => {
    const css = await readFile(resolve(root, 'web-nuxt/assets/css/home-nocturne.css'), 'utf8')
    const homeRoot = readCssBlock(css, '[data-home-pilot="nocturne-b1"] {')
    const subtitle = readCssBlock(css, '[data-home-pilot="nocturne-b1"] .hero-sub {')

    expect(homeRoot).toMatch(/--home-color-on-media-text:\s*var\(--surface-white\)/)
    expect(homeRoot).toMatch(/--home-color-on-media-plate:\s*rgba\(var\(--black-rgb\),\s*\.7[2-9]\)/)
    expect(subtitle).toMatch(/color:\s*var\(--home-color-on-media-text\)/)
    expect(subtitle).toMatch(/background:\s*var\(--home-color-on-media-plate\)/)
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

  it('executes the complete semantic and control contrast audit set', { timeout: contrastSubprocessTimeout }, async () => {
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
          `homepage-on-media-text-${theme}-${format}`,
          `homepage-focus-action-${theme}-${format}`,
          `homepage-focus-media-${theme}-${format}`,
          `homepage-today-text-${theme}-${format}`,
        ]),
      ),
    ]
    const outputNames = stdout.trim().split(/\r?\n/).map(line => line.split(/\s+/)[0])

    expect(outputNames).toEqual(expectedNames)
    expect(stdout).toContain('homepage-amber-text-light-srgb 4.86 4.5')
    expect(stdout).toContain('homepage-today-text-light-srgb 13.78 4.5')
    expect(stdout).toContain('homepage-amber-text-dark-srgb 6.81 4.5')
    expect(stdout).toContain('homepage-today-text-dark-srgb 13.35 4.5')
    expect(stdout).toContain('homepage-amber-text-light-oklch 5.33 4.5')
    expect(stdout).toContain('homepage-today-text-light-oklch 13.76 4.5')
    expect(stdout).toContain('homepage-amber-text-dark-oklch 6.80 4.5')
    expect(stdout).toContain('homepage-today-text-dark-oklch 13.37 4.5')
    expect(stdout).toContain('homepage-focus-media-light-srgb 4.52 3.0')
    expect(stdout).toContain('homepage-focus-media-dark-srgb 4.52 3.0')
    expect(stdout).toContain('homepage-focus-media-light-oklch 4.52 3.0')
    expect(stdout).toContain('homepage-focus-media-dark-oklch 4.52 3.0')
    expect(stdout).toContain('homepage-on-media-text-light-srgb 10.55 4.5')
    expect(stdout).toContain('homepage-on-media-text-dark-srgb 10.55 4.5')
    expect(stdout).toContain('homepage-on-media-text-light-oklch 10.52 4.5')
    expect(stdout).toContain('homepage-on-media-text-dark-oklch 10.52 4.5')
  })

  it('fails closed when an audited numeric token parses as non-finite', { timeout: contrastSubprocessTimeout }, async () => {
    const source = await readFile(resolve(root, 'web-nuxt/assets/css/variables.css'), 'utf8')
    const invalidWeight = '9'.repeat(400)
    const invalidCss = source.replace(
      /(--color-action-border:\s*color-mix\(in srgb, var\(--color-action\) )([0-9.]+)(%, transparent\);)/,
      (_, prefix, _weight, suffix) => `${prefix}${invalidWeight}${suffix}`,
    )
    await expect(runContrastWithSources({
      'assets/css/variables.css': invalidCss,
    })).rejects.toMatchObject({ stderr: expect.stringContaining('Non-finite numeric value') })
  })

  it.each([
    {
      name: 'missing action alias hidden in a comment',
      mutate: (source: string) => source.replace(
        '--home-color-focus-on-action: var(--color-on-action);',
        '/* --home-color-focus-on-action: var(--color-on-action); */',
      ),
      message: 'Missing semantic alias assignment for --home-color-focus-on-action',
    },
    {
      name: 'malformed action alias',
      mutate: (source: string) => source.replace(
        '--home-color-focus-on-action: var(--color-on-action);',
        '--home-color-focus-on-action: var(--color-on-action;',
      ),
      message: 'Unclosed bracket',
    },
    {
      name: 'duplicate action alias',
      mutate: (source: string) => source.replace(
        '--home-color-focus-on-action: var(--color-on-action);',
        '--home-color-focus-on-action: var(--color-on-action);\n  --home-color-focus-on-action: var(--color-on-action);',
      ),
      message: 'Duplicate semantic alias assignment for --home-color-focus-on-action',
    },
    {
      name: 'missing media alias hidden in a comment',
      mutate: (source: string) => source.replace(
        '--home-color-focus-on-media: var(--surface-white);',
        '/* --home-color-focus-on-media: var(--surface-white); */',
      ),
      message: 'Missing semantic alias assignment for --home-color-focus-on-media',
    },
    {
      name: 'malformed light media alias',
      mutate: (source: string) => source.replace(
        '.light [data-home-pilot="nocturne-b1"] {\n  --home-color-focus-on-media: var(--surface-white);',
        '.light [data-home-pilot="nocturne-b1"] {\n  --home-color-focus-on-media: var(--surface-white;',
      ),
      message: 'Unclosed bracket',
    },
    {
      name: 'duplicate light media alias',
      mutate: (source: string) => source.replace(
        '.light [data-home-pilot="nocturne-b1"] {\n  --home-color-focus-on-media: var(--surface-white);',
        '.light [data-home-pilot="nocturne-b1"] {\n  --home-color-focus-on-media: var(--surface-white);\n  --home-color-focus-on-media: var(--surface-white);',
      ),
      message: 'Duplicate semantic alias assignment for --home-color-focus-on-media',
    },
    {
      name: 'missing today text alias hidden in a comment',
      mutate: (source: string) => source.replace(
        '--home-color-today-text: var(--color-text);',
        '/* --home-color-today-text: var(--color-text); */',
      ),
      message: 'Missing semantic alias assignment for --home-color-today-text',
    },
    {
      name: 'malformed today text alias',
      mutate: (source: string) => source.replace(
        '--home-color-today-text: var(--color-text);',
        '--home-color-today-text: var(--color-text;',
      ),
      message: 'Unclosed bracket',
    },
    {
      name: 'duplicate today text alias',
      mutate: (source: string) => source.replace(
        '--home-color-today-text: var(--color-text);',
        '--home-color-today-text: var(--color-text);\n  --home-color-today-text: var(--color-text);',
      ),
      message: 'Duplicate semantic alias assignment for --home-color-today-text',
    },
    {
      name: 'unsupported media alias',
      mutate: (source: string) => source.replace(
        '--home-color-focus-on-media: var(--surface-white);',
        '--home-color-focus-on-media: var(--color-brand);',
      ),
      message: 'Unsupported semantic alias for --home-color-focus-on-media',
    },
    {
      name: 'missing on-media text alias hidden in a comment',
      mutate: (source: string) => source.replace(
        '--home-color-on-media-text: var(--surface-white);',
        '/* --home-color-on-media-text: var(--surface-white); */',
      ),
      message: 'Missing semantic alias assignment for --home-color-on-media-text',
    },
    {
      name: 'unsupported media halo alias',
      mutate: (source: string) => source.replace(
        '--home-color-focus-on-media-halo: var(--color-mask-opaque);',
        '--home-color-focus-on-media-halo: var(--color-brand);',
      ),
      message: 'Unsupported semantic alias for --home-color-focus-on-media-halo',
    },
    {
      name: 'duplicate on-media plate',
      mutate: (source: string) => source.replace(
        '--home-color-on-media-plate: rgba(var(--black-rgb), .76);',
        '--home-color-on-media-plate: rgba(var(--black-rgb), .76);\n  --home-color-on-media-plate: rgba(var(--black-rgb), .76);',
      ),
      message: 'Duplicate rgba declaration for --home-color-on-media-plate',
    },
    {
      name: 'duplicate Amber surface mix',
      mutate: (source: string) => source.replace(
        '--home-color-amber-surface: color-mix(in srgb, var(--color-material-amber) 14%, transparent);',
        '--home-color-amber-surface: color-mix(in srgb, var(--color-material-amber) 14%, transparent);\n  --home-color-amber-surface: color-mix(in srgb, var(--color-material-amber) 14%, transparent);',
      ),
      message: 'Duplicate color-mix declaration for --home-color-amber-surface',
    },
    {
      name: 'duplicate today surface mix',
      mutate: (source: string) => source.replace(
        '--home-color-today-surface: color-mix(in srgb, var(--color-error) 14%, transparent);',
        '--home-color-today-surface: color-mix(in srgb, var(--color-error) 14%, transparent);\n  --home-color-today-surface: color-mix(in srgb, var(--color-error) 14%, transparent);',
      ),
      message: 'Duplicate color-mix declaration for --home-color-today-surface',
    },
    {
      name: 'later Homepage root block overriding focus',
      mutate: (source: string) => `${source}\n[data-home-pilot="nocturne-b1"] { --home-color-focus-on-action: var(--color-focus); }`,
      message: 'Duplicate CSS block: [data-home-pilot="nocturne-b1"] {',
    },
    {
      name: 'later Homepage root block overriding today',
      mutate: (source: string) => `${source}\n[data-home-pilot="nocturne-b1"] { --home-color-today-text: var(--color-focus); }`,
      message: 'Duplicate CSS block: [data-home-pilot="nocturne-b1"] {',
    },
    {
      name: 'later light Homepage block overriding media focus',
      mutate: (source: string) => `${source}\n.light [data-home-pilot="nocturne-b1"] { --home-color-focus-on-media: var(--color-focus); }`,
      message: 'Duplicate CSS block: .light [data-home-pilot="nocturne-b1"] {',
    },
    {
      name: 'stronger equivalent selector overriding action focus',
      mutate: (source: string) => `${source}\n[data-home-pilot="nocturne-b1"].home { --home-color-focus-on-action: var(--color-focus); }`,
      message: 'Unexpected protected declaration for --home-color-focus-on-action',
    },
    {
      name: 'stronger light selector overriding media focus',
      mutate: (source: string) => `${source}\n.light [data-home-pilot="nocturne-b1"].home { --home-color-focus-on-media: var(--color-focus); }`,
      message: 'Unexpected protected declaration for --home-color-focus-on-media',
    },
    {
      name: 'selector list overriding media halo',
      mutate: (source: string) => `${source}\n[data-home-pilot="nocturne-b1"], .never { --home-color-focus-on-media-halo: var(--color-focus); }`,
      message: 'Unexpected protected declaration for --home-color-focus-on-media-halo',
    },
    {
      name: 'reordered stronger selector overriding on-media text',
      mutate: (source: string) => `${source}\n.home[data-home-pilot="nocturne-b1"] { --home-color-on-media-text: var(--color-text); }`,
      message: 'Unexpected protected declaration for --home-color-on-media-text',
    },
    {
      name: 'later stronger block overriding on-media plate syntax',
      mutate: (source: string) => `${source}\n.home[data-home-pilot="nocturne-b1"] { --home-color-on-media-plate: transparent; }`,
      message: 'Unexpected protected declaration for --home-color-on-media-plate',
    },
    {
      name: 'nested media query overriding today text',
      mutate: (source: string) => `${source}\n@media (min-width: 1px) { .home[data-home-pilot="nocturne-b1"] { --home-color-today-text: var(--color-focus); } }`,
      message: 'Unexpected protected declaration for --home-color-today-text',
    },
    {
      name: 'stronger selector overriding today surface syntax',
      mutate: (source: string) => `${source}\n[data-home-pilot="nocturne-b1"].home { --home-color-today-surface: var(--color-canvas); }`,
      message: 'Unexpected protected declaration for --home-color-today-surface',
    },
    {
      name: 'selector list overriding Amber text',
      mutate: (source: string) => `${source}\n[data-home-pilot="nocturne-b1"], .never { --home-color-amber-text: var(--color-text); }`,
      message: 'Unexpected protected declaration for --home-color-amber-text',
    },
    {
      name: 'nested media query overriding Amber surface syntax',
      mutate: (source: string) => `${source}\n@media (min-width: 1px) { [data-home-pilot="nocturne-b1"].home { --home-color-amber-surface: transparent; } }`,
      message: 'Unexpected protected declaration for --home-color-amber-surface',
    },
    {
      name: 'nested at-rule declaration inside the approved root rule',
      mutate: (source: string) => source.replace(
        '  --home-color-today-surface: color-mix(in srgb, var(--color-error) 14%, transparent);\n  background:',
        '  --home-color-today-surface: color-mix(in srgb, var(--color-error) 14%, transparent);\n  @media (min-width: 1px) { --home-color-on-media-text: var(--color-text); }\n  background:',
      ),
      message: 'Unexpected protected declaration for --home-color-on-media-text',
    },
    {
      name: 'nested stronger selector inside the approved root rule',
      mutate: (source: string) => source.replace(
        '  --home-color-today-surface: color-mix(in srgb, var(--color-error) 14%, transparent);\n  background:',
        '  --home-color-today-surface: color-mix(in srgb, var(--color-error) 14%, transparent);\n  &.home { --home-color-focus-on-action: var(--color-focus); }\n  background:',
      ),
      message: 'Unexpected protected declaration for --home-color-focus-on-action',
    },
    {
      name: 'comment delimiters inside escaped content strings hiding an override',
      mutate: (source: string) => `${source}\n${String.raw`
[data-home-pilot="nocturne-b1"] .comment-open::before { content: "escaped quote: \" /* { ;"; }
[data-home-pilot="nocturne-b1"].home { --home-color-focus-on-media: var(--color-focus); }
[data-home-pilot="nocturne-b1"] .comment-close::after { content: "*/ } ; backslash: \\"; }
`}`,
      message: 'Unexpected protected declaration for --home-color-focus-on-media',
    },
    {
      name: 'hex-escaped media alias in a stronger selector',
      mutate: (source: string) => `${source}\n[data-home-pilot="nocturne-b1"].home { --home-color-focus-on-medi\\000061: var(--color-focus); }`,
      message: 'Unexpected protected declaration for --home-color-focus-on-media',
    },
    {
      name: 'hex-escaped action alias with terminator whitespace',
      mutate: (source: string) => `${source}\n.home[data-home-pilot="nocturne-b1"] { --home-color-\\66 ocus-on-action: var(--color-focus); }`,
      message: 'Unexpected protected declaration for --home-color-focus-on-action',
    },
    {
      name: 'simple-escaped media halo alias in a selector list',
      mutate: (source: string) => `${source}\n[data-home-pilot="nocturne-b1"], .never { --home-color-focus-on\\-media-halo: var(--color-focus); }`,
      message: 'Unexpected protected declaration for --home-color-focus-on-media-halo',
    },
    {
      name: 'escaped protected alias inside a nested media override',
      mutate: (source: string) => `${source}\n@media (min-width: 1px) { [data-home-pilot="nocturne-b1"].home { --home-color-today\\-text: var(--color-focus); } }`,
      message: 'Unexpected protected declaration for --home-color-today-text',
    },
    {
      name: 'escaped leading hyphens on a protected alias',
      mutate: (source: string) => `${source}\n${String.raw`[data-home-pilot="nocturne-b1"].home { \2d \2d home-color-focus-on-action: var(--color-focus); }`}`,
      message: 'Unexpected protected declaration for --home-color-focus-on-action',
    },
    {
      name: 'escaped delimiter leaving an invalid custom property identifier',
      mutate: (source: string) => `${source}\n[data-home-pilot="nocturne-b1"].home { --home-color-focus-on-media\\: var(--color-focus); }`,
      message: 'Unknown word --home-color-focus-on-media',
    },
  ])('fails closed for $name', { timeout: contrastSubprocessTimeout }, async ({ mutate, message }) => {
    const homeSource = await readFile(resolve(root, 'web-nuxt/assets/css/home-nocturne.css'), 'utf8')
    await expect(runContrastWithHomeCss(mutate(homeSource))).rejects.toMatchObject({
      stderr: expect.stringContaining(message),
    })
  })

  it.each([
    {
      name: 'an extra closing brace',
      mutate: (source: string) => `${source}\n}`,
      message: 'Unexpected }',
    },
    {
      name: 'an unclosed function in an unrelated declaration',
      mutate: (source: string) => `${source}\n.syntax-probe { color: var(--color-text; }`,
      message: 'Unclosed bracket',
    },
  ])('rejects malformed Homepage CSS with $name', { timeout: contrastSubprocessTimeout }, async ({ mutate, message }) => {
    const homeSource = await readFile(resolve(root, 'web-nuxt/assets/css/home-nocturne.css'), 'utf8')
    await expect(runContrastWithHomeCss(mutate(homeSource))).rejects.toMatchObject({
      stderr: expect.stringContaining(message),
    })
  })

  it.each([
    {
      name: 'hero subtitle override',
      source: 'assets/css/base.css',
      path: 'web-nuxt/assets/css/base.css',
      mutation: '.hero-sub { opacity: .2; }',
      message: 'Unexpected protected consumer declaration: assets/css/base.css',
    },
    {
      name: 'nearby focus override',
      source: 'assets/css/base.css',
      path: 'web-nuxt/assets/css/base.css',
      mutation: '.hero-nearby:focus-visible { outline: none; }',
      message: 'Unexpected protected consumer declaration: assets/css/base.css',
    },
    {
      name: 'nested media override',
      source: 'assets/css/base.css',
      path: 'web-nuxt/assets/css/base.css',
      mutation: '@media (min-width: 1px) { .hero-search { background: transparent; } }',
      message: 'Unexpected protected consumer declaration: assets/css/base.css',
    },
    {
      name: 'selector-list override',
      source: 'assets/css/dark-overrides.css',
      path: 'web-nuxt/assets/css/dark-overrides.css',
      mutation: '.never, .ec-today { color: transparent; }',
      message: 'Unexpected protected consumer declaration: assets/css/dark-overrides.css',
    },
    {
      name: ':is() override',
      source: 'assets/css/home-nocturne.css',
      path: 'web-nuxt/assets/css/home-nocturne.css',
      mutation: ':is(.hero-search, .never) input:focus-visible { outline: none; }',
      message: 'Unexpected protected consumer declaration: assets/css/home-nocturne.css',
    },
    {
      name: 'escaped class-name override',
      source: 'assets/css/home-nocturne.css',
      path: 'web-nuxt/assets/css/home-nocturne.css',
      mutation: String.raw`.hero\2d sub { opacity: .2; }`,
      message: 'Unexpected protected consumer declaration: assets/css/home-nocturne.css',
    },
    {
      name: 'reserved soft-action override',
      source: 'assets/css/home-nocturne.css',
      path: 'web-nuxt/assets/css/home-nocturne.css',
      mutation: '.hero-action--soft { color: transparent; }',
      message: 'Unexpected protected consumer declaration: assets/css/home-nocturne.css',
    },
  ])('rejects unapproved $name', { timeout: contrastSubprocessTimeout }, async ({ source, path, mutation, message }) => {
    const original = await readFile(resolve(root, path), 'utf8')
    await expect(runContrastWithSources({ [source]: `${original}\n${mutation}` })).rejects.toMatchObject({
      stderr: expect.stringContaining(message),
    })
  })

  it('rejects an unapproved ec-today override in the Homepage SFC style', { timeout: contrastSubprocessTimeout }, async () => {
    const pageSource = await readFile(resolve(root, 'web-nuxt/pages/index.vue'), 'utf8')
    const mutatedPage = pageSource.replace('</style>', '.ec-today { color: transparent; }\n</style>')

    await expect(runContrastWithSources({ 'pages/index.vue': mutatedPage })).rejects.toMatchObject({
      stderr: expect.stringContaining('Unexpected protected consumer declaration: pages/index.vue#style-0'),
    })
  })

  it.each([
    {
      name: 'protected alias from another global stylesheet',
      path: 'assets/css/components.css',
      mutation: '[data-home-pilot="nocturne-b1"] { --home-color-today-text: var(--color-focus); }',
    },
    {
      name: 'hero subtitle background-color reset',
      path: 'assets/css/components.css',
      mutation: '.hero-sub { background-color: transparent; }',
    },
    {
      name: 'nearby outline-color reset',
      path: 'assets/css/components.css',
      mutation: '.hero-nearby:focus-visible { outline-color: transparent; }',
    },
    {
      name: 'actual search input all reset',
      path: 'assets/css/components.css',
      mutation: '.hero-search input { all: unset; }',
    },
    {
      name: 'dossier action important transparency',
      path: 'assets/css/components.css',
      mutation: '.home-feature-dossier__action { background-color: transparent !important; }',
    },
    {
      name: 'dossier action modifier transparency',
      path: 'assets/css/components.css',
      mutation: '.home-feature-dossier__action--secondary { background-color: transparent; }',
    },
    {
      name: 'event date background image reset',
      path: 'assets/css/components.css',
      mutation: '.ec-date { background-image: none; }',
    },
    {
      name: 'countdown destructive filter',
      path: 'assets/css/components.css',
      mutation: '.ec-countdown { filter: opacity(0); }',
    },
    {
      name: 'today text fill reset',
      path: 'assets/css/components.css',
      mutation: '.ec-today { -webkit-text-fill-color: transparent; }',
    },
    {
      name: 'nested media selector list with subject is()',
      path: 'assets/css/components.css',
      mutation: '@media (min-width: 1px) { :is(.never, .home-feature-dossier__action), .hero\\2d search input { border-top-color: transparent; } }',
    },
  ])('scans every global CSS source and rejects $name', { timeout: contrastSubprocessTimeout }, async ({ path, mutation }) => {
    const original = await readFile(resolve(root, 'web-nuxt', path), 'utf8')

    await expect(runContrastWithSources({ [path]: `${original}\n${mutation}` })).rejects.toMatchObject({
      stderr: expect.stringContaining(path),
    })
  })

  it.each([
    {
      name: 'page SFC dossier action reset',
      path: 'pages/tim-kiem.vue',
      mutation: '.home-feature-dossier__action { background-color: transparent !important; }',
    },
    {
      name: 'component SFC search input reset',
      path: 'components/SearchAutocomplete.vue',
      mutation: '.hero-search input { outline-style: none; }',
    },
  ])('scans every Vue style block and rejects $name', { timeout: contrastSubprocessTimeout }, async ({ path, mutation }) => {
    const original = await readFile(resolve(root, 'web-nuxt', path), 'utf8')
    const mutated = `${original}\n<style>${mutation}</style>\n`

    await expect(runContrastWithSources({ [path]: mutated })).rejects.toMatchObject({
      stderr: expect.stringContaining(path),
    })
  })

  it('fails loudly when an unrelated CSS or Vue style block cannot be parsed', { timeout: contrastSubprocessTimeout }, async () => {
    const componentsCss = await readFile(resolve(root, 'web-nuxt/assets/css/components.css'), 'utf8')
    const search = await readFile(resolve(root, 'web-nuxt/components/SearchAutocomplete.vue'), 'utf8')

    await expect(runContrastWithSources({
      'assets/css/components.css': `${componentsCss}\n.syntax-error { color: var(--color-text; }`,
    })).rejects.toMatchObject({ stderr: expect.stringContaining('assets/css/components.css') })
    await expect(runContrastWithSources({
      'components/SearchAutocomplete.vue': `${search}\n<style>.syntax-error { color: var(--color-text; }</style>`,
    })).rejects.toMatchObject({ stderr: expect.stringContaining('components/SearchAutocomplete.vue') })
  })

  it('does not treat classes used only inside :not() or :has() as protected subjects', { timeout: contrastSubprocessTimeout }, async () => {
    const homeSource = await readFile(resolve(root, 'web-nuxt/assets/css/home-nocturne.css'), 'utf8')
    const safeRelationalSelectors = `
.audit-probe:not(.hero-sub) { background: transparent; }
.audit-probe:has(.home-feature-dossier__action) { color: transparent; }
.audit-probe:not(:is(.hero-nearby, .ec-today)) { outline: none; }
`

    await expect(runContrastWithHomeCss(`${homeSource}\n${safeRelationalSelectors}`)).resolves.toMatchObject({
      stdout: expect.stringContaining('homepage-on-media-text-light-srgb 10.55 4.5'),
      stderr: '',
    })
  })

  it('reports the intentional Nuxt/Vue audit toolchain and compatible parser versions', { timeout: contrastSubprocessTimeout }, async () => {
    const { stdout } = await execFileAsync(process.execPath, ['scripts/check-tri-region-contrast.mjs'], {
      cwd: resolve(root, 'web-nuxt'),
      env: { ...process.env, TRI_REGION_AUDIT_TOOLCHAIN: '1' },
    })

    expect(stdout).toMatch(/audit-toolchain .*nuxt@4\..*vue\/compiler-sfc@3\..*postcss@8\..*postcss-selector-parser@7\./)
  })

  // Mốc dời 96bfba4c → 358fe697 (2026-08-05): thêm devDependency `axe-core` để
  // R30.6 có nguồn sinh axe-report.json — trước đó cổng hard-ratchet ấy chưa
  // từng chạy lần nào. Đây là thay đổi toolchain CÓ CHỦ ĐÍCH, chủ dự án duyệt;
  // khác biệt so với mốc cũ đúng một dòng. Chốt chặn giữ nguyên tác dụng: mọi
  // dependency thêm sau đây vẫn làm test đỏ cho tới khi có người dời mốc và
  // giải trình.
  it.each(['package.json', 'package-lock.json'])('keeps %s identical to the remediation base', async (path) => {
    const [{ stdout: baseline }, current] = await Promise.all([
      execFileAsync('git', ['show', `358fe697:web-nuxt/${path}`], { cwd: root }),
      readFile(resolve(root, 'web-nuxt', path), 'utf8'),
    ])

    expect(current.replace(/\r\n/g, '\n')).toBe(baseline.replace(/\r\n/g, '\n'))
  })

  it.each([
    {
      name: 'a function containing a semicolon',
      fixture: '.syntax-probe { background-image: url("data:image/svg+xml;utf8,<svg>{}</svg>"); }',
    },
    {
      name: 'a balanced custom-property block',
      fixture: '.syntax-probe { --unprotected-block: {a;b}; color: var(--color-text); }',
    },
    {
      name: 'an escaped brace in a selector',
      fixture: String.raw`.syntax-probe\{literal { color: var(--color-text); }`,
    },
  ])('accepts valid CSS with $name', { timeout: contrastSubprocessTimeout }, async ({ fixture }) => {
    const homeSource = await readFile(resolve(root, 'web-nuxt/assets/css/home-nocturne.css'), 'utf8')
    await expect(runContrastWithHomeCss(`${homeSource}\n${fixture}`)).resolves.toMatchObject({
      stdout: expect.stringContaining('homepage-on-media-text-light-srgb 10.55 4.5'),
      stderr: '',
    })
  })

  it('keeps legitimate comment markers, escapes, braces and continuations inside CSS strings', { timeout: contrastSubprocessTimeout }, async () => {
    const homeSource = await readFile(resolve(root, 'web-nuxt/assets/css/home-nocturne.css'), 'utf8')
    const safeStrings = String.raw`
[data-home-pilot="nocturne-b1"] .string-probe::before {
  content: "literal /* */ escaped quote: \" backslash: \\ braces: { } semicolon: ;";
  --unprotected-copy: "continued\
line";
}
[data-home-pilot="nocturne-b1"] .string-probe::after {
  content: 'literal /* */ escaped quote: \' backslash: \\ braces: { } semicolon: ;';
}
`

    await expect(runContrastWithHomeCss(`${homeSource}\n${safeStrings}`)).resolves.toMatchObject({
      stdout: expect.stringContaining('homepage-on-media-text-light-srgb 10.55 4.5'),
      stderr: '',
    })
  })
})
