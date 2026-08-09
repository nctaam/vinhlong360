import { spawn } from 'node:child_process'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const previewUrl = 'http://127.0.0.1:4173/'
const mainVisibleBudgetMs = 5000

export function evaluatePublicAccessibilitySnapshot(snapshot) {
  const reasons = []
  if (!snapshot.forcedColorsActive) reasons.push('forced-colors-inactive')
  if (snapshot.forcedColorAdjust !== 'auto') reasons.push('forced-color-adjust-not-auto')
  if (!snapshot.forcedControlBorderVisible) reasons.push('forced-control-border-missing')
  if (snapshot.devicePixelRatio < 2
    || Math.abs((snapshot.viewportWidth * 2) - snapshot.screenWidth) > 2) reasons.push('zoom-layout-not-2x')
  if (snapshot.horizontalOverflow > 0) reasons.push('horizontal-overflow')
  if (!snapshot.mainVisible) reasons.push('main-content-hidden')
  if (snapshot.controlsBelow44 > 0) reasons.push('undersized-controls')
  if (snapshot.mainVisibleMs > mainVisibleBudgetMs) reasons.push('main-visible-budget-exceeded')
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

async function launchChrome(chromePath, profileDir) {
  const child = spawn(chromePath, [
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

  const websocketUrl = await new Promise((resolveUrl, reject) => {
    const timer = setTimeout(() => reject(new Error('Chrome CDP startup timed out')), 20000)
    child.once('error', reject)
    child.stderr.setEncoding('utf8')
    child.stderr.on('data', chunk => {
      const match = chunk.match(/DevTools listening on (ws:\/\/[^\s]+)/)
      if (!match) return
      clearTimeout(timer)
      resolveUrl(match[1])
    })
  })

  const port = new URL(websocketUrl).port
  const targets = await fetch(`http://127.0.0.1:${port}/json/list`).then(response => response.json())
  const pageTarget = targets.find(target => target.type === 'page')
  if (!pageTarget?.webSocketDebuggerUrl) throw new Error('Chrome page target unavailable')
  return { child, websocketUrl: pageTarget.webSocketDebuggerUrl }
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
      { name: 'forced-colors', value: 'active' },
      { name: 'prefers-reduced-motion', value: 'reduce' },
    ],
  })

  const load = cdp.waitFor('Page.loadEventFired')
  const navigationStarted = Date.now()
  await cdp.send('Page.navigate', { url: previewUrl })
  await load

  let mainVisible = false
  while (!mainVisible && Date.now() - navigationStarted <= mainVisibleBudgetMs) {
    const evaluated = await cdp.send('Runtime.evaluate', {
      expression: "Boolean(document.querySelector('main, #main-content')?.getBoundingClientRect().height)",
      returnByValue: true,
    })
    mainVisible = evaluated.result.value === true
    if (!mainVisible) await new Promise(resolveWait => setTimeout(resolveWait, 50))
  }
  const mainVisibleMs = Date.now() - navigationStarted

  const evaluated = await cdp.send('Runtime.evaluate', {
    expression: `(() => {
      const root = document.documentElement
      const controls = [...document.querySelectorAll('a[href],button,input:not([type="hidden"]),select,textarea,summary')]
        .filter(el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' })
      const forcedControlBorderVisible = controls.some(el => {
        const s = getComputedStyle(el)
        return (s.borderStyle !== 'none' && parseFloat(s.borderWidth) > 0)
          || (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0)
      })
      return {
        forcedColorsActive: matchMedia('(forced-colors: active)').matches,
        forcedColorAdjust: getComputedStyle(root).forcedColorAdjust,
        forcedControlBorderVisible,
        viewportWidth: innerWidth,
        screenWidth: screen.width,
        devicePixelRatio,
        horizontalOverflow: Math.max(0, root.scrollWidth - root.clientWidth),
        controlsBelow44: controls.filter(el => el.getBoundingClientRect().height < 44).length,
      }
    })()`,
    returnByValue: true,
  })

  return { ...evaluated.result.value, mainVisible, mainVisibleMs }
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
