#!/usr/bin/env node
/**
 * Quét axe-core 14 trang công khai → sinh `axe-report.json` cho cổng R30.6.
 *
 * R30.6 đã có checker từ 2026-07-10 nhưng KHÔNG nơi nào trong repo sinh ra
 * report, nên cổng hạng hard-ratchet đó vĩnh viễn graceful-skip về 0 (rà soát
 * 2026-08-05, docs/standards/95-ra-soat-cong.md). Script này là nguồn sinh còn
 * thiếu.
 *
 * Lái Chrome bằng CDP thuần như `scripts/smoke_e2e_chrome.mjs` — không thêm
 * puppeteer/playwright, không tải browser riêng (§B8 ngân sách). Runner CI của
 * GitHub và máy dev đều đã có sẵn Chrome/Chromium.
 *
 * Dùng:
 *   node scripts/axe_scan.mjs                    # cần server đang chạy ở :3000
 *   AXE_BASE_URL=http://localhost:3000 node scripts/axe_scan.mjs
 */
import { spawn } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(HERE, '..')
const AXE_SOURCE = path.join(REPO_ROOT, 'web-nuxt', 'node_modules', 'axe-core', 'axe.min.js')
const OUT_FILE = path.join(REPO_ROOT, 'axe-report.json')

const baseUrl = process.env.AXE_BASE_URL || 'http://localhost:3000'
const port = Number(process.env.AXE_CDP_PORT || 9224)
const settleMs = Number(process.env.AXE_SETTLE_MS || 900)

// 14 trang sweep — chỉ trang CÔNG KHAI, không cần đăng nhập, để scan chạy được
// trên CI mà không cần seed tài khoản.
const ROUTES = (process.env.AXE_ROUTES || [
  '/',
  '/du-lich',
  '/san-pham',
  '/ocop',
  '/luu-tru',
  '/le-hoi',
  '/su-kien',
  '/theo-mua',
  '/ban-do',
  '/lich-trinh',
  '/tim-kiem',
  '/cong-dong',
  '/bang-xep-hang',
  '/huong-dan',
].join(',')).split(',').map(s => s.trim()).filter(Boolean)

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

function findChrome() {
  return [
    process.env.CHROME_PATH,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    process.env.LOCALAPPDATA
      ? path.join(process.env.LOCALAPPDATA, 'Google\\Chrome\\Application\\chrome.exe')
      : '',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium',
  ].filter(Boolean).find(p => existsSync(p))
}

class Cdp {
  constructor(wsUrl) {
    this.wsUrl = wsUrl
    this.seq = 0
    this.pending = new Map()
  }

  connect() {
    if (typeof WebSocket === 'undefined') {
      throw new Error('Cần Node.js có WebSocket toàn cục (Node 22+)')
    }
    this.ws = new WebSocket(this.wsUrl)
    this.ws.onmessage = event => {
      const msg = JSON.parse(event.data)
      if (!msg.id || !this.pending.has(msg.id)) return
      const { resolve, reject, timer } = this.pending.get(msg.id)
      clearTimeout(timer)
      this.pending.delete(msg.id)
      if (msg.error) reject(new Error(msg.error.message || 'CDP error'))
      else resolve(msg.result || {})
    }
    return new Promise((resolve, reject) => {
      this.ws.onopen = resolve
      this.ws.onerror = () => reject(new Error(`Không nối được CDP tại ${this.wsUrl}`))
    })
  }

  send(method, params = {}, timeoutMs = 60000) {
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

  close() {
    this.ws?.close()
  }
}

async function waitForChrome() {
  for (let i = 0; i < 80; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`)
      if (res.ok && (await res.json()).webSocketDebuggerUrl) return
    } catch { /* chưa lên */ }
    await sleep(250)
  }
  throw new Error('Chrome không mở được cổng CDP')
}

async function waitForServer() {
  for (let i = 0; i < 120; i++) {
    try {
      const res = await fetch(baseUrl, { redirect: 'manual' })
      if (res.status < 500) return
    } catch { /* chưa lên */ }
    await sleep(500)
  }
  throw new Error(`Server không phản hồi tại ${baseUrl}`)
}

async function newTarget() {
  const endpoint = `http://127.0.0.1:${port}/json/new?about:blank`
  let res = await fetch(endpoint, { method: 'PUT' })
  if (!res.ok) res = await fetch(endpoint)
  if (!res.ok) throw new Error(`Không tạo được tab: ${res.status}`)
  return (await res.json()).webSocketDebuggerUrl
}

async function scanRoute(cdp, axeSource, route) {
  const url = new URL(route, baseUrl).toString()
  await cdp.send('Page.navigate', { url })
  await sleep(settleMs)
  await cdp.send('Runtime.evaluate', { expression: axeSource, returnByValue: false })
  const result = await cdp.send('Runtime.evaluate', {
    // Chỉ lấy trường cần cho cổng; nguyên bản axe kèm cả DOM snapshot rất nặng.
    expression: `axe.run(document, { resultTypes: ['violations'] }).then(r => JSON.stringify({
      violations: r.violations.map(v => ({
        id: v.id, impact: v.impact, help: v.help,
        nodes: v.nodes.map(n => ({ target: n.target })),
      })),
    }))`,
    awaitPromise: true,
    returnByValue: true,
    timeout: 60000,
  })
  const payload = JSON.parse(result.result?.value || '{"violations":[]}')
  return { url: route, violations: payload.violations || [] }
}

async function main() {
  if (!existsSync(AXE_SOURCE)) {
    console.error(`✖ Không thấy ${AXE_SOURCE} — chạy \`npm ci\` trong web-nuxt trước.`)
    return 2
  }
  const chrome = findChrome()
  if (!chrome) {
    console.error('✖ Không tìm thấy Chrome/Chromium. Đặt CHROME_PATH nếu cài ở chỗ khác.')
    return 2
  }

  await waitForServer()
  const axeSource = readFileSync(AXE_SOURCE, 'utf8')
  const profile = await mkdtemp(path.join(tmpdir(), 'axe-scan-'))
  const proc = spawn(chrome, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--no-sandbox',
  ], { stdio: 'ignore' })

  const report = []
  let cdp
  try {
    await waitForChrome()
    cdp = new Cdp(await newTarget())
    await cdp.connect()
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    for (const route of ROUTES) {
      const entry = await scanRoute(cdp, axeSource, route)
      report.push(entry)
      const severe = entry.violations.filter(v => ['serious', 'critical'].includes(v.impact))
      const mark = severe.length ? '✖' : '·'
      console.log(`  ${mark} ${route} — ${entry.violations.length} violation, ${severe.length} serious+`)
    }
  } finally {
    cdp?.close()
    proc.kill()
    await rm(profile, { recursive: true, force: true }).catch(() => {})
  }

  await writeFile(OUT_FILE, JSON.stringify(report, null, 2), 'utf8')
  const severe = report.flatMap(r => r.violations).filter(v => ['serious', 'critical'].includes(v.impact))
  console.log(`\n→ ${OUT_FILE} (${ROUTES.length} trang, ${severe.length} violation serious+)`)
  return 0
}

main().then(code => process.exit(code)).catch(error => {
  console.error(`✖ axe scan lỗi: ${error.message}`)
  process.exit(2)
})
