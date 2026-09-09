import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import CatalogAeoPlaque from '../components/CatalogAeoPlaque.vue'

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

async function mount(props: any) {
  const wrapper = await mountSuspended(CatalogAeoPlaque, {
    props,
    global: { stubs: { IconLine: true, NuxtLink: true } },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('CatalogAeoPlaque — Reusable Hub Answer Plaque', () => {
  it('renders with accessible heading, custom kicker, and entries', async () => {
    const wrapper = await mount({
      title: 'Cẩm nang 3 vùng Mekong',
      kicker: 'Định hướng khám phá',
      accent: 'clay',
      icon: 'map',
      entries: [
        { heading: 'Vùng 1', text: 'Nội dung vùng 1 giải đáp ngắn gọn.' },
        { heading: 'Vùng 2', text: 'Nội dung vùng 2 giải đáp ngắn gọn.' },
      ],
      ctaTo: '/ban-do',
      ctaLabel: 'Xem trên bản đồ',
    })

    expect(wrapper.find('[data-catalog-aeo-plaque]').exists()).toBe(true)
    expect(wrapper.attributes('data-material-accent')).toBe('clay')
    expect(wrapper.text()).toContain('Cẩm nang 3 vùng Mekong')
    expect(wrapper.text()).toContain('Định hướng khám phá')
    expect(wrapper.text()).toContain('Vùng 1')
    expect(wrapper.text()).toContain('Nội dung vùng 1 giải đáp ngắn gọn.')

    const cta = wrapper.find('[data-catalog-aeo-cta]')
    expect(cta.exists()).toBe(true)
    expect(cta.attributes('to')).toBe('/ban-do')
  })

  it('renders default kicker and omits CTA when not provided', async () => {
    const wrapper = await mount({
      title: 'Đặc sản OCOP theo mùa',
      entries: [
        { heading: 'Tiêu chuẩn', text: 'Đánh giá xếp hạng theo Quyết định Thủ tướng.' },
      ],
    })

    expect(wrapper.attributes('data-material-accent')).toBe('amber')
    expect(wrapper.text()).toContain('Góc nhìn bản địa · Giải đáp nhanh AEO')
    expect(wrapper.text()).toContain('Đặc sản OCOP theo mùa')
    expect(wrapper.find('[data-catalog-aeo-cta]').exists()).toBe(false)
  })

  it('supports river and clay accents appropriately', async () => {
    const wrapper = await mount({
      title: 'Lễ hội sông nước',
      accent: 'river',
      entries: [{ heading: 'Nghi thức', text: 'Lễ rước nước truyền thống.' }],
    })
    expect(wrapper.attributes('data-material-accent')).toBe('river')
  })

  it('strictly adheres to design tokens with zero raw hex in styles', () => {
    const filePath = resolve(__dirname, '../components/CatalogAeoPlaque.vue')
    const source = readFileSync(filePath, 'utf8')
    const rawHexPattern = /(?<![&\w-])#[0-9a-fA-F]{3,8}\b/g
    const matches = source.match(rawHexPattern) || []
    expect(matches).toEqual([])
  })
})
