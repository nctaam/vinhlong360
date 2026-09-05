import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { basename, dirname, isAbsolute, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const appRoot = resolve(scriptDir, '..')
const manifestPath = resolve(appRoot, 'config/tri-region-color-debt.json')
const rawHexPattern = /(?<![&\w-])#[0-9a-f]{3,8}\b/gi
const legacyPrimaryPattern = /\bvar\s*\(\s*--primary(?:-[\w-]+)?\b/g
// Capture declarations with or without a trailing semicolon. CSS custom
// properties are frequently the final declaration before `}` or EOF.
const customPropertyDeclarationPattern = /(--[\w-]+)\s*:\s*([^;{}]*?)(?:;|(?=\s*}|\s*$))/g
const cssDeclarationPattern = /(?:^|[;{}])\s*([\w-]+)\s*:\s*([^;{}]+)/gim
const rawCssHexPattern = /#[0-9a-f]{3,8}\b/i
const rawModernColorFunctionPattern = /\b(?:hsl|hsla|hwb|oklch|oklab|lab|lch|color)\s*\(/i
const rawModernRgbPattern = /\b(?:rgb|rgba)\s*\([^)]*\)/i
const rawColorMixPattern = /\bcolor-mix\s*\([^)]*(?:#[0-9a-f]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|hwb|oklch|oklab|lab|lch|color)\s*\()/i
const cssNamedColorPattern = /(?<![-\w])(?:aliceblue|antiquewhite|aqua|aquamarine|azure|beige|bisque|black|blanchedalmond|blue|blueviolet|brown|burlywood|cadetblue|chartreuse|chocolate|coral|cornflowerblue|cornsilk|crimson|cyan|darkblue|darkcyan|darkgoldenrod|darkgray|darkgreen|darkgrey|darkkhaki|darkmagenta|darkolivegreen|darkorange|darkorchid|darkred|darksalmon|darkseagreen|darkslateblue|darkslategray|darkslategrey|darkturquoise|darkviolet|deeppink|deepskyblue|dimgray|dimgrey|dodgerblue|firebrick|floralwhite|forestgreen|fuchsia|gainsboro|ghostwhite|gold|goldenrod|gray|green|greenyellow|grey|honeydew|hotpink|indianred|indigo|ivory|khaki|lavender|lavenderblush|lawngreen|lemonchiffon|lightblue|lightcoral|lightcyan|lightgoldenrodyellow|lightgray|lightgreen|lightgrey|lightpink|lightsalmon|lightseagreen|lightskyblue|lightslategray|lightslategrey|lightsteelblue|lightyellow|lime|limegreen|linen|magenta|maroon|mediumaquamarine|mediumblue|mediumorchid|mediumpurple|mediumseagreen|mediumslateblue|mediumspringgreen|mediumturquoise|mediumvioletred|midnightblue|mintcream|mistyrose|moccasin|navajowhite|navy|oldlace|olive|olivedrab|orange|orangered|orchid|palegoldenrod|palegreen|paleturquoise|palevioletred|papayawhip|peachpuff|peru|pink|plum|powderblue|purple|rebeccapurple|red|rosybrown|royalblue|saddlebrown|salmon|sandybrown|seagreen|seashell|sienna|silver|skyblue|slateblue|slategray|slategrey|snow|springgreen|steelblue|tan|teal|thistle|tomato|turquoise|violet|wheat|white|whitesmoke|yellow|yellowgreen)(?![-\w])/i
const semanticColorPropertyPattern = /^(?:color|background(?:-(?:color|image))?|border(?:-(?:(?:top|right|bottom|left|block|inline)(?:-(?:start|end))?|(?:block|inline)-(?:start|end)))?(?:-color|-image(?:-source)?)?|outline(?:-color)?|box-shadow|text-shadow|text-decoration(?:-color)?|text-emphasis(?:-color)?|fill|stroke|caret-color|accent-color|column-rule(?:-color)?|scrollbar-color|-webkit-text-(?:fill|stroke)(?:-color)?)$/i
const rawZIndexDeclarationPattern = /z-index\s*:\s*([^;{}]+)/gi
const builtInCompatibilityAliases = [
  ['--catalog-legacy-primary', '--primary'],
  ['--catalog-legacy-primary-rgb', '--primary-rgb'],
  ['--catalog-legacy-primary-fg', '--primary-fg'],
  ['--catalog-legacy-primary-fg-strong', '--primary-fg-strong'],
]

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
  'assets/css/catalog.css': { rawHex: 5, legacyPrimary: 51 },
  'assets/css/detail.css': { rawHex: 20, legacyPrimary: 39 },
}

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
const stripImportant = (value) => value.replace(/\s*!important\s*$/i, '').trim()
const stripDataUrls = (value) => value.replace(/url\(\s*["']?data:[\s\S]*?["']?\s*\)/gi, '')
const stripUrlFunctions = (value) => value.replace(/url\(\s*(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^)]*)\s*\)/gi, '')

const isForcedColorsDeclaration = (source, index) => {
  const mediaStart = source.lastIndexOf('@media (forced-colors', index)
  const blockEnd = source.lastIndexOf('}', index)
  return mediaStart > blockEnd
}

const containsRawSemanticColor = (value, { includeHex = true } = {}) => {
  let candidate = stripUrlFunctions(stripDataUrls(stripImportant(value)))
    // Existing, named semantic fallbacks remain typed compatibility values;
    // arbitrary var(--name, raw) values are intentionally not exempt.
    .replace(/var\(\s*--(?:text-on-dark|secondary-fg-strong|error-light|accent-light)\s*,\s*#[0-9a-f]{3,8}\s*\)/gi, '')
    .replace(/\b(?:rgb|rgba)\s*\(\s*var\(\s*--[\w-]*rgb\s*\)\s*(?:[,/]\s*[\d.%\s]+)?\)/gi, '')
  // `color-mix(in oklab, var(--token) ...)` is a tokenized semantic blend;
  // only count color-mix when it contains an actual raw color component.
  const mixWithoutSpace = candidate.replace(/\bcolor-mix\s*\(\s*in\s+[^,]+,/i, 'color-mix(')
  if (/\bcolor-mix\s*\(/i.test(candidate) && !rawColorMixPattern.test(mixWithoutSpace)) {
    candidate = candidate.replace(/\bcolor-mix\s*\([^)]*\)/gi, '')
  }
  // A known named color is raw even inside a fallback or gradient. Function
  // names and token identifiers do not match this boundary-aware list.
  const rawNamedColor = cssNamedColorPattern.test(candidate)
  return (includeHex && rawCssHexPattern.test(candidate))
    || rawModernColorFunctionPattern.test(candidate)
    || rawModernRgbPattern.test(candidate)
    || rawColorMixPattern.test(candidate)
    || rawNamedColor
}

const removeApprovedCompatibilityAliases = (source, relativePath, registry = {}) => {
  if (relativePath !== 'assets/css/tri-region-color.css') return source
  const registryAliases = registry?.compatibility_aliases ?? []
  // Standalone ratchet fixtures intentionally copy only the checker and debt
  // manifest. Keep their documented bootstrap aliases measurable without
  // making the production registry optional when it is available.
  const hasRegistry = registry && typeof registry === 'object' && Object.keys(registry).length > 0
  const approvedCompatibilityAliases = new Map((hasRegistry ? registryAliases : builtInCompatibilityAliases.map(([alias, canonical]) => ({ alias, canonical })))
    .filter((entry) => hasRegistry
      ? isValidCompatibilityAlias(entry) && entry.allowed_files.some((allowedPath) => pathMatches(relativePath, allowedPath))
      : entry?.alias && entry?.canonical)
    .map((entry) => [entry.alias, entry.canonical]))

  return source.replace(customPropertyDeclarationPattern, (declaration, property, value) => {
    const approvedTarget = approvedCompatibilityAliases.get(property)
    if (!approvedTarget) return declaration
    return value.replace(/\s+/g, '') === `var(${approvedTarget})` ? '' : declaration
  })
}

export const countLegacyPrimaryUsages = (source, relativePath, registry = {}) => {
  const normalizedSource = removeApprovedCompatibilityAliases(stripCssComments(source), relativePath, registry)
  return countMatches(normalizedSource, legacyPrimaryPattern)
}

const walkSourceFiles = (directory) => {
  if (!existsSync(directory)) return []
  const files = []
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (['node_modules', '.output', '.nuxt', '.tmp', 'tests', 'docs'].includes(entry.name)) continue
    const path = resolve(directory, entry.name)
    if (entry.isDirectory()) files.push(...walkSourceFiles(path))
    else if (/\.(?:css|vue|ts|mjs)$/.test(entry.name)) files.push(path)
  }
  return files
}

/**
 * Machine-readable debt summary used by the design/legal contract tests.
 * Existing primitive/scene values are classified by file and exemption; only
 * new semantic declarations or stacking values outside the registry are debt.
 */
const loadTokenRegistry = () => {
  const registryPath = resolve(appRoot, '..', 'config/ui-token-registry.json')
  try { return JSON.parse(readFileSync(registryPath, 'utf8')) } catch { return null }
}

const productionRegistryPath = resolve(appRoot, '..', 'config/ui-token-registry.json')
const builtInSemanticTokenNames = new Set([
  '--color-brand', '--color-brand-rgb', '--color-canvas', '--color-surface',
  '--color-surface-raised', '--color-surface-subtle', '--color-text',
  '--color-text-muted', '--color-border', '--color-action', '--color-action-rgb',
  '--color-action-hover', '--color-action-border', '--color-error', '--color-error-rgb',
  '--color-success', '--color-success-rgb', '--color-warning', '--color-warning-rgb',
  '--primary', '--primary-dark', '--primary-light', '--primary-fg', '--secondary',
  '--secondary-dark', '--secondary-fg', '--accent', '--accent-dark', '--accent-light',
  '--accent-text', '--river-rgb', '--ink-rgb', '--black-rgb', '--white-rgb',
])
let cachedSemanticTokenNames

const reviewedPrimitiveNames = (source, registry) => {
  const suffix = registry?.semantic_authority?.primitive_suffix
  if (typeof suffix !== 'string' || !suffix.trim()) return new Set()
  const escapedSuffix = suffix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const pattern = new RegExp(`^--[\\w-]+${escapedSuffix}$`)
  return new Set([...stripCssComments(source).matchAll(customPropertyDeclarationPattern)]
    .filter((match) => isGlobalCustomPropertyDeclaration(stripCssComments(source), match.index ?? 0) && pattern.test(match[1]))
    .map((match) => match[1]))
}

const loadSemanticTokenNames = () => {
  if (cachedSemanticTokenNames) return cachedSemanticTokenNames
  const names = new Set(builtInSemanticTokenNames)
  try {
    const variables = readFileSync(resolve(appRoot, 'assets/css/variables.css'), 'utf8')
    for (const match of variables.matchAll(/(--[\w-]+)\s*:/g)) names.add(match[1])
  } catch {
    // Standalone ratchet fixtures use the conservative built-in set.
  }
  cachedSemanticTokenNames = names
  return names
}

const hasUnknownSemanticVariable = (value, knownNames = loadSemanticTokenNames()) => {
  const candidate = stripUrlFunctions(stripDataUrls(stripImportant(value)))
  return [...candidate.matchAll(/var\(\s*(--[\w-]+)\b/gi)]
    .some((match) => !knownNames.has(match[1]))
}

const isGlobalCustomPropertyDeclaration = (source, index) => {
  const blockStart = source.lastIndexOf('{', index)
  const blockEnd = source.lastIndexOf('}', index)
  if (blockStart < 0 || blockStart < blockEnd) return true
  const selector = source.slice(blockEnd + 1, blockStart).trim()
  return /(?:^|[,{\s])(?::root|html|body)(?:[\s,{>]|$)/i.test(selector)
}

const declaredCustomPropertyNames = (source, { allowGlobal = false } = {}) => {
  const normalizedSource = stripCssComments(source)
  return new Set([
    ...[...normalizedSource.matchAll(customPropertyDeclarationPattern)]
      .filter((match) => allowGlobal || !isGlobalCustomPropertyDeclaration(normalizedSource, match.index ?? 0))
      .map((match) => match[1]),
    // Vue inline style bindings can declare a custom property without a CSS
    // declaration (for example `{ '--int-rgb': tint }`).
    ...[...normalizedSource.matchAll(/["'](--[\w-]+)["']\s*:/g)].map((match) => match[1]),
  ])
}

const normalizeRegistryPath = (value) => String(value ?? '').replaceAll('\\', '/').replace(/^web-nuxt\//, '')
const pathMatches = (candidate, allowed) => {
  const normalizedCandidate = normalizeRegistryPath(candidate)
  if (String(allowed ?? '').replaceAll('\\', '/') === 'web-nuxt') {
    return /^(?:assets|components|composables|layouts|middleware|pages|plugins|scripts|utils)(?:\/|$)/.test(normalizedCandidate)
  }
  const normalizedAllowed = normalizeRegistryPath(allowed).replace(/\/$/, '')
  return normalizedCandidate === normalizedAllowed || normalizedCandidate.startsWith(`${normalizedAllowed}/`)
}

const isValidExpiry = (value) => {
  if (typeof value !== 'string' || !/^20\d{2}-\d{2}-\d{2}$/.test(value)) return false
  const parsed = new Date(`${value}T23:59:59.999Z`)
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value
}

const isActiveExpiry = (value) => isValidExpiry(value) && new Date(`${value}T23:59:59.999Z`).getTime() >= Date.now()

const isValidCompatibilityAlias = (entry) => isPlainObject(entry)
  && typeof entry.alias === 'string' && /^--[\w-]+$/.test(entry.alias)
  && typeof entry.canonical === 'string' && /^--[\w-]+$/.test(entry.canonical)
  && typeof entry.owner === 'string' && entry.owner.trim().length > 0
  && isActiveExpiry(entry.expiry)
  && Array.isArray(entry.allowed_files)
  && entry.allowed_files.length > 0
  && entry.allowed_files.every((path) => typeof path === 'string'
    && /^(?:web-nuxt)(?:\/|$)/.test(path.replaceAll('\\', '/'))
    && path.replaceAll('\\', '/') !== 'web-nuxt'
    && isRootContained(normalizeRegistryPath(path)))

export const validateProductionRegistry = (registry) => {
  if (!isPlainObject(registry)) return ['registry must be a plain object']
  const errors = []
  if (!Number.isInteger(registry.version) || registry.version < 1) {
    errors.push('registry version must be a positive integer')
  }
  if (registry.canonical_semantic_prefix !== '--color-') {
    errors.push('registry canonical_semantic_prefix must be --color-')
  }
  if (!isPlainObject(registry.semantic_authority)
    || typeof registry.semantic_authority.owner !== 'string'
    || !registry.semantic_authority.owner.trim()
    || typeof registry.semantic_authority.source !== 'string'
    || !registry.semantic_authority.source.trim()
    || !/^(?:web-nuxt)(?:\/|$)/.test(registry.semantic_authority.source.replaceAll('\\', '/'))
    || registry.semantic_authority.source.replaceAll('\\', '/') === 'web-nuxt'
    || !isRootContained(normalizeRegistryPath(registry.semantic_authority.source))
    || !existsSync(resolve(appRoot, normalizeRegistryPath(registry.semantic_authority.source)))
    || typeof registry.semantic_authority.rule !== 'string'
    || !registry.semantic_authority.rule.trim()
    || typeof registry.semantic_authority.primitive_suffix !== 'string'
    || !/^-[\w-]+$/.test(registry.semantic_authority.primitive_suffix)) {
    errors.push('registry semantic_authority is incomplete')
  }
  if (!isPlainObject(registry.state_tokens)
    || Object.values(registry.state_tokens).some((value) => typeof value !== 'string' || !value.trim())) {
    errors.push('registry state_tokens must contain non-empty string values')
  }
  if (registry.admin_density !== 'dense-workbench') {
    errors.push('registry admin_density must be dense-workbench')
  }
  if (!isPlainObject(registry.z_layers)
    || Object.values(registry.z_layers).some((value) => !Number.isInteger(value))) {
    errors.push('registry z_layers must contain only integer values')
  } else {
    const requiredLayers = ['base', 'rel', 'dropdown', 'floating', 'sticky', 'mobile_nav', 'mobile_nav_backdrop', 'mobile_nav_top', 'nav', 'command_palette', 'overlay', 'overlay_raised', 'overlay_top', 'drawer', 'modal', 'modal_high', 'lightbox', 'toast', 'skip_link']
    const missingLayers = requiredLayers.filter((name) => !Object.hasOwn(registry.z_layers, name))
    if (missingLayers.length) errors.push(`registry z_layers missing required layers: ${missingLayers.join(',')}`)
    if (!Array.isArray(registry.z_layer_order)
      || registry.z_layer_order.length !== Object.keys(registry.z_layers).length
      || new Set(registry.z_layer_order).size !== registry.z_layer_order.length
      || registry.z_layer_order.some((name) => typeof name !== 'string' || !Object.hasOwn(registry.z_layers, name))) {
      errors.push('registry z_layer_order must list every z_layers key exactly once')
    } else {
      for (let index = 1; index < registry.z_layer_order.length; index += 1) {
        const previous = registry.z_layers[registry.z_layer_order[index - 1]]
        const current = registry.z_layers[registry.z_layer_order[index]]
        if (current < previous) {
          errors.push('registry z_layer_order must follow non-decreasing z-layer values')
          break
        }
      }
    }
  }
  if (!Array.isArray(registry.compatibility_aliases)) {
    errors.push('registry compatibility_aliases must be an array')
  } else {
    const aliases = new Set()
    registry.compatibility_aliases.forEach((entry, index) => {
      if (!isValidCompatibilityAlias(entry)) errors.push(`registry compatibility_aliases[${index}] is malformed`)
      if (isPlainObject(entry) && typeof entry.alias === 'string') {
        if (aliases.has(entry.alias)) errors.push(`registry compatibility_aliases[${index}] duplicates alias ${entry.alias}`)
        aliases.add(entry.alias)
      }
    })
    const aliasMap = new Map(registry.compatibility_aliases
      .filter((entry) => isPlainObject(entry) && typeof entry.alias === 'string' && typeof entry.canonical === 'string')
      .map((entry) => [entry.alias, entry.canonical]))
    for (const [alias] of aliasMap) {
      const seen = new Set([alias])
      let target = aliasMap.get(alias)
      while (target && aliasMap.has(target)) {
        if (seen.has(target)) {
          errors.push(`registry compatibility_aliases contains alias cycle at ${alias}`)
          break
        }
        seen.add(target)
        target = aliasMap.get(target)
      }
      if (target && !loadSemanticTokenNames().has(target) && !aliasMap.has(target)) {
        errors.push(`registry compatibility_aliases canonical target is unknown: ${target}`)
      }
    }
  }
  for (const key of ['semantic_value_exemptions', 'z_index_exemptions']) {
    if (!Array.isArray(registry[key])) {
      errors.push(`registry ${key} must be an array`)
      continue
    }
    registry[key].forEach((entry, index) => {
      const validPath = isPlainObject(entry) && typeof entry.path === 'string' && isRootContained(normalizeRegistryPath(entry.path))
      const validMetadata = isPlainObject(entry)
        && ['type', 'reason'].every((field) => typeof entry[field] === 'string' && entry[field].trim().length > 0)
        && (key === 'z_index_exemptions'
          ? ['decorative-scene', 'local-stack', 'forced-colors'].includes(entry.type)
          : ['decorative-scene', 'media-scrim', 'semantic-ui', 'forced-colors'].includes(entry.type))
      const validValues = key !== 'z_index_exemptions' || (Array.isArray(entry.values) && entry.values.every((value) => Number.isInteger(value)))
      if (!validPath || !validMetadata || !validValues) errors.push(`registry ${key}[${index}] is malformed`)
    })
  }
  return errors
}

const registryLayerValues = (registry) => {
  const values = Object.values(registry?.z_layers ?? {})
  return new Set(values.filter((value) => Number.isInteger(value)))
}

const registryPathExemption = (registry, relativePath, key) => (registry?.[key] ?? [])
  .filter((entry) => isPlainObject(entry) && typeof entry.path === 'string' && pathMatches(relativePath, entry.path))

const typedSemanticExemptionAllows = (value, property, exemption) => {
  const type = exemption?.type
  if (!['decorative-scene', 'media-scrim', 'semantic-ui', 'forced-colors'].includes(type)) return false
  const candidate = stripUrlFunctions(stripDataUrls(stripImportant(value)))
  // Scene/scrim exemptions cover opacity layers and token-backed RGB channels;
  // they do not permit a new functional palette value or arbitrary fallback.
  const approvedFallbacksRemoved = candidate.replace(/var\(\s*--(?:text-on-dark|secondary-fg-strong|error-light|accent-light)\s*,\s*#[0-9a-f]{3,8}\s*\)/gi, '')
  if (/var\(\s*--[\w-]+\s*,\s*(?:#|(?:rgb|rgba|hsl|hsla|hwb|oklch|oklab|lab|lch|color)\s*\(|(?:red|white|black|blue|green|orange|purple|yellow)\b)/i.test(approvedFallbacksRemoved)) return false
  if (/\b(?:hsl|hsla|hwb|oklch|oklab|lab|lch|color)\s*\(/i.test(approvedFallbacksRemoved)) return false
  if (/[#][0-9a-f]{3,8}\b/i.test(approvedFallbacksRemoved)) return false
  if (cssNamedColorPattern.test(approvedFallbacksRemoved)) return false
  if (/\brgb\s*\(/i.test(approvedFallbacksRemoved) && !/\brgba\s*\(\s*var\(\s*--[\w-]*rgb\b/i.test(approvedFallbacksRemoved)
    && !/\brgb\s*\(\s*var\(\s*--[\w-]*rgb\b/i.test(approvedFallbacksRemoved)) return false
  // Keep the argument explicit so future exemption entries cannot become a
  // path-wide bypass merely by matching a file.
  return typeof property === 'string' && property.length > 0
}

/** Scan one source string; exported for focused contract regressions. */
export const scanSourceTokenDebt = (source, relativePath = '', registry = loadTokenRegistry(), { includeDirect = true, knownSemanticVariables: providedSemanticVariables } = {}) => {
  let unregisteredSemanticColors = 0
  let rawZIndexOutsideAllowlist = 0
  const knownLayers = registryLayerValues(registry)
  const knownLayerNames = new Set(Object.keys(registry?.z_layers ?? {}).map((name) => `--z-${name.replaceAll('_', '-')}`))
  if (relativePath === 'assets/css/variables.css') return { unregisteredSemanticColors: 0, rawZIndexOutsideAllowlist: 0 }
  const normalizedSource = stripCssComments(source)
  // Component styles routinely declare private aliases (for example
  // `--card-ink`) beside the rule that consumes them. Keep those aliases
  // valid without turning an undeclared `var(--evil)` into an exemption.
  const knownSemanticVariables = new Set([
    ...loadSemanticTokenNames(),
    ...(providedSemanticVariables ?? []),
    ...declaredCustomPropertyNames(normalizedSource),
    ...reviewedPrimitiveNames(normalizedSource, registry),
  ])
  const directExemptions = registryPathExemption(registry, relativePath, 'semantic_value_exemptions')
  const zIndexExemptions = registryPathExemption(registry, relativePath, 'z_index_exemptions')
  for (const declaration of normalizedSource.matchAll(customPropertyDeclarationPattern)) {
    if (/^--color-/.test(declaration[1])
      && (containsRawSemanticColor(declaration[2]) || hasUnknownSemanticVariable(declaration[2], knownSemanticVariables))) {
      unregisteredSemanticColors += 1
    }
  }
  // Token-backed RGB blends are the existing primitive transport. Any raw
  // color left in a semantic declaration (including shorthands) is debt.
  for (const declaration of includeDirect ? normalizedSource.matchAll(cssDeclarationPattern) : []) {
    const property = declaration[1]
    const value = stripImportant(declaration[2])
    if (!semanticColorPropertyPattern.test(property)) continue
    const withoutTokenRgb = value.replace(/\b(?:rgb|rgba)\s*\(\s*var\(\s*--[\w-]*rgb\s*\)\s*(?:[,/]\s*[^)]*)?\)/gi, '')
    const rawFallback = /var\(\s*--[\w-]+\s*,\s*(?:#[0-9a-f]{3,8}\b|(?:rgb|rgba|hsl|hsla|hwb|oklch|oklab|lab|lch|color)\s*\((?!\s*var\(\s*--[\w-]*rgb\b))/i.test(value)
    const unknownSemanticVariable = hasUnknownSemanticVariable(value, knownSemanticVariables)
    // Typed scene/scrim exemptions may keep functional transport values, but
    // never mask a direct primitive/name or unapproved var fallback on a
    // semantic property (for example `color: red !important`).
    const exemption = directExemptions.find((entry) => typedSemanticExemptionAllows(value, property, entry))
    if (!isForcedColorsDeclaration(normalizedSource, declaration.index)
      && (unknownSemanticVariable || (!exemption && (rawFallback || containsRawSemanticColor(withoutTokenRgb))))) {
      unregisteredSemanticColors += 1
    }
  }
  for (const match of normalizedSource.matchAll(rawZIndexDeclarationPattern)) {
    const value = stripImportant(match[1])
    const tokenReferences = [...value.matchAll(/var\(\s*(--[\w-]+)\b/gi)].map((entry) => entry[1])
    if (value.toLowerCase() === 'auto') continue
    if (tokenReferences.some((token) => !knownLayerNames.has(token))) {
      rawZIndexOutsideAllowlist += 1
      continue
    }
    const tokenReference = value.match(/^var\(\s*(--z-[\w-]+)\s*\)$/i)
    if (tokenReference) {
      if (!knownLayerNames.has(tokenReference[1])) rawZIndexOutsideAllowlist += 1
      continue
    }
    if (/^-?\d+$/.test(value)) {
      const number = Number(value)
      const exemptNumber = zIndexExemptions.some((entry) => Array.isArray(entry.values) && entry.values.includes(number))
      if (!knownLayers.has(number) && !exemptNumber) rawZIndexOutsideAllowlist += 1
      continue
    }
    // Only an exact registered token is safe. Fallbacks and arithmetic can
    // resolve to an unregistered layer at runtime and therefore fail closed.
    rawZIndexOutsideAllowlist += 1
  }
  return { unregisteredSemanticColors, rawZIndexOutsideAllowlist }
}

export const scanTokenDebt = () => {
  let unregisteredSemanticColors = 0
  let rawZIndexOutsideAllowlist = 0
  const sourceFiles = walkSourceFiles(appRoot)
  const registry = loadTokenRegistry()

  // The production scanner is only trustworthy with a complete registry. A
  // missing or malformed authority must fail closed instead of silently
  // falling back to standalone fixture aliases.
  // Ratchet tests copy this checker into an isolated temporary fixture without
  // the repository registry. The real Nuxt source root is named `web-nuxt`;
  // only that production invocation fails closed when the authority is absent.
  const isProductionSourceRoot = basename(appRoot) === 'web-nuxt' && existsSync(resolve(appRoot, 'package.json'))
  if (isProductionSourceRoot && (!existsSync(productionRegistryPath) || validateProductionRegistry(registry).length > 0)) {
    return { unregisteredSemanticColors: 1, rawZIndexOutsideAllowlist: 1 }
  }

  // Build one declaration index so a token declared by the shared theme or a
  // companion stylesheet is recognised by consumers in another file.
  const declaredSemanticVariables = new Set(loadSemanticTokenNames())
  for (const filePath of sourceFiles) {
    const source = readFileSync(filePath, 'utf8')
    const relativePath = relative(appRoot, filePath).replaceAll('\\', '/')
    for (const name of declaredCustomPropertyNames(source)) {
      declaredSemanticVariables.add(name)
    }
    // These two files are the reviewed authorities for cross-file scene
    // aliases; their root-scoped declarations are intentionally consumable by
    // page/component styles. Arbitrary root declarations elsewhere remain
    // debt and cannot self-authorise a token.
    if (relativePath === 'assets/css/tri-region-color.css' || relativePath === 'assets/css/home-nocturne.css') {
      for (const name of declaredCustomPropertyNames(source, { allowGlobal: true })) {
        declaredSemanticVariables.add(name)
      }
    }
  }

  for (const filePath of sourceFiles) {
    const relativePath = relative(appRoot, filePath).replaceAll('\\', '/')
    const source = readFileSync(filePath, 'utf8')
    // variables.css is the canonical semantic authority and may contain the
    // primitive fallback values that semantic tokens point to. Parse actual
    // custom-property declarations so comments and fixture strings do not
    // become false positives.
    const debt = scanSourceTokenDebt(source, relativePath, registry, {
      includeDirect: true,
      knownSemanticVariables: declaredSemanticVariables,
    })
    unregisteredSemanticColors += debt.unregisteredSemanticColors
    rawZIndexOutsideAllowlist += debt.rawZIndexOutsideAllowlist
  }

  return { unregisteredSemanticColors, rawZIndexOutsideAllowlist }
}

const fail = (message) => {
  console.error(`tri-region color debt: FAIL - ${message}`)
  process.exitCode = 1
}

const runCli = () => {
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
    legacyPrimary: countLegacyPrimaryUsages(source, relativePath, loadTokenRegistry()),
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

const tokenDebt = scanTokenDebt()
console.log(`computed token debt: semantic ${tokenDebt.unregisteredSemanticColors}, z-index ${tokenDebt.rawZIndexOutsideAllowlist}`)
if (tokenDebt.unregisteredSemanticColors > 0 || tokenDebt.rawZIndexOutsideAllowlist > 0) {
  failed = true
}

  if (failed) {
    fail('budget exceeded or scoped file missing')
  } else {
    console.log('tri-region color debt: PASS')
  }
}

const invokedPath = process.argv[1] ? resolve(process.argv[1]) : ''
if (invokedPath === fileURLToPath(import.meta.url)) runCli()
