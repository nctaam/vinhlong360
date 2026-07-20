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

const DNS_LABEL_PATTERN = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$/
const PUNYCODE_PAYLOAD_PATTERN = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,57}[A-Za-z0-9])?$/
const POST_UGC_DATA_IMAGE_PATTERN = /^data:image\/(?:jpeg|png|webp);base64,(?=.+$)(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/

const ALLOWED_SOURCE_COMBINATIONS = new Set([
  'ai-generated|entity-editorial|entity-ai',
  'placeholder|generated-placeholder|entity-placeholder',
  'user-uploaded|review-ugc|ugc-photo',
  'user-uploaded|post-ugc|ugc-photo',
])

function isValidPort(port: string): boolean {
  if (port.length > 5 || !/^[0-9]+$/.test(port)) return false
  const value = Number(port)
  return Number.isSafeInteger(value) && value >= 1 && value <= 65535
}

function isValidPunycodeLabel(label: string): boolean {
  if (!label.toLowerCase().startsWith('xn--')) return true
  return PUNYCODE_PAYLOAD_PATTERN.test(label.slice(4))
}

function isValidDnsHost(host: string): boolean {
  if (!host || host.length > 253) return false
  const labels = host.split('.')
  if (labels.some(label => (
    !DNS_LABEL_PATTERN.test(label)
    || !isValidPunycodeLabel(label)
  ))) return false

  if (labels.every(label => /^\d+$/.test(label))) {
    if (labels.length !== 4) return false
    return labels.every(label => (
      (label === '0' || !label.startsWith('0'))
      && Number(label) <= 255
    ))
  }
  return true
}

function isValidHttpsAuthority(authority: string): boolean {
  if (!authority || authority.includes('@') || authority.includes('%')) return false

  if (authority.startsWith('[')) {
    const closing = authority.indexOf(']')
    if (
      closing <= 1
      || authority.indexOf('[', 1) !== -1
      || authority.indexOf(']', closing + 1) !== -1
    ) return false
    const host = authority.slice(1, closing)
    const suffix = authority.slice(closing + 1)
    if (suffix && (!suffix.startsWith(':') || !isValidPort(suffix.slice(1)))) return false
    try {
      // WHATWG URL validates the bracketed IPv6 grammar after the lexical checks above.
      new URL(`https://[${host}]/`)
    } catch {
      return false
    }
    return true
  }

  if (authority.includes('[') || authority.includes(']')) return false
  if ((authority.match(/:/g) ?? []).length > 1) return false
  const separator = authority.indexOf(':')
  if (separator >= 0) {
    if (!isValidPort(authority.slice(separator + 1))) return false
    authority = authority.slice(0, separator)
  }
  return isValidDnsHost(authority)
}

export function normalizeRenderableImageUrl(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const url = value.trim()
  if (!url || /[\u0000-\u0020\u007f\\]/.test(url) || url.includes('#')) return null
  if (url.startsWith('//')) return null
  if (url.startsWith('/')) return url
  if (!/^https:\/\//i.test(url)) return null

  const remainder = url.slice(8)
  let authorityEnd = remainder.length
  for (const delimiter of ['/', '?']) {
    const position = remainder.indexOf(delimiter)
    if (position >= 0) authorityEnd = Math.min(authorityEnd, position)
  }
  return isValidHttpsAuthority(remainder.slice(0, authorityEnd)) ? url : null
}

function normalizePostUgcImageUrl(value: unknown): string | null {
  const renderable = normalizeRenderableImageUrl(value)
  if (renderable !== null) return renderable
  return typeof value === 'string' && POST_UGC_DATA_IMAGE_PATTERN.test(value) ? value : null
}

function normalizeDescriptorImageUrl(
  value: unknown,
  descriptor: Record<string, unknown>,
): string | null {
  if (
    descriptor.source_class === 'user-uploaded'
    && descriptor.source_kind === 'post-ugc'
    && descriptor.disclosure_key === 'ugc-photo'
  ) return normalizePostUgcImageUrl(value)
  return normalizeRenderableImageUrl(value)
}

export function parseGalleryDescriptor(value: unknown): Readonly<ImageDescriptor> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const descriptor = value as Record<string, unknown>
  if (Object.keys(descriptor).sort().join('\0') !== DESCRIPTOR_KEY_SIGNATURE) return null

  const normalizedUrl = descriptor.url === null ? null : normalizeDescriptorImageUrl(descriptor.url, descriptor)
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

const ENTITY_EDITORIAL_UPLOAD_ERROR = [
  'entity.images accepts AI editorial media only',
  'entity.images chỉ nhận AI editorial',
].join('; ')

/** Enforce the AI-only entity image contract before admin data reaches the API. */
export function normalizeEntityEditorialUpload(value: unknown): Readonly<ImageDescriptor> {
  const descriptor = parseGalleryDescriptor(value)
  if (
    descriptor === null
    || descriptor.source_class !== 'ai-generated'
    || descriptor.source_kind !== 'entity-editorial'
    || descriptor.disclosure_key !== 'entity-ai'
    || descriptor.url === null
  ) {
    throw new TypeError(ENTITY_EDITORIAL_UPLOAD_ERROR)
  }
  return descriptor
}

export function normalizeReviewPhoto(input: {
  url: unknown
  alt: unknown
  credit?: unknown
}): Readonly<ImageDescriptor> | null {
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

type UGCPhotoInput = {
  url: unknown
  alt: unknown
  credit?: unknown
}

function normalizeUgcPhoto(
  input: UGCPhotoInput,
  sourceKind: 'post-ugc' | 'review-ugc',
  label: 'post' | 'review',
): Readonly<ImageDescriptor> | null {
  const url = sourceKind === 'post-ugc'
    ? normalizePostUgcImageUrl(input.url)
    : normalizeRenderableImageUrl(input.url)
  if (url === null) return null

  if (typeof input.alt !== 'string' || !input.alt.trim()) {
    throw new TypeError(`${label} photo alt must be non-blank`)
  }
  if (input.credit !== undefined && input.credit !== null && typeof input.credit !== 'string') {
    throw new TypeError(`${label} photo credit must be a string`)
  }
  const credit = typeof input.credit === 'string' ? input.credit.trim() || null : null
  const descriptor = {
    url,
    alt: input.alt.trim(),
    source_class: 'user-uploaded' as const,
    source_kind: sourceKind,
    disclosure_key: 'ugc-photo' as const,
    short_label: aiDisclosure.ugc_photo.short_label,
    full_disclosure: aiDisclosure.ugc_photo.full_disclosure,
    credit,
    width: null,
    height: null,
  }
  return parseGalleryDescriptor(descriptor)
}

function suppliedUgcDescriptor(value: unknown, sourceKind: 'post-ugc' | 'review-ugc'): Readonly<ImageDescriptor> | null {
  const parsed = parseGalleryDescriptor(value)
  if (!parsed || parsed.source_class !== 'user-uploaded' || parsed.source_kind !== sourceKind || parsed.disclosure_key !== 'ugc-photo') return null
  return parseGalleryDescriptor({
    ...parsed,
    alt: parsed.alt.trim(),
    credit: parsed.credit?.trim() || null,
  })
}

function imageRows(input: any): unknown[] {
  if (Array.isArray(input)) return input
  if (Array.isArray(input?.images)) return input.images
  return []
}

function descriptorRows(input: any): unknown[] {
  if (Array.isArray(input?.image_descriptors)) return input.image_descriptors
  if (Object.prototype.hasOwnProperty.call(input || {}, 'image_descriptor')) return [input.image_descriptor]
  return []
}

function creditAt(input: any, index: number): unknown {
  const credits = input?.image_credits ?? input?.credits ?? input?.imageCredits
  return Array.isArray(credits) ? credits[index] : input?.credit
}

function describedCredit(value: unknown): string | null {
  return typeof value === 'string' ? value.trim() || null : null
}

function describedAlt(value: unknown, fallback: string): string {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

/** Normalize post-uploaded media without inferring or changing its source classification. */
export function normalizePostPhoto(input: UGCPhotoInput): Readonly<ImageDescriptor> | null {
  return normalizeUgcPhoto(input, 'post-ugc', 'post')
}

/** Describe only post UGC; pre-classified non-post descriptors are ignored, never reclassified. */
export function describePostImages(input: any): ImageDescriptor[] {
  const supplied = descriptorRows(input).flatMap(value => {
    const descriptor = suppliedUgcDescriptor(value, 'post-ugc')
    return descriptor ? [descriptor] : []
  })
  if (descriptorRows(input).length) return supplied

  const name = typeof input?.display_name === 'string' && input.display_name.trim()
    ? input.display_name.trim()
    : 'Bài viết'
  return imageRows(input).flatMap((value, index) => {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      const row = value as Record<string, unknown>
      const descriptor = suppliedUgcDescriptor(row, 'post-ugc')
      if (descriptor) return [descriptor]
      if (Object.prototype.hasOwnProperty.call(row, 'source_class')) return []
      const normalized = normalizePostPhoto({
        url: row.url,
        alt: describedAlt(row.alt, `${name} — ảnh bài viết ${index + 1}`),
        credit: describedCredit(row.credit ?? creditAt(input, index)),
      })
      return normalized ? [normalized] : []
    }
    const descriptor = normalizePostPhoto({
      url: value,
      alt: `${name} — ảnh bài viết ${index + 1}`,
      credit: describedCredit(creditAt(input, index)),
    })
    return descriptor ? [descriptor] : []
  })
}

/** Describe only review UGC; pre-classified non-review descriptors are ignored, never reclassified. */
export function describeReviewImages(input: any): ImageDescriptor[] {
  const supplied = descriptorRows(input).flatMap(value => {
    const descriptor = suppliedUgcDescriptor(value, 'review-ugc')
    return descriptor ? [descriptor] : []
  })
  if (descriptorRows(input).length) return supplied

  const name = typeof input?.display_name === 'string' && input.display_name.trim()
    ? input.display_name.trim()
    : 'Đánh giá'
  return imageRows(input).flatMap((value, index) => {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      const row = value as Record<string, unknown>
      const descriptor = suppliedUgcDescriptor(row, 'review-ugc')
      if (descriptor) return [descriptor]
      if (Object.prototype.hasOwnProperty.call(row, 'source_class')) return []
      const normalized = normalizeUgcPhoto({
        url: row.url,
        alt: describedAlt(row.alt, `${name} — ảnh đánh giá ${index + 1}`),
        credit: describedCredit(row.credit ?? creditAt(input, index)),
      }, 'review-ugc', 'review')
      return normalized ? [normalized] : []
    }
    const descriptor = normalizeUgcPhoto({
      url: value,
      alt: `${name} — ảnh đánh giá ${index + 1}`,
      credit: describedCredit(creditAt(input, index)),
    }, 'review-ugc', 'review')
    return descriptor ? [descriptor] : []
  })
}

type EntityImageLike = {
  id?: unknown
  name?: unknown
  images?: unknown
  image?: unknown
  image_descriptor?: unknown
  image_descriptors?: unknown
}

function descriptorAlt(entity: EntityImageLike): string {
  const name = typeof entity.name === 'string' && entity.name.trim() ? entity.name.trim() : 'Địa điểm'
  return `${name} — ảnh minh họa`
}

function suppliedEntityDescriptors(entity: EntityImageLike): {
  present: boolean
  descriptors: ImageDescriptor[]
} {
  const hasMany = Object.prototype.hasOwnProperty.call(entity, 'image_descriptors')
  const hasOne = Object.prototype.hasOwnProperty.call(entity, 'image_descriptor')
  const supplied = [
    ...(hasMany && Array.isArray(entity.image_descriptors) ? entity.image_descriptors : []),
    ...(hasOne ? [entity.image_descriptor] : []),
  ]
  const descriptors = supplied.flatMap(value => {
    const parsed = parseGalleryDescriptor(value)
    return parsed ? [parsed] : []
  })
  return { present: hasMany || hasOne, descriptors }
}

/** Convert API descriptors or legacy entity image URLs at the shared render boundary. */
export function describeEntityImages(entity: EntityImageLike): ImageDescriptor[] {
  const supplied = suppliedEntityDescriptors(entity)
  if (supplied.present) return supplied.descriptors

  const legacy = Array.isArray(entity.images)
    ? entity.images
    : typeof entity.image === 'string'
      ? [entity.image]
      : []
  return legacy.flatMap(value => {
    const url = normalizeRenderableImageUrl(value)
    if (!url) return []
    return [{
      url,
      alt: descriptorAlt(entity),
      source_class: 'ai-generated',
      source_kind: 'entity-editorial',
      disclosure_key: 'entity-ai',
      short_label: aiDisclosure.entity_ai.short_label,
      full_disclosure: aiDisclosure.entity_ai.full_disclosure,
      credit: null,
      width: null,
      height: null,
    } satisfies ImageDescriptor]
  })
}

export function describeEntityPlaceholder(entity: EntityImageLike): ImageDescriptor {
  const name = typeof entity.name === 'string' && entity.name.trim() ? entity.name.trim() : 'Địa điểm'
  return {
    url: null,
    alt: `${name} — chưa có ảnh riêng`,
    source_class: 'placeholder',
    source_kind: 'generated-placeholder',
    disclosure_key: 'entity-placeholder',
    short_label: aiDisclosure.placeholder.short_label,
    full_disclosure: aiDisclosure.placeholder.full_disclosure,
    credit: null,
    width: null,
    height: null,
  }
}
