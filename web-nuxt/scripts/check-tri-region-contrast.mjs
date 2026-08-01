import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const css = readFileSync(resolve(process.cwd(), 'assets/css/variables.css'), 'utf8')
const homeCss = readFileSync(resolve(process.cwd(), 'assets/css/home-nocturne.css'), 'utf8')
const parsedHomeCss = stripCssComments(homeCss)
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

const homeRootMarker = '[data-home-pilot="nocturne-b1"] {'
const homeLightMarker = '.light [data-home-pilot="nocturne-b1"] {'
const homeRootBlock = readUniqueCssBlock(parsedHomeCss, homeRootMarker)
const homeLightBlock = readUniqueCssBlock(parsedHomeCss, homeLightMarker)
const actionSurfaceWeight = readMixWeight('color-action-surface')
const actionBorderWeight = readMixWeight('color-action-border')
const homeAmberSurfaceWeight = readMixWeight(
  'home-color-amber-surface',
  parsedHomeCss,
  'color-material-amber',
)
const homeTodaySurfaceWeight = readMixWeight(
  'home-color-today-surface',
  parsedHomeCss,
  'color-error',
)
const homeOnMediaPlateAlpha = readRgbaAlpha(
  'home-color-on-media-plate',
  parsedHomeCss,
  'black-rgb',
)
const supportedSemanticAliases = new Set([
  'color-action',
  'color-mask-opaque',
  'color-on-action',
  'color-focus',
  'color-text',
  'surface-white',
])
const homeFocusActionAlias = readSemanticAlias(homeRootBlock, 'home-color-focus-on-action')
const homeFocusMediaAlias = readSemanticAlias(homeRootBlock, 'home-color-focus-on-media')
const homeFocusMediaLightAlias = readSemanticAlias(homeLightBlock, 'home-color-focus-on-media')
const homeFocusMediaHaloAlias = readSemanticAlias(homeRootBlock, 'home-color-focus-on-media-halo')
const homeOnMediaTextAlias = readSemanticAlias(homeRootBlock, 'home-color-on-media-text')
const homeTodayTextAlias = readSemanticAlias(homeRootBlock, 'home-color-today-text')
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
const fallbackRoot = readCssBlock(css, ':root {')
const darkBlock = readCssBlock(css, '\n.dark {')
const finalOklchSupport = css.lastIndexOf('@supports (color: oklch(0% 0 0))')
if (finalOklchSupport < 0) throw new Error('Missing final OKLCH runtime block')
const darkOklchBlock = readCssBlock(css, '\n  .dark {', finalOklchSupport)

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function stripCssComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//g, '')
}

function readCssBlock(source, marker, fromIndex = 0) {
  const start = source.indexOf(marker, fromIndex)
  if (start < 0) throw new Error(`Missing CSS block: ${marker}`)
  const open = source.indexOf('{', start)
  if (open < 0) throw new Error(`Missing opening brace: ${marker}`)

  return readCssBlockAt(source, open, marker)
}

function readCssBlockAt(source, open, marker) {
  if (source[open] !== '{') throw new Error(`Missing opening brace: ${marker}`)

  let depth = 0
  for (let index = open; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1
    if (source[index] === '}') depth -= 1
    if (depth === 0) return source.slice(open + 1, index)
  }

  throw new Error(`Missing closing brace: ${marker}`)
}

function readCssBlocks(source, marker) {
  const selector = marker.slice(0, marker.lastIndexOf('{')).trim()
  const blocks = []
  for (let open = 0; open < source.length; open += 1) {
    if (source[open] !== '{') continue
    let boundary = open - 1
    while (boundary >= 0 && !'{};'.includes(source[boundary])) boundary -= 1
    if (source.slice(boundary + 1, open).trim() === selector) {
      blocks.push(readCssBlockAt(source, open, marker))
    }
  }
  return blocks
}

function readUniqueCssBlock(source, marker) {
  const blocks = readCssBlocks(source, marker)
  if (blocks.length === 0) throw new Error(`Missing CSS block: ${marker}`)
  if (blocks.length > 1) throw new Error(`Duplicate CSS block: ${marker}`)
  return blocks[0]
}

function readFiniteNumber(value, label) {
  const number = Number(value)
  if (!Number.isFinite(number)) throw new Error(`Non-finite numeric value for ${label}`)
  return number
}

function readMixWeight(name, source = css, sourceToken = 'color-action') {
  const escaped = escapeRegExp(name)
  const escapedSourceToken = escapeRegExp(sourceToken)
  const declarations = [...source.matchAll(new RegExp(
    `--${escaped}:\\s*color-mix\\(in srgb, var\\(--${escapedSourceToken}\\)\\s+([0-9.]+)%, transparent\\)\\s*;`,
    'gi',
  ))]
  if (declarations.length === 0) throw new Error(`Missing sRGB color-mix contract for --${name}`)
  if (declarations.length > 1) throw new Error(`Duplicate color-mix declaration for --${name}`)
  const weight = readFiniteNumber(declarations[0][1], `--${name}`) / 100
  if (weight < 0 || weight > 1) throw new Error(`Out-of-range color-mix weight for --${name}`)
  return weight
}

function readRgbaAlpha(name, source, sourceToken) {
  const escaped = escapeRegExp(name)
  const escapedSourceToken = escapeRegExp(sourceToken)
  const declarations = [...source.matchAll(new RegExp(
    `--${escaped}:\\s*rgba\\(var\\(--${escapedSourceToken}\\),\\s*([0-9.]+)\\)\\s*;`,
    'gi',
  ))]
  if (declarations.length === 0) throw new Error(`Missing rgba contract for --${name}`)
  if (declarations.length > 1) throw new Error(`Duplicate rgba declaration for --${name}`)
  const alpha = readFiniteNumber(declarations[0][1], `--${name}`)
  if (alpha < 0 || alpha > 1) throw new Error(`Out-of-range rgba alpha for --${name}`)
  return alpha
}

function readSemanticAlias(block, name) {
  const escaped = escapeRegExp(name)
  const declarations = [...block.matchAll(new RegExp(`--${escaped}\\s*:\\s*([^;{}]*)(?:;|$)`, 'gi'))]
  if (declarations.length === 0) throw new Error(`Missing semantic alias assignment for --${name}`)
  if (declarations.length > 1) throw new Error(`Duplicate semantic alias assignment for --${name}`)
  const value = declarations[0][1].trim()
  const match = /^var\(--([\w-]+)\)$/.exec(value)
  if (!match) throw new Error(`Malformed semantic alias assignment for --${name}`)
  const alias = match[1]
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

function readHexDeclaration(block, name) {
  const escaped = escapeRegExp(name)
  const match = new RegExp(`--${escaped}:\\s*(#[0-9a-f]{6})\\s*;`, 'i').exec(block)
  if (!match) throw new Error(`Missing sRGB declaration for --${name}`)
  return hexToSrgb(match[1])
}

function readOklchDeclaration(block, name) {
  const escaped = escapeRegExp(name)
  const match = new RegExp(
    `--${escaped}:\\s*oklch\\(\\s*([0-9.]+)%\\s+([0-9.]+)\\s+([0-9.]+)\\s*\\)\\s*;`,
    'i',
  ).exec(block)
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
        amberText: readHexToken('harvest-700'),
        materialAmber: readHexToken('harvest-600'),
        directContact: readHexDeclaration(fallbackRoot, 'brand-zalo'),
        backgrounds: {
          canvas: readHexToken('alluvial-paper'),
          surface: readHexToken('surface-white'),
          subtle: readHexDeclaration(fallbackRoot, 'color-surface-subtle'),
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
        amberText: readHexToken('night-amber'),
        materialAmber: readHexToken('night-amber'),
        directContact: readHexDeclaration(darkBlock, 'brand-zalo'),
        backgrounds: {
          canvas: readHexToken('night-canvas'),
          surface: readHexToken('night-surface'),
          subtle: readHexDeclaration(darkBlock, 'color-surface-subtle'),
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
      amberText: readOklchToken('harvest-700'),
      materialAmber: readOklchToken('harvest-600'),
      directContact: readHexDeclaration(fallbackRoot, 'brand-zalo'),
      backgrounds: {
        canvas: readOklchToken('alluvial-paper'),
        surface: readOklchToken('surface-white'),
        // Parchment subtle remains an explicit sRGB semantic value in the runtime cascade.
        subtle: readHexDeclaration(fallbackRoot, 'color-surface-subtle'),
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
      amberText: readOklchToken('night-amber'),
      materialAmber: readOklchToken('night-amber'),
      directContact: readHexDeclaration(darkBlock, 'brand-zalo'),
      backgrounds: {
        canvas: readOklchToken('night-canvas'),
        surface: readOklchToken('night-surface'),
        subtle: readOklchDeclaration(darkOklchBlock, 'color-surface-subtle'),
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
      amberText,
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
    const focusAction = resolveSemanticAlias(homeFocusActionAlias, themeData)
    const focusMedia = resolveSemanticAlias(
      theme === 'light' ? homeFocusMediaLightAlias : homeFocusMediaAlias,
      themeData,
    )
    const focusMediaHalo = resolveSemanticAlias(homeFocusMediaHaloAlias, themeData)
    const onMediaText = resolveSemanticAlias(homeOnMediaTextAlias, themeData)
    const onMediaPlate = composite(blackRgb, backgrounds.canvas, homeOnMediaPlateAlpha)
    const todayText = resolveSemanticAlias(homeTodayTextAlias, themeData)
    const todaySurface = composite(error, backgrounds.canvas, homeTodaySurfaceWeight)
    audit(`homepage-amber-text-${theme}-${format}`, amberText, amberSurface, 4.5)
    audit(`homepage-on-media-text-${theme}-${format}`, onMediaText, onMediaPlate, 4.5)
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
