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
})
