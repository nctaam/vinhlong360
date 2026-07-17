// @vitest-environment node

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi } from 'vitest'

import {
  CACHE_ISOLATION_REVISION,
  INDEX_POLICY_REVISION,
  RESPONSE_MATRIX_REVISION,
  SITEMAP_PROTOCOL_REVISION,
  buildPolicyFingerprint,
} from '../server/utils/launch/launchEvidence'
import { resolveBaseLaunchSafetyDecision } from '../server/utils/launch/launchSafetyDecision'
import { readLaunchIntent } from '../server/utils/launch/launchIntent'
import type { BackendAttestation, LaunchBuildEvidence } from '../types/launch'

const fixture = JSON.parse(
  readFileSync(resolve(process.cwd(), '../../tests/fixtures/launch-policy-fingerprint.json'), 'utf8'),
) as {
  inputs: {
    route_revision: string
    route_digest: string
    disclosure_revision: string
    disclosure_digest: string
  }
  expected_sha256: string
}

const matchingBuild: LaunchBuildEvidence = {
  routeRevision: fixture.inputs.route_revision,
  routeDigest: fixture.inputs.route_digest,
  disclosureRevision: fixture.inputs.disclosure_revision,
  disclosureDigest: fixture.inputs.disclosure_digest,
}

const matchingAttestation: BackendAttestation = {
  policy_fingerprint: fixture.expected_sha256,
  route_manifest_revision: fixture.inputs.route_revision,
  backend_policy_revision: INDEX_POLICY_REVISION,
}

describe('launch policy fingerprint', () => {
  it('matches the canonical Python fingerprint fixture', () => {
    expect(buildPolicyFingerprint({
      routeRevision: fixture.inputs.route_revision,
      routeDigest: fixture.inputs.route_digest,
      disclosureRevision: fixture.inputs.disclosure_revision,
      disclosureDigest: fixture.inputs.disclosure_digest,
    })).toBe(fixture.expected_sha256)
  })

  it.each([
    ['route revision', { routeRevision: 'launch-indexing-policy-v2' }],
    ['route digest', { routeDigest: '3'.repeat(64) }],
    ['disclosure revision', { disclosureRevision: 'ai-disclosure-v2' }],
    ['disclosure digest', { disclosureDigest: '4'.repeat(64) }],
  ])('changes when the %s changes', (_label, mutation) => {
    expect(buildPolicyFingerprint({ ...matchingBuild, ...mutation })).not.toBe(fixture.expected_sha256)
  })

  it.each([
    ['index policy', { indexPolicy: 'index-policy-v2' }],
    ['response matrix', { responseMatrix: 'launch-safety-matrix-v2' }],
    ['cache isolation', { cacheIsolation: 'launch-cache-isolation-v2' }],
    ['sitemap protocol', { sitemapProtocol: 'pinned-sitemap-bundle-v2' }],
  ])('changes when the %s semantic revision changes', (_label, mutation) => {
    expect(buildPolicyFingerprint(matchingBuild, mutation)).not.toBe(fixture.expected_sha256)
  })
})

describe('readLaunchIntent', () => {
  it.each([
    [{}, false, 'closed-default'],
    [{ LAUNCH_INDEXING_MODE: 'selective-open' }, false, 'owner-approval-missing'],
    [{ LAUNCH_INDEXING_OWNER_APPROVED: 'true' }, false, 'invalid-configuration'],
    [{ LAUNCH_INDEXING_MODE: ' selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' }, false, 'invalid-configuration'],
    [{ LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'TRUE' }, false, 'owner-approval-missing'],
    [{ LAUNCH_INDEXING_MODE: 'open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' }, false, 'invalid-configuration'],
    [{ LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: '1' }, false, 'owner-approval-missing'],
    [{ LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' }, true, 'valid-two-key-unlock'],
  ] as const)('enforces exact two-key intent: %j', (env, openIntent, reason) => {
    expect(readLaunchIntent(env)).toEqual({ openIntent, reason })
  })
})

describe('resolveBaseLaunchSafetyDecision', () => {
  it.each([
    [{}, 'closed', 'closed-default'],
    [{ LAUNCH_INDEXING_MODE: 'selective-open' }, 'closed', 'owner-approval-missing'],
    [{ LAUNCH_INDEXING_OWNER_APPROVED: 'true' }, 'closed', 'invalid-configuration'],
    [{ LAUNCH_INDEXING_MODE: ' selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' }, 'closed', 'invalid-configuration'],
    [{ LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'TRUE' }, 'closed', 'owner-approval-missing'],
    [{ LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' }, 'selective-open', 'valid-two-key-unlock'],
  ] as const)('enforces exact two-key decision: %j', async (env, state, reason) => {
    const fetchAttestation = vi.fn().mockResolvedValue(matchingAttestation)
    const decision = await resolveBaseLaunchSafetyDecision({ env, build: matchingBuild, fetchAttestation })

    expect(decision.operational_state).toBe(state)
    expect(decision.reason).toBe(reason)
    if (state === 'closed') expect(fetchAttestation).not.toHaveBeenCalled()
  })

  it('opens only when backend evidence exactly matches all build evidence', async () => {
    const decision = await resolveBaseLaunchSafetyDecision({
      env: { LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' },
      build: matchingBuild,
      fetchAttestation: vi.fn().mockResolvedValue(matchingAttestation),
    })

    expect(decision).toEqual({
      operational_state: 'selective-open',
      indexing_posture: 'selective-open',
      policy_fingerprint: fixture.expected_sha256,
      route_manifest_revision: fixture.inputs.route_revision,
      backend_policy_revision: INDEX_POLICY_REVISION,
      sitemap_batch_revision: null,
      sitemap_action: 'guarded-proxy',
      reason: 'valid-two-key-unlock',
    })
  })

  it('fails open safely when attestation is unavailable', async () => {
    const decision = await resolveBaseLaunchSafetyDecision({
      env: { LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' },
      build: matchingBuild,
      fetchAttestation: vi.fn().mockRejectedValue(new Error('backend unavailable')),
    })

    expect(decision).toMatchObject({
      operational_state: 'failed-open',
      indexing_posture: 'closed',
      sitemap_action: 'unavailable',
      reason: 'policy-attestation-unavailable',
      policy_fingerprint: null,
      route_manifest_revision: null,
      backend_policy_revision: null,
      sitemap_batch_revision: null,
    })
  })

  it('fails open safely when attestation is stale or malformed', async () => {
    for (const attestation of [
      { ...matchingAttestation, policy_fingerprint: 'f'.repeat(64) },
      { ...matchingAttestation, route_manifest_revision: 'launch-indexing-policy-v0' },
      { ...matchingAttestation, backend_policy_revision: 'index-policy-v0' },
      { ...matchingAttestation, policy_fingerprint: 'not-a-digest' },
    ]) {
      const decision = await resolveBaseLaunchSafetyDecision({
        env: { LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' },
        build: matchingBuild,
        fetchAttestation: vi.fn().mockResolvedValue(attestation),
      })

      expect(decision).toMatchObject({ operational_state: 'failed-open', reason: 'policy-mismatch' })
    }
  })

  it('fails closed when build artifact evidence is incomplete', async () => {
    const decision = await resolveBaseLaunchSafetyDecision({
      env: { LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' },
      build: { ...matchingBuild, disclosureDigest: '' },
      fetchAttestation: vi.fn().mockResolvedValue(matchingAttestation),
    })

    expect(decision).toMatchObject({ operational_state: 'failed-open', reason: 'build-isolation-unsafe' })
  })
})
