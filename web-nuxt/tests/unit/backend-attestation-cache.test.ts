// @vitest-environment node
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  clearBackendAttestationCache,
  fetchBackendAttestation,
} from '../../server/utils/launch/backendAttestation'

const validPayload = {
  policy_fingerprint: 'a'.repeat(64),
  route_manifest_revision: 'launch-indexing-policy-v1',
  backend_policy_revision: 'index-policy-v1',
}

describe('Wave 16: SSR Parallelism & Backend Attestation TTL Cache', () => {
  beforeEach(() => {
    clearBackendAttestationCache()
    vi.useRealTimers()
  })

  it('caches verified attestation for cacheTtlMs and never caches failures', async () => {
    vi.useFakeTimers()
    const fetcher = vi.fn().mockResolvedValue(validPayload)

    const r1 = await fetchBackendAttestation({
      baseURL: 'http://127.0.0.1:8360',
      fetcher,
      cacheTtlMs: 5_000,
    })
    const r2 = await fetchBackendAttestation({
      baseURL: 'http://127.0.0.1:8360/',
      fetcher,
      cacheTtlMs: 5_000,
    })

    expect(r1).toEqual(validPayload)
    expect(r2).toBe(r1)
    expect(fetcher).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(5_001)
    await fetchBackendAttestation({
      baseURL: 'http://127.0.0.1:8360',
      fetcher,
      cacheTtlMs: 5_000,
    })
    expect(fetcher).toHaveBeenCalledTimes(2)
  })

  it('evicts cached entry and does not cache when fetcher fails', async () => {
    const failingFetcher = vi.fn().mockRejectedValueOnce(new Error('network down')).mockResolvedValueOnce(validPayload)
    await expect(
      fetchBackendAttestation({
        baseURL: 'http://127.0.0.1:8360',
        fetcher: failingFetcher,
        cacheTtlMs: 5_000,
      }),
    ).rejects.toThrow(/unavailable/i)

    const recovered = await fetchBackendAttestation({
      baseURL: 'http://127.0.0.1:8360',
      fetcher: failingFetcher,
      cacheTtlMs: 5_000,
    })
    expect(recovered).toEqual(validPayload)
    expect(failingFetcher).toHaveBeenCalledTimes(2)
  })

  it('parallelizes SSR useAsyncData calls in dia-diem/[id].vue and xa-phuong/[id].vue via Promise.all', () => {
    const entityPage = readFileSync(resolve(process.cwd(), 'pages/dia-diem/[id].vue'), 'utf8')
    const wardPage = readFileSync(resolve(process.cwd(), 'pages/xa-phuong/[id].vue'), 'utf8')

    expect(entityPage).toContain('await Promise.all([')
    expect(wardPage).toContain('await Promise.all([')
  })
})
