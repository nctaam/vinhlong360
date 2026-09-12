import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Mekong Terroir Resilience & Astronomical Tide Integrity', () => {
  const briefingVue = readFileSync(resolve(__dirname, '../components/home/HomeLocalBriefing.vue'), 'utf8')

  it('incorporates authentic lunar calendar calculation for Mekong river tides', () => {
    expect(briefingVue).toContain("import { solarToLunar } from '~/composables/useLunar'")
    expect(briefingVue).toMatch(/const\s+tidePhase\s*=\s*computed/)
    expect(briefingVue).toContain('Kỳ Nước rong')
    expect(briefingVue).toContain('Kỳ Nước kém')
    expect(briefingVue).toContain('Kỳ Nước chuyển')
  })

  it('renders authentic folk wisdom rule for river tides in the template', () => {
    expect(briefingVue).toContain('home-local-briefing__tide')
    expect(briefingVue).toMatch(/Nước rong rằm (&|&amp;) mùng một, nước kém mùng bảy (&|&amp;) hăm ba/)
  })

  it('strictly adheres to CLAUDE.md §1.7 unavailable policy (no empty frames or fake data)', () => {
    expect(briefingVue).toContain("v-if=\"reading.status !== 'unavailable'\"")
  })
})
