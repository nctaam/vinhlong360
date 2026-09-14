import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import HomeNativeStories from '../components/home/HomeNativeStories.vue'
import HomeCategoryIndex from '../components/home/HomeCategoryIndex.vue'

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

describe('Home Visual Prominence & Photo-to-Text Balance', () => {
  it('ensures HomeNativeStories stories are visually driven with images and no text wall exceeds 150 chars', async () => {
    const wrapper = await mountSuspended(HomeNativeStories, {
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    // Media presence check
    const images = wrapper.findAll('img.home-story-card__img')
    expect(images.length).toBeGreaterThanOrEqual(2)

    // Paragraph brevity check to avoid text desert and ensure punchy reading
    const paragraphs = wrapper.findAll('p')
    for (const p of paragraphs) {
      expect(p.text().length).toBeLessThan(150)
    }
  })

  it('ensures HomeCategoryIndex cards prioritize media plates for all primary categories', async () => {
    const fakeGroups = {
      primary: [
        { key: 'du-lich', label: 'Du lịch', hint: 'Khám phá xứ cù lao', accent: 'river-600', to: '/du-lich', icon: 'map-pin', countLabel: '124 điểm' },
        { key: 'am-thuc', label: 'Ẩm thực', hint: 'Món ngon miệt vườn', accent: 'mangthit-600', to: '/am-thuc', icon: 'sparkle', countLabel: '58 món' },
      ],
      utility: [
        { key: 'lich-trinh', label: 'Lịch trình', hint: 'Gợi ý điền dã', accent: 'harvest-700', to: '/lich-trinh', icon: 'compass', countLabel: '12 tour' },
      ],
    }

    const wrapper = await mountSuspended(HomeCategoryIndex, {
      props: { groups: fakeGroups as any },
      global: { stubs: { IconLine: true, NuxtLink: { template: '<a><slot /></a>' } } },
    })
    wrappers.push(wrapper)

    const mediaElements = wrapper.findAll('.home-category-index__media')
    expect(mediaElements.length).toBe(fakeGroups.primary.length)

    const mediaImgs = wrapper.findAll('.home-category-index__media-img')
    expect(mediaImgs.length).toBe(fakeGroups.primary.length)

    for (const group of fakeGroups.primary) {
      expect(group.hint.length).toBeLessThanOrEqual(100)
    }
  })
})
