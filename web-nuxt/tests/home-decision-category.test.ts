import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Home Decision Ledger and Category Index', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')

  it('contains category hover micro-lift and decision ledger active styles', () => {
    expect(homeCss).toContain('.home-decision-ledger__link:hover')
    expect(homeCss).toContain('.home-category-index__primary-link:hover')
    expect(homeCss).toContain('--shadow-card-hover')
  })

  it('enforces haptic active feedback and spring snap transitions on interactive ledger and category elements', () => {
    expect(homeCss).toContain('.home-decision-ledger__link:active')
    expect(homeCss).toContain('transform: scale(0.98)')
    expect(homeCss).toContain('cubic-bezier(0.16, 1, 0.3, 1)')
  })

  it('eradicates generic AI-slop filler "Trải nghiệm phong phú" from category header', () => {
    const categoryVue = readFileSync(resolve(__dirname, '../components/home/HomeCategoryIndex.vue'), 'utf8')
    expect(categoryVue).not.toContain('Trải nghiệm phong phú')
    expect(categoryVue).toContain('Không gian bản địa')
  })
})
