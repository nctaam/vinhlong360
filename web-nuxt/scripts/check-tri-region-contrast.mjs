import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const css = readFileSync(resolve(process.cwd(), 'assets/css/variables.css'), 'utf8')
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

const actionSurfaceWeight = readMixWeight('color-action-surface')
const actionBorderWeight = readMixWeight('color-action-border')

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function readMixWeight(name) {
  const escaped = escapeRegExp(name)
  const match = new RegExp(
    `--${escaped}:\\s*color-mix\\(in srgb, var\\(--color-action\\)\\s+([0-9.]+)%, transparent\\)\\s*;`,
    'i',
  ).exec(css)
  if (!match) throw new Error(`Missing sRGB color-mix contract for --${name}`)
  return Number(match[1]) / 100
}

function readHexToken(name) {
  const escaped = escapeRegExp(name)
  const match = new RegExp(`--${escaped}:\\s*(#[0-9a-f]{6})\\s*;`, 'i').exec(css)
  if (!match) throw new Error(`Missing sRGB fallback for --${name}`)
  return hexToSrgb(match[1])
}

function readOklchToken(name) {
  const escaped = escapeRegExp(name)
  const match = new RegExp(
    `--${escaped}:\\s*oklch\\(\\s*([0-9.]+)%\\s+([0-9.]+)\\s+([0-9.]+)\\s*\\)\\s*;`,
    'i',
  ).exec(css)
  if (!match) throw new Error(`Missing OKLCH runtime value for --${name}`)
  return oklchToSrgb(Number(match[1]) / 100, Number(match[2]), Number(match[3]))
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
  return foreground.map((channel, index) => channel * weight + background[index] * (1 - weight))
}

let failed = false
function audit(name, foreground, background, threshold) {
  const ratio = contrastRatio(foreground, background)
  console.log(`${name} ${ratio.toFixed(2)} ${threshold.toFixed(1)}`)
  if (ratio < threshold) failed = true
}

function auditTokenPairs(format, readToken) {
  const suffix = format === 'srgb' ? '' : `-${format}`
  for (const [name, foregroundToken, backgroundToken, threshold] of pairs) {
    audit(`${name}${suffix}`, readToken(foregroundToken), readToken(backgroundToken), threshold)
  }

  for (const [theme, actionToken, canvasToken] of [
    ['light', 'river-600', 'alluvial-paper'],
    ['dark', 'night-river', 'night-canvas'],
  ]) {
    const action = readToken(actionToken)
    const canvas = readToken(canvasToken)
    const surface = composite(action, canvas, actionSurfaceWeight)
    // CSS backgrounds paint beneath translucent borders, so audit the rendered border against its tinted surface.
    const border = composite(action, surface, actionBorderWeight)
    audit(`control-border-${theme}-${format}`, border, surface, 3)
  }
}

auditTokenPairs('srgb', readHexToken)
auditTokenPairs('oklch', readOklchToken)

if (failed) process.exitCode = 1
