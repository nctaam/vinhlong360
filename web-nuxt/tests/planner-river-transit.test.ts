import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import PlannerRiverTransitWarning from '../components/planner/PlannerRiverTransitWarning.vue'

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

async function mount(props: any) {
  const wrapper = await mountSuspended(PlannerRiverTransitWarning, {
    props,
    global: { stubs: { IconLine: true } },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('PlannerRiverTransitWarning — Mekong Ferry & Water Route Advisories', () => {
  it('renders river transit advisory when stops span across multiple areas or cù lao islands', async () => {
    const stops = [
      { id: '1', name: 'Điểm Vĩnh Long', place_area: 'vinh-long' },
      { id: '2', name: 'Nhà vườn An Bình', place_area: 'an-binh' },
    ]
    const wrapper = await mount({ stops })

    expect(wrapper.find('[data-planner-river-transit]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Lưu ý đò phà & nhịp sông nước thực địa')
    expect(wrapper.text()).toContain('Phà An Bình')
  })

  it('hides the warning when stops do not cross river/island areas', async () => {
    const stops = [
      { id: '1', name: 'Điểm 1', place_area: 'vinh-long' },
    ]
    const wrapper = await mount({ stops })
    expect(wrapper.find('[data-planner-river-transit]').exists()).toBe(false)
  })

  it('strictly adheres to design tokens with zero raw hex in styles', () => {
    const filePath = resolve(__dirname, '../components/planner/PlannerRiverTransitWarning.vue')
    const source = readFileSync(filePath, 'utf8')
    const rawHexPattern = /(?<![&w-])#[0-9a-fA-F]{3,8}/g
    const matches = source.match(rawHexPattern) || []
    expect(matches).toEqual([])
  })
})
