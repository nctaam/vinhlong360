import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Homepage Smart Terroir Elevation & Ergonomics', () => {
  const indexVue = readFileSync(resolve(__dirname, '../pages/index.vue'), 'utf8')
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const dossierVue = readFileSync(resolve(__dirname, '../components/home/HomeFeatureDossier.vue'), 'utf8')
  const briefingVue = readFileSync(resolve(__dirname, '../components/home/HomeLocalBriefing.vue'), 'utf8')

  it('renders contextual terroir search chips in the hero section', () => {
    expect(indexVue).toContain('hero-terroir-chips')
    expect(indexVue).toContain('Cù lao An Bình')
    expect(indexVue).toContain('Lò gạch Mang Thít')
  })

  it('provides haptic depression and spring physics for hero terroir chips', () => {
    expect(homeCss).toContain('.hero-terroir-chip')
    expect(homeCss).toMatch(/\.hero-terroir-chip:active\s*\{[^}]*transform:\s*scale\(\s*0\.96\s*\)/)
  })

  it('incorporates a Terroir Heritage Stamp in the Feature Dossier', () => {
    expect(dossierVue).toContain('home-feature-dossier__stamp')
    expect(dossierVue).toContain('Thổ nhưỡng di sản')
  })

  it('incorporates traditional river tide guidance in the Local Briefing', () => {
    expect(briefingVue).toContain('home-local-briefing__tide')
    expect(briefingVue).toContain('Nhịp nước sông Cửu Long')
  })
})
