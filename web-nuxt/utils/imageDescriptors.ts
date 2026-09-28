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
  'source_url',
  'url',
  'width',
]

const DESCRIPTOR_KEY_SIGNATURE = [...DESCRIPTOR_KEYS].sort().join('\0')

const DNS_LABEL_PATTERN = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$/
const PUNYCODE_PAYLOAD_PATTERN = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,57}[A-Za-z0-9])?$/
const POST_UGC_DATA_IMAGE_PREFIXES = [
  'data:image/jpeg;base64,',
  'data:image/png;base64,',
  'data:image/webp;base64,',
] as const

// A 10 MiB upload expands to about 13.34 MiB as base64; cap the persisted URL at 14 MiB.
export const MAX_POST_UGC_DATA_IMAGE_URL_CHARS = 14 * 1024 * 1024

const ALLOWED_SOURCE_COMBINATIONS = new Set([
  'ai-generated|entity-editorial|entity-ai',
  'placeholder|generated-placeholder|entity-placeholder',
  'user-uploaded|review-ugc|ugc-photo',
  'user-uploaded|post-ugc|ugc-photo',
  'rights-cleared|documentary|entity-sourced-photo',
  'rights-cleared|journalistic|entity-sourced-photo',
  'rights-cleared|official|entity-sourced-photo',
  'rights-cleared|press|entity-sourced-photo',
])

const RENDERABLE_ENTITY_SOURCE_COMBINATIONS = new Set([
  'ai-generated|entity-editorial|entity-ai',
  'placeholder|generated-placeholder|entity-placeholder',
  'rights-cleared|documentary|entity-sourced-photo',
  'rights-cleared|journalistic|entity-sourced-photo',
  'rights-cleared|official|entity-sourced-photo',
  'rights-cleared|press|entity-sourced-photo',
])

const CANONICAL_LEGACY_ENTITY_IMAGE_PATTERN = /^\/img\/entities\/[a-z0-9]+(?:-+[a-z0-9]+)*\.webp$/
const DOCUMENTARY_IMAGE_TYPES = new Set(['documentary', 'journalistic', 'official', 'press'])
const PLACEHOLDER_HOSTS = new Set([
  'example', 'example.test', 'example.com', 'example.net', 'example.org',
  'localhost', 'local', 'localdomain', 'invalid', 'test', 'home.arpa',
  'corp', 'internal', 'intranet', 'lan',
])
const CONCRETE_LICENSE_PATTERNS = [
  /\bcc0\s+1\.0\b/i,
  /\bcc\s*by\s+4\.0\b/i,
  /\bcc\s*by[-\s]sa\s+4\.0\b/i,
  /\bcc\s*by[-\s]nc[-\s]nd\s+4\.0\b/i,
  /\bpublic\s+domain\s+mark\s+1\.0\b/i,
]
const AFFIRMATIVE_GRANT_PATTERNS = [
  /\b(?:permitted|allowed)\s+(?:to\s+|for\s+)?(?:re-?host(?:ing)?|reuse|republish)\b/i,
  /\bpermission\s+granted\s+(?:to\s+|for\s+)?(?:re-?host(?:ing)?|reuse|republish)\b/i,
  /\b(?:re-?host(?:ing)?|reuse|republish)\s+(?:is\s+)?(?:permitted|allowed)\b/i,
  /\b(?:được\s+phép|cho\s+phép)\s+(?:re-?host|tái\s+(?:sử\s+dụng|lưu\s+trữ|đăng\s+lại|đăng\s+tải))\b/i,
]
const LICENSE_DENIAL_PATTERNS = [
  /\ball\s+rights\s+reserved\b/i,
  /\b(?:not|no|never|prohibited|forbidden|denied|unavailable|cannot)\b/i,
  /\bwithout\s+(?:permission|rights?|authorization)\b/i,
  /\bkhông\s+(?:được\s+phép|cho\s+phép)\b/i,
]

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

function normalizedStatement(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const normalized = value.trim().replace(/\s+/g, ' ')
  return normalized || null
}

function isAffirmativeLicenseScope(value: unknown): boolean {
  const statement = normalizedStatement(value)
  return statement !== null
    && !LICENSE_DENIAL_PATTERNS.some(pattern => pattern.test(statement))
    && [...CONCRETE_LICENSE_PATTERNS, ...AFFIRMATIVE_GRANT_PATTERNS].some(pattern => pattern.test(statement))
}

function selectedLicenseScope(attributes: Record<string, unknown>): string | null {
  const statements = [attributes.image_license, attributes.license_scope]
    .map(normalizedStatement)
    .filter((value): value is string => value !== null)
  if (statements.some(statement => LICENSE_DENIAL_PATTERNS.some(pattern => pattern.test(statement)))) return null
  return statements.find(statement => isAffirmativeLicenseScope(statement)) ?? null
}

function ipv4Value(hostname: string): number | null {
  const octets = hostname.split('.')
  if (octets.length !== 4 || !octets.every(octet => /^(0|[1-9][0-9]{0,2})$/.test(octet))) return null
  const values = octets.map(Number)
  if (values.some(value => value > 255)) return null
  return values.reduce((value, octet) => (value * 256) + octet, 0)
}

function isInIpv4Range(value: number, network: number, prefix: number): boolean {
  const mask = prefix === 0 ? 0 : (0xffffffff << (32 - prefix)) >>> 0
  return (value & mask) === (network & mask)
}

function parseIpv6Value(hostname: string): bigint | null {
  const host = hostname.replace(/^\[|\]$/g, '').toLowerCase()
  if (!host || (host.match(/::/g) ?? []).length > 1) return null
  const [leftRaw, rightRaw] = host.split('::')
  const parsePart = (part: string): number[] | null => {
    if (!part) return []
    const pieces = part.split(':')
    const values: number[] = []
    for (const piece of pieces) {
      if (piece.includes('.')) {
        const value = ipv4Value(piece)
        if (value === null) return null
        values.push(value >>> 16, value & 0xffff)
      } else if (/^[0-9a-f]{1,4}$/.test(piece)) {
        values.push(Number.parseInt(piece, 16))
      } else {
        return null
      }
    }
    return values
  }
  const left = parsePart(leftRaw ?? '')
  const right = parsePart(rightRaw ?? '')
  if (left === null || right === null) return null
  const missing = 8 - left.length - right.length
  if (missing < 0 || (host.includes('::') ? missing < 1 : missing !== 0)) return null
  const words = [...left, ...Array.from({ length: missing }, () => 0), ...right]
  return words.reduce((value, word) => (value << 16n) | BigInt(word), 0n)
}

function isInIpv6Range(value: bigint, network: bigint, prefix: number): boolean {
  if (prefix === 0) return true
  const mask = ((1n << BigInt(prefix)) - 1n) << BigInt(128 - prefix)
  return (value & mask) === (network & mask)
}

function isPublicIpv4Value(value: number): boolean {
  const privateRanges: Array<[number, number]> = [
    [0, 8], [0x0a000000, 8], [0x7f000000, 8], [0xa9fe0000, 16],
    [0xac100000, 12], [0xc0000000, 24], [0xc00000aa, 31], [0xc0000200, 24],
    [0xc0a80000, 16], [0xc6120000, 15], [0xc6336400, 24], [0xcb007100, 24],
    [0xf0000000, 4], [0xffffffff, 32],
  ]
  if (value === 0xc0000009 || value === 0xc000000a) return true
  if (isInIpv4Range(value, 0x64400000, 10)) return false
  return !privateRanges.some(([network, prefix]) => isInIpv4Range(value, network, prefix))
}

function isPublicIpv4(hostname: string): boolean | null {
  const value = ipv4Value(hostname)
  if (value === null) return null
  return isPublicIpv4Value(value)
}

function isPublicIpv6(hostname: string): boolean {
  const value = parseIpv6Value(hostname)
  if (value === null) return false
  const mapped = isInIpv6Range(value, 0xffffn << 32n, 96)
  if (mapped) return isPublicIpv4Value(Number(value & 0xffffffffn))
  const privateRanges: Array<[bigint, number]> = [
    [0n, 128], [0xffffn << 32n, 96], [0x64ff9b00000000000000000000000000n, 48],
    [0x10000000000000000000000000000000n, 64], [0x20010000000000000000000000000000n, 23],
    [0x20010db8000000000000000000000000n, 32], [0x20020000000000000000000000000000n, 16],
    [0x3fff0000000000000000000000000000n, 20], [0xfc00000000000000000000000000000000n, 7],
    [0xfe80000000000000000000000000000000n, 10],
  ]
  const exceptions: Array<[bigint, number]> = [
    [0x20010000000000000000000000000001n, 128], [0x20010000000000000000000000000002n, 128],
    [0x20010003000000000000000000000000n, 32], [0x20010470000000000000000000000000n, 48],
    [0x20012000000000000000000000000000n, 28], [0x20013000000000000000000000000000n, 28],
  ]
  return !privateRanges.some(([network, prefix]) => isInIpv6Range(value, network, prefix))
    || exceptions.some(([network, prefix]) => isInIpv6Range(value, network, prefix))
}

function isPublicProvenanceUrl(value: unknown): value is string {
  if (typeof value !== 'string' || !value.trim()) return false
  try {
    const url = new URL(value.trim())
    const hostname = url.hostname.toLowerCase().replace(/\.$/, '')
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.hash) return false
    if (!url.pathname || url.pathname === '/') return false
    const ipv4 = isPublicIpv4(hostname)
    if (ipv4 !== null) return ipv4
    if (hostname.includes(':')) return isPublicIpv6(hostname)
    return hostname.includes('.') && ![...PLACEHOLDER_HOSTS].some(suffix => hostname === suffix || hostname.endsWith(`.${suffix}`))
  } catch {
    return false
  }
}

type SourcedPhotoEvidence = {
  imageType: 'documentary' | 'journalistic' | 'official' | 'press'
  credit: string
  sourceUrl: string
}

function sourcedPhotoEvidence(attributes: Record<string, unknown>): SourcedPhotoEvidence | null {
  const imageType = normalizedStatement(attributes.image_type)?.toLowerCase()
  const author = normalizedStatement(attributes.image_author)
  const source = normalizedStatement(attributes.image_source)
  const sourceUrl = normalizedStatement(attributes.image_source_url)
  const permissionEvidence = normalizedStatement(attributes.permission_evidence)
  if (
    imageType === undefined
    || !DOCUMENTARY_IMAGE_TYPES.has(imageType)
    || attributes.is_verified_photo !== true
    || !author
    || !source
    || !sourceUrl
    || !isPublicProvenanceUrl(sourceUrl)
    || !selectedLicenseScope(attributes)
    || !permissionEvidence
  ) return null
  return {
    imageType: imageType as SourcedPhotoEvidence['imageType'],
    credit: `${author} · ${source}`,
    sourceUrl,
  }
}

function normalizePostUgcImageUrl(value: unknown): string | null {
  const renderable = normalizeRenderableImageUrl(value)
  if (renderable !== null) return renderable
  if (typeof value !== 'string' || value.length > MAX_POST_UGC_DATA_IMAGE_URL_CHARS) return null

  const prefix = POST_UGC_DATA_IMAGE_PREFIXES.find(candidate => value.startsWith(candidate))
  if (!prefix || !hasValidBase64Payload(value, prefix.length)) return null
  return value
}

function isBase64Code(code: number): boolean {
  return (
    (code >= 48 && code <= 57)
    || (code >= 65 && code <= 90)
    || (code >= 97 && code <= 122)
    || code === 43
    || code === 47
  )
}

function hasValidBase64Payload(value: string, payloadStart: number): boolean {
  const payloadLength = value.length - payloadStart
  if (payloadLength <= 0 || payloadLength % 4 !== 0) return false

  let padding = 0
  if (value.endsWith('=')) {
    padding = 1
    if (value.endsWith('==')) padding = 2
  }
  const payloadEnd = value.length - padding
  if (padding === 1 && (payloadEnd - payloadStart) % 4 !== 3) return false
  if (padding === 2 && (payloadEnd - payloadStart) % 4 !== 2) return false

  for (let index = payloadStart; index < payloadEnd; index++) {
    if (!isBase64Code(value.charCodeAt(index))) return false
  }
  for (let index = payloadEnd; index < value.length; index++) {
    if (value.charCodeAt(index) !== 61) return false
  }
  return true
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
      : descriptor.disclosure_key === 'entity-sourced-photo'
        ? aiDisclosure.sourced_photo
        : aiDisclosure.ugc_photo
  if (
    descriptor.short_label !== canonical.short_label
    || descriptor.full_disclosure !== canonical.full_disclosure
  ) return null
  if (descriptor.source_class !== 'placeholder' && descriptor.url === null) return null
  if (descriptor.source_class === 'rights-cleared') {
    if (typeof descriptor.credit !== 'string' || !descriptor.credit.trim() || !isPublicProvenanceUrl(descriptor.source_url)) return null
  } else {
    if (descriptor.source_url !== null) return null
    if (descriptor.source_class !== 'user-uploaded' && descriptor.credit !== null) return null
  }

  const dimensions = [descriptor.width, descriptor.height]
  if (dimensions.some(dimension => (
    dimension !== null
    && (typeof dimension !== 'number' || !Number.isInteger(dimension) || dimension <= 0)
  ))) return null
  if ((descriptor.width === null) !== (descriptor.height === null)) return null

  return Object.freeze({ ...descriptor, url: normalizedUrl }) as unknown as ImageDescriptor
}

function isRenderableEntityDescriptor(descriptor: Readonly<ImageDescriptor>): boolean {
  return RENDERABLE_ENTITY_SOURCE_COMBINATIONS.has([
    descriptor.source_class,
    descriptor.source_kind,
    descriptor.disclosure_key,
  ].join('|'))
}

export function isCanonicalLegacyEntityImageUrl(value: unknown): value is string {
  return typeof value === 'string' && CANONICAL_LEGACY_ENTITY_IMAGE_PATTERN.test(value)
}

const ENTITY_EDITORIAL_UPLOAD_ERROR = [
  'entity.images accepts AI editorial media only',
  'entity.images chỉ nhận AI editorial',
].join('; ')

/** Keep this admin upload path AI-only; rights-cleared press media uses audited ingestion. */
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
    source_url: null,
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
    source_url: null,
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

export type UgcPreviewRow = Readonly<{
  rawIndex: number
  rawValue: unknown
  descriptor: Readonly<ImageDescriptor> | null
  status: 'valid' | 'invalid'
  auditText: string
}>

const INVALID_UGC_PREVIEW_AUDIT_TEXT = 'Ảnh xem trước không hợp lệ; ảnh không được hiển thị.'

function describeUgcPreviewRows(
  input: any,
  describeImages: (isolatedInput: any) => ImageDescriptor[],
): UgcPreviewRow[] {
  return imageRows(input).map((rawValue, rawIndex) => {
    const descriptor = describeImages({
      display_name: input?.display_name,
      images: [rawValue],
      image_credits: [creditAt(input, rawIndex)],
    })[0] ?? null
    return {
      rawIndex,
      rawValue,
      descriptor,
      status: descriptor ? 'valid' : 'invalid',
      auditText: descriptor?.full_disclosure || INVALID_UGC_PREVIEW_AUDIT_TEXT,
    }
  })
}

/** Preserve raw composer indices even when post image validation fails closed. */
export function describePostPreviewRows(input: any): UgcPreviewRow[] {
  return describeUgcPreviewRows(input, describePostImages)
}

/** Preserve raw uploader indices even when review image validation fails closed. */
export function describeReviewPreviewRows(input: any): UgcPreviewRow[] {
  return describeUgcPreviewRows(input, describeReviewImages)
}

type EntityImageLike = {
  id?: unknown
  name?: unknown
  images?: unknown
  image?: unknown
  image_descriptor?: unknown
  image_descriptors?: unknown
  attributes?: unknown
}

function classifiedLocalImages(entity: EntityImageLike): Array<{ index: number, url: string }> {
  const values = Array.isArray(entity.images)
    ? entity.images
    : typeof entity.image === 'string'
      ? [entity.image]
      : []
  return values.flatMap((value, index) => {
    const url = normalizeRenderableImageUrl(value)
    return url?.startsWith('/') ? [{ index, url }] : []
  })
}

function classifiedPlaceholder(url: string, entity: EntityImageLike, index: number): ImageDescriptor {
  const name = typeof entity.name === 'string' && entity.name.trim() ? entity.name.trim() : 'Địa điểm'
  return {
    url,
    alt: `${name} — minh họa chưa được xác minh ${index + 1}`,
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
    return parsed && isRenderableEntityDescriptor(parsed) ? [parsed] : []
  })
  return { present: hasMany || hasOne, descriptors }
}

/** Convert API descriptors or legacy entity image URLs at the shared render boundary. */
export function describeEntityImages(entity: EntityImageLike): ImageDescriptor[] {
  const supplied = suppliedEntityDescriptors(entity)
  if (supplied.present) return supplied.descriptors

  if (!entity.attributes || typeof entity.attributes !== 'object' || Array.isArray(entity.attributes)) return []
  const attributes = entity.attributes as Record<string, unknown>
  const mediaClass = normalizedStatement(attributes.image_type)?.toLowerCase()
  if (mediaClass !== 'ai-generated' && mediaClass !== 'generated-placeholder' && !DOCUMENTARY_IMAGE_TYPES.has(mediaClass || '')) return []

  const evidence = sourcedPhotoEvidence(attributes)
  return classifiedLocalImages(entity).map(({ index, url }) => {
    if (evidence) return {
      url,
      alt: `${typeof entity.name === 'string' && entity.name.trim() ? entity.name.trim() : 'Địa điểm'} — ảnh tư liệu ${index + 1}`,
      source_class: 'rights-cleared',
      source_kind: evidence.imageType,
      disclosure_key: 'entity-sourced-photo',
      short_label: aiDisclosure.sourced_photo.short_label,
      full_disclosure: aiDisclosure.sourced_photo.full_disclosure,
      credit: evidence.credit,
      source_url: evidence.sourceUrl,
      width: null,
      height: null,
    } satisfies ImageDescriptor
    if (mediaClass === 'ai-generated' && attributes.is_verified_photo === false) return {
      url,
      alt: descriptorAlt(entity),
      source_class: 'ai-generated',
      source_kind: 'entity-editorial',
      disclosure_key: 'entity-ai',
      short_label: aiDisclosure.entity_ai.short_label,
      full_disclosure: aiDisclosure.entity_ai.full_disclosure,
      credit: null,
      source_url: null,
      width: null,
      height: null,
    } satisfies ImageDescriptor
    return classifiedPlaceholder(url, entity, index)
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
    source_url: null,
    width: null,
    height: null,
  }
}
