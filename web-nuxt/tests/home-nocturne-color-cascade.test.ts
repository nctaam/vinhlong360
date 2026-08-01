import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import HomeFeatureDossier from '../components/home/HomeFeatureDossier.vue'
import SearchAutocomplete from '../components/SearchAutocomplete.vue'
import type { ImageDescriptor } from '../types/image'

const root = resolve(import.meta.dirname, '../..')
const wrappers: Array<{ unmount: () => void }> = []
const stylesheets: HTMLStyleElement[] = []

const descriptor: ImageDescriptor = {
  url: null,
  alt: 'Ảnh đang cập nhật',
  source_class: 'placeholder',
  source_kind: 'generated-placeholder',
  disclosure_key: 'entity-placeholder',
  short_label: 'Ảnh đại diện đang cập nhật',
  full_disclosure: 'Hình đại diện tạm thời trong khi ảnh thực tế đang được cập nhật.',
  credit: null,
  width: null,
  height: null,
}

function pageStyle(source: string): string {
  const start = source.indexOf('<style>')
  const end = source.indexOf('</style>', start)
  if (start < 0 || end < 0) throw new Error('Missing Homepage inline style')
  return source.slice(start + '<style>'.length, end)
}

async function installActualHomepageStyles() {
  const config = await readFile(resolve(root, 'web-nuxt/nuxt.config.ts'), 'utf8')
  const cssList = config.slice(config.indexOf('css: ['), config.indexOf('],', config.indexOf('css: [')))
  const orderedGlobalFiles = [...cssList.matchAll(/'~\/assets\/css\/([^']+)'/g)].map(match => match[1]!)
  const globalCss = await Promise.all(orderedGlobalFiles.map(file => readFile(resolve(root, 'web-nuxt/assets/css', file), 'utf8')))
  const indexSource = await readFile(resolve(root, 'web-nuxt/pages/index.vue'), 'utf8')
  const homeCss = await readFile(resolve(root, 'web-nuxt/assets/css/home-nocturne.css'), 'utf8')
  const stylesheet = document.createElement('style')
  stylesheet.textContent = [...globalCss, pageStyle(indexSource), homeCss].join('\n')
  document.head.append(stylesheet)
  stylesheets.push(stylesheet)
}

function rgb(value: string): [number, number, number] {
  const match = /rgba?\(\s*([0-9.]+)[, ]+([0-9.]+)[, ]+([0-9.]+)/.exec(value)
  if (!match) throw new Error(`Expected computed RGB color, received: ${value}`)
  return [Number(match[1]), Number(match[2]), Number(match[3])]
}

function composite(foreground: [number, number, number], background: [number, number, number], opacity: number) {
  return foreground.map((channel, index) => channel * opacity + background[index]! * (1 - opacity)) as [number, number, number]
}

function luminance(color: [number, number, number]) {
  const channels = color.map((channel) => {
    const normalized = channel / 255
    return normalized <= .04045 ? normalized / 12.92 : ((normalized + .055) / 1.055) ** 2.4
  })
  return .2126 * channels[0]! + .7152 * channels[1]! + .0722 * channels[2]!
}

function contrast(foreground: [number, number, number], background: [number, number, number]) {
  const a = luminance(foreground)
  const b = luminance(background)
  return (Math.max(a, b) + .05) / (Math.min(a, b) + .05)
}

function cascadeFixture(tokens: Record<string, string>) {
  return defineComponent({
    setup: () => () => h('main', {
      class: 'home',
      'data-home-pilot': 'nocturne-b1',
      'data-color-system': 'tri-region-v1',
      'data-page-recipe': 'homepage',
      'data-material-accent': 'clay',
      style: tokens,
    }, [
      h('section', { class: 'hero', 'data-test-hero': '' }, [
        h(SearchAutocomplete, {
          class: 'hero-search hero-ac',
          'data-home-search': '',
          'data-color-role': 'action-primary',
        }),
        h('a', { class: 'hero-nearby', href: '#nearby' }, 'Tìm quanh tôi'),
        h(HomeFeatureDossier, {
          eyebrow: 'Gợi ý nổi bật',
          title: 'Một ngày ven sông',
          descriptor,
          disclosureId: 'cascade-feature-disclosure',
          detailTo: '/dia-diem/experience-1',
          plannerTo: '/tao-lich-trinh?add=experience-1',
          sourceTier: 'unknown',
        }),
      ]),
      h('span', { class: 'ec-date', 'data-material-accent': 'amber' }, [
        h('span', { class: 'ec-month' }, 'Th8'),
      ]),
      h('span', { class: 'ec-countdown', 'data-material-accent': 'amber' }, 'Còn 4 ngày'),
      h('span', { class: 'ec-countdown ec-today', 'data-material-accent': 'amber' }, 'Hôm nay!'),
    ]),
  })
}

async function mountCascade(tokens: Record<string, string>) {
  await installActualHomepageStyles()
  const wrapper = await mountSuspended(cascadeFixture(tokens), { attachTo: document.body })
  wrappers.push(wrapper)
  return wrapper
}

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  for (const stylesheet of stylesheets.splice(0)) stylesheet.remove()
  document.documentElement.classList.remove('dark', 'light')
  localStorage.clear()
})

describe('Homepage Nocturne computed color cascade', () => {
  it.each([
    {
      theme: 'light',
      text: 'rgb(126, 93, 29)',
      surface: 'rgb(249, 244, 232)',
    },
    {
      theme: 'dark',
      text: 'rgb(206, 167, 112)',
      surface: 'rgb(42, 41, 34)',
    },
  ])('keeps rendered Amber month text AA in $theme', async ({ theme, text, surface }) => {
    document.documentElement.classList.add(theme)
    const wrapper = await mountCascade({
      '--home-color-amber-text': text,
      '--home-color-amber-surface': surface,
      '--accent-text': 'rgb(180, 30, 30)',
      '--accent-rgb': '180, 30, 30',
    })

    const date = wrapper.get<HTMLElement>('.ec-date').element
    const month = wrapper.get<HTMLElement>('.ec-month').element
    const dateStyle = getComputedStyle(date)
    const monthStyle = getComputedStyle(month)
    expect(monthStyle.opacity).toBe('1')

    const background = rgb(dateStyle.backgroundColor)
    const renderedText = composite(rgb(monthStyle.color), background, Number(monthStyle.opacity))

    expect(dateStyle.backgroundColor).toBe(surface)
    expect(monthStyle.color).toBe(text)
    expect(contrast(renderedText, background)).toBeGreaterThanOrEqual(4.5)
  })

  it.each([
    {
      theme: 'light',
      action: 'rgb(3, 90, 105)',
      onAction: 'rgb(253, 252, 249)',
      focusOnMedia: 'rgb(253, 252, 249)',
      hero: 'rgb(8, 26, 22)',
    },
    {
      theme: 'dark',
      action: 'rgb(125, 174, 186)',
      onAction: 'rgb(7, 18, 16)',
      focusOnMedia: 'rgb(206, 167, 112)',
      hero: 'rgb(7, 18, 16)',
    },
  ])('maps action and media focus to their adjacent surfaces in $theme', async ({ theme, action, onAction, focusOnMedia, hero }) => {
    document.documentElement.classList.add(theme)
    const wrapper = await mountCascade({
      '--color-action': action,
      '--color-on-action': onAction,
      '--color-focus': theme === 'dark' ? focusOnMedia : 'rgb(3, 90, 105)',
      '--color-mask-opaque': 'rgb(0, 0, 0)',
      '--white-rgb': '255, 255, 255',
      '--black-rgb': '0, 0, 0',
    })
    const heroElement = wrapper.get<HTMLElement>('[data-test-hero]').element
    heroElement.style.backgroundColor = hero

    const search = wrapper.get<HTMLElement>('[data-home-search]').element
    const input = wrapper.get<HTMLInputElement>('[data-home-search] input').element
    input.focus()
    expect(document.activeElement).toBe(input)
    const searchStyle = getComputedStyle(search)
    const inputStyle = getComputedStyle(input)
    expect(searchStyle.backgroundColor).toBe(action)
    expect(inputStyle.outlineColor).toBe(onAction)
    expect(inputStyle.boxShadow).toContain('rgb(0, 0, 0)')
    expect(contrast(rgb(inputStyle.outlineColor), rgb(searchStyle.backgroundColor))).toBeGreaterThanOrEqual(3)

    const nearby = wrapper.get<HTMLElement>('.hero-nearby').element
    nearby.focus()
    expect(document.activeElement).toBe(nearby)
    expect(getComputedStyle(nearby).outlineColor).toBe(focusOnMedia)
    expect(getComputedStyle(nearby).boxShadow).toContain('rgb(0, 0, 0)')
    expect(contrast(rgb(getComputedStyle(nearby).outlineColor), rgb(hero))).toBeGreaterThanOrEqual(3)
  })

  it('keeps both feature actions on the semantic secondary recipe after component styles', async () => {
    const wrapper = await mountCascade({
      '--color-action': 'rgb(3, 90, 105)',
      '--color-action-border': 'rgb(2, 72, 84)',
      '--color-action-surface': 'rgb(220, 235, 238)',
      '--color-border': 'rgb(180, 180, 180)',
      '--color-text': 'rgb(8, 26, 22)',
    })

    for (const action of wrapper.findAll<HTMLElement>('[data-home-feature-action]')) {
      const style = getComputedStyle(action.element)
      expect(style.color).toBe('rgb(3, 90, 105)')
      expect(style.borderColor).toBe('rgb(2, 72, 84)')
      expect(style.backgroundColor).toBe('rgb(220, 235, 238)')
    }
  })

  it('wins the legacy dark countdown override with scoped Amber semantics', async () => {
    document.documentElement.classList.add('dark')
    const wrapper = await mountCascade({
      '--home-color-amber-text': 'rgb(206, 167, 112)',
      '--home-color-amber-surface': 'rgb(42, 41, 34)',
      '--accent-text': 'rgb(180, 30, 30)',
      '--accent-rgb': '180, 30, 30',
    })

    const style = getComputedStyle(wrapper.get<HTMLElement>('.ec-countdown').element)
    expect(style.color).toBe('rgb(206, 167, 112)')
    expect(style.backgroundColor).toBe('rgb(42, 41, 34)')
  })

  it.each([
    {
      theme: 'light',
      text: 'rgb(8, 26, 22)',
      surface: 'rgb(244, 226, 223)',
      error: 'rgb(189, 65, 63)',
    },
    {
      theme: 'dark',
      text: 'rgb(237, 235, 229)',
      surface: 'rgb(46, 43, 40)',
      error: 'rgb(223, 127, 120)',
    },
  ])('keeps the visible today label readable with a Coral status accent in $theme', async ({ theme, text, surface, error }) => {
    document.documentElement.classList.add(theme)
    const wrapper = await mountCascade({
      '--home-color-amber-text': 'rgb(133, 90, 22)',
      '--home-color-amber-surface': 'rgb(249, 244, 232)',
      '--home-color-today-surface': surface,
      '--color-text': text,
      '--color-error': error,
    })

    const today = wrapper.get<HTMLElement>('.ec-today')
    const style = getComputedStyle(today.element)
    expect(today.text()).toBe('Hôm nay!')
    expect(style.color).toBe(text)
    expect(style.backgroundColor).toBe(surface)
    expect(style.boxShadow).toContain(error)
    expect(contrast(rgb(style.color), rgb(style.backgroundColor))).toBeGreaterThanOrEqual(4.5)
  })
})
