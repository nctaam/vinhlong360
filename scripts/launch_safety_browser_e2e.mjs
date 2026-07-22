#!/usr/bin/env node

import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const POLICY_CACHE_NAMES = new Set([
  'navigation',
  'html',
  'root-seo',
  'internal',
  'api',
  'selective-open',
  'failed-open',
  'vl360-v3-html',
  'vl360-v3-assets',
  'vl360-launch-assets-v1',
  'vl360-launch-v0-assets',
  'vl360-selective-open-html',
  'vl360-failed-open-api',
])
const LEGACY_MARKER = 'launch-safety-legacy-policy-replay-marker'
const DEFAULT_BASE_URL = process.env.SMOKE_BASE_URL || 'http://localhost:3000'
const MAX_EVIDENCE_BYTES = 16 * 1024

class LaunchSafetyError extends Error {
  constructor(code, message, { blocked = false } = {}) {
    super(message)
    this.code = code
    this.blocked = blocked
  }
}

function usage() {
  return `Usage: node scripts/launch_safety_browser_e2e.mjs [options]

Options:
  --probe-browser                           Check browser availability without side effects
  --base-url <url>                         Public Nuxt origin to exercise
  --profile <directory>                    Chrome user-data directory to reuse
  --install-legacy-worker-first            Install and seed the legacy worker
  --activate-current-worker                Activate the current service worker
  --assert-policy-cache-storage-empty      Require policy-bearing caches purged
  --assert-offline-policy-replay-denied    Require offline policy navigation denied
  --evidence <path>                        Write bounded, redacted JSON evidence
  --help                                   Show this help
`
}

function parseArgs(argv) {
  const args = {
    baseUrl: DEFAULT_BASE_URL,
    profile: process.env.SMOKE_PROFILE || '',
    installLegacyWorkerFirst: false,
    activateCurrentWorker: false,
    assertPolicyCacheStorageEmpty: false,
    assertOfflinePolicyReplayDenied: false,
    evidence: process.env.SMOKE_LAUNCH_SAFETY_EVIDENCE || '',
    help: false,
  }
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index]
    if (flag === '--help') {
      args.help = true
      continue
    }
    if (flag === '--install-legacy-worker-first') {
      args.installLegacyWorkerFirst = true
      continue
    }
    if (flag === '--activate-current-worker') {
      args.activateCurrentWorker = true
      continue
    }
    if (flag === '--assert-policy-cache-storage-empty') {
      args.assertPolicyCacheStorageEmpty = true
      continue
    }
    if (flag === '--assert-offline-policy-replay-denied') {
      args.assertOfflinePolicyReplayDenied = true
      continue
    }
    if (['--base-url', '--profile', '--evidence'].includes(flag)) {
      const value = argv[index + 1]
      if (!value || value.startsWith('--')) throw new LaunchSafetyError('invalid-arguments', `${flag} requires a value`)
      index += 1
      if (flag === '--base-url') args.baseUrl = value
      if (flag === '--profile') args.profile = value
      if (flag === '--evidence') args.evidence = value
      continue
    }
    throw new LaunchSafetyError('invalid-arguments', `unknown option: ${flag}`)
  }
  if (args.help) return args
  let parsed
  try {
    parsed = new URL(args.baseUrl)
  } catch {
    throw new LaunchSafetyError('invalid-base-url', 'base URL is invalid')
  }
  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password || parsed.hash) {
    throw new LaunchSafetyError('invalid-base-url', 'base URL is invalid')
  }
  if (args.assertPolicyCacheStorageEmpty && !args.installLegacyWorkerFirst) {
    throw new LaunchSafetyError('invalid-arguments', 'cache assertion requires legacy worker installation')
  }
  if ((args.assertPolicyCacheStorageEmpty || args.assertOfflinePolicyReplayDenied) && !args.activateCurrentWorker) {
    throw new LaunchSafetyError('invalid-arguments', 'policy assertions require current worker activation')
  }
  args.baseUrl = parsed.origin
  return args
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function findChrome() {
  if (Object.prototype.hasOwnProperty.call(process.env, 'CHROME_PATH')) {
    return process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH)
      ? process.env.CHROME_PATH
      : undefined
  }
  const candidates = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA, 'Google\\Chrome\\Application\\chrome.exe') : '',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium',
  ].filter(Boolean)
  return candidates.find(candidate => existsSync(candidate))
}

function redactSensitiveUrl(input) {
  const raw = String(input || '')
  try {
    const url = new URL(raw)
    for (const key of ['token', 'access_token', 'auth', 'authorization', 'session', 'session_token', 'vl360_token', 'code']) {
      if (url.searchParams.has(key)) url.searchParams.set(key, '[redacted]')
    }
    return url.toString()
  } catch {
    return raw.replace(/([?&](?:token|access_token|auth|authorization|session|session_token|vl360_token|code)=)[^&#\s]+/gi, '$1[redacted]')
  }
}

function safeMessage(error) {
  return redactSensitiveUrl(error instanceof Error ? error.message : String(error || 'unknown error')).slice(0, 500)
}

async function assertServer(baseUrl) {
  let response
  try {
    response = await fetch(new URL('/', baseUrl), { signal: AbortSignal.timeout(5000) })
  } catch {
    throw new LaunchSafetyError('server-unavailable', 'base URL is not reachable', { blocked: true })
  }
  if (response.status >= 500) throw new LaunchSafetyError('server-unavailable', 'base URL returned a server error', { blocked: true })
  let worker
  try {
    worker = await fetch(new URL('/sw.js', baseUrl), { signal: AbortSignal.timeout(5000) })
  } catch {
    throw new LaunchSafetyError('service-worker-unavailable', 'current service worker is not reachable', { blocked: true })
  }
  if (!worker.ok || !(await worker.text()).trim()) {
    throw new LaunchSafetyError('service-worker-unavailable', 'current service worker is not reachable', { blocked: true })
  }
}

class CdpClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl
    this.seq = 0
    this.pending = new Map()
    this.listeners = new Map()
  }

  connect() {
    if (typeof WebSocket === 'undefined') throw new LaunchSafetyError('node-websocket-unavailable', 'Node WebSocket support is unavailable', { blocked: true })
    this.ws = new WebSocket(this.wsUrl)
    this.ws.onmessage = event => {
      const message = JSON.parse(event.data)
      if (message.id && this.pending.has(message.id)) {
        const pending = this.pending.get(message.id)
        clearTimeout(pending.timer)
        this.pending.delete(message.id)
        if (message.error) pending.reject(new Error(message.error.message || 'CDP error'))
        else pending.resolve(message.result || {})
        return
      }
      if (message.method && this.listeners.has(message.method)) {
        for (const handler of this.listeners.get(message.method)) handler(message.params || {})
      }
    }
    return new Promise((resolve, reject) => {
      this.ws.onopen = resolve
      this.ws.onerror = () => reject(new LaunchSafetyError('cdp-connect-failed', 'Chrome CDP connection failed', { blocked: true }))
    })
  }

  send(method, params = {}, timeoutMs = 15000) {
    const id = ++this.seq
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id)
        reject(new LaunchSafetyError('cdp-timeout', `CDP timeout: ${method}`))
      }, timeoutMs)
      this.pending.set(id, { resolve, reject, timer })
      this.ws.send(JSON.stringify({ id, method, params }))
    })
  }

  on(method, handler) {
    if (!this.listeners.has(method)) this.listeners.set(method, new Set())
    this.listeners.get(method).add(handler)
    return () => this.listeners.get(method)?.delete(handler)
  }

  waitFor(method, timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
      let timer
      const off = this.on(method, params => {
        clearTimeout(timer)
        off()
        resolve(params)
      })
      timer = setTimeout(() => {
        off()
        reject(new LaunchSafetyError('cdp-event-timeout', `CDP event timeout: ${method}`))
      }, timeoutMs)
    })
  }

  close() {
    this.ws?.close()
  }
}

export function parseSpawnedCdpEndpoint(output) {
  const match = /DevTools listening on (ws:\/\/[^\s]+)/u.exec(String(output || ''))
  if (!match) {
    throw new LaunchSafetyError('chrome-cdp-unavailable', 'Chrome did not announce a CDP endpoint', { blocked: true })
  }
  let parsed
  try {
    parsed = new URL(match[1])
  } catch {
    throw new LaunchSafetyError('chrome-cdp-ownership-mismatch', 'Chrome announced an invalid CDP endpoint', { blocked: true })
  }
  if (
    parsed.protocol !== 'ws:'
    || !['127.0.0.1', '::1', 'localhost'].includes(parsed.hostname)
    || !/^\/devtools\/browser\/[^/]+$/u.test(parsed.pathname)
    || !Number.isInteger(Number(parsed.port))
    || Number(parsed.port) < 1
    || Number(parsed.port) > 65535
  ) {
    throw new LaunchSafetyError('chrome-cdp-ownership-mismatch', 'Chrome announced an invalid CDP endpoint', { blocked: true })
  }
  const host = parsed.hostname === '::1' ? '[::1]' : parsed.hostname
  return Object.freeze({
    port: Number(parsed.port),
    versionUrl: `http://${host}:${parsed.port}/json/version`,
    webSocketDebuggerUrl: parsed.toString(),
  })
}

export function verifySpawnedCdpEndpoint(endpoint, payload) {
  if (
    !endpoint
    || typeof endpoint.webSocketDebuggerUrl !== 'string'
    || !payload
    || payload.webSocketDebuggerUrl !== endpoint.webSocketDebuggerUrl
  ) {
    throw new LaunchSafetyError('chrome-cdp-ownership-mismatch', 'CDP endpoint does not belong to the spawned Chrome process', { blocked: true })
  }
  return endpoint
}

function waitForSpawnedCdpAnnouncement(chrome) {
  if (!chrome.stderr) {
    throw new LaunchSafetyError('chrome-cdp-unavailable', 'Chrome stderr is unavailable', { blocked: true })
  }
  return new Promise((resolve, reject) => {
    let output = ''
    let settled = false
    const finish = (handler, value) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      chrome.stderr.off('data', onData)
      chrome.off('error', onError)
      chrome.off('exit', onExit)
      handler(value)
    }
    const onData = chunk => {
      output = `${output}${String(chunk)}`.slice(-16384)
      try {
        finish(resolve, parseSpawnedCdpEndpoint(output))
      } catch (error) {
        if (!(error instanceof LaunchSafetyError) || error.code !== 'chrome-cdp-unavailable') {
          finish(reject, error)
        }
      }
    }
    const onError = () => finish(
      reject,
      new LaunchSafetyError('chrome-cdp-unavailable', 'Chrome process failed before CDP startup', { blocked: true }),
    )
    const onExit = () => finish(
      reject,
      new LaunchSafetyError('chrome-cdp-unavailable', 'Chrome exited before CDP startup', { blocked: true }),
    )
    const timer = setTimeout(() => finish(
      reject,
      new LaunchSafetyError('chrome-cdp-unavailable', 'Chrome did not announce a CDP endpoint', { blocked: true }),
    ), 20000)
    chrome.stderr.on('data', onData)
    chrome.once('error', onError)
    chrome.once('exit', onExit)
  })
}

async function waitForSpawnedChrome(chrome) {
  const endpoint = await waitForSpawnedCdpAnnouncement(chrome)
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      const response = await fetch(endpoint.versionUrl, { signal: AbortSignal.timeout(1000) })
      if (!response.ok) throw new Error('CDP version endpoint is unavailable')
      return verifySpawnedCdpEndpoint(endpoint, await response.json())
    } catch (error) {
      if (error instanceof LaunchSafetyError && error.code === 'chrome-cdp-ownership-mismatch') throw error
    }
    await sleep(250)
  }
  throw new LaunchSafetyError('chrome-cdp-unavailable', 'Spawned Chrome did not open its CDP endpoint', { blocked: true })
}

async function createPageTarget(port) {
  const endpoint = `http://127.0.0.1:${port}/json/new?about:blank`
  let response = await fetch(endpoint, { method: 'PUT' })
  if (!response.ok) response = await fetch(endpoint)
  if (!response.ok) throw new LaunchSafetyError('chrome-target-unavailable', 'Chrome page target is unavailable', { blocked: true })
  const payload = await response.json()
  if (!payload.webSocketDebuggerUrl) throw new LaunchSafetyError('chrome-target-unavailable', 'Chrome page target is unavailable', { blocked: true })
  return payload.webSocketDebuggerUrl
}

async function evaluate(cdp, expression) {
  const result = await cdp.send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
    userGesture: true,
  })
  if (result.exceptionDetails) throw new LaunchSafetyError('page-evaluation-failed', 'page evaluation failed')
  return result.result?.value
}

async function navigate(cdp, url) {
  const load = cdp.waitFor('Page.loadEventFired', 20000).catch(() => undefined)
  const result = await cdp.send('Page.navigate', { url })
  await load
  return result
}

const LEGACY_WORKER = `
const CACHE = 'vl360-selective-open-html'
self.addEventListener('install', event => event.waitUntil(self.skipWaiting()))
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()))
self.addEventListener('fetch', event => {
  if (event.request.mode === 'navigate' || event.request.url.includes('launch-matrix-offline')) {
    event.respondWith(caches.match(event.request).then(hit => hit || fetch(event.request)))
  }
})
`

async function registerServiceWorker(url) {
  const registration = await navigator.serviceWorker.register(url, { scope: '/' })
  const wait = worker => new Promise((resolve, reject) => {
    if (!worker) return reject(new Error('worker missing'))
    if (worker.state === 'activated') return resolve()
    const timer = setTimeout(() => reject(new Error('worker activation timeout')), 20000)
    worker.addEventListener('statechange', () => {
      if (worker.state === 'activated') { clearTimeout(timer); resolve() }
      if (worker.state === 'redundant') { clearTimeout(timer); reject(new Error('worker redundant')) }
    })
  })
  await wait(registration.installing || registration.waiting || registration.active)
  await navigator.serviceWorker.ready
  return { active: registration.active?.scriptURL || '', controller: navigator.serviceWorker.controller?.scriptURL || '' }
}

async function seedCaches(target, marker, names) {
  for (const name of names) {
    const cache = await caches.open(name)
    await cache.put(new Request(target), new Response(marker, {
      status: 200,
      headers: {
        'content-type': 'text/html; charset=utf-8',
        'cache-control': 'no-store',
        'x-launch-indexing-policy': 'selective-open',
      },
    }))
  }
  return await caches.keys()
}

async function installLegacyWorker(cdp, origin) {
  const scriptUrl = `${origin}/sw.js?launch-safety-legacy=${Date.now()}`
  const body = Buffer.from(LEGACY_WORKER, 'utf8').toString('base64')
  let fulfillError
  const off = cdp.on('Fetch.requestPaused', params => {
    const requestUrl = params.request?.url || ''
    const task = requestUrl.startsWith(`${origin}/sw.js`)
      ? cdp.send('Fetch.fulfillRequest', {
        requestId: params.requestId,
        responseCode: 200,
        responseHeaders: [
          { name: 'Content-Type', value: 'application/javascript; charset=utf-8' },
          { name: 'Cache-Control', value: 'no-store' },
          { name: 'Service-Worker-Allowed', value: '/' },
        ],
        body,
      })
      : cdp.send('Fetch.continueRequest', { requestId: params.requestId })
    task.catch(error => { fulfillError = error })
  })
  await cdp.send('Fetch.enable', { patterns: [{ urlPattern: `${origin}/sw.js*`, requestStage: 'Request' }] })
  try {
    const state = await evaluate(cdp, `(${registerServiceWorker.toString()})(${JSON.stringify(scriptUrl)})`)
    if (!state?.active || fulfillError) throw new LaunchSafetyError('legacy-worker-activation-failed', 'legacy worker activation failed')
  } finally {
    off()
    await cdp.send('Fetch.disable').catch(() => {})
  }
}

async function seedLegacyCaches(cdp, offlineUrl) {
  const result = await evaluate(cdp, `(${seedCaches.toString()})(${JSON.stringify(offlineUrl)}, ${JSON.stringify(LEGACY_MARKER)}, ${JSON.stringify([...POLICY_CACHE_NAMES])})`)
  if (!Array.isArray(result) || !result.some(name => name === 'vl360-selective-open-html')) {
    throw new LaunchSafetyError('legacy-cache-seed-failed', 'legacy policy cache seed failed')
  }
}

async function activateCurrentWorker(cdp, origin) {
  const scriptUrl = `${origin}/sw.js?launch-safety-current=${Date.now()}`
  const state = await evaluate(cdp, `(${registerServiceWorker.toString()})(${JSON.stringify(scriptUrl)})`)
  if (!state?.active) throw new LaunchSafetyError('current-worker-activation-failed', 'current worker activation failed')
}

async function cacheState(cdp) {
  const state = await evaluate(cdp, `caches.keys()`)
  if (!Array.isArray(state)) throw new LaunchSafetyError('cache-inspection-failed', 'cache storage inspection failed')
  const policyCacheCount = state.filter(name => POLICY_CACHE_NAMES.has(name)).length
  return { policyCacheCount, cacheCount: state.length }
}

async function assertOfflineReplay(cdp, baseUrl, offlineUrl) {
  await cdp.send('Network.emulateNetworkConditions', {
    offline: true,
    latency: 0,
    downloadThroughput: 0,
    uploadThroughput: 0,
  })
  try {
    const replay = await evaluate(cdp, `fetch(${JSON.stringify(new URL('/robots.txt', baseUrl).toString())}, { cache: 'no-store' }).then(response => ({ ok: true, status: response.status })).catch(() => ({ ok: false }))`)
    if (replay?.ok) throw new LaunchSafetyError('offline-policy-replay-allowed', 'offline policy replay resolved')
    const navigation = await cdp.send('Page.navigate', { url: offlineUrl })
    if (!navigation.errorText || navigation.errorText === '') throw new LaunchSafetyError('offline-navigation-replay-allowed', 'offline policy navigation resolved')
  } finally {
    await cdp.send('Network.emulateNetworkConditions', {
      offline: false,
      latency: 0,
      downloadThroughput: -1,
      uploadThroughput: -1,
    }).catch(() => {})
  }
}

async function writeEvidence(file, payload) {
  if (!file) return
  const encoded = `${JSON.stringify(payload, null, 2)}\n`
  if (Buffer.byteLength(encoded, 'utf8') > MAX_EVIDENCE_BYTES) throw new LaunchSafetyError('evidence-too-large', 'evidence exceeds bound')
  await mkdir(path.dirname(file), { recursive: true })
  await writeFile(file, encoded, { encoding: 'utf8', mode: 0o600 })
}

async function main(argv = process.argv.slice(2)) {
  if (argv.includes('--probe-browser')) {
    if (argv.length !== 1) return 2
    return findChrome() ? 0 : 3
  }

  let args
  try {
    args = parseArgs(argv)
  } catch (error) {
    console.error(`launch-safety browser smoke blocked: ${safeMessage(error)}`)
    return 2
  }
  if (args.help) {
    console.log(usage())
    return 0
  }

  const evidence = {
    schema_version: 1,
    verdict: 'blocked',
    reasons: [],
    assertions: {
      legacy_worker_installed: false,
      current_worker_activated: false,
      policy_cache_storage_empty: false,
      offline_policy_replay_denied: false,
    },
  }
  let profile = args.profile ? path.resolve(args.profile) : ''
  let temporaryProfile = false
  let chrome
  let cdp
  try {
    await assertServer(args.baseUrl)
    const chromePath = findChrome()
    if (!chromePath) throw new LaunchSafetyError('chrome-unavailable', 'Chrome or Edge was not found', { blocked: true })
    if (!profile) {
      profile = await mkdtemp(path.join(tmpdir(), 'vl360-launch-safety-'))
      temporaryProfile = true
    } else {
      await mkdir(profile, { recursive: true })
    }
    chrome = spawn(chromePath, [
      '--headless=new',
      '--remote-debugging-port=0',
      `--user-data-dir=${profile}`,
      '--disable-gpu',
      '--no-first-run',
      '--no-default-browser-check',
      'about:blank',
    ], { stdio: ['ignore', 'ignore', 'pipe'] })
    const endpoint = await waitForSpawnedChrome(chrome)
    cdp = new CdpClient(await createPageTarget(endpoint.port))
    await cdp.connect()
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Network.enable')
    await navigate(cdp, args.baseUrl)

    const origin = new URL(args.baseUrl).origin
    const offlineUrl = new URL('/launch-matrix-offline.html?proof=1', args.baseUrl).toString()
    if (args.installLegacyWorkerFirst) {
      await installLegacyWorker(cdp, origin)
      evidence.assertions.legacy_worker_installed = true
      await seedLegacyCaches(cdp, offlineUrl)
    }
    if (args.activateCurrentWorker) {
      await activateCurrentWorker(cdp, origin)
      // Reload once so clients.claim() controls the page used for offline replay.
      await navigate(cdp, args.baseUrl)
      evidence.assertions.current_worker_activated = true
    }
    if (args.assertPolicyCacheStorageEmpty) {
      const state = await cacheState(cdp)
      if (state.policyCacheCount !== 0) throw new LaunchSafetyError('policy-cache-storage-not-empty', 'policy-bearing caches remain')
      evidence.assertions.policy_cache_storage_empty = true
    }
    if (args.assertOfflinePolicyReplayDenied) {
      await assertOfflineReplay(cdp, args.baseUrl, offlineUrl)
      evidence.assertions.offline_policy_replay_denied = true
    }
    evidence.verdict = 'pass'
  } catch (error) {
    evidence.verdict = error instanceof LaunchSafetyError && error.blocked ? 'blocked' : 'fail'
    evidence.reasons.push(error instanceof LaunchSafetyError ? error.code : 'browser-smoke-failed')
    const prefix = evidence.verdict === 'blocked' ? 'launch-safety browser smoke blocked' : 'launch-safety browser smoke failed'
    console.error(`${prefix}: ${error instanceof LaunchSafetyError ? error.code : safeMessage(error)}`)
  } finally {
    cdp?.close()
    chrome?.kill()
    await sleep(250)
    if (temporaryProfile && profile) await rm(profile, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 }).catch(() => {})
  }
  try {
    await writeEvidence(args.evidence, evidence)
  } catch (error) {
    console.error(`launch-safety browser smoke failed: ${error instanceof LaunchSafetyError ? error.code : 'evidence-write-failed'}`)
    return 2
  }
  return evidence.verdict === 'pass' ? 0 : evidence.verdict === 'blocked' ? 2 : 1
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().then(code => { process.exitCode = code }).catch(error => {
    console.error(`launch-safety browser smoke failed: ${safeMessage(error)}`)
    process.exitCode = 1
  })
}
