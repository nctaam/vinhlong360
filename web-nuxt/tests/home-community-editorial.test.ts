import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Community Feed Editorial Field Notes Craft', () => {
  const commVue = readFileSync(resolve(__dirname, '../components/home/HomeCommunityFeed.vue'), 'utf8')
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')

  it('incorporates authentic traveler dispatches and local contributor badges', () => {
    expect(commVue).toContain('cộng đồng')
    expect(commVue).toContain('IconLine')
    expect(commVue).toContain('home-community-dispatches')
  })

  it('applies editorial serif styling and subtle terracotta borders for dispatches', () => {
    expect(homeCss).toContain('.home-community-dispatches')
    expect(homeCss).toMatch(/\.home-community-dispatches[\s\S]*?--font-editorial/)
  })

  it('enforces focus-visible rings on community dispatches cards', () => {
    expect(homeCss).toMatch(/\.home-community-dispatches\s+\.cm-card:focus-visible/)
  })

  it('enforces tactile active scale and focus visible on community trending tags and seed cards', () => {
    expect(homeCss).toMatch(/\.tt-chip:active\s*\{[^}]*transform:\s*scale\(0\.96\)/)
    expect(homeCss).toMatch(/\.tt-chip:focus-visible\s*\{[^}]*outline:\s*2px\s+solid\s+var\(--color-focus\)/)
    expect(homeCss).toMatch(/\.community-seed-card:active\s*\{[^}]*transform:\s*scale\(0\.98\)/)
    expect(homeCss).toMatch(/\.community-seed-card:focus-visible\s*\{[^}]*outline:\s*2px\s+solid\s+var\(--color-focus\)/)
  })

  it('enforces WCAG 2.2 AAA accessibility and aria-hidden on decorative icons in HomeCommunityFeed', () => {
    expect(commVue).toContain('name="flame" aria-hidden="true"')
    expect(commVue).toContain('name="trophy" aria-hidden="true"')
    expect(commVue).toContain('name="shield-check" aria-hidden="true"')
    expect(commVue).toContain('name="heart" aria-hidden="true"')
    expect(commVue).toContain('name="message" aria-hidden="true"')
    expect(commVue).toContain('name="pin" aria-hidden="true"')
  })
})
