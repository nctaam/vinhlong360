import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

import disclosureArtifactSource from '#launch-config/ai-disclosure.json?raw'
import routeArtifactSource from '#launch-config/launch-indexing-policy.json?raw'

import { aiDisclosure } from '../../../utils/aiDisclosure'
import { buildPolicyFingerprint } from './launchEvidence'
import { launchRouteManifest } from './launchRouteManifest'

export const READINESS_MANIFEST_SCHEMA_VERSION = 1 as const
export const ROUTE_MANIFEST_REVISION = 'launch-indexing-policy-v1' as const
export const AI_DISCLOSURE_REVISION = 'ai-disclosure-v1' as const
export const SERVICE_WORKER_VERSION = 'vl360-launch-v1' as const

export const POLICY_ROUTE_CLASSES = Object.freeze([
  'public-html',
  'public-api',
  'root-seo',
  'internal-readiness',
] as const)

export const CACHE_PURGE_DECLARATION = Object.freeze({
  revision: 'launch-cache-purge-v1',
  strategy: 'delete-all-except',
  retained_cache_names: Object.freeze(['vl360-launch-v1-assets'] as const),
  forbidden_cache_classes: Object.freeze([
    'navigation',
    'html',
    'root-seo',
    'internal',
    'api',
    'selective-open',
    'failed-open',
  ] as const),
  activation_verified: true,
} as const)

const SHA256_PATTERN = /^[a-f0-9]{64}$/u
const SOURCE_REVISION_PATTERN = /^[a-f0-9]{40}$/u
const POLICY_PRERENDER_PATTERN = /\.html(?:\.(?:br|gz))?$/iu

export type CachePurgeDeclaration = {
  readonly revision: 'launch-cache-purge-v1'
  readonly strategy: 'delete-all-except'
  readonly retained_cache_names: readonly ['vl360-launch-v1-assets']
  readonly forbidden_cache_classes: readonly [
    'navigation',
    'html',
    'root-seo',
    'internal',
    'api',
    'selective-open',
    'failed-open',
  ]
  readonly activation_verified: true
}

export type LaunchReadinessManifest = {
  readonly schema_version: 1
  readonly build_revision: string
  readonly artifacts: {
    readonly route_manifest: { readonly revision: typeof ROUTE_MANIFEST_REVISION; readonly sha256: string }
    readonly ai_disclosure: { readonly revision: typeof AI_DISCLOSURE_REVISION; readonly sha256: string }
    readonly policy_fingerprint: string
  }
  readonly policy_route_classes: readonly [
    'public-html',
    'public-api',
    'root-seo',
    'internal-readiness',
  ]
  readonly compiled_cache_rules: readonly string[]
  readonly public_prerender_files: readonly string[]
  readonly service_worker: {
    readonly version: typeof SERVICE_WORKER_VERSION
    readonly rule_digest: string
    readonly cache_purge: CachePurgeDeclaration
  }
}

export type ReadinessCheck = {
  readonly name: string
  readonly ok: boolean
  readonly reason: string
}

export type ReadinessManifestCheckResult = {
  readonly ok: boolean
  readonly checks: readonly ReadinessCheck[]
  readonly reason: 'manifest-valid' | 'manifest-invalid'
  readonly manifest?: LaunchReadinessManifest
}

export type ReadinessManifestEvidence = {
  readonly routeDigest: string
  readonly disclosureDigest: string
  readonly serviceWorkerDigest: string
}

const EMBEDDED_BUILD_EVIDENCE: Readonly<Omit<ReadinessManifestEvidence, 'serviceWorkerDigest'>> = Object.freeze({
  routeDigest: createHash('sha256').update(routeArtifactSource, 'utf8').digest('hex'),
  disclosureDigest: createHash('sha256').update(disclosureArtifactSource, 'utf8').digest('hex'),
})

if (
  launchRouteManifest.revision !== ROUTE_MANIFEST_REVISION
  || aiDisclosure.revision !== AI_DISCLOSURE_REVISION
) {
  throw new Error('readiness manifest embedded artifact revision mismatch')
}

function plainRecord(value: unknown, label: string): Record<string, unknown> {
  if (
    value === null
    || typeof value !== 'object'
    || Array.isArray(value)
    || Object.getPrototypeOf(value) !== Object.prototype
  ) {
    throw new Error(`readiness manifest ${label} must be a plain JSON object`)
  }
  return value as Record<string, unknown>
}

function exactKeys(value: Record<string, unknown>, expected: readonly string[], label: string): void {
  const actual: string[] = []
  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key)
    if (typeof key !== 'string' || !descriptor?.enumerable || !('value' in descriptor)) {
      throw new Error(`readiness manifest ${label} keys mismatch`)
    }
    actual.push(key)
  }
  actual.sort()
  const sortedExpected = [...expected].sort()
  if (actual.join('\0') !== sortedExpected.join('\0')) {
    throw new Error(`readiness manifest ${label} keys mismatch`)
  }
}

function denseArray(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype) {
    throw new Error(`readiness manifest ${label} must be a plain dense JSON array`)
  }
  const ownKeys = Reflect.ownKeys(value)
  if (ownKeys.length !== value.length + 1 || !ownKeys.includes('length')) {
    throw new Error(`readiness manifest ${label} must be a plain dense JSON array`)
  }
  for (let index = 0; index < value.length; index += 1) {
    const descriptor = Object.getOwnPropertyDescriptor(value, String(index))
    if (!descriptor?.enumerable || !('value' in descriptor)) {
      throw new Error(`readiness manifest ${label} must be a plain dense JSON array`)
    }
  }
  return value
}

function nonEmptyString(value: unknown, label: string): string {
  if (typeof value !== 'string' || value.length === 0 || value.trim() !== value) {
    throw new Error(`readiness manifest ${label} must be a non-empty canonical string`)
  }
  return value
}

function sha256(value: unknown, label: string): string {
  if (typeof value !== 'string' || !SHA256_PATTERN.test(value)) {
    throw new Error(`readiness manifest ${label} must be a lowercase SHA-256 digest`)
  }
  return value
}

function sourceRevision(value: unknown): string {
  if (typeof value !== 'string' || !SOURCE_REVISION_PATTERN.test(value)) {
    throw new Error('readiness manifest build revision must be a lowercase 40-hex source revision')
  }
  return value
}

function exactStringArray(value: unknown, label: string): string[] {
  return denseArray(value, label).map((entry, index) => nonEmptyString(entry, `${label}[${index}]`))
}

function equalArray(actual: readonly unknown[], expected: readonly unknown[], label: string): void {
  if (actual.length !== expected.length || actual.some((value, index) => value !== expected[index])) {
    throw new Error(`readiness manifest ${label} mismatch`)
  }
}

function parseCachePurge(value: unknown): CachePurgeDeclaration {
  const purge = plainRecord(value, 'service_worker.cache_purge')
  exactKeys(purge, [
    'revision',
    'strategy',
    'retained_cache_names',
    'forbidden_cache_classes',
    'activation_verified',
  ], 'service_worker.cache_purge')

  if (purge.revision !== CACHE_PURGE_DECLARATION.revision || purge.strategy !== CACHE_PURGE_DECLARATION.strategy) {
    throw new Error('readiness manifest cache purge declaration mismatch')
  }
  const retained = exactStringArray(purge.retained_cache_names, 'cache purge retained cache names')
  const forbidden = exactStringArray(purge.forbidden_cache_classes, 'cache purge forbidden cache classes')
  equalArray(retained, CACHE_PURGE_DECLARATION.retained_cache_names, 'cache purge retained cache names')
  equalArray(forbidden, CACHE_PURGE_DECLARATION.forbidden_cache_classes, 'cache purge forbidden cache classes')
  if (purge.activation_verified !== true) {
    throw new Error('readiness manifest cache purge activation verification failed')
  }

  return {
    revision: CACHE_PURGE_DECLARATION.revision,
    strategy: CACHE_PURGE_DECLARATION.strategy,
    retained_cache_names: ['vl360-launch-v1-assets'],
    forbidden_cache_classes: [...CACHE_PURGE_DECLARATION.forbidden_cache_classes],
    activation_verified: true,
  }
}

export function validateReadinessManifest(value: unknown): LaunchReadinessManifest {
  const root = plainRecord(value, 'root')
  exactKeys(root, [
    'schema_version',
    'build_revision',
    'artifacts',
    'policy_route_classes',
    'compiled_cache_rules',
    'public_prerender_files',
    'service_worker',
  ], 'root')
  if (root.schema_version !== READINESS_MANIFEST_SCHEMA_VERSION) {
    throw new Error('readiness manifest schema version mismatch')
  }

  const buildRevision = sourceRevision(root.build_revision)
  const artifacts = plainRecord(root.artifacts, 'artifacts')
  exactKeys(artifacts, ['route_manifest', 'ai_disclosure', 'policy_fingerprint'], 'artifacts')
  const routeManifest = plainRecord(artifacts.route_manifest, 'route manifest artifact')
  const aiDisclosure = plainRecord(artifacts.ai_disclosure, 'AI disclosure artifact')
  exactKeys(routeManifest, ['revision', 'sha256'], 'route manifest artifact')
  exactKeys(aiDisclosure, ['revision', 'sha256'], 'AI disclosure artifact')
  if (routeManifest.revision !== ROUTE_MANIFEST_REVISION || typeof routeManifest.revision !== 'string') {
    throw new Error('readiness manifest artifact revision mismatch')
  }
  if (aiDisclosure.revision !== AI_DISCLOSURE_REVISION || typeof aiDisclosure.revision !== 'string') {
    throw new Error('readiness manifest artifact revision mismatch')
  }
  const routeDigest = sha256(routeManifest.sha256, 'route manifest artifact sha256')
  const disclosureDigest = sha256(aiDisclosure.sha256, 'AI disclosure artifact sha256')
  const policyFingerprint = sha256(artifacts.policy_fingerprint, 'policy fingerprint')
  const expectedFingerprint = buildPolicyFingerprint({
    routeRevision: ROUTE_MANIFEST_REVISION,
    routeDigest,
    disclosureRevision: AI_DISCLOSURE_REVISION,
    disclosureDigest,
  })
  if (policyFingerprint !== expectedFingerprint) {
    throw new Error('readiness manifest policy fingerprint mismatch')
  }

  const routeClasses = exactStringArray(root.policy_route_classes, 'policy route classes')
  equalArray(routeClasses, POLICY_ROUTE_CLASSES, 'policy route classes')

  const compiledCacheRules = exactStringArray(root.compiled_cache_rules, 'compiled cache rules')
  if (compiledCacheRules.length > 0) {
    throw new Error('readiness manifest compiled cache rules are unsafe')
  }

  const publicPrerenderFiles = exactStringArray(root.public_prerender_files, 'public prerender files')
  const policyPrerender = publicPrerenderFiles.filter(file => POLICY_PRERENDER_PATTERN.test(file))
  if (policyPrerender.length > 0) {
    throw new Error(`readiness manifest policy-bearing prerender artifact: ${policyPrerender.join(', ')}`)
  }

  const serviceWorker = plainRecord(root.service_worker, 'service worker')
  if (!Object.hasOwn(serviceWorker, 'cache_purge')) {
    throw new Error('readiness manifest cache purge declaration missing')
  }
  exactKeys(serviceWorker, ['version', 'rule_digest', 'cache_purge'], 'service worker')
  if (serviceWorker.version !== SERVICE_WORKER_VERSION) {
    throw new Error('readiness manifest service-worker version mismatch')
  }
  const ruleDigest = sha256(serviceWorker.rule_digest, 'service-worker rule digest')
  const cachePurge = parseCachePurge(serviceWorker.cache_purge)

  return deepFreeze({
    schema_version: READINESS_MANIFEST_SCHEMA_VERSION,
    build_revision: buildRevision,
    artifacts: {
      route_manifest: { revision: ROUTE_MANIFEST_REVISION, sha256: routeDigest },
      ai_disclosure: { revision: AI_DISCLOSURE_REVISION, sha256: disclosureDigest },
      policy_fingerprint: policyFingerprint,
    },
    policy_route_classes: [...POLICY_ROUTE_CLASSES],
    compiled_cache_rules: compiledCacheRules,
    public_prerender_files: publicPrerenderFiles,
    service_worker: {
      version: SERVICE_WORKER_VERSION,
      rule_digest: ruleDigest,
      cache_purge: cachePurge,
    },
  })
}

export function inspectReadinessManifest(value: unknown): ReadinessManifestCheckResult {
  try {
    const manifest = validateReadinessManifest(value)
    return {
      ok: true,
      reason: 'manifest-valid',
      checks: Object.freeze([
        { name: 'manifest-schema', ok: true, reason: 'manifest-valid' },
        { name: 'artifact-evidence', ok: true, reason: 'artifact-evidence-valid' },
        { name: 'compiled-cache-rules', ok: true, reason: 'compiled-cache-rules-safe' },
        { name: 'public-prerender', ok: true, reason: 'public-prerender-safe' },
        { name: 'service-worker-cache-purge', ok: true, reason: 'cache-purge-verified' },
      ]),
      manifest,
    }
  } catch {
    return {
      ok: false,
      reason: 'manifest-invalid',
      checks: Object.freeze([{ name: 'manifest', ok: false, reason: 'manifest-invalid' }]),
    }
  }
}

export function validateReadinessManifestEvidence(
  value: unknown,
  evidence: ReadinessManifestEvidence,
): LaunchReadinessManifest {
  const manifest = validateReadinessManifest(value)
  const routeDigest = sha256(evidence.routeDigest, 'expected route artifact sha256')
  const disclosureDigest = sha256(evidence.disclosureDigest, 'expected AI disclosure artifact sha256')
  const serviceWorkerDigest = sha256(evidence.serviceWorkerDigest, 'expected service-worker rule digest')
  if (manifest.artifacts.route_manifest.sha256 !== routeDigest) {
    throw new Error('readiness manifest stale route artifact evidence')
  }
  if (manifest.artifacts.ai_disclosure.sha256 !== disclosureDigest) {
    throw new Error('readiness manifest stale AI disclosure artifact evidence')
  }
  if (manifest.service_worker.rule_digest !== serviceWorkerDigest) {
    throw new Error('readiness manifest stale service-worker evidence')
  }
  return manifest
}

export function loadReadinessManifest(
  manifestPath = resolve(process.cwd(), '.output/server/launch-readiness-manifest.json'),
): LaunchReadinessManifest {
  let raw: string
  try {
    raw = readFileSync(manifestPath, 'utf8')
  } catch {
    throw new Error('readiness manifest missing')
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    throw new Error('readiness manifest corrupt')
  }
  let serviceWorkerSource: Buffer
  try {
    serviceWorkerSource = readFileSync(resolve(dirname(manifestPath), '../public/sw.js'))
  } catch {
    throw new Error('readiness manifest final service-worker source missing')
  }
  return validateReadinessManifestEvidence(parsed, {
    ...EMBEDDED_BUILD_EVIDENCE,
    serviceWorkerDigest: createHash('sha256').update(serviceWorkerSource).digest('hex'),
  })
}

function deepFreeze<T>(value: T): T {
  if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value)
    for (const child of Object.values(value as Record<string, unknown>)) deepFreeze(child)
  }
  return value
}
