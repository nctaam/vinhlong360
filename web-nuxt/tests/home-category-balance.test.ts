import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Home Category Index Balanced Editorial Layout', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const catVue = readFileSync(resolve(__dirname, '../components/home/HomeCategoryIndex.vue'), 'utf8')

  it('preserves lead card class while enforcing balanced desktop grid rules', () => {
    expect(catVue).toContain('home-category-index__card--lead')
    expect(homeCss).toContain('.home-category-index__card--lead')
    expect(homeCss).toMatch(/\.home-category-index__card--lead\s*\{[^}]*grid-column:\s*span\s*2/)
  })

  it('guarantees balanced 4-column desktop display without empty grid holes', () => {
    expect(homeCss).toContain('BALANCED 4-COLUMN DESKTOP CATEGORY ROW')
    expect(homeCss).toMatch(/@media\s*\(\s*min-width:\s*960px\s*\)[^{]*\{[\s\S]*?\.home-category-index__primary\s*\{[\s\S]*?grid-template-columns:\s*repeat\(\s*4\s*,\s*minmax\(0\s*,\s*1fr\)\s*\)/)
  })

  it('has smooth micro-transitions and elevated shadow on card hover', () => {
    expect(homeCss).toMatch(/\.home-category-index__primary-link:hover[\s\S]*?transform:\s*translateY\(-3px\)/)
    expect(homeCss).toMatch(/\.home-category-index__primary-link:hover\s+\.home-category-index__media-img[\s\S]*?scale\(1\.06\)/)
  })
})
