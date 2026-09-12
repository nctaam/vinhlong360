import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Homepage Editorial Layout Asymmetry & Terroir Craft', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const catVue = readFileSync(resolve(__dirname, '../components/home/HomeCategoryIndex.vue'), 'utf8')

  it('incorporates lead feature tile styling for primary category index', () => {
    expect(catVue).toContain('home-category-index__card--lead')
  })

  it('enforces asymmetric editorial grid layout for category exploration', () => {
    expect(homeCss).toContain('.home-category-index__card--lead')
    expect(homeCss).toMatch(/\.home-category-index__card--lead\s*\{[^}]*grid-column:\s*span\s*2/)
  })

  it('incorporates Mekong river hairline flow divider with alluvial gradient', () => {
    expect(homeCss).toContain('home-river-divider')
    expect(homeCss).toMatch(/\.home-river-divider\s*\{[^}]*background:[^;]*linear-gradient/)
  })

  it('preserves clean token discipline without AI SaaS neon purples or cyan', () => {
    expect(homeCss).not.toMatch(/#a855f7|#8b5cf6|#00f0ff/i)
  })
})
