// @vitest-environment node

import { describe, expect, it } from 'vitest'
import provenanceCorpusJson from '../../tests/fixtures/media-provenance-validator-corpus.json'
import { aiDisclosure } from '../utils/aiDisclosure'
import {
  describeEntityImages,
  describeEntityPlaceholder,
  normalizeRenderableImageUrl,
  normalizeReviewPhoto,
  parseGalleryDescriptor,
} from '../utils/imageDescriptors'

const apiEntityImage = {
  url: '/img/entities/entity.webp',
  alt: 'Chùa Vàm Ray — ảnh minh họa 1',
  source_class: 'ai-generated',
  source_kind: 'entity-editorial',
  disclosure_key: 'entity-ai',
  short_label: aiDisclosure.entity_ai.short_label,
  full_disclosure: aiDisclosure.entity_ai.full_disclosure,
  credit: null,
  source_url: null,
  width: null,
  height: null,
}

const apiReviewImage = {
  url: '/img/review.jpg',
  alt: 'Chùa Vàm Ray — ảnh đánh giá',
  source_class: 'user-uploaded',
  source_kind: 'review-ugc',
  disclosure_key: 'ugc-photo',
  short_label: aiDisclosure.ugc_photo.short_label,
  full_disclosure: aiDisclosure.ugc_photo.full_disclosure,
  credit: 'Lan',
  source_url: null,
  width: null,
  height: null,
}

const apiPlaceholderImage = {
  url: null,
  alt: 'Chua co anh rieng',
  source_class: 'placeholder',
  source_kind: 'generated-placeholder',
  disclosure_key: 'entity-placeholder',
  short_label: aiDisclosure.placeholder.short_label,
  full_disclosure: aiDisclosure.placeholder.full_disclosure,
  credit: null,
  source_url: null,
  width: null,
  height: null,
}

describe('renderable image URL normalization', () => {
  it.each([
    [' /media/minh-hoa.webp?size=large&crop=wide ', '/media/minh-hoa.webp?size=large&crop=wide'],
    ['https://cdn.example/image.webp?size=large', 'https://cdn.example/image.webp?size=large'],
    ['https://[2001:db8::1]:443/image.webp', 'https://[2001:db8::1]:443/image.webp'],
    ['https://xn--strae-oqa.example/image.webp', 'https://xn--strae-oqa.example/image.webp'],
    ['https://xn--fa-hia.example/image.webp', 'https://xn--fa-hia.example/image.webp'],
  ])('accepts the same canonical forms as the backend: %s', (raw, expected) => {
    expect(normalizeRenderableImageUrl(raw)).toBe(expected)
  })

  it.each([
    null,
    7,
    '',
    '   ',
    'relative/image.webp',
    '/image with-space.webp',
    '/image\twith-tab.webp',
    '/image\nwith-newline.webp',
    '/image\\backslash.webp',
    '/image.webp#fragment',
    '//cdn.example/image.webp',
    '///media/image.webp',
    'http://cdn.example/image.webp',
    'ftp://cdn.example/image.webp',
    'mailto:image@example.com',
    'https:///image.webp',
    'https://@cdn.example/image.webp',
    'https://:@cdn.example/image.webp',
    'https://%40cdn.example/image.webp',
    'https://user@cdn.example/image.webp',
    'https://user:secret@cdn.example/image.webp',
    'https://host^x/image.webp',
    'https://host|x/image.webp',
    'https://host<x/image.webp',
    'https://host>x/image.webp',
    'https://[v1.fe]/image.webp',
    'https://999.999.999.999/image.webp',
    'https://256.256.256.256/image.webp',
    'https://xn--/image.webp',
    'https://cdn.example:not-a-port/image.webp',
    `https://cdn.example:${'9'.repeat(4301)}/image.webp`,
    'https://[2001:db8::1/image.webp',
  ])('rejects the same unsafe or malformed values as the backend: %s', (raw) => {
    expect(normalizeRenderableImageUrl(raw)).toBeNull()
  })
})

describe('non-rights-cleared descriptor source URLs', () => {
  it('requires factories to emit a null source_url exact key', () => {
    expect(normalizeReviewPhoto({ url: '/img/review.jpg', alt: 'Review' })).not.toBeNull()
    expect(describeEntityImages({
      name: 'Entity',
      images: ['/img/entities/entity.webp'],
      attributes: { image_type: 'ai-generated', is_verified_photo: false },
    })[0]?.source_url).toBeNull()
    expect(describeEntityPlaceholder({ name: 'Entity' }).source_url).toBeNull()
  })
})

describe('rights-cleared descriptor provenance URLs', () => {
  const pressDescriptor = {
    url: '/img/entities/dinh-long-ho.webp',
    alt: 'Đình Long Hồ — ảnh tư liệu',
    source_class: 'rights-cleared',
    source_kind: 'press',
    disclosure_key: 'entity-sourced-photo',
    short_label: aiDisclosure.sourced_photo.short_label,
    full_disclosure: aiDisclosure.sourced_photo.full_disclosure,
    credit: 'Trần Phước · Báo Vĩnh Long',
    source_url: 'https://baovinhlong.com.vn/images/photo.webp',
    width: null,
    height: null,
  }

  it('rejects private-network source URLs with otherwise canonical sourced fields', () => {
    expect(parseGalleryDescriptor({
      ...pressDescriptor,
      source_url: 'https://192.168.1.1/images/photo.webp',
    })).toBeNull()
  })

  it.each(provenanceCorpusJson)(
    'matches the shared provenance corpus for $name',
    (row) => {
      const descriptor = describeEntityImages({
        name: 'Đình Long Hồ',
        images: ['/img/entities/dinh-long-ho.webp'],
        attributes: row.attributes,
      })[0]

      expect(descriptor?.source_class === 'rights-cleared').toBe(row.accepted)
    },
  )
})

describe('legacy entity media classification', () => {
  const pressAttributes = {
    image_type: 'press',
    is_verified_photo: true,
    image_author: 'Trần Phước',
    image_source: 'Báo Vĩnh Long',
    image_source_url: 'https://baovinhlong.com.vn/images/photo.webp',
    image_license: 'Permission granted for re-hosting',
    permission_evidence: 'owner-record:IMG-2026-001',
  }

  it('derives a rights-cleared descriptor only from complete documentary evidence', () => {
    expect(describeEntityImages({
      name: 'Đình Long Hồ',
      images: ['/img/entities/dinh-long-ho.webp'],
      attributes: pressAttributes,
    })).toEqual([expect.objectContaining({
      source_class: 'rights-cleared',
      source_kind: 'press',
      disclosure_key: 'entity-sourced-photo',
      short_label: aiDisclosure.sourced_photo.short_label,
      full_disclosure: aiDisclosure.sourced_photo.full_disclosure,
      credit: 'Trần Phước · Báo Vĩnh Long',
      source_url: 'https://baovinhlong.com.vn/images/photo.webp',
    })])
  })

  it.each([
    ['an unknown raw entity path', {}, 'no descriptor'],
    ['an incomplete sourced record', { ...pressAttributes, permission_evidence: undefined }, 'placeholder'],
    ['an AI record without an explicit false verified flag', { image_type: 'ai-generated' }, 'placeholder'],
    ['an AI record with a null verified flag', { image_type: 'ai-generated', is_verified_photo: null }, 'placeholder'],
    ['a placeholder record without an explicit false verified flag', { image_type: 'generated-placeholder' }, 'placeholder'],
  ])('fails closed for %s', (_label, attributes, expected) => {
    const descriptors = describeEntityImages({
      name: 'Đình Long Hồ',
      images: ['/img/entities/dinh-long-ho.webp'],
      attributes,
    })

    if (expected === 'no descriptor') {
      expect(descriptors).toEqual([])
      return
    }
    expect(descriptors).toEqual([expect.objectContaining({
      source_class: 'placeholder',
      disclosure_key: 'entity-placeholder',
    })])
  })
})

describe('entity image descriptor producers', () => {
  it('classifies only canonical legacy entity images with canonical AI disclosure', () => {
    expect(describeEntityImages({
      id: 'entity-1',
      name: 'Điểm đến',
      images: ['/img/entities/diem-den.webp'],
      attributes: { image_type: 'ai-generated', is_verified_photo: false },
    })).toEqual([
      expect.objectContaining({
        url: '/img/entities/diem-den.webp',
        alt: 'Điểm đến — ảnh minh họa',
        source_class: 'ai-generated',
        source_kind: 'entity-editorial',
        disclosure_key: 'entity-ai',
        short_label: aiDisclosure.entity_ai.short_label,
        full_disclosure: aiDisclosure.entity_ai.full_disclosure,
      }),
    ])
    expect(describeEntityImages({
      id: 'entity-1',
      name: 'Điểm đến',
      images: [
        'https://cdn.example/entity.webp',
        '/img/entities/UPPER.webp',
        '/img/entities/diem-den.webp?size=md',
      ],
    })).toEqual([])
  })

  it('omits unsafe legacy URLs and emits a canonical placeholder when no image remains', () => {
    expect(describeEntityImages({ id: 'entity-1', name: 'Điểm đến', images: ['javascript:alert(1)'] })).toEqual([])
    expect(describeEntityPlaceholder({ id: 'entity-1', name: 'Điểm đến' })).toEqual(expect.objectContaining({
      url: null,
      source_class: 'placeholder',
      source_kind: 'generated-placeholder',
      disclosure_key: 'entity-placeholder',
      full_disclosure: aiDisclosure.placeholder.full_disclosure,
    }))
  })

  it('keeps valid supplied descriptors authoritative over raw entity images', () => {
    const supplied = { ...apiEntityImage, url: '/descriptor.webp', alt: 'Supplied descriptor' }
    expect(describeEntityImages({
      id: 'entity-1',
      name: 'Điểm đến',
      images: ['/conflicting.webp'],
      image_descriptor: supplied,
    })).toEqual([expect.objectContaining({ url: '/descriptor.webp', alt: 'Supplied descriptor' })])
  })

  it('fails closed when a structured descriptor is invalid instead of relabeling a legacy URL', () => {
    expect(describeEntityImages({
      id: 'entity-1',
      name: 'Điểm đến',
      images: ['/legacy.webp'],
      image_descriptor: { ...apiEntityImage, url: 'javascript:alert(1)' },
    })).toEqual([])
  })

  it('parses a valid singleton when an explicitly supplied descriptor array is empty', () => {
    expect(describeEntityImages({
      id: 'entity-1',
      name: 'Điểm đến',
      images: ['/legacy.webp'],
      image_descriptors: [],
      image_descriptor: apiEntityImage,
    })).toEqual([apiEntityImage])
  })

  it('suppresses a structured UGC descriptor without assigning AI disclosure', () => {
    const descriptors = describeEntityImages({
      id: 'entity-1',
      name: 'Điểm đến',
      images: ['/legacy.webp'],
      image_descriptors: [apiReviewImage],
    })

    expect(descriptors).toEqual([])
  })

  it('allows an explicit canonical placeholder descriptor', () => {
    expect(describeEntityImages({
      id: 'entity-1',
      name: 'Điểm đến',
      image_descriptor: apiPlaceholderImage,
    })).toEqual([apiPlaceholderImage])
  })
})

describe('gallery image descriptors', () => {
  it('keeps entity and review source classes distinct', () => {
    expect(parseGalleryDescriptor(apiEntityImage)!.source_class).toBe('ai-generated')
    expect(parseGalleryDescriptor(apiReviewImage)!.source_class).toBe('user-uploaded')
  })

  it.each(['/img/entity.webp', '/media/entity.webp?v=2', 'https://cdn.example/entity.webp'])(
    'accepts the same renderable URL forms as the backend: %s',
    url => expect(parseGalleryDescriptor({ ...apiEntityImage, url })?.url).toBe(url),
  )

  it.each([
    '//cdn.example/entity.webp',
    'http://cdn.example/entity.webp',
    'data:image/png;base64,AA==',
    'javascript:alert(1)',
    'ftp://cdn.example/entity.webp',
    '/img\\entity.webp',
  ])('rejects unsafe URL form %s', (url) => {
    expect(parseGalleryDescriptor({ ...apiEntityImage, url })).toBeNull()
  })

  it.each([
    ['extra key', { ...apiReviewImage, extra: true }],
    ['missing key', Object.fromEntries(Object.entries(apiReviewImage).filter(([key]) => key !== 'credit'))],
    ['unclassified UGC', { ...apiReviewImage, source_class: 'user-uploaded', source_kind: 'entity-editorial' }],
    ['AI copy on UGC', { ...apiReviewImage, full_disclosure: aiDisclosure.entity_ai.full_disclosure }],
    ['altered short copy', { ...apiReviewImage, short_label: `${aiDisclosure.ugc_photo.short_label}!` }],
    ['blank alt', { ...apiReviewImage, alt: ' ' }],
    ['blank credit', { ...apiReviewImage, credit: ' ' }],
    ['fractional width', { ...apiReviewImage, width: 640.5, height: 480 }],
    ['partial dimensions', { ...apiReviewImage, width: 640, height: null }],
  ])('rejects %s', (_name, value) => {
    expect(parseGalleryDescriptor(value)).toBeNull()
  })

  it.each([
    apiEntityImage,
    apiPlaceholderImage,
    apiReviewImage,
    { ...apiReviewImage, source_kind: 'post-ugc' },
  ])('accepts only documented source combinations %#', (value) => {
    expect(parseGalleryDescriptor(value)).toEqual(value)
  })

  it('returns an owned frozen descriptor', () => {
    const input = { ...apiReviewImage }
    const parsed = parseGalleryDescriptor(input)
    expect(parsed).not.toBe(input)
    expect(Object.isFrozen(parsed)).toBe(true)
  })
})

describe('review photo normalization', () => {
  it.each(['//cdn.example/review.jpg', 'http://cdn.example/review.jpg', 'javascript:alert(1)', '/img\\review.jpg'])(
    'returns null so callers omit an unsafe review URL: %s',
    url => expect(normalizeReviewPhoto({ url, alt: 'Review photo' })).toBeNull(),
  )

  it('omits null review descriptors at the collection boundary', () => {
    const images = [
      { url: '/img/review.jpg', alt: 'Valid review photo' },
      { url: 'data:image/png;base64,AA==', alt: 'Invalid review photo' },
    ].flatMap((photo) => {
      const descriptor = normalizeReviewPhoto(photo)
      return descriptor ? [descriptor] : []
    })
    expect(images.map(image => image.url)).toEqual(['/img/review.jpg'])
  })

  it.each([
    [{ url: '/img/review.jpg', alt: ' ' }, 'review photo alt must be non-blank'],
    [{ url: '/img/review.jpg', alt: 'Review photo', credit: ' ' }, 'review photo credit must be non-blank'],
  ])('throws for invalid trusted review metadata %#', (input, message) => {
    expect(() => normalizeReviewPhoto(input)).toThrow(message)
  })

  it('classifies valid review input with canonical UGC disclosure copy', () => {
    const descriptor = normalizeReviewPhoto({
      url: '/img/review.jpg',
      alt: apiReviewImage.alt,
      credit: 'Lan',
    })

    expect(descriptor).toEqual(apiReviewImage)
    expect(Object.isFrozen(descriptor)).toBe(true)
  })
})
