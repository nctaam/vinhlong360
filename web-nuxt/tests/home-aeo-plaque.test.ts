import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import HomeAeoPlaque from '../components/home/HomeAeoPlaque.vue'

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

async function mount() {
  const wrapper = await mountSuspended(HomeAeoPlaque, {
    global: { stubs: { IconLine: true, NuxtLink: true } },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('HomeAeoPlaque — Editorial Answer Plaque (AEO/GEO)', () => {
  it('renders with correct semantic landmarks and accessible attributes', async () => {
    const wrapper = await mount()
    const section = wrapper.find('[data-home-section="aeo-plaque"]')
    expect(section.exists()).toBe(true)
    expect(section.attributes('data-home-aeo-plaque')).toBeDefined()
    expect(section.attributes('aria-labelledby')).toBe('home-aeo-title')

    const title = wrapper.find('#home-aeo-title')
    expect(title.exists()).toBe(true)
    expect(title.text()).toContain('Cẩm nang du lịch theo mùa')
  })

  it('contains concise seasonal answers for water season and terracotta heritage', async () => {
    const wrapper = await mount()
    const text = wrapper.text()
    expect(text).toContain('Mùa nước nổi')
    expect(text).toContain('Cù Lao An Bình')
    expect(text).toContain('Mang Thít')
    expect(text).toContain('gốm')
  })

  it('provides a direct CTA navigation to seasonal guide /theo-mua', async () => {
    const wrapper = await mount()
    const cta = wrapper.find('[data-home-aeo-cta]')
    expect(cta.exists()).toBe(true)
    expect(cta.attributes('to')).toBe('/theo-mua')
  })

  it('strictly adheres to design token rules with zero raw hex colors', () => {
    const filePath = resolve(__dirname, '../components/home/HomeAeoPlaque.vue')
    const source = readFileSync(filePath, 'utf8')
    const rawHexPattern = /(?<![&\w-])#[0-9a-fA-F]{3,8}\b/g
    const matches = source.match(rawHexPattern) || []
    expect(matches).toEqual([])
  })
})
