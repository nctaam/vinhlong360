import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('UI Tokens - Elevation & Tactile Depth', () => {
  const css = readFileSync(resolve(__dirname, '../assets/css/variables.css'), 'utf8')
  const darkCss = readFileSync(resolve(__dirname, '../assets/css/dark-overrides.css'), 'utf8')

  it('defines ambient shadow and elevation tokens in variables.css', () => {
    expect(css).toContain('--shadow-card-ambient:')
    expect(css).toContain('--shadow-card-hover:')
    expect(css).toContain('--radius-surface-refined:')
    expect(css).toContain('--radius-control-refined:')
  })

  it('provides dark mode ambient glow / depth equivalents in dark-overrides.css', () => {
    expect(darkCss).toContain('--shadow-card-ambient:')
    expect(darkCss).toContain('--shadow-card-hover:')
  })
})
