import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Homepage Anti-AI-Slop Craftsmanship & Terroir Depth', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const ocopVue = readFileSync(resolve(__dirname, '../components/home/HomeOcopLedger.vue'), 'utf8')

  it('enforces tactile haptic depression (:active scale 0.98) on interactive cards and buttons', () => {
    expect(homeCss).toMatch(/transform:\s*scale\(\s*0\.98\s*\)/)
  })

  it('enforces weighted spring physics easing (cubic-bezier(0.16, 1, 0.3, 1))', () => {
    expect(homeCss).toContain('cubic-bezier(0.16, 1, 0.3, 1)')
  })

  it('incorporates subtle radar pulse indicator for nearby discovery action', () => {
    expect(homeCss).toContain('keyframes pulse')
    expect(homeCss).toContain('.hero-nearby')
  })

  it('incorporates Mang Thit terracotta subtle borders on category cards', () => {
    expect(homeCss).toMatch(/\.home-category-index__card\s*\{[^}]*border:[^;]*color-mix\(in srgb,\s*var\(--mangthit-/)
  })

  it('strictly bans AI SaaS neon purple and cyan colors', () => {
    const bannedColors = [
      /#a855f7/i,
      /#8b5cf6/i,
      /#d946ef/i,
      /#7c3aed/i,
      /#00f0ff/i,
      /#00ffff/i,
    ]
    for (const pattern of bannedColors) {
      expect(homeCss).not.toMatch(pattern)
    }
  })

  it('OCOP ledger enforces national OCOP standards without fabricated product listings', () => {
    expect(ocopVue).toContain('OCOP')
    expect(ocopVue).toContain('quốc gia')
    expect(ocopVue).toMatch(/3\s*sao|4\s*sao|5\s*sao/i)
  })

  it('eradicates AI sparkle icon from heritage stamp in HomeFeatureDossier', () => {
    const dossierVue = readFileSync(resolve(__dirname, '../components/home/HomeFeatureDossier.vue'), 'utf8')
    expect(dossierVue).not.toContain('name="sparkle"')
    expect(dossierVue).toMatch(/name="(flame|leaf)"/)
  })
})
