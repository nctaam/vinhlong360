import type {
  BackendAttestation,
  LaunchBuildEvidence,
  LaunchSafetyDecision,
} from '../../../types/launch'
import { INDEX_POLICY_REVISION, buildPolicyFingerprint, isSha256 } from './launchEvidence'
import { BackendAttestationMismatchError, parseBackendAttestation } from './backendAttestation'
import { readLaunchIntent } from './launchIntent'

type AttestationFetcher = () => Promise<BackendAttestation | unknown>

export interface ResolveBaseLaunchSafetyDecisionInput {
  readonly env: NodeJS.ProcessEnv
  readonly build: LaunchBuildEvidence
  readonly fetchAttestation: AttestationFetcher
}

function failedOpen(reason: LaunchSafetyDecision['reason']): LaunchSafetyDecision {
  return {
    operational_state: 'failed-open',
    indexing_posture: 'closed',
    policy_fingerprint: null,
    route_manifest_revision: null,
    backend_policy_revision: null,
    sitemap_batch_revision: null,
    sitemap_action: 'unavailable',
    reason,
  }
}

function closed(reason: LaunchSafetyDecision['reason']): LaunchSafetyDecision {
  return {
    operational_state: 'closed',
    indexing_posture: 'closed',
    policy_fingerprint: null,
    route_manifest_revision: null,
    backend_policy_revision: null,
    sitemap_batch_revision: null,
    sitemap_action: 'closed-empty',
    reason,
  }
}

function validBuildEvidence(build: LaunchBuildEvidence): boolean {
  if (build === null || typeof build !== 'object') return false
  const values = [build.routeRevision, build.disclosureRevision]
  if (values.some(value => typeof value !== 'string' || !value || value.trim() !== value)) return false
  return isSha256(build.routeDigest) && isSha256(build.disclosureDigest)
}

export async function resolveBaseLaunchSafetyDecision({
  env,
  build,
  fetchAttestation,
}: ResolveBaseLaunchSafetyDecisionInput): Promise<LaunchSafetyDecision> {
  const intent = readLaunchIntent(env)
  if (!intent.openIntent) return closed(intent.reason)
  if (!validBuildEvidence(build)) return failedOpen('build-isolation-unsafe')

  let expectedFingerprint: string
  try {
    expectedFingerprint = buildPolicyFingerprint(build)
  } catch {
    return failedOpen('build-isolation-unsafe')
  }

  let attestation: BackendAttestation
  try {
    attestation = parseBackendAttestation(await fetchAttestation())
  } catch (error: unknown) {
    if (error instanceof BackendAttestationMismatchError) return failedOpen('policy-mismatch')
    return failedOpen('policy-attestation-unavailable')
  }

  if (
    attestation.policy_fingerprint !== expectedFingerprint
    || attestation.route_manifest_revision !== build.routeRevision
    || attestation.backend_policy_revision !== INDEX_POLICY_REVISION
  ) {
    return failedOpen('policy-mismatch')
  }

  return {
    operational_state: 'selective-open',
    indexing_posture: 'selective-open',
    policy_fingerprint: expectedFingerprint,
    route_manifest_revision: build.routeRevision,
    backend_policy_revision: INDEX_POLICY_REVISION,
    sitemap_batch_revision: null,
    sitemap_action: 'guarded-proxy',
    reason: 'valid-two-key-unlock',
  }
}
