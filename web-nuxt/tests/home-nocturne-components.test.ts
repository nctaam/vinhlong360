import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import HomeCategoryIndex from '../components/home/HomeCategoryIndex.vue'
import HomeDecisionLedger from '../components/home/HomeDecisionLedger.vue'
import HomeFeatureDossier from '../components/home/HomeFeatureDossier.vue'
import type { ImageDescriptor } from '../types/image'
import { createHomeNocturnePresentation } from '../utils/homeNocturnePresentation'

const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: { type: String, required: true }, alt: { type: String, required: true } },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt, 'data-nuxt-img-stub': 'true' })
  },
})
const wrappers: Array<{ unmount: () => void }> = []

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
})

const descriptor: ImageDescriptor = {
  url: '/img/hero.webp',
  alt: 'Vườn cây ven sông',
  source_class: 'ai-generated',
  source_kind: 'entity-editorial',
  disclosure_key: 'entity-ai',
  short_label: 'Ảnh minh họa',
  full_disclosure: 'Ảnh minh họa do AI dựng, không phải ảnh chụp tại hiện trường.',
  credit: null,
  width: 960,
  height: 640,
}

describe('homepage Nocturne presentation components', () => {
  it('renders only supplied feature anatomy and keeps disclosure attached to media', async () => {
    const wrapper = await mountSuspended(HomeFeatureDossier, {
      props: {
        eyebrow: 'Trải nghiệm tại Long Hồ',
        title: 'Một buổi trong vườn',
        summary: 'Đi chậm giữa vườn cây và rạch nhỏ.',
        region: 'Long Hồ',
        descriptor,
        disclosureId: 'home-feature-disclosure',
        detailTo: '/dia-diem/hero-1',
        plannerTo: '/tao-lich-trinh?add=hero-1',
        sourceTier: 'official',
      },
      global: { stubs: { NuxtImg: NuxtImgStub, IconLine: true } },
    })
    wrappers.push(wrapper)

    const media = wrapper.get('[data-home-feature-media]')
    const image = media.get('img')
    expect(image.attributes('data-nuxt-img-stub')).toBeUndefined()
    expect(image.attributes('aria-describedby')).toBe('home-feature-disclosure')
    expect(image.attributes('width')).toBe('960')
    expect(image.attributes('height')).toBe('640')
    expect(image.attributes('loading')).toBe('eager')
    expect(image.attributes('fetchpriority')).toBe('high')
    expect(wrapper.get('#home-feature-disclosure').text()).toBe(descriptor.full_disclosure)
    expect(wrapper.get('[data-dossier-title]').text()).toBe('Một buổi trong vườn')
    expect(wrapper.findAll('[data-home-feature-action]')).toHaveLength(2)
    expect(wrapper.get('[data-source-mark]').text()).toContain('Chính thức')
    expect(wrapper.get('[data-source-mark]').attributes('data-source-tier')).toBe('official')
    expect(wrapper.findAll('[data-home-feature-action]').map(action => action.attributes('data-color-role'))).toEqual([
      'action-secondary',
      'action-secondary',
    ])
    expect(wrapper.find('[data-rating]').exists()).toBe(false)
  })

  it('uses Nuxt image optimization for remote feature media', async () => {
    const wrapper = await mountSuspended(HomeFeatureDossier, {
      props: {
        eyebrow: 'Trải nghiệm ven sông',
        title: 'Một chiều trên bến',
        descriptor: {
          ...descriptor,
          url: 'https://images.example.com/hero.webp',
        },
        disclosureId: 'home-feature-remote-disclosure',
        detailTo: '/dia-diem/remote-hero',
        sourceTier: 'verified',
      },
      global: { stubs: { NuxtImg: NuxtImgStub, IconLine: true } },
    })
    wrappers.push(wrapper)

    const image = wrapper.get('[data-home-feature-media] img')
    expect(image.attributes('data-nuxt-img-stub')).toBe('true')
    expect(image.attributes('src')).toBe('https://images.example.com/hero.webp')
    expect(image.attributes('aria-describedby')).toBe('home-feature-remote-disclosure')
    expect(image.attributes('width')).toBe('960')
    expect(image.attributes('height')).toBe('640')
    expect(image.attributes('sizes')).toBe('375px sm:540px md:640px')
    expect(image.attributes('loading')).toBe('eager')
    expect(image.attributes('fetchpriority')).toBe('high')
  })

  it('preserves feature geometry and disclosure when no image URL is supplied', async () => {
    const wrapper = await mountSuspended(HomeFeatureDossier, {
      props: {
        eyebrow: 'Gợi ý nổi bật',
        title: 'Điểm đến đang cập nhật ảnh',
        descriptor: {
          ...descriptor,
          url: null,
          source_class: 'placeholder',
          source_kind: 'generated-placeholder',
          disclosure_key: 'entity-placeholder',
          short_label: 'Ảnh đại diện đang cập nhật',
          full_disclosure: 'Hình đại diện tạm thời trong khi ảnh thực tế đang được cập nhật.',
        },
        disclosureId: 'home-feature-placeholder',
        detailTo: '/dia-diem/placeholder-1',
        sourceTier: 'unknown',
      },
      global: { stubs: { NuxtImg: NuxtImgStub, IconLine: true } },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[data-home-feature-media]').classes()).toContain('home-feature-dossier__media--empty')
    expect(wrapper.find('[data-home-feature-media] img').exists()).toBe(false)
    expect(wrapper.get('#home-feature-placeholder').text()).toContain('Hình đại diện tạm thời')
    expect(wrapper.findAll('[data-home-feature-action]')).toHaveLength(1)
  })

  it('renders an unnumbered deterministic decision ledger', async () => {
    const wrapper = await mountSuspended(HomeDecisionLedger, {
      props: {
        entries: [
          { id: 'event-1', eyebrow: 'Ngày mai', title: 'Có lịch gần nhất', text: 'Lễ hội sông nước', to: '/dia-diem/event-1', tone: 'event' },
          { id: 'season-1', eyebrow: 'Tháng 8', title: 'Đang vào mùa', text: 'Chôm chôm', to: '/theo-mua?mua=8', tone: 'season' },
        ],
      },
    })
    wrappers.push(wrapper)

    expect(wrapper.find('ol').exists()).toBe(false)
    const rows = wrapper.findAll('[data-home-decision-entry]')
    expect(rows.map(row => row.get('.home-decision-ledger__eyebrow').text())).toEqual(['Ngày mai', 'Tháng 8'])
    expect(rows.map(row => row.get('.home-decision-ledger__title').text())).toEqual(['Có lịch gần nhất', 'Đang vào mùa'])
    expect(rows.map(row => row.get('.home-decision-ledger__text').text())).toEqual(['Lễ hội sông nước', 'Chôm chôm'])
    expect(rows.map(row => row.get('.home-decision-ledger__link').attributes('data-material-accent'))).toEqual(['amber', 'amber'])
    expect(wrapper.text()).not.toMatch(/\b0[1-9]\b/)
  })

  it('renders primary and utility routes exactly once', async () => {
    const { categoryGroups } = createHomeNocturnePresentation({
      currentMonth: 8,
      upcomingEvents: [],
      seasonal: [],
      topDishes: [],
      itineraries: [],
      categoryCounts: { experiences: 5, areas: 3 },
    })
    const wrapper = await mountSuspended(HomeCategoryIndex, {
      props: { groups: categoryGroups },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[data-home-category-primary]').text()).toContain('5 gợi ý')
    expect(wrapper.get('[data-home-category-utility]').text()).not.toContain('gợi ý')
    expect(wrapper.findAll('a').map(link => link.attributes('href'))).toEqual([
      '/du-lich',
      '/kham-pha/am-thuc',
      '/ocop',
      '/le-hoi',
      '/luu-tru',
      '/lich-trinh',
      '/ban-do',
    ])
    expect(wrapper.findAll('a').map(link => link.attributes('data-material-accent'))).toEqual([
      'leaf',
      'amber',
      'clay',
      'amber',
      'river',
      'river',
      'river',
    ])
  })
})
