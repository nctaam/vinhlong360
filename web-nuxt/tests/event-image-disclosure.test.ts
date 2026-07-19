import { mountSuspended } from '@nuxt/test-utils/runtime'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineComponent, h } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LeHoiPage from '../pages/le-hoi.vue'
import SuKienPage from '../pages/su-kien.vue'
import { aiDisclosure } from '../utils/aiDisclosure'

const apiFetchMock = vi.hoisted(() => vi.fn())
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))

const fixtureEvents = [
  {
    id: 'local/event one',
    type: 'event',
    name: 'Lễ hội ảnh địa phương',
    summary: 'Ảnh nội bộ',
    images: ['/img/events/local.webp'],
    attributes: { category: 'le-hoi', date_start: '2099-01-02', date_end: '2099-01-03' },
  },
  {
    id: 'remote/event-two',
    type: 'event',
    name: 'Lễ hội ảnh từ xa',
    summary: 'Ảnh CDN',
    images: ['https://cdn.example.test/events/remote.webp'],
    attributes: { category: 'le-hoi', date_start: '2099-02-02', date_end: '2099-02-03' },
  },
  {
    id: 'unsafe/event-three',
    type: 'event',
    name: 'Lễ hội ảnh không an toàn',
    images: ['javascript:alert(1)'],
    attributes: { category: 'le-hoi', date_start: '2099-03-02', date_end: '2099-03-03' },
  },
  {
    id: 'missing/event-four',
    type: 'event',
    name: 'Lễ hội chưa có ảnh',
    attributes: { category: 'le-hoi', date_start: '2099-04-02', date_end: '2099-04-03' },
  },
  {
    id: 'event/five',
    type: 'event',
    name: 'Sự kiện minh họa',
    images: ['/img/events/event.webp'],
    attributes: { category: 'su-kien', date_start: '2099-05-02', date_end: '2099-05-03' },
  },
  {
    id: 'remote/event-six',
    type: 'event',
    name: 'Sự kiện ảnh từ xa',
    images: ['https://cdn.example.test/events/event-remote.webp'],
    attributes: { category: 'su-kien', date_start: '2099-06-02', date_end: '2099-06-03' },
  },
  {
    id: 'unsafe/event-seven',
    type: 'event',
    name: 'Sự kiện ảnh không an toàn',
    images: ['javascript:alert(2)'],
    attributes: { category: 'su-kien', date_start: '2099-07-02', date_end: '2099-07-03' },
  },
  {
    id: 'missing/event-eight',
    type: 'event',
    name: 'Sự kiện chưa có ảnh',
    attributes: { category: 'su-kien', date_start: '2099-08-02', date_end: '2099-08-03' },
  },
]

const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: { type: String, required: true }, alt: { type: String, required: true } },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})

const NuxtLinkStub = defineComponent({
  inheritAttrs: false,
  setup(_, { attrs, slots }) {
    return () => h('a', attrs, slots.default?.())
  },
})

const globals = {
  stubs: {
    NuxtImg: NuxtImgStub,
    NuxtLink: NuxtLinkStub,
    Breadcrumb: true,
    CountUp: true,
    CatalogSpotlight: true,
    CatalogInterstitial: true,
    FilterChips: true,
    EmptyState: true,
    SkeletonGrid: true,
    SkeletonList: true,
    IconLine: true,
  },
}

beforeEach(() => {
  apiFetchMock.mockResolvedValue({ events: fixtureEvents })
})

async function mountPage(page: typeof LeHoiPage | typeof SuKienPage) {
  return mountSuspended(page, { global: globals })
}

describe.each([
  ['le-hoi', LeHoiPage, ['/img/events/local.webp', 'https://cdn.example.test/events/remote.webp']],
  ['su-kien', SuKienPage, ['/img/events/event.webp', 'https://cdn.example.test/events/event-remote.webp']],
 ] as const)('%s event imagery disclosure', (_name, Page, expectedUrls) => {
  it('renders canonical local and HTTPS URLs with visible AI label and exact full disclosure association', async () => {
    const wrapper = await mountPage(Page)
    const images = wrapper.findAll('.event-thumb img')
    expect(wrapper.findAll('[data-event-image]')).toHaveLength(images.length)
    expect(images.map(image => image.attributes('src'))).toEqual(expect.arrayContaining([...expectedUrls]))

    const disclosures = wrapper.findAll('.event-media [data-full-disclosure]')
    expect(disclosures).toHaveLength(images.length)
    expect(new Set(disclosures.map(disclosure => disclosure.attributes('id'))).size).toBe(disclosures.length)
    for (const image of images) {
      const id = image.attributes('aria-describedby')
      expect(id).toBeTruthy()
      expect(wrapper.get(`#${id}`).text()).toBe(aiDisclosure.entity_ai.full_disclosure)
    }
    expect(wrapper.findAll('[data-short-label]').some(node => node.text() === aiDisclosure.entity_ai.short_label)).toBe(true)
  })

  it('does not render empty image sources for malformed, unsafe, or missing imagery', async () => {
    const wrapper = await mountPage(Page)
    expect(wrapper.findAll('.event-thumb img').every(image => Boolean(image.attributes('src')))).toBe(true)
    expect(wrapper.text()).not.toContain('javascript:alert(1)')
    expect(wrapper.findAll('.event-thumb').length).toBeGreaterThan(0)
  })
})

describe('event image disclosure source boundaries', () => {
  it('uses shared descriptor classification instead of direct legacy image rendering', () => {
    for (const file of ['pages/le-hoi.vue', 'pages/su-kien.vue']) {
      const source = readFileSync(resolve(process.cwd(), file), 'utf8')
      expect(source).toContain('describeEntityImages')
      expect(source).toContain('describeEntityPlaceholder')
      expect(source).not.toMatch(/e\.images\?\.\[0\]/)
      expect(source).not.toMatch(/e\.images\s*\[\s*0\s*\]/)
    }
  })
})

describe('map popup no-image invariant', () => {
  it('marks popup roots as no-image and keeps imagery out of the HTML contract', () => {
    const source = readFileSync(resolve(process.cwd(), 'pages/ban-do.vue'), 'utf8')
    const popupStart = source.indexOf('function popupHTML')
    const popupEnd = source.indexOf('// GĐ10.4', popupStart)
    const popupFunction = popupStart >= 0 && popupEnd > popupStart ? source.slice(popupStart, popupEnd) : ''
    expect(popupFunction).toContain('data-entity-image-policy="no-image-invariant"')
    expect(popupFunction).not.toMatch(/<img|NuxtImg|background-image|image\s*[:(]/i)
    expect(popupFunction).not.toMatch(/image\s*[,(]/i)
  })
})
