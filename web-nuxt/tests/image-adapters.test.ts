import { mountSuspended } from '@nuxt/test-utils/runtime'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineComponent, h } from 'vue'
import { describe, expect, it } from 'vitest'
import SavedEntityCard from '../components/SavedEntityCard.vue'
import { createFavoriteItem, readFavoriteStorage, runFavoriteBootstrap } from '../composables/useFavorites'
import { normalizeRecommendationItems } from '../composables/useContextualRecommendations'
import { createRecentItem, readRecentStorage } from '../composables/useRecentlyViewed'
import { aiDisclosure } from '../utils/aiDisclosure'
import { normalizeSavedImageSnapshot } from '../utils/savedImageDescriptors'
import type { ImageDescriptor } from '../types/image'

const aiDescriptor: ImageDescriptor = {
  url: '/img/entity.webp',
  alt: 'Điểm đến — ảnh minh họa',
  source_class: 'ai-generated',
  source_kind: 'entity-editorial',
  disclosure_key: 'entity-ai',
  short_label: aiDisclosure.entity_ai.short_label,
  full_disclosure: aiDisclosure.entity_ai.full_disclosure,
  credit: null,
  width: null,
  height: null,
}

const reviewDescriptor: ImageDescriptor = {
  url: 'https://cdn.example/review.webp',
  alt: 'Ảnh do Lan chia sẻ',
  source_class: 'user-uploaded',
  source_kind: 'review-ugc',
  disclosure_key: 'ugc-photo',
  short_label: aiDisclosure.ugc_photo.short_label,
  full_disclosure: aiDisclosure.ugc_photo.full_disclosure,
  credit: 'Lan',
  width: null,
  height: null,
}

const entity = (overrides: Record<string, unknown> = {}) => ({
  id: 'entity-1',
  name: 'Điểm đến',
  type: 'attraction',
  ...overrides,
})

describe('saved image descriptor snapshots', () => {
  it('takes the snapshot revision from the canonical disclosure artifact', () => {
    const source = readFileSync(resolve(__dirname, '../utils/savedImageDescriptors.ts'), 'utf8')
    expect(source).toContain('aiDisclosure.revision')
    expect(source).not.toContain("SAVED_DESCRIPTOR_REVISION = 'ai-disclosure-v1'")
  })

  it('migrates a legacy entity image URL to an AI descriptor snapshot', () => {
    const migrated = normalizeSavedImageSnapshot(entity({ image: '/img/entity.webp' }))

    expect(migrated.image_descriptor).toEqual(aiDescriptor)
    expect(migrated.descriptor_revision).toBe('ai-disclosure-v1')
    expect(migrated).not.toHaveProperty('image')
  })

  it('preserves valid remote UGC provenance without relabeling it as AI', () => {
    const normalized = normalizeSavedImageSnapshot(entity({
      image: '/conflicting.webp',
      image_descriptor: reviewDescriptor,
    }))

    expect(normalized.image_descriptor).toEqual(reviewDescriptor)
    expect(normalized.image_descriptor.source_class).toBe('user-uploaded')
    expect(normalized).not.toHaveProperty('image')
  })

  it('fails closed on an invalid structured descriptor instead of using a raw fallback', () => {
    const normalized = normalizeSavedImageSnapshot(entity({
      image: '/legacy.webp',
      image_descriptor: { ...aiDescriptor, url: 'javascript:alert(1)' },
    }))

    expect(normalized.image_descriptor).toEqual(expect.objectContaining({
      url: null,
      source_class: 'placeholder',
      disclosure_key: 'entity-placeholder',
    }))
  })

  it('does not guess that an unknown non-entity raw image is AI-generated', () => {
    const normalized = normalizeSavedImageSnapshot({
      id: 'post-1',
      name: 'Bài cộng đồng',
      type: 'post',
      kind: 'post',
      image: '/uploads/community.webp',
    })

    expect(normalized.image_descriptor.source_class).toBe('placeholder')
    expect(normalized.image_descriptor.url).toBeNull()
  })

  it.each([
    { id: 'trip-1', name: 'Lịch trình', type: 'itinerary', kind: 'itinerary', image: '/img/trip.webp' },
    { id: 'post-1', name: 'Bài cộng đồng', type: 'post', image: '/uploads/community.webp' },
    { id: 'other-1', name: 'Nội dung khác', type: 'unknown', image: '/uploads/other.webp' },
  ])('does not infer AI provenance for a non-entity legacy URL: $id', (item) => {
    expect(normalizeSavedImageSnapshot(item).image_descriptor).toEqual(expect.objectContaining({
      url: null,
      source_class: 'placeholder',
    }))
  })

  it('recognizes a generated placeholder data URL as a placeholder snapshot', () => {
    const normalized = normalizeSavedImageSnapshot(entity({
      image: "url('data:image/svg+xml,%3Csvg%3E%3C/svg%3E')",
    }))

    expect(normalized.image_descriptor).toEqual(expect.objectContaining({
      url: null,
      source_class: 'placeholder',
    }))
  })

  it('treats an explicitly present undefined descriptor as structured invalid input', () => {
    const normalized = normalizeSavedImageSnapshot(entity({
      image: '/legacy.webp',
      image_descriptor: undefined,
    }))

    expect(normalized.image_descriptor).toEqual(expect.objectContaining({
      url: null,
      source_class: 'placeholder',
    }))
  })
})

describe('favorite, recent, and recommendation adapters', () => {
  it('loads local favorites before logged-in server merge', async () => {
    const order: string[] = []
    let localItems: unknown[] = []
    let requestMethod = 'GET'
    await runFavoriteBootstrap(
      async () => {
        order.push('load')
        localItems = [{ id: 'local-1' }]
      },
      () => true,
      async () => {
        order.push('merge')
        requestMethod = localItems.length ? 'POST' : 'GET'
      },
    )

    expect(order).toEqual(['load', 'merge'])
    expect(requestMethod).toBe('POST')
  })

  it('rewrites migrated favorite storage while preserving order and saved timestamps', () => {
    localStorage.setItem('vl360_favorites', JSON.stringify([
      { id: 'first', name: 'First', type: 'attraction', image: '/first.webp', savedAt: '2026-07-19T01:00:00.000Z' },
      { id: 'second', name: 'Second', type: 'attraction', image: '/second.webp', savedAt: '2026-07-19T02:00:00.000Z' },
    ]))

    const items = readFavoriteStorage(localStorage)
    const persisted = JSON.parse(localStorage.getItem('vl360_favorites') || '[]')
    expect(items.map(item => [item.id, item.savedAt])).toEqual([
      ['first', '2026-07-19T01:00:00.000Z'],
      ['second', '2026-07-19T02:00:00.000Z'],
    ])
    expect(persisted).toEqual(items)
    expect(persisted.every((item: Record<string, unknown>) => !('image' in item))).toBe(true)
  })

  it('rewrites migrated recent storage while preserving order and viewed timestamps', () => {
    localStorage.setItem('vl360_recent', JSON.stringify([
      { id: 'first', name: 'First', type: 'attraction', image: '/first.webp', viewedAt: 100 },
      { id: 'second', name: 'Second', type: 'attraction', image: '/second.webp', viewedAt: 200 },
    ]))

    const items = readRecentStorage(localStorage)
    const persisted = JSON.parse(localStorage.getItem('vl360_recent') || '[]')
    expect(items.map(item => [item.id, item.viewedAt])).toEqual([['first', 100], ['second', 200]])
    expect(persisted).toEqual(items)
    expect(persisted.every((item: Record<string, unknown>) => !('image' in item))).toBe(true)
  })

  it('stores descriptors in favorite snapshots', () => {
    const favorite = createFavoriteItem(entity({ image_descriptor: reviewDescriptor }), '2026-07-19T00:00:00.000Z')

    expect(favorite.image_descriptor).toEqual(reviewDescriptor)
    expect(favorite.descriptor_revision).toBe('ai-disclosure-v1')
    expect(favorite).not.toHaveProperty('image')
  })

  it('stores descriptors in recently viewed snapshots', () => {
    const recent = createRecentItem(entity({ images: ['/img/entity.webp'] }), 123)

    expect(recent.image_descriptor).toEqual(aiDescriptor)
    expect(recent.descriptor_revision).toBe('ai-disclosure-v1')
    expect(recent).not.toHaveProperty('image')
  })

  it('preserves descriptors while normalizing contextual recommendation images', () => {
    const [recommendation] = normalizeRecommendationItems([
      entity({ image: '/conflicting.webp', image_descriptor: reviewDescriptor }),
    ])

    expect(recommendation?.image_descriptor).toEqual(reviewDescriptor)
    expect(recommendation?.descriptor_revision).toBe('ai-disclosure-v1')
    expect(recommendation).not.toHaveProperty('image')
  })
})

describe('saved-card and search rendering', () => {
  it('renders a saved descriptor with an accessible disclosure association', async () => {
    const NuxtImgStub = defineComponent({
      inheritAttrs: false,
      props: { src: { type: String, required: true }, alt: { type: String, required: true } },
      setup(props, { attrs }) {
        return () => h('img', { ...attrs, src: props.src, alt: props.alt })
      },
    })
    const wrapper = await mountSuspended(SavedEntityCard, {
      props: { item: entity({ image_descriptor: reviewDescriptor }) },
      global: { stubs: { NuxtImg: NuxtImgStub } },
    })

    const image = wrapper.get('img')
    const disclosure = wrapper.get('[data-full-disclosure]')
    expect(image.attributes('src')).toBe(reviewDescriptor.url)
    expect(image.attributes('aria-describedby')).toBe(disclosure.attributes('id'))
    expect(wrapper.get('[data-image-disclosure]').text()).toContain(aiDisclosure.ugc_photo.short_label)
    expect(wrapper.text()).not.toContain(aiDisclosure.entity_ai.short_label || '')
  })

  it('keeps all saved consumers delegated and the recent-search thumbnail descriptor-based', () => {
    for (const file of ['pages/da-luu.vue', 'pages/lich-trinh/index.vue', 'pages/nguoi-dung/[id].vue']) {
      expect(readFileSync(resolve(__dirname, '..', file), 'utf8')).toContain('SavedEntityCard')
    }

    const search = readFileSync(resolve(__dirname, '../pages/tim-kiem.vue'), 'utf8')
    expect(search).not.toContain('v-if="r.image"')
    expect(search).toContain('recentImageDescriptor(r)')
    expect(search).toContain('ImageDisclosure')
    expect(search).toContain('@error="markRecentImageError(r.id)"')
    expect(search).toContain('describeEntityPlaceholder')
  })
})
