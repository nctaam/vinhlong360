#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { existsSync } from 'node:fs'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const webRoot = path.join(repoRoot, 'web-nuxt')
const appPort = Number(process.env.SMOKE_APP_PORT || 3199)
const chromePort = Number(process.env.SMOKE_CDP_PORT || 9239)
const baseUrl = process.env.SMOKE_BASE_URL || `http://127.0.0.1:${appPort}`
const settleMs = Number(process.env.SMOKE_SETTLE_MS || 350)

const STITCH_SCREENS = Object.freeze({
  detailV2: '6a86654f63f243679ebe997ea340172b',
  savedItinerary: 'db76e318f0354ee3b1b8e3a0860443a5',
  community: 'dc2a7a19958e442a990f548953a042e9',
  mobileDarkPremium: '9dac45c42bd7470797ff912060690909',
  search: '41df1bef12c443fe8247a62b3f50f419',
})

const defaultPreferences = () => ({
  region_id: null,
  region_label: null,
  region_scope: 'unknown',
  location_source: 'default',
  location_accuracy: 'unknown',
  location_consent_state: 'unknown',
  location_enabled: false,
  personalization_enabled: true,
  explicit_interests: [],
  derived_age_band: '25_34',
  recommendation_reset_at: null,
  consent_version: 'identity-location-trust-v1',
  revision: 0,
})

const fixture = {
  user: {
    id: 'smoke-personalization-user',
    display_name: 'Người kiểm thử',
    username: 'smoke-personalization-user',
    role: 'user',
    has_password: true,
  },
  preferences: defaultPreferences(),
  flags: { failNextPreferencePatch: false, conflictNextPreferencePatch: false },
  calls: { preferencePatch: 0, preferenceGet: 0, locationResolve: 0, ipResolve: 0, reset: 0, contextual: 0, popular: 0 },
  lastLocationBody: null,
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function jsonResponse(res, status, body) {
  const payload = JSON.stringify(body)
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
    'content-length': Buffer.byteLength(payload),
  })
  res.end(payload)
}

async function readJson(req) {
  const chunks = []
  for await (const chunk of req) chunks.push(chunk)
  if (!chunks.length) return {}
  return JSON.parse(Buffer.concat(chunks).toString('utf8'))
}

function recommendationFixture() {
  return {
    id: 'smoke-recommendation',
    type: 'place',
    name: 'Vườn trái cây ven sông',
    summary: 'Một điểm ghé chậm rãi trong ngày.',
    attributes: {},
    relationships: [],
    relationship_total: 0,
    reason_vi: 'Cùng khu vực bạn chọn',
    explanation: {
      primary_reason: 'Cùng khu vực bạn chọn',
      reasons: ['Cùng khu vực bạn chọn', 'Phù hợp với sở thích bạn đã chọn'],
      region_label: fixture.preferences.region_label || 'Toàn tỉnh',
      explicit_interests: fixture.preferences.explicit_interests,
    },
    source_tier: 'official',
    freshness_status: 'fresh',
  }
}

function detailFixture(id) {
  const variants = {
    'smoke-official': {
      tier: 'official',
      title: 'Cổng thông tin tỉnh Vĩnh Long',
      freshness: 'fresh',
      verifiedAt: null,
    },
    'smoke-verified': {
      tier: 'verified',
      title: 'Đối tác dữ liệu địa phương',
      freshness: 'aging',
      verifiedAt: '2026-07-18T00:00:00Z',
    },
    'smoke-community': {
      tier: 'community',
      title: 'Chia sẻ từ người dân địa phương',
      freshness: 'stale',
      verifiedAt: null,
    },
  }
  const variant = variants[id] || variants['smoke-official']
  return {
    id,
    type: 'place',
    name: `Địa điểm kiểm thử ${id}`,
    summary: 'Nội dung công khai dùng để kiểm tra lớp giải thích và độ tin cậy.',
    description: 'Thông tin mô phỏng đầy đủ tại biên API, trang và drawer vẫn là implementation thật.',
    attributes: {},
    relationships: [],
    relationship_total: 0,
    area: 'vinh-long',
    place_area: 'vinh-long',
    publication_status: 'published',
    quality: {
      has_source: true,
      source_title: variant.title,
      source_url: `https://example.vn/sources/${id}`,
      source_tier: variant.tier,
      verified_at: variant.verifiedAt,
    },
    source_freshness: {
      source_title: variant.title,
      source_url: `https://example.vn/sources/${id}`,
      updated_at: '2026-07-20T00:00:00Z',
      verified_at: variant.verifiedAt,
      days_since_update: variant.freshness === 'stale' ? 120 : 9,
      freshness_status: variant.freshness,
    },
  }
}

function applyPreferencePatch(body) {
  const { revision: _revision, latitude: _latitude, longitude: _longitude, gps: _gps, ip: _ip, ...allowed } = body || {}
  fixture.preferences = {
    ...fixture.preferences,
    ...allowed,
    revision: fixture.preferences.revision + 1,
  }
  return clone(fixture.preferences)
}

function startFixtureApi() {
  const server = createServer(async (req, res) => {
    try {
      const url = new URL(req.url || '/', 'http://fixture.local')
      const pathname = decodeURIComponent(url.pathname)
      const method = req.method || 'GET'

      if (pathname === '/auth/me') return jsonResponse(res, 200, { user: fixture.user })
      if (pathname === '/auth/csrf') return jsonResponse(res, 200, { csrf_token: 'fixture-csrf-token' })
      if (pathname === '/auth/privacy') return jsonResponse(res, 200, { profile_visibility: 'public', show_activity: true, show_saved: true })
      if (pathname === '/auth/consent-history') return jsonResponse(res, 200, { history: [] })
      if (pathname === '/api/site-settings') return jsonResponse(res, 200, {})
      if (pathname === '/api/notification-preferences') return jsonResponse(res, 200, {})
      if (pathname.startsWith('/api/users/')) return jsonResponse(res, 200, { user: fixture.user })

      if (pathname === '/api/me/preferences' && method === 'GET') {
        fixture.calls.preferenceGet += 1
        return jsonResponse(res, 200, clone(fixture.preferences))
      }
      if (pathname === '/api/me/preferences' && method === 'PATCH') {
        fixture.calls.preferencePatch += 1
        const body = await readJson(req)
        if (fixture.flags.failNextPreferencePatch) {
          fixture.flags.failNextPreferencePatch = false
          return jsonResponse(res, 503, { detail: 'Fixture offline mutation' })
        }
        if (fixture.flags.conflictNextPreferencePatch) {
          fixture.flags.conflictNextPreferencePatch = false
          fixture.preferences = {
            ...fixture.preferences,
            region_id: 'province-tv',
            region_label: 'Trà Vinh',
            region_scope: 'province',
            location_source: 'manual',
            location_accuracy: 'province',
          }
          return jsonResponse(res, 409, clone(fixture.preferences))
        }
        return jsonResponse(res, 200, applyPreferencePatch(body))
      }
      if (pathname === '/api/me/location/resolve' && method === 'POST') {
        fixture.calls.locationResolve += 1
        fixture.lastLocationBody = await readJson(req)
        return jsonResponse(res, 200, {
          region_id: 'province-vl',
          region_label: 'Vĩnh Long',
          region_scope: 'province',
          location_source: 'gps',
          location_accuracy: 'province',
        })
      }
      if (pathname.includes('/location/ip')) {
        fixture.calls.ipResolve += 1
        return jsonResponse(res, 200, {})
      }
      if (pathname === '/api/me/recommendations/reset' && method === 'POST') {
        fixture.calls.reset += 1
        if (!fixture.preferences.recommendation_reset_at) {
          fixture.preferences = {
            ...fixture.preferences,
            recommendation_reset_at: '2026-07-29T08:00:00Z',
            revision: fixture.preferences.revision + 1,
          }
        }
        return jsonResponse(res, 200, clone(fixture.preferences))
      }
      if (pathname === '/api/me/recommendations/contextual') {
        fixture.calls.contextual += 1
        const items = fixture.preferences.personalization_enabled ? [recommendationFixture()] : []
        return jsonResponse(res, 200, { items, reasons: {}, profile: { signal_count: 4 } })
      }
      if (pathname === '/api/entities/popular') {
        fixture.calls.popular += 1
        return jsonResponse(res, 200, { entities: [recommendationFixture()] })
      }

      const galleryMatch = /^\/api\/entities\/([^/]+)\/gallery$/.exec(pathname)
      if (galleryMatch) return jsonResponse(res, 200, { images: [] })
      const similarMatch = /^\/api\/entities\/([^/]+)\/similar$/.exec(pathname)
      if (similarMatch) return jsonResponse(res, 200, { similar: [recommendationFixture()] })
      const entityMatch = /^\/api\/entities\/([^/]+)$/.exec(pathname)
      if (entityMatch) return jsonResponse(res, 200, detailFixture(entityMatch[1]))
      if (pathname.startsWith('/seo/jsonld/')) return jsonResponse(res, 200, null)

      if (pathname.startsWith('/api/') || pathname.startsWith('/auth/')) return jsonResponse(res, 200, {})
      return jsonResponse(res, 404, { detail: 'Fixture route not found' })
    } catch (error) {
      return jsonResponse(res, 500, { detail: error.message })
    }
  })
  return new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      resolve({ server, origin: `http://127.0.0.1:${address.port}` })
    })
  })
}

function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA, 'Google', 'Chrome', 'Application', 'chrome.exe') : '',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
  ].filter(Boolean)
  return candidates.find(candidate => existsSync(candidate))
}

async function waitForHttp(url, processRef, logs, timeoutMs = 90000) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    if (processRef?.exitCode != null) throw new Error(`Nuxt exited early (${processRef.exitCode}): ${logs.slice(-12).join('\n')}`)
    try {
      const response = await fetch(url)
      if (response.status < 500) return
    } catch {}
    await sleep(250)
  }
  throw new Error(`Timed out waiting for ${url}: ${logs.slice(-12).join('\n')}`)
}

class CdpClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl
    this.seq = 0
    this.pending = new Map()
    this.listeners = new Map()
  }

  connect() {
    if (typeof WebSocket === 'undefined') throw new Error('Node.js global WebSocket support is required')
    this.ws = new WebSocket(this.wsUrl)
    this.ws.onmessage = event => {
      const message = JSON.parse(event.data)
      if (message.id && this.pending.has(message.id)) {
        const entry = this.pending.get(message.id)
        clearTimeout(entry.timer)
        this.pending.delete(message.id)
        if (message.error) entry.reject(new Error(message.error.message || 'CDP error'))
        else entry.resolve(message.result || {})
        return
      }
      if (message.method && this.listeners.has(message.method)) {
        for (const listener of this.listeners.get(message.method)) listener(message.params || {})
      }
    }
    return new Promise((resolve, reject) => {
      this.ws.onopen = resolve
      this.ws.onerror = () => reject(new Error(`Cannot connect to Chrome CDP at ${this.wsUrl}`))
    })
  }

  send(method, params = {}, timeoutMs = 20000) {
    const id = ++this.seq
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id)
        reject(new Error(`CDP timeout: ${method}`))
      }, timeoutMs)
      this.pending.set(id, { resolve, reject, timer })
      this.ws.send(JSON.stringify({ id, method, params }))
    })
  }

  on(method, listener) {
    if (!this.listeners.has(method)) this.listeners.set(method, new Set())
    this.listeners.get(method).add(listener)
    return () => this.listeners.get(method).delete(listener)
  }

  waitFor(method, timeoutMs = 20000) {
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
  for (let index = 0; index < 80; index += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${chromePort}/json/version`)
      const data = await response.json()
      if (data.webSocketDebuggerUrl) return
    } catch {}
    await sleep(250)
  }
  throw new Error('Chrome did not expose CDP in time')
}

async function createPageTarget() {
  const endpoint = `http://127.0.0.1:${chromePort}/json/new?about:blank`
  let response = await fetch(endpoint, { method: 'PUT' })
  if (!response.ok) response = await fetch(endpoint)
  if (!response.ok) throw new Error(`Cannot create Chrome target: ${response.status}`)
  return (await response.json()).webSocketDebuggerUrl
}

async function evaluate(cdp, expression) {
  const response = await cdp.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
  if (response.exceptionDetails) throw new Error(response.exceptionDetails.text || 'Runtime evaluation failed')
  return response.result?.value
}

async function waitForPage(cdp, expression, label, timeoutMs = 20000) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    if (await evaluate(cdp, `Boolean(${expression})`)) return
    await sleep(100)
  }
  throw new Error(`Timed out waiting for ${label}`)
}

async function waitForNode(predicate, label, timeoutMs = 10000) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    if (predicate()) return
    await sleep(50)
  }
  throw new Error(`Timed out waiting for ${label}`)
}

async function navigate(cdp, route) {
  const loaded = cdp.waitFor('Page.loadEventFired').catch(() => {})
  await cdp.send('Page.navigate', { url: new URL(route, baseUrl).toString() })
  await loaded
  await sleep(settleMs)
}

async function reload(cdp) {
  const loaded = cdp.waitFor('Page.loadEventFired').catch(() => {})
  await cdp.send('Page.reload', { ignoreCache: true })
  await loaded
  await sleep(settleMs)
}

async function click(cdp, selector) {
  const clicked = await evaluate(cdp, `(() => { const node = document.querySelector(${JSON.stringify(selector)}); if (!node) return false; node.click(); return true })()`)
  if (!clicked) throw new Error(`Missing clickable selector: ${selector}`)
}

async function assertText(cdp, selector, expected) {
  await waitForPage(cdp, `document.querySelector(${JSON.stringify(selector)})?.textContent?.includes(${JSON.stringify(expected)})`, `${selector} containing ${expected}`)
}

async function captureBaseline(cdp, name, width, height, theme, reducedMotion = false, textZoom = 100) {
  await cdp.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width <= 390 })
  await cdp.send('Emulation.setEmulatedMedia', {
    media: 'screen',
    features: [
      { name: 'prefers-color-scheme', value: theme },
      { name: 'prefers-reduced-motion', value: reducedMotion ? 'reduce' : 'no-preference' },
    ],
  })
  await evaluate(cdp, `document.documentElement.classList.toggle('dark', ${theme === 'dark'}); document.documentElement.style.fontSize = '${textZoom}%'; window.scrollTo(0, 0)`)
  await sleep(150)
  const screenshot = await cdp.send('Page.captureScreenshot', { format: 'png', fromSurface: true })
  if (!screenshot.data || screenshot.data.length < 1000) throw new Error(`Empty visual baseline: ${name}`)
  const layout = await evaluate(cdp, `({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth, title: document.title, text: document.body.innerText.slice(0, 120) })`)
  if (!layout.title || !layout.text) throw new Error(`Blank page during baseline: ${name}`)
  if (layout.scrollWidth > Math.ceil(layout.width * 1.05)) throw new Error(`Horizontal overflow during baseline ${name}: ${layout.scrollWidth}/${layout.width}`)
  console.log(`[BASELINE] ${name} ${width}x${height} ${theme} reduced=${reducedMotion} text=${textZoom}% png=${screenshot.data.length}`)
  await evaluate(cdp, `document.documentElement.style.fontSize = ''`)
}

async function exerciseFlow(cdp) {
  await navigate(cdp, '/cai-dat#khu-vuc-de-xuat')
  await waitForPage(cdp, `document.querySelector('[role="dialog"][aria-label="Thiết lập khu vực và sở thích"]')`, 'initial personalization setup')
  if (await evaluate(cdp, 'window.__smokeGeoCalls')) throw new Error('Geolocation was called before a user gesture')

  await click(cdp, '[data-action="skip"]')
  await waitForPage(cdp, `!document.querySelector('[role="dialog"][aria-label="Thiết lập khu vực và sở thích"]')`, 'setup skip')
  console.log('[OK] registered fixture session can skip and configure later')

  await reload(cdp)
  await waitForPage(cdp, `document.querySelector('[role="dialog"][aria-label="Thiết lập khu vực và sở thích"]')`, 'reopened setup')
  await click(cdp, '[data-region="province-vl"]')
  await click(cdp, '[data-action="continue"]')
  await waitForNode(() => fixture.preferences.location_source === 'manual', 'manual region save')
  await click(cdp, '[data-interest="food"]')
  await click(cdp, '[data-action="continue"]')
  await waitForNode(() => fixture.preferences.explicit_interests.includes('food'), 'explicit interests save')
  if (await evaluate(cdp, 'window.__smokeGeoCalls')) throw new Error('Geolocation was called before clicking use-location')
  await click(cdp, '[data-action="use-location"]')
  await waitForNode(() => fixture.preferences.location_consent_state === 'denied', 'denial persistence')
  await assertText(cdp, '[role="dialog"] [role="status"]', 'bị từ chối')
  await click(cdp, '[data-action="skip"]')
  console.log('[OK] manual region/interests survive denied GPS and no pre-gesture prompt occurs')

  await navigate(cdp, '/tai-khoan')
  await waitForPage(cdp, `document.querySelector('[data-action="why-this"]')`, 'personalized recommendation disclosure')
  await click(cdp, '[data-action="why-this"]')
  await assertText(cdp, '[role="dialog"][data-why-this]', 'Vĩnh Long')
  await assertText(cdp, '[role="dialog"][data-why-this]', 'Ẩm thực')
  await click(cdp, '[aria-label="Đóng giải thích"]')

  await navigate(cdp, '/cai-dat#khu-vuc-de-xuat')
  await waitForPage(cdp, `document.querySelector('#khu-vuc-de-xuat:not([hidden])')`, 'preference panel')
  await click(cdp, '[data-region="province-bt"]')
  await waitForNode(() => fixture.preferences.region_id === 'province-bt', 'region change')
  await navigate(cdp, '/tai-khoan')
  await waitForPage(cdp, `document.querySelector('[data-action="why-this"]')`, 'updated recommendation')
  await click(cdp, '[data-action="why-this"]')
  await assertText(cdp, '[role="dialog"][data-why-this]', 'Bến Tre')
  console.log('[OK] region change updates the rendered explanation')

  await navigate(cdp, '/cai-dat#khu-vuc-de-xuat')
  await waitForPage(cdp, `document.querySelector('#khu-vuc-de-xuat:not([hidden])')`, 'settings before offline case')
  fixture.flags.failNextPreferencePatch = true
  const patchCountBeforeOffline = fixture.calls.preferencePatch
  await click(cdp, '[data-region="province-vl"]')
  await assertText(cdp, '#khu-vuc-de-xuat', 'Bến Tre')
  await evaluate(cdp, `window.__smokeOnline = false; window.dispatchEvent(new Event('offline'))`)
  await assertText(cdp, '#khu-vuc-de-xuat', 'Đang ngoại tuyến')
  await evaluate(cdp, `window.__smokeOnline = true`)
  await click(cdp, '[data-action="retry-preferences"]')
  await waitForNode(() => fixture.calls.preferenceGet > 1, 'offline retry refresh')
  if (fixture.calls.preferencePatch !== patchCountBeforeOffline + 1) throw new Error('Offline retry duplicated the failed mutation')
  console.log('[OK] offline failure preserves cached state and retry does not duplicate mutation')

  fixture.flags.conflictNextPreferencePatch = true
  await click(cdp, '[data-region="province-bt"]')
  await assertText(cdp, '#khu-vuc-de-xuat', 'Dữ liệu trên máy chủ đã thay đổi')
  await assertText(cdp, '#khu-vuc-de-xuat', 'Trà Vinh')
  await click(cdp, '[data-action="retry-conflict"]')
  await waitForNode(() => fixture.preferences.region_id === 'province-bt', 'conflict retry')
  console.log('[OK] conflict renders server state and retries explicitly')

  await click(cdp, '[data-action="reset-recommendations"]')
  await waitForNode(() => fixture.calls.reset === 1, 'first reset')
  const firstReset = clone(fixture.preferences)
  await click(cdp, '[data-action="reset-recommendations"]')
  await waitForNode(() => fixture.calls.reset === 2, 'second reset')
  if (fixture.preferences.recommendation_reset_at !== firstReset.recommendation_reset_at || fixture.preferences.revision !== firstReset.revision) {
    throw new Error('Repeated reset changed the idempotent reset snapshot')
  }
  console.log('[OK] repeated recommendation reset is idempotent')

  fixture.preferences = defaultPreferences()
  await evaluate(cdp, `window.__smokeGeoMode = 'success'; window.__smokeGeoCalls = 0`)
  await reload(cdp)
  await waitForPage(cdp, `document.querySelector('[role="dialog"][aria-label="Thiết lập khu vực và sở thích"]')`, 'isolated GPS setup')
  await click(cdp, '[data-region="province-vl"]')
  await click(cdp, '[data-action="continue"]')
  await click(cdp, '[data-action="continue"]')
  if (await evaluate(cdp, 'window.__smokeGeoCalls')) throw new Error('Successful GPS case prompted before click')
  await click(cdp, '[data-action="use-location"]')
  await assertText(cdp, '[role="dialog"]', 'Độ chính xác: Cấp tỉnh')
  await click(cdp, '[data-action="confirm-location"]')
  await waitForNode(() => fixture.preferences.location_consent_state === 'granted', 'GPS confirmation')
  if (!fixture.lastLocationBody || !('latitude' in fixture.lastLocationBody) || !('longitude' in fixture.lastLocationBody)) throw new Error('GPS resolution boundary did not receive transient coordinates')
  for (const key of ['latitude', 'longitude', 'gps', 'ip']) {
    if (key in fixture.preferences) throw new Error(`Raw location key persisted in preferences: ${key}`)
  }
  console.log('[OK] isolated GPS resolve requires explicit confirmation and persists no raw coordinates')

  await navigate(cdp, '/cai-dat#khu-vuc-de-xuat')
  await waitForPage(cdp, `document.querySelector('#khu-vuc-de-xuat:not([hidden])')`, 'settings before location off')
  const resolveCountBeforeOff = fixture.calls.locationResolve
  const ipCountBeforeOff = fixture.calls.ipResolve
  await click(cdp, '[data-action="toggle-location"]')
  await waitForNode(() => fixture.preferences.location_consent_state === 'off', 'location off')
  if (fixture.calls.locationResolve !== resolveCountBeforeOff || fixture.calls.ipResolve !== ipCountBeforeOff) throw new Error('Location off triggered GPS/IP resolution')
  await assertText(cdp, '#khu-vuc-de-xuat', 'khu vực thủ công vẫn được dùng')
  await click(cdp, '[data-action="toggle-personalization"]')
  await waitForNode(() => fixture.preferences.personalization_enabled === false, 'personalization off')
  await navigate(cdp, '/tai-khoan')
  await waitForPage(cdp, `document.querySelector('.smart-rec .card')`, 'public fallback recommendation')
  const personalizedSubtitle = await evaluate(cdp, `document.body.innerText.includes('Đang tinh chỉnh theo hoạt động gần đây của bạn.')`)
  if (personalizedSubtitle) throw new Error('Personalization-off surface still claims activity personalization')
  console.log('[OK] location off blocks GPS/IP and personalization off uses public fallback')

  const trustCases = [
    ['smoke-official', 'official', 'Nguồn chính thức', 'Mới cập nhật'],
    ['smoke-verified', 'verified', 'Đối tác xác minh kèm ngày', 'Cần kiểm tra định kỳ'],
    ['smoke-community', 'community', 'Nguồn cộng đồng', 'Có thể đã cũ'],
  ]
  for (const [id, tier, label, freshness] of trustCases) {
    await navigate(cdp, `/dia-diem/${id}`)
    await waitForPage(cdp, `document.querySelector('[data-action="open-source-trust"]')`, `${tier} trust trigger`)
    await click(cdp, '[data-action="open-source-trust"]')
    await assertText(cdp, '[role="dialog"][data-source-trust]', label)
    await assertText(cdp, '[role="dialog"][data-source-trust]', freshness)
    const observedTier = await evaluate(cdp, `document.querySelector('[data-source-trust]')?.dataset.sourceTier`)
    if (observedTier !== tier) throw new Error(`Trust tier mismatch: expected ${tier}, got ${observedTier}`)
  }
  console.log('[OK] official/verified/community and fresh/aging/stale remain separate')

  await navigate(cdp, '/cai-dat#khu-vuc-de-xuat')
  await waitForPage(cdp, `document.querySelector('#khu-vuc-de-xuat:not([hidden])')`, 'visual baseline settings panel')
  for (const [width, height] of [[1440, 1000], [1024, 768], [390, 844]]) {
    for (const theme of ['light', 'dark']) {
      await captureBaseline(cdp, `settings-${width}-${theme}`, width, height, theme)
    }
  }
  await captureBaseline(cdp, 'settings-mobile-dark-reduced', 390, 844, 'dark', true, 100)
  await captureBaseline(cdp, 'settings-mobile-light-text-200', 390, 844, 'light', false, 200)
  console.log(`[STITCH] ${Object.values(STITCH_SCREENS).join(', ')}`)
}

async function main() {
  const chromePath = findChrome()
  if (!chromePath) throw new Error('Chrome/Edge not found. Set CHROME_PATH to a Chromium executable.')
  const fixtureApi = await startFixtureApi()
  const appLogs = []
  const nuxtEntry = path.join(webRoot, 'node_modules', 'nuxt', 'bin', 'nuxt.mjs')
  if (!existsSync(nuxtEntry)) throw new Error(`Nuxt runtime not found at ${nuxtEntry}`)
  const app = spawn(process.execPath, [nuxtEntry, 'dev', '--no-fork', '--logLevel', 'info', '--host', '127.0.0.1', '--port', String(appPort)], {
    cwd: webRoot,
    env: { ...process.env, API_BASE: fixtureApi.origin, NUXT_PUBLIC_SITE_NOINDEX: 'true' },
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  })
  for (const stream of [app.stdout, app.stderr]) {
    stream.setEncoding('utf8')
    stream.on('data', chunk => {
      appLogs.push(...String(chunk).split(/\r?\n/).filter(Boolean))
      if (appLogs.length > 80) appLogs.splice(0, appLogs.length - 80)
    })
  }

  const userDataDir = await mkdtemp(path.join(tmpdir(), 'vl360-personalization-smoke-'))
  let chrome
  let cdp
  const runtimeFailures = []
  try {
    await waitForHttp(baseUrl, app, appLogs)
    chrome = spawn(chromePath, [
      '--headless=new',
      `--remote-debugging-port=${chromePort}`,
      `--user-data-dir=${userDataDir}`,
      '--disable-gpu',
      '--no-first-run',
      '--no-default-browser-check',
      'about:blank',
    ], { stdio: 'ignore', windowsHide: true })
    await waitForChrome()
    cdp = new CdpClient(await createPageTarget())
    await cdp.connect()
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Network.enable')
    await cdp.send('Log.enable')

    cdp.on('Runtime.consoleAPICalled', params => {
      if (['error', 'assert'].includes(params.type)) runtimeFailures.push(`console ${params.type}: ${(params.args || []).map(arg => arg.value || arg.description || '').join(' ').slice(0, 400)}`)
    })
    cdp.on('Runtime.exceptionThrown', params => runtimeFailures.push(`exception: ${params.exceptionDetails?.text || params.exceptionDetails?.exception?.description || 'unknown'}`))
    cdp.on('Network.responseReceived', params => {
      if ((params.response?.status || 0) >= 500 && !params.response.url.includes('/api/me/preferences')) runtimeFailures.push(`HTTP ${params.response.status} ${params.response.url}`)
    })

    const origin = new URL(baseUrl)
    await cdp.send('Network.setCookie', {
      name: 'vl360_token',
      value: 'fixture-session',
      domain: origin.hostname,
      path: '/',
      secure: false,
      sameSite: 'Lax',
    })
    await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
      source: `
        window.__smokeGeoCalls = 0;
        window.__smokeGeoMode = 'deny';
        window.__smokeOnline = true;
        Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => window.__smokeOnline });
        Object.defineProperty(navigator, 'geolocation', {
          configurable: true,
          value: {
            getCurrentPosition(success, error) {
              window.__smokeGeoCalls += 1;
              if (window.__smokeGeoMode === 'success') {
                success({ coords: { latitude: 10.24, longitude: 105.97, accuracy: 2400 } });
              } else {
                error({ code: 1, message: 'denied', PERMISSION_DENIED: 1 });
              }
            }
          }
        });
      `,
    })

    await exerciseFlow(cdp)
    if (runtimeFailures.length) throw new Error(`Rendered runtime failures:\n${[...new Set(runtimeFailures)].join('\n')}`)
    console.log('[PASS] personalization Chrome smoke completed')
  } finally {
    cdp?.close()
    chrome?.kill()
    app.kill()
    await new Promise(resolve => fixtureApi.server.close(resolve))
    await sleep(300)
    await rm(userDataDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 200 }).catch(() => {})
  }
}

main().catch(error => {
  console.error(error.stack || error.message)
  process.exit(1)
})
