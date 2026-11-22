import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Homepage Smart Terroir Elevation & Ergonomics', () => {
  const indexVue = readFileSync(resolve(__dirname, '../pages/index.vue'), 'utf8')
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const dossierVue = readFileSync(resolve(__dirname, '../components/home/HomeFeatureDossier.vue'), 'utf8')
  const briefingVue = readFileSync(resolve(__dirname, '../components/home/HomeLocalBriefing.vue'), 'utf8')

  it('renders clean architectural quick-links in the hero section', () => {
    expect(indexVue).toContain('hero-quick-index')
    expect(indexVue).toContain('hero-quick-link')
    expect(indexVue).not.toContain('hero-terroir-chips')
  })

  it('provides tactile active scale and smooth transition for hero quick links', () => {
    expect(homeCss).toContain('.hero-quick-link')
    expect(homeCss).toMatch(/\.hero-quick-link:active\s*\{[^}]*transform:\s*scale\(\s*0\.98\s*\)/)
  })

  it('removes decorative Terroir Heritage Stamp pill from the Feature Dossier', () => {
    expect(dossierVue).not.toContain('home-feature-dossier__stamp')
    expect(dossierVue).not.toContain('Thổ nhưỡng di sản')
  })

  it('incorporates traditional river tide guidance in the Local Briefing', () => {
    expect(briefingVue).toContain('home-local-briefing__tide')
    expect(briefingVue).toContain('Nhịp nước sông Cửu Long')
  })

  it('keeps hero search container unboxed and pairs crisp seasonal fruit note', () => {
    expect(homeCss).toMatch(/\[data-home-pilot="nocturne-b1"\]\s*\.hero-search-island/)
    expect(homeCss).toMatch(/\[data-home-pilot="nocturne-b1"\]\s*\.hero-season-note/)
  })

  it('enforces tactile active scale on hero nearby discovery link', () => {
    expect(homeCss).toMatch(/\[data-home-pilot="nocturne-b1"\]\s+\.hero-nearby:active\s*\{[^}]*transform:\s*scale\(0\.97\)/)
  })
})

