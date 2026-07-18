// @vitest-environment node

import { describe, expect, it } from 'vitest'
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

import { buildPolicyFingerprint } from '../server/utils/launch/launchEvidence'
import {
  CACHE_PURGE_DECLARATION,
  validateReadinessManifest,
  validateReadinessManifestEvidence,
  type LaunchReadinessManifest,
} from '../server/utils/launch/readinessManifest'

const routeDigest = '1'.repeat(64)
const disclosureDigest = '2'.repeat(64)

type GeneratorModule = {
  auditCompiledRouteRules: (rules: Record<string, Record<string, unknown>>) => string[]
  auditPublicPrerenderFiles: (files: string[]) => string[]
  buildGeneratorPolicyFingerprint: (input: {
    routeRevision: string
    routeDigest: string
    disclosureRevision: string
    disclosureDigest: string
  }) => string
  readCompiledRouteRules: (outputRoot: string) => Record<string, Record<string, unknown>>
  readEmbeddedArtifactSources: (outputRoot: string, expected: {
    routeSource: Buffer
    disclosureSource: Buffer
  }) => { routeDigest: string; disclosureDigest: string }
  verifyServiceWorkerActivation: (source: string) => Promise<Record<string, unknown>>
}

async function loadGenerator(): Promise<GeneratorModule> {
  return import(pathToFileURL(resolve(process.cwd(), 'scripts/generate-launch-readiness-manifest.mjs')).href) as Promise<GeneratorModule>
}

function withOutputFixture(sources: string[], check: (outputRoot: string) => void): void {
  const outputRoot = mkdtempSync(resolve(tmpdir(), 'vl360-readiness-'))
  const chunksRoot = resolve(outputRoot, 'server/chunks')
  mkdirSync(chunksRoot, { recursive: true })
  try {
    sources.forEach((source, index) => writeFileSync(resolve(chunksRoot, `${index}.mjs`), source, 'utf8'))
    check(outputRoot)
  } finally {
    rmSync(outputRoot, { recursive: true, force: true })
  }
}

const validManifest: LaunchReadinessManifest = {
  schema_version: 1,
  build_revision: 'source-revision',
  artifacts: {
    route_manifest: {
      revision: 'launch-indexing-policy-v1',
      sha256: routeDigest,
    },
    ai_disclosure: {
      revision: 'ai-disclosure-v1',
      sha256: disclosureDigest,
    },
    policy_fingerprint: buildPolicyFingerprint({
      routeRevision: 'launch-indexing-policy-v1',
      routeDigest,
      disclosureRevision: 'ai-disclosure-v1',
      disclosureDigest,
    }),
  },
  policy_route_classes: ['public-html', 'public-api', 'root-seo', 'internal-readiness'],
  compiled_cache_rules: [],
  public_prerender_files: [],
  service_worker: {
    version: 'vl360-launch-v1',
    rule_digest: '3'.repeat(64),
    cache_purge: { ...CACHE_PURGE_DECLARATION },
  },
}

function mutateCachePurge(
  manifest: LaunchReadinessManifest,
  mutation: 'missing' | 'wrong-retained-cache' | 'unverified',
): Record<string, unknown> {
  const serviceWorker = { ...manifest.service_worker }
  if (mutation === 'missing') {
    const { cache_purge: _cachePurge, ...withoutCachePurge } = serviceWorker
    return { ...manifest, service_worker: withoutCachePurge }
  }

  const cachePurge: Record<string, unknown> = { ...serviceWorker.cache_purge }
  if (mutation === 'wrong-retained-cache') {
    cachePurge.retained_cache_names = ['legacy-html-cache']
  } else {
    cachePurge.activation_verified = false
  }
  return { ...manifest, service_worker: { ...serviceWorker, cache_purge: cachePurge } }
}

describe('launch readiness manifest', () => {
  it('accepts the exact schema and canonical artifact evidence', () => {
    expect(validateReadinessManifest(validManifest)).toMatchObject({
      schema_version: 1,
      artifacts: {
        route_manifest: { revision: 'launch-indexing-policy-v1', sha256: expect.stringMatching(/^[a-f0-9]{64}$/) },
        ai_disclosure: { revision: 'ai-disclosure-v1', sha256: expect.stringMatching(/^[a-f0-9]{64}$/) },
      },
    })
  })

  it('rejects symbol and accessor keys instead of evaluating them', () => {
    const symbolCandidate = { ...validManifest, [Symbol('hidden')]: true }
    expect(() => validateReadinessManifest(symbolCandidate)).toThrow(/root keys mismatch/i)

    const accessorCandidate = { ...validManifest }
    Object.defineProperty(accessorCandidate, 'build_revision', {
      enumerable: true,
      get: () => 'source-revision',
    })
    expect(() => validateReadinessManifest(accessorCandidate)).toThrow(/root keys mismatch/i)
  })

  it('rejects a policy-bearing prerender artifact', () => {
    expect(() => validateReadinessManifest({
      ...validManifest,
      public_prerender_files: ['public/index.html'],
    })).toThrow(/policy-bearing prerender/i)
  })

  it('requires the final service-worker digest', () => {
    expect(validateReadinessManifest(validManifest).service_worker.rule_digest).toMatch(/^[a-f0-9]{64}$/)
    expect(() => validateReadinessManifest({
      ...validManifest,
      service_worker: { ...validManifest.service_worker, rule_digest: 'not-a-digest' },
    })).toThrow(/service-worker.*digest/i)
  })

  it('requires both artifact revisions as well as digests', () => {
    expect(validateReadinessManifest(validManifest).artifacts).toMatchObject({
      route_manifest: { revision: 'launch-indexing-policy-v1', sha256: expect.stringMatching(/^[a-f0-9]{64}$/) },
      ai_disclosure: { revision: 'ai-disclosure-v1', sha256: expect.stringMatching(/^[a-f0-9]{64}$/) },
    })
    expect(() => validateReadinessManifest({
      ...validManifest,
      artifacts: {
        ...validManifest.artifacts,
        route_manifest: { ...validManifest.artifacts.route_manifest, revision: '' },
      },
    })).toThrow(/artifact revision/i)
  })

  it('rejects a self-consistent manifest whose evidence is stale against the final build', () => {
    const staleRouteDigest = '4'.repeat(64)
    const staleManifest: LaunchReadinessManifest = {
      ...validManifest,
      artifacts: {
        ...validManifest.artifacts,
        route_manifest: { revision: 'launch-indexing-policy-v1', sha256: staleRouteDigest },
        policy_fingerprint: buildPolicyFingerprint({
          routeRevision: 'launch-indexing-policy-v1',
          routeDigest: staleRouteDigest,
          disclosureRevision: 'ai-disclosure-v1',
          disclosureDigest,
        }),
      },
    }
    expect(() => validateReadinessManifestEvidence(staleManifest, {
      routeDigest,
      disclosureDigest,
      serviceWorkerDigest: '3'.repeat(64),
    })).toThrow(/stale route artifact/i)
  })

  it.each(['missing', 'wrong-retained-cache', 'unverified'] as const)(
    'rejects %s cache-purge declaration',
    (mutation) => {
      expect(() => validateReadinessManifest(mutateCachePurge(validManifest, mutation)))
        .toThrow(/cache purge/i)
    },
  )

  it('keeps the Node generator fingerprint in exact Task 9/20 parity', async () => {
    const generator = await loadGenerator()
    const input = {
      routeRevision: 'launch-indexing-policy-v1',
      routeDigest,
      disclosureRevision: 'ai-disclosure-v1',
      disclosureDigest,
    }
    expect(generator.buildGeneratorPolicyFingerprint(input)).toBe(buildPolicyFingerprint(input))
  })

  it('audits compiled cache rules and compressed public HTML fail closed', async () => {
    const generator = await loadGenerator()
    expect(generator.auditCompiledRouteRules({
      '/__nuxt_error': { cache: false },
      '/_nuxt/**': { headers: { 'cache-control': 'public, max-age=31536000, immutable' } },
      '/**': { headers: { 'X-Content-Type-Options': 'nosniff' } },
    })).toEqual([])
    expect(() => generator.auditCompiledRouteRules({ '/dia-diem/**': { swr: 60 } }))
      .toThrow(/compiled cache rule/i)
    expect(() => generator.auditPublicPrerenderFiles(['public/index.html.gz']))
      .toThrow(/policy-bearing prerender/i)
  })

  it('requires exactly one compiled Nitro inline-config marker', async () => {
    const generator = await loadGenerator()
    const configSource = `const _inlineRuntimeConfig = ${JSON.stringify({ nitro: { routeRules: {} } })};`
    withOutputFixture(['export default {}'], outputRoot => {
      expect(() => generator.readCompiledRouteRules(outputRoot)).toThrow(/exactly one compiled Nitro config/i)
    })
    withOutputFixture([`${configSource}\n${configSource}`], outputRoot => {
      expect(() => generator.readCompiledRouteRules(outputRoot)).toThrow(/exactly one compiled Nitro config/i)
    })
  })

  it('rejects built-server artifact bytes that differ from the root artifacts', async () => {
    const generator = await loadGenerator()
    const routeSource = readFileSync(resolve(process.cwd(), '../config/launch-indexing-policy.json'))
    const disclosureSource = readFileSync(resolve(process.cwd(), '../config/ai-disclosure.json'))
    const staleSource = [
      `const disclosureArtifactSource = ${JSON.stringify(disclosureSource.toString('utf8'))};`,
      `const routeArtifactSource = ${JSON.stringify(`${routeSource.toString('utf8')} `)};`,
    ].join('\n')
    withOutputFixture([staleSource], outputRoot => {
      expect(() => generator.readEmbeddedArtifactSources(outputRoot, { routeSource, disclosureSource }))
        .toThrow(/embedded route artifact.*mismatch/i)
    })
  })

  it('executes the final worker activation and reads its exact frozen declaration', async () => {
    const generator = await loadGenerator()
    const source = readFileSync(resolve(process.cwd(), 'public/sw.js'), 'utf8')
    await expect(generator.verifyServiceWorkerActivation(source)).resolves.toMatchObject(CACHE_PURGE_DECLARATION)
  })

  it('runs the readiness generator only after nuxt build', () => {
    const packageJson = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf8')) as {
      scripts?: Record<string, string>
    }
    expect(packageJson.scripts?.build).toBe('nuxt build && node scripts/generate-launch-readiness-manifest.mjs')
  })
})
