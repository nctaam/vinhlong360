import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Home Hero & Feature Dossier Polish', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const dossierVue = readFileSync(resolve(__dirname, '../components/home/HomeFeatureDossier.vue'), 'utf8')
  const indexVue = readFileSync(resolve(__dirname, '../pages/index.vue'), 'utf8')

  it('enforces refined search shadow and dossier container styling', () => {
    expect(homeCss).toContain('--shadow-card-ambient')
    expect(homeCss).toContain('--radius-surface-refined')
    expect(dossierVue).toContain('home-feature-dossier')
  })

  it('strictly restricts Hero Dossier to destination/experience types and excludes dishes', () => {
    expect(indexVue).toContain('HERO_ELIGIBLE_TYPES')
    expect(indexVue).toContain("'attraction'")
    expect(indexVue).toContain("'experience'")
    expect(indexVue).toContain("'craft_village'")
    expect(indexVue).toContain("'nature'")
    // Must NOT include food/product in eligible types
    expect(indexVue).not.toMatch(/HERO_ELIGIBLE_TYPES\s*=\s*new Set\([^)]*'dish'/)
    expect(indexVue).not.toMatch(/HERO_ELIGIBLE_TYPES\s*=\s*new Set\([^)]*'product'/)
  })

  it('prioritizes iconic Vinh Long cultural heritage in Hero Dossier', () => {
    expect(indexVue).toContain('HERO_ICONIC_IDS')
    expect(indexVue).toContain('de-an-di-san-duong-dai-mang-thit')
    expect(indexVue).toContain('cu-lao-an-binh')
    expect(indexVue).toContain('cho-noi-tra-on')
    expect(indexVue).toContain('chua-tien-chau-tien-chau-tu')
    expect(indexVue).toContain('nha-gom-do-tu-buoi')
  })
})
