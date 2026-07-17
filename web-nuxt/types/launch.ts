export type OperationalState = 'closed' | 'selective-open' | 'failed-open'

export type IndexingPosture = 'closed' | 'selective-open'

export type SitemapAction = 'closed-empty' | 'guarded-proxy' | 'unavailable'

export type LaunchSafetyReason =
  | 'closed-default'
  | 'valid-two-key-unlock'
  | 'invalid-configuration'
  | 'owner-approval-missing'
  | 'policy-attestation-unavailable'
  | 'policy-mismatch'
  | 'build-isolation-unsafe'
  | 'entity-policy-unavailable'
  | 'entity-policy-mismatch'
  | 'sitemap-batch-unavailable'
  | 'sitemap-evidence-mismatch'

export interface LaunchSafetyDecision {
  readonly operational_state: OperationalState
  readonly indexing_posture: IndexingPosture
  readonly policy_fingerprint: string | null
  readonly route_manifest_revision: string | null
  readonly backend_policy_revision: string | null
  readonly sitemap_batch_revision: string | null
  readonly sitemap_action: SitemapAction
  readonly reason: LaunchSafetyReason
}

export interface LaunchPageDecision extends LaunchSafetyDecision {
  readonly robots: 'index, follow' | 'noindex, follow'
  readonly sitemapDiscovery: boolean
}

export interface LaunchBuildEvidence {
  readonly routeRevision: string
  readonly routeDigest: string
  readonly disclosureRevision: string
  readonly disclosureDigest: string
}

export interface BackendAttestation {
  readonly policy_fingerprint: string
  readonly route_manifest_revision: string
  readonly backend_policy_revision: string
}
