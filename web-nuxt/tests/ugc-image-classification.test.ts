import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { DOMWrapper } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PostCard from '../components/PostCard.vue'
import { aiDisclosure } from '../utils/aiDisclosure'
import {
  describePostImages,
  describeReviewImages,
  normalizePostPhoto,
  parseGalleryDescriptor,
} from '../utils/imageDescriptors'

const root = resolve(__dirname, '..')
vi.setConfig({ hookTimeout: 30_000 })
const mountedWrappers: Array<{ unmount: () => void }> = []

afterEach(() => {
  for (const wrapper of mountedWrappers.splice(0)) wrapper.unmount()
  document.body.querySelectorAll('[role="dialog"]').forEach(dialog => dialog.remove())
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
})

describe('PostCard UGC disclosure', () => {
  it('omits unsafe media and binds exact disclosure plus credit to the grid and lightbox', async () => {
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

    const media = wrapper.get('.thread-img-wrap img')
    expect(media.attributes('src')).toBe('/media/community.webp')
    expect(wrapper.find('img[src^="javascript:"]').exists()).toBe(false)
    expect(wrapper.get('[data-source-class]').attributes('data-source-class')).toBe('user-uploaded')

    const disclosureId = media.attributes('aria-describedby')
    expect(disclosureId).toBeTruthy()
    expect(wrapper.get(`[data-full-disclosure][id="${disclosureId}"]`).text())
      .toBe(aiDisclosure.ugc_photo.full_disclosure)
    expect(wrapper.get('[data-short-label]').text()).toBe(aiDisclosure.ugc_photo.short_label)
    expect(wrapper.get('[data-credit]').text()).toBe('Lan Nguyễn')

    await wrapper.get('.thread-img-wrap').trigger('click')
    const dialog = new DOMWrapper(document.body).get('[role="dialog"]')
    const lightboxMedia = dialog.get('.lb-img')
    expect(lightboxMedia.attributes('src')).toBe('/media/community.webp')
    const lightboxDisclosureId = lightboxMedia.attributes('aria-describedby')
    expect(lightboxDisclosureId).toBeTruthy()
    expect(dialog.get(`[data-full-disclosure][id="${lightboxDisclosureId}"]`).text())
      .toBe(`${aiDisclosure.ugc_photo.full_disclosure} — Lan Nguyễn`)
    expect(dialog.text()).not.toContain('Minh họa AI')
  })
})

describe('UGC disclosure surfaces', () => {
  it.each([
    ['components/ReviewCard.vue', 'data-source-class="user-uploaded"'],
    ['components/PostCard.vue', 'data-source-class="user-uploaded"'],
    ['components/EntityFeed.vue', 'data-source-class="user-uploaded"'],
    ['pages/index.vue', 'data-source-class="user-uploaded"'],
    ['pages/bai-viet/[id].vue', 'describePostImages'],
    ['pages/admin/kiem-duyet.vue', 'data-source-class="user-uploaded"'],
  ])('wires %s through the UGC disclosure boundary', (relativePath, marker) => {
    const source = readFileSync(resolve(root, relativePath), 'utf8')
    expect(source).toContain(marker)
    expect(source).not.toMatch(/AI photo|AI-generated|ảnh thật|real photo/i)
  })

  it('builds post-detail ImageObject JSON-LD from the same UGC descriptors', () => {
    const source = readFileSync(resolve(root, 'pages/bai-viet/[id].vue'), 'utf8')
    expect(source).toContain("'@type': 'ImageObject'")
    expect(source).toContain('caption: descriptor.alt')
    expect(source).toContain('description: descriptor.full_disclosure')
    expect(source).toContain('creditText: descriptor.credit')
    expect(source).toContain('postImageDescriptors.value.map')
  })

  it('uses full UGC disclosure in the moderation preview', () => {
    const source = readFileSync(resolve(root, 'pages/admin/kiem-duyet.vue'), 'utf8')
    expect(source).toContain(':descriptor="img" presentation="full"')
    expect(source).toContain('const previewImages = computed(() => describePostImages(previewPost.value))')
  })
})
