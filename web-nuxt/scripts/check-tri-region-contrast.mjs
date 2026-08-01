import { readdirSync, readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { relative, resolve } from 'node:path'
import { parse as parseVueSfc } from 'vue/compiler-sfc'

const auditProjectRoot = process.cwd()
const auditScriptRoot = resolve(import.meta.dirname, '..')
const appRequire = createRequire(import.meta.url)
const appPackage = readJsonFile(resolve(auditScriptRoot, 'package.json'), 'application package.json')
validateDirectToolchainDependency(appPackage, 'nuxt')
validateDirectToolchainDependency(appPackage, 'vue')
const nuxtPackagePath = resolveRequiredPackage(appRequire, 'nuxt/package.json', 'direct Nuxt dependency')
const nuxtPackage = readJsonFile(nuxtPackagePath, 'Nuxt package.json')
validatePackageMajor('nuxt', nuxtPackage.version, 4)
const nuxtRequire = createRequire(nuxtPackagePath)
const postcssTool = loadNuxtTool('postcss', 8)
const selectorParserTool = loadNuxtTool('postcss-selector-parser', 7)
const postcss = postcssTool.module.default ?? postcssTool.module
const selectorParser = selectorParserTool.module.default ?? selectorParserTool.module
const vuePackagePath = resolveRequiredPackage(appRequire, 'vue/package.json', 'direct Vue dependency')
const vuePackage = readJsonFile(vuePackagePath, 'Vue package.json')
validatePackageMajor('vue/compiler-sfc', vuePackage.version, 3)

if (process.env.TRI_REGION_AUDIT_TOOLCHAIN === '1') {
  console.log(`audit-toolchain nuxt@${nuxtPackage.version} vue/compiler-sfc@${vuePackage.version} postcss@${postcssTool.version} postcss-selector-parser@${selectorParserTool.version}`)
}

const allStyleSources = loadAllStyleSources(auditProjectRoot)
const styleSourceByName = new Map(allStyleSources.map(entry => [entry.source, entry]))
const variablesSource = readStyleSource(styleSourceByName, 'assets/css/variables.css')
const homeSource = readStyleSource(styleSourceByName, 'assets/css/home-nocturne.css')
const css = variablesSource.css
const variablesRoot = variablesSource.root
const homeRoot = homeSource.root
const pairs = [
  ['body-light', 'mekong-ink', 'alluvial-paper', 7],
  ['muted-light', 'mekong-muted', 'alluvial-paper', 4.5],
  ['action-light', 'river-600', 'alluvial-paper', 4.5],
  ['on-action-light', 'surface-white', 'river-600', 4.5],
  ['brand-light', 'mangthit-600', 'alluvial-paper', 4.5],
  ['verified-light', 'orchard-600', 'alluvial-paper', 4.5],
  ['warning-light', 'harvest-700', 'alluvial-paper', 4.5],
  ['error-light', 'coral-error', 'alluvial-paper', 4.5],
  ['body-dark', 'night-text', 'night-canvas', 7],
  ['action-dark', 'night-river', 'night-canvas', 4.5],
  ['on-action-dark', 'night-canvas', 'night-river', 4.5],
  ['brand-dark', 'night-clay', 'night-canvas', 4.5],
  ['verified-dark', 'night-leaf', 'night-canvas', 4.5],
  ['warning-dark', 'night-amber', 'night-canvas', 4.5],
  ['error-dark', 'night-error', 'night-canvas', 4.5],
]

const homeRootSelector = '[data-home-pilot="nocturne-b1"]'
const homeLightSelector = '.light [data-home-pilot="nocturne-b1"]'
const protectedHomeRootNames = new Set([
  'home-color-amber-text',
  'home-color-amber-surface',
  'home-color-focus-on-action',
  'home-color-focus-on-media',
  'home-color-focus-on-media-halo',
  'home-color-on-media-text',
  'home-color-on-media-plate',
  'home-color-today-text',
  'home-color-today-surface',
])
const protectedHomeLightNames = new Set(['home-color-focus-on-media'])
const homeRootRule = readUniqueTopLevelRule(homeRoot, homeRootSelector)
const homeLightRule = readUniqueTopLevelRule(homeRoot, homeLightSelector)
validateProtectedHomeDeclarations(allStyleSources, homeRootRule, homeLightRule)
const actionSurfaceWeight = readMixWeight('color-action-surface', variablesRoot)
const actionBorderWeight = readMixWeight('color-action-border', variablesRoot)
const homeAmberSurfaceWeight = readMixWeight(
  'home-color-amber-surface',
  homeRootRule,
  'color-material-amber',
)
const homeTodaySurfaceWeight = readMixWeight(
  'home-color-today-surface',
  homeRootRule,
  'color-error',
)
const homeOnMediaPlateAlpha = readRgbaAlpha(
  'home-color-on-media-plate',
  homeRootRule,
  'black-rgb',
)
const supportedSemanticAliases = new Set([
  'color-action',
  'color-mask-opaque',
  'color-on-action',
  'color-focus',
  'color-text',
  'color-warning',
  'surface-white',
])
const homeAmberTextAlias = readSemanticAlias(homeRootRule, 'home-color-amber-text')
const homeFocusActionAlias = readSemanticAlias(homeRootRule, 'home-color-focus-on-action')
const homeFocusMediaAlias = readSemanticAlias(homeRootRule, 'home-color-focus-on-media')
const homeFocusMediaLightAlias = readSemanticAlias(homeLightRule, 'home-color-focus-on-media')
const homeFocusMediaHaloAlias = readSemanticAlias(homeRootRule, 'home-color-focus-on-media-halo')
const homeOnMediaTextAlias = readSemanticAlias(homeRootRule, 'home-color-on-media-text')
const homeTodayTextAlias = readSemanticAlias(homeRootRule, 'home-color-today-text')
const whiteRgb = readRgbTuple('white-rgb')
const blackRgb = readRgbTuple('black-rgb')
const semanticNames = pairs.map(([name]) => name)
const expectedAuditNames = new Set([
  ...semanticNames,
  ...semanticNames.map(name => `${name}-oklch`),
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
])
const fallbackRootRule = readFirstTopLevelRule(variablesRoot, ':root')
const darkRule = readFirstTopLevelRule(variablesRoot, '.dark')
const darkOklchRule = readFinalNestedRule(
  variablesRoot,
  'supports',
  '(color: oklch(0% 0 0))',
  '.dark',
)

function readJsonFile(path, label) {
  let source
  try {
    source = readFileSync(path, 'utf8')
  }
  catch (error) {
    throw new Error(`Unable to read ${label} at ${path}: ${error.message}`)
  }
  try {
    return JSON.parse(source)
  }
  catch (error) {
    throw new Error(`Invalid ${label} at ${path}: ${error.message}`)
  }
}

function validateDirectToolchainDependency(packageJson, name) {
  if (!packageJson.dependencies?.[name]) {
    throw new Error(`Audit toolchain requires ${name} as a direct application dependency`)
  }
}

function resolveRequiredPackage(requireFrom, id, label) {
  try {
    return requireFrom.resolve(id)
  }
  catch (error) {
    throw new Error(`Unable to resolve ${label} (${id}): ${error.message}`)
  }
}

function validatePackageMajor(name, version, expectedMajor) {
  const major = Number.parseInt(String(version).split('.')[0], 10)
  if (!Number.isInteger(major) || major !== expectedMajor) {
    throw new Error(`Unsupported ${name} version ${version}; expected major ${expectedMajor}`)
  }
}

function loadNuxtTool(name, expectedMajor) {
  const modulePath = resolveRequiredPackage(nuxtRequire, name, `Nuxt audit tool ${name}`)
  const packagePath = resolveRequiredPackage(nuxtRequire, `${name}/package.json`, `${name} package metadata`)
  const nodeModulesRoot = resolve(nuxtPackagePath, '../..').replaceAll('\\', '/').toLowerCase()
  const normalizedModulePath = resolve(modulePath).replaceAll('\\', '/').toLowerCase()
  if (!normalizedModulePath.startsWith(`${nodeModulesRoot}/`) && normalizedModulePath !== nodeModulesRoot) {
    throw new Error(`Resolved ${name} outside the direct Nuxt toolchain: ${modulePath}`)
  }
  const packageJson = readJsonFile(packagePath, `${name} package.json`)
  validatePackageMajor(name, packageJson.version, expectedMajor)
  try {
    return { module: nuxtRequire(name), version: packageJson.version, path: modulePath }
  }
  catch (error) {
    throw new Error(`Unable to load Nuxt audit tool ${name} from ${modulePath}: ${error.message}`)
  }
}

function readRequiredText(path, source) {
  try {
    return readFileSync(path, 'utf8')
  }
  catch (error) {
    throw new Error(`Unable to read audit source ${source}: ${error.message}`)
  }
}

function listFilesRecursively(directory, extension) {
  let entries
  try {
    entries = readdirSync(directory, { withFileTypes: true })
  }
  catch (error) {
    throw new Error(`Unable to enumerate audit directory ${directory}: ${error.message}`)
  }
  entries.sort((left, right) => left.name < right.name ? -1 : left.name > right.name ? 1 : 0)
  const files = []
  for (const entry of entries) {
    const path = resolve(directory, entry.name)
    if (entry.isDirectory()) files.push(...listFilesRecursively(path, extension))
    else if (entry.isFile() && entry.name.endsWith(extension)) files.push(path)
  }
  return files
}

function sourceName(projectRoot, path) {
  return relative(projectRoot, path).replaceAll('\\', '/')
}

function parseVueStyles(source, from) {
  let parsed
  try {
    parsed = parseVueSfc(source, { filename: from })
  }
  catch (error) {
    throw new Error(`Unable to parse Vue SFC ${from}: ${error.message}`)
  }
  if (parsed.errors.length > 0) {
    const message = parsed.errors.map(error => error instanceof Error ? error.message : String(error)).join('; ')
    throw new Error(`Invalid Vue SFC ${from}: ${message}`)
  }
  return parsed.descriptor.styles.map((style, index) => {
    if (style.lang && style.lang !== 'css') {
      throw new Error(`Unsupported style language in ${from}#style-${index}: ${style.lang}`)
    }
    const styleSource = `${from}#style-${index}`
    return { source: styleSource, css: style.content, root: parseStylesheet(style.content, styleSource) }
  })
}

function loadAllStyleSources(projectRoot) {
  const sources = []
  for (const path of listFilesRecursively(resolve(projectRoot, 'assets/css'), '.css')) {
    const source = sourceName(projectRoot, path)
    const content = readRequiredText(path, source)
    sources.push({ source, css: content, root: parseStylesheet(content, source) })
  }
  for (const directory of ['pages', 'components']) {
    for (const path of listFilesRecursively(resolve(projectRoot, directory), '.vue')) {
      const source = sourceName(projectRoot, path)
      sources.push(...parseVueStyles(readRequiredText(path, source), source))
    }
  }
  return sources
}

function readStyleSource(sourceMap, source) {
  const entry = sourceMap.get(source)
  if (!entry) throw new Error(`Missing required audit source: ${source}`)
  return entry
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function normalizeCssPrelude(value) {
  return value.replace(/\s+/g, ' ').trim()
}

function isCssHexDigit(character) {
  return Boolean(character) && /[0-9a-f]/i.test(character)
}

function isCssWhitespace(character) {
  return character === ' ' || character === '\t' || character === '\n'
    || character === '\r' || character === '\f'
}

function decodeCssIdentifierEscape(source, start) {
  const first = source[start + 1]
  if (!first || first === '\n' || first === '\r' || first === '\f') {
    throw new Error('Invalid CSS identifier escape')
  }

  if (!isCssHexDigit(first)) {
    if (first.codePointAt(0) === 0) throw new Error('Invalid CSS identifier escape')
    return { value: first, end: start + 2 }
  }

  let end = start + 1
  while (end < source.length && end < start + 7 && isCssHexDigit(source[end])) end += 1
  const codePoint = Number.parseInt(source.slice(start + 1, end), 16)
  if (codePoint === 0 || codePoint > 0x10FFFF || (codePoint >= 0xD800 && codePoint <= 0xDFFF)) {
    throw new Error('Invalid CSS identifier escape')
  }
  if (isCssWhitespace(source[end])) {
    if (source[end] === '\r' && source[end + 1] === '\n') end += 2
    else end += 1
  }
  return { value: String.fromCodePoint(codePoint), end }
}

function canonicalizeCssIdentifier(source) {
  let value = ''
  for (let index = 0; index < source.length;) {
    if (source[index] !== '\\') {
      if (source[index].codePointAt(0) === 0) throw new Error('Invalid CSS identifier escape')
      value += source[index]
      index += 1
      continue
    }
    const decoded = decodeCssIdentifierEscape(source, index)
    value += decoded.value
    index = decoded.end
  }
  return value
}

function parseStylesheet(source, from) {
  try {
    return postcss.parse(source, { from })
  }
  catch (error) {
    throw new Error(`Unable to parse audit stylesheet ${from}: ${error.message}`)
  }
}

function isInsideRelationalFilter(node) {
  for (let parent = node.parent; parent; parent = parent.parent) {
    if (parent.type !== 'pseudo') continue
    const name = parent.value.toLowerCase()
    if (name === ':not' || name === ':has') return true
  }
  return false
}

function readSelector(selector) {
  const classes = new Set()
  const actionRoles = new Set()
  const normalized = selectorParser((root) => {
    root.walkClasses((node) => {
      if (!isInsideRelationalFilter(node)) classes.add(node.value)
    })
    root.walkAttributes((node) => {
      if (isInsideRelationalFilter(node)) return
      if (node.attribute !== 'data-color-role') return
      const value = String(node.value ?? '').replace(/^['"]|['"]$/g, '')
      if (value === 'action-primary' || value === 'action-secondary') actionRoles.add(value)
    })
  }).processSync(selector, { lossless: false })
  return { selector: normalized, classes, actionRoles }
}

function readRuleChain(node) {
  const rules = []
  for (let parent = node.parent; parent && parent.type !== 'root'; parent = parent.parent) {
    if (parent.type === 'rule') rules.unshift(parent)
  }
  return rules
}

function readAtRuleContext(node) {
  const contexts = []
  for (let parent = node.parent; parent && parent.type !== 'root'; parent = parent.parent) {
    if (parent.type === 'atrule') {
      contexts.unshift(normalizeCssPrelude(`@${parent.name} ${parent.params}`))
    }
  }
  return contexts.length === 0 ? 'top level' : contexts.join(' > ')
}

function readSelectorChain(node) {
  const classes = new Set()
  const actionRoles = new Set()
  const selectors = readRuleChain(node).map((rule) => {
    const parsed = readSelector(rule.selector)
    for (const className of parsed.classes) classes.add(className)
    for (const role of parsed.actionRoles) actionRoles.add(role)
    return parsed.selector
  })
  return { selector: selectors.join(' -> '), classes, actionRoles }
}

function readUniqueTopLevelRule(root, selector) {
  const normalizedSelector = readSelector(selector).selector
  const matches = root.nodes.filter(node => node.type === 'rule'
    && readSelector(node.selector).selector === normalizedSelector)
  const marker = `${selector} {`
  if (matches.length === 0) throw new Error(`Missing CSS block: ${marker}`)
  if (matches.length > 1) throw new Error(`Duplicate CSS block: ${marker}`)
  return matches[0]
}

function readFirstTopLevelRule(root, selector) {
  const normalizedSelector = readSelector(selector).selector
  const match = root.nodes.find(node => node.type === 'rule'
    && readSelector(node.selector).selector === normalizedSelector)
  if (!match) throw new Error(`Missing CSS block: ${selector} {`)
  return match
}

function readFinalNestedRule(root, atRuleName, atRuleParams, selector) {
  const atRules = root.nodes.filter(node => node.type === 'atrule'
    && node.name === atRuleName && normalizeCssPrelude(node.params) === atRuleParams)
  const finalAtRule = atRules.at(-1)
  if (!finalAtRule) throw new Error('Missing final OKLCH runtime block')
  const normalizedSelector = readSelector(selector).selector
  const match = finalAtRule.nodes?.find(node => node.type === 'rule'
    && readSelector(node.selector).selector === normalizedSelector)
  if (!match) throw new Error(`Missing CSS block: ${selector} {`)
  return match
}

function canonicalDeclarationName(declaration) {
  const name = canonicalizeCssIdentifier(declaration.prop)
  if (name.startsWith('--home-color-') && !/^--[a-z0-9-]+$/.test(name)) {
    throw new Error(`Invalid protected custom property name: ${name}`)
  }
  return name
}

function findDeclarations(container, name) {
  const declarations = []
  container.walkDecls((declaration) => {
    if (canonicalDeclarationName(declaration) === `--${name}`) declarations.push(declaration)
  })
  return declarations
}

function declarationCountError(name, count) {
  const prefix = count === 0 ? 'Missing' : 'Duplicate'
  if (name === 'home-color-on-media-plate') return `${prefix} rgba ${count === 0 ? 'contract' : 'declaration'} for --${name}`
  if (name === 'home-color-amber-surface' || name === 'home-color-today-surface') {
    return `${prefix} ${count === 0 ? 'sRGB color-mix contract' : 'color-mix declaration'} for --${name}`
  }
  return `${prefix} semantic alias assignment for --${name}`
}

function validateApprovedDeclarationCounts(rule, names) {
  for (const name of names) {
    const count = findDeclarations(rule, name).filter(declaration => declaration.parent === rule).length
    if (count !== 1) throw new Error(declarationCountError(name, count))
  }
}

function validateProtectedHomeDeclarations(sources, rootRule, lightRule) {
  const protectedNames = new Set([...protectedHomeRootNames, ...protectedHomeLightNames])
  for (const { source, root } of sources) {
    root.walkDecls((declaration) => {
      const canonicalName = canonicalDeclarationName(declaration)
      if (!canonicalName.startsWith('--')) return
      const name = canonicalName.slice(2)
      if (!protectedNames.has(name)) return
      const approved = (declaration.parent === rootRule && protectedHomeRootNames.has(name))
        || (declaration.parent === lightRule && protectedHomeLightNames.has(name))
      if (!approved) {
        const { selector } = readSelectorChain(declaration)
        throw new Error(`Unexpected protected declaration for --${name} in ${source} | ${selector} (${readAtRuleContext(declaration)})`)
      }
    })
  }
  validateApprovedDeclarationCounts(rootRule, protectedHomeRootNames)
  validateApprovedDeclarationCounts(lightRule, protectedHomeLightNames)
}

const protectedConsumerClasses = new Set([
  'hero-sub',
  'hero-nearby',
  'hero-search',
  'hero-action--soft',
  'home-feature-dossier__action',
  'home-feature-dossier__action--secondary',
  'ec-date',
  'ec-countdown',
  'ec-today',
])

function isProtectedConsumerProperty(property) {
  return property === 'all'
    || property === 'color'
    || property === '-webkit-text-fill-color'
    || property === 'opacity'
    || property === 'box-shadow'
    || property === 'text-shadow'
    || property === 'filter'
    || property === 'background'
    || property.startsWith('background-')
    || property === 'outline'
    || property.startsWith('outline-')
    || property === 'border'
    || property.startsWith('border-')
}

function consumerTupleKey(tuple) {
  return JSON.stringify(tuple)
}

const approvedConsumerTuples = new Set([
  ['assets/css/tri-region-color.css', 'top level', '[data-color-system="tri-region-v1"] [data-color-role="action-primary"]', 'border-color', 'var(--color-action)'],
  ['assets/css/tri-region-color.css', 'top level', '[data-color-system="tri-region-v1"] [data-color-role="action-primary"]', 'background', 'var(--color-action)'],
  ['assets/css/tri-region-color.css', 'top level', '[data-color-system="tri-region-v1"] [data-color-role="action-primary"]', 'color', 'var(--color-on-action)'],
  ['assets/css/tri-region-color.css', 'top level', '[data-color-system="tri-region-v1"] [data-color-role="action-secondary"]', 'border-color', 'var(--color-action-border)'],
  ['assets/css/tri-region-color.css', 'top level', '[data-color-system="tri-region-v1"] [data-color-role="action-secondary"]', 'background', 'var(--color-action-surface)'],
  ['assets/css/tri-region-color.css', 'top level', '[data-color-system="tri-region-v1"] [data-color-role="action-secondary"]', 'color', 'var(--color-action)'],
  ['assets/css/base.css', 'top level', '.hero-search input', 'border', '2px solid transparent'],
  ['assets/css/base.css', 'top level', '.hero-search input', 'border-radius', 'var(--radius-md)'],
  ['assets/css/base.css', 'top level', '.hero-search input:focus', 'outline', 'none'],
  ['assets/css/base.css', 'top level', '.hero-search input:focus', 'border-color', 'var(--accent)'],
  ['assets/css/base.css', 'top level', '.hero-search input:focus', 'box-shadow', '0 0 0 2px rgba(var(--accent-rgb), .4), inset 0 0 0 1.5px rgba(var(--accent-rgb), .2)'],
  ['assets/css/base.css', 'top level', '.hero-search button', 'border', 'none'],
  ['assets/css/base.css', 'top level', '.hero-search button', 'border-radius', 'var(--radius-md)'],
  ['assets/css/base.css', 'top level', '.hero-search button', 'background', 'var(--accent)'],
  ['assets/css/base.css', 'top level', '.hero-search button', 'color', 'var(--ink)'],
  ['assets/css/base.css', 'top level', '.hero-search button:hover', 'background', 'var(--accent-dark)'],
  ['assets/css/base.css', 'top level', '.hero-search button:hover', 'color', 'var(--ink)'],
  ['assets/css/base.css', 'top level', '.hero-search button:hover', 'box-shadow', '0 4px 20px rgba(var(--accent-rgb), .45)'],
  ['assets/css/base.css', 'top level', '.hero-search button:active', 'box-shadow', '0 2px 8px rgba(var(--accent-rgb), .3)'],
  ['assets/css/base.css', 'top level', '.hero-search button:focus-visible', 'outline', '2px solid var(--text-on-dark, #fff)'],
  ['assets/css/base.css', 'top level', '.hero-search button:focus-visible', 'outline-offset', '2px'],
  ['assets/css/base.css', 'top level', '.dark .hero-search input', 'background', 'var(--bg-alt)'],
  ['assets/css/base.css', 'top level', '.dark .hero-search input', 'color', 'var(--ink)'],
  ['assets/css/base.css', 'top level', '.dark .hero-search input', 'border-color', 'var(--line)'],
  ['assets/css/base.css', 'top level', '.dark .hero-search', 'border-color', 'var(--glass-border)'],
  ['assets/css/base.css', 'top level', '.dark .hero-search:focus-within', 'border-color', 'var(--primary-fg)'],
  ['assets/css/base.css', 'top level', '.dark .hero-search:focus-within', 'box-shadow', '0 0 0 3px rgba(var(--primary-rgb), .18)'],
  ['assets/css/dark-overrides.css', 'top level', '.dark .ec-countdown', 'color', 'var(--accent-text)'],
  ['assets/css/dark-overrides.css', 'top level', '.dark .ec-countdown', 'background', 'rgba(var(--accent-rgb), .12)'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-sub', 'opacity', '.95'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-sub', 'text-shadow', '0 1px 8px rgba(var(--black-rgb),.22)'],
  ['pages/index.vue#style-0', 'top level', '.dark .home .hero-sub', 'opacity', '1'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-search', 'background', 'rgba(var(--white-rgb),.14)'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-search', 'border', '.5px solid rgba(var(--white-rgb),.30)'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-search', 'border-radius', 'calc(var(--radius-md) + var(--space-1))'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-search', 'box-shadow', '0 8px 30px rgba(var(--black-rgb),.18), 0 2px 8px rgba(var(--black-rgb),.12)'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-search:focus-within', 'border-color', 'var(--color-focus)'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-search:focus-within', 'box-shadow', '0 12px 40px rgba(var(--black-rgb),.22), 0 0 0 4px color-mix(in srgb, var(--color-focus) 22%, transparent)'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-search input', 'border-color', 'transparent'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-search input', 'background', 'var(--card)'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-search input:focus', 'border-color', 'transparent'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-search input:focus', 'box-shadow', 'none'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-nearby', 'color', 'rgba(var(--white-rgb),.92)'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-nearby', 'text-shadow', '0 1px 6px rgba(var(--black-rgb),.35)'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-nearby:focus-visible', 'outline', '2px solid var(--color-focus)'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-nearby:focus-visible', 'outline-offset', '3px'],
  ['pages/index.vue#style-0', 'top level', '.home .hero-nearby:focus-visible', 'border-radius', '4px'],
  ['pages/index.vue#style-0', 'top level', '.ec-date', 'background', 'var(--home-color-amber-surface)'],
  ['pages/index.vue#style-0', 'top level', '.ec-date', 'border-radius', 'var(--radius-sm)'],
  ['pages/index.vue#style-0', 'top level', '.ec-date', 'color', 'var(--home-color-amber-text)'],
  ['pages/index.vue#style-0', 'top level', '.ec-countdown', 'color', 'var(--home-color-amber-text)'],
  ['pages/index.vue#style-0', 'top level', '.ec-countdown', 'background', 'var(--home-color-amber-surface)'],
  ['pages/index.vue#style-0', 'top level', '.ec-countdown', 'border-radius', 'var(--radius-full)'],
  ['pages/index.vue#style-0', 'top level', '.ec-today', 'color', 'var(--color-error)'],
  ['pages/index.vue#style-0', 'top level', '.dark .home .hero-search', 'background', 'rgba(var(--white-rgb),.22)'],
  ['pages/index.vue#style-0', 'top level', '.dark .home .hero-search', 'border-color', 'rgba(var(--white-rgb),.38)'],
  ['pages/index.vue#style-0', 'top level', '.dark .home .hero-search input', 'background', 'var(--bg-warm)'],
  ['pages/index.vue#style-0', 'top level', '.dark .home .hero-search input', 'color', 'var(--ink)'],
  ['pages/index.vue#style-0', 'top level', '.dark .home .hero-search input::placeholder', 'color', 'rgba(var(--white-rgb),.50)'],
  ['pages/index.vue#style-0', 'top level', '.dark .home .hero-search:focus-within', 'border-color', 'var(--color-focus)'],
  ['pages/index.vue#style-0', 'top level', '.dark .ec-today', 'color', 'var(--color-error)'],
  ['pages/index.vue#style-0', '@media (prefers-reduced-transparency: reduce)', '.home .hero-search', 'background', 'rgba(var(--black-rgb),.35)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-sub', 'background', 'var(--home-color-on-media-plate)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-sub', 'color', 'var(--home-color-on-media-text)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-sub', 'opacity', '1'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-search[data-color-role="action-primary"]', 'border-color', 'var(--color-action)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-search[data-color-role="action-primary"]', 'background', 'var(--color-action)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-search[data-color-role="action-primary"]', 'color', 'var(--color-on-action)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-search[data-color-role="action-primary"]:focus-within', 'outline', '3px solid var(--home-color-focus-on-media)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-search[data-color-role="action-primary"]:focus-within', 'outline-offset', '3px'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-search[data-color-role="action-primary"]:focus-within', 'border-color', 'var(--color-action)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-search[data-color-role="action-primary"]:focus-within', 'box-shadow', '0 0 0 2px var(--home-color-focus-on-media-halo)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-nearby:focus-visible', 'outline', '3px solid var(--home-color-focus-on-media)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-nearby:focus-visible', 'outline-offset', '3px'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-nearby:focus-visible', 'box-shadow', '0 0 0 2px var(--home-color-focus-on-media-halo)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-search[data-color-role="action-primary"] input:focus-visible', 'outline', '3px solid var(--home-color-focus-on-action)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-search[data-color-role="action-primary"] input:focus-visible', 'outline-offset', '3px'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .hero-search[data-color-role="action-primary"] input:focus-visible', 'box-shadow', '0 0 0 2px var(--home-color-focus-on-media-halo)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .home-feature-dossier__action', 'border', '1px solid var(--color-action)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .home-feature-dossier__action', 'color', 'var(--color-action)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .home-feature-dossier__action--secondary', 'border-color', 'var(--color-border)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .home-feature-dossier__action--secondary', 'color', 'var(--color-text)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .home-feature-dossier__action[data-color-role="action-secondary"]', 'border-color', 'var(--color-action-border)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .home-feature-dossier__action[data-color-role="action-secondary"]', 'background', 'var(--color-action-surface)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .home-feature-dossier__action[data-color-role="action-secondary"]', 'color', 'var(--color-action)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .ec-date[data-material-accent="amber"],[data-home-pilot="nocturne-b1"] .ec-countdown[data-material-accent="amber"]', 'background', 'var(--home-color-amber-surface)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .ec-date[data-material-accent="amber"],[data-home-pilot="nocturne-b1"] .ec-countdown[data-material-accent="amber"]', 'color', 'var(--home-color-amber-text)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .ec-countdown.ec-today[data-material-accent="amber"]', 'background', 'var(--home-color-today-surface)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .ec-countdown.ec-today[data-material-accent="amber"]', 'color', 'var(--home-color-today-text)'],
  ['assets/css/home-nocturne.css', 'top level', '[data-home-pilot="nocturne-b1"] .ec-countdown.ec-today[data-material-accent="amber"]', 'box-shadow', 'inset 0 0 0 1px var(--color-error)'],
].map(consumerTupleKey))

function validateProtectedConsumerDeclarations(sources) {
  for (const { source, root } of sources) {
    root.walkDecls((declaration) => {
      const property = canonicalDeclarationName(declaration).toLowerCase()
      if (!isProtectedConsumerProperty(property)) return
      const { selector, classes, actionRoles } = readSelectorChain(declaration)
      const hasProtectedClass = [...classes].some(className => protectedConsumerClasses.has(className))
      if (!hasProtectedClass && actionRoles.size === 0) return
      const value = `${declaration.value.trim()}${declaration.important ? ' !important' : ''}`
      const tuple = [source, readAtRuleContext(declaration), selector, property, value]
      if (!approvedConsumerTuples.has(consumerTupleKey(tuple))) {
        throw new Error(`Unexpected protected consumer declaration: ${tuple.join(' | ')}`)
      }
    })
  }
}

validateProtectedConsumerDeclarations([
  ...allStyleSources,
])

function readFiniteNumber(value, label) {
  const number = Number(value)
  if (!Number.isFinite(number)) throw new Error(`Non-finite numeric value for ${label}`)
  return number
}

function readMixWeight(name, container, sourceToken = 'color-action') {
  const declarations = findDeclarations(container, name)
  if (declarations.length === 0) throw new Error(`Missing sRGB color-mix contract for --${name}`)
  if (declarations.length > 1) throw new Error(`Duplicate color-mix declaration for --${name}`)
  const match = /^color-mix\(\s*in\s+srgb\s*,\s*var\(\s*(.*?)\s*\)\s+([0-9.]+)%\s*,\s*transparent\s*\)$/i
    .exec(declarations[0].value.trim())
  if (!match || canonicalizeCssIdentifier(match[1]) !== `--${sourceToken}`) {
    throw new Error(`Missing sRGB color-mix contract for --${name}`)
  }
  const weight = readFiniteNumber(match[2], `--${name}`) / 100
  if (weight < 0 || weight > 1) throw new Error(`Out-of-range color-mix weight for --${name}`)
  return weight
}

function readRgbaAlpha(name, container, sourceToken) {
  const declarations = findDeclarations(container, name)
  if (declarations.length === 0) throw new Error(`Missing rgba contract for --${name}`)
  if (declarations.length > 1) throw new Error(`Duplicate rgba declaration for --${name}`)
  const match = /^rgba\(\s*var\(\s*(.*?)\s*\)\s*,\s*([0-9.]+)\s*\)$/i
    .exec(declarations[0].value.trim())
  if (!match || canonicalizeCssIdentifier(match[1]) !== `--${sourceToken}`) {
    throw new Error(`Missing rgba contract for --${name}`)
  }
  const alpha = readFiniteNumber(match[2], `--${name}`)
  if (alpha < 0 || alpha > 1) throw new Error(`Out-of-range rgba alpha for --${name}`)
  return alpha
}

function readSemanticAlias(container, name) {
  const declarations = findDeclarations(container, name).filter(declaration => declaration.parent === container)
  if (declarations.length === 0) throw new Error(`Missing semantic alias assignment for --${name}`)
  if (declarations.length > 1) throw new Error(`Duplicate semantic alias assignment for --${name}`)
  const match = /^var\(\s*(.*?)\s*\)$/i.exec(declarations[0].value.trim())
  if (!match || match[1].length === 0) {
    throw new Error(`Malformed semantic alias assignment for --${name}`)
  }
  const canonicalAlias = canonicalizeCssIdentifier(match[1])
  if (!canonicalAlias.startsWith('--')) throw new Error(`Malformed semantic alias assignment for --${name}`)
  const alias = canonicalAlias.slice(2)
  if (!supportedSemanticAliases.has(alias)) {
    throw new Error(`Unsupported semantic alias for --${name}: --${alias}`)
  }
  return alias
}

function readHexToken(name) {
  const escaped = escapeRegExp(name)
  const match = new RegExp(`--${escaped}:\\s*(#[0-9a-f]{6})\\s*;`, 'i').exec(css)
  if (!match) throw new Error(`Missing sRGB fallback for --${name}`)
  return hexToSrgb(match[1])
}

function readRgbTuple(name) {
  const escaped = escapeRegExp(name)
  const declarations = [...css.matchAll(new RegExp(
    `--${escaped}:\\s*([0-9.]+)\\s*,\\s*([0-9.]+)\\s*,\\s*([0-9.]+)\\s*;`,
    'gi',
  ))]
  if (declarations.length === 0) throw new Error(`Missing RGB tuple for --${name}`)
  if (declarations.length > 1) throw new Error(`Duplicate RGB tuple for --${name}`)
  return declarations[0].slice(1, 4).map((channel) => {
    const value = readFiniteNumber(channel, `--${name}`) / 255
    if (value < 0 || value > 1) throw new Error(`Out-of-range RGB tuple for --${name}`)
    return value
  })
}

function readOklchToken(name) {
  const escaped = escapeRegExp(name)
  const match = new RegExp(
    `--${escaped}:\\s*oklch\\(\\s*([0-9.]+)%\\s+([0-9.]+)\\s+([0-9.]+)\\s*\\)\\s*;`,
    'i',
  ).exec(css)
  if (!match) throw new Error(`Missing OKLCH runtime value for --${name}`)
  return oklchToSrgb(
    readFiniteNumber(match[1], `--${name} lightness`) / 100,
    readFiniteNumber(match[2], `--${name} chroma`),
    readFiniteNumber(match[3], `--${name} hue`),
  )
}

function readHexDeclaration(rule, name) {
  const declarations = findDeclarations(rule, name).filter(declaration => declaration.parent === rule)
  if (declarations.length !== 1 || !/^#[0-9a-f]{6}$/i.test(declarations[0].value.trim())) {
    throw new Error(`Missing sRGB declaration for --${name}`)
  }
  return hexToSrgb(declarations[0].value.trim())
}

function readOklchDeclaration(rule, name) {
  const declarations = findDeclarations(rule, name).filter(declaration => declaration.parent === rule)
  const match = declarations.length === 1
    ? /^oklch\(\s*([0-9.]+)%\s+([0-9.]+)\s+([0-9.]+)\s*\)$/i.exec(declarations[0].value.trim())
    : null
  if (!match) throw new Error(`Missing OKLCH declaration for --${name}`)
  return oklchToSrgb(
    readFiniteNumber(match[1], `--${name} lightness`) / 100,
    readFiniteNumber(match[2], `--${name} chroma`),
    readFiniteNumber(match[3], `--${name} hue`),
  )
}

function hexToSrgb(hex) {
  const value = Number.parseInt(hex.slice(1), 16)
  return [((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255]
}

function oklchToSrgb(lightness, chroma, hue) {
  const radians = hue * Math.PI / 180
  const a = chroma * Math.cos(radians)
  const b = chroma * Math.sin(radians)
  const lRoot = lightness + 0.3963377774 * a + 0.2158037573 * b
  const mRoot = lightness - 0.1055613458 * a - 0.0638541728 * b
  const sRoot = lightness - 0.0894841775 * a - 1.291485548 * b
  const l = lRoot ** 3
  const m = mRoot ** 3
  const s = sRoot ** 3
  const linear = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ]

  return linear.map((channel) => {
    const clipped = Math.min(1, Math.max(0, channel))
    return clipped <= 0.0031308
      ? 12.92 * clipped
      : 1.055 * clipped ** (1 / 2.4) - 0.055
  })
}

function relativeLuminance(color) {
  assertColor(color, 'relative luminance input')
  const channels = color.map((channel) => {
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

function contrastRatio(foreground, background) {
  const a = relativeLuminance(foreground)
  const b = relativeLuminance(background)
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)
}

function composite(foreground, background, weight) {
  assertColor(foreground, 'composite foreground')
  assertColor(background, 'composite background')
  if (!Number.isFinite(weight)) throw new Error('Non-finite composite weight')
  return foreground.map((channel, index) => channel * weight + background[index] * (1 - weight))
}

function assertColor(color, label) {
  if (color.length !== 3 || color.some(channel => !Number.isFinite(channel) || channel < 0 || channel > 1)) {
    throw new Error(`Invalid color channels for ${label}`)
  }
}

let failed = false
const auditedNames = new Set()
function auditRatio(name, ratio, threshold) {
  if (!expectedAuditNames.has(name)) throw new Error(`Unexpected audit: ${name}`)
  if (auditedNames.has(name)) throw new Error(`Duplicate audit: ${name}`)
  if (!Number.isFinite(threshold)) throw new Error(`Non-finite threshold for ${name}`)
  if (!Number.isFinite(ratio)) throw new Error(`Non-finite contrast ratio for ${name}`)
  console.log(`${name} ${ratio.toFixed(2)} ${threshold.toFixed(1)}`)
  auditedNames.add(name)
  if (ratio < threshold) failed = true
}

function audit(name, foreground, background, threshold) {
  assertColor(foreground, `${name} foreground`)
  assertColor(background, `${name} background`)
  auditRatio(name, contrastRatio(foreground, background), threshold)
}

function minimumDualRingContrast(firstRing, secondRing) {
  // The worst host luminance lies where the two ring contrast ratios intersect.
  return Math.sqrt(contrastRatio(firstRing, secondRing))
}

function minimumOverlayTextContrast(text, overlay, weight, hostExtremes) {
  return Math.min(...hostExtremes.map(host => contrastRatio(text, composite(overlay, host, weight))))
}

function auditSemanticPairs(format, readToken) {
  const suffix = format === 'srgb' ? '' : `-${format}`
  for (const [name, foregroundToken, backgroundToken, threshold] of pairs) {
    audit(`${name}${suffix}`, readToken(foregroundToken), readToken(backgroundToken), threshold)
  }
}

function controlThemes(format) {
  if (format === 'srgb') {
    return [
      {
        theme: 'light',
        action: readHexToken('river-600'),
        onAction: readHexToken('surface-white'),
        focus: readHexToken('river-600'),
        text: readHexToken('mekong-ink'),
        error: readHexToken('coral-error'),
        surfaceWhite: readHexToken('surface-white'),
        maskOpaque: readHexToken('mask-opaque'),
        warning: readHexToken('harvest-700'),
        materialAmber: readHexToken('harvest-600'),
        directContact: readHexDeclaration(fallbackRootRule, 'brand-zalo'),
        backgrounds: {
          canvas: readHexToken('alluvial-paper'),
          surface: readHexToken('surface-white'),
          subtle: readHexDeclaration(fallbackRootRule, 'color-surface-subtle'),
        },
      },
      {
        theme: 'dark',
        action: readHexToken('night-river'),
        onAction: readHexToken('night-canvas'),
        focus: readHexToken('night-amber'),
        text: readHexToken('night-text'),
        error: readHexToken('night-error'),
        surfaceWhite: readHexToken('surface-white'),
        maskOpaque: readHexToken('mask-opaque'),
        warning: readHexToken('night-amber'),
        materialAmber: readHexToken('night-amber'),
        directContact: readHexDeclaration(darkRule, 'brand-zalo'),
        backgrounds: {
          canvas: readHexToken('night-canvas'),
          surface: readHexToken('night-surface'),
          subtle: readHexDeclaration(darkRule, 'color-surface-subtle'),
        },
      },
    ]
  }

  return [
    {
      theme: 'light',
      action: readOklchToken('river-600'),
      onAction: readOklchToken('surface-white'),
      focus: readOklchToken('river-600'),
      text: readOklchToken('mekong-ink'),
      error: readOklchToken('coral-error'),
      surfaceWhite: readOklchToken('surface-white'),
      maskOpaque: readHexToken('mask-opaque'),
      warning: readOklchToken('harvest-700'),
      materialAmber: readOklchToken('harvest-600'),
      directContact: readHexDeclaration(fallbackRootRule, 'brand-zalo'),
      backgrounds: {
        canvas: readOklchToken('alluvial-paper'),
        surface: readOklchToken('surface-white'),
        // Parchment subtle remains an explicit sRGB semantic value in the runtime cascade.
        subtle: readHexDeclaration(fallbackRootRule, 'color-surface-subtle'),
      },
    },
    {
      theme: 'dark',
      action: readOklchToken('night-river'),
      onAction: readOklchToken('night-canvas'),
      focus: readOklchToken('night-amber'),
      text: readOklchToken('night-text'),
      error: readOklchToken('night-error'),
      surfaceWhite: readOklchToken('surface-white'),
      maskOpaque: readHexToken('mask-opaque'),
      warning: readOklchToken('night-amber'),
      materialAmber: readOklchToken('night-amber'),
      directContact: readHexDeclaration(darkRule, 'brand-zalo'),
      backgrounds: {
        canvas: readOklchToken('night-canvas'),
        surface: readOklchToken('night-surface'),
        subtle: readOklchDeclaration(darkOklchRule, 'color-surface-subtle'),
      },
    },
  ]
}

function resolveSemanticAlias(alias, theme) {
  const values = {
    'color-action': theme.action,
    'color-on-action': theme.onAction,
    'color-focus': theme.focus,
    'color-mask-opaque': theme.maskOpaque,
    'color-text': theme.text,
    'color-warning': theme.warning,
    'surface-white': theme.surfaceWhite,
  }
  const value = values[alias]
  if (!value) throw new Error(`Missing resolved value for semantic alias --${alias}`)
  return value
}

function auditControls(format) {
  for (const themeData of controlThemes(format)) {
    const {
      theme,
      action,
      onAction,
      focus,
      text,
      error,
      materialAmber,
      directContact,
      backgrounds,
    } = themeData
    audit(`filled-action-${theme}-${format}`, onAction, action, 4.5)
    audit(`direct-contact-zalo-${theme}-${format}`, onAction, directContact, 4.5)
    for (const [surfaceName, host] of Object.entries(backgrounds)) {
      const surface = composite(action, host, actionSurfaceWeight)
      // CSS backgrounds paint beneath translucent borders, so audit the rendered border against its tinted surface.
      const border = composite(action, surface, actionBorderWeight)
      audit(`control-border-${theme}-${surfaceName}-${format}`, border, surface, 3)
    }
    for (const [surfaceName, host] of Object.entries(backgrounds)) {
      audit(`focus-${theme}-${surfaceName}-${format}`, focus, host, 3)
    }
    const amberSurface = composite(materialAmber, backgrounds.canvas, homeAmberSurfaceWeight)
    const amberText = resolveSemanticAlias(homeAmberTextAlias, themeData)
    const focusAction = resolveSemanticAlias(homeFocusActionAlias, themeData)
    const focusMedia = resolveSemanticAlias(
      theme === 'light' ? homeFocusMediaLightAlias : homeFocusMediaAlias,
      themeData,
    )
    const focusMediaHalo = resolveSemanticAlias(homeFocusMediaHaloAlias, themeData)
    const onMediaText = resolveSemanticAlias(homeOnMediaTextAlias, themeData)
    const todayText = resolveSemanticAlias(homeTodayTextAlias, themeData)
    const todaySurface = composite(error, backgrounds.canvas, homeTodaySurfaceWeight)
    audit(`homepage-amber-text-${theme}-${format}`, amberText, amberSurface, 4.5)
    auditRatio(
      `homepage-on-media-text-${theme}-${format}`,
      minimumOverlayTextContrast(
        onMediaText,
        blackRgb,
        homeOnMediaPlateAlpha,
        [blackRgb, whiteRgb],
      ),
      4.5,
    )
    audit(`homepage-focus-action-${theme}-${format}`, focusAction, action, 3)
    auditRatio(
      `homepage-focus-media-${theme}-${format}`,
      minimumDualRingContrast(focusMedia, focusMediaHalo),
      3,
    )
    audit(`homepage-today-text-${theme}-${format}`, todayText, todaySurface, 4.5)
  }
}

auditSemanticPairs('srgb', readHexToken)
auditSemanticPairs('oklch', readOklchToken)
auditControls('srgb')
auditControls('oklch')

const missingAudits = [...expectedAuditNames].filter(name => !auditedNames.has(name))
if (missingAudits.length > 0 || auditedNames.size !== expectedAuditNames.size) {
  throw new Error(`Incomplete audit set: ${missingAudits.join(', ')}`)
}

if (failed) process.exitCode = 1
