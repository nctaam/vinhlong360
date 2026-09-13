import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import HomeFeatureDossier from '../components/home/HomeFeatureDossier.vue'
import type { ImageDescriptor } from '../types/image'

const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: { type: String, required: true }, alt: { type: String, required: true } },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt, 'data-nuxt-img-stub': 'true' })
  },
})

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

const BASE_DESCRIPTOR: ImageDescriptor = {
  url: '/img/spread/song-nuoc.webp',
  alt: 'Sông nước Cổ Chiên',
  source_class: 'verified',
  source_kind: 'entity-editorial',
  disclosure_key: 'fieldwork-photograph',
  short_label: 'Ảnh thực địa',
  full_disclosure: 'Ảnh chụp thực địa bởi Ban biên tập vinhlong360.',
  credit: 'VinhLong360',
  width: 960,
  height: 640,
}

async function mountDossier(propsOverrides = {}) {
  const wrapper = await mountSuspended(HomeFeatureDossier, {
    props: {
      eyebrow: 'Điểm đến nổi bật',
      title: 'Lò gạch Mang Thít',
      summary: 'Vương quốc gốm đỏ bên bờ sông Thầy Kay.',
      region: 'Mang Thít',
      descriptor: BASE_DESCRIPTOR,
      disclosureId: 'dossier-disc-1',
      detailTo: '/dia-diem/mang-thit',
      sourceTier: 'official',
      ...propsOverrides,
    },
    global: {
      stubs: {
        NuxtImg: NuxtImgStub,
        IconLine: true,
      },
    },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('HomeFeatureDossier — Empirical Stress Testing', () => {
  describe('Adverse Scenario 1: Missing or null optional props', () => {
    it('renders cleanly when summary, region, plannerTo, and mapTo are omitted or null', async () => {
      const wrapper = await mountDossier({
        summary: null,
        region: null,
        plannerTo: undefined,
        mapTo: null,
        sourceTitle: null,
        sourceUrl: null,
        verifiedAt: null,
      })

      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('[data-dossier-title]').text()).toBe('Lò gạch Mang Thít')
      // No planner button rendered when plannerTo is undefined
      expect(wrapper.findAll('[data-home-feature-action]')).toHaveLength(1)
      // Coords span rendered instead of link when mapTo is null
      expect(wrapper.find('.home-feature-dossier__coords--link').exists()).toBe(false)
      expect(wrapper.find('.home-feature-dossier__coords').exists()).toBe(true)
      // Default fallback coordinates applied
      expect(wrapper.find('.home-feature-dossier__coords').text()).toContain('10.254° N, 105.972° E')
    })

    it('falls back to default coordinates when coordinates prop is null or empty', async () => {
      const wrapper = await mountDossier({ coordinates: null })
      expect(wrapper.get('.home-feature-dossier__coords').text()).toContain('10.254° N, 105.972° E')
    })
  })

  describe('Adverse Scenario 2: Media variations and empty descriptors', () => {
    it('collapses into empty media placeholder when descriptor url is empty string', async () => {
      const emptyDescriptor: ImageDescriptor = {
        ...BASE_DESCRIPTOR,
        url: '',
      }
      const wrapper = await mountDossier({ descriptor: emptyDescriptor })

      expect(wrapper.find('.home-feature-dossier__media--empty').exists()).toBe(true)
      expect(wrapper.find('a.home-feature-dossier__media').exists()).toBe(false)
    })

    it('uses NuxtImg optimization when descriptor URL is remote http/https', async () => {
      const remoteDescriptor: ImageDescriptor = {
        ...BASE_DESCRIPTOR,
        url: 'https://cdn.vinhlong360.vn/photos/mangthit.jpg',
      }
      const wrapper = await mountDossier({ descriptor: remoteDescriptor })

      const media = wrapper.get('[data-home-feature-media]')
      expect(media.find('img[data-nuxt-img-stub]').exists()).toBe(true)
    })

    it('uses standard img tag for local assets without NuxtImg overhead', async () => {
      const wrapper = await mountDossier({ descriptor: BASE_DESCRIPTOR })
      const media = wrapper.get('[data-home-feature-media]')
      expect(media.find('img[data-nuxt-img-stub]').exists()).toBe(false)
      expect(media.find('img').exists()).toBe(true)
    })
  })

  describe('Adverse Scenario 3: Adversarial XSS & template integrity', () => {
    it('safely escapes hostile script injection in title and summary', async () => {
      const hostileTitle = '<script>alert("xss")</script>Test & Title'
      const hostileSummary = '"><img src=x onerror=alert(1)>'
      const wrapper = await mountDossier({
        title: hostileTitle,
        summary: hostileSummary,
      })

      // Verify no script or unescaped img elements were injected into DOM
      expect(wrapper.find('script').exists()).toBe(false)
      expect(wrapper.find('img[onerror]').exists()).toBe(false)
      expect(wrapper.get('[data-dossier-title]').text()).toBe(hostileTitle)
      expect(wrapper.get('.framed-dossier__summary').text()).toBe(hostileSummary)
      expect(wrapper.html()).not.toContain('{{')
      expect(wrapper.html()).not.toContain('}}')
    })
  })

  describe('Adverse Scenario 4: Touch targets & ergonomic contracts', () => {
    it('ensures action buttons and coordinates link meet ergonomic standards', async () => {
      const wrapper = await mountDossier({
        plannerTo: '/tao-lich-trinh?add=mang-thit',
        mapTo: '/ban-do?selected=mang-thit',
      })

      // Action links
      const actions = wrapper.findAll('[data-home-feature-action]')
      expect(actions).toHaveLength(2)
      expect(actions[0].attributes('href')).toBe('/dia-diem/mang-thit')
      expect(actions[1].attributes('href')).toBe('/tao-lich-trinh?add=mang-thit')

      // Coords link
      const coordsLink = wrapper.get('.home-feature-dossier__coords--link')
      expect(coordsLink.exists()).toBe(true)
      expect(coordsLink.attributes('href')).toBe('/ban-do?selected=mang-thit')
    })
  })
})
