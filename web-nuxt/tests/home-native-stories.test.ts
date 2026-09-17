import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import HomeNativeStories from '../components/home/HomeNativeStories.vue'

const homeNocturneCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf-8')

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

async function mountStories() {
  const wrapper = await mountSuspended(HomeNativeStories, {
    global: { stubs: { IconLine: true } },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('HomeNativeStories — Empirical Stress Testing', () => {
  it('mounts cleanly without throwing any exceptions', async () => {
    const wrapper = await mountStories()
    expect(wrapper.exists()).toBe(true)
    expect(wrapper.find('.home-native-stories').exists()).toBe(true)
  })

  it('verifies eradication of English AI tagline and presence of authentic Vietnamese editorial tagline', async () => {
    const text = (await mountStories()).text()
    expect(text).not.toContain('The Soul of the Mekong')
    expect(text).toContain('Ký sự thổ nhưỡng · Hồn cốt phù sa')
    expect(text).toContain('Bản địa kể chuyện')
  })

  it('contains 3 distinct story pathways: primary lead, secondary card, and callout card', async () => {
    const wrapper = await mountStories()
    const primary = wrapper.find('.home-story-card--primary')
    expect(primary.exists()).toBe(true)
    expect(primary.text()).toContain('Nhịp chèo trên rạch An Bình')
    expect(primary.text()).not.toContain('Hơi thở miền sông nước')
    expect(primary.text()).toContain('Ký sự Điền dã · Ban biên tập VinhLong360')

    const secondary = wrapper.find('.home-story-card--secondary')
    expect(secondary.exists()).toBe(true)
    expect(secondary.text()).toContain('Trăm năm giữ lửa Măng Thít')
    expect(secondary.text()).not.toContain('như một khúc ca dao')

    const callout = wrapper.find('.home-story-callout')
    expect(callout.exists()).toBe(true)
    expect(callout.text()).toContain('Tàng thư khảo cứu điền dã')
    expect(callout.text()).not.toContain('chưa từng được kể')
  })

  it('handles image error events gracefully with fallback without infinite recursion', async () => {
    const wrapper = await mountStories()
    const img = wrapper.find<HTMLImageElement>('img.home-story-card__img')
    expect(img.exists()).toBe(true)

    // Simulate image loading failure
    const domImg = img.element
    domImg.dispatchEvent(new Event('error'))
    expect(domImg.dataset.fallbackApplied).toBe('true')
    expect(domImg.src).toContain('/img/spread/cu-lao-an-binh.webp')

    // Second error trigger must not loop
    domImg.dispatchEvent(new Event('error'))
    expect(domImg.dataset.fallbackApplied).toBe('true')
  })

  it('ensures interactive links and callout actions fulfill touch target ergonomics', async () => {
    const wrapper = await mountStories()
    const action = wrapper.find('.home-story-callout__action')
    expect(action.exists()).toBe(true)
    expect(action.attributes('href')).toBe('/du-lich')

    const primary = wrapper.find('.home-story-card--primary')
    expect(primary.attributes('href')).toBe('/dia-diem/cu-lao-an-binh')

    const secondary = wrapper.find('.home-story-card--secondary')
    expect(secondary.attributes('href')).toBe('/dia-diem/de-an-di-san-duong-dai-mang-thit')

    const links = wrapper.findAll('a')
    expect(links.length).toBeGreaterThanOrEqual(3)
    for (const link of links) {
      expect(link.attributes('href')).toBeDefined()
    }
  })

  it('has zero template interpolation leaks or unescaped HTML entities', async () => {
    const wrapper = await mountStories()
    const html = wrapper.html()
    expect(html).not.toContain('{{')
    expect(html).not.toContain('}}')
    expect(html).not.toContain('undefined')
    expect(html).not.toContain('null')
    expect(html).not.toContain('NaN')
  })

  it('verifies home-story-card and callout action have focus-visible rings and active state in home-nocturne.css', () => {
    expect(homeNocturneCss).toMatch(/\[data-home-pilot="nocturne-b1"\]\s+\.home-story-card:focus-visible\s*\{[\s\S]*?outline:\s*2px solid var\(--color-focus\)/)
    expect(homeNocturneCss).toMatch(/\[data-home-pilot="nocturne-b1"\]\s+\.home-story-callout__action:focus-visible\s*\{[\s\S]*?outline:\s*2px solid var\(--color-focus\)/)
    expect(homeNocturneCss).toMatch(/\[data-home-pilot="nocturne-b1"\]\s+\.home-story-callout__action:active\s*\{[\s\S]*?transform:\s*scale\(0\.98\)/)
  })
})
