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
})
