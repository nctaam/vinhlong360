import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import MapPage from '../pages/ban-do.vue'

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

describe('/ban-do — Outdoor ergonomics & Riverine/Pottery presets', () => {
  it('toggles outdoor high-contrast state on user click', async () => {
    const wrapper = await mountSuspended(MapPage, {
      route: '/ban-do',
      global: {
        stubs: {
          Breadcrumb: true,
          FilterChips: true,
          PageState: true,
          IconLine: true,
          MapListSurface: true,
        },
      },
    })
    wrappers.push(wrapper)

    const rootSection = wrapper.find('.page')
    expect(rootSection.attributes('data-outdoor-contrast')).toBe('normal')

    const contrastBtn = wrapper.find('.map-contrast-toggle')
    expect(contrastBtn.exists()).toBe(true)

    await contrastBtn.trigger('click')
    expect(rootSection.attributes('data-outdoor-contrast')).toBe('high')
    expect(contrastBtn.text()).toContain('Tương phản ngoài trời: BẬT')

    await contrastBtn.trigger('click')
    expect(rootSection.attributes('data-outdoor-contrast')).toBe('normal')
  })

  it('renders riverine, pottery and ferry quick presets', async () => {
    const wrapper = await mountSuspended(MapPage, {
      route: '/ban-do',
      global: {
        stubs: {
          Breadcrumb: true,
          FilterChips: true,
          PageState: true,
          IconLine: true,
          MapListSurface: true,
        },
      },
    })
    wrappers.push(wrapper)

    const presetButtons = wrapper.findAll('.map-quick-preset-btn')
    expect(presetButtons.length).toBe(3)
    expect(wrapper.text()).toContain('Cù lao & Ven sông')
    expect(wrapper.text()).toContain('Lò gốm Mang Thít')
    expect(wrapper.text()).toContain('Bến đò - Phà')
  })

  it('strictly adheres to design tokens with zero raw hex in ban-do.vue', () => {
    const filePath = resolve(__dirname, '../pages/ban-do.vue')
    const source = readFileSync(filePath, 'utf8')
    const styleMatch = source.match(/<style[^>]*>([\s\S]*?)<\/style>/)
    const styleContent = styleMatch ? styleMatch[1] : ''
    const rawHexPattern = /(?<![&w-])#[0-9a-fA-F]{3,8}\b/g
    const matches = styleContent.match(rawHexPattern) || []
    expect(matches).toEqual([])
  })
})
