// @vitest-environment node

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

type Renderer = {
  file: string
  surface: string
  access_path: string
  source_class: 'ai-generated' | 'placeholder' | 'user-uploaded' | 'none'
  descriptor_producer: string
  render_policy: 'render' | 'suppress'
  presentation: 'short' | 'full' | 'short-and-full' | 'none'
  accessibility: string
  test_file: string
}

const root = resolve(process.cwd())
const registry = JSON.parse(readFileSync(resolve(root, 'config/entity-image-renderers.json'), 'utf8')) as {
  schema_version: number
  renderers: Renderer[]
}

const requiredBoundaries = [
  ['pages/dia-diem/[id].vue', 'detail-hero', 'ai-generated'],
  ['pages/dia-diem/[id].vue', 'detail-hero', 'placeholder'],
  ['pages/dia-diem/[id].vue', 'detail-rail', 'ai-generated'],
  ['pages/dia-diem/[id].vue', 'detail-rail', 'placeholder'],
  ['pages/dia-diem/[id].vue', 'mixed-gallery', 'ai-generated'],
  ['pages/dia-diem/[id].vue', 'mixed-gallery', 'user-uploaded'],
  ['components/PhotoGallery.vue', 'photo-gallery', 'ai-generated'],
  ['components/PhotoGallery.vue', 'photo-gallery', 'user-uploaded'],
  ['components/PhotoGallery.vue', 'photo-gallery', 'placeholder'],
  ['components/ImageLightbox.vue', 'image-lightbox', 'ai-generated'],
  ['components/ImageLightbox.vue', 'image-lightbox', 'user-uploaded'],
  ['components/ImageLightbox.vue', 'image-lightbox', 'placeholder'],
  ['components/EntityCard.vue', 'entity-card', 'ai-generated'],
  ['components/EntityCard.vue', 'entity-card', 'placeholder'],
  ['components/home/EntityFeature.vue', 'entity-feature', 'ai-generated'],
  ['components/home/EntityFeature.vue', 'entity-feature', 'placeholder'],
  ['pages/index.vue', 'home-hero', 'ai-generated'],
  ['pages/index.vue', 'home-hero', 'placeholder'],
  ['pages/index.vue', 'home-spotlight', 'ai-generated'],
  ['pages/index.vue', 'home-community', 'user-uploaded'],
  ['pages/index.vue', 'home-for-you', 'ai-generated'],
  ['pages/index.vue', 'home-for-you', 'placeholder'],
  ['pages/index.vue', 'home-entity-card-consumer', 'ai-generated'],
  ['pages/dia-diem/index.vue', 'listing-entity-card-consumer', 'ai-generated'],
  ['pages/du-lich.vue', 'tourism-entity-card-consumer', 'ai-generated'],
  ['pages/kham-pha/[interest].vue', 'interest-entity-card-consumer', 'ai-generated'],
  ['pages/khu-vuc/[area].vue', 'area-entity-card-consumer', 'ai-generated'],
  ['pages/luu-tru.vue', 'lodging-entity-card-consumer', 'ai-generated'],
  ['pages/ocop.vue', 'ocop-entity-card-consumer', 'ai-generated'],
  ['pages/san-pham.vue', 'product-entity-card-consumer', 'ai-generated'],
  ['pages/theo-mua.vue', 'season-entity-card-consumer', 'ai-generated'],
  ['pages/tim-kiem.vue', 'search-entity-card-consumer', 'ai-generated'],
  ['pages/xa-phuong/[id].vue', 'ward-entity-card-consumer', 'ai-generated'],
  ['components/NearbyEntities.vue', 'nearby-delegated', 'ai-generated'],
  ['components/SmartRecommendations.vue', 'smart-delegated', 'ai-generated'],
  ['components/AIRecommendations.vue', 'ai-delegated', 'ai-generated'],
  ['composables/useFavorites.ts', 'favorite-adapter', 'ai-generated'],
  ['composables/useRecentlyViewed.ts', 'recent-adapter', 'ai-generated'],
  ['composables/useContextualRecommendations.ts', 'context-adapter', 'ai-generated'],
  ['components/SavedEntityCard.vue', 'saved-card', 'ai-generated'],
  ['components/SavedEntityCard.vue', 'saved-card', 'placeholder'],
  ['pages/da-luu.vue', 'saved-consumer', 'ai-generated'],
  ['pages/lich-trinh/index.vue', 'itinerary-saved-consumer', 'ai-generated'],
  ['pages/nguoi-dung/[id].vue', 'profile-saved-consumer', 'ai-generated'],
  ['pages/tim-kiem.vue', 'recent-search', 'ai-generated'],
  ['pages/tim-kiem.vue', 'recent-search', 'placeholder'],
  ['pages/le-hoi.vue', 'event-thumbnail', 'ai-generated'],
  ['pages/le-hoi.vue', 'event-thumbnail', 'placeholder'],
  ['pages/su-kien.vue', 'event-thumbnail', 'ai-generated'],
  ['pages/su-kien.vue', 'event-thumbnail', 'placeholder'],
  ['pages/ban-do.vue', 'map-popup', 'none'],
  ['pages/admin/entities.vue', 'admin-entity-thumbnail', 'ai-generated'],
  ['pages/admin/entities.vue', 'admin-entity-thumbnail', 'placeholder'],
  ['pages/admin/entities.vue', 'admin-entity-editor', 'ai-generated'],
  ['pages/admin/entities.vue', 'admin-entity-editor', 'placeholder'],
  ['pages/admin/media.vue', 'admin-media', 'ai-generated'],
  ['pages/admin/media.vue', 'admin-media', 'placeholder'],
  ['pages/admin/media.vue', 'admin-media-preview', 'ai-generated'],
  ['pages/admin/media.vue', 'admin-media-preview', 'placeholder'],
  ['pages/admin/duyet-tu-hoc.vue', 'admin-self-learning', 'ai-generated'],
  ['pages/admin/duyet-tu-hoc.vue', 'admin-self-learning', 'placeholder'],
  ['components/ReviewCard.vue', 'review-card', 'user-uploaded'],
  ['components/PostCard.vue', 'post-grid', 'user-uploaded'],
  ['components/PostCard.vue', 'post-lightbox', 'user-uploaded'],
  ['components/EntityFeed.vue', 'entity-feed', 'user-uploaded'],
  ['pages/bai-viet/[id].vue', 'related-post', 'user-uploaded'],
  ['pages/bai-viet/[id].vue', 'post-detail-card', 'user-uploaded'],
  ['pages/bai-viet/[id].vue', 'post-metadata', 'user-uploaded'],
  ['pages/admin/kiem-duyet.vue', 'admin-moderation', 'user-uploaded'],
  ['components/EntityReviews.vue', 'review-upload-preview', 'user-uploaded'],
  ['pages/cong-dong.vue', 'community-upload-preview', 'user-uploaded'],
  ['components/ShareButton.vue', 'native-share', 'ai-generated'],
  ['composables/useSeoHelpers.ts', 'metadata-helpers', 'ai-generated'],
  ['pages/dia-diem/[id].vue', 'entity-metadata', 'ai-generated'],
  ['pages/xa-phuong/[id].vue', 'entity-metadata', 'ai-generated'],
  ['pages/khu-vuc/[area].vue', 'entity-metadata', 'ai-generated'],
] as const

const key = (row: Pick<Renderer, 'file' | 'surface' | 'source_class'>) => `${row.file}|${row.surface}|${row.source_class}`

describe('entity image renderer inventory', () => {
  it('uses schema version 1 and exact nine-key rows', () => {
    expect(registry.schema_version).toBe(1)
    for (const row of registry.renderers) {
      expect(Object.keys(row).sort()).toEqual([
        'access_path',
        'accessibility',
        'descriptor_producer',
        'file',
        'presentation',
        'render_policy',
        'source_class',
        'surface',
        'test_file',
      ])
    }
  })

  it('renders only AI/placeholder rows and suppresses public UGC with no-image invariants', () => {
    for (const row of registry.renderers) {
      if (row.source_class === 'ai-generated' || row.source_class === 'placeholder') {
        expect(row.render_policy).toBe('render')
      }
      if (row.source_class === 'user-uploaded' && !row.file.includes('/admin/') && !row.surface.includes('upload-preview')) {
        expect(row).toEqual(expect.objectContaining({
          render_policy: 'suppress',
          descriptor_producer: 'no-image-invariant',
          presentation: 'none',
          accessibility: 'no-image-invariant',
        }))
      }
    }
  })

  it('contains exactly every required implementation boundary', () => {
    const actual = new Set(registry.renderers.map(key))
    const required = new Set(requiredBoundaries.map(([file, surface, source_class]) => `${file}|${surface}|${source_class}`))
    expect(actual).toEqual(required)
  })

  it('points every row to an existing source and focused test', () => {
    for (const row of registry.renderers) {
      expect(readFileSync(resolve(root, row.file), 'utf8')).toBeTruthy()
      expect(readFileSync(resolve(root, row.test_file), 'utf8')).toBeTruthy()
    }
  })
})
