import { spawnSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { basename, dirname, resolve } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'

const appRoot = resolve(import.meta.dirname, '..')
const checkerSource = readFileSync(resolve(appRoot, 'scripts/check-tri-region-color-debt.mjs'), 'utf8')
const fixturePaths: string[] = []

const approvedBudgets = {
  'pages/index.vue': { rawHex: 0, legacyPrimary: 0 },
  'assets/css/home-nocturne.css': { rawHex: 0, legacyPrimary: 0 },
  'pages/du-lich.vue': { rawHex: 0, legacyPrimary: 0 },
  'pages/tim-kiem.vue': { rawHex: 0, legacyPrimary: 0 },
  'pages/dia-diem/[id].vue': { rawHex: 0, legacyPrimary: 0 },
  'components/home/HomeFeatureDossier.vue': { rawHex: 0, legacyPrimary: 0 },
  'components/home/HomeDecisionLedger.vue': { rawHex: 0, legacyPrimary: 0 },
  'components/home/HomeCategoryIndex.vue': { rawHex: 0, legacyPrimary: 0 },
  'components/SourceMark.vue': { rawHex: 0, legacyPrimary: 0 },
  'components/FreshnessLine.vue': { rawHex: 0, legacyPrimary: 0 },
  'components/EntityTrustPanel.vue': { rawHex: 0, legacyPrimary: 0 },
  'components/EntityCard.vue': { rawHex: 0, legacyPrimary: 0 },
  'components/CatalogSpotlight.vue': { rawHex: 0, legacyPrimary: 0 },
  'components/CatalogInterstitial.vue': { rawHex: 0, legacyPrimary: 0 },
  'components/ContactWidget.vue': { rawHex: 0, legacyPrimary: 0 },
  'components/ImageDisclosure.vue': { rawHex: 0, legacyPrimary: 0 },
  'components/EntityHeroPlaceholder.vue': { rawHex: 0, legacyPrimary: 0 },
  'assets/css/tri-region-color.css': { rawHex: 0, legacyPrimary: 0 },
  'assets/css/catalog.css': { rawHex: 5, legacyPrimary: 58 },
  'assets/css/detail.css': { rawHex: 20, legacyPrimary: 45 },
}

type Manifest = Record<string, { rawHex?: unknown, legacyPrimary?: unknown }>

const cloneManifest = (): Manifest => JSON.parse(JSON.stringify(approvedBudgets))

const repeatedLegacyConsumers = (count: number) => Array.from(
  { length: count },
  (_, index) => `.legacy-${index} { color: var(--primary); }`,
).join('\n')

const approvedCompatibilityAliases = `
:root[data-color-system="tri-region-v1"] {
  --catalog-legacy-primary: var(--primary);
  --catalog-legacy-primary-rgb: var(--primary-rgb);
  --catalog-legacy-primary-fg: var(--primary-fg);
  --catalog-legacy-primary-fg-strong: var(--primary-fg-strong);
}
`

const baselineSources = () => ({
  'assets/css/tri-region-color.css': approvedCompatibilityAliases,
  'assets/css/catalog.css': `${repeatedLegacyConsumers(57)}\n:root {\n  --AREA-rgb: var(--primary-rgb);\n}\n`,
  'assets/css/detail.css': repeatedLegacyConsumers(45),
})

const createFixture = ({
  manifest = cloneManifest(),
  sources = {},
}: {
  manifest?: unknown
  sources?: Record<string, string>
} = {}) => {
  const root = mkdtempSync(resolve(tmpdir(), 'tri-region-color-debt-'))
  fixturePaths.push(root)
  const mergedSources = { ...baselineSources(), ...sources }

  mkdirSync(resolve(root, 'scripts'), { recursive: true })
  mkdirSync(resolve(root, 'config'), { recursive: true })
  writeFileSync(resolve(root, 'scripts/check-tri-region-color-debt.mjs'), checkerSource)
  writeFileSync(resolve(root, 'config/tri-region-color-debt.json'), JSON.stringify(manifest, null, 2))

  for (const relativePath of Object.keys(approvedBudgets)) {
    const filePath = resolve(root, relativePath)
    mkdirSync(dirname(filePath), { recursive: true })
    writeFileSync(filePath, mergedSources[relativePath as keyof typeof mergedSources] ?? '')
  }

  return root
}

const runChecker = (root: string) => spawnSync(
  process.execPath,
  ['scripts/check-tri-region-color-debt.mjs'],
  { cwd: root, encoding: 'utf8' },
)

afterEach(() => {
  while (fixturePaths.length) {
    rmSync(fixturePaths.pop()!, { recursive: true, force: true })
  }
})

describe('tri-region color debt ratchet', () => {
  it('keeps the committed wave files within the approved debt baseline', () => {
    const result = runChecker(appRoot)

    expect(result.status).toBe(0)
    expect(result.stdout).toContain('tri-region color debt: PASS')
  })

  it('counts the existing catalog custom-property dependency in the exact accepted baseline', () => {
    const result = runChecker(createFixture())

    expect(result.status).toBe(0)
    expect(result.stdout).toContain('assets/css/catalog.css: rawHex 0/5, legacyPrimary 58/58')
    expect(result.stdout).toContain('shared catalog.css + detail.css: rawHex 0/25, legacyPrimary 103/103')
  })

  it('rejects one new shared legacy-primary consumer above the exact baseline', () => {
    const result = runChecker(createFixture({
      sources: {
        'assets/css/catalog.css': `${baselineSources()['assets/css/catalog.css']}\n.extra { color: var(--primary); }`,
      },
    }))

    expect(result.status).not.toBe(0)
    expect(result.stderr).toContain('tri-region color debt: FAIL')
  })

  it('rejects a manifest that removes a required scoped path', () => {
    const manifest = cloneManifest()
    delete manifest['pages/index.vue']
    const result = runChecker(createFixture({ manifest }))

    expect(result.status).not.toBe(0)
    expect(result.stderr).toContain('exact required path set')
  })

  it('rejects a manifest ceiling increase even when the measured source remains below it', () => {
    const manifest = cloneManifest()
    manifest['assets/css/catalog.css']!.legacyPrimary = 59
    const result = runChecker(createFixture({ manifest }))

    expect(result.status).not.toBe(0)
    expect(result.stderr).toContain('approved budget')
  })

  it.each([
    ['missing ceiling', { rawHex: 0 }],
    ['string ceiling', { rawHex: '0', legacyPrimary: 0 }],
    ['null ceiling', { rawHex: null, legacyPrimary: 0 }],
    ['fractional ceiling', { rawHex: 0.5, legacyPrimary: 0 }],
  ])('rejects a %s instead of finite non-negative integer budgets', (_label, invalidBudget) => {
    const manifest = cloneManifest()
    manifest['pages/index.vue'] = invalidBudget
    const result = runChecker(createFixture({ manifest }))

    expect(result.status).not.toBe(0)
    expect(result.stderr).toContain('finite non-negative integer')
  })

  it('rejects a non-object manifest before trying to scan files', () => {
    const result = runChecker(createFixture({ manifest: [] }))

    expect(result.status).not.toBe(0)
    expect(result.stderr).toContain('plain object')
  })

  it('rejects extra manifest paths even when a traversal target exists', () => {
    const manifest = cloneManifest()
    const root = createFixture({ manifest })
    const outsidePath = resolve(root, '..', `${basename(root)}-outside.css`)
    const outsideRelativePath = `../${basename(root)}-outside.css`
    manifest[outsideRelativePath] = { rawHex: 0, legacyPrimary: 0 }
    fixturePaths.push(outsidePath)
    writeFileSync(outsidePath, '')
    writeFileSync(resolve(root, 'config/tri-region-color-debt.json'), JSON.stringify(manifest, null, 2))
    const result = runChecker(root)

    expect(result.status).not.toBe(0)
    expect(result.stderr).toContain('exact required path set')
    expect(result.stderr).toContain('root-contained')
  })

  it('counts valid var whitespace and comments that previously bypassed zero budgets', () => {
    const result = runChecker(createFixture({
      sources: {
        'pages/index.vue': `
          .action {
            color: var( --primary);
            border-color: rgb(var(/* valid CSS comment */ --primary-rgb));
          }
        `,
      },
    }))

    expect(result.status).not.toBe(0)
    expect(result.stdout).toContain('pages/index.vue: rawHex 0/0, legacyPrimary 2/0')
  })

  it('exempts only approved compatibility aliases and counts other custom-property dependencies', () => {
    const result = runChecker(createFixture({
      sources: {
        'assets/css/tri-region-color.css': `${approvedCompatibilityAliases}\n:root {\n  --local-action: var(--primary);\n}`,
      },
    }))

    expect(result.status).not.toBe(0)
    expect(result.stdout).toContain('assets/css/tri-region-color.css: rawHex 0/0, legacyPrimary 1/0')
  })
})
