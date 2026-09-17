import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ThemeModeControl from '../components/shell/ThemeModeControl.vue'

const colorMode = vi.hoisted(() => ({ value: 'dark' as unknown, preference: 'dark' as unknown }))
mockNuxtImport('useColorMode', () => () => colorMode)
const wrappers: Array<{ unmount: () => void }> = []

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  colorMode.value = 'dark'
  colorMode.preference = 'dark'
})

describe('Header Smart Editorial Refinement - Task 1: Theme Micro-Toggle', () => {
  it('renders compact micro-toggle while preserving accessible text labels for screen readers', async () => {
    const wrapper = await mountSuspended(ThemeModeControl, { attachTo: document.body })
    wrappers.push(wrapper)

    const darkBtn = wrapper.get('button[data-theme-mode="dark"]')
    const lightBtn = wrapper.get('button[data-theme-mode="light"]')

    expect(darkBtn.text()).toContain('Nocturne')
    expect(lightBtn.text()).toContain('Nền sáng dễ đọc')

    // Nhãn chữ được bọc trong class sr-only để triệt tiêu text rườm rà trên thanh điều hướng
    expect(darkBtn.find('.theme-mode-label').classes()).toContain('sr-only')
    expect(lightBtn.find('.theme-mode-label').classes()).toContain('sr-only')

    // Cả 2 nút đều có icon trực quan
    expect(darkBtn.find('.line-icon').exists()).toBe(true)
    expect(lightBtn.find('.line-icon').exists()).toBe(true)
  })
})
