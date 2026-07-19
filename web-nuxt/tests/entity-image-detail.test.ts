import { mountSuspended } from '@nuxt/test-utils/runtime'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineComponent, h } from 'vue'
import { describe, expect, it } from 'vitest'
import EntityHeroPlaceholder from '../components/EntityHeroPlaceholder.vue'
import ImageDisclosure from '../components/ImageDisclosure.vue'
import { currentGalleryDescriptors, type GalleryDescriptorCarrier } from '../utils/entityGallery'
import { aiDisclosure } from '../utils/aiDisclosure'
import type { ImageDescriptor } from '../types/image'

const aiDescriptor: ImageDescriptor = {
  url: '/img/entity.webp',
  alt: 'Chùa Vàm Ray — ảnh minh họa 1',
  source_class: 'ai-generated',
  source_kind: 'entity-editorial',
  disclosure_key: 'entity-ai',
  short_label: aiDisclosure.entity_ai.short_label,
  full_disclosure: aiDisclosure.entity_ai.full_disclosure,
  credit: null,
  width: null,
  height: null,
}

const placeholderDescriptor: ImageDescriptor = {
  url: null,
  alt: 'Chùa Vàm Ray — chưa có ảnh riêng',
  source_class: 'placeholder',
  source_kind: 'generated-placeholder',
  disclosure_key: 'entity-placeholder',
  short_label: aiDisclosure.placeholder.short_label,
  full_disclosure: aiDisclosure.placeholder.full_disclosure,
  credit: null,
  width: null,
  height: null,
}

describe('ImageDisclosure', () => {
  it('associates the visible short label with deterministic full disclosure text', async () => {
    const wrapper = await mountSuspended(ImageDisclosure, {
      props: { id: 'entity-abc-hero-0', descriptor: aiDescriptor, presentation: 'short' },
    })

    const description = wrapper.get('[data-full-disclosure]')
    expect(description.attributes('id')).toBe('entity-abc-hero-0')
    expect(description.text()).toBe(aiDisclosure.entity_ai.full_disclosure)
    expect(wrapper.get('[data-short-label]').text()).toBe(aiDisclosure.entity_ai.short_label)
    expect(wrapper.get('[data-disclosure-target]').attributes('aria-describedby')).toBe('entity-abc-hero-0')
  })

  it('renders the exact placeholder disclosure when no short label exists', async () => {
    const wrapper = await mountSuspended(ImageDisclosure, {
      props: { id: 'entity-abc-placeholder', descriptor: placeholderDescriptor, presentation: 'short' },
    })

    expect(wrapper.get('[data-disclosure-target]').text()).toBe(aiDisclosure.placeholder.full_disclosure)
    expect(wrapper.find('[data-short-label]').exists()).toBe(false)
  })

  it('generates unique SSR-safe ids when callers omit an id', async () => {
    const Harness = defineComponent({
      setup() {
        return () => h('div', [
          h(ImageDisclosure, { descriptor: aiDescriptor, presentation: 'short' }),
          h(ImageDisclosure, { descriptor: placeholderDescriptor, presentation: 'short' }),
        ])
      },
    })
    const wrapper = await mountSuspended(Harness)
    const ids = wrapper.findAll('[data-full-disclosure]').map(node => node.attributes('id'))

    expect(ids).toHaveLength(2)
    expect(new Set(ids).size).toBe(2)
    expect(ids.every(id => /^image-disclosure-[A-Za-z0-9_-]+$/.test(id || ''))).toBe(true)
    expect(wrapper.findAll('[data-disclosure-target]').map(node => node.attributes('aria-describedby'))).toEqual(ids)
  })

  it('sanitizes explicit ids without changing the disclosure association', async () => {
    const wrapper = await mountSuspended(ImageDisclosure, {
      props: { id: 'entity/[unsafe] hero', descriptor: aiDescriptor, presentation: 'short' },
    })
    const id = wrapper.get('[data-full-disclosure]').attributes('id')

    expect(id).toMatch(/^[A-Za-z][A-Za-z0-9_-]*$/)
    expect(id).not.toContain('[')
    expect(wrapper.get('[data-disclosure-target]').attributes('aria-describedby')).toBe(id)
  })

  it('maps detail hero and every rail target to its rendered disclosure node', async () => {
    const railDescriptors = [
      aiDescriptor,
      { ...aiDescriptor, url: '/img/entity-2.webp', alt: 'Chùa Vàm Ray — ảnh minh họa 2' },
    ]
    const Harness = defineComponent({
      setup() {
        return () => h('section', [
          h('figure', { 'data-entity-hero': true, 'aria-describedby': 'detail-hero-disclosure' }, [
            h('img', { alt: aiDescriptor.alt }),
            h(ImageDisclosure, { id: 'detail-hero-disclosure', descriptor: aiDescriptor, presentation: 'short' }),
          ]),
          h('div', { class: 'dc-thumbs' }, railDescriptors.map((descriptor, index) => {
            const disclosureId = `detail-rail-disclosure-${index}`
            return h('button', {
              class: 'dc-thumb-btn',
              'aria-describedby': disclosureId,
            }, [
              h('img', { alt: descriptor.alt }),
              h(ImageDisclosure, { id: disclosureId, descriptor, presentation: 'short' }),
            ])
          })),
        ])
      },
    })

    const wrapper = await mountSuspended(Harness)
    const disclosures = wrapper.findAll('[data-full-disclosure]')
    const disclosureById = new Map(disclosures.map(node => [node.attributes('id'), node]))
    const hero = wrapper.get('[data-entity-hero]')
    const heroDisclosureId = hero.attributes('aria-describedby')

    expect(heroDisclosureId).toBe('detail-hero-disclosure')
    expect(disclosureById.get(heroDisclosureId)?.text()).toBe(aiDisclosure.entity_ai.full_disclosure)
    expect(hero.text()).toContain(aiDisclosure.entity_ai.short_label)

    const railButtons = wrapper.findAll('.dc-thumb-btn')
    const railDisclosureIds = railButtons.map(button => button.attributes('aria-describedby'))
    expect(new Set(railDisclosureIds).size).toBe(railButtons.length)
    for (const [index, button] of railButtons.entries()) {
      const disclosureId = railDisclosureIds[index]
      expect(disclosureId).toBeTruthy()
      expect(disclosureById.get(disclosureId)?.text()).toBe(aiDisclosure.entity_ai.full_disclosure)
      expect(button.get('img').attributes('alt')).toBe(railDescriptors[index]?.alt)
    }
  })

  it('leaves placeholder disclosure rendering to the detail ImageDisclosure when descriptor is supplied', async () => {
    const wrapper = await mountSuspended(EntityHeroPlaceholder, {
      props: { id: 'entity-placeholder', cat: 'place', descriptor: placeholderDescriptor },
    })

    expect(wrapper.find('.ehp-note').exists()).toBe(false)
    expect(wrapper.get('[role="img"]').attributes('aria-label')).toBe(placeholderDescriptor.alt)
  })
})

describe('entity detail image descriptor boundary', () => {
  const detailSource = readFileSync(resolve(process.cwd(), 'pages/dia-diem/[id].vue'), 'utf8')

  it('loads and strictly parses the Task33 gallery descriptor response', () => {
    expect(detailSource).toContain('/api/entities/${encodedId.value}/gallery')
    expect(detailSource).toMatch(/interface GalleryResponse[\s\S]*images:\s*unknown\[\]/)
    expect(detailSource).toContain('apiFetch<GalleryResponse>')
    expect(detailSource).toContain('Array.isArray(response.images)')
    expect(detailSource).toContain('response.images.flatMap')
    expect(detailSource).toContain('parseGalleryDescriptor')
    expect(detailSource).toContain('catch { return { requestId, descriptors: [] } }')
    expect(detailSource).toContain('normalizeRenderableImageUrl(raw)')
    expect(detailSource).toContain('source_class: \'ai-generated\'')
    expect(detailSource).toContain('source_kind: \'entity-editorial\'')
    expect(detailSource).toContain('requestId')
    expect(detailSource).toContain('currentGalleryDescriptors')
  })

  it('does not render a stale gallery carrier after a route change', () => {
    const entityA: GalleryDescriptorCarrier = {
      requestId: 'entity-a',
      descriptors: [aiDescriptor],
    }
    const entityBDescriptor = { ...aiDescriptor, url: '/img/entity-b.webp', alt: 'Entity B — ảnh minh họa 1' }
    const entityB: GalleryDescriptorCarrier = {
      requestId: 'entity-b',
      descriptors: [entityBDescriptor],
    }

    expect(currentGalleryDescriptors(entityA, 'entity-b')).toEqual([])
    expect(currentGalleryDescriptors(entityB, 'entity-b')).toEqual([entityBDescriptor])
    expect(detailSource).toContain('galleryCarrier.value')
  })

  it('keeps descriptors authoritative through the hero and rail', () => {
    expect(detailSource).toContain('data-entity-hero')
    expect(detailSource).toContain(':alt="heroDescriptor.alt"')
    expect(detailSource).toContain(':aria-describedby="heroDisclosureId"')
    expect(detailSource).toContain(':aria-describedby="disclosureIdFor(i)"')
    expect(detailSource).toContain(':alt="descriptor.alt"')
    expect(detailSource).toContain(':descriptor="heroDescriptor"')
    expect(detailSource).toContain(':descriptor="descriptor"')
    expect(detailSource).not.toContain('imageCredit')
  })

  it('passes classified descriptors directly through the final Task35 component boundary', () => {
    expect(detailSource).not.toContain('task35ImageUrls')
    expect(detailSource).toContain(':images="entityImageDescriptors"')
    expect(detailSource).toContain('entityImageDescriptors.value.some(descriptor => descriptor.url !== null)')
    expect(detailSource).not.toContain('const entityImages')
  })

  it('keeps disclosure ids safe and does not hide their assistive-technology target', () => {
    expect(detailSource).toContain('sanitizeDisclosureIdToken')
    expect(detailSource).toContain('const disclosureEntityId')
    expect(detailSource).toContain('entity-image-disclosure-${disclosureEntityId.value}-hero')

    const detailCss = readFileSync(resolve(process.cwd(), 'assets/css/detail-shared.css'), 'utf8')
    expect(detailCss).not.toMatch(/image-disclosure-sr-only[^}]*display\s*:\s*none/i)
  })
})
