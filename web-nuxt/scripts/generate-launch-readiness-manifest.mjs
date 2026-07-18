import { spawnSync } from 'node:child_process'
import { createHash, randomUUID } from 'node:crypto'
import {
  existsSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs'
import { basename, dirname, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import vm from 'node:vm'
import {
  parseAiDisclosureArtifact,
  parseLaunchRouteManifestArtifact,
} from '../utils/launchArtifactValidators.mjs'

const ROUTE_MANIFEST_REVISION = 'launch-indexing-policy-v1'
const AI_DISCLOSURE_REVISION = 'ai-disclosure-v1'
const SERVICE_WORKER_VERSION = 'vl360-launch-v1'
const POLICY_ROUTE_CLASSES = Object.freeze([
  'public-html',
  'public-api',
  'root-seo',
  'internal-readiness',
])
const SEMANTIC_REVISIONS = Object.freeze({
  indexPolicy: 'index-policy-v1',
  responseMatrix: 'launch-safety-matrix-v1',
  cacheIsolation: 'launch-cache-isolation-v1',
  sitemapProtocol: 'pinned-sitemap-bundle-v1',
})
const CACHE_PURGE_DECLARATION = deepFreeze({
  revision: 'launch-cache-purge-v1',
  strategy: 'delete-all-except',
  retained_cache_names: ['vl360-launch-v1-assets'],
  forbidden_cache_classes: [
    'navigation',
    'html',
    'root-seo',
    'internal',
    'api',
    'selective-open',
    'failed-open',
  ],
  activation_verified: true,
})
const SHA256_PATTERN = /^[a-f0-9]{64}$/u
const POLICY_PRERENDER_PATTERN = /\.html(?:\.(?:br|gz))?$/iu
const INLINE_CONFIG_MARKER = 'const _inlineRuntimeConfig = '

function sha256(source) {
  return createHash('sha256').update(source).digest('hex')
}

function exactRevision(value, expected, label) {
  if (typeof value !== 'string' || value !== expected) {
    throw new Error(`${label} revision mismatch`)
  }
  return value
}

function exactSha256(value, label) {
  if (typeof value !== 'string' || !SHA256_PATTERN.test(value)) {
    throw new Error(`${label} must be a lowercase SHA-256 digest`)
  }
  return value
}

function plainRecord(value, label) {
  if (
    value === null
    || typeof value !== 'object'
    || Array.isArray(value)
    || Object.getPrototypeOf(value) !== Object.prototype
  ) {
    throw new Error(`${label} must be a plain JSON object`)
  }
  return value
}

function exactString(value, label) {
  if (typeof value !== 'string' || value.length === 0 || value.trim() !== value) {
    throw new Error(`${label} must be a non-empty canonical string`)
  }
  return value
}

export function buildGeneratorPolicyFingerprint(input) {
  const routeRevision = exactString(input?.routeRevision, 'route revision')
  const routeDigest = exactSha256(input?.routeDigest, 'route digest')
  const disclosureRevision = exactString(input?.disclosureRevision, 'disclosure revision')
  const disclosureDigest = exactSha256(input?.disclosureDigest, 'disclosure digest')
  const payload = JSON.stringify({
    cache_isolation: SEMANTIC_REVISIONS.cacheIsolation,
    disclosure_artifact: {
      revision: disclosureRevision,
      sha256: disclosureDigest,
    },
    index_policy: SEMANTIC_REVISIONS.indexPolicy,
    response_matrix: SEMANTIC_REVISIONS.responseMatrix,
    route_artifact: {
      revision: routeRevision,
      sha256: routeDigest,
    },
    sitemap_protocol: SEMANTIC_REVISIONS.sitemapProtocol,
  })
  return sha256(payload)
}

function isReviewedAssetRule(path) {
  return path === '/favicon.svg'
    || path === '/manifest.json'
    || path === '/apple-touch-icon.png'
    || path.startsWith('/_nuxt/')
    || path.startsWith('/_fonts/')
    || path.startsWith('/fonts/')
    || path.startsWith('/icons/')
    || path.startsWith('/img/')
}

function cacheControlHeader(headers) {
  if (headers === undefined) return undefined
  const record = plainRecord(headers, 'compiled route-rule headers')
  const name = Object.keys(record).find(key => key.toLowerCase() === 'cache-control')
  return name === undefined ? undefined : record[name]
}

export function auditCompiledRouteRules(routeRules) {
  const rules = plainRecord(routeRules, 'compiled route rules')
  for (const [path, rawRule] of Object.entries(rules)) {
    const rule = plainRecord(rawRule, `compiled route rule ${path}`)
    for (const key of ['swr', 'isr', 'prerender', 'cache']) {
      if (Object.hasOwn(rule, key) && rule[key] !== false) {
        throw new Error(`compiled cache rule is unsafe: ${path}`)
      }
    }

    const cacheControl = cacheControlHeader(rule.headers)
    if (cacheControl !== undefined) {
      if (
        !isReviewedAssetRule(path)
        || typeof cacheControl !== 'string'
        || !/^public,\s*max-age=\d+,\s*immutable$/iu.test(cacheControl)
      ) {
        throw new Error(`compiled cache rule is unsafe: ${path}`)
      }
    }
  }
  return []
}

export function auditPublicPrerenderFiles(files) {
  if (!Array.isArray(files) || files.some(file => typeof file !== 'string')) {
    throw new Error('public/prerender file inventory is invalid')
  }
  const policyBearing = files.filter(file => POLICY_PRERENDER_PATTERN.test(file))
  if (policyBearing.length > 0) {
    throw new Error(`policy-bearing prerender artifact: ${policyBearing.join(', ')}`)
  }
  return []
}

function normalizeJson(value) {
  return JSON.parse(JSON.stringify(value))
}

function assertExactCachePurgeDeclaration(value) {
  const normalized = normalizeJson(value)
  if (JSON.stringify(normalized) !== JSON.stringify(CACHE_PURGE_DECLARATION)) {
    throw new Error('service-worker cache purge declaration mismatch')
  }
  return normalized
}

export async function verifyServiceWorkerActivation(source) {
  if (typeof source !== 'string' || source.length === 0) {
    throw new Error('final service-worker source is missing')
  }

  const listeners = new Map()
  const cacheNames = new Set([
    ...CACHE_PURGE_DECLARATION.retained_cache_names,
    ...CACHE_PURGE_DECLARATION.forbidden_cache_classes,
    'vl360-v3-html',
    'vl360-v3-assets',
    'vl360-launch-assets-v1',
    'vl360-launch-v0-assets',
    'vl360-selective-open-html',
    'vl360-failed-open-api',
  ])
  let claimCount = 0
  const cachesApi = {
    open: async (name) => {
      cacheNames.add(name)
      return {
        addAll: async () => undefined,
        match: async () => undefined,
        put: async () => undefined,
      }
    },
    keys: async () => [...cacheNames],
    delete: async (name) => cacheNames.delete(name),
  }
  const workerGlobal = {
    location: { origin: 'https://vinhlong360.vn' },
    clients: { claim: () => { claimCount += 1 } },
    skipWaiting: () => undefined,
    addEventListener: (type, listener) => listeners.set(type, listener),
  }

  const instrumentedSource = `${source}\nself.__AUDITED_CACHE_VERSION = CACHE_VERSION\n`
  vm.runInNewContext(instrumentedSource, {
    self: workerGlobal,
    caches: cachesApi,
    fetch: async () => undefined,
    URL,
    Promise,
    console,
  }, { filename: 'public/sw.js' })

  if (workerGlobal.__AUDITED_CACHE_VERSION !== SERVICE_WORKER_VERSION) {
    throw new Error('service-worker version mismatch')
  }

  const declaration = assertExactCachePurgeDeclaration(workerGlobal.CACHE_PURGE_DECLARATION)
  if (
    !Object.isFrozen(workerGlobal.CACHE_PURGE_DECLARATION)
    || !Object.isFrozen(workerGlobal.CACHE_PURGE_DECLARATION.retained_cache_names)
    || !Object.isFrozen(workerGlobal.CACHE_PURGE_DECLARATION.forbidden_cache_classes)
  ) {
    throw new Error('service-worker cache purge declaration must be frozen')
  }

  const activate = listeners.get('activate')
  if (typeof activate !== 'function') {
    throw new Error('service-worker activation handler is missing')
  }
  const waits = []
  activate({ waitUntil: value => waits.push(Promise.resolve(value)) })
  await Promise.all(waits)

  const retained = [...cacheNames].sort()
  const expectedRetained = [...CACHE_PURGE_DECLARATION.retained_cache_names].sort()
  if (JSON.stringify(retained) !== JSON.stringify(expectedRetained) || claimCount !== 1) {
    throw new Error('service-worker cache purge activation verification failed')
  }
  return declaration
}

function listFiles(rootDirectory) {
  if (!existsSync(rootDirectory)) return []
  const files = []
  for (const entry of readdirSync(rootDirectory)) {
    const path = resolve(rootDirectory, entry)
    if (statSync(path).isDirectory()) files.push(...listFiles(path))
    else files.push(path)
  }
  return files
}

function portableRelative(rootDirectory, path) {
  return relative(rootDirectory, path).split(sep).join('/')
}

function markerIndexes(source, marker) {
  const indexes = []
  let offset = 0
  while (offset < source.length) {
    const index = source.indexOf(marker, offset)
    if (index === -1) break
    indexes.push(index)
    offset = index + marker.length
  }
  return indexes
}

function extractJsonObject(source, marker, markerIndex) {
  const start = source.indexOf('{', markerIndex + marker.length)
  if (start === -1) throw new Error('compiled Nitro config object is missing')

  let depth = 0
  let inString = false
  let escaped = false
  for (let index = start; index < source.length; index += 1) {
    const character = source[index]
    if (inString) {
      if (escaped) escaped = false
      else if (character === '\\') escaped = true
      else if (character === '"') inString = false
      continue
    }
    if (character === '"') inString = true
    else if (character === '{') depth += 1
    else if (character === '}') {
      depth -= 1
      if (depth === 0) return source.slice(start, index + 1)
    }
  }
  throw new Error('compiled Nitro config object is truncated')
}

export function readCompiledRouteRules(outputRoot) {
  const serverRoot = resolve(outputRoot, 'server')
  const matches = []
  for (const path of listFiles(serverRoot).filter(file => file.endsWith('.mjs'))) {
    const source = readFileSync(path, 'utf8')
    for (const markerIndex of markerIndexes(source, INLINE_CONFIG_MARKER)) {
      matches.push({ source, markerIndex })
    }
  }
  if (matches.length !== 1) {
    throw new Error(`expected exactly one compiled Nitro config marker, found ${matches.length}`)
  }
  const match = matches[0]
  const rawConfig = extractJsonObject(match.source, INLINE_CONFIG_MARKER, match.markerIndex)
  const config = JSON.parse(rawConfig)
  return plainRecord(plainRecord(config.nitro, 'compiled Nitro config').routeRules, 'compiled route rules')
}

function extractJsonString(source, marker, markerIndex) {
  let start = markerIndex + marker.length
  while (/\s/u.test(source[start] ?? '')) start += 1
  if (source[start] !== '"') throw new Error(`compiled ${marker.trim()} value is not a JSON string`)
  let escaped = false
  for (let index = start + 1; index < source.length; index += 1) {
    const character = source[index]
    if (escaped) escaped = false
    else if (character === '\\') escaped = true
    else if (character === '"') return JSON.parse(source.slice(start, index + 1))
  }
  throw new Error(`compiled ${marker.trim()} value is truncated`)
}

function readUniqueEmbeddedString(outputRoot, marker, label) {
  const matches = []
  for (const path of listFiles(resolve(outputRoot, 'server')).filter(file => file.endsWith('.mjs'))) {
    const source = readFileSync(path, 'utf8')
    for (const markerIndex of markerIndexes(source, marker)) matches.push({ source, markerIndex })
  }
  if (matches.length !== 1) {
    throw new Error(`expected exactly one embedded ${label} marker, found ${matches.length}`)
  }
  return Buffer.from(extractJsonString(matches[0].source, marker, matches[0].markerIndex), 'utf8')
}

export function readEmbeddedArtifactSources(outputRoot, expected) {
  const routeSource = readUniqueEmbeddedString(outputRoot, 'const routeArtifactSource = ', 'route artifact')
  const disclosureSource = readUniqueEmbeddedString(
    outputRoot,
    'const disclosureArtifactSource = ',
    'AI disclosure artifact',
  )
  if (!Buffer.isBuffer(expected?.routeSource) || !routeSource.equals(expected.routeSource)) {
    throw new Error('embedded route artifact source mismatch')
  }
  if (!Buffer.isBuffer(expected?.disclosureSource) || !disclosureSource.equals(expected.disclosureSource)) {
    throw new Error('embedded AI disclosure artifact source mismatch')
  }
  return {
    routeDigest: sha256(routeSource),
    disclosureDigest: sha256(disclosureSource),
  }
}

function parseArtifactJson(source, label) {
  try {
    return JSON.parse(source.toString('utf8'))
  } catch {
    throw new Error(`${label} artifact is not valid JSON`)
  }
}

export function validateGeneratorRouteArtifact(source) {
  return parseLaunchRouteManifestArtifact(parseArtifactJson(Buffer.from(source), 'route manifest'))
}

export function validateGeneratorAiDisclosure(source) {
  return parseAiDisclosureArtifact(parseArtifactJson(Buffer.from(source), 'AI disclosure'))
}

function readArtifactEvidence(path, expectedRevision, label, validator) {
  const raw = readFileSync(path)
  const artifact = plainRecord(validator(raw), `${label} artifact`)
  return {
    revision: exactRevision(artifact.revision, expectedRevision, `${label} artifact`),
    sha256: sha256(raw),
    source: raw,
  }
}

const SOURCE_REVISION_PATTERN = /^[0-9a-f]{40}$/u

export function resolveSourceRevision(options = {}) {
  const env = options.env ?? process.env
  const repositoryRoot = options.repositoryRoot ?? process.cwd()
  const gitCommand = options.gitCommand ?? 'git'
  for (const name of ['BUILD_REVISION', 'GIT_COMMIT', 'SOURCE_REVISION']) {
    if (!Object.hasOwn(env, name) || env[name] === undefined) continue
    const value = env[name]
    if (typeof value !== 'string' || !SOURCE_REVISION_PATTERN.test(value)) {
      throw new Error(`${name} must be a lowercase 40-hex source revision`)
    }
    return value
  }
  const result = spawnSync(gitCommand, ['rev-parse', '--verify', 'HEAD'], {
    cwd: repositoryRoot,
    encoding: 'utf8',
    windowsHide: true,
  })
  const revision = result.status === 0 ? result.stdout.trim() : ''
  if (!SOURCE_REVISION_PATTERN.test(revision)) {
    throw new Error('source revision unavailable: set BUILD_REVISION for builds without git')
  }
  return revision
}

export function writeLaunchReadinessManifest(outputManifestPath, manifest, options = {}) {
  const fsOps = options.fsOps ?? { writeFileSync, renameSync, rmSync }
  const temporaryPath = resolve(
    dirname(outputManifestPath),
    `.${basename(outputManifestPath)}.${process.pid}.${randomUUID()}.tmp`,
  )
  try {
    fsOps.writeFileSync(temporaryPath, `${JSON.stringify(manifest, null, 2)}\n`, {
      encoding: 'utf8',
      flag: 'wx',
    })
    fsOps.renameSync(temporaryPath, outputManifestPath)
  } finally {
    fsOps.rmSync(temporaryPath, { force: true })
  }
}

export async function generateLaunchReadinessManifest(options = {}) {
  const projectRoot = resolve(options.projectRoot ?? resolve(dirname(fileURLToPath(import.meta.url)), '..'))
  const repositoryRoot = resolve(projectRoot, '..')
  const outputRoot = resolve(projectRoot, '.output')
  const outputManifestPath = resolve(outputRoot, 'server/launch-readiness-manifest.json')
  rmSync(outputManifestPath, { force: true })
  if (!existsSync(resolve(outputRoot, 'server')) || !existsSync(resolve(outputRoot, 'public'))) {
    throw new Error('Nuxt output is missing; run nuxt build before readiness generation')
  }

  const routeManifest = readArtifactEvidence(
    resolve(repositoryRoot, 'config/launch-indexing-policy.json'),
    ROUTE_MANIFEST_REVISION,
    'route manifest',
    validateGeneratorRouteArtifact,
  )
  const aiDisclosure = readArtifactEvidence(
    resolve(repositoryRoot, 'config/ai-disclosure.json'),
    AI_DISCLOSURE_REVISION,
    'AI disclosure',
    validateGeneratorAiDisclosure,
  )
  const embeddedArtifacts = readEmbeddedArtifactSources(outputRoot, {
    routeSource: routeManifest.source,
    disclosureSource: aiDisclosure.source,
  })
  if (
    embeddedArtifacts.routeDigest !== routeManifest.sha256
    || embeddedArtifacts.disclosureDigest !== aiDisclosure.sha256
  ) {
    throw new Error('embedded launch artifact digest mismatch')
  }
  const compiledCacheRules = auditCompiledRouteRules(readCompiledRouteRules(outputRoot))
  const publicFiles = listFiles(resolve(outputRoot, 'public'))
    .map(path => `public/${portableRelative(resolve(outputRoot, 'public'), path)}`)
    .sort()
  const publicPrerenderFiles = auditPublicPrerenderFiles(publicFiles)

  const finalWorkerPath = resolve(outputRoot, 'public/sw.js')
  const sourceWorkerPath = resolve(projectRoot, 'public/sw.js')
  const finalWorkerSource = readFileSync(finalWorkerPath)
  const sourceWorkerSource = readFileSync(sourceWorkerPath)
  if (!finalWorkerSource.equals(sourceWorkerSource)) {
    throw new Error('final service-worker source is stale')
  }
  const cachePurge = await verifyServiceWorkerActivation(finalWorkerSource.toString('utf8'))

  const manifest = {
    schema_version: 1,
    build_revision: resolveSourceRevision({ env: process.env, repositoryRoot }),
    artifacts: {
      route_manifest: { revision: routeManifest.revision, sha256: routeManifest.sha256 },
      ai_disclosure: { revision: aiDisclosure.revision, sha256: aiDisclosure.sha256 },
      policy_fingerprint: buildGeneratorPolicyFingerprint({
        routeRevision: routeManifest.revision,
        routeDigest: routeManifest.sha256,
        disclosureRevision: aiDisclosure.revision,
        disclosureDigest: aiDisclosure.sha256,
      }),
    },
    policy_route_classes: [...POLICY_ROUTE_CLASSES],
    compiled_cache_rules: compiledCacheRules,
    public_prerender_files: publicPrerenderFiles,
    service_worker: {
      version: SERVICE_WORKER_VERSION,
      rule_digest: sha256(finalWorkerSource),
      cache_purge: cachePurge,
    },
  }

  writeLaunchReadinessManifest(outputManifestPath, manifest)
  return manifest
}

function deepFreeze(value) {
  if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value)
    for (const child of Object.values(value)) deepFreeze(child)
  }
  return value
}

const invokedPath = process.argv[1] ? resolve(process.argv[1]) : ''
if (invokedPath.toLowerCase() === fileURLToPath(import.meta.url).toLowerCase()) {
  generateLaunchReadinessManifest()
    .then(manifest => {
      console.log(`launch readiness manifest generated for ${manifest.build_revision}`)
    })
    .catch((error) => {
      const message = error instanceof Error ? error.message : 'unknown readiness generation failure'
      console.error(`launch readiness generation failed: ${message}`)
      process.exitCode = 1
    })
}
