import type { ImageDescriptor } from '../types/image'
import { aiDisclosure } from './aiDisclosure'
import {
  describeEntityPlaceholder,
  isCanonicalLegacyEntityImageUrl,
  normalizeRenderableImageUrl,
} from './imageDescriptors'

export interface AdminMediaDescriptor extends ImageDescriptor {
  moderation_only: true
  raw_value: unknown
}

export function adminRawMediaUrl(value: unknown): string | null {
  if (typeof value === 'string') return value
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const url = (value as Record<string, unknown>).url
  return typeof url === 'string' ? url : null
}

/** Describe stored media for authenticated moderation without granting public provenance. */
export function describeAdminRawMedia(input: {
  url: unknown
  entity_name?: unknown
  credit?: unknown
}): AdminMediaDescriptor {
  const name = typeof input.entity_name === 'string' && input.entity_name.trim()
    ? input.entity_name.trim()
    : 'Entity'
  const url = normalizeRenderableImageUrl(adminRawMediaUrl(input.url))

  if (url === null) {
    return {
      ...describeEntityPlaceholder({ name }),
      moderation_only: true,
      raw_value: input.url,
    }
  }

  if (isCanonicalLegacyEntityImageUrl(url)) {
    return {
      url,
      alt: `${name} — ảnh minh họa`,
      source_class: 'ai-generated',
      source_kind: 'entity-editorial',
      disclosure_key: 'entity-ai',
      short_label: aiDisclosure.entity_ai.short_label,
      full_disclosure: aiDisclosure.entity_ai.full_disclosure,
      credit: null,
      width: null,
      height: null,
      moderation_only: true,
      raw_value: input.url,
    }
  }

  const credit = typeof input.credit === 'string' && input.credit.trim()
    ? input.credit.trim()
    : null
  return {
    url,
    alt: `${name} — ảnh cần kiểm duyệt`,
    source_class: 'user-uploaded',
    source_kind: 'post-ugc',
    disclosure_key: 'ugc-photo',
    short_label: aiDisclosure.ugc_photo.short_label,
    full_disclosure: aiDisclosure.ugc_photo.full_disclosure,
    credit,
    width: null,
    height: null,
    moderation_only: true,
    raw_value: input.url,
  }
}
