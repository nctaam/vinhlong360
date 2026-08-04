import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const appRoot = resolve(scriptDir, '..')
const manifestPath = resolve(appRoot, 'config/tri-region-color-debt.json')
const rawHexPattern = /(?<![&\w-])#[0-9a-f]{3,8}\b/gi
const legacyPrimaryPattern = /var\(--primary(?:-[\w-]+)?/g
const sharedLimits = { rawHex: 25, legacyPrimary: 103 }

const countMatches = (source, pattern) => source.match(pattern)?.length ?? 0
const countLegacyPrimaryUsages = (source) => source
  .split(/\r?\n/)
  // Compatibility aliases declare semantic tokens; they are not legacy consumers.
  .filter((line) => !/^\s*--[\w-]+\s*:/.test(line))
  .reduce((count, line) => count + countMatches(line, legacyPrimaryPattern), 0)

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

let failed = false
const totals = { rawHex: 0, legacyPrimary: 0 }

for (const [relativePath, budget] of Object.entries(manifest)) {
  const filePath = resolve(appRoot, relativePath)
  if (!existsSync(filePath)) {
    console.error(`${relativePath}: missing (budget rawHex=${budget.rawHex}, legacyPrimary=${budget.legacyPrimary})`)
    failed = true
    continue
  }

  const source = readFileSync(filePath, 'utf8')
  const rawHex = countMatches(source, rawHexPattern)
  const legacyPrimary = countLegacyPrimaryUsages(source)
  totals.rawHex += rawHex
  totals.legacyPrimary += legacyPrimary
  console.log(`${relativePath}: rawHex ${rawHex}/${budget.rawHex}, legacyPrimary ${legacyPrimary}/${budget.legacyPrimary}`)

  if (rawHex > budget.rawHex || legacyPrimary > budget.legacyPrimary) {
    failed = true
  }
}

const sharedRawHex = ['assets/css/catalog.css', 'assets/css/detail.css']
  .reduce((sum, relativePath) => {
    const filePath = resolve(appRoot, relativePath)
    if (!existsSync(filePath)) return sum
    return sum + countMatches(readFileSync(filePath, 'utf8'), rawHexPattern)
  }, 0)
const sharedLegacyPrimary = ['assets/css/catalog.css', 'assets/css/detail.css']
  .reduce((sum, relativePath) => {
    const filePath = resolve(appRoot, relativePath)
    if (!existsSync(filePath)) return sum
    return sum + countLegacyPrimaryUsages(readFileSync(filePath, 'utf8'))
  }, 0)

console.log(`shared catalog.css + detail.css: rawHex ${sharedRawHex}/${sharedLimits.rawHex}, legacyPrimary ${sharedLegacyPrimary}/${sharedLimits.legacyPrimary}`)
if (sharedRawHex > sharedLimits.rawHex || sharedLegacyPrimary > sharedLimits.legacyPrimary) {
  failed = true
}

if (failed) {
  fail('budget exceeded or scoped file missing')
} else {
  console.log('tri-region color debt: PASS')
}
