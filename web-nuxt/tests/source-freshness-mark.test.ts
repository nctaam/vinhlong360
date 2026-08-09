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

  it('degrades a bare verified tier to unknown until public evidence is supplied', async () => {
    const wrapper = await mountSuspended(SourceMark, {
      props: { tier: 'verified' },
      global: { stubs: { IconLine: { props: ['name'], template: '<i :data-icon="name" />' } } },
    })
    wrappers.push(wrapper)

    const mark = wrapper.get('[data-source-mark]')
    expect(mark.attributes('data-source-tier')).toBe('unknown')
    expect(mark.text()).toContain('Chưa rõ nguồn')
    expect(mark.get('[data-icon="info"]')).toBeTruthy()
  })

  it('shows a verified tier only with a public source and valid evidence date', async () => {
    const wrapper = await mountSuspended(SourceMark, {
      props: {
        tier: 'verified',
        sourceTitle: 'Đối tác dữ liệu địa phương',
        sourceUrl: 'https://partner.example.vn/entity-1',
        verifiedAt: '2026-07-18T00:00:00Z',
      },
      global: { stubs: { IconLine: { props: ['name'], template: '<i :data-icon="name" />' } } },
    })
    wrappers.push(wrapper)

    const mark = wrapper.get('[data-source-mark]')
    expect(mark.attributes('data-source-tier')).toBe('verified')
    expect(mark.text()).toContain('Có nguồn đối tác')
    expect(mark.get('[data-icon="check"]')).toBeTruthy()
  })

  it('makes conflicting freshness evidence explicit', async () => {
    const wrapper = await mountSuspended(FreshnessLine, {
      props: { status: 'conflict', updatedLabel: '' },
      global: { stubs: { IconLine: { props: ['name'], template: '<i :data-icon="name" />' } } },
    })
    wrappers.push(wrapper)

    const line = wrapper.get('[data-freshness-line]')
    expect(line.text()).toContain('Thông tin có mâu thuẫn')
    expect(line.attributes('aria-label')).toContain('Thông tin có mâu thuẫn')
    expect(line.get('[data-icon="alert-triangle"]')).toBeTruthy()
  })
})
