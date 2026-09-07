import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import CatalogAeoPlaque from '../components/CatalogAeoPlaque.vue'

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

async function mount() {
  const wrapper = await mountSuspended(CatalogAeoPlaque, {
    props: {
      title: 'Cẩm nang du lịch theo mùa',
      kicker: 'Góc nhìn bản địa · Giải đáp nhanh AEO',
      accent: 'amber',
      icon: 'bulb',
      entries: [
        {
          heading: 'Mùa nước nổi & Miệt vườn (Tháng 8 – 10)',
          text: 'Thời điểm vàng trải nghiệm sinh thái sông nước Cửu Long. Xuồng ba lá len lỏi dưới bóng dừa nước Cù Lao An Bình, thưởng thức cá linh non đầu mùa và trái cây chín cây thanh ngọt.',
        },
        {
          heading: 'Mùa di sản gốm & Hoa xuân (Tháng 1 – 3)',
          text: 'Vương quốc gốm đỏ Mang Thít vào vụ nung đỏ lửa bên dòng Cổ Chiên. Khí hậu mát dịu lý tưởng cho các tour di sản kiến trúc tâm linh, làng nghề truyền thống và lễ hội đầu năm.',
        },
      ],
      ctaTo: '/theo-mua',
      ctaLabel: 'Khám phá lịch trình theo mùa',
    },
    attrs: {
      'data-home-section': 'aeo-plaque',
      'data-home-aeo-plaque': '',
    },
    global: { stubs: { IconLine: true, NuxtLink: true } },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('HomeAeoPlaque — Editorial Answer Plaque Unification (AEO/GEO)', () => {
  it('renders with correct semantic landmarks and accessible attributes', async () => {
    const wrapper = await mount()
    const section = wrapper.find('[data-home-section="aeo-plaque"]')
    expect(section.exists()).toBe(true)
    expect(section.attributes('data-home-aeo-plaque')).toBeDefined()
    expect(section.attributes('aria-labelledby')).toBeDefined()

    const title = wrapper.find('h2')
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
    const cta = wrapper.find('[data-catalog-aeo-cta]')
    expect(cta.exists()).toBe(true)
    expect(cta.attributes('to')).toBe('/theo-mua')
  })

  it('strictly adheres to design token rules with zero raw hex colors', () => {
    const filePath = resolve(__dirname, '../components/CatalogAeoPlaque.vue')
    const source = readFileSync(filePath, 'utf8')
    const rawHexPattern = /(?<![&\w-])#[0-9a-fA-F]{3,8}\b/g
    const matches = source.match(rawHexPattern) || []
    expect(matches).toEqual([])
  })
})
