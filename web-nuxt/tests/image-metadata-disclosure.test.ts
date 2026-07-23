// @vitest-environment nuxt

import { mountSuspended } from '@nuxt/test-utils/runtime'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ShareButton from '../components/ShareButton.vue'
import type { ImageDescriptor } from '../types/image'
import {
  appendImageDisclosureToShareText,
  buildImageMeta,
  descriptorToImageObject,
  SITE_URL,
} from '../composables/useSeoHelpers'
import { aiDisclosure } from '../utils/aiDisclosure'

vi.setConfig({ hookTimeout: 30_000 })

const aiDescriptor: ImageDescriptor = {
  url: '/media/ai-editorial.webp',
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

const placeholderDescriptor: ImageDescriptor = {
  ...aiDescriptor,
  url: null,
  alt: 'Điểm đến — chưa có ảnh riêng',
  source_class: 'placeholder',
  source_kind: 'generated-placeholder',
  disclosure_key: 'entity-placeholder',
  short_label: aiDisclosure.placeholder.short_label,
  full_disclosure: aiDisclosure.placeholder.full_disclosure,
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('image metadata disclosure helpers', () => {
  it('appends the exact disclosure only when a descriptor has an image URL', () => {
    expect(appendImageDisclosureToShareText('Khám phá địa điểm', aiDescriptor))
      .toBe(`Khám phá địa điểm\n\n${aiDescriptor.full_disclosure}`)
    expect(appendImageDisclosureToShareText('Khám phá địa điểm', placeholderDescriptor))
      .toBe('Khám phá địa điểm')
  })

  it('builds absolute OG/Twitter metadata with the exact disclosure in alt text', () => {
    const meta = buildImageMeta(aiDescriptor)
    const absoluteUrl = `${SITE_URL}${aiDescriptor.url}`
    expect(meta).toEqual({
      ogImage: absoluteUrl,
      ogImageAlt: `${aiDescriptor.alt} — ${aiDescriptor.full_disclosure}`,
      twitterImage: absoluteUrl,
      twitterImageAlt: `${aiDescriptor.alt} — ${aiDescriptor.full_disclosure}`,
    })
    expect(buildImageMeta(placeholderDescriptor)).toEqual({})
  })

  it('builds a truthful ImageObject and omits placeholders', () => {
    expect(descriptorToImageObject(aiDescriptor)).toEqual({
      '@type': 'ImageObject',
      contentUrl: `${SITE_URL}${aiDescriptor.url}`,
      caption: aiDescriptor.full_disclosure,
      description: `${aiDescriptor.alt} — ${aiDescriptor.full_disclosure}`,
    })
    expect(descriptorToImageObject(aiDescriptor)).not.toHaveProperty('photographer')
    expect(descriptorToImageObject(aiDescriptor)).not.toHaveProperty('exifData')
    expect(descriptorToImageObject(aiDescriptor)).not.toHaveProperty('contentLocation')
    expect(descriptorToImageObject(placeholderDescriptor)).toBeNull()
  })
})

describe('ShareButton image disclosure behavior', () => {
  it('appends disclosure to native share text but keeps clipboard fallback URL-only', async () => {
    const share = vi.fn().mockResolvedValue(undefined)
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'share', { configurable: true, value: share })
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })

    const wrapper = await mountSuspended(ShareButton, {
      props: { title: 'Điểm đến', text: 'Khám phá địa điểm', descriptor: aiDescriptor },
    })
    await wrapper.get('button').trigger('click')

    expect(share).toHaveBeenCalledWith({
      title: 'Điểm đến',
      text: `Khám phá địa điểm\n\n${aiDescriptor.full_disclosure}`,
      url: window.location.href,
    })
    expect(writeText).not.toHaveBeenCalled()
    wrapper.unmount()

    share.mockRejectedValueOnce(new Error('unsupported'))
    const fallbackWrapper = await mountSuspended(ShareButton, {
      props: { title: 'Điểm đến', text: 'Khám phá địa điểm', descriptor: aiDescriptor },
    })
    await fallbackWrapper.get('button').trigger('click')

    expect(writeText).toHaveBeenCalledWith(window.location.href)
    fallbackWrapper.unmount()
  })
})

describe('metadata consumers', () => {
  it('keeps public post metadata image-free even when legacy UGC rows still carry photos', () => {
    const source = readFileSync(resolve(process.cwd(), 'pages/bai-viet/[id].vue'), 'utf8')
    expect(source).toContain('data-image-surface="post-metadata"')
    expect(source).toContain('data-entity-image-policy="no-image-invariant"')
    expect(source).not.toContain('buildImageMeta(postImageDescriptors.value[0])')
    expect(source).not.toContain('articleLd.image')
    expect(source).not.toContain('entityOgImage(post.value?.images)')
  })

  it('derives area OG/Twitter metadata from a classified featured entity descriptor', () => {
    const source = readFileSync(resolve(process.cwd(), 'pages/khu-vuc/[area].vue'), 'utf8')
    expect(source).toContain('describeEntityImages(featured.value[0]')
    expect(source).toContain('buildImageMeta(featuredImageDescriptor.value)')
    expect(source).toContain('if (describeEntityImages(e).length) withImages.push(e)')
    expect(source).not.toContain('entityOgImage(featured.value[0]?.images)')
    expect(source).not.toContain('if (e.images?.length) withImages.push(e)')
  })

  it('keeps the legacy image helper scoped to non-entity profile covers', () => {
    const source = readFileSync(resolve(process.cwd(), 'pages/nguoi-dung/[id].vue'), 'utf8')
    expect(source).toContain('profileOgImage(')
    expect(source).not.toContain('entityOgImage(')
  })
})
