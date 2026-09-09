import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import PlannerMobilePassModal from '../components/planner/PlannerMobilePassModal.vue'

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

async function mount(props: any) {
  const wrapper = await mountSuspended(PlannerMobilePassModal, {
    props,
    global: { stubs: { IconLine: true } },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('PlannerMobilePassModal — Offline Field Itinerary Pass', () => {
  const mockStops = [
    { id: '1', name: 'Chợ Vĩnh Long', place_name: 'Phường 1' },
    { id: '2', name: 'Lò Gốm Mang Thít', place_name: 'Mỹ Phước' },
  ]

  it('renders itinerary pass modal with landmarks and stops when open', async () => {
    const wrapper = await mount({
      open: true,
      title: 'Khám phá 1 ngày gốm đỏ',
      stops: mockStops,
    })

    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Thẻ hành trình thực địa')
    expect(wrapper.text()).toContain('Khám phá 1 ngày gốm đỏ')
    expect(wrapper.text()).toContain('Chợ Vĩnh Long')
    expect(wrapper.text()).toContain('Lò Gốm Mang Thít')
  })

  it('does not render when open is false', async () => {
    const wrapper = await mount({
      open: false,
      title: 'Lịch trình',
      stops: mockStops,
    })

    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('strictly adheres to design tokens with zero raw hex in styles', () => {
    const filePath = resolve(__dirname, '../components/planner/PlannerMobilePassModal.vue')
    const source = readFileSync(filePath, 'utf8')
    const rawHexPattern = /(?<![&w-])#[0-9a-fA-F]{3,8}/g
    const matches = source.match(rawHexPattern) || []
    expect(matches).toEqual([])
  })
})
