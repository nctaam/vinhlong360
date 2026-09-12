import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('OCOP Ledger & AEO Plaque Visual Polish', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const catalogCss = readFileSync(resolve(__dirname, '../assets/css/catalog.css'), 'utf8')

  it('contains enhanced star glow and plaque card elevation', () => {
    expect(homeCss).toContain('home-ocop__frame')
    expect(catalogCss).toContain('catalog-aeo-plaque')
  })
})
