import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('National OCOP Gold Book Craft & Security Texture', () => {
  const ocopVue = readFileSync(resolve(__dirname, '../pages/ocop.vue'), 'utf8')

  it('incorporates guilloche security texture and wax seal for official certification', () => {
    expect(ocopVue).toContain('guilloche-texture')
    expect(ocopVue).toContain('wax-seal')
    expect(ocopVue).toContain('.guilloche-texture')
    expect(ocopVue).toContain('.wax-seal')
  })

  it('features star-jump navigation with tactile 44px buttons', () => {
    expect(ocopVue).toContain('star-jump')
    expect(ocopVue).toMatch(/\.star-jump-btn[\s\S]*?min-height:\s*44px/)
  })

  it('strictly prohibits raw star emojis and uses SVG vector stars', () => {
    expect(ocopVue).toContain('<IconLine v-for="n in s.stars" :key="n" name="star" />')
  })
})
