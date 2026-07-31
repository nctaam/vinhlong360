import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ThemeModeControl from '../components/shell/ThemeModeControl.vue'

const colorMode = vi.hoisted(() => ({ value: 'dark', preference: 'dark' as 'dark' | 'light' }))
mockNuxtImport('useColorMode', () => () => colorMode)
const wrappers: Array<{ unmount: () => void }> = []

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  colorMode.value = 'dark'
  colorMode.preference = 'dark'
})

describe('public theme mode control', () => {
  it('offers explicit Nocturne and Daylight Parchment choices', async () => {
    const wrapper = await mountSuspended(ThemeModeControl, { attachTo: document.body })
    wrappers.push(wrapper)
    const control = wrapper.get('[data-theme-control]')
    expect(control.attributes('aria-label')).toBe('Chọn giao diện')
    expect(wrapper.get('button[data-theme-mode="dark"]').text()).toContain('Nocturne')
    expect(wrapper.get('button[data-theme-mode="light"]').text()).toContain('Nền sáng dễ đọc')
    expect(wrapper.findAll('button')).toHaveLength(2)
    expect(wrapper.get('button[data-theme-mode="dark"]').attributes('aria-pressed')).toBe('true')
  })

  it('uses Nocturne as the deterministic SSR fallback for unsupported values', async () => {
    colorMode.value = 'unknown'
    const wrapper = await mountSuspended(ThemeModeControl)
    wrappers.push(wrapper)
    expect(wrapper.get('button[data-theme-mode="dark"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('button[data-theme-mode="light"]').attributes('aria-pressed')).toBe('false')
  })

  it('persists the selected mode through useColorMode and keeps focus', async () => {
    const wrapper = await mountSuspended(ThemeModeControl, { attachTo: document.body })
    wrappers.push(wrapper)
    const light = wrapper.get<HTMLButtonElement>('button[data-theme-mode="light"]')
    await light.trigger('click')
    expect(colorMode.preference).toBe('light')
    expect(document.activeElement).toBe(light.element)
  })
})
