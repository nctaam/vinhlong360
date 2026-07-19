import { mountSuspended } from '@nuxt/test-utils/runtime'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineComponent, h } from 'vue'
import { describe, expect, it } from 'vitest'
import EntityCard from '../components/EntityCard.vue'
import EntityFeature from '../components/home/EntityFeature.vue'
import { aiDisclosure } from '../utils/aiDisclosure'
import type { ImageDescriptor } from '../types/image'

const ai = (url: string, alt = 'Điểm đến — ảnh minh họa'): ImageDescriptor => ({
  url,
  alt,
  source_class: 'ai-generated',
  source_kind: 'entity-editorial',
  disclosure_key: 'entity-ai',
  short_label: aiDisclosure.entity_ai.short_label,
  full_disclosure: aiDisclosure.entity_ai.full_disclosure,
  credit: null,
  width: null,
  height: null,
})

const placeholder: ImageDescriptor = {
  url: null,
  alt: 'Điểm đến — chưa có ảnh riêng',
  source_class: 'placeholder',
  source_kind: 'generated-placeholder',
  disclosure_key: 'entity-placeholder',
  short_label: null,
  full_disclosure: aiDisclosure.placeholder.full_disclosure,
  credit: null,
  width: null,
  height: null,
}

const entity = (overrides: Record<string, unknown> = {}) => ({
  id: 'entity-1',
  type: 'place',
  name: 'Điểm đến',
  summary: 'Một nơi đáng ghé trong ngày.',
  ...overrides,
})

const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: { type: String, required: true }, alt: { type: String, required: true } },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt, 'data-remote-image': 'true' })
  },
})

const globals = {
  stubs: {
    NuxtImg: NuxtImgStub,
    SaveButton: true,
    IconLine: true,
  },
}

describe('EntityCard image disclosure', () => {
  it('uses a supplied descriptor over a conflicting legacy URL and associates the full copy', async () => {
    const supplied = ai('/descriptor.webp')
    const wrapper = await mountSuspended(EntityCard, {
      props: { entity: entity({ images: ['/legacy.webp'], image_descriptor: supplied }) },
      global: globals,
    })

    const image = wrapper.get('img')
    expect(image.attributes('src')).toBe('/descriptor.webp')
    const disclosure = wrapper.get('[data-full-disclosure]')
    expect(disclosure.text()).toBe(aiDisclosure.entity_ai.full_disclosure)
    expect(image.attributes('aria-describedby')).toBe(disclosure.attributes('id'))
    expect(wrapper.get('[data-image-disclosure]').text()).toContain(aiDisclosure.entity_ai.short_label)
  })

  it('classifies legacy entity images as AI with the exact canonical copy', async () => {
    const wrapper = await mountSuspended(EntityCard, {
      props: { entity: entity({ images: ['/legacy.webp'] }) },
      global: globals,
    })

    expect(wrapper.get('img').attributes('src')).toBe('/legacy.webp')
    expect(wrapper.get('[data-full-disclosure]').text()).toBe(aiDisclosure.entity_ai.full_disclosure)
    expect(wrapper.get('[data-image-disclosure]').text()).toContain('Minh họa AI')
  })

  it('keeps disclosure and local/remote rendering tied to the active carousel slide', async () => {
    const wrapper = await mountSuspended(EntityCard, {
      props: { entity: entity({ image_descriptors: [ai('/local.webp'), ai('https://cdn.example/remote.webp')] }) },
      global: globals,
    })

    const firstDisclosureId = wrapper.get('[data-full-disclosure]').attributes('id')
    expect(wrapper.get('img').attributes('src')).toBe('/local.webp')
    expect(wrapper.get('img').attributes('data-remote-image')).toBeUndefined()

    await wrapper.get('.card-arrow-next').trigger('click')
    const remote = wrapper.get('img')
    const secondDisclosure = wrapper.get('[data-full-disclosure]')
    expect(remote.attributes('src')).toBe('https://cdn.example/remote.webp')
    expect(remote.attributes('data-remote-image')).toBe('true')
    expect(secondDisclosure.attributes('id')).not.toBe(firstDisclosureId)
    expect(remote.attributes('aria-describedby')).toBe(secondDisclosure.attributes('id'))

    await remote.trigger('error')
    expect(wrapper.get('[data-full-disclosure]').text()).toBe(aiDisclosure.placeholder.full_disclosure)
    expect(wrapper.find('[data-short-label]').exists()).toBe(false)
    await wrapper.get('.card-arrow-prev').trigger('click')
    expect(wrapper.get('img').attributes('src')).toBe('/local.webp')
  })

  it('renders the canonical placeholder, without an AI label, for no-image and unsafe-image entities', async () => {
    for (const images of [undefined, ['javascript:alert(1)']]) {
      const wrapper = await mountSuspended(EntityCard, {
        props: { entity: entity({ images }) },
        global: globals,
      })
      expect(wrapper.get('.cover-generated').text()).toContain(aiDisclosure.placeholder.full_disclosure)
      expect(wrapper.find('[data-short-label]').exists()).toBe(false)
      expect(wrapper.find('img').exists()).toBe(false)
    }
  })

  it('creates safe unique disclosure ids for repeated cards', async () => {
    const Harness = defineComponent({
      setup() {
        return () => h('div', [
          h(EntityCard, { entity: entity({ id: 'unsafe/id' }) }),
          h(EntityCard, { entity: entity({ id: 'unsafe/id' }) }),
        ])
      },
    })
    const wrapper = await mountSuspended(Harness, { global: globals })
    const ids = wrapper.findAll('[data-full-disclosure]').map(node => node.attributes('id'))
    expect(ids).toHaveLength(2)
    expect(new Set(ids).size).toBe(2)
    expect(ids.every(id => /^[A-Za-z][A-Za-z0-9_-]*$/.test(id || ''))).toBe(true)
  })
})

describe('EntityFeature image disclosure', () => {
  it('uses a descriptor for its background and associates the full disclosure copy', async () => {
    const descriptor = ai('/img/features/trai-nghiem.webp', 'Trải nghiệm miệt vườn — ảnh minh họa')
    const wrapper = await mountSuspended(EntityFeature, {
      props: {
        image: descriptor,
        kicker: 'Trải nghiệm',
        title: 'Miệt vườn mở cửa đón bạn',
        lede: 'Những ngày chậm rãi rất Nam Bộ.',
        ctaText: 'Khám phá',
        ctaTo: '/du-lich',
      },
      global: globals,
    })

    const background = wrapper.get('[data-background-image]')
    const disclosure = wrapper.get('[data-full-disclosure]')
    expect(background.attributes('role')).toBe('img')
    expect(background.attributes('aria-label')).toBe(descriptor.alt)
    expect(background.attributes('aria-describedby')).toBe(disclosure.attributes('id'))
    expect(background.attributes('style')).toContain('trai-nghiem.webp')
  })
})

describe('Task36 image boundaries', () => {
  it('keeps home feature, spotlight, for-you, and contextual recommendation sinks descriptor-based', () => {
    const source = readFileSync(resolve(__dirname, '../pages/index.vue'), 'utf8')
    expect(source).not.toMatch(/spotlight\.value\?\.images\?\.\[0\]/)
    expect(source).not.toMatch(/heroFeature\.value\?\.images\?\.\[0\]/)
    expect(source).not.toMatch(/push\(e\.id, e\.name, e\.type, e\.images\?\.\[0\]/)
    expect(source).not.toMatch(/v-if="item\.image\s*&&/)
    expect(source).toContain(':aria-describedby="item.disclosureId"')
    expect(source).toContain(':id="item.disclosureId"')
    expect(source).toContain('SPOT_CAT_PHOTO')
    expect(source).toContain('EntityFeature')
  })

  it('keeps nearby and recommendation surfaces delegated through EntityCard', () => {
    for (const file of ['components/NearbyEntities.vue', 'components/SmartRecommendations.vue', 'components/AIRecommendations.vue']) {
      const source = readFileSync(resolve(__dirname, '..', file), 'utf8')
      expect(source).toContain('<EntityCard')
    }
  })
})
