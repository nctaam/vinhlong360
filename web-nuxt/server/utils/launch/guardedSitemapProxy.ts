import type { H3Event } from 'h3'
import { useRuntimeConfig } from 'nitropack/runtime'

import type { LaunchSafetyDecision } from '../../../types/launch'

const XML_CONTENT_TYPE = 'application/xml; charset=utf-8'
const SHA256_PATTERN = /^[a-f0-9]{64}$/u
const PINNED_QUERY_PATTERN = /^\?batch=([a-f0-9]{64})$/u
const ROOT_SITEMAP_DOCUMENTS = new Set<RootSitemapDocument>([
  'sitemap.xml',
  'sitemap-media.xml',
  'sitemap-index.xml',
])
const LAUNCH_HEADER_NAMES = new Set([
  'x-launch-policy-fingerprint',
  'x-launch-route-manifest-revision',
  'x-launch-backend-policy-revision',
  'x-launch-sitemap-batch-revision',
  'x-launch-sitemap-requested-batch',
])

export type RootSitemapDocument = 'sitemap.xml' | 'sitemap-media.xml' | 'sitemap-index.xml'

export type GuardedSitemapFailureReason =
  | 'sitemap-batch-unavailable'
  | 'sitemap-evidence-mismatch'

export class GuardedSitemapFailure extends Error {
  constructor(readonly reason: GuardedSitemapFailureReason) {
    super(reason)
    this.name = 'GuardedSitemapFailure'
  }
}

export interface InternalRawSitemapResponse {
  readonly status: number
  readonly body: string
  readonly headers: Record<string, string>
}

export type InternalRawFetcher = (
  document: RootSitemapDocument,
  requestedBatch: string | null,
) => Promise<InternalRawSitemapResponse>

interface RawHeaderCollection {
  forEach(callback: (value: string, key: string) => void): void
}

interface RawHttpResponse {
  readonly status: number
  readonly _data?: unknown
  readonly headers: RawHeaderCollection
}

interface RawHttpFetchOptions {
  readonly method: 'GET'
  readonly responseType: 'text'
  readonly redirect: 'manual'
  readonly ignoreResponseError: true
  readonly retry: false
  readonly headers: { readonly accept: 'application/xml' }
}

export type InternalRawHttpFetcher = (
  request: string,
  options: RawHttpFetchOptions,
) => Promise<RawHttpResponse>

interface GuardedSitemapInput {
  readonly event: H3Event
  readonly document: RootSitemapDocument
  readonly decision: Readonly<LaunchSafetyDecision>
  readonly url: URL
  readonly fetchRaw: InternalRawFetcher
}

export interface GuardedSitemapSuccess {
  readonly status: 200
  readonly body: string
  readonly contentType: typeof XML_CONTENT_TYPE
  readonly decision: Readonly<LaunchSafetyDecision>
  readonly requestedBatch: string | null
  readonly failureReason: null
}

export interface GuardedSitemapUnavailable {
  readonly status: 503
  readonly body: ''
  readonly contentType: typeof XML_CONTENT_TYPE
  readonly decision: Readonly<LaunchSafetyDecision>
  readonly requestedBatch: null
  readonly failureReason: GuardedSitemapFailureReason
}

export type GuardedSitemapResult = GuardedSitemapSuccess | GuardedSitemapUnavailable

function defaultRawHttpFetcher(
  request: string,
  options: RawHttpFetchOptions,
): Promise<RawHttpResponse> {
  const raw = ($fetch as unknown as { raw: InternalRawHttpFetcher }).raw
  return raw(request, options)
}

function snapshotDecision(decision: Readonly<LaunchSafetyDecision>): Readonly<LaunchSafetyDecision> {
  return Object.freeze({
    operational_state: decision.operational_state,
    indexing_posture: decision.indexing_posture,
    policy_fingerprint: decision.policy_fingerprint,
    route_manifest_revision: decision.route_manifest_revision,
    backend_policy_revision: decision.backend_policy_revision,
    sitemap_batch_revision: decision.sitemap_batch_revision,
    sitemap_action: decision.sitemap_action,
    reason: decision.reason,
  })
}

function failedOpenSitemap(reason: GuardedSitemapFailureReason): GuardedSitemapUnavailable {
  const decision: Readonly<LaunchSafetyDecision> = Object.freeze({
    operational_state: 'failed-open',
    indexing_posture: 'closed',
    policy_fingerprint: null,
    route_manifest_revision: null,
    backend_policy_revision: null,
    sitemap_batch_revision: null,
    sitemap_action: 'unavailable',
    reason,
  })
  return Object.freeze({
    status: 503,
    body: '',
    contentType: XML_CONTENT_TYPE,
    requestedBatch: null,
    failureReason: reason,
    decision,
  })
}

export function validateSitemapQuery(
  document: RootSitemapDocument,
  url: URL,
): { readonly requestedBatch: string | null } {
  if (
    !(url instanceof URL)
    || !ROOT_SITEMAP_DOCUMENTS.has(document)
    || url.pathname !== `/${document}`
    || url.hash !== ''
    || url.href.endsWith('#')
  ) {
    throw new GuardedSitemapFailure('sitemap-batch-unavailable')
  }

  if (document === 'sitemap-index.xml') {
    if (url.search !== '') throw new GuardedSitemapFailure('sitemap-batch-unavailable')
    return Object.freeze({ requestedBatch: null })
  }

  const match = PINNED_QUERY_PATTERN.exec(url.search)
  if (!match?.[1]) throw new GuardedSitemapFailure('sitemap-batch-unavailable')
  return Object.freeze({ requestedBatch: match[1] })
}

function normalizeLaunchHeaders(value: unknown): Record<string, string> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new GuardedSitemapFailure('sitemap-evidence-mismatch')
  }

  const normalized: Record<string, string> = Object.create(null) as Record<string, string>
  for (const [name, headerValue] of Object.entries(value)) {
    const lowerName = name.toLowerCase()
    if (!LAUNCH_HEADER_NAMES.has(lowerName)) continue
    if (
      name.trim() !== name
      || typeof headerValue !== 'string'
      || Object.prototype.hasOwnProperty.call(normalized, lowerName)
    ) {
      throw new GuardedSitemapFailure('sitemap-evidence-mismatch')
    }
    normalized[lowerName] = headerValue
  }
  return normalized
}

function validateAllLaunchEvidence(
  rawHeaders: unknown,
  decision: Readonly<LaunchSafetyDecision>,
  requestedBatch: string | null,
): string {
  const headers = normalizeLaunchHeaders(rawHeaders)
  const mismatch = (): never => {
    throw new GuardedSitemapFailure('sitemap-evidence-mismatch')
  }

  if (
    typeof decision.policy_fingerprint !== 'string'
    || !SHA256_PATTERN.test(decision.policy_fingerprint)
    || headers['x-launch-policy-fingerprint'] !== decision.policy_fingerprint
  ) mismatch()
  if (
    typeof decision.route_manifest_revision !== 'string'
    || !decision.route_manifest_revision
    || headers['x-launch-route-manifest-revision'] !== decision.route_manifest_revision
  ) mismatch()
  if (
    typeof decision.backend_policy_revision !== 'string'
    || !decision.backend_policy_revision
    || headers['x-launch-backend-policy-revision'] !== decision.backend_policy_revision
  ) mismatch()

  const servedBatch = headers['x-launch-sitemap-batch-revision']
  if (typeof servedBatch !== 'string' || !SHA256_PATTERN.test(servedBatch)) mismatch()

  const hasRequestedBatchEcho = Object.prototype.hasOwnProperty.call(
    headers,
    'x-launch-sitemap-requested-batch',
  )
  if (requestedBatch === null) {
    if (hasRequestedBatchEcho) mismatch()
  } else if (
    !hasRequestedBatchEcho
    || headers['x-launch-sitemap-requested-batch'] !== requestedBatch
    || servedBatch !== requestedBatch
  ) mismatch()

  return servedBatch
}

function normalizePrivateApiBase(value: unknown): string {
  if (typeof value !== 'string' || !value || value.trim() !== value) {
    throw new TypeError('Private runtime apiBase is invalid')
  }

  let parsed: URL
  try {
    parsed = new URL(value)
  } catch {
    throw new TypeError('Private runtime apiBase is invalid')
  }
  if (
    (parsed.protocol !== 'http:' && parsed.protocol !== 'https:')
    || parsed.username !== ''
    || parsed.password !== ''
    || parsed.pathname !== '/'
    || parsed.search !== ''
    || parsed.hash !== ''
    || parsed.origin === 'null'
  ) {
    throw new TypeError('Private runtime apiBase is invalid')
  }
  return parsed.origin
}

function internalDocumentQuery(document: RootSitemapDocument, requestedBatch: string | null): string {
  if (!ROOT_SITEMAP_DOCUMENTS.has(document)) {
    throw new TypeError('Internal sitemap document is invalid')
  }
  if (document === 'sitemap-index.xml') {
    if (requestedBatch !== null) throw new TypeError('Internal sitemap query is invalid')
    return ''
  }
  if (typeof requestedBatch !== 'string' || !SHA256_PATTERN.test(requestedBatch)) {
    throw new TypeError('Internal sitemap query is invalid')
  }
  return `?batch=${requestedBatch}`
}

export function createInternalSitemapFetcher(
  event: H3Event,
  fetchRawHttp: InternalRawHttpFetcher = defaultRawHttpFetcher,
): InternalRawFetcher {
  return async (document, requestedBatch) => {
    const apiBase = normalizePrivateApiBase(useRuntimeConfig(event).apiBase)
    const query = internalDocumentQuery(document, requestedBatch)
    const response = await fetchRawHttp(
      `${apiBase}/_internal/launch-sitemaps/${document}${query}`,
      {
        method: 'GET',
        responseType: 'text',
        redirect: 'manual',
        ignoreResponseError: true,
        retry: false,
        headers: { accept: 'application/xml' },
      },
    )
    const headers: Record<string, string> = Object.create(null) as Record<string, string>
    response.headers.forEach((value, key) => {
      const lowerKey = key.toLowerCase()
      headers[lowerKey] = Object.prototype.hasOwnProperty.call(headers, lowerKey)
        ? `${headers[lowerKey]}, ${value}`
        : value
    })
    return Object.freeze({
      status: response.status,
      body: typeof response._data === 'string' ? response._data : '',
      headers: Object.freeze(headers),
    })
  }
}

export async function proxyGuardedSitemap(input: GuardedSitemapInput): Promise<GuardedSitemapResult> {
  try {
    const decision = snapshotDecision(input.decision)
    if (decision.sitemap_action !== 'guarded-proxy') {
      return failedOpenSitemap('sitemap-batch-unavailable')
    }

    const query = validateSitemapQuery(input.document, input.url)
    let upstream: InternalRawSitemapResponse
    try {
      upstream = await input.fetchRaw(input.document, query.requestedBatch)
    } catch {
      throw new GuardedSitemapFailure('sitemap-batch-unavailable')
    }
    if (upstream.status !== 200) {
      throw new GuardedSitemapFailure('sitemap-batch-unavailable')
    }

    const servedBatch = validateAllLaunchEvidence(upstream.headers, decision, query.requestedBatch)
    const refinedDecision = Object.freeze({ ...decision, sitemap_batch_revision: servedBatch })
    return Object.freeze({
      status: 200,
      body: upstream.body,
      contentType: XML_CONTENT_TYPE,
      requestedBatch: query.requestedBatch,
      failureReason: null,
      decision: refinedDecision,
    })
  } catch (error: unknown) {
    const reason = error instanceof GuardedSitemapFailure
      ? error.reason
      : 'sitemap-batch-unavailable'
    return failedOpenSitemap(reason)
  }
}

export async function fetchAndValidateActiveSitemapIndex(
  event: H3Event,
  decision: Readonly<LaunchSafetyDecision>,
): Promise<GuardedSitemapResult> {
  return proxyGuardedSitemap({
    event,
    document: 'sitemap-index.xml',
    decision,
    url: new URL('/sitemap-index.xml', 'http://internal'),
    fetchRaw: createInternalSitemapFetcher(event),
  })
}
