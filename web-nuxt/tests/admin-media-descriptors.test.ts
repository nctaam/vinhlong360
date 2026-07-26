// @vitest-environment node

import { describe, expect, it } from 'vitest'
import { aiDisclosure } from '../utils/aiDisclosure'
import { adminRawMediaUrl, describeAdminRawMedia } from '../utils/adminMediaDescriptors'

describe('admin raw media descriptors', () => {
  it('preserves noncanonical stored media for authenticated moderation', () => {
    const raw = '/uploads/community-photo.webp'
    const descriptor = describeAdminRawMedia({
      url: raw,
      entity_name: 'Diem den thu',
      credit: 'Nguoi dung',
    })

    expect(descriptor).toEqual(expect.objectContaining({
      url: raw,
      source_class: 'user-uploaded',
      source_kind: 'post-ugc',
      disclosure_key: 'ugc-photo',
      full_disclosure: aiDisclosure.ugc_photo.full_disclosure,
      credit: 'Nguoi dung',
      moderation_only: true,
      raw_value: raw,
    }))
  })

  it('keeps canonical entity media classified as AI editorial', () => {
    const descriptor = describeAdminRawMedia({
      url: '/img/entities/admin-media.webp',
      entity_name: 'Diem den thu',
    })

    expect(descriptor).toEqual(expect.objectContaining({
      url: '/img/entities/admin-media.webp',
      source_class: 'ai-generated',
      source_kind: 'entity-editorial',
      disclosure_key: 'entity-ai',
      moderation_only: true,
    }))
  })

  it('extracts raw URLs without accepting malformed stored shapes', () => {
    expect(adminRawMediaUrl({ url: '/uploads/object.webp' })).toBe('/uploads/object.webp')
    expect(adminRawMediaUrl({ url: 42 })).toBeNull()
    expect(adminRawMediaUrl(['nested'])).toBeNull()

    const descriptor = describeAdminRawMedia({ url: 'javascript:alert(1)' })
    expect(descriptor.url).toBeNull()
    expect(descriptor.source_class).toBe('placeholder')
    expect(descriptor.raw_value).toBe('javascript:alert(1)')
  })
})
