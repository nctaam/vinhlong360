import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import DetailAeoSummary from '../components/DetailAeoSummary.vue'

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

async function mount(props: any) {
  const wrapper = await mountSuspended(DetailAeoSummary, {
    props,
    global: { stubs: { IconLine: true } },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('DetailAeoSummary — 30s Field Digest (AEO/GEO)', () => {
  const mockEntity: any = {
    id: 'lo-gom-mang-thit',
    name: 'Lò Gốm Mang Thít',
    type: 'craft_village',
    description: 'Di sản lò gốm đỏ trăm năm ven dòng Thầy Cai.',
    attributes: {
      highlight: 'Vương quốc đỏ nghìn lò gạch.',
      hours: '07:00 - 17:00',
      transport: 'Đi thuyền trên kênh Thầy Cai hoặc xe máy đường 902',
      suggested_duration: '2 giờ',
      price: 'Miễn phí tham quan',
      local_tip: 'Nên ghé lúc sáng sớm đón nắng xiên vào miệng lò.',
    },
  }

  it('renders 30s field digest cards with semantic landmarks and values', async () => {
    const wrapper = await mount({ entity: mockEntity, accent: 'clay' })

    expect(wrapper.find('[data-detail-aeo-summary]').exists()).toBe(true)
    expect(wrapper.attributes('data-material-accent')).toBe('clay')
    expect(wrapper.text()).toContain('30s Thực địa · Góc nhìn Bản địa')
    expect(wrapper.text()).toContain('Vương quốc đỏ nghìn lò gạch.')
    expect(wrapper.text()).toContain('Thời điểm vàng')
    expect(wrapper.text()).toContain('07:00 - 17:00')
    expect(wrapper.text()).toContain('Cách tiếp cận')
    expect(wrapper.text()).toContain('kênh Thầy Cai')
    expect(wrapper.text()).toContain('2 giờ · Miễn phí tham quan')
    expect(wrapper.text()).toContain('Mẹo người bản địa')
    expect(wrapper.text()).toContain('nắng xiên vào miệng lò')
  })

  it('provides safe fallbacks for missing attributes', async () => {
    const wrapper = await mount({
      entity: { id: 'test-item', name: 'Điểm thử nghiệm', type: 'dish' },
      accent: 'amber',
    })

    expect(wrapper.attributes('data-material-accent')).toBe('amber')
    expect(wrapper.text()).toContain('Điểm thử nghiệm')
    expect(wrapper.text()).toContain('Thời điểm vàng')
    expect(wrapper.text()).toContain('Cách tiếp cận')
  })

  it('strictly adheres to design tokens with zero raw hex in styles', () => {
    const filePath = resolve(__dirname, '../components/DetailAeoSummary.vue')
    const source = readFileSync(filePath, 'utf8')
    const rawHexPattern = /(?<![&w-])#[0-9a-fA-F]{3,8}/g
    const matches = source.match(rawHexPattern) || []
    expect(matches).toEqual([])
  })
})
