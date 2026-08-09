import { spawn } from 'node:child_process'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { gzipSync } from 'node:zlib'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const previewUrl = 'http://127.0.0.1:4173/'
const apiFixturePath = '/api/places?limit=1'
const mainVisibleBudgetMs = 5000
const lcpBudgetMs = 2500
const clsBudget = 0.1
const inpBudgetMs = 200
const apiBudgetMs = 1500
const textScaleTarget = 2
const axeSourcePath = join(webRoot, 'node_modules', 'axe-core', 'axe.min.js')
const bundleBudgetPath = resolve(webRoot, '..', 'docs', 'standards', 'bundle-budget.json')

export function measureApiFixtureResources(resources, fixtureUrl) {
  const matches = resources.filter(entry => entry?.name === fixtureUrl)
  const durations = matches.map(entry => entry.duration)
  return {
    apiObservedCount: matches.length,
    apiMaxMs: durations.length > 0 && durations.every(Number.isFinite) ? Math.max(...durations) : null,
  }
}

export async function fulfillApiFixtureRequest(cdp, paused, fixtureUrl) {
  const matches = paused?.requestId
    && paused.request?.method === 'GET'
    && paused.request.url === fixtureUrl
  if (!matches) {
    if (paused?.requestId) {
      await cdp.send('Fetch.failRequest', { requestId: paused.requestId, errorReason: 'Aborted' })
    }
    return false
  }
  await cdp.send('Fetch.fulfillRequest', {
    requestId: paused.requestId,
    responseCode: 200,
    responsePhrase: 'OK',
    responseHeaders: [{ name: 'Content-Type', value: 'application/json; charset=utf-8' }],
    body: Buffer.from('{"places":[]}', 'utf8').toString('base64'),
  })
  return true
}

export function evaluatePublicAccessibilitySnapshot(snapshot) {
  const reasons = []
  if (!snapshot.forcedColorsActive) reasons.push('forced-colors-inactive')
  if (snapshot.forcedColorAdjust !== 'auto') reasons.push('forced-color-adjust-not-auto')
  if (!snapshot.forcedControlBorderVisible
    || !snapshot.forcedRepresentativeControls
    || snapshot.forcedRepresentativeControls.total < 1
    || snapshot.forcedRepresentativeControls.bounded < snapshot.forcedRepresentativeControls.total) {
    reasons.push('forced-control-border-missing')
  }
  if (snapshot.textScale !== textScaleTarget || snapshot.textScaleApplied !== true) reasons.push('text-scale-not-200-percent')
  if (snapshot.devicePixelRatio < 2
    || Math.abs((snapshot.viewportWidth * 2) - snapshot.screenWidth) > 2) reasons.push('zoom-layout-not-2x')
  if (snapshot.horizontalOverflow > 0) reasons.push('horizontal-overflow')
  if (!snapshot.mainVisible || snapshot.mainUsable !== true) reasons.push('main-content-hidden')
  if (snapshot.controlsBelow44 > 0) reasons.push('undersized-controls')
  if (snapshot.mainVisibleMs > mainVisibleBudgetMs) reasons.push('main-visible-budget-exceeded')
  const contrastAudits = [
    { available: snapshot.normalContrastAuditAvailable, audited: snapshot.normalContrastAuditedCount, violations: snapshot.normalContrastViolations },
    { available: snapshot.contrastAuditAvailable, audited: snapshot.contrastAuditedCount, violations: snapshot.contrastViolations },
  ]
  if (contrastAudits.some(audit => audit.available !== true)) reasons.push('contrast-audit-unavailable')
  if (contrastAudits.some(audit => !Number.isFinite(audit.audited) || audit.audited < 1)) reasons.push('contrast-audit-empty')
  if (contrastAudits.some(audit => audit.violations > 0)) reasons.push('contrast-violations')
  if (!Number.isFinite(snapshot.lcpMs)) reasons.push('lcp-audit-unavailable')
  else if (snapshot.lcpMs > lcpBudgetMs) reasons.push('lcp-budget-exceeded')
  if (!Number.isFinite(snapshot.cls)) reasons.push('cls-audit-unavailable')
  else if (snapshot.cls > clsBudget) reasons.push('cls-budget-exceeded')
  if (snapshot.inpAvailable !== true) reasons.push('inp-audit-unavailable')
  if (snapshot.inpEvidence !== 'rendered-interaction') reasons.push('inp-evidence-not-rendered')
  if (Number.isFinite(snapshot.inpMs) && snapshot.inpMs > inpBudgetMs) reasons.push('inp-budget-exceeded')
  if (snapshot.apiFixtureFulfilled !== true) reasons.push('api-fixture-unavailable')
  if (!Number.isFinite(snapshot.apiObservedCount) || snapshot.apiObservedCount < 1) reasons.push('api-audit-empty')
  if (snapshot.apiObservedCount >= 1 && snapshot.apiResponseSuccessful !== true) reasons.push('api-response-unsuccessful')
  if (!Number.isFinite(snapshot.apiMaxMs)) reasons.push('api-duration-unavailable')
  else if (snapshot.apiMaxMs > apiBudgetMs) reasons.push('api-budget-exceeded')
  if (snapshot.bundleAuditAvailable !== true) reasons.push('bundle-audit-unavailable')
  if (snapshot.bundleViolations > 0) reasons.push('bundle-budget-exceeded')
  return reasons
}

function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    process.env.LOCALAPPDATA ? join(process.env.LOCALAPPDATA, 'Google/Chrome/Application/chrome.exe') : '',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  ].filter(Boolean)
  return candidates.find(candidate => {
    try { return requireExists(candidate) } catch { return false }
  })
}

function requireExists(path) {
  try {
    return Boolean(process.getBuiltinModule('node:fs').existsSync(path))
  } catch {
    return false
  }
}

async function waitForHttp(url, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url)
      if (response.ok) return
    } catch { /* preview is still starting */ }
    await new Promise(resolveWait => setTimeout(resolveWait, 150))
  }
  throw new Error(`Preview did not become ready: ${url}`)
}

export async function launchChrome(chromePath, profileDir, options = {}) {
  const spawnProcess = options.spawnProcess || spawn
  const fetchImpl = options.fetchImpl || fetch
  const child = spawnProcess(chromePath, [
    '--headless=new',
    '--disable-background-networking',
    '--disable-component-update',
    '--disable-default-apps',
    '--disable-extensions',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--remote-debugging-address=127.0.0.1',
    '--remote-debugging-port=0',
    `--user-data-dir=${profileDir}`,
    '--window-size=1440,900',
    'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'], windowsHide: true })

  try {
    const websocketUrl = await new Promise((resolveUrl, reject) => {
      const timer = setTimeout(() => reject(new Error('Chrome CDP startup timed out')), 20000)
      const fail = error => {
        clearTimeout(timer)
        reject(error)
      }
      child.once('error', fail)
      child.once('exit', code => fail(new Error(`Chrome exited before CDP startup (${code ?? 'unknown'})`)))
      child.stderr?.setEncoding?.('utf8')
      child.stderr?.on('data', chunk => {
        const match = chunk.match(/DevTools listening on (ws:\/\/[^\s]+)/)
        if (!match) return
        clearTimeout(timer)
        resolveUrl(match[1])
      })
    })

    const port = new URL(websocketUrl).port
    const targets = await fetchImpl(`http://127.0.0.1:${port}/json/list`).then(response => response.json())
    const pageTarget = targets.find(target => target.type === 'page')
    if (!pageTarget?.webSocketDebuggerUrl) throw new Error('Chrome page target unavailable')
    return { child, websocketUrl: pageTarget.webSocketDebuggerUrl }
  } catch (error) {
    await stopChild(child)
    throw error
  }
}

class CdpClient {
  constructor(url) {
    this.socket = new WebSocket(url)
    this.nextId = 0
    this.pending = new Map()
    this.events = new Map()
  }

  async open() {
    await new Promise((resolveOpen, reject) => {
      this.socket.onopen = resolveOpen
      this.socket.onerror = () => reject(new Error('CDP WebSocket connection failed'))
    })
    this.socket.onmessage = event => {
      const message = JSON.parse(event.data)
      if (message.id) {
        const pending = this.pending.get(message.id)
        if (!pending) return
        this.pending.delete(message.id)
        if (message.error) pending.reject(new Error(message.error.message || 'CDP command failed'))
        else pending.resolve(message.result)
        return
      }
      const listeners = this.events.get(message.method) || []
      this.events.delete(message.method)
      for (const listener of listeners) listener(message.params)
    }
  }

  send(method, params = {}) {
    const id = ++this.nextId
    return new Promise((resolveCommand, reject) => {
      this.pending.set(id, { resolve: resolveCommand, reject })
      this.socket.send(JSON.stringify({ id, method, params }))
    })
  }

  waitFor(method, timeoutMs = 15000) {
    return new Promise((resolveEvent, reject) => {
      const timer = setTimeout(() => reject(new Error(`CDP event timed out: ${method}`)), timeoutMs)
      const listener = params => {
        clearTimeout(timer)
        resolveEvent(params)
      }
      this.events.set(method, [...(this.events.get(method) || []), listener])
    })
  }

  close() {
    this.socket.close()
  }
}

function allFiles(root) {
  if (!existsSync(root)) return []
  return readdirSync(root, { withFileTypes: true }).flatMap(entry => {
    const path = join(root, entry.name)
    return entry.isDirectory() ? allFiles(path) : [path]
  })
}

function bundleSnapshot() {
  const outputRoot = resolve(webRoot, '.output', 'public', '_nuxt')
  if (!existsSync(outputRoot)) return { bundleAuditAvailable: false, bundleViolations: 1 }
  let budget = { total_gz_kb: 800, max_chunk_gz_kb: 280, total_css_gz_kb: 190 }
  try { budget = { ...budget, ...JSON.parse(readFileSync(bundleBudgetPath, 'utf8')) } } catch { /* fail below */ }
  const js = readdirSync(outputRoot, { withFileTypes: true })
    .filter(entry => entry.isFile() && entry.name.endsWith('.js'))
    .map(entry => join(outputRoot, entry.name))
  const css = allFiles(outputRoot).filter(path => path.endsWith('.css'))
  if (!js.length) return { bundleAuditAvailable: false, bundleViolations: 1 }
  const gzKb = path => Math.floor(gzipSync(readFileSync(path)).length / 1024)
  const jsSizes = js.map(path => ({ path, kb: gzKb(path) }))
  const totalJs = jsSizes.reduce((sum, item) => sum + item.kb, 0)
  const maxJs = Math.max(...jsSizes.map(item => item.kb))
  const totalCss = css.reduce((sum, path) => sum + gzKb(path), 0)
  const bundleViolations = Number(totalJs > budget.total_gz_kb)
    + Number(maxJs > budget.max_chunk_gz_kb)
    + Number(totalCss > budget.total_css_gz_kb)
  return { bundleAuditAvailable: true, bundleViolations, bundleTotalGzKb: totalJs, bundleMaxGzKb: maxJs, bundleCssGzKb: totalCss }
}

async function navigateAndWait(cdp, method, params) {
  const load = cdp.waitFor('Page.loadEventFired')
  await cdp.send(method, params)
  await load
}

async function runApiFixtureProbe(cdp) {
  const fixtureUrl = new URL(apiFixturePath, previewUrl).href
  const urlPattern = fixtureUrl.replace(/[?*\\]/g, character => `\\${character}`)
  await cdp.send('Fetch.enable', { patterns: [{ urlPattern, requestStage: 'Request' }] })
  const pausedRequest = cdp.waitFor('Fetch.requestPaused', 5000)
  const evaluation = cdp.send('Runtime.evaluate', {
    expression: `(async () => { const fixtureUrl = ${JSON.stringify(fixtureUrl)}; window.__vl360Perf.apiRequestUrl = fixtureUrl; const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 3000); try { const response = await fetch(fixtureUrl, { cache: 'no-store', signal: controller.signal }); window.__vl360Perf.apiResponseSuccessful = response.ok && response.url === fixtureUrl } catch (_) { window.__vl360Perf.apiResponseSuccessful = false } finally { clearTimeout(timeout) } })()`,
    awaitPromise: true,
  })
  let fulfilled = false
  try {
    fulfilled = await fulfillApiFixtureRequest(cdp, await pausedRequest, fixtureUrl)
    await evaluation
  } catch { /* snapshot records the unavailable fixture below */ }
  finally {
    await cdp.send('Fetch.disable').catch(() => {})
    await evaluation.catch(() => {})
  }
  await cdp.send('Runtime.evaluate', {
    expression: `window.__vl360Perf.apiFixtureFulfilled = ${JSON.stringify(fulfilled)}`,
  })
}

async function contrastAudit(cdp) {
  if (!existsSync(axeSourcePath)) return { contrastAuditAvailable: false, contrastViolations: 1 }
  const source = readFileSync(axeSourcePath, 'utf8')
  await cdp.send('Runtime.evaluate', { expression: source })
  const evaluated = await cdp.send('Runtime.evaluate', {
    expression: "(() => { const context = [...document.querySelectorAll('.btn,button,[role=button]')].filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 }); return axe.run(context, { runOnly: { type: 'rule', values: ['color-contrast'] } }).then(result => JSON.stringify({ audited: context.length, violations: result.violations.length, ratios: result.violations.flatMap(v => v.nodes.flatMap(n => (n.any || []).map(check => check.data?.contrastRatio).filter(Number.isFinite))), details: result.violations.flatMap(v => v.nodes.map(n => ({ target: n.target, data: (n.any || []).map(check => check.data).filter(Boolean) }))) })) })()",
    awaitPromise: true,
    returnByValue: true,
  })
  const value = JSON.parse(evaluated.result?.value || '{}')
  return { contrastAuditAvailable: true, contrastAuditedCount: Number(value.audited || 0), contrastViolations: Number(value.violations || 0), contrastMinRatio: value.ratios?.length ? Math.min(...value.ratios) : null }
}

async function browserSnapshot(cdp) {
  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: 720,
    height: 450,
    screenWidth: 1440,
    screenHeight: 900,
    deviceScaleFactor: 2,
    mobile: false,
    scale: 1,
  })
  await cdp.send('Emulation.setEmulatedMedia', {
    media: 'screen',
    features: [
      { name: 'forced-colors', value: 'none' },
      { name: 'prefers-reduced-motion', value: 'reduce' },
    ],
  })

  await navigateAndWait(cdp, 'Page.navigate', { url: previewUrl })
  await cdp.send('Runtime.evaluate', {
    expression: `localStorage.setItem('vl360-accessibility-profile', ${JSON.stringify(JSON.stringify({ theme: 'nocturne', density: 'comfortable', textScale: 2 }))})`,
  })
  const load = cdp.waitFor('Page.loadEventFired')
  const navigationStarted = Date.now()
  await cdp.send('Page.reload', { ignoreCache: true })
  await load
  const normalContrast = await contrastAudit(cdp)

  await cdp.send('Emulation.setEmulatedMedia', {
    media: 'screen',
    features: [
      { name: 'forced-colors', value: 'active' },
      { name: 'prefers-reduced-motion', value: 'reduce' },
    ],
  })
  const forcedLoad = cdp.waitFor('Page.loadEventFired')
  await cdp.send('Page.reload', { ignoreCache: true })
  await forcedLoad

  let mainVisible = false
  let mainUsable = false
  while (!mainVisible && Date.now() - navigationStarted <= mainVisibleBudgetMs) {
    const evaluated = await cdp.send('Runtime.evaluate', {
      expression: "(() => { const el = document.querySelector('main, #main-content'); if (!el) return { visible: false, usable: false }; const r = el.getBoundingClientRect(); const s = getComputedStyle(el); return { visible: r.width > 0 && r.height > 0, usable: r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity) > 0 }; })()",
      returnByValue: true,
    })
    mainVisible = evaluated.result.value?.visible === true
    mainUsable = evaluated.result.value?.usable === true
    if (!mainVisible) await new Promise(resolveWait => setTimeout(resolveWait, 50))
  }
  const mainVisibleMs = Date.now() - navigationStarted

  const evaluated = await cdp.send('Runtime.evaluate', {
    expression: `(() => {
      const root = document.documentElement
      const controls = [...document.querySelectorAll('a[href],button,input:not([type="hidden"]),select,textarea,summary')]
        .filter(el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' })
      const hasBoundary = el => {
        const s = getComputedStyle(el)
        const visibleColor = value => value && value !== 'transparent' && !(value.startsWith('rgba') && value.endsWith(', 0)'))
        return ((s.borderStyle !== 'none' && parseFloat(s.borderWidth) > 0 && visibleColor(s.borderColor))
          || (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0 && visibleColor(s.outlineColor)))
      }
      const representatives = controls.filter(el => el.matches('[data-color-role="action-primary"],.btn-primary,button,input,select,textarea,summary,[role="button"]'))
      const boundedControls = (representatives.length ? representatives : controls).filter(hasBoundary)
      const main = document.querySelector('main, #main-content')
      const mainRect = main?.getBoundingClientRect()
      const mainStyle = main ? getComputedStyle(main) : null
      return {
        forcedColorsActive: matchMedia('(forced-colors: active)').matches,
        forcedColorAdjust: getComputedStyle(root).forcedColorAdjust,
        forcedControlBorderVisible: boundedControls.length > 0 && boundedControls.length === (representatives.length || controls.length),
        forcedRepresentativeControls: { total: representatives.length || controls.length, bounded: boundedControls.length },
        viewportWidth: innerWidth,
        screenWidth: screen.width,
        devicePixelRatio,
        textScale: Number.parseFloat(getComputedStyle(root).getPropertyValue('--a11y-text-scale')),
        textScaleApplied: Number.parseFloat(getComputedStyle(root).getPropertyValue('--a11y-text-scale')) === 2,
        horizontalOverflow: Math.max(0, root.scrollWidth - root.clientWidth),
        controlsBelow44: controls.filter(el => el.getBoundingClientRect().height < 44).length,
        mainVisible: Boolean(mainRect?.width && mainRect.height),
        mainUsable: Boolean(mainRect?.width && mainRect.height && mainStyle?.display !== 'none' && mainStyle?.visibility !== 'hidden' && Number(mainStyle?.opacity) > 0),
      }
    })()`,
    returnByValue: true,
  })

  await cdp.send('Runtime.evaluate', {
    expression: `(() => { const observerCtor = window.PerformanceObserver; const supportedEntryTypes = Array.isArray(observerCtor?.supportedEntryTypes) ? observerCtor.supportedEntryTypes : []; window.__vl360Perf = { lcp: null, cls: 0, inp: null, inpSupported: supportedEntryTypes.includes('event') || supportedEntryTypes.includes('first-input'), inpEvidence: 'unsupported' }; try { if (observerCtor) { new observerCtor(list => { const entries = list.getEntries(); const last = entries[entries.length - 1]; if (last) window.__vl360Perf.lcp = last.startTime }).observe({ type: 'largest-contentful-paint', buffered: true }); new observerCtor(list => { window.__vl360Perf.cls += list.getEntries().filter(entry => !entry.hadRecentInput).reduce((sum, entry) => sum + entry.value, 0) }).observe({ type: 'layout-shift', buffered: true }); if (supportedEntryTypes.includes('event')) new observerCtor(list => { window.__vl360Perf.inp = Math.max(window.__vl360Perf.inp || 0, ...list.getEntries().map(entry => entry.duration)) }).observe({ type: 'event', durationThreshold: 16, buffered: true }); if (supportedEntryTypes.includes('first-input')) new observerCtor(list => { window.__vl360Perf.inp = Math.max(window.__vl360Perf.inp || 0, ...list.getEntries().map(entry => entry.duration)) }).observe({ type: 'first-input', buffered: true }); } if (window.__vl360Perf.inpSupported) { const target = [...document.querySelectorAll('button,[role="button"],a[href]')].find(el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el); return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity) > 0 }); if (target) { target.setAttribute('data-vl360-inp-target', ''); window.__vl360Perf.inpEvidence = 'rendered-interaction' } } } catch (_) { window.__vl360Perf.inpSupported = false } })()`,
  })
  const point = await cdp.send('Runtime.evaluate', { expression: "(() => { const el = document.querySelector('[data-vl360-inp-target]'); if (!el) return null; const r = el.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 } })()", returnByValue: true })
  if (point.result?.value) {
    await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.result.value.x, y: point.result.value.y, button: 'left', clickCount: 1 })
    await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.result.value.x, y: point.result.value.y, button: 'left', clickCount: 1 })
  }
  await new Promise(resolveWait => setTimeout(resolveWait, 100))
  await runApiFixtureProbe(cdp)
  const forcedContrast = await contrastAudit(cdp)
  const perf = await cdp.send('Runtime.evaluate', {
    expression: `(() => { const state = window.__vl360Perf || {}; const api = (${measureApiFixtureResources.toString()})(performance.getEntriesByType('resource'), state.apiRequestUrl); return { lcpMs: state.lcp ?? performance.getEntriesByType('largest-contentful-paint').at(-1)?.startTime ?? null, cls: state.cls, inpAvailable: state.inpSupported === true && Number.isFinite(state.inp), inpMs: state.inp, inpEvidence: state.inpEvidence, ...api, apiResponseSuccessful: state.apiResponseSuccessful === true, apiFixtureFulfilled: state.apiFixtureFulfilled === true } })()`,
    returnByValue: true,
  })
  return {
    ...evaluated.result.value,
    mainVisible,
    mainUsable,
    mainVisibleMs,
    ...forcedContrast,
    normalContrastAuditAvailable: normalContrast.contrastAuditAvailable,
    normalContrastAuditedCount: normalContrast.contrastAuditedCount,
    normalContrastViolations: normalContrast.contrastViolations,
    normalContrastMinRatio: normalContrast.contrastMinRatio,
    ...perf.result.value,
    ...bundleSnapshot(),
  }
}

async function run() {
  const chromePath = findChrome()
  if (!chromePath) throw new Error('Chrome executable unavailable')
  const profileDir = await mkdtemp(join(tmpdir(), 'vl360-public-a11y-'))
  const preview = spawn(process.execPath, ['.output/server/index.mjs'], {
    cwd: webRoot,
    env: { ...process.env, HOST: '127.0.0.1', PORT: '4173', NITRO_HOST: '127.0.0.1', NITRO_PORT: '4173' },
    stdio: ['ignore', 'ignore', 'pipe'],
    windowsHide: true,
  })
  let chrome
  let cdp
  try {
    await waitForHttp(previewUrl)
    chrome = await launchChrome(chromePath, profileDir)
    cdp = new CdpClient(chrome.websocketUrl)
    await cdp.open()
    const snapshot = await browserSnapshot(cdp)
    const reasons = evaluatePublicAccessibilitySnapshot(snapshot)
    process.stdout.write(`${JSON.stringify({ snapshot, reasons }, null, 2)}\n`)
    if (reasons.length) process.exitCode = 1
    await cdp.send('Browser.close').catch(() => {})
  } finally {
    cdp?.close()
    await stopChild(chrome?.child)
    await stopChild(preview)
    for (let attempt = 0; attempt < 5; attempt += 1) {
      try {
        await rm(profileDir, { recursive: true, force: true })
        break
      } catch (error) {
        if (attempt === 4) throw error
        await new Promise(resolveWait => setTimeout(resolveWait, 200))
      }
    }
  }
}

async function stopChild(child) {
  if (!child || child.exitCode !== null) return
  await new Promise(resolveExit => {
    const timer = setTimeout(() => {
      child.kill()
      resolveExit()
    }, 3000)
    child.once('exit', () => {
      clearTimeout(timer)
      resolveExit()
    })
    child.kill()
  })
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  run().catch(error => {
    process.stderr.write(`${error.stack || error.message}\n`)
    process.exitCode = 1
  })
}
