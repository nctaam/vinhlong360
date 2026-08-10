import { spawn, spawnSync } from 'node:child_process'
import { createHash, randomUUID } from 'node:crypto'
import { existsSync } from 'node:fs'
import { createServer } from 'node:http'
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

export const PUBLIC_ROUTE_SPECS = Object.freeze([
  Object.freeze({ key: 'home', path: '/', visualPath: '/', recipe: 'homepage', readySelector: '[data-home-section="editorial-lead"] h1' }),
  Object.freeze({ key: 'tourism', path: '/du-lich', visualPath: '/du-lich', recipe: 'discovery', readySelector: '[data-catalog-result]' }),
  Object.freeze({ key: 'search', path: '/tim-kiem', visualPath: '/tim-kiem?q=g%E1%BB%91m&intent=place&area=vinh-long&type=craft_village', recipe: 'search', readySelector: '[data-map-list-surface]' }),
  Object.freeze({ key: 'map', path: '/ban-do', visualPath: '/ban-do?q=g%E1%BB%91m&intent=place&area=vinh-long&type=craft_village', recipe: 'map', readySelector: '[data-map-list-surface]' }),
  Object.freeze({ key: 'detail', path: '/dia-diem/{id}', visualPath: '/dia-diem/gom-do-mang-thit', recipe: 'detail', readySelector: '[data-detail-action-safe-area]' }),
  Object.freeze({ key: 'planner', path: '/tao-lich-trinh', visualPath: '/tao-lich-trinh?add=gom-do-mang-thit', recipe: 'planner', readySelector: '.planner-picker' }),
])

export const PUBLIC_STATE_KINDS = Object.freeze([
  'loading',
  'ready',
  'partial',
  'stale',
  'empty',
  'error',
  'offline',
  '404-confirmed',
  'retryable-5xx',
])

export const PUBLIC_VISUAL_THEMES = Object.freeze(['nocturne', 'parchment'])
export const PUBLIC_VISUAL_SCHEMA_REVISION = 'adaptive-nocturne-public-v2'
export const PUBLIC_VISUAL_VIEWPORTS = Object.freeze([
  Object.freeze({ width: 375, height: 812 }),
  Object.freeze({ width: 390, height: 844 }),
  Object.freeze({ width: 768, height: 1024 }),
  Object.freeze({ width: 1024, height: 768 }),
  Object.freeze({ width: 1440, height: 900 }),
])

export const SMOKE_JOURNEY_STEPS = Object.freeze([
  Object.freeze({ id: 'homepage', route: '/' }),
  Object.freeze({ id: 'search', route: '/tim-kiem' }),
  Object.freeze({ id: 'map-panel', route: '/tim-kiem' }),
  Object.freeze({ id: 'list-panel', route: '/tim-kiem' }),
  Object.freeze({ id: 'detail', route: '/dia-diem/{id}' }),
  Object.freeze({ id: 'planner', route: '/tao-lich-trinh' }),
  Object.freeze({ id: 'back-to-detail', route: '/dia-diem/{id}' }),
  Object.freeze({ id: 'back-to-search', route: '/tim-kiem' }),
  Object.freeze({ id: 'map-failure', route: '/ban-do' }),
  Object.freeze({ id: 'detail-retryable-5xx', route: '/dia-diem/{id}' }),
])

function expectedStateContract(route, state) {
  const detail404 = route.key === 'detail' && state === '404-confirmed'
  const actions = []
  if (state === 'partial') actions.push('retry-panel')
  if (state === 'empty') actions.push('recover')
  if (state === 'error' || state === 'retryable-5xx' || (state === '404-confirmed' && !detail404)) actions.push('retry')
  if (detail404) actions.push('back-to-results')
  return Object.freeze({
    preserveContent: ['partial', 'stale', 'offline'].includes(state),
    contentVisible: state === 'ready',
    confirmed404: detail404,
    actions: Object.freeze(actions),
  })
}

export function buildPublicStateMatrix() {
  return PUBLIC_ROUTE_SPECS.flatMap(route => PUBLIC_STATE_KINDS.map(state => Object.freeze({
    route,
    state,
    expected: expectedStateContract(route, state),
  })))
}

export function buildPublicStateFixture(scenario) {
  const fixtures = {
    loading: { kind: 'loading' },
    ready: { kind: 'ready', data: { id: scenario.route.key } },
    partial: { kind: 'partial', data: { id: scenario.route.key }, failedPanels: ['media'] },
    stale: { kind: 'stale', data: { id: scenario.route.key }, updatedAt: '2026-08-09' },
    empty: { kind: 'empty', recovery: { id: 'browse', label: 'Xem tất cả' } },
    error: { kind: 'error', retry: { label: 'Thử lại' } },
    offline: { kind: 'offline', cached: { id: scenario.route.key }, cachedAt: '2026-08-09' },
    '404-confirmed': { kind: 'error', retry: { label: 'Thử lại' } },
    'retryable-5xx': { kind: 'error', retry: { label: 'Thử lại' } },
  }
  const isConfirmedDetail404 = scenario.route.key === 'detail' && scenario.state === '404-confirmed'
  const isDetailFailure = scenario.route.key === 'detail'
    && ['404-confirmed', 'retryable-5xx'].includes(scenario.state)

  return Object.freeze({
    surfaceState: isConfirmedDetail404 ? null : Object.freeze(fixtures[scenario.state]),
    detailFailure: isDetailFailure
      ? Object.freeze(scenario.state === '404-confirmed'
          ? { response: { status: 404, _data: { detail: 'not_found' } } }
          : { response: { status: 503, _data: { detail: 'temporarily_unavailable' } } })
      : null,
    detailResolution: isDetailFailure
      ? scenario.state === '404-confirmed' ? 'not_found' : 'error'
      : null,
  })
}

export function evaluatePublicStateEvidence(scenario, evidence) {
  const reasons = []
  if (!evidence?.shellVisible) reasons.push('shell-not-visible')
  if (!evidence?.mainVisible) reasons.push('main-not-visible')
  if (Number(evidence?.actionDockOverlap || 0) > 0) reasons.push('action-dock-overlap')
  if (scenario.expected.preserveContent && !evidence?.contentVisible) reasons.push('content-not-preserved')
  if (scenario.expected.contentVisible && !evidence?.contentVisible) reasons.push('ready-content-not-visible')
  if (scenario.expected.confirmed404 !== Boolean(evidence?.confirmed404)) {
    reasons.push(evidence?.confirmed404 ? 'false-404' : 'confirmed-404-missing')
  }
  for (const action of scenario.expected.actions) {
    if (!evidence?.actions?.includes(action)) reasons.push(`recovery-action-missing:${action}`)
  }
  return reasons
}

export function visualScreenshotName({ routeKey, theme, viewport, state }) {
  return `${routeKey}__${theme}__${viewport.width}px__${state}.png`
}

export function createVisualBaselineScenarios() {
  return PUBLIC_ROUTE_SPECS.flatMap(route => PUBLIC_VISUAL_THEMES.flatMap(theme => PUBLIC_VISUAL_VIEWPORTS.map(viewport => Object.freeze({
    route,
    theme,
    viewport,
    state: 'ready',
    fileName: visualScreenshotName({ routeKey: route.key, theme, viewport, state: 'ready' }),
  }))))
}

function visualScenarioIdentity(scenario) {
  return Object.freeze({
    schemaRevision: PUBLIC_VISUAL_SCHEMA_REVISION,
    routeKey: scenario.route.key,
    visualPath: scenario.route.visualPath,
    recipe: scenario.route.recipe,
    readySelector: scenario.route.readySelector,
    theme: scenario.theme,
    viewport: scenario.viewport,
    state: scenario.state,
    fileName: scenario.fileName,
  })
}

function sha256Bytes(value) {
  return createHash('sha256').update(value).digest('hex')
}

function visualIdentitySha256(scenario) {
  return sha256Bytes(JSON.stringify(visualScenarioIdentity(scenario)))
}

export function evaluateVisualReadiness(scenario, evidence) {
  const reasons = []
  const expectedPathname = new URL(scenario.route.visualPath, 'http://visual.local').pathname
  if (evidence?.pathname !== expectedPathname) reasons.push('route-mismatch')
  if (evidence?.recipe !== scenario.route.recipe) reasons.push('recipe-mismatch')
  if (!evidence?.hydrated) reasons.push('not-hydrated')
  if (evidence?.theme !== scenario.theme) reasons.push('theme-mismatch')
  if (!(Number(evidence?.mainHeight) > 0)) reasons.push('main-not-visible')
  if (!evidence?.readySelectorVisible || !String(evidence?.contentIdentity || '').trim()) reasons.push('ready-content-missing')
  for (const state of evidence?.blockingStates || []) reasons.push(`blocking-state:${state}`)
  return reasons
}

export function createVisualArtifactManifest({ scenario, runId, capturedAt, screenshotBytes, readiness }) {
  return Object.freeze({
    schemaRevision: PUBLIC_VISUAL_SCHEMA_REVISION,
    runId,
    capturedAt,
    fileName: scenario.fileName,
    scenarioIdentitySha256: visualIdentitySha256(scenario),
    screenshotSha256: sha256Bytes(screenshotBytes),
    routeKey: scenario.route.key,
    visualPath: scenario.route.visualPath,
    theme: scenario.theme,
    viewport: scenario.viewport,
    state: scenario.state,
    recipe: scenario.route.recipe,
    readySelector: scenario.route.readySelector,
    contentIdentity: String(readiness?.contentIdentity || '').trim().slice(0, 500),
  })
}

export function validateVisualArtifactForResume(scenario, artifact, screenshotBytes, runId) {
  const reasons = []
  if (!artifact) return ['manifest-entry-missing']
  if (artifact.schemaRevision !== PUBLIC_VISUAL_SCHEMA_REVISION) reasons.push('schema-revision-mismatch')
  if (artifact.runId !== runId) reasons.push('run-id-mismatch')
  if (artifact.scenarioIdentitySha256 !== visualIdentitySha256(scenario)) reasons.push('scenario-identity-mismatch')
  if (!screenshotBytes) reasons.push('screenshot-missing')
  else if (artifact.screenshotSha256 !== sha256Bytes(screenshotBytes)) reasons.push('screenshot-digest-mismatch')
  if (!String(artifact.contentIdentity || '').trim()) reasons.push('content-identity-missing')
  return reasons
}

export function compareVisualArtifacts(candidate, baseline) {
  const reasons = []
  if (!baseline) return ['authoritative-baseline-missing']
  if (candidate?.scenarioIdentitySha256 !== baseline.scenarioIdentitySha256) reasons.push('baseline-scenario-identity-mismatch')
  if (candidate?.screenshotSha256 !== baseline.screenshotSha256) reasons.push('baseline-pixel-digest-mismatch')
  if (candidate?.contentIdentity !== baseline.contentIdentity) reasons.push('baseline-content-identity-mismatch')
  return reasons
}

export function selectPendingVisualScenarios(scenarios, artifactValidation, resume = false) {
  if (!resume) return scenarios
  return scenarios.filter(scenario => {
    const reasons = artifactValidation.get(scenario.fileName)
    return !reasons || reasons.length > 0
  })
}

export function classifySmokeIssue(issue) {
  if (issue?.kind === 'http'
    && Number(issue.status) >= 500
    && ['retryable-detail', 'map-fallback'].includes(issue.renderedRecovery)) {
    return 'external-backend-limitation'
  }
  return 'product-regression'
}

function formatRuntimeSmokeIssue(issue) {
  if (issue?.kind === 'http') return `HTTP ${issue.status} ${redactSensitiveUrl(issue.url)}`
  if (issue?.kind === 'log') return `log ${redactSensitiveText(issue.text)}`
  if (issue?.kind === 'console') return `console ${redactSensitiveText(issue.message)}`
  if (issue?.kind === 'exception') return `exception ${redactSensitiveText(issue.message)}`
  return `runtime ${redactSensitiveText(JSON.stringify(issue))}`
}

export function evaluateRuntimeSmokeIssues(issues) {
  return issues
    .filter(issue => classifySmokeIssue(issue) === 'product-regression')
    .map(formatRuntimeSmokeIssue)
}

export function evaluateSmokeJourneyEvidence(evidence) {
  const reasons = []
  if (evidence?.expectedSearchUrl !== evidence?.restoredSearchUrl) reasons.push('search-state-not-preserved')
  if (evidence?.consoleErrors?.length) reasons.push('console-error')
  if (evidence?.actionDockOverlaps?.some(item => Number(item.pixels) > 0)) reasons.push('action-dock-overlap')
  const completed = new Set(evidence?.completedSteps || [])
  for (const step of SMOKE_JOURNEY_STEPS) {
    if (!completed.has(step.id)) reasons.push(`journey-step-missing:${step.id}`)
  }
  if (!evidence?.mapFallbackVisible) reasons.push('map-fallback-missing')
  if (!evidence?.detailRetryVisible) reasons.push('detail-retry-missing')
  if (evidence?.detailConfirmed404) reasons.push('retryable-detail-false-404')
  return reasons
}

export async function activateVisibleControl({ pointerClick, elementClick, isActivated, settle = () => sleep(75), maxAttempts = 2 }) {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    await pointerClick()
    await settle()
    if (await isActivated()) return { method: 'pointer', attempts: attempt }

    await elementClick()
    await settle()
    if (await isActivated()) return { method: 'element', attempts: attempt }
  }
  throw new Error(`Visible control did not reach its expected state after ${maxAttempts} attempts`)
}

let baseUrl = process.env.SMOKE_BASE_URL || 'http://localhost:3000'
let apiBaseUrl = process.env.SMOKE_API_BASE_URL || baseUrl
const phone = process.env.SMOKE_PHONE || '0909090909'
const password = process.env.SMOKE_PASSWORD || 'PassHomnay.2'
const username = process.env.SMOKE_USERNAME || 'testuser09'
const port = Number(process.env.SMOKE_CDP_PORT || 9223)
const settleMs = Number(process.env.SMOKE_SETTLE_MS || 1200)
const visualDir = process.env.SMOKE_VISUAL_DIR || path.join(tmpdir(), 'vinhlong360-task10-visual')
const visualBaselineDir = process.env.SMOKE_VISUAL_BASELINE_DIR || ''
const visualRunId = process.env.SMOKE_VISUAL_RUN_ID || `visual-${new Date().toISOString()}-${randomUUID()}`
const visualManifestName = 'visual-manifest.json'

const defaultRoutes = [
  '/',
  '/tai-khoan',
  '/cai-dat',
  `/nguoi-dung/${username}`,
  '/tim-kiem',
  '/cong-dong',
  '/ban-do',
  '/lich-trinh',
  '/du-lich',
  '/san-pham',
  '/ocop',
  '/luu-tru',
  '/le-hoi',
  '/su-kien',
  '/theo-mua',
  '/bang-xep-hang',
  '/thong-bao',
  '/da-luu',
  '/tao-lich-trinh',
  '/huong-dan-thanh-vien',
]
const routes = process.env.SMOKE_ROUTES
  ? process.env.SMOKE_ROUTES.split(',').map(s => s.trim()).filter(Boolean)
  : defaultRoutes

let activeSmokeRoute = ''
const fixtureMode = { mapFailure: false, detailFailure: false }
const fixtureEntity = Object.freeze({
  id: 'gom-do-mang-thit',
  type: 'craft_village',
  name: 'Gốm đỏ Mang Thít',
  summary: 'Theo dấu đất và lửa dọc sông Cổ Chiên.',
  description: 'Một không gian làng nghề ven sông với những lò gốm đỏ còn lưu giữ ký ức địa phương.',
  place_name: 'Mang Thít, Vĩnh Long',
  area: 'vinh-long',
  coordinates: { lat: 10.187, lng: 106.105 },
  attributes: { address: 'Mang Thít, Vĩnh Long', best_months: [8, 9, 10] },
  quality: {
    source_tier: 'official',
    source_title: 'Cổng thông tin Vĩnh Long',
    source_url: 'https://vinhlong.gov.vn',
  },
  source_freshness: {
    source_tier: 'official',
    source_title: 'Cổng thông tin Vĩnh Long',
    source_url: 'https://vinhlong.gov.vn',
    updated_at: '2026-08-09T07:00:00+07:00',
    freshness_status: 'fresh',
  },
})

function fixturePayload(url) {
  const pathname = url.pathname
  if (pathname === '/api/homepage') {
    return {
      month: 8,
      seasonal_tagline: 'Theo dòng sông, gặp mùa trái chín',
      experiences: [fixtureEntity],
      products: [],
      upcoming_events: [],
      seasonal: [{ id: 'buoi-nam-roi', type: 'product', name: 'Bưởi Năm Roi' }],
      top_dishes: [],
      itineraries: [],
      area_counts: { 'vinh-long': 1 },
    }
  }
  if (pathname === '/api/feed') return { posts: [] }
  if (pathname === '/api/community/stats') return null
  if (pathname === '/api/community/leaderboard') return { leaders: [] }
  if (pathname === '/api/community/trending-tags') return { tags: [] }
  if (pathname === `/api/users/${username}`) {
    return {
      user: {
        id: 'smoke-user',
        username,
        display_name: 'Người dùng smoke',
        bio: 'Hồ sơ kiểm tra tuyến công khai.',
      },
    }
  }
  if (pathname === '/api/itineraries') return []
  if (pathname === '/api/search') {
    return { entities: [fixtureEntity], results: [fixtureEntity], posts: [], users: [], totals: { entities: 1, posts: 0, users: 0 } }
  }
  if (pathname === '/api/map-pins') return [fixtureEntity]
  if (pathname === '/api/entities/popular') return { entities: [fixtureEntity] }
  if (pathname === '/api/entities/gom-do-mang-thit/gallery') return { images: [] }
  if (pathname === '/api/entities/gom-do-mang-thit/relationships') return { relationships: [], total: 0 }
  if (pathname === '/api/entities/gom-do-mang-thit') return fixtureEntity
  if (pathname === '/api/entities') return { entities: [fixtureEntity], total: 1 }
  if (pathname === '/seo/jsonld/gom-do-mang-thit') return null
  return {}
}

async function startFixtureServer() {
  if (process.env.SMOKE_USE_FIXTURES === '0') return null
  const fixturePort = Number(process.env.SMOKE_FIXTURE_PORT || 8360)
  try {
    const response = await fetch(`http://127.0.0.1:${fixturePort}/api/homepage`)
    if (response.ok) return null
  } catch {}

  const server = createServer((request, response) => {
    const url = new URL(request.url || '/', `http://127.0.0.1:${fixturePort}`)
    if (fixtureMode.mapFailure && url.pathname === '/api/map-pins') {
      response.writeHead(503, { 'content-type': 'application/json' })
      response.end(JSON.stringify({ detail: 'map fixture unavailable' }))
      return
    }
    if (fixtureMode.detailFailure && url.pathname === '/api/entities/gom-do-mang-thit') {
      response.writeHead(503, { 'content-type': 'application/json' })
      response.end(JSON.stringify({ detail: 'detail fixture unavailable' }))
      return
    }
    response.writeHead(200, { 'content-type': 'application/json; charset=utf-8' })
    response.end(JSON.stringify(fixturePayload(url)))
  })

  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(fixturePort, '127.0.0.1', resolve)
  })
  return server
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
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
  return candidates.find(p => existsSync(p))
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${options.method || 'GET'} ${redactSensitiveUrl(url)} -> ${res.status} ${text.slice(0, 160)}`)
  }
  return res.json()
}

async function login() {
  const data = await fetchJson(new URL('/auth/login', apiBaseUrl), {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ phone, password }),
  })
  if (!data.token) throw new Error('Login succeeded but no token was returned')
  return data.token
}

class CdpClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl
    this.seq = 0
    this.pending = new Map()
    this.listeners = new Map()
  }

  connect() {
    if (typeof WebSocket === 'undefined') {
      throw new Error('This smoke script requires Node.js with global WebSocket support')
    }
    this.ws = new WebSocket(this.wsUrl)
    this.ws.onmessage = event => {
      const msg = JSON.parse(event.data)
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject, timer } = this.pending.get(msg.id)
        clearTimeout(timer)
        this.pending.delete(msg.id)
        if (msg.error) reject(new Error(`${msg.error.message || 'CDP error'} ${JSON.stringify(msg.error.data || '')}`))
        else resolve(msg.result || {})
        return
      }
      if (msg.method && this.listeners.has(msg.method)) {
        for (const fn of this.listeners.get(msg.method)) fn(msg.params || {})
      }
    }
    return new Promise((resolve, reject) => {
      this.ws.onopen = resolve
      this.ws.onerror = () => reject(new Error(`Cannot connect to Chrome CDP at ${this.wsUrl}`))
    })
  }

  send(method, params = {}, timeoutMs = 15000) {
    const id = ++this.seq
    const payload = JSON.stringify({ id, method, params })
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id)
        reject(new Error(`CDP timeout: ${method}`))
      }, timeoutMs)
      this.pending.set(id, { resolve, reject, timer })
      this.ws.send(payload)
    })
  }

  on(method, fn) {
    if (!this.listeners.has(method)) this.listeners.set(method, new Set())
    this.listeners.get(method).add(fn)
    return () => this.listeners.get(method).delete(fn)
  }

  waitFor(method, timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
      const off = this.on(method, params => {
        clearTimeout(timer)
        off()
        resolve(params)
      })
      const timer = setTimeout(() => {
        off()
        reject(new Error(`Timed out waiting for ${method}`))
      }, timeoutMs)
    })
  }

  close() {
    this.ws?.close()
  }
}

async function waitForChrome() {
  const versionUrl = `http://127.0.0.1:${port}/json/version`
  for (let i = 0; i < 80; i++) {
    try {
      const data = await fetchJson(versionUrl)
      if (data.webSocketDebuggerUrl) return
    } catch {}
    await sleep(250)
  }
  throw new Error('Chrome did not open a CDP endpoint in time')
}

async function createPageTarget() {
  const endpoint = `http://127.0.0.1:${port}/json/new?about:blank`
  let res = await fetch(endpoint, { method: 'PUT' })
  if (!res.ok) res = await fetch(endpoint)
  if (!res.ok) throw new Error(`Cannot create Chrome target: ${res.status}`)
  const data = await res.json()
  return data.webSocketDebuggerUrl
}

function absoluteUrl(route) {
  return new URL(route, baseUrl).toString()
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

function redactSensitiveText(input) {
  return redactSensitiveUrl(String(input || '')).replace(/\bBearer\s+[A-Za-z0-9._~+/=-]{16,}/g, 'Bearer [redacted]')
}

function summarizeConsole(params) {
  const args = (params.args || []).map(arg => arg.value || arg.description || arg.type).join(' ')
  return redactSensitiveText(`${params.type}: ${args}`).slice(0, 500)
}

function isSameOriginNuxtAsset(url) {
  try {
    const parsed = new URL(url)
    const base = new URL(baseUrl)
    return parsed.origin === base.origin && parsed.pathname.startsWith('/_nuxt/')
  } catch {
    return false
  }
}

async function probeSameOriginAsset(url) {
  if (!isSameOriginNuxtAsset(url)) return false
  try {
    let res = await fetch(url, { method: 'HEAD' })
    if (res.status === 405) res = await fetch(url, { method: 'GET' })
    return res.status > 0 && res.status < 500
  } catch {
    return false
  }
}

const routeContracts = [
  {
    name: 'search input',
    match: route => route === '/tim-kiem',
    selectors: ['.cat-search', 'input[type="search"]', 'button.btn-primary'],
  },
  {
    name: 'map explorer',
    match: route => route === '/ban-do',
    selectors: ['.cat-map', '[data-map-list-surface]'],
  },
  {
    name: 'saved workspace',
    match: route => route === '/da-luu',
    selectors: ['.saved-page', '.saved-guest, .saved-header'],
  },
  {
    name: 'planner workspace',
    match: route => route === '/tao-lich-trinh',
    selectors: ['.planner-picker', '.planner-builder', 'input[type="search"]'],
  },
]

async function runRouteContract(cdp, route, routeFailures) {
  const contract = routeContracts.find(item => item.match(route))
  if (!contract) return
  const expression = `(${JSON.stringify(contract.selectors)}).filter(s=>!document.querySelector(s))`
  const result = await cdp.send('Runtime.evaluate', {
    expression,
    returnByValue: true,
  }).catch(err => {
    routeFailures.push(`route contract ${contract.name} failed to evaluate: ${err.message}`)
    return null
  })
  const missing = result?.result?.value || []
  if (Array.isArray(missing) && missing.length) {
    routeFailures.push(`route contract ${contract.name} missing selectors: ${missing.join(', ')}`)
  }
}

async function runLegacyRouteSweep(cdp, failures, runtimeIssues) {
  for (const route of routes) {
    const routeFailures = []
    const routeAssetFailures = []
    const offConsole = cdp.on('Runtime.consoleAPICalled', params => {
      if (['error', 'assert'].includes(params.type)) {
        const issue = { kind: 'console', message: summarizeConsole(params), pageRoute: route }
        runtimeIssues.push(issue)
        routeFailures.push(formatRuntimeSmokeIssue(issue))
      }
    })
    const offException = cdp.on('Runtime.exceptionThrown', params => {
      const issue = {
        kind: 'exception',
        message: String(params.exceptionDetails?.text || params.exceptionDetails?.exception?.description || '').slice(0, 500),
        pageRoute: route,
      }
      runtimeIssues.push(issue)
      routeFailures.push(formatRuntimeSmokeIssue(issue))
    })
    const offLog = cdp.on('Log.entryAdded', params => {
      if (params.entry?.level !== 'error') return
      const entry = params.entry
      const suffix = entry.url ? ` (${redactSensitiveUrl(entry.url)}${entry.networkRequestId ? ` #${entry.networkRequestId}` : ''})` : ''
      const issue = { kind: 'log', level: entry.level, text: `${entry.text}${suffix}`, url: entry.url, pageRoute: route }
      if (String(entry.text || '').includes('net::ERR_FAILED') && entry.url && isSameOriginNuxtAsset(entry.url)) {
        routeAssetFailures.push({ url: entry.url, issue })
      } else {
        runtimeIssues.push(issue)
        routeFailures.push(formatRuntimeSmokeIssue(issue))
      }
    })
    const offResponse = cdp.on('Network.responseReceived', params => {
      const status = params.response?.status || 0
      if (status < 500) return
      const issue = { kind: 'http', status, url: params.response.url, pageRoute: route }
      runtimeIssues.push(issue)
      routeFailures.push(formatRuntimeSmokeIssue(issue))
    })

    activeSmokeRoute = route
    const load = cdp.waitFor('Page.loadEventFired', 20000).catch(error => {
      routeFailures.push(error.message)
    })
    await cdp.send('Page.navigate', { url: absoluteUrl(route) })
    await load
    await sleep(settleMs)

    const title = await cdp.send('Runtime.evaluate', {
      expression: 'document.title',
      returnByValue: true,
    }).catch(() => ({ result: { value: '' } }))
    if (String(title.result?.value || '').match(/\b500\b|Internal Server Error/i)) {
      routeFailures.push(`document title looks like an error: ${title.result.value}`)
    }
    await runRouteContract(cdp, route, routeFailures)
    for (const item of routeAssetFailures) {
      if (!(await probeSameOriginAsset(item.url))) {
        runtimeIssues.push(item.issue)
        routeFailures.push(formatRuntimeSmokeIssue(item.issue))
      }
    }

    offConsole()
    offException()
    offLog()
    offResponse()

    if (routeFailures.length) {
      failures.push({ route, failures: [...new Set(routeFailures)] })
      console.log(`[FAIL] ${route}`)
    } else {
      console.log(`[OK] ${route}`)
    }
  }
}

async function probeApp(url) {
  try {
    const response = await fetch(url, { redirect: 'manual' })
    return response.status > 0 && response.status < 500
  } catch {
    return false
  }
}

export function managedSmokeLaunchConfig({ baseUrl: requestedBaseUrl, explicitBaseUrl, forceManaged }) {
  const requested = new URL(requestedBaseUrl)
  const port = Number(requested.port || (requested.protocol === 'https:' ? 443 : 80))
  const host = requested.hostname
  if (forceManaged && !['127.0.0.1', 'localhost'].includes(host)) {
    throw new Error('SMOKE_FORCE_MANAGED_APP only supports an explicit loopback base URL')
  }
  if (forceManaged && (!explicitBaseUrl || !requested.port || !Number.isInteger(port) || port <= 0)) {
    throw new Error('SMOKE_FORCE_MANAGED_APP requires SMOKE_BASE_URL with an explicit port')
  }
  return { startManaged: Boolean(forceManaged), host, port }
}

export function managedSmokeStartupTimeout(env = process.env) {
  const requested = Number(env.SMOKE_APP_STARTUP_TIMEOUT_MS)
  return Number.isFinite(requested) && requested >= 5_000 && requested <= 120_000
    ? Math.round(requested)
    : 60_000
}

export function managedSmokeCommand({ mode, repoRoot, host, port, platform = process.platform, nodePath = process.execPath }) {
  if (mode === 'preview') {
    return {
      command: nodePath,
      args: [path.join(repoRoot, 'web-nuxt', '.output', 'server', 'index.mjs')],
      shell: false,
      env: { NITRO_HOST: host, NITRO_PORT: String(port) },
    }
  }
  return {
    command: platform === 'win32' ? 'npm.cmd' : 'npm',
    args: ['--prefix', 'web-nuxt', 'run', 'dev', '--', '--host', host, '--port', String(port)],
    shell: platform === 'win32',
    env: { NUXT_IGNORE_LOCK: '1' },
  }
}

export function smokeRunMode(env = process.env) {
  return { legacySweepOnly: env.SMOKE_LEGACY_SWEEP_ONLY === '1' }
}

export function terminateManagedProcess(appProcess, options = {}) {
  if (!appProcess) return
  const platform = options.platform || process.platform
  const run = options.run || spawnSync
  if (platform === 'win32' && Number.isInteger(appProcess.pid) && appProcess.pid > 0) {
    const result = run('taskkill.exe', ['/PID', String(appProcess.pid), '/T', '/F'], {
      stdio: 'ignore',
      timeout: 10_000,
    })
    if (result?.status === 0) return
  }
  appProcess.kill()
}

export async function closeSmokeServers({ appProcess, fixtureServer }) {
  terminateManagedProcess(appProcess)
  if (fixtureServer) await new Promise(resolve => fixtureServer.close(resolve))
}

async function resolveWebApp() {
  const forceManaged = process.env.SMOKE_FORCE_MANAGED_APP === '1'
  const launch = managedSmokeLaunchConfig({
    baseUrl,
    explicitBaseUrl: Boolean(process.env.SMOKE_BASE_URL),
    forceManaged,
  })
  if (process.env.SMOKE_BASE_URL && !forceManaged) {
    if (!(await probeApp(baseUrl))) throw new Error(`Smoke base URL is unavailable: ${baseUrl}`)
    return null
  }
  if (!forceManaged) {
    for (const candidate of [baseUrl, 'http://127.0.0.1:4173']) {
      if (await probeApp(candidate)) {
        baseUrl = candidate
        apiBaseUrl = process.env.SMOKE_API_BASE_URL || candidate
        return null
      }
    }
  }

  const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
  const managedCommand = managedSmokeCommand({
    mode: process.env.SMOKE_MANAGED_APP_MODE || 'dev',
    repoRoot,
    host: launch.host,
    port: launch.port,
  })
  if (managedCommand.args[0]?.endsWith(path.join('.output', 'server', 'index.mjs'))
    && !existsSync(managedCommand.args[0])) {
    throw new Error(`Managed preview build is missing: ${managedCommand.args[0]}`)
  }
  const startupOutput = []
  let spawnError = null
  const child = spawn(managedCommand.command, managedCommand.args, {
    cwd: repoRoot,
    env: { ...process.env, ...managedCommand.env },
    shell: managedCommand.shell,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  const rememberOutput = chunk => {
    startupOutput.push(redactSensitiveText(chunk).slice(-2000))
    if (startupOutput.length > 10) startupOutput.shift()
  }
  child.stdout?.on('data', rememberOutput)
  child.stderr?.on('data', rememberOutput)
  child.once('error', error => { spawnError = error })

  const deadline = Date.now() + managedSmokeStartupTimeout()
  while (Date.now() < deadline) {
    if (await probeApp(baseUrl)) return child
    if (spawnError) throw new Error(`Nuxt dev server failed to start: ${spawnError.message}`)
    if (child.exitCode !== null) {
      throw new Error(`Nuxt dev server exited with code ${child.exitCode}: ${startupOutput.join('\n').slice(-4000)}`)
    }
    await sleep(250)
  }
  child.kill()
  throw new Error(`Nuxt dev server did not become ready at ${baseUrl} within ${managedSmokeStartupTimeout()}ms: ${startupOutput.join('\n').slice(-4000)}`)
}

async function evaluateValue(cdp, expression) {
  const result = await cdp.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  return result.result?.value
}

async function waitForCondition(cdp, expression, label, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await evaluateValue(cdp, expression).catch(() => false)) return
    await sleep(100)
  }
  throw new Error(`Timed out waiting for ${label}`)
}

async function navigate(cdp, route) {
  activeSmokeRoute = route
  const load = cdp.waitFor('Page.loadEventFired', 30000)
  await cdp.send('Page.navigate', { url: absoluteUrl(route) })
  await load
  await sleep(settleMs)
}

async function clickByText(cdp, selector, text, expectedExpression, expectedLabel, expectedTimeoutMs = 750) {
  const point = await evaluateValue(cdp, `(() => {
    const target = [...document.querySelectorAll(${JSON.stringify(selector)})]
      .find(element => element.textContent?.trim().includes(${JSON.stringify(text)}));
    if (!target) return null;
    target.scrollIntoView({ block: 'center', inline: 'center' });
    const rect = target.getBoundingClientRect();
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
  })()`)
  if (!point) throw new Error(`Could not find ${selector} containing ${text}`)
  if (!expectedExpression) {
    await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1 })
    await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1 })
    return
  }

  await activateVisibleControl({
    pointerClick: async () => {
      await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1 })
      await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1 })
    },
    elementClick: () => evaluateValue(cdp, `(() => {
      const target = [...document.querySelectorAll(${JSON.stringify(selector)})]
        .find(element => element.textContent?.trim().includes(${JSON.stringify(text)}));
      target?.click();
      return Boolean(target);
    })()`),
    isActivated: async () => {
      try {
        await waitForCondition(cdp, expectedExpression, expectedLabel || text, expectedTimeoutMs)
        return true
      } catch {
        return false
      }
    },
  }).catch(error => {
    throw new Error(`${expectedLabel || text}: ${error.message}`)
  })
}

async function actionDockOverlap(cdp) {
  return evaluateValue(cdp, `(() => {
    const docks = [...document.querySelectorAll('[data-action-dock], [data-detail-action-safe-area], [data-planner-action-safe-area]')];
    const fixed = [...document.querySelectorAll('.journey-bar, .bottom-nav, [data-fixed-action-rail]')]
      .filter(element => getComputedStyle(element).position === 'fixed');
    let pixels = 0;
    for (const dock of docks) {
      const a = dock.getBoundingClientRect();
      for (const rail of fixed) {
        const b = rail.getBoundingClientRect();
        const overlapX = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
        const overlapY = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
        if (overlapX > 0) pixels = Math.max(pixels, overlapY);
      }
    }
    return pixels;
  })()`)
}

async function setTheme(cdp, theme) {
  await evaluateValue(cdp, `(() => {
    localStorage.setItem('vl360-accessibility-profile', JSON.stringify({ theme: ${JSON.stringify(theme)}, density: 'comfortable', textScale: 1 }));
    localStorage.setItem('theme', ${JSON.stringify(theme === 'parchment' ? 'light' : 'dark')});
    return true;
  })()`)
}

async function readVisualManifest(directory) {
  try {
    const parsed = JSON.parse(await readFile(path.join(directory, visualManifestName), 'utf8'))
    if (parsed?.schemaRevision !== PUBLIC_VISUAL_SCHEMA_REVISION || !Array.isArray(parsed.artifacts)) return new Map()
    return new Map(parsed.artifacts.map(artifact => [artifact.fileName, artifact]))
  } catch {
    return new Map()
  }
}

async function writeVisualManifest(directory, artifacts) {
  const payload = {
    schemaRevision: PUBLIC_VISUAL_SCHEMA_REVISION,
    runId: visualRunId,
    comparisonMode: visualBaselineDir ? 'authoritative-exact-sha256' : 'capture-for-review',
    baselineDirectory: visualBaselineDir ? path.resolve(visualBaselineDir) : null,
    artifacts: [...artifacts.values()].sort((left, right) => left.fileName.localeCompare(right.fileName)),
  }
  await writeFile(path.join(directory, visualManifestName), `${JSON.stringify(payload, null, 2)}\n`)
}

async function readVisualPng(directory, fileName) {
  return readFile(path.join(directory, fileName)).catch(() => null)
}

async function collectVisualReadiness(cdp, scenario) {
  return evaluateValue(cdp, `(() => {
    const ready = document.querySelector(${JSON.stringify(scenario.route.readySelector)});
    const visible = element => {
      if (!element) return false;
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    };
    const blockingStates = [];
    if (document.querySelector('[data-page-state="loading"], [aria-label*="Đang tải"], .skeleton-grid')) blockingStates.push('loading');
    if (document.querySelector('[data-page-state="error"], .detail-recovery-page, [data-color-role="status-error"]')) blockingStates.push('error');
    if (document.querySelector('[data-home-section="recovery"]')) blockingStates.push('home-recovery');
    if (document.querySelector('vite-error-overlay, nuxt-error-page, #nuxt-error')) blockingStates.push('nuxt-error-overlay');
    return {
      pathname: location.pathname,
      recipe: document.querySelector('[data-page-recipe]')?.getAttribute('data-page-recipe') || '',
      hydrated: Boolean(document.querySelector('#__nuxt')?.__vue_app__),
      theme: document.documentElement.dataset.theme || '',
      mainHeight: document.querySelector('main')?.getBoundingClientRect().height || 0,
      readySelectorVisible: visible(ready),
      contentIdentity: ready?.textContent?.replace(/\\s+/g, ' ').trim().slice(0, 500) || '',
      blockingStates,
    };
  })()`)
}

async function waitForVisualReadiness(cdp, scenario, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs
  let evidence = null
  let reasons = ['readiness-not-evaluated']
  while (Date.now() < deadline) {
    evidence = await collectVisualReadiness(cdp, scenario)
    reasons = evaluateVisualReadiness(scenario, evidence)
    if (!reasons.length) return evidence
    await sleep(100)
  }
  throw new Error(`Visual ${scenario.fileName} is not ready: ${reasons.join(', ')}; evidence=${JSON.stringify(evidence)}`)
}

async function captureVisual(cdp, scenario) {
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: scenario.viewport.width,
    height: scenario.viewport.height,
    deviceScaleFactor: 1,
    mobile: scenario.viewport.width < 768,
  })
  await navigate(cdp, scenario.route.visualPath)
  await setTheme(cdp, scenario.theme)
  await navigate(cdp, scenario.route.visualPath)
  const readiness = await waitForVisualReadiness(cdp, scenario)
  const metrics = await cdp.send('Page.getLayoutMetrics')
  const size = metrics.cssContentSize || metrics.contentSize
  const screenshot = await cdp.send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: true,
    fromSurface: true,
    clip: { x: 0, y: 0, width: Math.ceil(size.width), height: Math.ceil(size.height), scale: 1 },
  }, 30000)
  const screenshotBytes = Buffer.from(screenshot.data, 'base64')
  await writeFile(path.join(visualDir, scenario.fileName), screenshotBytes)
  return createVisualArtifactManifest({
    scenario,
    runId: visualRunId,
    capturedAt: new Date().toISOString(),
    screenshotBytes,
    readiness,
  })
}

async function main() {
  const chromePath = findChrome()
  if (!chromePath) throw new Error('Chrome/Edge not found. Set CHROME_PATH to a Chromium executable.')

  const failures = []
  const legacyRuntimeIssues = []
  const journeyRuntimeIssues = []
  const evidence = {
    expectedSearchUrl: '/tim-kiem?q=g%E1%BB%91m&intent=place&area=vinh-long&type=craft_village',
    restoredSearchUrl: '',
    consoleErrors: [],
    actionDockOverlaps: [],
    completedSteps: [],
    mapFallbackVisible: false,
    detailRetryVisible: false,
    detailConfirmed404: false,
  }
  let fixtureServer = null
  let appProcess = null
  let userDataDir = ''
  let chrome = null
  let cdp
  try {
    fixtureServer = await startFixtureServer()
    appProcess = await resolveWebApp()
    const token = process.env.SMOKE_REQUIRE_LOGIN === '1' ? await login() : ''
    await mkdir(visualDir, { recursive: true })
    userDataDir = await mkdtemp(path.join(tmpdir(), 'vl360-smoke-'))
    chrome = spawn(chromePath, [
      '--headless=new',
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${userDataDir}`,
      '--disable-gpu',
      '--no-first-run',
      '--no-default-browser-check',
      'about:blank',
    ], { stdio: 'ignore' })

    await waitForChrome()
    cdp = new CdpClient(await createPageTarget())
    await cdp.connect()
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Network.enable')
    await cdp.send('Log.enable')

    if (token) {
      const base = new URL(baseUrl)
      await cdp.send('Network.setCookie', {
        name: 'vl360_token',
        value: token,
        domain: base.hostname,
        path: '/',
        secure: base.protocol === 'https:',
        sameSite: 'Lax',
      })
    }

    await runLegacyRouteSweep(cdp, failures, legacyRuntimeIssues)

    if (!smokeRunMode().legacySweepOnly) {
    const offConsole = cdp.on('Runtime.consoleAPICalled', params => {
      if (['error', 'assert'].includes(params.type)) evidence.consoleErrors.push(summarizeConsole(params))
    })
    const offException = cdp.on('Runtime.exceptionThrown', params => {
      evidence.consoleErrors.push(redactSensitiveText(params.exceptionDetails?.text || params.exceptionDetails?.exception?.description || '').slice(0, 500))
    })
    const offLog = cdp.on('Log.entryAdded', params => {
      if (params.entry?.level !== 'error') return
      journeyRuntimeIssues.push({
        kind: 'log',
        level: params.entry.level,
        text: params.entry.text,
        url: params.entry.url,
        pageRoute: activeSmokeRoute,
      })
    })
    const offResponse = cdp.on('Network.responseReceived', params => {
      const status = params.response?.status || 0
      if (status >= 500) {
        journeyRuntimeIssues.push({
          kind: 'http',
          status,
          url: params.response.url,
          pageRoute: activeSmokeRoute,
        })
      }
    })

    await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })
    await navigate(cdp, '/')
    await waitForCondition(cdp, `document.querySelector('[data-page-recipe="homepage"]')`, 'homepage recipe')
    await waitForCondition(cdp, `Boolean(document.querySelector('#__nuxt')?.__vue_app__)`, 'homepage hydration')
    evidence.completedSteps.push('homepage')

    await navigate(cdp, '/tim-kiem?q=g%E1%BB%91m')
    evidence.completedSteps.push('search')

    await navigate(cdp, evidence.expectedSearchUrl)
    await waitForCondition(cdp, `document.querySelector('[data-map-list-surface]') && document.body.innerText.includes('Gốm đỏ Mang Thít')`, 'search result surface')
    await waitForCondition(cdp, `Boolean(document.querySelector('#__nuxt')?.__vue_app__)`, 'search hydration')
    await clickByText(cdp, '[data-map-list-surface] button', 'Bản đồ', `document.querySelector('[data-map-list-surface]')?.getAttribute('data-panel') === 'map'`, 'map panel')
    await waitForCondition(cdp, `document.querySelector('[data-map-list-surface]')?.getAttribute('data-panel') === 'map'`, 'map panel')
    evidence.completedSteps.push('map-panel')
    await clickByText(cdp, '[data-map-list-surface] button', 'Danh sách', `document.querySelector('[data-map-list-surface]')?.getAttribute('data-panel') === 'list'`, 'list panel')
    await waitForCondition(cdp, `document.querySelector('[data-map-list-surface]')?.getAttribute('data-panel') === 'list'`, 'list panel')
    evidence.completedSteps.push('list-panel')

    await clickByText(cdp, '[data-map-list-surface] a[href="/dia-diem/gom-do-mang-thit"]', 'Gốm đỏ Mang Thít', `location.pathname === '/dia-diem/gom-do-mang-thit' && document.querySelector('[data-page-recipe="detail"]')`, 'detail page', 5000)
    await waitForCondition(cdp, `location.pathname === '/dia-diem/gom-do-mang-thit' && document.querySelector('[data-page-recipe="detail"]')`, 'detail page')
    evidence.completedSteps.push('detail')
    evidence.actionDockOverlaps.push({ route: '/dia-diem/gom-do-mang-thit', pixels: await actionDockOverlap(cdp) })

    await clickByText(cdp, 'a[href^="/tao-lich-trinh"]', 'Thêm vào lịch trình', `location.pathname === '/tao-lich-trinh'`, 'planner navigation', 5000)
    await waitForCondition(cdp, `location.pathname === '/tao-lich-trinh'`, 'planner navigation')
    evidence.completedSteps.push('planner')
    evidence.actionDockOverlaps.push({ route: '/tao-lich-trinh', pixels: await actionDockOverlap(cdp) })

    await cdp.send('Runtime.evaluate', { expression: 'history.back()' })
    await waitForCondition(cdp, `location.pathname === '/dia-diem/gom-do-mang-thit'`, 'back to detail')
    evidence.completedSteps.push('back-to-detail')
    await cdp.send('Runtime.evaluate', { expression: 'history.back()' })
    await waitForCondition(cdp, `location.pathname === '/tim-kiem'`, 'back to search')
    evidence.restoredSearchUrl = await evaluateValue(cdp, `location.pathname + location.search`)
    evidence.completedSteps.push('back-to-search')

    const mapFailureScript = await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
      source: `(() => {
        const original = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, ...args) {
          if (String(type).toLowerCase().includes('webgl')) return null;
          return original.call(this, type, ...args);
        };
      })();`,
    })
    await navigate(cdp, evidence.expectedSearchUrl.replace('/tim-kiem', '/ban-do'))
    await waitForCondition(cdp, `document.querySelector('[data-map-fallback][data-map-state="error"]')`, 'map renderer fallback')
    evidence.mapFallbackVisible = Boolean(await evaluateValue(cdp, `document.querySelector('[data-map-fallback][data-map-state="error"]')`))
    evidence.completedSteps.push('map-failure')
    await cdp.send('Page.removeScriptToEvaluateOnNewDocument', { identifier: mapFailureScript.identifier })

    fixtureMode.detailFailure = true
    await navigate(cdp, '/dia-diem/gom-do-mang-thit?smoke=retryable-5xx')
    evidence.detailRetryVisible = Boolean(await evaluateValue(cdp, `document.querySelector('.detail-recovery-page') && [...document.querySelectorAll('button')].some(button => button.textContent?.includes('Thử lại'))`))
    evidence.detailConfirmed404 = Boolean(await evaluateValue(cdp, `document.body.innerText.includes('Không tìm thấy địa điểm này')`))
    evidence.completedSteps.push('detail-retryable-5xx')
    fixtureMode.detailFailure = false

    for (const issue of journeyRuntimeIssues) {
      if (issue.kind === 'http'
        && String(issue.pageRoute).startsWith('/dia-diem/gom-do-mang-thit')
        && evidence.detailRetryVisible) {
        issue.renderedRecovery = 'retryable-detail'
      }
      if (issue.kind === 'http'
        && String(issue.pageRoute).startsWith('/ban-do')
        && evidence.mapFallbackVisible) {
        issue.renderedRecovery = 'map-fallback'
      }
    }
    const runtimeFailures = evaluateRuntimeSmokeIssues(journeyRuntimeIssues)
    if (runtimeFailures.length) failures.push({ route: 'public-journey-runtime', failures: [...new Set(runtimeFailures)] })
    for (const reason of evaluateSmokeJourneyEvidence(evidence)) failures.push({ route: 'public-journey', failures: [reason] })

    if (process.env.SMOKE_SKIP_VISUALS !== '1') {
      if (visualBaselineDir && path.resolve(visualBaselineDir) === path.resolve(visualDir)) {
        throw new Error('SMOKE_VISUAL_BASELINE_DIR must be separate from SMOKE_VISUAL_DIR')
      }
      const scenarios = createVisualBaselineScenarios()
      const candidateArtifacts = await readVisualManifest(visualDir)
      const artifactValidation = new Map()
      for (const scenario of scenarios) {
        const screenshotBytes = await readVisualPng(visualDir, scenario.fileName)
        artifactValidation.set(
          scenario.fileName,
          validateVisualArtifactForResume(
            scenario,
            candidateArtifacts.get(scenario.fileName),
            screenshotBytes,
            visualRunId,
          ),
        )
      }
      const visualScenarios = selectPendingVisualScenarios(scenarios, artifactValidation, process.env.SMOKE_RESUME_VISUALS === '1')
      console.log(`[VISUAL] mode=${visualBaselineDir ? 'authoritative-exact-sha256' : 'capture-for-review'} run=${visualRunId}`)
      console.log(`[VISUAL] ${visualScenarios.length} pending of ${scenarios.length}`)
      for (const scenario of visualScenarios) {
        const artifact = await captureVisual(cdp, scenario)
        candidateArtifacts.set(scenario.fileName, artifact)
        await writeVisualManifest(visualDir, candidateArtifacts)
        console.log(`[SHOT] ${scenario.fileName}`)
      }

      if (visualBaselineDir) {
        const baselineArtifacts = await readVisualManifest(visualBaselineDir)
        for (const scenario of scenarios) {
          const candidate = candidateArtifacts.get(scenario.fileName)
          const baseline = baselineArtifacts.get(scenario.fileName)
          const baselineBytes = await readVisualPng(visualBaselineDir, scenario.fileName)
          const baselineIntegrity = validateVisualArtifactForResume(
            scenario,
            baseline,
            baselineBytes,
            baseline?.runId,
          )
          const comparison = compareVisualArtifacts(candidate, baseline)
          const reasons = [...baselineIntegrity, ...comparison]
          if (reasons.length) failures.push({ route: `visual:${scenario.fileName}`, failures: reasons })
        }
      } else {
        console.log('[VISUAL] No authoritative baseline supplied; fresh candidates require review before promotion.')
      }
    }

    offConsole()
    offException()
    offLog()
    offResponse()
    console.log(`Smoke evidence: ${JSON.stringify({ ...evidence, visualDir, legacyRuntimeIssueCount: legacyRuntimeIssues.length, journeyRuntimeIssues })}`)
    } else {
      console.log(`Smoke evidence: ${JSON.stringify({ mode: 'legacy-sweep-only', routes, legacyRuntimeIssueCount: legacyRuntimeIssues.length })}`)
    }
  } finally {
    cdp?.close()
    chrome?.kill()
    if (chrome) await sleep(500)
    await closeSmokeServers({ appProcess, fixtureServer })
    if (userDataDir && !process.env.SMOKE_KEEP_BROWSER) {
      try {
        await rm(userDataDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 250 })
      } catch {
        console.warn(`Warning: could not remove temporary Chrome profile ${userDataDir}`)
      }
    }
  }

  if (failures.length) {
    console.error('\nSmoke E2E failed:')
    for (const item of failures) {
      console.error(`- ${item.route}`)
      for (const failure of item.failures) console.error(`  ${failure}`)
    }
    process.exit(1)
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(err => {
    console.error(err.stack || err.message)
    process.exitCode = 1
  })
}
