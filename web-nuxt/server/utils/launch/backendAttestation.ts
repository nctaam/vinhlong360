import type { BackendAttestation } from '../../../types/launch'
import { ATTESTATION_TIMEOUT_MS, withRequestDeadline } from '../../../utils/requestDeadline'

const ATTESTATION_PATH = '/_internal/launch-policy-attestation'
const FINGERPRINT_PATTERN = /^[0-9a-f]{64}$/u
const ROUTE_REVISION = 'launch-indexing-policy-v1'
const BACKEND_POLICY_REVISION = 'index-policy-v1'
const DEFAULT_ATTESTATION_CACHE_TTL_MS = 5_000
const MAX_ATTESTATION_CACHE_ENTRIES = 8

interface CachedAttestationEntry {
  readonly value: Readonly<BackendAttestation>
  readonly expiresAt: number
}

const attestationCache = new Map<string, CachedAttestationEntry>()
const inflightAttestations = new Map<string, Promise<BackendAttestation>>()
const verifiedAttestations = new WeakSet<BackendAttestation>()

export function clearBackendAttestationCache(): void {
  attestationCache.clear()
  inflightAttestations.clear()
}

export class BackendAttestationMismatchError extends Error {
  constructor(message = 'Backend launch policy attestation mismatch') {
    super(message)
    this.name = 'BackendAttestationMismatchError'
  }
}

export class BackendAttestationUnavailableError extends Error {
  constructor(message = 'Backend launch policy attestation unavailable') {
    super(message)
    this.name = 'BackendAttestationUnavailableError'
  }
}

type AttestationRecord = Record<string, unknown>

function isPlainRecord(value: unknown): value is AttestationRecord {
  return value !== null
    && typeof value === 'object'
    && !Array.isArray(value)
    && Object.getPrototypeOf(value) === Object.prototype
}

function hasExactKeys(value: AttestationRecord): boolean {
  const keys = Reflect.ownKeys(value)
  if (keys.length !== 3 || keys.some(key => typeof key !== 'string')) return false
  const names = (keys as string[]).sort()
  if (
    names[0] !== 'backend_policy_revision'
    || names[1] !== 'policy_fingerprint'
    || names[2] !== 'route_manifest_revision'
  ) return false
  return names.every((key) => {
    const descriptor = Object.getOwnPropertyDescriptor(value, key)
    return descriptor?.enumerable === true && 'value' in descriptor
  })
}

function validRevision(value: unknown, expected: string): value is string {
  return typeof value === 'string' && value === expected
}

export function parseBackendAttestation(value: unknown): BackendAttestation {
  if (typeof value === 'object' && value !== null && verifiedAttestations.has(value as BackendAttestation)) {
    return value as BackendAttestation
  }
  if (!isPlainRecord(value) || !hasExactKeys(value)) {
    throw new BackendAttestationMismatchError('Backend launch policy attestation shape mismatch')
  }

  const fingerprint = value.policy_fingerprint
  if (typeof fingerprint !== 'string' || !FINGERPRINT_PATTERN.test(fingerprint)) {
    throw new BackendAttestationMismatchError('Backend launch policy fingerprint is invalid')
  }
  if (!validRevision(value.route_manifest_revision, ROUTE_REVISION)) {
    throw new BackendAttestationMismatchError('Backend route manifest revision is stale')
  }
  if (!validRevision(value.backend_policy_revision, BACKEND_POLICY_REVISION)) {
    throw new BackendAttestationMismatchError('Backend policy revision is stale')
  }

  const parsed = Object.freeze({
    policy_fingerprint: fingerprint,
    route_manifest_revision: value.route_manifest_revision,
    backend_policy_revision: value.backend_policy_revision,
  })
  verifiedAttestations.add(parsed)
  return parsed
}

export type BackendAttestationFetcher = (
  request: string,
  options: {
    baseURL: string
    method: 'GET'
    headers: { accept: 'application/json' }
    signal: AbortSignal
  },
) => Promise<unknown>

function defaultFetcher(request: string, options: Parameters<BackendAttestationFetcher>[1]): Promise<unknown> {
  // Nitro's generated route overloads are recursive; keep this internal
  // client on its deliberately narrow transport contract.
  return ($fetch as unknown as BackendAttestationFetcher)(request, options)
}

export async function fetchBackendAttestation(input: {
  baseURL: string
  fetcher?: BackendAttestationFetcher
  cacheTtlMs?: number
}): Promise<BackendAttestation> {
  const baseURL = typeof input.baseURL === 'string' ? input.baseURL.trim().replace(/\/+$/u, '') : ''
  if (!baseURL) throw new BackendAttestationUnavailableError()

  const ttlMs = input.cacheTtlMs ?? (input.fetcher ? 0 : DEFAULT_ATTESTATION_CACHE_TTL_MS)
  const now = Date.now()
  if (ttlMs > 0) {
    const cached = attestationCache.get(baseURL)
    if (cached && cached.expiresAt > now) {
      return cached.value
    }
    attestationCache.delete(baseURL)
    const existingInflight = inflightAttestations.get(baseURL)
    if (existingInflight) return existingInflight
  }

  const execute = async (): Promise<BackendAttestation> => {
    try {
      const payload = await withRequestDeadline(ATTESTATION_TIMEOUT_MS, signal => (
        input.fetcher ?? defaultFetcher
      )(ATTESTATION_PATH, {
        baseURL,
        method: 'GET',
        headers: { accept: 'application/json' },
        signal,
      }))
      const parsed = parseBackendAttestation(payload)
      if (ttlMs > 0) {
        if (attestationCache.size >= MAX_ATTESTATION_CACHE_ENTRIES) {
          const oldestKey = attestationCache.keys().next().value
          if (oldestKey !== undefined) attestationCache.delete(oldestKey)
        }
        attestationCache.set(baseURL, { value: parsed, expiresAt: Date.now() + ttlMs })
      }
      return parsed
    } catch (error: unknown) {
      attestationCache.delete(baseURL)
      if (error instanceof BackendAttestationMismatchError) throw error
      if (error instanceof BackendAttestationUnavailableError) throw error
      const message = error instanceof Error ? error.message : 'request failed'
      throw new BackendAttestationUnavailableError(`Backend launch policy attestation unavailable: ${message}`)
    } finally {
      if (ttlMs > 0) inflightAttestations.delete(baseURL)
    }
  }

  const promise = execute()
  if (ttlMs > 0) inflightAttestations.set(baseURL, promise)
  return promise
}
