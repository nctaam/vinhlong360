import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'

import SystemStatePanel from '../components/system/SystemStatePanel.vue'

const wrappers: Array<{ unmount: () => void }> = []

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
})

describe('SystemStatePanel', () => {
  it('renders a permission state with a structural SVG icon and primary action', async () => {
    const wrapper = await mountSuspended(SystemStatePanel, {
      props: {
        kind: 'permission-denied',
        title: 'Bạn chưa có quyền truy cập',
        description: 'Tài khoản hiện tại không có phạm vi cần thiết.',
        primaryLabel: 'Mở khu vực được phép',
      },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[role="alert"]').text()).toContain('Bạn chưa có quyền truy cập')
    expect(wrapper.find('.line-icon svg').exists()).toBe(true)
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('primary')).toHaveLength(1)
  })

  it('shows retry timing and emits independent secondary recovery', async () => {
    const wrapper = await mountSuspended(SystemStatePanel, {
      props: {
        kind: 'rate-limited',
        title: 'Bạn thao tác quá nhanh',
        description: 'Vui lòng chờ trước khi thử lại.',
        retryAfter: '14:30',
        primaryLabel: 'Thử lại',
        secondaryLabel: 'Quay về',
      },
    })
    wrappers.push(wrapper)

    expect(wrapper.text()).toContain('Có thể thử lại lúc 14:30')
    const buttons = wrapper.findAll('button')
    await buttons[1]!.trigger('click')
    expect(wrapper.emitted('secondary')).toHaveLength(1)
  })
})
