import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { unref } from 'vue'
import ThemeModeControl from '../components/shell/ThemeModeControl.vue'

const colorMode = vi.hoisted(() => ({ value: 'dark' as unknown, preference: 'dark' as unknown }))
const headEntries = vi.hoisted(() => [] as unknown[])
mockNuxtImport('useColorMode', () => () => colorMode)
mockNuxtImport('useHead', () => (entry: unknown) => { headEntries.push(entry) })
const wrappers: Array<{ unmount: () => void }> = []
const runtimeWindow = window as Window & {
  __NUXT_COLOR_MODE__?: { preference?: string; value?: string }
}

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  colorMode.value = 'dark'
  colorMode.preference = 'dark'
  document.documentElement.classList.remove('light', 'dark')
  delete document.documentElement.dataset.theme
  delete runtimeWindow.__NUXT_COLOR_MODE__
  headEntries.splice(0)
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

  it('uses Nocturne as the deterministic SSR fallback for unsupported values', async () => {
    colorMode.value = 'unknown'
    colorMode.preference = 'unknown'
    const wrapper = await mountSuspended(ThemeModeControl)
    wrappers.push(wrapper)
    expect(wrapper.get('button[data-theme-mode="dark"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('button[data-theme-mode="light"]').attributes('aria-pressed')).toBe('false')

    const head = headEntries.at(-1) as {
      htmlAttrs: { 'data-theme': unknown }
      script: Array<{ innerHTML: string; tagPosition: string }>
    }
    expect(unref(head.htmlAttrs['data-theme'])).toBe('nocturne')
    expect(head.script[0]?.tagPosition).toBe('head')
    expect(head.script[0]?.innerHTML).toContain("localStorage.getItem('vl360-color-mode')")
    expect(head.script[0]?.innerHTML).toContain("v==='light'?'parchment':'nocturne'")
  })

  it('persists the selected mode through useColorMode and keeps focus', async () => {
    const wrapper = await mountSuspended(ThemeModeControl, { attachTo: document.body })
    wrappers.push(wrapper)
    const light = wrapper.get<HTMLButtonElement>('button[aria-label="Nền sáng dễ đọc"]')
    await light.trigger('click')
    expect(colorMode.preference).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('parchment')
    expect(document.activeElement).toBe(light.element)
  })

  it('synchronizes a pre-painted Parchment choice before the first interaction', async () => {
    document.documentElement.classList.add('light')
    const wrapper = await mountSuspended(ThemeModeControl, { attachTo: document.body })
    wrappers.push(wrapper)
    await new Promise<void>(resolve => queueMicrotask(resolve))
    expect(colorMode.preference).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('parchment')
    expect(wrapper.get('button[data-theme-mode="light"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('button[data-theme-mode="dark"]').attributes('aria-pressed')).toBe('false')
  })

  it('prefers the color-mode bootstrap when hydration temporarily repaints the document', async () => {
    runtimeWindow.__NUXT_COLOR_MODE__ = { preference: 'light', value: 'light' }
    document.documentElement.classList.add('dark')
    const wrapper = await mountSuspended(ThemeModeControl, { attachTo: document.body })
    wrappers.push(wrapper)
    await new Promise<void>(resolve => queueMicrotask(resolve))
    expect(colorMode.preference).toBe('light')
    expect(wrapper.get('button[data-theme-mode="light"]').attributes('aria-pressed')).toBe('true')
  })
})
