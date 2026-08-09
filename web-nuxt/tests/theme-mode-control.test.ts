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
  localStorage.clear()
  document.documentElement.classList.remove('light', 'dark')
  delete document.documentElement.dataset.theme
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
    expect(document.documentElement.dataset.theme).toBe('nocturne')
  })

  it('uses Nocturne as the deterministic fallback for unsupported values', async () => {
    colorMode.value = 'unknown'
    colorMode.preference = 'unknown'
    const wrapper = await mountSuspended(ThemeModeControl)
    wrappers.push(wrapper)
    expect(wrapper.get('button[data-theme-mode="dark"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('button[data-theme-mode="light"]').attributes('aria-pressed')).toBe('false')
    expect(document.documentElement.dataset.theme).toBe('nocturne')
  })

  it('persists the selected mode through the accessibility profile and keeps focus', async () => {
    const wrapper = await mountSuspended(ThemeModeControl, { attachTo: document.body })
    wrappers.push(wrapper)
    const light = wrapper.get<HTMLButtonElement>('button[aria-label="Nền sáng dễ đọc"]')
    await light.trigger('click')
    expect(colorMode.preference).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('parchment')
    expect(JSON.parse(localStorage.getItem('vl360-accessibility-profile') || '{}')).toMatchObject({ theme: 'parchment' })
    expect(document.activeElement).toBe(light.element)
  })

  it('hydrates the explicit Parchment choice even when legacy color-mode storage disagrees', async () => {
    localStorage.setItem('vl360-accessibility-profile', JSON.stringify({
      theme: 'parchment',
      density: 'comfortable',
      textScale: 1,
    }))
    localStorage.setItem('vl360-color-mode', 'dark')
    const wrapper = await mountSuspended(ThemeModeControl, { attachTo: document.body })
    wrappers.push(wrapper)

    expect(colorMode.preference).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('parchment')
    expect(wrapper.get('button[data-theme-mode="light"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('button[data-theme-mode="dark"]').attributes('aria-pressed')).toBe('false')
  })
})
