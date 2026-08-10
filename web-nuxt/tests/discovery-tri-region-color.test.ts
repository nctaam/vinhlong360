import { clearNuxtData } from '#app'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TourismPage from '../pages/du-lich.vue'

const apiFetchMock = vi.hoisted(() => vi.fn())
mockNuxtImport('apiFetch', () => apiFetchMock)

const wrappers: Array<{ unmount: () => void }> = []
const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: String, alt: String },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})
const stubs = {
  NuxtImg: NuxtImgStub,
  Breadcrumb: true,
  CountUp: { props: ['value'], template: '<span>{{ value }}</span>' },
  FilterChips: {
    props: ['filters', 'modelValue'],
    emits: ['update:modelValue'],
    template: '<div data-filter-chips><button v-for="filter in filters" :key="filter.key" type="button" :data-filter-key="filter.key" @click="$emit(\'update:modelValue\', [filter.key])">{{ filter.label }}</button></div>',
  },
  EmptyState: true,
  SkeletonGrid: true,
  SaveButton: true,
  ImageDisclosure: true,
  JourneyBar: true,
  IconLine: { props: ['name'], template: '<i :data-icon="name" />' },
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

beforeEach(() => apiFetchMock.mockReset())
afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  await clearNuxtData()
})

describe('Discovery Tri-Region color recipe', () => {
  it('changes one approved material accent when the user changes discovery mode', async () => {
    apiFetchMock.mockResolvedValue({
      entities: [
        {
          id: 'craft-1',
          type: 'craft_village',
          name: 'Làng gốm',
          summary: 'Một làng nghề ven sông với câu chuyện dài về đất, lửa và những gia đình còn giữ lò gốm đỏ.',
          quality: { source_tier: 'official' },
        },
        { id: 'stay-1', type: 'accommodation', name: 'Nhà vườn', quality: { source_tier: 'verified' } },
      ],
      total: 2,
    })

    const wrapper = await mountSuspended(TourismPage, { global: { stubs } })
    wrappers.push(wrapper)
    await flushUi()

    const root = wrapper.get('[data-page-recipe="discovery"]')
    expect(wrapper.text()).toContain('Chính thức')
    expect(wrapper.text()).toContain('Chưa rõ nguồn')
    expect(wrapper.text()).not.toContain('Đã xác minh')
    expect(wrapper.find('.cspot').exists()).toBe(false)
    expect(wrapper.find('.catalog-interstitial').exists()).toBe(false)
    expect(wrapper.get('[data-catalog-section="evidence"]')).toBeTruthy()

    for (const [label, accent] of [
      ['Trải nghiệm', 'leaf'],
      ['Ẩm thực', 'amber'],
      ['Làng nghề', 'clay'],
      ['Lưu trú', 'river'],
    ] as const) {
      const buttons = wrapper.findAll('.mode-pill')
      const selected = buttons.find(button => button.text().includes(label))
      expect(selected).toBeTruthy()
      await selected!.trigger('click')

      expect(root.attributes('data-material-accent')).toBe(accent)
      for (const button of buttons) {
        expect(button.attributes('aria-pressed')).toBe(button === selected ? 'true' : 'false')
      }
    }
  })

  it('keeps the unfiltered orientation truthful and mode selection understandable without relying on color', async () => {
    const wrapper = await mountSuspended(TourismPage, { global: { stubs } })
    wrappers.push(wrapper)
    await flushUi()

    expect(wrapper.get('[data-route-node-active]').text()).toContain('Tất cả loại hình')
    expect(wrapper.find('.mode-pill[aria-pressed="true"]').exists()).toBe(false)

    const selected = wrapper.findAll('.mode-pill').find(button => button.text().includes('Trải nghiệm'))!
    await selected.trigger('click')
    await nextTick()
    expect(selected.text()).toContain('Trải nghiệm')
    expect(selected.classes()).toContain('active')
    expect(selected.attributes('aria-pressed')).toBe('true')
  })

  it('updates the orientation trace when a type chip changes the effective filter', async () => {
    apiFetchMock.mockResolvedValue({ entities: [], total: 0 })
    const wrapper = await mountSuspended(TourismPage, { global: { stubs } })
    wrappers.push(wrapper)
    await flushUi()

    await wrapper.get('[data-filter-key="dish"]').trigger('click')
    await nextTick()
    expect(wrapper.get('[data-route-node-active]').text()).toContain('Ẩm thực')
    expect(wrapper.get('.mode-pill[aria-pressed="true"]').text()).toContain('Ẩm thực')
    expect(wrapper.get('[data-page-recipe="discovery"]').attributes('data-material-accent')).toBe('amber')

    await wrapper.get('[data-filter-key="accommodation"]').trigger('click')
    await nextTick()
    expect(wrapper.get('[data-route-node-active]').text()).toContain('Lưu trú')
    expect(wrapper.get('.mode-pill[aria-pressed="true"]').text()).toContain('Lưu trú')
    expect(wrapper.get('[data-page-recipe="discovery"]').attributes('data-material-accent')).toBe('river')
  })
})
