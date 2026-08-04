import { existsSync, readFileSync } from 'node:fs'
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const appRoot = resolve(scriptDir, '..')
const manifestPath = resolve(appRoot, 'config/tri-region-color-debt.json')
const rawHexPattern = /(?<![&\w-])#[0-9a-f]{3,8}\b/gi
const legacyPrimaryPattern = /\bvar\s*\(\s*--primary(?:-[\w-]+)?\b/g
const customPropertyDeclarationPattern = /(--[\w-]+)\s*:\s*([^;{}]*);/g

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

const approvedCompatibilityAliases = new Map([
  ['--catalog-legacy-primary', '--primary'],
  ['--catalog-legacy-primary-rgb', '--primary-rgb'],
  ['--catalog-legacy-primary-fg', '--primary-fg'],
  ['--catalog-legacy-primary-fg-strong', '--primary-fg-strong'],
])

const requiredPaths = Object.keys(approvedBudgets)
const sharedPaths = ['assets/css/catalog.css', 'assets/css/detail.css']
const sharedLimits = sharedPaths.reduce((limits, relativePath) => ({
  rawHex: limits.rawHex + approvedBudgets[relativePath].rawHex,
  legacyPrimary: limits.legacyPrimary + approvedBudgets[relativePath].legacyPrimary,
}), { rawHex: 0, legacyPrimary: 0 })

const isPlainObject = (value) => value !== null
  && typeof value === 'object'
  && !Array.isArray(value)
  && Object.getPrototypeOf(value) === Object.prototype

const isRootContained = (relativePath) => {
  if (isAbsolute(relativePath)) return false
  const resolvedPath = resolve(appRoot, relativePath)
  const fromRoot = relative(appRoot, resolvedPath)
  return fromRoot !== '..' && !fromRoot.startsWith(`..${sep}`) && !isAbsolute(fromRoot)
}

const validateManifest = (manifest) => {
  if (!isPlainObject(manifest)) {
    return ['manifest must be a plain object']
  }

  const errors = []
  const actualPaths = Object.keys(manifest)
  const missingPaths = requiredPaths.filter((path) => !Object.hasOwn(manifest, path))
  const extraPaths = actualPaths.filter((path) => !Object.hasOwn(approvedBudgets, path))
  if (missingPaths.length || extraPaths.length) {
    errors.push(`manifest must use the exact required path set (missing=${missingPaths.join(',') || 'none'}; extra=${extraPaths.join(',') || 'none'})`)
  }

  for (const relativePath of actualPaths) {
    if (!isRootContained(relativePath)) {
      errors.push(`manifest path must be root-contained: ${relativePath}`)
    }

    const budget = manifest[relativePath]
    if (!isPlainObject(budget)) {
      errors.push(`${relativePath}: budget must be a plain object`)
      continue
    }

    const fields = Object.keys(budget).sort()
    if (fields.join(',') !== 'legacyPrimary,rawHex') {
      errors.push(`${relativePath}: budget must contain exactly rawHex and legacyPrimary`)
    }

    for (const field of ['rawHex', 'legacyPrimary']) {
      if (!Number.isFinite(budget[field]) || !Number.isInteger(budget[field]) || budget[field] < 0) {
        errors.push(`${relativePath}.${field}: budget must be a finite non-negative integer`)
      }
    }

    const approved = approvedBudgets[relativePath]
    if (approved && Number.isInteger(budget.rawHex) && Number.isInteger(budget.legacyPrimary)) {
      if (budget.rawHex !== approved.rawHex || budget.legacyPrimary !== approved.legacyPrimary) {
        errors.push(`${relativePath}: budget must match the approved budget rawHex=${approved.rawHex}, legacyPrimary=${approved.legacyPrimary}`)
      }
    }
  }

  return errors
}

const countMatches = (source, pattern) => source.match(pattern)?.length ?? 0
const stripCssComments = (source) => source.replace(/\/\*[\s\S]*?\*\//g, ' ')

const removeApprovedCompatibilityAliases = (source, relativePath) => {
  if (relativePath !== 'assets/css/tri-region-color.css') return source

  return source.replace(customPropertyDeclarationPattern, (declaration, property, value) => {
    const approvedTarget = approvedCompatibilityAliases.get(property)
    if (!approvedTarget) return declaration
    return value.replace(/\s+/g, '') === `var(${approvedTarget})` ? '' : declaration
  })
}

const countLegacyPrimaryUsages = (source, relativePath) => {
  const normalizedSource = removeApprovedCompatibilityAliases(stripCssComments(source), relativePath)
  return countMatches(normalizedSource, legacyPrimaryPattern)
}

const fail = (message) => {
  console.error(`tri-region color debt: FAIL - ${message}`)
  process.exitCode = 1
}

if (!existsSync(manifestPath)) {
  fail(`missing manifest ${manifestPath}`)
  process.exit()
}

let manifest
try {
  manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))
} catch (error) {
  fail(`cannot read manifest: ${error instanceof Error ? error.message : String(error)}`)
  process.exit()
}

const manifestErrors = validateManifest(manifest)
if (manifestErrors.length) {
  fail(manifestErrors.join('; '))
  process.exit()
}

let failed = false
const measurements = new Map()

for (const relativePath of requiredPaths) {
  const budget = approvedBudgets[relativePath]
  const filePath = resolve(appRoot, relativePath)
  if (!existsSync(filePath)) {
    console.error(`${relativePath}: missing (budget rawHex=${budget.rawHex}, legacyPrimary=${budget.legacyPrimary})`)
    failed = true
    continue
  }

  const source = readFileSync(filePath, 'utf8')
  const measurement = {
    rawHex: countMatches(source, rawHexPattern),
    legacyPrimary: countLegacyPrimaryUsages(source, relativePath),
  }
  measurements.set(relativePath, measurement)
  console.log(`${relativePath}: rawHex ${measurement.rawHex}/${budget.rawHex}, legacyPrimary ${measurement.legacyPrimary}/${budget.legacyPrimary}`)

  if (measurement.rawHex > budget.rawHex || measurement.legacyPrimary > budget.legacyPrimary) {
    failed = true
  }
}

const sharedMeasurement = sharedPaths.reduce((total, relativePath) => {
  const measurement = measurements.get(relativePath) ?? { rawHex: 0, legacyPrimary: 0 }
  return {
    rawHex: total.rawHex + measurement.rawHex,
    legacyPrimary: total.legacyPrimary + measurement.legacyPrimary,
  }
}, { rawHex: 0, legacyPrimary: 0 })

console.log(`shared catalog.css + detail.css: rawHex ${sharedMeasurement.rawHex}/${sharedLimits.rawHex}, legacyPrimary ${sharedMeasurement.legacyPrimary}/${sharedLimits.legacyPrimary}`)
if (sharedMeasurement.rawHex > sharedLimits.rawHex || sharedMeasurement.legacyPrimary > sharedLimits.legacyPrimary) {
  failed = true
}

if (failed) {
  fail('budget exceeded or scoped file missing')
} else {
  console.log('tri-region color debt: PASS')
}
