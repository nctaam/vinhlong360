import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import EmptyState from '../components/EmptyState.vue'
import IconLine from '../components/IconLine.vue'

/**
 * EmptyState có HAI đường vẽ biểu tượng, và đường cũ phải sống nguyên vẹn.
 *
 * `icon` nhận một chuỗi emoji và render nó thành CHỮ; nó đang được dùng ở 61 nơi.
 * `iconName` là đường mới, render <IconLine>. Thêm đường mới rồi mới bỏ đường cũ
 * (B2 additive-first), nên trong lúc di cư từng trang thì cả hai cùng tồn tại —
 * test này khoá đúng điều đó, kể cả thứ tự ưu tiên khi truyền cả hai.
 */
const global = { components: { IconLine } }

describe('EmptyState — hai đường vẽ biểu tượng', () => {
  it('đường CŨ: icon dạng emoji vẫn render thành chữ', () => {
    const w = mount(EmptyState, { props: { icon: '⚠️', title: 'Lỗi' }, global })
    expect(w.find('.empty-icon').text()).toBe('⚠️')
    expect(w.findComponent(IconLine).exists()).toBe(false)
  })

  it('đường MỚI: iconName render IconLine, không render chữ emoji', () => {
    const w = mount(EmptyState, { props: { iconName: 'alert-triangle', title: 'Lỗi' }, global })
    const icon = w.findComponent(IconLine)
    expect(icon.exists()).toBe(true)
    expect(icon.props('name')).toBe('alert-triangle')
    expect(w.find('.empty-icon').text()).toBe('')
  })

  it('truyền cả hai thì iconName THẮNG — để trang đã di cư không hiện hai biểu tượng', () => {
    const w = mount(EmptyState, { props: { icon: '⚠️', iconName: 'alert-triangle' }, global })
    expect(w.findComponent(IconLine).exists()).toBe(true)
    expect(w.find('.empty-icon').text()).toBe('')
  })

  it('không truyền gì thì vẫn rơi về hình minh hoạ mặc định', () => {
    const w = mount(EmptyState, { props: { title: 'Trống' }, global })
    expect(w.find('.empty-icon').exists()).toBe(false)
    expect(w.find('.empty-illust').exists()).toBe(true)
  })

  it('biểu tượng luôn ẩn khỏi cây a11y — nghĩa nằm ở title/message', () => {
    for (const props of [{ icon: '⚠️' }, { iconName: 'alert-triangle' }]) {
      const w = mount(EmptyState, { props, global })
      expect(w.find('.empty-icon').attributes('aria-hidden')).toBe('true')
    }
  })
})
