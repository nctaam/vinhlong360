#!/usr/bin/env node

import { spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, readFileSync } from 'node:fs'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { basename, dirname, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  collectAssetSetFailures,
  collectStateFailures,
  compactGateEvidence,
  isFreshNavigationState,
  isOwnedBrowserProcess,
} from './detail-grid-gate-core.mjs'

const ROUTE = '/dia-diem/cong-vien-an-hoi'
const REVISION_PATTERN = /^[a-f0-9]{40}$/u
const MAX_CONSOLE_ERRORS = 8
const MAX_REASONS = 32
const MAX_EVIDENCE_BYTES = 64 * 1024
const TOLERANCE_PX = 1
const CONSOLE_DRAIN_MS = 300
const MOBILE_VIEWPORT = Object.freeze({ width: 390, height: 844, mobile: true })
const DESKTOP_VIEWPORT = Object.freeze({ width: 1440, height: 1000, mobile: false })
const STATE_CONFIGS = Object.freeze([
  { viewport_name: 'mobile', viewport: MOBILE_VIEWPORT, mode: 'dark', theme: 'nocturne' },
  { viewport_name: 'mobile', viewport: MOBILE_VIEWPORT, mode: 'light', theme: 'parchment' },
  { viewport_name: 'desktop', viewport: DESKTOP_VIEWPORT, mode: 'dark', theme: 'nocturne' },
  { viewport_name: 'desktop', viewport: DESKTOP_VIEWPORT, mode: 'light', theme: 'parchment' },
])
const scriptRoot = dirname(fileURLToPath(import.meta.url))
const projectRoot = resolve(scriptRoot, '..')
const outputPublicRoot = resolve(projectRoot, '.output/public')

class GateError extends Error {
  constructor(code, message, { blocked = false } = {}) {
    super(message)
    this.code = code
    this.blocked = blocked
  }
}

function usage() {
  return [
    'Usage: node scripts/check-detail-grid-containment.mjs --base-url <url> --expected-revision <sha>',
    '',
    'Required:',
    '  --base-url <url>             Production preview origin',
    '  --expected-revision <sha>    Reviewed lowercase 40-hex source revision',
    '',
    'Mutation proof:',
    '  --mutation mobile-main-auto-min-width',
    '      Inject a later min-width:auto !important regression rule',
    '',
  ].join('\n')
}

function parseArgs(argv) {
  const args = { baseUrl: '', expectedRevision: '', mutation: '', help: false }
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index]
    if (flag === '--help') {
      args.help = true
      continue
    }
    if (flag === '--base-url' || flag === '--expected-revision' || flag === '--mutation') {
      const value = argv[index + 1]
      if (!value || value.startsWith('--')) throw new GateError('invalid-arguments', flag + ' requires a value')
      index += 1
      if (flag === '--base-url') args.baseUrl = value
      else if (flag === '--expected-revision') args.expectedRevision = value
      else args.mutation = value
      continue
    }
    throw new GateError('invalid-arguments', 'unknown option: ' + flag)
  }
  if (args.help) return args
  if (!args.baseUrl || !args.expectedRevision) {
    throw new GateError('invalid-arguments', '--base-url and --expected-revision are required')
  }
  let parsed
  try {
    parsed = new URL(args.baseUrl)
  } catch {
    throw new GateError('invalid-base-url', 'base URL is invalid')
  }
  if (
    !['http:', 'https:'].includes(parsed.protocol)
    || parsed.username
    || parsed.password
    || parsed.pathname !== '/'
    || parsed.search
    || parsed.hash
  ) {
    throw new GateError('invalid-base-url', 'base URL must be an HTTP(S) origin')
  }
  if (!REVISION_PATTERN.test(args.expectedRevision)) {
    throw new GateError('invalid-expected-revision', 'expected revision must be lowercase 40-hex')
  }
  if (args.mutation && args.mutation !== 'mobile-main-auto-min-width') {
    throw new GateError('invalid-mutation', 'mutation must be mobile-main-auto-min-width')
  }
  args.baseUrl = parsed.origin
  return args
}

function safeMessage(error) {
  return (error instanceof Error ? error.message : String(error || 'unknown error'))
    .replace(/([?&](?:token|auth|session|code)=)[^&#\s]+/giu, '$1[redacted]')
    .slice(0, 300)
}

function sleep(ms) {
  return new Promise(resolveSleep => setTimeout(resolveSleep, ms))
}

function addReason(evidence, code, message) {
  if (evidence.reasons.length >= MAX_REASONS) return
  evidence.reasons.push({ code: String(code).slice(0, 100), message: String(message).slice(0, 300) })
}

function stateReason(evidence, state, code, message) {
  state.failures.push(code)
  addReason(evidence, state.viewport_name + ':' + state.theme + ':' + code, message)
}

function readManifest() {
  const path = resolve(projectRoot, '.output/server/launch-readiness-manifest.json')
  let manifest
  try {
    manifest = JSON.parse(readFileSync(path, 'utf8'))
  } catch {
    throw new GateError('manifest-unavailable', 'local launch readiness manifest is unavailable', { blocked: true })
  }
  const revision = manifest?.build_revision
  if (!REVISION_PATTERN.test(revision || '')) {
    throw new GateError('manifest-invalid', 'local launch readiness manifest revision is invalid')
  }
  return revision
}

function nuxtAssetPath(baseUrl, value) {
  const origin = new URL(baseUrl).origin
  try {
    const parsed = new URL(value, origin)
    return parsed.origin === origin && parsed.pathname.startsWith('/_nuxt/') ? parsed.pathname : ''
  } catch {
    return ''
  }
}

function localAssetPath(assetPath) {
  const candidate = resolve(outputPublicRoot, '.' + assetPath)
  const prefix = (outputPublicRoot + sep).toLowerCase()
  if (!candidate.toLowerCase().startsWith(prefix)) {
    throw new GateError('asset-path-invalid', 'preview asset path escaped output root')
  }
  return candidate
}

function findChrome() {
  if (Object.hasOwn(process.env, 'CHROME_PATH')) {
    return process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH) ? process.env.CHROME_PATH : undefined
  }
  const candidates = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    process.env.LOCALAPPDATA ? resolve(process.env.LOCALAPPDATA, 'Google/Chrome/Application/chrome.exe') : '',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
  ].filter(Boolean)
  return candidates.find(candidate => existsSync(candidate))
}

function childExited(child) {
  return !child || child.exitCode !== null || child.signalCode !== null
}

function waitForExit(child, timeoutMs) {
  if (childExited(child)) return Promise.resolve(true)
  return new Promise(resolveWait => {
    let timer
    const finish = exited => {
      clearTimeout(timer)
      child.off('exit', onExit)
      child.off('error', onError)
      resolveWait(exited)
    }
    const onExit = () => finish(true)
    const onError = () => finish(false)
    child.once('exit', onExit)
    child.once('error', onError)
    timer = setTimeout(() => finish(childExited(child)), timeoutMs)
  })
}

async function stopChrome(child) {
  if (childExited(child)) return
  if (process.platform === 'win32') {
    let taskkillError
    try {
      await new Promise((resolveKill, reject) => {
        const killer = spawn(process.env.ComSpec || 'cmd.exe', ['/d', '/s', '/c', 'taskkill /PID ' + child.pid + ' /T /F'], {
          stdio: 'ignore',
          windowsHide: true,
        })
        killer.once('error', reject)
        killer.once('exit', code => code === 0 ? resolveKill() : reject(new Error('taskkill exited with code ' + code)))
      })
    } catch (error) {
      taskkillError = error
    }
    if (taskkillError && !(await waitForExit(child, 5000))) throw taskkillError
  } else {
    child.kill('SIGTERM')
  }
  if (!(await waitForExit(child, 5000))) {
    child.kill('SIGKILL')
    if (!(await waitForExit(child, 1000))) throw new Error('Chrome did not exit after cleanup')
  }
}

function runCaptured(command, args, options = {}) {
  return new Promise((resolveRun, reject) => {
    const child = spawn(command, args, { ...options, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true })
    let stdout = ''
    let stderr = ''
    const append = (current, chunk) => (current + String(chunk)).slice(-512 * 1024)
    child.stdout?.on('data', chunk => { stdout = append(stdout, chunk) })
    child.stderr?.on('data', chunk => { stderr = append(stderr, chunk) })
    child.once('error', reject)
    child.once('exit', code => {
      if (code === 0) resolveRun({ stdout, stderr })
      else reject(new Error(basename(command) + ' exited with code ' + code + (stderr.trim() ? ': ' + stderr.trim() : '')))
    })
  })
}

async function listOwnedBrowserProcesses({ profile, browserPath }) {
  let processes = []
  if (process.platform === 'win32') {
    const source = [
      "$ErrorActionPreference = 'Stop'",
      "$browserName = [IO.Path]::GetFileName($env:VL360_GATE_BROWSER_PATH).Replace(\"'\", \"''\")",
      "$filter = \"Name='\" + $browserName + \"'\"",
      '$items = @(Get-CimInstance Win32_Process -Filter $filter | Select-Object ProcessId, ExecutablePath, CommandLine)',
      'ConvertTo-Json -InputObject $items -Compress',
    ].join('; ')
    const result = await runCaptured('powershell.exe', ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', source], {
      env: { ...process.env, VL360_GATE_BROWSER_PATH: browserPath },
    })
    const parsed = JSON.parse(result.stdout.trim() || '[]')
    processes = (Array.isArray(parsed) ? parsed : [parsed]).map(processInfo => ({
      pid: Number(processInfo.ProcessId || 0),
      executablePath: String(processInfo.ExecutablePath || ''),
      commandLine: String(processInfo.CommandLine || ''),
    }))
  } else {
    const result = await runCaptured('ps', ['-axo', 'pid=,command='])
    processes = result.stdout.split(/\r?\n/u).map(line => {
      const match = /^\s*(\d+)\s+(.+)$/u.exec(line)
      return match ? { pid: Number(match[1]), executablePath: browserPath, commandLine: match[2] } : null
    }).filter(Boolean)
  }
  return processes.filter(processInfo => isOwnedBrowserProcess(processInfo, { profile, browserPath }))
}

async function waitForOwnedBrowserExit(browser, timeoutMs = 5000) {
  const deadline = Date.now() + timeoutMs
  let remaining = []
  do {
    remaining = await listOwnedBrowserProcesses(browser)
    if (remaining.length === 0) return []
    await sleep(100)
  } while (Date.now() < deadline)
  return remaining
}

function parseCdpEndpoint(output) {
  const match = /DevTools listening on (ws:\/\/[^\s]+)/u.exec(output)
  if (!match) return undefined
  const parsed = new URL(match[1])
  if (parsed.protocol !== 'ws:' || !['127.0.0.1', 'localhost', '::1'].includes(parsed.hostname) || !parsed.port) {
    throw new GateError('chrome-cdp-ownership-mismatch', 'Chrome announced a non-loopback CDP endpoint', { blocked: true })
  }
  return { port: Number(parsed.port), webSocketDebuggerUrl: parsed.toString() }
}

async function launchChrome() {
  const chromePath = findChrome()
  if (!chromePath) throw new GateError('chrome-unavailable', 'Chrome or Edge executable is unavailable', { blocked: true })
  const profile = await mkdtemp(resolve(tmpdir(), 'vl360-detail-grid-'))
  let child
  try {
    child = spawn(chromePath, [
      '--headless=new',
      '--disable-background-networking',
      '--disable-component-update',
      '--disable-default-apps',
      '--disable-extensions',
      '--disable-sync',
      '--no-first-run',
      '--no-default-browser-check',
      '--remote-debugging-port=0',
      '--user-data-dir=' + profile,
      '--window-size=' + DESKTOP_VIEWPORT.width + ',' + DESKTOP_VIEWPORT.height,
      'about:blank',
    ], { stdio: ['ignore', 'ignore', 'pipe'], windowsHide: true })
    let output = ''
    const endpoint = await new Promise((resolveEndpoint, reject) => {
      let timer
      const finish = (handler, value) => {
        clearTimeout(timer)
        child.stderr?.off('data', onData)
        child.off('error', onError)
        child.off('exit', onExit)
        handler(value)
      }
      const onData = chunk => {
        output = (output + String(chunk)).slice(-16384)
        try {
          const parsed = parseCdpEndpoint(output)
          if (parsed) finish(resolveEndpoint, parsed)
        } catch (error) {
          finish(reject, error)
        }
      }
      const onError = () => finish(reject, new GateError('chrome-start-failed', 'Chrome failed before CDP startup', { blocked: true }))
      const onExit = () => finish(reject, new GateError('chrome-start-failed', 'Chrome exited before CDP startup', { blocked: true }))
      timer = setTimeout(() => finish(reject, new GateError('chrome-cdp-unavailable', 'Chrome did not announce CDP', { blocked: true })), 20000)
      child.stderr?.on('data', onData)
      child.once('error', onError)
      child.once('exit', onExit)
    })
    return { child, endpoint, profile, browserPath: chromePath }
  } catch (error) {
    const cleanupErrors = []
    try { await stopChrome(child) } catch (cleanupError) { cleanupErrors.push('chrome:' + safeMessage(cleanupError)) }
    try {
      const remaining = await waitForOwnedBrowserExit({ child, profile, browserPath: chromePath })
      if (remaining.length > 0) cleanupErrors.push('owned-processes:' + remaining.map(processInfo => processInfo.pid).join(','))
    } catch (cleanupError) {
      cleanupErrors.push('owned-process-audit:' + safeMessage(cleanupError))
    }
    try {
      await rm(profile, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 })
    } catch (cleanupError) {
      cleanupErrors.push('profile:' + safeMessage(cleanupError))
    }
    if (cleanupErrors.length > 0) {
      throw new GateError('chrome-start-cleanup-failed', safeMessage(error) + '; ' + cleanupErrors.join('; '), { blocked: true })
    }
    throw error
  }
}

async function createPageTarget(port) {
  const endpoint = 'http://127.0.0.1:' + port + '/json/new?about:blank'
  let response = await fetch(endpoint, { method: 'PUT', signal: AbortSignal.timeout(5000) })
  if (!response.ok) response = await fetch(endpoint, { signal: AbortSignal.timeout(5000) })
  if (!response.ok) throw new GateError('chrome-target-unavailable', 'Chrome page target is unavailable', { blocked: true })
  const payload = await response.json()
  if (!payload.webSocketDebuggerUrl) throw new GateError('chrome-target-unavailable', 'Chrome page target is unavailable', { blocked: true })
  return payload.webSocketDebuggerUrl
}

class CdpClient {
  constructor(url) {
    this.url = url
    this.sequence = 0
    this.pending = new Map()
    this.listeners = new Map()
  }

  connect() {
    if (typeof WebSocket === 'undefined') {
      throw new GateError('node-websocket-unavailable', 'Node WebSocket support is unavailable', { blocked: true })
    }
    this.ws = new WebSocket(this.url)
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
      for (const handler of this.listeners.get(message.method) || []) handler(message.params || {})
    }
    return new Promise((resolveConnect, reject) => {
      this.ws.onopen = resolveConnect
      this.ws.onerror = () => reject(new GateError('cdp-connect-failed', 'Chrome CDP connection failed', { blocked: true }))
    })
  }

  send(method, params = {}, timeoutMs = 15000) {
    const id = ++this.sequence
    return new Promise((resolveSend, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id)
        reject(new GateError('cdp-timeout', 'CDP timeout: ' + method, { blocked: true }))
      }, timeoutMs)
      this.pending.set(id, { resolve: resolveSend, reject, timer })
      this.ws.send(JSON.stringify({ id, method, params }))
    })
  }

  on(method, handler) {
    if (!this.listeners.has(method)) this.listeners.set(method, new Set())
    this.listeners.get(method).add(handler)
    return () => this.listeners.get(method)?.delete(handler)
  }

  waitFor(method, timeoutMs = 20000) {
    return new Promise((resolveEvent, reject) => {
      let timer
      const handler = params => {
        clearTimeout(timer)
        this.listeners.get(method)?.delete(handler)
        resolveEvent(params)
      }
      this.on(method, handler)
      timer = setTimeout(() => {
        this.listeners.get(method)?.delete(handler)
        reject(new GateError('cdp-event-timeout', 'CDP event timeout: ' + method, { blocked: true }))
      }, timeoutMs)
    })
  }

  close() {
    this.ws?.close()
  }
}

class NavigationAssetCapture {
  constructor(cdp, baseUrl) {
    this.cdp = cdp
    this.baseUrl = baseUrl
    this.loaderId = ''
    this.requests = new Map()
    this.unsubscribe = []
  }

  start() {
    this.unsubscribe.push(
      this.cdp.on('Network.requestWillBeSent', params => {
        const assetPath = nuxtAssetPath(this.baseUrl, params.request?.url || '')
        if (!assetPath) return
        this.requests.set(params.requestId, {
          requestId: params.requestId,
          loaderId: params.loaderId || '',
          assetPath,
          response: null,
          finished: false,
          failed: '',
          updatedAt: Date.now(),
        })
      }),
      this.cdp.on('Network.responseReceived', params => {
        const record = this.requests.get(params.requestId)
        if (!record) return
        record.loaderId = params.loaderId || record.loaderId
        record.response = { status: params.response?.status || 0, url: params.response?.url || '' }
        record.updatedAt = Date.now()
      }),
      this.cdp.on('Network.loadingFinished', params => {
        const record = this.requests.get(params.requestId)
        if (!record) return
        record.finished = true
        record.updatedAt = Date.now()
      }),
      this.cdp.on('Network.loadingFailed', params => {
        const record = this.requests.get(params.requestId)
        if (!record) return
        record.failed = String(params.errorText || 'asset request failed')
        record.updatedAt = Date.now()
      }),
    )
  }

  bind(loaderId) {
    if (!loaderId) throw new GateError('navigation-loader-unavailable', 'Detail navigation did not expose a loader ID', { blocked: true })
    this.loaderId = loaderId
  }

  stop() {
    for (const unsubscribe of this.unsubscribe.splice(0)) unsubscribe()
  }

  boundRequests() {
    return [...this.requests.values()].filter(record => record.loaderId === this.loaderId)
  }

  async waitForSettled(timeoutMs = 20000) {
    const deadline = Date.now() + timeoutMs
    while (Date.now() < deadline) {
      const records = this.boundRequests()
      const lastEventAt = Math.max(0, ...records.map(record => record.updatedAt))
      if (
        records.length > 0
        && records.every(record => record.finished || record.failed)
        && Date.now() - lastEventAt >= 300
      ) {
        return records
      }
      await sleep(50)
    }
    throw new GateError('preview-assets-timeout', 'Detail navigation assets did not finish loading', { blocked: true })
  }

  async verify() {
    const records = await this.waitForSettled()
    const failed = records.find(record => record.failed)
    if (failed) {
      throw new GateError('preview-asset-unavailable', 'served asset failed to load: ' + failed.assetPath + ' (' + failed.failed + ')', { blocked: true })
    }
    const sorted = records.sort((left, right) => left.assetPath.localeCompare(right.assetPath) || left.requestId.localeCompare(right.requestId))
    const uniqueAssets = new Map()
    const detailCssPaths = new Set()
    for (const record of sorted) {
      if (!record.response || record.response.status < 200 || record.response.status >= 300) {
        throw new GateError('preview-asset-unavailable', 'served asset returned ' + (record.response?.status || 0) + ': ' + record.assetPath)
      }
      const localPath = localAssetPath(record.assetPath)
      if (!existsSync(localPath)) throw new GateError('preview-asset-missing-local', 'local asset is missing: ' + record.assetPath)
      let payload
      try {
        payload = await this.cdp.send('Network.getResponseBody', { requestId: record.requestId })
      } catch {
        throw new GateError('preview-asset-body-unavailable', 'browser response body is unavailable: ' + record.assetPath, { blocked: true })
      }
      const servedBytes = Buffer.from(payload.body || '', payload.base64Encoded ? 'base64' : 'utf8')
      const localBytes = readFileSync(localPath)
      if (!servedBytes.equals(localBytes)) {
        throw new GateError('preview-asset-mismatch', 'measured navigation asset differs from local build: ' + record.assetPath)
      }
      if (
        record.assetPath.endsWith('.css')
        && servedBytes.includes(Buffer.from('.detail-body{max-width:var(--maxw);'))
        && servedBytes.includes(Buffer.from('.detail-main .lead'))
      ) {
        detailCssPaths.add(record.assetPath)
      }
      const previousBytes = uniqueAssets.get(record.assetPath)
      if (previousBytes && !servedBytes.equals(previousBytes)) {
        throw new GateError('preview-asset-inconsistent', 'duplicate asset responses differed: ' + record.assetPath)
      }
      uniqueAssets.set(record.assetPath, servedBytes)
    }
    if (detailCssPaths.size !== 1) {
      throw new GateError('detail-css-unbound', 'expected one Detail CSS response for the measured navigation, found ' + detailCssPaths.size)
    }
    const allAssetPaths = [...uniqueAssets.keys()].sort((left, right) => left.localeCompare(right))
    const cssPaths = allAssetPaths.filter(assetPath => assetPath.endsWith('.css'))
    const jsPaths = allAssetPaths.filter(assetPath => assetPath.endsWith('.js'))
    const assetPaths = [...cssPaths, ...jsPaths].sort((left, right) => left.localeCompare(right))
    if (cssPaths.length === 0 || jsPaths.length === 0) {
      throw new GateError('preview-asset-types-incomplete', 'measured navigation must bind both CSS and JavaScript assets')
    }
    const fingerprint = createHash('sha256')
    for (const assetPath of assetPaths) {
      fingerprint.update(assetPath)
      fingerprint.update('\0')
      fingerprint.update(uniqueAssets.get(assetPath))
      fingerprint.update('\0')
    }
    return {
      count: sorted.length,
      unique_count: allAssetPaths.length,
      supplemental_asset_count: allAssetPaths.length - assetPaths.length,
      asset_paths: assetPaths,
      css_paths: cssPaths,
      js_paths: jsPaths,
      detail_css_path: [...detailCssPaths][0],
      fingerprint_sha256: fingerprint.digest('hex'),
    }
  }
}

async function evaluate(cdp, expression) {
  const result = await cdp.send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
    userGesture: true,
  })
  if (result.exceptionDetails) throw new GateError('page-evaluation-failed', result.exceptionDetails.text || 'page evaluation failed')
  return result.result?.value
}

function callExpression(fn, arg) {
  return '(' + fn.toString() + ')(' + JSON.stringify(arg) + ')'
}

async function evaluateFunction(cdp, fn, arg = null) {
  return evaluate(cdp, callExpression(fn, arg))
}

async function waitForValue(cdp, fn, arg, predicate, message, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs
  let lastValue
  while (Date.now() < deadline) {
    lastValue = await evaluateFunction(cdp, fn, arg)
    if (predicate(lastValue)) return lastValue
    await sleep(100)
  }
  throw new GateError('page-state-timeout', message + '; last state: ' + JSON.stringify(lastValue ?? null).slice(0, 500))
}

async function setViewport(cdp, viewport) {
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: viewport.width,
    height: viewport.height,
    deviceScaleFactor: 1,
    mobile: viewport.mobile,
    screenWidth: viewport.width,
    screenHeight: viewport.height,
  })
}

async function navigate(cdp, url, assetCapture) {
  const previousDocument = await evaluateFunction(cdp, () => ({
    href: location.href,
    documentToken: String(globalThis.__vl360DetailGateDocumentToken || ''),
  }))
  const loaded = cdp.waitFor('Page.loadEventFired', 20000)
  const navigation = await cdp.send('Page.navigate', { url })
  if (navigation.errorText) throw new GateError('preview-unavailable', 'Detail navigation failed: ' + navigation.errorText, { blocked: true })
  if (!navigation.loaderId) throw new GateError('navigation-loader-unavailable', 'Detail navigation did not expose a loader ID', { blocked: true })
  assetCapture?.bind(navigation.loaderId)
  await loaded
  await waitForValue(
    cdp,
    () => {
      const visible = element => {
        if (!element) return false
        const rect = element.getBoundingClientRect()
        const style = getComputedStyle(element)
        return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden'
      }
      return {
        href: location.href,
        readyState: document.readyState,
        documentToken: String(globalThis.__vl360DetailGateDocumentToken || ''),
        nuxtRoot: Boolean(document.querySelector('#__nuxt')),
        detailBody: Boolean(document.querySelector('.detail-body')),
        detailMain: Boolean(document.querySelector('.detail-main')),
        detailAside: Boolean(document.querySelector('.detail-aside')),
        hero: visible(document.querySelector('.detail-cover')),
        photo: visible(document.querySelector('.dc-photo-btn')),
        dark: visible(document.querySelector('[data-theme-mode="dark"]')),
        light: visible(document.querySelector('[data-theme-mode="light"]')),
        onboardingSeen: localStorage.getItem('vl360_onboarding_seen') === '1',
        onboardingVisible: visible(document.querySelector('.onboarding-overlay')),
      }
    },
    null,
    value => isFreshNavigationState({
      expectedUrl: url,
      previousDocumentToken: previousDocument?.documentToken || '',
      href: value?.href,
      readyState: value?.readyState,
      documentToken: value?.documentToken,
    })
      && value?.nuxtRoot
      && value?.detailBody
      && value?.detailMain
      && value?.detailAside
      && value?.hero
      && value?.photo
      && value?.dark
      && value?.light
      && value?.onboardingSeen
      && !value?.onboardingVisible,
    'Detail page did not hydrate',
    20000,
  )
  await waitForValue(
    cdp,
    () => {
      const image = document.querySelector('.dc-bg')
      return {
        present: Boolean(image),
        loadedClass: Boolean(image?.classList.contains('loaded')),
        complete: Boolean(image?.complete),
        naturalWidth: Number(image?.naturalWidth || 0),
      }
    },
    null,
    value => value?.present && value?.loadedClass && value?.complete && value?.naturalWidth > 0,
    'Detail hero image did not reach its stable loaded state',
    20000,
  )
  await sleep(250)
}

async function navigateWithBoundAssets(cdp, baseUrl) {
  const blankLoaded = cdp.waitFor('Page.loadEventFired', 10000)
  const blankNavigation = await cdp.send('Page.navigate', { url: 'about:blank' })
  if (blankNavigation.errorText) throw new GateError('navigation-reset-failed', 'could not reset the measured document: ' + blankNavigation.errorText, { blocked: true })
  await blankLoaded
  await waitForValue(
    cdp,
    () => ({ href: location.href, readyState: document.readyState }),
    null,
    value => value?.href === 'about:blank' && value?.readyState === 'complete',
    'browser document reset did not complete',
    10000,
  )
  await cdp.send('Network.clearBrowserCache')
  const capture = new NavigationAssetCapture(cdp, baseUrl)
  capture.start()
  try {
    await navigate(cdp, new URL(ROUTE, baseUrl).toString(), capture)
    return await capture.verify()
  } finally {
    capture.stop()
  }
}

async function elementRect(cdp, selector) {
  return evaluateFunction(cdp, value => {
    const element = document.querySelector(value)
    if (!element) return null
    element.scrollIntoView({ block: 'center', inline: 'center' })
    const rect = element.getBoundingClientRect()
    return {
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height,
      left: rect.left,
      right: rect.right,
      top: rect.top,
      bottom: rect.bottom,
      centerX: rect.left + rect.width / 2,
      centerY: rect.top + rect.height / 2,
    }
  }, selector)
}

async function physicalClick(cdp, selector) {
  const rect = await elementRect(cdp, selector)
  if (!rect || rect.width <= 0 || rect.height <= 0) {
    throw new GateError('target-not-visible', 'physical click target is not visible: ' + selector)
  }
  await sleep(50)
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: rect.centerX, y: rect.centerY })
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: rect.centerX, y: rect.centerY, button: 'left', buttons: 1, clickCount: 1 })
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: rect.centerX, y: rect.centerY, button: 'left', buttons: 0, clickCount: 1 })
  return rect
}

async function hitTarget(cdp, selector, index = 0) {
  await evaluateFunction(cdp, ({ selector: targetSelector, index: targetIndex }) => {
    const element = document.querySelectorAll(targetSelector)[targetIndex]
    element?.scrollIntoView({ block: 'center', inline: 'center' })
    return Boolean(element)
  }, { selector, index })
  await sleep(100)
  return evaluateFunction(cdp, ({ selector: targetSelector, index: targetIndex }) => {
    const element = document.querySelectorAll(targetSelector)[targetIndex]
    if (!element) return { present: false, visible: false, belongs: false, tag: '', text: '' }
    const rect = element.getBoundingClientRect()
    const style = getComputedStyle(element)
    const visible = rect.width > 0
      && rect.height > 0
      && style.display !== 'none'
      && style.visibility !== 'hidden'
      && rect.bottom > 0
      && rect.top < innerHeight
      && rect.right > 0
      && rect.left < innerWidth
    const target = visible ? document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2) : null
    const describe = candidate => candidate
      ? candidate.tagName.toLowerCase()
        + (candidate.id ? '#' + candidate.id : '')
        + (candidate.classList.length ? '.' + [...candidate.classList].slice(0, 3).join('.') : '')
      : ''
    return {
      present: true,
      visible,
      belongs: Boolean(target && (target === element || element.contains(target))),
      tag: describe(target),
      text: String(element.textContent || '').trim().slice(0, 60),
    }
  }, { selector, index })
}

async function exerciseLightbox(cdp) {
  const evidence = {
    opened: false,
    aria_modal: false,
    dialog_rect: null,
    surface_visible: false,
    media_visible: false,
    close_hit: { present: false, visible: false, belongs: false, tag: '', text: '' },
    closed: false,
  }
  await physicalClick(cdp, '.dc-photo-btn')
  try {
    const opened = await waitForValue(
      cdp,
      () => {
        const visible = element => {
          if (!element) return false
          const rect = element.getBoundingClientRect()
          const style = getComputedStyle(element)
          return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden'
        }
        const dialog = document.querySelector('[role="dialog"][aria-label="Xem ảnh"]')
        const surface = dialog?.querySelector('[data-image-surface="image-lightbox"]')
        const media = dialog?.querySelector('[data-active-media]')
        const dialogRect = dialog?.getBoundingClientRect()
        const mediaReady = media?.matches('img')
          ? Boolean(media.complete && media.naturalWidth > 0 && media.naturalHeight > 0)
          : Boolean(media?.matches('[data-placeholder-media="true"]'))
        return {
          opened: Boolean(dialog),
          ariaModal: dialog?.getAttribute('aria-modal') === 'true',
          dialogRect: dialogRect ? {
            width: dialogRect.width,
            height: dialogRect.height,
            left: dialogRect.left,
            right: dialogRect.right,
            top: dialogRect.top,
            bottom: dialogRect.bottom,
          } : null,
          surfaceVisible: visible(surface),
          mediaVisible: visible(media) && mediaReady,
        }
      },
      null,
      value => value?.opened && value?.ariaModal && value?.surfaceVisible && value?.mediaVisible,
      'Detail photo action did not open a stable lightbox',
      8000,
    )
    evidence.opened = opened.opened
    evidence.aria_modal = opened.ariaModal
    evidence.dialog_rect = roundedRect(opened.dialogRect)
    evidence.surface_visible = opened.surfaceVisible
    evidence.media_visible = opened.mediaVisible
  } catch (error) {
    if (!(error instanceof GateError) || error.code !== 'page-state-timeout') throw error
    return evidence
  }

  await sleep(250)
  evidence.close_hit = await hitTarget(cdp, '.lb-close')
  if (!evidence.close_hit.present || !evidence.close_hit.visible) return evidence
  await physicalClick(cdp, '.lb-close')
  try {
    await waitForValue(
      cdp,
      () => !document.querySelector('[role="dialog"][aria-label="Xem ảnh"]'),
      null,
      Boolean,
      'Detail lightbox did not close',
      5000,
    )
    evidence.closed = true
  } catch (error) {
    if (!(error instanceof GateError) || error.code !== 'page-state-timeout') throw error
  }
  return evidence
}

async function injectMutation(cdp, mutation) {
  if (!mutation) return null
  return evaluateFunction(cdp, mutationId => {
    const sourceGuardPresent = (() => {
      const hasGuard = rules => {
        for (const rule of rules || []) {
          if (
            rule.style
            && String(rule.selectorText || '').split(',').some(selector => selector.trim() === '.detail-main')
            && ['0', '0px'].includes(rule.style.getPropertyValue('min-width').trim())
          ) {
            return true
          }
          if (rule.cssRules && hasGuard(rule.cssRules)) return true
        }
        return false
      }
      for (const sheet of document.styleSheets) {
        try {
          if (hasGuard(sheet.cssRules)) return true
        } catch {
          // Same-origin production assets are readable; ignore unrelated sheets.
        }
      }
      return false
    })()
    const selector = '.detail-main'
    const style = document.createElement('style')
    style.id = 'detail-grid-containment-mutation'
    style.textContent = selector + ' { min-width: auto !important; }'
    document.head.append(style)
    const main = document.querySelector(selector)
    const rule = style.sheet?.cssRules?.[0]
    return {
      id: mutationId,
      selector_matches: Boolean(main?.matches(selector)),
      rule_selector: rule?.selectorText || '',
      declared_min_width: rule?.style?.getPropertyValue('min-width') || '',
      declared_priority: rule?.style?.getPropertyPriority('min-width') || '',
      computed_min_width: main ? getComputedStyle(main).minWidth : '',
      source_guard_present: sourceGuardPresent,
    }
  }, mutation)
}

function assertMutationApplied(mutation, requestedMutation) {
  if (!requestedMutation) return
  const failures = []
  if (!mutation?.selector_matches) failures.push('selector did not match')
  if (mutation?.rule_selector !== '.detail-main') failures.push('rule selector differs')
  if (mutation?.declared_min_width !== 'auto' || mutation?.declared_priority !== 'important') {
    failures.push('min-width:auto !important is absent')
  }
  if (mutation?.computed_min_width !== 'auto') failures.push('computed min-width is not auto')
  if (!mutation?.source_guard_present) failures.push('production min-width:0 declaration is absent')
  if (failures.length > 0) throw new GateError('mutation-not-applied', failures.join('; '))
}

function rounded(value) {
  return Math.round(value * 100) / 100
}

function roundedRect(rect) {
  if (!rect) return null
  return Object.fromEntries(Object.entries(rect).map(([key, value]) => [key, rounded(value)]))
}

function intersectionRect(a, b) {
  const left = Math.max(a.left, b.left)
  const right = Math.min(a.right, b.right)
  const top = Math.max(a.top, b.top)
  const bottom = Math.min(a.bottom, b.bottom)
  const width = Math.max(0, right - left)
  const height = Math.max(0, bottom - top)
  return { width: rounded(width), height: rounded(height), area: rounded(width * height) }
}

async function selectTheme(cdp, mode) {
  await physicalClick(cdp, '[data-theme-mode="' + mode + '"]')
  return waitForValue(
    cdp,
    selectedMode => ({
      pressed: document.querySelector('[data-theme-mode="' + selectedMode + '"]')?.getAttribute('aria-pressed') === 'true',
      className: document.documentElement.className,
      stored: localStorage.getItem('vl360-color-mode'),
    }),
    mode,
    value => value?.pressed
      && value?.stored === mode
      && String(value?.className || '').split(/\s+/u).includes(mode),
    'theme ' + mode + ' did not become active after physical click',
  )
}

async function measureGeometry(cdp) {
  return evaluateFunction(cdp, () => {
    const rect = element => {
      if (!element) return null
      const value = element.getBoundingClientRect()
      return {
        x: value.x,
        y: value.y,
        width: value.width,
        height: value.height,
        left: value.left,
        right: value.right,
        top: value.top,
        bottom: value.bottom,
      }
    }
    const metric = element => {
      if (!element) return null
      const style = getComputedStyle(element)
      return {
        rect: rect(element),
        client_width: element.clientWidth,
        scroll_width: element.scrollWidth,
        overflow_px: Math.max(0, element.scrollWidth - element.clientWidth),
        min_width: style.minWidth,
        overflow_x: style.overflowX,
        white_space: style.whiteSpace,
        display: style.display,
        position: style.position,
        visibility: style.visibility,
      }
    }
    const hit = element => {
      const value = rect(element)
      if (!element || !value || value.width <= 0 || value.height <= 0) return { belongs: false, tag: '' }
      const target = document.elementFromPoint(value.left + value.width / 2, value.top + value.height / 2)
      const describe = candidate => candidate
        ? candidate.tagName.toLowerCase()
          + (candidate.id ? '#' + candidate.id : '')
          + (candidate.classList.length ? '.' + [...candidate.classList].slice(0, 3).join('.') : '')
        : ''
      return { belongs: Boolean(target && (target === element || element.contains(target))), tag: describe(target) }
    }

    const detailBody = document.querySelector('.detail-body')
    const main = document.querySelector('.detail-main')
    const lead = document.querySelector('.detail-main .lead')
    const description = document.querySelector('.entity-description')
    const aside = document.querySelector('.detail-aside')
    const trust = document.querySelector('[data-entity-trust-panel]')
    const cover = document.querySelector('.detail-cover')
    const heroImage = document.querySelector('.dc-bg')
    const trip = document.querySelector('.dc-trip')
    const photo = document.querySelector('.dc-photo-btn')
    const contact = document.querySelector('.detail-contact-widget')
    const contactControls = [...document.querySelectorAll('.detail-contact-widget .cw-btn')].slice(0, 4)
    const tripControls = [...document.querySelectorAll('.dc-trip .trip-btn')].slice(0, 4)
    const sticky = document.querySelector('.sticky-cta-bar')
    const root = document.documentElement
    const coverRect = rect(cover)
    const imageRect = rect(heroImage)
    const bodyRect = rect(detailBody)
    const mainRect = rect(main)
    const leadRect = rect(lead)
    const descriptionRect = rect(description)
    const asideRect = rect(aside)
    const trustRect = rect(trust)
    const tripRect = rect(trip)
    const photoRect = rect(photo)
    const within = (inner, outer) => Boolean(
      inner
      && outer
      && inner.left >= outer.left - 1
      && inner.right <= outer.right + 1
    )

    return {
      viewport: { width: innerWidth, height: innerHeight, root_client_width: root.clientWidth },
      class_name: document.documentElement.className,
      grid_template_columns: detailBody ? getComputedStyle(detailBody).gridTemplateColumns : '',
      detail_body: metric(detailBody),
      main: metric(main),
      lead: metric(lead),
      description: metric(description),
      aside: metric(aside),
      trust: metric(trust),
      containment: {
        main_in_body: within(mainRect, bodyRect),
        lead_in_body: within(leadRect, bodyRect),
        description_in_body: within(descriptionRect, bodyRect),
        aside_in_body: within(asideRect, bodyRect),
        trust_in_body: within(trustRect, bodyRect),
      },
      page_overflow_px: Math.max(0, Math.max(root.scrollWidth, document.body?.scrollWidth || 0) - root.clientWidth),
      hero: {
        cover_rect: coverRect,
        image_rect: imageRect,
        image_loaded_class: Boolean(heroImage?.classList.contains('loaded')),
        image_complete: Boolean(heroImage?.complete),
        image_natural_width: Number(heroImage?.naturalWidth || 0),
        image_natural_height: Number(heroImage?.naturalHeight || 0),
        image_src: String(heroImage?.currentSrc || heroImage?.getAttribute('src') || '').slice(0, 240),
        image_in_cover: within(imageRect, coverRect),
      },
      actions: {
        trip_rect: tripRect,
        photo_rect: photoRect,
        trip_photo_intersection: tripRect && photoRect ? {
          left: Math.max(tripRect.left, photoRect.left),
          right: Math.min(tripRect.right, photoRect.right),
          top: Math.max(tripRect.top, photoRect.top),
          bottom: Math.min(tripRect.bottom, photoRect.bottom),
        } : null,
        photo_hit: hit(photo),
        trip_hits: tripControls.map(control => ({ text: String(control.textContent || '').trim().slice(0, 40), ...hit(control) })),
      },
      contact: {
        metric: metric(contact),
        controls: contactControls.map(control => ({ text: String(control.textContent || '').trim().slice(0, 50), metric: metric(control), hit: hit(control) })),
      },
      sticky: metric(sticky),
    }
  })
}

function normalizeGeometry(geometry) {
  for (const key of ['detail_body', 'main', 'lead', 'description', 'aside', 'trust', 'sticky']) {
    if (geometry[key]?.rect) geometry[key].rect = roundedRect(geometry[key].rect)
    if (geometry[key]) {
      geometry[key].client_width = rounded(geometry[key].client_width)
      geometry[key].scroll_width = rounded(geometry[key].scroll_width)
      geometry[key].overflow_px = rounded(geometry[key].overflow_px)
    }
  }
  geometry.viewport = Object.fromEntries(Object.entries(geometry.viewport).map(([key, value]) => [key, rounded(value)]))
  geometry.page_overflow_px = rounded(geometry.page_overflow_px)
  geometry.hero.cover_rect = roundedRect(geometry.hero.cover_rect)
  geometry.hero.image_rect = roundedRect(geometry.hero.image_rect)
  geometry.actions.trip_rect = roundedRect(geometry.actions.trip_rect)
  geometry.actions.photo_rect = roundedRect(geometry.actions.photo_rect)
  const rawIntersection = geometry.actions.trip_photo_intersection
  geometry.actions.trip_photo_intersection = rawIntersection
    ? intersectionRect(geometry.actions.trip_rect, geometry.actions.photo_rect)
    : null
  if (geometry.contact.metric?.rect) geometry.contact.metric.rect = roundedRect(geometry.contact.metric.rect)
  for (const control of geometry.contact.controls) {
    if (control.metric?.rect) control.metric.rect = roundedRect(control.metric.rect)
    if (control.metric) {
      control.metric.client_width = rounded(control.metric.client_width)
      control.metric.scroll_width = rounded(control.metric.scroll_width)
      control.metric.overflow_px = rounded(control.metric.overflow_px)
    }
  }
  return geometry
}

function assertState(evidence, state, geometry) {
  const mobile = state.viewport_name === 'mobile'
  const body = geometry.detail_body
  const main = geometry.main
  const lead = geometry.lead
  const description = geometry.description
  const aside = geometry.aside
  const trust = geometry.trust

  if (!body || body.overflow_px > TOLERANCE_PX) {
    stateReason(evidence, state, 'detail-body-overflow', 'Detail body inner overflow is ' + (body?.overflow_px ?? 'missing') + 'px')
  }
  if (!main || main.overflow_px > TOLERANCE_PX) {
    stateReason(evidence, state, 'detail-main-overflow', 'Detail main content overflow is ' + (main?.overflow_px ?? 'missing') + 'px')
  }
  if (!lead || lead.overflow_px > TOLERANCE_PX) {
    stateReason(evidence, state, 'lead-overflow', 'lead content overflow is ' + (lead?.overflow_px ?? 'missing') + 'px')
  }
  if (!description || description.overflow_px > TOLERANCE_PX) {
    stateReason(evidence, state, 'description-overflow', 'description content overflow is ' + (description?.overflow_px ?? 'missing') + 'px')
  }
  if (geometry.page_overflow_px > TOLERANCE_PX) {
    stateReason(evidence, state, 'page-overflow', 'page overflows horizontally by ' + geometry.page_overflow_px + 'px')
  }
  for (const [name, contained] of Object.entries(geometry.containment)) {
    if (!contained) stateReason(evidence, state, name.replaceAll('_', '-'), name + ' is false')
  }
  for (const [name, metric] of [['main', main], ['lead', lead], ['description', description]]) {
    if (metric && ['hidden', 'clip'].includes(metric.overflow_x)) {
      stateReason(evidence, state, name + '-clipped', name + ' uses overflow-x:' + metric.overflow_x)
    }
    if (metric?.white_space === 'nowrap') {
      stateReason(evidence, state, name + '-nowrap', name + ' prevents normal text wrapping')
    }
  }

  if (mobile) {
    if (main?.min_width !== '0px') stateReason(evidence, state, 'main-shrink-guard', 'mobile main min-width is ' + (main?.min_width || 'missing'))
    if (geometry.grid_template_columns.trim().split(/\s+/u).length !== 1) {
      stateReason(evidence, state, 'mobile-grid-columns', 'mobile grid columns are ' + geometry.grid_template_columns)
    }
  } else {
    const mainRect = main?.rect
    const asideRect = aside?.rect
    const gridColumns = geometry.grid_template_columns.trim().split(/\s+/u)
    if (gridColumns.length !== 2) {
      stateReason(evidence, state, 'desktop-grid-columns', 'desktop grid columns are ' + geometry.grid_template_columns)
    }
    if (!mainRect || !asideRect || asideRect.left <= mainRect.right || mainRect.width <= asideRect.width) {
      stateReason(evidence, state, 'desktop-layout', 'desktop main/sidebar layout is not two separated columns')
    }
  }
}

function consoleEntry(params, baseUrl) {
  if (params.entry?.level === 'error') {
    const source = String(params.entry.source || 'log')
    const message = String(params.entry.text || '').trim()
    const url = String(params.entry.url || '')
    let allowedReason = ''
    try {
      const parsed = new URL(url)
      if (
        source === 'network'
        && parsed.origin === new URL(baseUrl).origin
        && parsed.pathname === '/auth/me'
        && !parsed.search
        && /^Failed to load resource: the server responded with a status of 503 \(Service Unavailable\)$/u.test(message)
      ) {
        allowedReason = 'sqlite-lightweight-auth-me-503'
      }
    } catch {
      // Non-URL console entries never receive the narrow QA-backend allowance.
    }
    return { source, message: safeMessage(message), url: url ? safeMessage(url) : '', allowed_reason: allowedReason }
  }
  if (params.message?.level === 'error') {
    return { source: 'console', message: safeMessage(params.message.text || ''), url: '', allowed_reason: '' }
  }
  if (params.exceptionDetails) {
    return {
      source: 'exception',
      message: safeMessage(params.exceptionDetails.exception?.description || params.exceptionDetails.text || 'uncaught exception'),
      url: '',
      allowed_reason: '',
    }
  }
  return null
}

async function exerciseState({ cdp, baseUrl, mutation, consoleErrors, evidence, config }) {
  const state = {
    viewport_name: config.viewport_name,
    viewport: { width: config.viewport.width, height: config.viewport.height },
    theme: config.theme,
    requested_mode: config.mode,
    selected_mode: '',
    preview_assets: {
      count: 0,
      unique_count: 0,
      asset_paths: [],
      css_paths: [],
      js_paths: [],
      detail_css_path: '',
      fingerprint_sha256: '',
    },
    mutation: null,
    geometry: null,
    lightbox: null,
    console_errors: [],
    relevant_console_errors: [],
    failures: [],
  }
  const consoleStart = consoleErrors.length
  await setViewport(cdp, config.viewport)
  state.preview_assets = await navigateWithBoundAssets(cdp, baseUrl)
  evidence.preconditions.onboarding_seen_seeded = true
  state.mutation = await injectMutation(cdp, mutation)
  assertMutationApplied(state.mutation, mutation)
  const themeState = await selectTheme(cdp, config.mode)
  state.selected_mode = themeState.stored
  state.geometry = normalizeGeometry(await measureGeometry(cdp))
  state.geometry.actions.photo_hit = await hitTarget(cdp, '.dc-photo-btn')
  const tripControlCount = await evaluateFunction(cdp, () => document.querySelectorAll('.dc-trip .trip-btn').length)
  state.geometry.actions.trip_hits = []
  for (let index = 0; index < tripControlCount; index += 1) {
    state.geometry.actions.trip_hits.push(await hitTarget(cdp, '.dc-trip .trip-btn', index))
  }
  state.lightbox = await exerciseLightbox(cdp)
  const contactControlCount = await evaluateFunction(cdp, () => document.querySelectorAll('.detail-contact-widget .cw-btn').length)
  state.geometry.contact.controls = []
  for (let index = 0; index < contactControlCount; index += 1) {
    state.geometry.contact.controls.push({ hit: await hitTarget(cdp, '.detail-contact-widget .cw-btn', index) })
  }
  await sleep(CONSOLE_DRAIN_MS)
  state.console_errors = consoleErrors.slice(consoleStart, consoleStart + MAX_CONSOLE_ERRORS)
  state.relevant_console_errors = state.console_errors.filter(entry => !entry.allowed_reason)
  assertState(evidence, state, state.geometry)
  for (const failure of collectStateFailures(state)) {
    stateReason(evidence, state, failure.code, failure.message)
  }
  return state
}

function boundedJson(evidence) {
  let json = JSON.stringify(evidence, null, 2) + '\n'
  if (Buffer.byteLength(json) <= MAX_EVIDENCE_BYTES) return json
  compactGateEvidence(evidence)
  json = JSON.stringify(evidence, null, 2) + '\n'
  if (Buffer.byteLength(json) > MAX_EVIDENCE_BYTES) throw new Error('bounded evidence exceeded byte limit')
  return json
}

async function run(args, evidence) {
  evidence.manifest_revision = readManifest()
  if (evidence.manifest_revision !== args.expectedRevision) {
    throw new GateError(
      'revision-mismatch',
      'manifest revision ' + evidence.manifest_revision + ' does not match expected revision ' + args.expectedRevision,
    )
  }
  let chrome
  let cdp
  try {
    chrome = await launchChrome()
    const pageUrl = await createPageTarget(chrome.endpoint.port)
    cdp = new CdpClient(pageUrl)
    await cdp.connect()
    const consoleErrors = []
    const recordConsole = params => {
      const entry = consoleEntry(params, args.baseUrl)
      if (!entry || consoleErrors.length >= MAX_CONSOLE_ERRORS * STATE_CONFIGS.length * 2) return
      if (!consoleErrors.some(candidate => JSON.stringify(candidate) === JSON.stringify(entry))) consoleErrors.push(entry)
    }
    cdp.on('Log.entryAdded', recordConsole)
    cdp.on('Console.messageAdded', recordConsole)
    cdp.on('Runtime.exceptionThrown', recordConsole)
    await Promise.all([
      cdp.send('Page.enable'),
      cdp.send('Runtime.enable'),
      cdp.send('Log.enable'),
      cdp.send('Console.enable'),
      cdp.send('Network.enable'),
      cdp.send('Network.setCacheDisabled', { cacheDisabled: true }),
    ])
    await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
      source: "globalThis.__vl360DetailGateDocumentToken = (globalThis.crypto?.randomUUID?.() || (Date.now() + ':' + Math.random())); if (location.origin === "
        + JSON.stringify(new URL(args.baseUrl).origin)
        + ") localStorage.setItem('vl360_onboarding_seen', '1')",
    })
    for (const config of STATE_CONFIGS) {
      evidence.states.push(await exerciseState({
        cdp,
        baseUrl: args.baseUrl,
        mutation: args.mutation,
        consoleErrors,
        evidence,
        config,
      }))
    }
    const detailCssPaths = [...new Set(evidence.states.map(state => state.preview_assets.detail_css_path).filter(Boolean))]
    const allStatesBound = evidence.states.every(state => (
      state.preview_assets.count > 0
      && state.preview_assets.unique_count > 0
      && state.preview_assets.asset_paths.length > 0
      && state.preview_assets.css_paths.length > 0
      && state.preview_assets.js_paths.length > 0
      && Boolean(state.preview_assets.detail_css_path)
      && /^[a-f0-9]{64}$/u.test(state.preview_assets.fingerprint_sha256)
    ))
    const aggregateFingerprint = createHash('sha256')
    for (const state of evidence.states) {
      aggregateFingerprint.update(state.viewport_name)
      aggregateFingerprint.update('\0')
      aggregateFingerprint.update(state.theme)
      aggregateFingerprint.update('\0')
      aggregateFingerprint.update(state.preview_assets.fingerprint_sha256)
      aggregateFingerprint.update('\0')
    }
    evidence.preview_assets = {
      state_count: evidence.states.length,
      all_states_bound: allStatesBound,
      detail_css_path: detailCssPaths.length === 1 ? detailCssPaths[0] : '',
      asset_paths: evidence.states[0]?.preview_assets.asset_paths || [],
      asset_groups: Object.fromEntries([...new Set(evidence.states.map(state => state.viewport_name))].map(viewportName => {
        const state = evidence.states.find(candidate => candidate.viewport_name === viewportName)
        return [viewportName, {
          state_count: evidence.states.filter(candidate => candidate.viewport_name === viewportName).length,
          asset_paths: state?.preview_assets.asset_paths || [],
          fingerprint_sha256: state?.preview_assets.fingerprint_sha256 || '',
        }]
      })),
      aggregate_fingerprint_sha256: aggregateFingerprint.digest('hex'),
    }
    if (detailCssPaths.length !== 1) addReason(evidence, 'detail-css-state-mismatch', 'states did not bind one shared Detail CSS asset')
    for (const failure of collectAssetSetFailures(evidence.states)) addReason(evidence, failure.code, failure.message)
  } finally {
    cdp?.close()
    if (chrome?.child) {
      try {
        await stopChrome(chrome.child)
      } catch (error) {
        evidence.cleanup_errors.push('chrome:' + safeMessage(error))
      }
    }
    if (chrome?.profile && chrome?.browserPath) {
      try {
        const remaining = await waitForOwnedBrowserExit(chrome)
        evidence.cleanup.owned_processes_remaining = remaining.map(processInfo => processInfo.pid)
        if (remaining.length > 0) {
          evidence.cleanup_errors.push('owned-processes:' + remaining.map(processInfo => processInfo.pid).join(','))
        }
      } catch (error) {
        evidence.cleanup_errors.push('owned-process-audit:' + safeMessage(error))
      }
    }
    if (chrome?.profile) {
      try {
        await rm(chrome.profile, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 })
        evidence.cleanup.profile_removed = !existsSync(chrome.profile)
        if (!evidence.cleanup.profile_removed) evidence.cleanup_errors.push('profile:owned profile still exists after removal')
      } catch (error) {
        evidence.cleanup_errors.push('profile:' + safeMessage(error))
      }
    }
  }
  if (evidence.cleanup_errors.length > 0) addReason(evidence, 'cleanup-failed', 'owned Chrome resources were not fully cleaned up')
  evidence.verdict = evidence.reasons.length === 0 && evidence.cleanup_errors.length === 0 ? 'pass' : 'fail'
}

let args
try {
  args = parseArgs(process.argv.slice(2))
} catch (error) {
  const evidence = {
    schema_version: 1,
    gate: 'detail-grid-containment',
    verdict: error instanceof GateError && error.blocked ? 'blocked' : 'fail',
    expected_revision: '',
    manifest_revision: '',
    route: ROUTE,
    mutation: '',
    preconditions: { onboarding_seen_seeded: false },
    preview_assets: { state_count: 0, all_states_bound: false, detail_css_path: '', asset_paths: [], asset_groups: {}, aggregate_fingerprint_sha256: '' },
    states: [],
    reasons: [{ code: error instanceof GateError ? error.code : 'unexpected-error', message: safeMessage(error) }],
    cleanup: { owned_processes_remaining: null, profile_removed: false },
    cleanup_errors: [],
  }
  process.stdout.write(boundedJson(evidence))
  process.exitCode = 1
}

if (args?.help) {
  process.stdout.write(usage())
} else if (args) {
  const evidence = {
    schema_version: 1,
    gate: 'detail-grid-containment',
    verdict: 'blocked',
    expected_revision: args.expectedRevision,
    manifest_revision: '',
    route: ROUTE,
    mutation: args.mutation,
    preconditions: { onboarding_seen_seeded: false },
    preview_assets: { state_count: 0, all_states_bound: false, detail_css_path: '', asset_paths: [], asset_groups: {}, aggregate_fingerprint_sha256: '' },
    states: [],
    reasons: [],
    cleanup: { owned_processes_remaining: null, profile_removed: false },
    cleanup_errors: [],
  }
  try {
    await run(args, evidence)
  } catch (error) {
    evidence.verdict = error instanceof GateError && error.blocked ? 'blocked' : 'fail'
    addReason(evidence, error instanceof GateError ? error.code : 'unexpected-error', safeMessage(error))
  }
  process.stdout.write(boundedJson(evidence))
  process.exitCode = evidence.verdict === 'pass' ? 0 : 1
}
