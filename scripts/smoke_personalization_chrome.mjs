#!/usr/bin/env node
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { existsSync } from 'node:fs'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const webRoot = path.join(repoRoot, 'web-nuxt')
let baseUrl = ''
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
  user: null,
  registeredUser: {
    id: 'smoke-personalization-user',
    display_name: 'Người kiểm thử',
    username: 'smoke-personalization-user',
    phone: '0901234567',
    role: 'user',
    has_password: true,
  },
  preferences: defaultPreferences(),
  flags: { failNextPreferencePatch: false, conflictNextPreferencePatch: false },
  calls: {
    authMe: 0,
    checkPhone: 0,
    requestOtp: 0,
    verifyOtp: 0,
    preferencePatch: 0,
    preferenceGet: 0,
    locationResolve: 0,
    ipResolve: 0,
    reset: 0,
    contextual: 0,
    popular: 0,
  },
  locationEvidence: { gpsRequestValidated: false, ipRequestValidated: false },
  unknownRoutes: [],
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

      if (pathname === '/auth/me') {
        fixture.calls.authMe += 1
        return fixture.user
          ? jsonResponse(res, 200, { user: fixture.user })
          : jsonResponse(res, 401, { detail: 'No fixture session' })
      }
      if (pathname === '/auth/check-phone' && method === 'POST') {
        fixture.calls.checkPhone += 1
        const body = await readJson(req)
        return jsonResponse(res, 200, { exists: body.phone !== fixture.registeredUser.phone })
      }
      if (pathname.startsWith('/auth/check-username/')) return jsonResponse(res, 200, { available: true })
      if (pathname === '/auth/request-otp' && method === 'POST') {
        fixture.calls.requestOtp += 1
        return jsonResponse(res, 200, { success: true })
      }
      if (pathname === '/auth/verify-otp' && method === 'POST') {
        fixture.calls.verifyOtp += 1
        const body = await readJson(req)
        if (body.phone !== fixture.registeredUser.phone || body.code !== '123456' || !body.consent || !body.full_name || !body.username || !body.password) {
          return jsonResponse(res, 400, { detail: 'Invalid deterministic registration payload' })
        }
        fixture.user = clone(fixture.registeredUser)
        return jsonResponse(res, 200, { user: clone(fixture.user), has_password: true })
      }
      if (pathname === '/auth/csrf') return jsonResponse(res, 200, { csrf_token: 'fixture-csrf-token' })
      if (pathname === '/auth/privacy') return jsonResponse(res, 200, { profile_visibility: 'public', show_activity: true, show_saved: true })
      if (pathname === '/auth/consent-history') return jsonResponse(res, 200, { history: [] })
      if (pathname === '/api/site-settings') return jsonResponse(res, 200, {})
      if (pathname === '/api/notification-preferences') return jsonResponse(res, 200, {})
      if (pathname === '/api/saved') return jsonResponse(res, 200, { items: [] })
      if (pathname === '/api/notifications') return jsonResponse(res, 200, { notifications: [], unread_count: 0 })
      if (pathname === '/api/notifications/stream') {
        res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-store', connection: 'keep-alive' })
        return res.end()
      }
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
        const body = await readJson(req)
        if (body.mode === 'gps') {
          const valid = Number.isFinite(body.latitude)
            && Number.isFinite(body.longitude)
            && body.latitude >= -90
            && body.latitude <= 90
            && body.longitude >= -180
            && body.longitude <= 180
          fixture.locationEvidence.gpsRequestValidated = valid
          if (!valid) return jsonResponse(res, 400, { detail: 'Invalid GPS resolution payload' })
        } else if (body.mode === 'ip') {
          fixture.calls.ipResolve += 1
          fixture.locationEvidence.ipRequestValidated = Object.keys(body).every(key => key === 'mode')
          if (!fixture.locationEvidence.ipRequestValidated) return jsonResponse(res, 400, { detail: 'Invalid IP resolution payload' })
        } else {
          return jsonResponse(res, 400, { detail: 'Unknown location resolution mode' })
        }
        return jsonResponse(res, 200, {
          region_id: 'province-vl',
          region_label: 'Vĩnh Long',
          region_scope: 'province',
          location_source: body.mode,
          location_accuracy: 'province',
        })
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
      if (pathname === '/api/search') {
        return jsonResponse(res, 200, {
          entities: [recommendationFixture()],
          posts: [],
          users: [],
          totals: { entities: 1, posts: 0, users: 0 },
        })
      }
      if (pathname === '/api/community/stats') return jsonResponse(res, 200, { posts: 12, reviews: 4, members: 8 })
      if (pathname === '/api/community/trending-tags') return jsonResponse(res, 200, { tags: [] })
      if (pathname === '/api/community/leaderboard') return jsonResponse(res, 200, { leaders: [] })
      if (pathname === '/api/community/suggested-follows') return jsonResponse(res, 200, { users: [] })
      if (pathname === '/api/feed') return jsonResponse(res, 200, { posts: [], page: 1, total: 0, has_more: false })
      if (pathname === '/api/scheduled') return jsonResponse(res, 200, { scheduled: [] })
      if (pathname === '/api/me/counts') return jsonResponse(res, 200, { saved: 0, visited: 0, following: 0 })
      if (pathname === '/api/me/stats') return jsonResponse(res, 200, { posts: 0, reviews: 0, contributions: 0 })
      if (pathname === '/api/me/activity') return jsonResponse(res, 200, { items: [] })
      if (pathname === '/api/following') return jsonResponse(res, 200, { following: [] })
      if (pathname.startsWith('/api/me/visits/check/')) return jsonResponse(res, 200, { status: null })
      if (/^\/api\/events\/[^/]+\/rsvp$/.test(pathname)) return jsonResponse(res, 200, { count: 0, going: false })

      const galleryMatch = /^\/api\/entities\/([^/]+)\/gallery$/.exec(pathname)
      if (galleryMatch) return jsonResponse(res, 200, { images: [] })
      const similarMatch = /^\/api\/entities\/([^/]+)\/similar$/.exec(pathname)
      if (similarMatch) return jsonResponse(res, 200, { similar: [recommendationFixture()] })
      const feedMatch = /^\/api\/entities\/([^/]+)\/feed$/.exec(pathname)
      if (feedMatch) return jsonResponse(res, 200, { posts: [], total: 0, page: 1, has_more: false })
      const entityMatch = /^\/api\/entities\/([^/]+)$/.exec(pathname)
      if (entityMatch) return jsonResponse(res, 200, detailFixture(entityMatch[1]))
      if (/^\/api\/entities\/[^/]+\/relationships$/.test(pathname)) return jsonResponse(res, 200, { total: 0, relationships: [] })
      if (pathname.startsWith('/seo/jsonld/')) return jsonResponse(res, 200, null)

      fixture.unknownRoutes.push(`${method} ${pathname}`)
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

async function allocateLocalPort() {
  const reservation = createServer()
  await new Promise((resolve, reject) => {
    reservation.once('error', reject)
    reservation.listen(0, '127.0.0.1', resolve)
  })
  const address = reservation.address()
  const port = address.port
  await new Promise(resolve => reservation.close(resolve))
  return port
}

async function waitForOwnedApp(origin, processRef, logs, fixtureState, timeoutMs = 90000) {
  const authMeBefore = fixtureState.calls.authMe
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    if (processRef?.exitCode != null) throw new Error(`Nuxt exited early (${processRef.exitCode}): ${logs.slice(-12).join('\n')}`)
    try {
      const response = await fetch(`${origin}/auth/me`, { redirect: 'manual' })
      if ([200, 401].includes(response.status) && fixtureState.calls.authMe > authMeBefore) return
    } catch {}
    await sleep(250)
  }
  throw new Error(`Timed out waiting for Nuxt ownership at ${origin}: ${logs.slice(-12).join('\n')}`)
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

async function waitForOwnedChrome(processRef, userDataDir, timeoutMs = 20000) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    if (processRef?.exitCode != null) throw new Error(`Chrome exited before exposing owned CDP (${processRef.exitCode})`)
    try {
      const activePort = await readFile(path.join(userDataDir, 'DevToolsActivePort'), 'utf8')
      const [portText, browserPath] = activePort.trim().split(/\r?\n/)
      const port = Number(portText)
      if (!Number.isInteger(port) || port <= 0 || !browserPath?.startsWith('/devtools/browser/')) throw new Error('Malformed DevToolsActivePort')
      const response = await fetch(`http://127.0.0.1:${port}/json/version`)
      const data = await response.json()
      const endpoint = new URL(data.webSocketDebuggerUrl)
      if (Number(endpoint.port) === port && endpoint.pathname === browserPath) {
        return { port, browserWsUrl: data.webSocketDebuggerUrl }
      }
    } catch {}
    await sleep(250)
  }
  throw new Error(`Task-owned Chrome profile did not expose CDP within ${timeoutMs}ms`)
}

async function createPageTarget(chromePort) {
  const endpoint = `http://127.0.0.1:${chromePort}/json/new?about:blank`
  let response = await fetch(endpoint, { method: 'PUT' })
  if (!response.ok) response = await fetch(endpoint)
  if (!response.ok) throw new Error(`Cannot create Chrome target: ${response.status}`)
  const target = await response.json()
  if (!target.id || !target.webSocketDebuggerUrl) throw new Error('Chrome target response is incomplete')
  return { id: target.id, webSocketDebuggerUrl: target.webSocketDebuggerUrl }
}

async function closePageTarget(chromePort, targetId) {
  const response = await fetch(`http://127.0.0.1:${chromePort}/json/close/${encodeURIComponent(targetId)}`)
  if (!response.ok) throw new Error(`Cannot close Chrome target ${targetId}: ${response.status}`)
}

async function waitForChildExit(child, timeoutMs) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return true
  return await new Promise((resolve) => {
    const timer = setTimeout(() => {
      child.off('exit', onExit)
      resolve(false)
    }, timeoutMs)
    const onExit = () => {
      clearTimeout(timer)
      resolve(true)
    }
    child.once('exit', onExit)
  })
}

async function stopChild(child, label, timeoutMs = 5000) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return
  if (!child.pid) throw new Error(`${label} has no owned process id`)
  if (process.platform === 'win32') {
    const killer = spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true })
    await waitForChildExit(killer, timeoutMs)
  } else {
    child.kill('SIGTERM')
    if (!await waitForChildExit(child, Math.min(timeoutMs, 2500))) child.kill('SIGKILL')
  }
  if (!await waitForChildExit(child, timeoutMs)) throw new Error(`${label} process ${child.pid} did not exit within ${timeoutMs}ms`)
}

async function cleanupSmokeResources({ cdp, closeTarget, chrome, app, fixtureApi, userDataDir }) {
  const errors = []
  async function cleanup(label, action) {
    try {
      await action()
    } catch (error) {
      errors.push(`${label}: ${error.message}`)
    }
  }
  if (closeTarget) await cleanup('target', closeTarget)
  if (cdp) await cleanup('cdp', async () => cdp.close())
  if (chrome) await cleanup('chrome', () => stopChild(chrome, 'Chrome'))
  if (app) await cleanup('nuxt', () => stopChild(app, 'Nuxt'))
  if (fixtureApi?.server) {
    await cleanup('fixture-api', async () => {
      fixtureApi.server.closeAllConnections?.()
      if (fixtureApi.server.listening) await new Promise((resolve, reject) => fixtureApi.server.close(error => error ? reject(error) : resolve()))
    })
  }
  if (userDataDir) await cleanup('profile', () => rm(userDataDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 200 }))
  if (errors.length) throw new Error(`Smoke cleanup failed:\n${errors.join('\n')}`)
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

async function prepareGpsSuccess(cdp) {
  await reload(cdp)
  await evaluate(cdp, `window.__smokeGeoMode = 'success'; window.__smokeGeoCalls = 0`)
}

async function click(cdp, selector) {
  const clicked = await evaluate(cdp, `(() => { const node = document.querySelector(${JSON.stringify(selector)}); if (!node) return false; node.click(); return true })()`)
  if (!clicked) throw new Error(`Missing clickable selector: ${selector}`)
}

async function setInputValue(cdp, selector, value, index = 0) {
  const updated = await evaluate(cdp, `(() => {
    const node = document.querySelectorAll(${JSON.stringify(selector)})[${index}];
    if (!node) return false;
    const descriptor = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(node), 'value');
    descriptor?.set?.call(node, ${JSON.stringify(value)});
    node.dispatchEvent(new Event('input', { bubbles: true }));
    node.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  })()`)
  if (!updated) throw new Error(`Missing input selector: ${selector}[${index}]`)
}

async function assertText(cdp, selector, expected) {
  await waitForPage(cdp, `document.querySelector(${JSON.stringify(selector)})?.textContent?.includes(${JSON.stringify(expected)})`, `${selector} containing ${expected}`)
}

function visualConfigurations() {
  return [
    { key: 'desktop-wide-light', width: 1440, height: 1000, theme: 'light', reducedMotion: false, textZoom: 100 },
    { key: 'desktop-wide-dark', width: 1440, height: 1000, theme: 'dark', reducedMotion: false, textZoom: 100 },
    { key: 'desktop-compact-light', width: 1024, height: 768, theme: 'light', reducedMotion: false, textZoom: 100 },
    { key: 'desktop-compact-dark', width: 1024, height: 768, theme: 'dark', reducedMotion: false, textZoom: 100 },
    { key: 'mobile-light', width: 390, height: 844, theme: 'light', reducedMotion: false, textZoom: 100 },
    { key: 'mobile-dark', width: 390, height: 844, theme: 'dark', reducedMotion: false, textZoom: 100 },
    { key: 'mobile-dark-reduced', width: 390, height: 844, theme: 'dark', reducedMotion: true, textZoom: 100 },
    { key: 'mobile-light-text-200', width: 390, height: 844, theme: 'light', reducedMotion: false, textZoom: 200 },
  ]
}

const VISUAL_SURFACES = Object.freeze([
  {
    key: 'detail',
    stitch: STITCH_SCREENS.detailV2,
    route: '/dia-diem/smoke-official',
    selector: '.entity-detail-page',
    requiredSelectors: ['[data-entity-hero]', '[data-action="open-source-trust"]'],
  },
  {
    key: 'community',
    stitch: STITCH_SCREENS.community,
    route: '/cong-dong',
    selector: '.threads-page',
    requiredSelectors: ['.almanac-masthead', '.threads-layout'],
  },
  {
    key: 'search',
    stitch: STITCH_SCREENS.search,
    route: '/tim-kiem',
    selector: '.search-hero',
    requiredSelectors: ['input[type="search"]', 'button'],
  },
  {
    key: 'settings',
    stitch: STITCH_SCREENS.savedItinerary,
    route: '/cai-dat#khu-vuc-de-xuat',
    selector: '#khu-vuc-de-xuat:not([hidden])',
    requiredSelectors: ['[data-action="toggle-location"]', '[data-action="toggle-personalization"]', '[data-action="reset-recommendations"]'],
  },
  {
    key: 'why-this',
    stitch: STITCH_SCREENS.search,
    route: '/tai-khoan',
    selector: '[role="dialog"][data-why-this]',
    openSelector: '[data-action="why-this"]',
    requiredSelectors: ['.why-signal-stack', '[data-action="reset"]', '[data-action="open-preferences"]'],
  },
  {
    key: 'source-trust',
    stitch: STITCH_SCREENS.detailV2,
    route: '/dia-diem/smoke-community',
    selector: '[role="dialog"][data-source-trust]',
    openSelector: '[data-action="open-source-trust"]',
    requiredSelectors: ['.tier-panel', '.trust-evidence', '[data-action="report"]'],
  },
])

async function inspectSurface(cdp, surface, entry) {
  const result = await evaluate(cdp, `(() => {
    const root = document.querySelector(${JSON.stringify(surface.selector)});
    if (!root) return { missingRoot: true };
    const style = getComputedStyle(root);
    const rect = root.getBoundingClientRect();
    const visible = style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity || 1) > 0 && rect.width > 0 && rect.height > 0;
    const requiredMissing = ${JSON.stringify(surface.requiredSelectors)}.filter(selector => !root.querySelector(selector));
    const nodes = [root, ...root.querySelectorAll('*')];
    const durationMs = value => String(value || '').split(',').reduce((max, token) => {
      const text = token.trim();
      const number = Number.parseFloat(text) || 0;
      return Math.max(max, text.endsWith('ms') ? number : number * 1000);
    }, 0);
    const maxMotionMs = nodes.reduce((max, node) => {
      const computed = getComputedStyle(node);
      return Math.max(max, durationMs(computed.animationDuration), durationMs(computed.transitionDuration));
    }, 0);
    const focusables = [...root.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')]
      .filter(node => {
        const nodeStyle = getComputedStyle(node);
        const nodeRect = node.getBoundingClientRect();
        return nodeStyle.display !== 'none' && nodeStyle.visibility !== 'hidden' && nodeRect.width > 0 && nodeRect.height > 0;
      });
    const clippedControls = focusables.filter(node => {
      const nodeRect = node.getBoundingClientRect();
      return nodeRect.left < -2 || nodeRect.right > innerWidth + 2;
    }).length;
    const firstControl = focusables[0];
    firstControl?.focus();
    return {
      missingRoot: false,
      visible,
      requiredMissing,
      focusableCount: focusables.length,
      focusAccepted: !!firstControl && document.activeElement === firstControl && root.contains(document.activeElement),
      clippedControls,
      maxMotionMs,
      viewportWidth: innerWidth,
      documentScrollWidth: document.documentElement.scrollWidth,
      rootLeft: rect.left,
      rootRight: rect.right,
      title: document.title,
      text: root.textContent?.trim().slice(0, 160) || '',
    };
  })()`)
  if (result.missingRoot || !result.visible) throw new Error(`Missing or hidden surface: ${surface.key}`)
  if (result.requiredMissing.length) throw new Error(`Missing ${surface.key} anatomy: ${result.requiredMissing.join(', ')}`)
  if (!result.title || !result.text) throw new Error(`Blank rendered surface: ${surface.key}`)
  if (result.focusableCount < 1 || !result.focusAccepted) throw new Error(`No visible focusable control on ${surface.key}`)
  if (result.clippedControls > 0) throw new Error(`Horizontally clipped controls on ${surface.key}: ${result.clippedControls}`)
  if (result.documentScrollWidth > result.viewportWidth + 4 || result.rootLeft < -2 || result.rootRight > result.viewportWidth + 2) {
    throw new Error(`Horizontal overflow on ${surface.key}: document=${result.documentScrollWidth}/${result.viewportWidth}, root=${result.rootLeft}/${result.rootRight}`)
  }
  if (entry.reducedMotion && result.maxMotionMs > 1) throw new Error(`Reduced-motion surface ${surface.key} retains ${result.maxMotionMs}ms motion`)
  return result
}

async function captureBaseline(cdp, surface, entry) {
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: entry.width, height: entry.height, deviceScaleFactor: 1, mobile: entry.width <= 390 })
  await cdp.send('Emulation.setEmulatedMedia', {
    media: 'screen',
    features: [
      { name: 'prefers-color-scheme', value: entry.theme },
      { name: 'prefers-reduced-motion', value: entry.reducedMotion ? 'reduce' : 'no-preference' },
    ],
  })
  await evaluate(cdp, `document.documentElement.classList.toggle('dark', ${entry.theme === 'dark'}); document.documentElement.style.fontSize = '${entry.textZoom}%'; document.querySelector(${JSON.stringify(surface.selector)})?.scrollIntoView({ block: 'start' })`)
  await sleep(150)
  const inspection = await inspectSurface(cdp, surface, entry)
  const screenshot = await cdp.send('Page.captureScreenshot', { format: 'png', fromSurface: true })
  if (!screenshot.data || screenshot.data.length < 1000) throw new Error(`Empty visual baseline: ${surface.key}-${entry.key}`)
  console.log(`[BASELINE] ${surface.key}-${entry.key} stitch=${surface.stitch} focusable=${inspection.focusableCount} motion=${inspection.maxMotionMs}ms png=${screenshot.data.length}`)
  await evaluate(cdp, `document.documentElement.style.fontSize = ''`)
}

function visualMatrixPlan() {
  return VISUAL_SURFACES.flatMap(surface => visualConfigurations().map(configuration => ({ surface: surface.key, ...configuration })))
}

async function captureVisualMatrix(cdp) {
  fixture.preferences = {
    ...defaultPreferences(),
    region_id: 'province-vl',
    region_label: 'Vĩnh Long',
    region_scope: 'province',
    location_source: 'manual',
    location_accuracy: 'province',
    personalization_enabled: true,
    explicit_interests: ['food'],
    revision: 1,
  }
  for (const surface of VISUAL_SURFACES) {
    await navigate(cdp, surface.route)
    if (surface.openSelector) {
      await waitForPage(cdp, `document.querySelector(${JSON.stringify(surface.openSelector)})`, `${surface.key} disclosure trigger`)
      await click(cdp, surface.openSelector)
    }
    await waitForPage(cdp, `document.querySelector(${JSON.stringify(surface.selector)})`, `${surface.key} visual surface`)
    for (const entry of visualConfigurations()) await captureBaseline(cdp, surface, entry)
  }
  console.log(`[STITCH VERIFIED IF EXECUTED] ${VISUAL_SURFACES.map(surface => `${surface.key}:${surface.stitch}`).join(', ')}`)
}

async function exerciseRegistration(cdp) {
  await navigate(cdp, '/tim-kiem')
  await waitForPage(cdp, `document.querySelector('.auth-btn')`, 'guest login control')
  await click(cdp, '.auth-btn')
  await waitForPage(cdp, `document.querySelector('#auth-modal-title')`, 'authentication dialog')
  await setInputValue(cdp, 'input[autocomplete="tel"]', fixture.registeredUser.phone)
  await click(cdp, '.consent-checkbox')
  await click(cdp, '.otp-step .btn-primary')
  await assertText(cdp, '.otp-step .step-label', 'Tạo tài khoản')
  await setInputValue(cdp, 'input[autocomplete="name"]', fixture.registeredUser.display_name)
  await setInputValue(cdp, 'input[autocomplete="username"]', fixture.registeredUser.username)
  await setInputValue(cdp, 'input[autocomplete="new-password"]', 'SmokePass123', 0)
  await setInputValue(cdp, 'input[autocomplete="new-password"]', 'SmokePass123', 1)
  await click(cdp, '.otp-step .btn-primary')
  await assertText(cdp, '.otp-step .step-label', 'Nhập mã OTP')
  for (let index = 0; index < 6; index += 1) await setInputValue(cdp, '.otp-input input', String(index + 1), index)
  await click(cdp, '.otp-step .btn-primary')
  await assertText(cdp, '.otp-step .step-label', 'Đăng ký thành công')
  await click(cdp, '.otp-done .btn-primary')
  await waitForPage(cdp, `document.querySelector('.auth-user')`, 'registered fixture session')
  if (!fixture.user || fixture.calls.checkPhone !== 1 || fixture.calls.requestOtp !== 1 || fixture.calls.verifyOtp !== 1) {
    throw new Error(`Registration boundary mismatch: ${JSON.stringify({ user: !!fixture.user, calls: fixture.calls })}`)
  }
}

async function exerciseFlow(cdp) {
  await exerciseRegistration(cdp)
  await waitForPage(cdp, `document.querySelector('[role="dialog"][aria-label="Thiết lập khu vực và sở thích"]')`, 'initial personalization setup')
  if (await evaluate(cdp, 'window.__smokeGeoCalls')) throw new Error('Geolocation was called before a user gesture')

  await click(cdp, '[data-action="skip"]')
  await waitForPage(cdp, `!document.querySelector('[role="dialog"][aria-label="Thiết lập khu vực và sở thích"]')`, 'setup skip')
  console.log('[OK] credential-free registration reaches a session that can skip setup')

  await navigate(cdp, '/cai-dat#khu-vuc-de-xuat')
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
  await prepareGpsSuccess(cdp)
  await waitForPage(cdp, `document.querySelector('[role="dialog"][aria-label="Thiết lập khu vực và sở thích"]')`, 'isolated GPS setup')
  await click(cdp, '[data-region="province-vl"]')
  await click(cdp, '[data-action="continue"]')
  await click(cdp, '[data-action="continue"]')
  if (await evaluate(cdp, 'window.__smokeGeoCalls')) throw new Error('Successful GPS case prompted before click')
  await click(cdp, '[data-action="use-location"]')
  await assertText(cdp, '[role="dialog"]', 'Độ chính xác: Cấp tỉnh')
  await click(cdp, '[data-action="confirm-location"]')
  await waitForNode(() => fixture.preferences.location_consent_state === 'granted', 'GPS confirmation')
  const geolocationCalls = await evaluate(cdp, 'window.__smokeGeoCalls')
  if (geolocationCalls !== 1) throw new Error(`Expected one geolocation call after the user gesture, received ${geolocationCalls}`)
  if (!fixture.locationEvidence.gpsRequestValidated) throw new Error('GPS resolution boundary did not validate transient coordinates')
  for (const key of ['latitude', 'longitude', 'gps', 'ip']) {
    if (key in fixture.preferences) throw new Error(`Raw location key persisted in preferences: ${key}`)
  }
  const retainedFixtureState = JSON.stringify(fixture)
  if (retainedFixtureState.includes('10.24') || retainedFixtureState.includes('105.97') || retainedFixtureState.includes('latitude') || retainedFixtureState.includes('longitude')) {
    throw new Error('Fixture retained raw GPS evidence after request validation')
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

  await captureVisualMatrix(cdp)
  if (fixture.unknownRoutes.length) throw new Error(`Incomplete fixture routes:\n${[...new Set(fixture.unknownRoutes)].join('\n')}`)
}

async function runSelfTests() {
  const failures = []
  async function check(name, test) {
    try {
      await test()
      console.log(`[SELF-TEST PASS] ${name}`)
    } catch (error) {
      failures.push(`${name}: ${error.message}`)
      console.error(`[SELF-TEST FAIL] ${name}: ${error.message}`)
    }
  }

  await check('GPS success is configured on the reloaded document', async () => {
    const documentState = { mode: 'deny', calls: 7 }
    const cdp = {
      waitFor: async () => {},
      send: async (method, params = {}) => {
        if (method === 'Page.reload') {
          documentState.mode = 'deny'
          documentState.calls = 0
        }
        if (method === 'Runtime.evaluate') {
          if (params.expression.includes("__smokeGeoMode = 'success'")) documentState.mode = 'success'
          if (params.expression.includes('__smokeGeoCalls = 0')) documentState.calls = 0
          return { result: { value: undefined } }
        }
        return {}
      },
    }
    await prepareGpsSuccess(cdp)
    assert.equal(documentState.mode, 'success')
    assert.equal(documentState.calls, 0)
  })

  const fixtureApi = await startFixtureApi()
  try {
    await check('fixture discards raw GPS coordinates after validation', async () => {
      const response = await fetch(`${fixtureApi.origin}/api/me/location/resolve`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ mode: 'gps', latitude: 10.24, longitude: 105.97 }),
      })
      assert.equal(response.status, 200)
      const retained = JSON.stringify(fixture)
      assert.equal(retained.includes('10.24'), false)
      assert.equal(retained.includes('105.97'), false)
      assert.equal(retained.includes('latitude'), false)
      assert.equal(retained.includes('longitude'), false)
    })

    await check('fixture begins unauthenticated before registration', async () => {
      const response = await fetch(`${fixtureApi.origin}/auth/me`)
      assert.equal(response.status, 401)
    })

    await check('fixture fails closed for unknown API routes', async () => {
      const response = await fetch(`${fixtureApi.origin}/api/not-a-smoke-route`)
      assert.equal(response.status, 404)
    })
  } finally {
    fixtureApi.server.closeAllConnections?.()
    await new Promise(resolve => fixtureApi.server.close(resolve))
  }

  await check('visual matrix includes every required surface and accessibility mode', () => {
    const plan = visualMatrixPlan()
    assert.deepEqual([...new Set(plan.map(entry => entry.surface))].sort(), ['community', 'detail', 'search', 'settings', 'source-trust', 'why-this'])
    for (const surface of ['community', 'detail', 'search', 'settings', 'source-trust', 'why-this']) {
      const entries = plan.filter(entry => entry.surface === surface)
      assert.equal(entries.some(entry => entry.reducedMotion), true, `${surface} lacks reduced-motion coverage`)
      assert.equal(entries.some(entry => entry.textZoom === 200), true, `${surface} lacks 200% text coverage`)
      assert.equal(entries.some(entry => entry.width === 1440 && entry.theme === 'light'), true, `${surface} lacks desktop light coverage`)
      assert.equal(entries.some(entry => entry.width === 390 && entry.theme === 'dark'), true, `${surface} lacks mobile dark coverage`)
    }
  })

  await check('app readiness rejects an unrelated listener without fixture ownership', async () => {
    const unrelated = createServer((_req, res) => jsonResponse(res, 200, { user: fixture.registeredUser }))
    await new Promise((resolve, reject) => {
      unrelated.once('error', reject)
      unrelated.listen(0, '127.0.0.1', resolve)
    })
    const address = unrelated.address()
    const before = fixture.calls.authMe
    try {
      await assert.rejects(
        waitForOwnedApp(`http://127.0.0.1:${address.port}`, { exitCode: null }, [], fixture, 250),
        /ownership/i,
      )
      assert.equal(fixture.calls.authMe, before)
    } finally {
      unrelated.closeAllConnections?.()
      await new Promise(resolve => unrelated.close(resolve))
    }
  })

  await check('CDP endpoint is derived from the task-owned Chrome profile', async () => {
    const profileDir = await mkdtemp(path.join(tmpdir(), 'vl360-cdp-owner-self-test-'))
    const fakeCdp = createServer((req, res) => {
      if (req.url === '/json/version') {
        return jsonResponse(res, 200, { webSocketDebuggerUrl: `ws://127.0.0.1:${fakeCdp.address().port}/devtools/browser/owned-token` })
      }
      return jsonResponse(res, 404, { detail: 'not found' })
    })
    await new Promise((resolve, reject) => {
      fakeCdp.once('error', reject)
      fakeCdp.listen(0, '127.0.0.1', resolve)
    })
    const port = fakeCdp.address().port
    await writeFile(path.join(profileDir, 'DevToolsActivePort'), `${port}\n/devtools/browser/owned-token\n`, 'utf8')
    try {
      const owned = await waitForOwnedChrome({ exitCode: null }, profileDir, 1000)
      assert.deepEqual(owned, { port, browserWsUrl: `ws://127.0.0.1:${port}/devtools/browser/owned-token` })
    } finally {
      fakeCdp.closeAllConnections?.()
      await new Promise(resolve => fakeCdp.close(resolve))
      await rm(profileDir, { recursive: true, force: true })
    }
  })

  await check('early failure cleanup closes target, server, process, and temp profile', async () => {
    const fixtureApi = await startFixtureApi()
    const profileDir = await mkdtemp(path.join(tmpdir(), 'vl360-cleanup-self-test-'))
    const child = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { stdio: 'ignore', windowsHide: true })
    let targetClosed = false
    let cdpClosed = false
    try {
      await cleanupSmokeResources({
        cdp: { close: () => { cdpClosed = true } },
        closeTarget: async () => { targetClosed = true },
        chrome: child,
        app: null,
        fixtureApi,
        userDataDir: profileDir,
      })
      assert.equal(targetClosed, true)
      assert.equal(cdpClosed, true)
      assert.equal(child.exitCode !== null || child.signalCode !== null, true)
      assert.equal(fixtureApi.server.listening, false)
      assert.equal(existsSync(profileDir), false)
    } finally {
      if (child.exitCode === null && child.signalCode === null) child.kill()
      if (fixtureApi.server.listening) {
        fixtureApi.server.closeAllConnections?.()
        await new Promise(resolve => fixtureApi.server.close(resolve))
      }
      await rm(profileDir, { recursive: true, force: true }).catch(() => {})
    }
  })

  if (failures.length) throw new Error(`Smoke self-tests failed:\n${failures.join('\n')}`)
  console.log('[SELF-TEST PASS] all smoke runner checks passed')
}

async function main() {
  const chromePath = findChrome()
  if (!chromePath) throw new Error('Chrome/Edge not found. Set CHROME_PATH to a Chromium executable.')
  const nuxtEntry = path.join(webRoot, 'node_modules', 'nuxt', 'bin', 'nuxt.mjs')
  if (!existsSync(nuxtEntry)) throw new Error(`Nuxt runtime not found at ${nuxtEntry}`)
  let fixtureApi
  let app
  let userDataDir
  let chrome
  let cdp
  let chromeOwnership
  let target
  let failure
  const appLogs = []
  const runtimeFailures = []
  try {
    const appPort = process.env.SMOKE_APP_PORT ? Number(process.env.SMOKE_APP_PORT) : await allocateLocalPort()
    if (!Number.isInteger(appPort) || appPort <= 0 || appPort > 65535) throw new Error(`Invalid SMOKE_APP_PORT: ${process.env.SMOKE_APP_PORT}`)
    baseUrl = process.env.SMOKE_BASE_URL || `http://127.0.0.1:${appPort}`
    if (Number(new URL(baseUrl).port || 80) !== appPort) throw new Error('SMOKE_BASE_URL port must match SMOKE_APP_PORT')

    fixtureApi = await startFixtureApi()
    app = spawn(process.execPath, [nuxtEntry, 'dev', '--no-fork', '--logLevel', 'info', '--host', '127.0.0.1', '--port', String(appPort)], {
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
    await waitForOwnedApp(baseUrl, app, appLogs, fixture)

    userDataDir = await mkdtemp(path.join(tmpdir(), 'vl360-personalization-smoke-'))
    chrome = spawn(chromePath, [
      '--headless=new',
      '--remote-debugging-port=0',
      `--user-data-dir=${userDataDir}`,
      '--disable-gpu',
      '--no-first-run',
      '--no-default-browser-check',
      'about:blank',
    ], { stdio: 'ignore', windowsHide: true })
    chromeOwnership = await waitForOwnedChrome(chrome, userDataDir)
    target = await createPageTarget(chromeOwnership.port)
    cdp = new CdpClient(target.webSocketDebuggerUrl)
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
  } catch (error) {
    failure = error
  }
  try {
    await cleanupSmokeResources({
      cdp,
      closeTarget: target && chromeOwnership ? () => closePageTarget(chromeOwnership.port, target.id) : null,
      chrome,
      app,
      fixtureApi,
      userDataDir,
    })
  } catch (cleanupError) {
    if (failure) throw new AggregateError([failure, cleanupError], `${failure.message}\n${cleanupError.message}`)
    throw cleanupError
  }
  if (failure) throw failure
}

const entry = process.argv.includes('--self-test') ? runSelfTests : main
entry().catch(error => {
  console.error(error.stack || error.message)
  process.exit(1)
})
