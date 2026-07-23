import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import EntityFeed from '../components/EntityFeed.vue'
import PostCard from '../components/PostCard.vue'
import ReviewCard from '../components/ReviewCard.vue'
import AdminModerationPage from '../pages/admin/kiem-duyet.vue'
import PostDetailPage from '../pages/bai-viet/[id].vue'
import HomePage from '../pages/index.vue'
import type { ImageDescriptor } from '../types/image'
import { aiDisclosure } from '../utils/aiDisclosure'
import {
  describePostImages,
  describeReviewImages,
  normalizePostPhoto,
  parseGalleryDescriptor,
} from '../utils/imageDescriptors'

const apiFetchMock = vi.hoisted(() => vi.fn())
const fetchMock = vi.hoisted(() => vi.fn())
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))

vi.setConfig({ hookTimeout: 30_000 })
const mountedWrappers: Array<{ unmount: () => void }> = []

const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: { type: String, required: true }, alt: { type: String, required: true } },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})

const pageStubs = {
  NuxtImg: NuxtImgStub,
  AvatarPlaceholder: true,
  Breadcrumb: true,
  EmptyState: true,
  EntityCard: true,
  HeroIllustration: true,
  IconLine: true,
  JourneyActionRail: true,
  LazyReportModal: true,
  LoadMoreButton: true,
  PostCard: true,
  SearchAutocomplete: true,
  SkeletonGrid: true,
  SkeletonList: true,
}

const postUgcDescriptor: ImageDescriptor = {
  url: '/media/post-descriptor.webp',
  alt: 'Ảnh bài viết đã phân loại',
  source_class: 'user-uploaded',
  source_kind: 'post-ugc',
  disclosure_key: 'ugc-photo',
  short_label: aiDisclosure.ugc_photo.short_label,
  full_disclosure: aiDisclosure.ugc_photo.full_disclosure,
  credit: 'Lan',
  width: null,
  height: null,
}

const reviewUgcDescriptor: ImageDescriptor = {
  ...postUgcDescriptor,
  url: '/media/review-descriptor.webp',
  alt: 'Ảnh đánh giá đã phân loại',
  source_kind: 'review-ugc',
}

const entityAiDescriptor: ImageDescriptor = {
  ...postUgcDescriptor,
  url: '/img/entity-descriptor.webp',
  alt: 'Ảnh minh họa thực thể đã phân loại',
  source_class: 'ai-generated',
  source_kind: 'entity-editorial',
  disclosure_key: 'entity-ai',
  short_label: aiDisclosure.entity_ai.short_label,
  full_disclosure: aiDisclosure.entity_ai.full_disclosure,
  credit: null,
}

const aiWording = /Minh họa AI|Ảnh minh họa do AI dựng|AI-generated|AI photo/i

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
}

function expectCanonicalUgcSurface(
  surface: any,
  expected: { src: string; disclosureId: string; credit: string; fullVisible?: boolean },
) {
  const image = surface.get('img')
  expect(image.attributes('src')).toBe(expected.src)
  expect(surface.attributes('data-source-class')).toBe('user-uploaded')
  expect(image.attributes('aria-describedby')).toBe(expected.disclosureId)

  const fullDisclosure = surface.get(`[data-full-disclosure][id="${expected.disclosureId}"]`)
  expect(fullDisclosure.text()).toBe(aiDisclosure.ugc_photo.full_disclosure)
  if (expected.fullVisible) expect(fullDisclosure.classes()).not.toContain('image-disclosure-sr-only')
  expect(surface.get('[data-credit]').text()).toBe(expected.credit)
  expect(surface.text()).not.toMatch(aiWording)
}

beforeEach(() => {
  apiFetchMock.mockReset()
  fetchMock.mockReset()
  fetchMock.mockResolvedValue({})
  vi.stubGlobal('$fetch', fetchMock)
})

afterEach(() => {
  for (const wrapper of mountedWrappers.splice(0)) wrapper.unmount()
  document.body.querySelectorAll('[role="dialog"]').forEach(dialog => dialog.remove())
  vi.unstubAllGlobals()
})

describe('UGC image descriptor producers', () => {
  it('classifies safe post photos with the canonical UGC contract and trimmed credit', () => {
    const descriptor = normalizePostPhoto({
      url: ' /media/post.webp ',
      alt: 'Bài viết về miệt vườn',
      credit: '  Lan  ',
    })

    expect(descriptor).toEqual(expect.objectContaining({
      url: '/media/post.webp',
      source_class: 'user-uploaded',
      source_kind: 'post-ugc',
      disclosure_key: 'ugc-photo',
      short_label: aiDisclosure.ugc_photo.short_label,
      full_disclosure: aiDisclosure.ugc_photo.full_disclosure,
      credit: 'Lan',
    }))
    expect(parseGalleryDescriptor(descriptor)).toEqual(descriptor)
  })

  it('keeps general post photos as post UGC even when the post type is review', () => {
    expect(describePostImages({
      post_type: 'review',
      display_name: 'Lan',
      images: ['/media/review-post.webp'],
    })[0]).toEqual(expect.objectContaining({
      source_class: 'user-uploaded',
      source_kind: 'post-ugc',
      disclosure_key: 'ugc-photo',
    }))
  })

  it('omits unsafe post and review URLs while preserving valid siblings', () => {
    expect(describePostImages({
      display_name: 'Lan',
      images: ['javascript:alert(1)', '/media/valid.webp'],
    })).toHaveLength(1)
    expect(describeReviewImages({
      display_name: 'Lan',
      images: ['//cdn.example/unsafe.webp', '/media/review.webp'],
    })).toEqual([
      expect.objectContaining({ source_class: 'user-uploaded', source_kind: 'review-ugc' }),
    ])
  })

  it('treats blank credits as absent and keeps the descriptor valid', () => {
    const descriptor = normalizePostPhoto({
      url: '/media/post.webp',
      alt: 'Bài viết',
      credit: '   ',
    })

    expect(descriptor?.credit).toBeNull()
    expect(parseGalleryDescriptor(descriptor)).not.toBeNull()
  })

  it('rejects invalid post alt and credit metadata instead of weakening the descriptor', () => {
    expect(() => normalizePostPhoto({ url: '/media/post.webp', alt: '   ' }))
      .toThrow('post photo alt must be non-blank')
    expect(() => normalizePostPhoto({ url: '/media/post.webp', alt: 'Bài viết', credit: 7 }))
      .toThrow('post photo credit must be a string')
  })

  it('omits supplied entity AI and review descriptors from post UGC without reclassification', () => {
    expect(describePostImages({
      images: ['/media/fallback.webp'],
      image_descriptors: [entityAiDescriptor, reviewUgcDescriptor],
    })).toEqual([])
  })

  it('omits supplied post descriptors from review UGC without reclassification', () => {
    expect(describeReviewImages({
      images: ['/media/fallback.webp'],
      image_descriptors: [postUgcDescriptor],
    })).toEqual([])
  })
})

describe('PostCard UGC disclosure', () => {
  it('keeps legacy post photos out of the public card and lightbox sinks', async () => {
    const wrapper = await mountSuspended(PostCard, {
      props: {
        post: {
          id: 'post-1',
          display_name: 'Lan',
          content: 'Một bài viết cộng đồng',
          post_type: 'review',
          images: ['javascript:alert(1)', '/media/community.webp'],
          image_credits: [null, '  Lan Nguyễn  '],
          created_at: '2026-07-20T00:00:00Z',
        },
      },
    })
    mountedWrappers.push(wrapper)

    const invariant = wrapper.get('[data-image-surface="post-grid"]')
    expect(invariant.attributes('data-entity-image-policy')).toBe('no-image-invariant')
    expect(invariant.classes()).toContain('thread-post')
    expect(wrapper.find('.thread-images').exists()).toBe(false)
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(wrapper.find('img[src="/media/community.webp"]').exists()).toBe(false)
  })
})

describe('ReviewCard UGC disclosure', () => {
  it('keeps legacy review photos out of the public review card', async () => {
    const wrapper = await mountSuspended(ReviewCard, {
      props: {
        review: {
          id: 'review-1',
          user_id: 'user-1',
          display_name: 'Lan',
          content: 'Một đánh giá cộng đồng',
          images: ['javascript:alert(1)', '/media/review.webp'],
          image_credits: [null, '  Lan Nguyễn  '],
          created_at: '2026-07-20T00:00:00Z',
        } as any,
        owned: false,
        deleting: false,
        deleteError: '',
      },
      global: { stubs: { AvatarPlaceholder: true, NuxtImg: NuxtImgStub } },
    })
    mountedWrappers.push(wrapper)

    const invariant = wrapper.get('[data-image-surface="review-card"]')
    expect(invariant.attributes('data-entity-image-policy')).toBe('no-image-invariant')
    expect(invariant.classes()).toContain('review-item')
    expect(wrapper.find('.ri-images').exists()).toBe(false)
    expect(wrapper.find('img[src="/media/review.webp"]').exists()).toBe(false)
  })
})

describe('EntityFeed UGC disclosure', () => {
  it('dispatches its feed URL without rendering community thumbnails', async () => {
    fetchMock.mockImplementation((url: unknown) => {
      if (String(url).startsWith('/api/entities/entity-1/feed?')) {
        return Promise.resolve({
          posts: [{
            id: 'feed-1',
            display_name: 'Lan',
            content: 'Một chia sẻ trong feed',
            images: ['//cdn.example/unsafe.webp', '/media/feed.webp'],
            image_credits: [null, '  Lan Nguyễn  '],
            created_at: '2026-07-20T00:00:00Z',
          }],
          total: 1,
        })
      }
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(EntityFeed, {
      props: { entityId: 'entity-1', entityName: 'Điểm đến thử' },
      global: { stubs: { NuxtImg: NuxtImgStub, IconLine: true } },
    })
    mountedWrappers.push(wrapper)
    await flushUi()

    expect(fetchMock).toHaveBeenCalledWith('/api/entities/entity-1/feed?limit=5')
    const invariant = wrapper.get('[data-image-surface="entity-feed"]')
    expect(invariant.attributes('data-entity-image-policy')).toBe('no-image-invariant')
    expect(invariant.classes()).toContain('entity-feed')
    expect(wrapper.find('.ef-media').exists()).toBe(false)
    expect(wrapper.find('img[src="/media/feed.webp"]').exists()).toBe(false)
  })
})

describe('UGC disclosure surfaces', () => {
  it('mounts the home community strip without public UGC thumbnails', async () => {
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/homepage') {
        return Promise.resolve({
          month: 7,
          seasonal: [],
          experiences: [],
          products: [],
          top_dishes: [],
          itineraries: [{ id: 'itinerary-1', title: 'Lịch trình thử' }],
          upcoming_events: [],
        })
      }
      if (path === '/api/feed?limit=10') {
        return Promise.resolve({
          posts: [{
            id: 'home-1',
            display_name: 'Lan',
            content: 'Một bài viết cộng đồng trên trang chủ',
            images: ['javascript:alert(1)', '/media/home.webp'],
            image_credits: [null, '  Lan Nguyễn  '],
          }],
        })
      }
      if (path === '/api/community/stats') return Promise.resolve({ posts: 1, reviews: 0, members: 1 })
      if (path === '/api/community/leaderboard?limit=3') return Promise.resolve({ leaders: [] })
      if (path === '/api/community/trending-tags?limit=8') return Promise.resolve({ tags: [] })
      if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs } })
    mountedWrappers.push(wrapper)
    await flushUi()

    const invariant = wrapper.get('[data-image-surface="home-community"]')
    expect(invariant.attributes('data-entity-image-policy')).toBe('no-image-invariant')
    expect(invariant.classes()).toContain('block')
    expect(wrapper.find('.cm-img').exists()).toBe(false)
    expect(wrapper.find('img[src="/media/home.webp"]').exists()).toBe(false)
  })

  it('mounts post detail without related, OG, or JSON-LD UGC image sinks', async () => {
    apiFetchMock.mockImplementation((url: unknown) => {
      if (String(url) === '/api/posts/post-1') {
        return Promise.resolve({
          post: {
            id: 'post-1',
            user_id: 'user-1',
            display_name: 'Lan',
            content: 'Bài viết chi tiết có ảnh cộng đồng',
            post_type: 'review',
            rating: 5,
            images: ['javascript:alert(1)', '/media/detail.webp'],
            image_credits: [null, '  Lan Nguyễn  '],
            created_at: '2026-07-20T00:00:00Z',
          },
        })
      }
      return Promise.resolve({})
    })
    fetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/posts/post-1/comments') return Promise.resolve({ comments: [] })
      if (path === '/api/posts/post-1/related?limit=2') {
        return Promise.resolve({
          posts: [{
            id: 'related-1',
            display_name: 'Mai',
            content: 'Bài viết liên quan có ảnh',
            images: ['//cdn.example/unsafe.webp', '/media/related.webp'],
            image_credits: [null, '  Mai Nguyễn  '],
          }],
        })
      }
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(PostDetailPage, {
      route: '/bai-viet/post-1',
      global: { stubs: pageStubs },
    })
    mountedWrappers.push(wrapper)
    await flushUi()

    const relatedInvariant = wrapper.get('[data-image-surface="related-post"]')
    expect(relatedInvariant.attributes('data-entity-image-policy')).toBe('no-image-invariant')
    expect(relatedInvariant.classes()).toContain('related-section')
    const metadataInvariant = wrapper.get('[data-image-surface="post-metadata"]')
    expect(metadataInvariant.attributes('data-entity-image-policy')).toBe('no-image-invariant')
    expect(metadataInvariant.classes()).toContain('thread-detail-page')
    const detailInvariant = wrapper.get('[data-image-surface="post-detail-card"]')
    expect(detailInvariant.attributes('data-entity-image-policy')).toBe('no-image-invariant')
    expect(detailInvariant.classes()).toContain('thread-detail')
    expect(wrapper.find('.related-media').exists()).toBe(false)
    expect(wrapper.find('img[src="/media/related.webp"]').exists()).toBe(false)

    const article = [...document.head.querySelectorAll('script[type="application/ld+json"]')]
      .map(script => JSON.parse(script.textContent || '{}'))
      .find(value => value['@type'] === 'Review')
    expect(article).toBeDefined()
    expect(article).not.toHaveProperty('image')
    expect(JSON.stringify(article)).not.toMatch(aiWording)
  })

  it('mounts moderation preview with the full UGC disclosure visible', async () => {
    fetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path.startsWith('/admin-api/moderation/queue?')) {
        return Promise.resolve({
          posts: [{
            id: 'moderation-1',
            display_name: 'Lan',
            content: 'Bài viết cần kiểm duyệt',
            post_type: 'post',
            moderation_status: 'pending',
            images: ['javascript:alert(1)', '/media/moderation.webp'],
            image_credits: [null, '  Lan Nguyễn  '],
            created_at: '2026-07-20T00:00:00Z',
          }],
          total: 1,
        })
      }
      if (path === '/admin-api/moderation/stats') return Promise.resolve({ counts: { pending: 1 } })
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(AdminModerationPage, {
      global: { stubs: { NuxtImg: NuxtImgStub } },
    })
    mountedWrappers.push(wrapper)
    await flushUi()
    const previewButton = wrapper.findAll('button').find(button => button.text() === 'Xem')
    expect(previewButton).toBeDefined()
    await previewButton!.trigger('click')
    await flushUi()

    const surface = wrapper.get('.mod-preview-images')
    expectCanonicalUgcSurface(surface, {
      src: '/media/moderation.webp',
      disclosureId: 'moderation-image-0-disclosure',
      credit: 'Lan Nguyễn',
      fullVisible: true,
    })
    expect(surface.find('[data-short-label]').exists()).toBe(false)
    expect(wrapper.find('img[src^="javascript:"]').exists()).toBe(false)
  })
})
