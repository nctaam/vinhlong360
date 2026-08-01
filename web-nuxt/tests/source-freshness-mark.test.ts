import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import FreshnessLine from '../components/FreshnessLine.vue'
import SourceMark from '../components/SourceMark.vue'

const wrappers: Array<{ unmount: () => void }> = []

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
})

describe('source and freshness primitives', () => {
  it.each([
    ['official', 'Chính thức', 'shield'],
    ['verified', 'Đã xác minh', 'check'],
    ['community', 'Cộng đồng', 'user'],
    ['unknown', 'Chưa rõ nguồn', 'info'],
  ] as const)('shows icon and visible label for %s', async (tier, label, icon) => {
    const wrapper = await mountSuspended(SourceMark, {
      props: { tier },
      global: { stubs: { IconLine: { props: ['name'], template: '<i :data-icon="name" />' } } },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[data-source-mark]').attributes('data-source-tier')).toBe(tier)
    expect(wrapper.get('[data-source-mark]').text()).toContain(label)
    expect(wrapper.get(`[data-icon="${icon}"]`)).toBeTruthy()
  })

  it.each([
    ['official', 'shield'],
    ['verified', 'check'],
    ['community', 'user'],
    ['unknown', 'info'],
  ] as const)('renders the real %s tier with its %s icon instead of fallback', async (tier, icon) => {
    const wrapper = await mountSuspended(SourceMark, {
      props: { tier },
    })
    wrappers.push(wrapper)

    const renderedIcon = wrapper.get('.line-icon')
    expect(renderedIcon.classes()).toContain(`li-${icon}`)
    expect(renderedIcon.classes()).not.toContain('li-circle-help')
    expect(renderedIcon.find('svg').exists()).toBe(true)
  })

  it('keeps freshness separate from provenance', async () => {
    const wrapper = await mountSuspended(FreshnessLine, {
      props: { status: 'stale', updatedLabel: '12/07/2026' },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[data-freshness-line]').attributes('data-freshness-status')).toBe('stale')
    expect(wrapper.text()).toContain('Có thể đã cũ')
    expect(wrapper.text()).toContain('12/07/2026')
    expect(wrapper.find('[data-source-mark]').exists()).toBe(false)
  })
})
