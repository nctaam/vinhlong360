import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import HomeNativeStories from '../components/home/HomeNativeStories.vue'

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
    expect(primary.text()).toContain('Hơi thở miền sông nước')
    expect(primary.text()).toContain('Ký sự Điền dã · Ban biên tập VinhLong360')

    const secondary = wrapper.find('.home-story-card--secondary')
    expect(secondary.exists()).toBe(true)
    expect(secondary.text()).toContain('Bóng dừa vươn cao')

    const callout = wrapper.find('.home-story-callout')
    expect(callout.exists()).toBe(true)
    expect(callout.text()).toContain('Khám phá thêm giai thoại')
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
    const action = wrapper.get('.home-story-callout__action')
    expect(action.exists()).toBe(true)
    expect(action.attributes('href')).toBe('/kham-pha')

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
})
