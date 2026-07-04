#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'

const baseUrl = process.env.SMOKE_BASE_URL || 'http://localhost:3000'
const apiBaseUrl = process.env.SMOKE_API_BASE_URL || baseUrl
const phone = process.env.SMOKE_PHONE || '0909090909'
const password = process.env.SMOKE_PASSWORD || 'PassHomnay.2'
const username = process.env.SMOKE_USERNAME || 'testuser09'
const port = Number(process.env.SMOKE_CDP_PORT || 9223)
const settleMs = Number(process.env.SMOKE_SETTLE_MS || 1200)

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
    selectors: ['.cat-map', '#mapContainer'],
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

async function main() {
  const chromePath = findChrome()
  if (!chromePath) throw new Error('Chrome/Edge not found. Set CHROME_PATH to a Chromium executable.')

  const token = await login()
  const userDataDir = await mkdtemp(path.join(tmpdir(), 'vl360-smoke-'))
  const chrome = spawn(chromePath, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    'about:blank',
  ], { stdio: 'ignore' })

  const failures = []
  let cdp
  try {
    await waitForChrome()
    cdp = new CdpClient(await createPageTarget())
    await cdp.connect()
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Network.enable')
    await cdp.send('Log.enable')

    const base = new URL(baseUrl)
    await cdp.send('Network.setCookie', {
      name: 'vl360_token',
      value: token,
      domain: base.hostname,
      path: '/',
      secure: base.protocol === 'https:',
      sameSite: 'Lax',
    })

    for (const route of routes) {
      const routeFailures = []
      const routeAssetFailures = []
      const offConsole = cdp.on('Runtime.consoleAPICalled', params => {
        if (['error', 'assert'].includes(params.type)) routeFailures.push(`console ${summarizeConsole(params)}`)
      })
      const offException = cdp.on('Runtime.exceptionThrown', params => {
        routeFailures.push(`exception ${redactSensitiveText(params.exceptionDetails?.text || params.exceptionDetails?.exception?.description || '').slice(0, 500)}`)
      })
      const offLog = cdp.on('Log.entryAdded', params => {
        if (params.entry?.level === 'error') {
          const entry = params.entry
          const suffix = entry.url ? ` (${redactSensitiveUrl(entry.url)}${entry.networkRequestId ? ` #${entry.networkRequestId}` : ''})` : ''
          const failure = `log ${redactSensitiveText(entry.text)}${suffix}`
          if (String(entry.text || '').includes('net::ERR_FAILED') && entry.url && isSameOriginNuxtAsset(entry.url)) {
            routeAssetFailures.push({ url: entry.url, failure })
          } else {
            routeFailures.push(failure)
          }
        }
      })
      const offResponse = cdp.on('Network.responseReceived', params => {
        const status = params.response?.status || 0
        if (status >= 500) routeFailures.push(`HTTP ${status} ${redactSensitiveUrl(params.response.url)}`)
      })

      const load = cdp.waitFor('Page.loadEventFired', 20000).catch(err => {
        routeFailures.push(err.message)
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
        if (!(await probeSameOriginAsset(item.url))) routeFailures.push(item.failure)
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
  } finally {
    cdp?.close()
    chrome.kill()
    await sleep(500)
    if (!process.env.SMOKE_KEEP_BROWSER) {
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

main().catch(err => {
  console.error(err.stack || err.message)
  process.exit(1)
})
