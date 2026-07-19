import type { ImageDescriptor } from '../types/image'
import { aiDisclosure } from './aiDisclosure'

const DESCRIPTOR_KEYS = [
  'alt',
  'credit',
  'disclosure_key',
  'full_disclosure',
  'height',
  'short_label',
  'source_class',
  'source_kind',
  'url',
  'width',
]

const DESCRIPTOR_KEY_SIGNATURE = [...DESCRIPTOR_KEYS].sort().join('\0')

const ALLOWED_SOURCE_COMBINATIONS = new Set([
  'ai-generated|entity-editorial|entity-ai',
  'placeholder|generated-placeholder|entity-placeholder',
  'user-uploaded|review-ugc|ugc-photo',
  'user-uploaded|post-ugc|ugc-photo',
])

export function normalizeRenderableImageUrl(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const url = value.trim()
  if (!url || /[\u0000-\u0020\u007f\\]/.test(url) || url.includes('#')) return null
  if (url.startsWith('//')) return null
  if (url.startsWith('/')) return url
  if (!/^https:\/\/[^/]/i.test(url)) return null

  try {
    const authority = url.slice(url.indexOf('//') + 2).split(/[/?#]/, 1)[0]
    const parsed = new URL(url)
    if (
      parsed.protocol !== 'https:'
      || !parsed.hostname
      || authority?.includes('@')
      || authority?.includes('%')
      || parsed.username
      || parsed.password
      || authority?.endsWith(':')
    ) return null
    return url
  } catch {
    return null
  }
}

export function parseGalleryDescriptor(value: unknown): ImageDescriptor | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const descriptor = value as Record<string, unknown>
  if (Object.keys(descriptor).sort().join('\0') !== DESCRIPTOR_KEY_SIGNATURE) return null

  const normalizedUrl = descriptor.url === null ? null : normalizeRenderableImageUrl(descriptor.url)
  if (descriptor.url !== null && normalizedUrl === null) return null
  if (typeof descriptor.alt !== 'string' || !descriptor.alt.trim()) return null
  if (descriptor.credit !== null && (typeof descriptor.credit !== 'string' || !descriptor.credit.trim())) return null
  if (descriptor.short_label !== null && (typeof descriptor.short_label !== 'string' || !descriptor.short_label.trim())) return null
  if (typeof descriptor.full_disclosure !== 'string' || !descriptor.full_disclosure.trim()) return null
  if (
    typeof descriptor.source_class !== 'string'
    || typeof descriptor.source_kind !== 'string'
    || typeof descriptor.disclosure_key !== 'string'
  ) return null

  const combination = `${descriptor.source_class}|${descriptor.source_kind}|${descriptor.disclosure_key}`
  if (!ALLOWED_SOURCE_COMBINATIONS.has(combination)) return null

  const canonical = descriptor.disclosure_key === 'entity-ai'
    ? aiDisclosure.entity_ai
    : descriptor.disclosure_key === 'entity-placeholder'
      ? aiDisclosure.placeholder
      : aiDisclosure.ugc_photo
  if (
    descriptor.short_label !== canonical.short_label
    || descriptor.full_disclosure !== canonical.full_disclosure
  ) return null
  if (descriptor.source_class !== 'placeholder' && descriptor.url === null) return null
  if (descriptor.source_class !== 'user-uploaded' && descriptor.credit !== null) return null

  const dimensions = [descriptor.width, descriptor.height]
  if (dimensions.some(dimension => (
    dimension !== null
    && (typeof dimension !== 'number' || !Number.isInteger(dimension) || dimension <= 0)
  ))) return null
  if ((descriptor.width === null) !== (descriptor.height === null)) return null

  return Object.freeze({ ...descriptor, url: normalizedUrl }) as unknown as ImageDescriptor
}

export function normalizeReviewPhoto(input: {
  url: unknown
  alt: unknown
  credit?: unknown
}): ImageDescriptor | null {
  const url = normalizeRenderableImageUrl(input.url)
  if (url === null) return null
  if (typeof input.alt !== 'string' || !input.alt.trim()) {
    throw new TypeError('review photo alt must be non-blank')
  }
  if (
    input.credit !== undefined
    && input.credit !== null
    && (typeof input.credit !== 'string' || !input.credit.trim())
  ) {
    throw new TypeError('review photo credit must be non-blank')
  }

  const descriptor = {
    url,
    alt: input.alt,
    source_class: 'user-uploaded',
    source_kind: 'review-ugc',
    disclosure_key: 'ugc-photo',
    short_label: aiDisclosure.ugc_photo.short_label,
    full_disclosure: aiDisclosure.ugc_photo.full_disclosure,
    credit: (input.credit as string | null | undefined) ?? null,
    width: null,
    height: null,
  }
  const parsed = parseGalleryDescriptor(descriptor)
  if (parsed === null) throw new Error('review photo descriptor invariant failed')
  return parsed
}
