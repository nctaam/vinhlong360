// @vitest-environment nuxt

import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import EntityReviews from '../components/EntityReviews.vue'
import type { ImageDescriptor } from '../types/image'
import { buildImageMeta, descriptorToImageObject } from '../composables/useSeoHelpers'
import { aiDisclosure } from '../utils/aiDisclosure'
import {
  describeEntityImages,
  describePostImages,
  describeReviewImages,
  normalizeRenderableImageUrl,
  normalizeReviewPhoto,
  parseGalleryDescriptor,
} from '../utils/imageDescriptors'

const mocks = vi.hoisted(() => ({
  fetch: vi.fn(),
  authHeaders: vi.fn(() => ({ Authorization: 'Bearer test-token' })),
  handleSessionExpired: vi.fn(),
}))

mockNuxtImport('useAuth', () => () => ({
  user: { value: { id: 'user-1', display_name: 'Lan' } },
  authHeaders: mocks.authHeaders,
  handleSessionExpired: mocks.handleSessionExpired,
}))
mockNuxtImport('useConfirm', () => () => ({ confirmDialog: vi.fn() }))
mockNuxtImport('useAuthModal', () => () => ({ openAuth: vi.fn() }))
mockNuxtImport('useInfiniteScroll', () => () => ({
  sentinel: { value: null },
  loading: { value: false },
}))

vi.setConfig({ hookTimeout: 30_000 })

const jpegDataUrl = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ=='
const pngDataUrl = 'data:image/png;base64,iVBORw0KGgo='
const webpDataUrl = 'data:image/webp;base64,UklGRg=='

function postDescriptor(url: string): ImageDescriptor {
  return {
    url,
    alt: 'Lan — ảnh bài viết 1',
    source_class: 'user-uploaded',
    source_kind: 'post-ugc',
    disclosure_key: 'ugc-photo',
    short_label: aiDisclosure.ugc_photo.short_label,
    full_disclosure: aiDisclosure.ugc_photo.full_disclosure,
    credit: null,
    width: null,
    height: null,
  }
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
}

beforeEach(() => {
  mocks.fetch.mockReset()
  mocks.authHeaders.mockClear()
  mocks.handleSessionExpired.mockClear()
  mocks.fetch.mockImplementation((url: unknown) => {
    if (String(url) === '/api/upload/image') return Promise.resolve({ url: '/media/review-upload.webp' })
    return Promise.resolve({ posts: [], rating: { avg: 0, count: 0 }, total: 0 })
  })
  vi.stubGlobal('$fetch', mocks.fetch)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('persisted post composer data images', () => {
  it.each([jpegDataUrl, pngDataUrl, webpDataUrl])(
    'accepts exact non-empty raster base64 only as post UGC: %s',
    (url) => {
      const descriptor = describePostImages({ display_name: 'Lan', images: [url] })[0]

      expect(descriptor).toEqual(postDescriptor(url))
      expect(parseGalleryDescriptor(descriptor)).toEqual(descriptor)
      expect(normalizeRenderableImageUrl(url)).toBeNull()
      expect(normalizeReviewPhoto({ url, alt: 'Ảnh đánh giá' })).toBeNull()
      expect(describeReviewImages({ images: [url] })).toEqual([])
      expect(describeEntityImages({ name: 'Điểm đến', images: [url] })).toEqual([])
    },
  )

  it.each([
    'data:image/svg+xml;base64,PHN2ZyBvbmxvYWQ9YWxlcnQoMSk+',
    'data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==',
    'data:image/jpeg;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg===',
    'data:image/jpeg;base64,',
    'data:image/jpeg;base64,not base64',
    'data:image/jpeg;BASE64,/9j/4AAQ',
    ' data:image/jpeg;base64,/9j/4AAQ ',
  ])('rejects SVG, HTML, script-like malformed, or non-exact data URL %s', (url) => {
    expect(describePostImages({ images: [url] })).toEqual([])
    expect(parseGalleryDescriptor(postDescriptor(url))).toBeNull()
  })

  it('does not admit a safe data URL under review or entity source contracts', () => {
    expect(parseGalleryDescriptor({
      ...postDescriptor(jpegDataUrl),
      source_kind: 'review-ugc',
    })).toBeNull()
    expect(parseGalleryDescriptor({
      ...postDescriptor(jpegDataUrl),
      source_class: 'ai-generated',
      source_kind: 'entity-editorial',
      disclosure_key: 'entity-ai',
      short_label: aiDisclosure.entity_ai.short_label,
      full_disclosure: aiDisclosure.entity_ai.full_disclosure,
    })).toBeNull()
  })

  it('keeps post data images out of OG/Twitter and structured metadata', () => {
    const descriptor = describePostImages({ images: [jpegDataUrl] })[0]
    expect(descriptor).toBeDefined()
    expect(buildImageMeta(descriptor)).toEqual({})
    expect(descriptorToImageObject(descriptor)).toBeNull()
  })
})

describe('UGC upload preview disclosure surfaces', () => {
  it('mounts the review uploader preview with exact UGC disclosure and source marker', async () => {
    const wrapper = await mountSuspended(EntityReviews, {
      props: { entityId: 'entity-1', entityName: 'Điểm đến thử' },
      global: { stubs: { IconLine: true, ReviewCard: true, ReviewStats: true } },
    })
    await flushUi()

    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      configurable: true,
      value: [new File(['jpeg'], 'review.jpg', { type: 'image/jpeg' })],
    })
    await input.trigger('change')
    await flushUi()

    const preview = wrapper.get('.rf-image-preview')
    const image = preview.get('img')
    expect(preview.attributes('data-source-class')).toBe('user-uploaded')
    expect(image.attributes('src')).toBe('/media/review-upload.webp')
    expect(image.attributes('aria-describedby')).toBe('review-upload-image-0-disclosure')
    expect(preview.get('[data-short-label]').text()).toBe(aiDisclosure.ugc_photo.short_label)
    expect(preview.get('#review-upload-image-0-disclosure').text())
      .toBe(aiDisclosure.ugc_photo.full_disclosure)
    expect(preview.text()).not.toMatch(/Minh họa AI|AI dựng/i)
    wrapper.unmount()
  })

  it('routes the community composer preview through post descriptors without changing payload data', () => {
    const source = readFileSync(resolve(process.cwd(), 'pages/cong-dong.vue'), 'utf8')
      .replaceAll('\r\n', '\n')

    expect(source).toContain("canvas.toDataURL('image/jpeg', quality)")
    expect(source).toContain('const previewImageDescriptors = computed(() => describePostImages({')
    expect(source).toContain('images: previewImages.value,')
    expect(source).toContain('v-for="(img, i) in previewImageDescriptors"')
    expect(source).toContain(':data-source-class="img.source_class"')
    expect(source).toContain(':aria-describedby="communityUploadDisclosureId(i)"')
    expect(source).toContain('<ImageDisclosure :id="communityUploadDisclosureId(i)" :descriptor="img" presentation="short" />')
    expect(source).not.toContain('v-for="(src, i) in previewImages"')
    expect(source).toContain('body.images = previewImages.value')
    expect(source).toContain('draftBody.images = previewImages.value')
  })
})
