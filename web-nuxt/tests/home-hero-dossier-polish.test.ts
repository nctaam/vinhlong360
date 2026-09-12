import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Home Hero & Feature Dossier Polish', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const dossierVue = readFileSync(resolve(__dirname, '../components/home/HomeFeatureDossier.vue'), 'utf8')

  it('enforces refined search shadow and dossier container styling', () => {
    expect(homeCss).toContain('--shadow-card-ambient')
    expect(homeCss).toContain('--radius-surface-refined')
    expect(dossierVue).toContain('home-feature-dossier')
  })
})
