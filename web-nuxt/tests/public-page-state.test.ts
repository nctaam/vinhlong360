import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ActionDock from '../components/public/ActionDock.vue'
import PageState from '../components/public/PageState.vue'
import WhyThisControl from '../components/public/WhyThisControl.vue'

const wrappers: Array<{ unmount: () => void }> = []

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
})

describe('public page-state primitives', () => {
  it('renders stale evidence without presenting it as an error', async () => {
    const wrapper = await mountSuspended(PageState, {
      props: { state: { kind: 'stale', data: {}, updatedAt: '2026-08-01' } },
      slots: { default: '<p>Thông tin vẫn dùng được</p>' },
    })
    wrappers.push(wrapper)

    const panel = wrapper.get('[data-page-state="stale"]')
    expect(panel.text()).toContain('Có thể đã cũ')
    expect(panel.text()).toContain('2026-08-01')
    expect(panel.attributes('role')).not.toBe('alert')
    expect(panel.text()).toContain('Thông tin vẫn dùng được')
  })

  it('keeps partial content and offers recovery for each failed panel', async () => {
    const retry = vi.fn()
    const wrapper = await mountSuspended(PageState, {
      props: { state: { kind: 'partial', data: {}, failedPanels: ['media', 'directions'] }, retry },
      slots: { default: '<p data-available-content>Phần thông tin còn lại</p>' },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[data-available-content]')).toBeTruthy()
    const actions = wrapper.findAll('[data-page-state-retry]')
    expect(actions).toHaveLength(2)
    await actions[1]!.trigger('click')
    expect(retry).toHaveBeenCalledWith('directions')
  })

  it('renders only the first primary action from the ActionDock slot', async () => {
    const wrapper = await mountSuspended(ActionDock, {
      slots: {
        primary: '<button data-primary="first">Chỉ đường</button><button data-primary="second">Gọi điện</button>',
        default: '<a href="/save">Lưu</a>',
      },
    })
    wrappers.push(wrapper)

    expect(wrapper.findAll('[data-action-dock-primary] button')).toHaveLength(1)
    expect(wrapper.find('[data-primary="first"]').exists()).toBe(true)
    expect(wrapper.find('[data-primary="second"]').exists()).toBe(false)
  })

  it('discloses why a suggestion appears and allows a reset', async () => {
    const onReset = vi.fn()
    const wrapper = await mountSuspended(WhyThisControl, {
      props: {
        reason: 'Phù hợp với khu vực bạn đã chọn',
        signals: ['Khu vực đã chọn', 'Chủ đề bạn quan tâm'],
        onReset,
      },
    })
    wrappers.push(wrapper)

    await wrapper.get('[data-why-this-trigger]').trigger('click')
    expect(wrapper.get('[data-why-this-control]').text()).toContain('Phù hợp với khu vực bạn đã chọn')
    expect(wrapper.get('[data-why-this-signals]').text()).toContain('Khu vực đã chọn')
    await wrapper.get('[data-why-this-reset]').trigger('click')
    expect(onReset).toHaveBeenCalledOnce()
  })
})
