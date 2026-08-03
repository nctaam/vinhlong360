#!/usr/bin/env node

import { spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, readFileSync } from 'node:fs'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const VIEWPORT = Object.freeze({ width: 390, height: 844 })
const QUERY = 'dừa'
const EXPECTED_LOCATION = '/tim-kiem?q=d%E1%BB%ABa'
const REVISION_PATTERN = /^[a-f0-9]{40}$/u
const SEARCH_CSS_PATTERN = /^\/_nuxt\/tim-kiem\.[A-Za-z0-9_-]+\.css$/u
const MAX_CONSOLE_ERRORS = 10
const MAX_REASONS = 20
const MAX_EVIDENCE_BYTES = 16 * 1024
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
  return `Usage: node scripts/check-search-mobile-hit-target.mjs --base-url <url> --expected-revision <sha>

Required:
  --base-url <url>             Production preview origin
  --expected-revision <sha>    Reviewed lowercase 40-hex source revision

Mutation proof:
  --mutation legacy-auto-width Inject the reviewed later-cascade regression fixture
`
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
      if (!value || value.startsWith('--')) throw new GateError('invalid-arguments', `${flag} requires a value`)
      index += 1
      if (flag === '--base-url') args.baseUrl = value
      else if (flag === '--expected-revision') args.expectedRevision = value
      else args.mutation = value
      continue
    }
    throw new GateError('invalid-arguments', `unknown option: ${flag}`)
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
  if (args.mutation && args.mutation !== 'legacy-auto-width') {
    throw new GateError('invalid-mutation', 'mutation must be legacy-auto-width')
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
  return new Promise(resolve => setTimeout(resolve, ms))
}

function addReason(evidence, code, message) {
  if (evidence.reasons.length >= MAX_REASONS) return
  evidence.reasons.push({ code: String(code).slice(0, 80), message: String(message).slice(0, 300) })
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
  const candidate = resolve(outputPublicRoot, `.${assetPath}`)
  const prefix = `${outputPublicRoot}${sep}`.toLowerCase()
  if (!candidate.toLowerCase().startsWith(prefix)) throw new GateError('asset-path-invalid', 'preview asset path escaped output root')
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
    await new Promise((resolveKill, reject) => {
      const killer = spawn(process.env.ComSpec || 'cmd.exe', ['/d', '/s', '/c', `taskkill /PID ${child.pid} /T /F`], {
        stdio: 'ignore',
        windowsHide: true,
      })
      killer.once('error', reject)
      killer.once('exit', code => code === 0 ? resolveKill() : reject(new Error(`taskkill exited with code ${code}`)))
    })
  } else {
    child.kill('SIGTERM')
  }
  if (!(await waitForExit(child, 5000))) {
    child.kill('SIGKILL')
    if (!(await waitForExit(child, 1000))) throw new Error('Chrome did not exit after cleanup')
  }
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
  const profile = await mkdtemp(resolve(tmpdir(), 'vl360-search-hit-target-'))
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
      `--user-data-dir=${profile}`,
      `--window-size=${VIEWPORT.width},${VIEWPORT.height}`,
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
        output = `${output}${String(chunk)}`.slice(-16384)
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
    return { child, endpoint, profile }
  } catch (error) {
    const cleanupErrors = []
    try { await stopChrome(child) } catch (cleanupError) { cleanupErrors.push(`chrome:${safeMessage(cleanupError)}`) }
    try {
      await rm(profile, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 })
    } catch (cleanupError) {
      cleanupErrors.push(`profile:${safeMessage(cleanupError)}`)
    }
    if (cleanupErrors.length > 0) {
      throw new GateError(
        'chrome-start-cleanup-failed',
        `${safeMessage(error)}; ${cleanupErrors.join('; ')}`,
        { blocked: true },
      )
    }
    throw error
  }
}

async function createPageTarget(port) {
  const endpoint = `http://127.0.0.1:${port}/json/new?about:blank`
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
    if (typeof WebSocket === 'undefined') throw new GateError('node-websocket-unavailable', 'Node WebSocket support is unavailable', { blocked: true })
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
        reject(new GateError('cdp-timeout', `CDP timeout: ${method}`, { blocked: true }))
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
        reject(new GateError('cdp-event-timeout', `CDP event timeout: ${method}`, { blocked: true }))
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
        record.response = {
          status: params.response?.status || 0,
          url: params.response?.url || '',
        }
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
    if (!loaderId) throw new GateError('navigation-loader-unavailable', 'Search navigation did not expose a loader ID', { blocked: true })
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
    throw new GateError('preview-assets-timeout', 'Search navigation assets did not finish loading', { blocked: true })
  }

  async verify() {
    const records = await this.waitForSettled()
    const failed = records.find(record => record.failed)
    if (failed) {
      throw new GateError('preview-asset-unavailable', `served asset failed to load: ${failed.assetPath} (${failed.failed})`, { blocked: true })
    }
    const searchCss = records.filter(record => SEARCH_CSS_PATTERN.test(record.assetPath))
    if (searchCss.length !== 1) {
      throw new GateError('search-css-unbound', `expected one Search CSS response for the measured navigation, found ${searchCss.length}`)
    }
    const sorted = records.sort((left, right) => left.assetPath.localeCompare(right.assetPath) || left.requestId.localeCompare(right.requestId))
    const fingerprint = createHash('sha256')
    for (const record of sorted) {
      if (!record.response || record.response.status < 200 || record.response.status >= 300) {
        throw new GateError('preview-asset-unavailable', `served asset returned ${record.response?.status || 0}: ${record.assetPath}`)
      }
      const localPath = localAssetPath(record.assetPath)
      if (!existsSync(localPath)) throw new GateError('preview-asset-missing-local', `local asset is missing: ${record.assetPath}`)
      let payload
      try {
        payload = await this.cdp.send('Network.getResponseBody', { requestId: record.requestId })
      } catch {
        throw new GateError('preview-asset-body-unavailable', `browser response body is unavailable: ${record.assetPath}`, { blocked: true })
      }
      const servedBytes = Buffer.from(payload.body || '', payload.base64Encoded ? 'base64' : 'utf8')
      const localBytes = readFileSync(localPath)
      if (!servedBytes.equals(localBytes)) {
        throw new GateError('preview-asset-mismatch', `measured navigation asset differs from local build: ${record.assetPath}`)
      }
      fingerprint.update(record.assetPath)
      fingerprint.update('\0')
      fingerprint.update(servedBytes)
      fingerprint.update('\0')
    }
    return {
      count: sorted.length,
      unique_count: new Set(sorted.map(record => record.assetPath)).size,
      search_css_path: searchCss[0].assetPath,
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

async function waitForValue(cdp, expression, predicate, message, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs
  let lastValue
  while (Date.now() < deadline) {
    lastValue = await evaluate(cdp, expression)
    if (predicate(lastValue)) return lastValue
    await sleep(100)
  }
  const diagnostic = JSON.stringify(lastValue ?? null).slice(0, 500)
  throw new GateError('page-state-timeout', `${message}; last state: ${diagnostic}`)
}

async function navigate(cdp, url, assetCapture) {
  const loaded = cdp.waitFor('Page.loadEventFired', 20000).catch(() => undefined)
  const navigation = await cdp.send('Page.navigate', { url })
  if (navigation.errorText) throw new GateError('preview-unavailable', `Search navigation failed: ${navigation.errorText}`, { blocked: true })
  assetCapture?.bind(navigation.loaderId)
  await loaded
  await waitForValue(
    cdp,
    `(() => {
      const visible = element => {
        if (!element || element.disabled) return false;
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
      };
      const input = document.querySelector('.search-row-hero input[type="search"]');
      const button = document.querySelector('[data-color-role="action-primary"]');
      const dark = document.querySelector('[data-theme-mode="dark"]');
      const light = document.querySelector('[data-theme-mode="light"]');
      return {
        readyState: document.readyState,
        nuxtRoot: Boolean(document.querySelector('#__nuxt')),
        input: Boolean(input),
        button: visible(button),
        dark: visible(dark),
        light: visible(light),
      };
    })()`,
    value => value?.readyState === 'complete' && value?.nuxtRoot && value?.input && value?.button && value?.dark && value?.light,
    'Search page did not hydrate',
    20000,
  )
  await sleep(250)
}

async function navigateWithBoundAssets(cdp, baseUrl) {
  await cdp.send('Network.clearBrowserCache')
  const capture = new NavigationAssetCapture(cdp, baseUrl)
  capture.start()
  try {
    await navigate(cdp, new URL('/tim-kiem', baseUrl).toString(), capture)
    return await capture.verify()
  } finally {
    capture.stop()
  }
}

async function elementRect(cdp, selector) {
  const encoded = JSON.stringify(selector)
  return evaluate(cdp, `(() => {
    const element = document.querySelector(${encoded});
    if (!element) return null;
    element.scrollIntoView({ block: 'center', inline: 'center' });
    const rect = element.getBoundingClientRect();
    return { x: rect.x, y: rect.y, width: rect.width, height: rect.height, left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, centerX: rect.left + rect.width / 2, centerY: rect.top + rect.height / 2 };
  })()`)
}

async function physicalClick(cdp, selector) {
  const rect = await elementRect(cdp, selector)
  if (!rect || rect.width <= 0 || rect.height <= 0) throw new GateError('target-not-visible', `physical click target is not visible: ${selector}`)
  await sleep(50)
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: rect.centerX, y: rect.centerY })
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: rect.centerX, y: rect.centerY, button: 'left', buttons: 1, clickCount: 1 })
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: rect.centerX, y: rect.centerY, button: 'left', buttons: 0, clickCount: 1 })
  return rect
}

async function clearFocusedInput(cdp) {
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65, modifiers: 2 })
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65, modifiers: 2 })
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8, nativeVirtualKeyCode: 8 })
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8, nativeVirtualKeyCode: 8 })
}

async function injectMutation(cdp, mutation) {
  if (!mutation) return null
  return evaluate(cdp, `(() => {
    const selector = '.search-row-hero .search-input-wrap input';
    const style = document.createElement('style');
    style.id = 'search-mobile-hit-target-mutation';
    style.textContent = selector + ' { width: auto !important; min-width: auto !important; }';
    document.head.append(style);
    const input = document.querySelector(selector);
    const wrapper = document.querySelector('.search-row-hero .search-input-wrap');
    const rule = style.sheet?.cssRules?.[0];
    const computed = input ? getComputedStyle(input) : null;
    const rect = input?.getBoundingClientRect();
    const wrapperRect = wrapper?.getBoundingClientRect();
    return {
      id: '${mutation}',
      selector_matches: Boolean(input?.matches(selector)),
      rule_selector: rule?.selectorText || '',
      declared_width: rule?.style?.getPropertyValue('width') || '',
      declared_width_priority: rule?.style?.getPropertyPriority('width') || '',
      declared_min_width: rule?.style?.getPropertyValue('min-width') || '',
      declared_min_width_priority: rule?.style?.getPropertyPriority('min-width') || '',
      computed_width: computed?.width || '',
      computed_min_width: computed?.minWidth || '',
      rendered_width: rect?.width || 0,
      rendered_height: rect?.height || 0,
      wrapper_rendered_width: wrapperRect?.width || 0,
      wrapper_overflow_px: rect && wrapperRect ? Math.max(0, rect.right - wrapperRect.right) : 0,
    };
  })()`)
}

function assertMutationApplied(mutation, requestedMutation) {
  if (!requestedMutation) return
  const failures = []
  if (!mutation?.selector_matches) failures.push('selector did not match')
  if (mutation?.rule_selector !== '.search-row-hero .search-input-wrap input') failures.push('rule selector differs')
  if (mutation?.declared_width !== 'auto' || mutation?.declared_width_priority !== 'important') failures.push('width:auto !important is absent')
  if (mutation?.declared_min_width !== 'auto' || mutation?.declared_min_width_priority !== 'important') failures.push('min-width:auto !important is absent')
  if (!(mutation?.rendered_width > mutation?.wrapper_rendered_width && mutation?.wrapper_overflow_px > 0)) {
    failures.push('fixture does not overflow the input wrapper')
  }
  if (failures.length > 0) throw new GateError('mutation-not-applied', failures.join('; '))
}

function roundedRect(rect) {
  if (!rect) return null
  return Object.fromEntries(Object.entries(rect).map(([key, value]) => [key, Math.round(value * 100) / 100]))
}

function intersectionRect(a, b) {
  const left = Math.max(a.left, b.left)
  const right = Math.min(a.right, b.right)
  const top = Math.max(a.top, b.top)
  const bottom = Math.min(a.bottom, b.bottom)
  const width = Math.max(0, right - left)
  const height = Math.max(0, bottom - top)
  return { width, height, area: width * height }
}

function stateReason(evidence, state, code, message) {
  state.failures.push(code)
  addReason(evidence, `${state.theme}:${code}`, message)
}

async function exerciseState({ cdp, baseUrl, mode, theme, mutation, consoleErrors, evidence }) {
  const state = {
    theme,
    requested_mode: mode,
    selected_mode: '',
    preview_assets: { count: 0, unique_count: 0, search_css_path: '', fingerprint_sha256: '' },
    mutation: null,
    input_rect: null,
    button_rect: null,
    intersection: null,
    button_center_hit: { belongs_to_button: false, tag: '' },
    input_focused: false,
    input_value: '',
    location: '',
    horizontal_overflow_px: 0,
    console_errors: [],
    relevant_console_errors: [],
    failures: [],
  }
  const consoleStart = evidence.states.length === 0 ? 0 : consoleErrors.length
  state.preview_assets = await navigateWithBoundAssets(cdp, baseUrl)
  state.mutation = await injectMutation(cdp, mutation)
  assertMutationApplied(state.mutation, mutation)
  await physicalClick(cdp, `[data-theme-mode="${mode}"]`)
  const themeState = await waitForValue(
    cdp,
    `(() => ({ mode: document.querySelector('[data-theme-mode="${mode}"]')?.getAttribute('aria-pressed') === 'true' ? '${mode}' : '', className: document.documentElement.className, stored: localStorage.getItem('vl360-color-mode') }))()`,
    value => value?.mode === mode && value?.stored === mode && String(value?.className || '').split(/\s+/u).includes(mode),
    `theme ${mode} did not become active after physical click`,
  )
  state.selected_mode = themeState.mode

  try {
    await physicalClick(cdp, '.search-row-hero input[type="search"]')
    await clearFocusedInput(cdp)
    await cdp.send('Input.insertText', { text: QUERY })
    const typed = await waitForValue(
      cdp,
      `(() => ({ focused: document.activeElement === document.querySelector('.search-row-hero input[type="search"]'), value: document.querySelector('.search-row-hero input[type="search"]')?.value || '' }))()`,
      value => value?.focused && value?.value === QUERY,
      'Search input did not receive the physical focus/type sequence',
    )
    state.input_focused = typed.focused
    state.input_value = typed.value
  } catch (error) {
    const typed = await evaluate(cdp, `(() => ({ focused: document.activeElement === document.querySelector('.search-row-hero input[type="search"]'), value: document.querySelector('.search-row-hero input[type="search"]')?.value || '' }))()`)
    state.input_focused = typed.focused
    state.input_value = typed.value
    stateReason(evidence, state, 'physical-input', safeMessage(error))
  }

  const geometry = await evaluate(cdp, `(() => {
    const input = document.querySelector('.search-row-hero input[type="search"]');
    const button = document.querySelector('[data-color-role="action-primary"]');
    const ir = input.getBoundingClientRect();
    const br = button.getBoundingClientRect();
    const x = br.left + br.width / 2;
    const y = br.top + br.height / 2;
    const hit = document.elementFromPoint(x, y);
    const describe = element => element ? [element.tagName.toLowerCase(), element.id ? '#' + element.id : '', element.classList.length ? '.' + [...element.classList].slice(0, 3).join('.') : ''].join('') : '';
    return {
      input: { x: ir.x, y: ir.y, width: ir.width, height: ir.height, left: ir.left, right: ir.right, top: ir.top, bottom: ir.bottom, centerX: ir.left + ir.width / 2, centerY: ir.top + ir.height / 2 },
      button: { x: br.x, y: br.y, width: br.width, height: br.height, left: br.left, right: br.right, top: br.top, bottom: br.bottom, centerX: x, centerY: y },
      hitBelongs: Boolean(hit && (hit === button || button.contains(hit))),
      hitTag: describe(hit),
      overflow: Math.max(0, Math.max(document.documentElement.scrollWidth, document.body?.scrollWidth || 0) - document.documentElement.clientWidth),
    };
  })()`)
  state.input_rect = roundedRect(geometry.input)
  state.button_rect = roundedRect(geometry.button)
  state.intersection = roundedRect(intersectionRect(geometry.input, geometry.button))
  state.button_center_hit = { belongs_to_button: geometry.hitBelongs, tag: String(geometry.hitTag || '').slice(0, 120) }
  state.horizontal_overflow_px = Math.round(geometry.overflow * 100) / 100

  if (geometry.input.width < 1) stateReason(evidence, state, 'input-width', `input width ${geometry.input.width.toFixed(2)}px is not physically reachable`)
  if (geometry.input.height < 44) stateReason(evidence, state, 'input-height', `input height ${geometry.input.height.toFixed(2)}px is below 44px`)
  if (geometry.button.height < 44) stateReason(evidence, state, 'button-height', `button height ${geometry.button.height.toFixed(2)}px is below 44px`)
  if (state.intersection.area > 0) stateReason(evidence, state, 'target-intersection', `input and button intersect by ${state.intersection.area.toFixed(2)}px squared`)
  if (!geometry.hitBelongs) stateReason(evidence, state, 'button-center-hit', `button center resolves to ${geometry.hitTag || 'no element'}`)
  if (geometry.overflow > 2) stateReason(evidence, state, 'horizontal-overflow', `page overflows horizontally by ${geometry.overflow.toFixed(2)}px`)

  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: geometry.button.centerX, y: geometry.button.centerY })
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: geometry.button.centerX, y: geometry.button.centerY, button: 'left', buttons: 1, clickCount: 1 })
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: geometry.button.centerX, y: geometry.button.centerY, button: 'left', buttons: 0, clickCount: 1 })
  try {
    state.location = await waitForValue(
      cdp,
      'location.pathname + location.search',
      value => value === EXPECTED_LOCATION,
      'physical button-center click did not navigate to the typed query',
      10000,
    )
  } catch (error) {
    state.location = await evaluate(cdp, 'location.pathname + location.search')
    stateReason(evidence, state, 'physical-navigation', `${safeMessage(error)}; observed ${state.location}`)
  }
  await sleep(250)
  state.console_errors = consoleErrors.slice(consoleStart, consoleStart + MAX_CONSOLE_ERRORS)
  state.relevant_console_errors = state.console_errors.filter(entry => !entry.allowed_reason)
  if (state.relevant_console_errors.length > 0) {
    stateReason(evidence, state, 'console-errors', `${state.relevant_console_errors.length} relevant browser console error(s) observed`)
  }
  return state
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
    return {
      source,
      message: safeMessage(message),
      url: url ? safeMessage(url) : '',
      allowed_reason: allowedReason,
    }
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

function boundedJson(evidence) {
  let json = `${JSON.stringify(evidence, null, 2)}\n`
  if (Buffer.byteLength(json) <= MAX_EVIDENCE_BYTES) return json
  for (const state of evidence.states) {
    state.console_errors = state.console_errors.slice(0, 2)
    state.relevant_console_errors = state.relevant_console_errors.slice(0, 2)
  }
  evidence.reasons = evidence.reasons.slice(0, 8)
  json = `${JSON.stringify(evidence, null, 2)}\n`
  if (Buffer.byteLength(json) > MAX_EVIDENCE_BYTES) throw new Error('bounded evidence exceeded byte limit')
  return json
}

async function run(args, evidence) {
  evidence.manifest_revision = readManifest()
  if (evidence.manifest_revision !== args.expectedRevision) {
    throw new GateError(
      'revision-mismatch',
      `manifest revision ${evidence.manifest_revision} does not match expected revision ${args.expectedRevision}`,
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
      if (!entry || consoleErrors.length >= MAX_CONSOLE_ERRORS * 3) return
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
      cdp.send('Emulation.setDeviceMetricsOverride', {
        width: VIEWPORT.width,
        height: VIEWPORT.height,
        deviceScaleFactor: 1,
        mobile: true,
        screenWidth: VIEWPORT.width,
        screenHeight: VIEWPORT.height,
      }),
    ])
    for (const stateConfig of [
      { mode: 'dark', theme: 'nocturne' },
      { mode: 'light', theme: 'parchment' },
    ]) {
      evidence.states.push(await exerciseState({ cdp, baseUrl: args.baseUrl, mutation: args.mutation, consoleErrors, evidence, ...stateConfig }))
    }
    const firstAssets = evidence.states[0]?.preview_assets
    const allStateAssetsMatch = evidence.states.every(state => (
      state.preview_assets.count === firstAssets?.count
      && state.preview_assets.unique_count === firstAssets?.unique_count
      && state.preview_assets.search_css_path === firstAssets?.search_css_path
      && state.preview_assets.fingerprint_sha256 === firstAssets?.fingerprint_sha256
    ))
    evidence.preview_assets = {
      count: allStateAssetsMatch ? firstAssets?.count || 0 : 0,
      unique_count: allStateAssetsMatch ? firstAssets?.unique_count || 0 : 0,
      search_css_path: allStateAssetsMatch ? firstAssets?.search_css_path || '' : '',
      fingerprint_sha256: allStateAssetsMatch ? firstAssets?.fingerprint_sha256 || '' : '',
      state_count: evidence.states.length,
    }
  } finally {
    cdp?.close()
    if (chrome?.child) {
      try {
        await stopChrome(chrome.child)
      } catch (error) {
        evidence.cleanup_errors.push(`chrome:${safeMessage(error)}`)
      }
    }
    if (chrome?.profile) {
      try {
        await rm(chrome.profile, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 })
      } catch (error) {
        evidence.cleanup_errors.push(`profile:${safeMessage(error)}`)
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
    gate: 'search-mobile-hit-target',
    verdict: error instanceof GateError && error.blocked ? 'blocked' : 'fail',
    expected_revision: '',
    manifest_revision: '',
    mutation: '',
    preview_assets: { count: 0, unique_count: 0, search_css_path: '', fingerprint_sha256: '', state_count: 0 },
    viewport: VIEWPORT,
    states: [],
    reasons: [{ code: error instanceof GateError ? error.code : 'unexpected-error', message: safeMessage(error) }],
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
    gate: 'search-mobile-hit-target',
    verdict: 'blocked',
    expected_revision: args.expectedRevision,
    manifest_revision: '',
    mutation: args.mutation,
    preview_assets: { count: 0, unique_count: 0, search_css_path: '', fingerprint_sha256: '', state_count: 0 },
    viewport: VIEWPORT,
    states: [],
    reasons: [],
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
