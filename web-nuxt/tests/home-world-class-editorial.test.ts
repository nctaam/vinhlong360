import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Homepage World-Class Editorial Benchmark & Anti-AI-Slop', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const dossierVue = readFileSync(resolve(__dirname, '../components/home/HomeFeatureDossier.vue'), 'utf8')
  const indexVue = readFileSync(resolve(__dirname, '../pages/index.vue'), 'utf8')

  it('incorporates authentic field geographic coordinates in hero feature dossier', () => {
    expect(dossierVue).toMatch(/10\.254°\s*N,\s*105\.972°\s*E|data-geo-coordinates/)
  })

  it('enforces asymmetric dual-rail editorial spread for signals section on desktop', () => {
    expect(homeCss).toContain('home-signals__grid')
    expect(homeCss).toMatch(/\.home-signals__grid\s*\{[^}]*display:\s*grid/)
  })

  it('employs fluid macro-rhythm breathability spacing for major sections', () => {
    expect(homeCss).toMatch(/padding-block:\s*clamp\([^)]*var\(--space-/)
  })

  it('eradicates generic AI copywriting buzzwords from homepage components', () => {
    const slopKeywords = ['nâng tầm trải nghiệm', 'hành trình vô tận', 'vẻ đẹp bất tận', 'khám phá không giới hạn']
    for (const kw of slopKeywords) {
      expect(indexVue.toLowerCase()).not.toContain(kw)
      expect(dossierVue.toLowerCase()).not.toContain(kw)
    }
  })
})
