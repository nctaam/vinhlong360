// @vitest-environment node

import { describe, expect, it, vi } from 'vitest'

import {
  BackendAttestationMismatchError,
  fetchBackendAttestation,
  parseBackendAttestation,
} from '../server/utils/launch/backendAttestation'

const matching = {
  policy_fingerprint: 'a'.repeat(64),
  route_manifest_revision: 'launch-indexing-policy-v1',
  backend_policy_revision: 'index-policy-v1',
}

describe('backend launch attestation client', () => {
  it('fetches through the private base URL without exposing public runtime config', async () => {
    const fetcher = vi.fn().mockResolvedValue(matching)
    await expect(fetchBackendAttestation({ baseURL: 'http://agent.internal:8360', fetcher }))
      .resolves.toEqual(matching)

    expect(fetcher).toHaveBeenCalledWith('/_internal/launch-policy-attestation', expect.objectContaining({
      baseURL: 'http://agent.internal:8360',
      method: 'GET',
      headers: { accept: 'application/json' },
    }))
  })

  it.each([
    ['missing fingerprint', { route_manifest_revision: matching.route_manifest_revision, backend_policy_revision: matching.backend_policy_revision }],
    ['malformed fingerprint', { ...matching, policy_fingerprint: 'not-a-digest' }],
    ['uppercase fingerprint', { ...matching, policy_fingerprint: 'A'.repeat(64) }],
    ['missing route revision', { policy_fingerprint: matching.policy_fingerprint, backend_policy_revision: matching.backend_policy_revision }],
    ['extra key', { ...matching, extra: true }],
  ])('rejects %s as an attestation mismatch', (_label, value) => {
    expect(() => parseBackendAttestation(value)).toThrow(BackendAttestationMismatchError)
  })

  it('propagates transport and HTTP failures as unavailable errors', async () => {
    await expect(fetchBackendAttestation({
      baseURL: 'http://agent.internal:8360',
      fetcher: vi.fn().mockRejectedValue(new Error('503')),
    })).rejects.toThrow(/unavailable/i)
  })
})
