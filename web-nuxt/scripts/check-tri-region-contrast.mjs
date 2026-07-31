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

function readHexToken(name) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = new RegExp(`--${escaped}:\\s*(#[0-9a-f]{6})\\s*;`, 'i').exec(css)
  if (!match) throw new Error(`Missing sRGB fallback for --${name}`)
  return match[1]
}

function hexToRgb(hex) {
  const value = Number.parseInt(hex.slice(1), 16)
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
}

function relativeLuminance(hex) {
  const channels = hexToRgb(hex).map((channel) => {
    const value = channel / 255
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

function contrastRatio(foreground, background) {
  const a = relativeLuminance(foreground)
  const b = relativeLuminance(background)
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)
}

let failed = false
for (const [name, foregroundToken, backgroundToken, threshold] of pairs) {
  const ratio = contrastRatio(readHexToken(foregroundToken), readHexToken(backgroundToken))
  console.log(`${name} ${ratio.toFixed(2)} ${threshold.toFixed(1)}`)
  if (ratio < threshold) failed = true
}

if (failed) process.exitCode = 1
