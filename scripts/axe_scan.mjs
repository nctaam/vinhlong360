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

import { SCRIM_SELECTORS, scrimShieldsText } from './axe_scrim_filter.mjs'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(HERE, '..')
const AXE_SOURCE = path.join(REPO_ROOT, 'web-nuxt', 'node_modules', 'axe-core', 'axe.min.js')
const OUT_FILE = path.join(REPO_ROOT, 'axe-report.json')

const baseUrl = process.env.AXE_BASE_URL || 'http://localhost:3000'
const port = Number(process.env.AXE_CDP_PORT || 9224)
const settleMs = Number(process.env.AXE_SETTLE_MS || 900)
// Site mặc định Nocturne (nuxt.config.ts: preference 'dark'), nên sweep trước
// 2026-08-06 CHỈ kiểm chế độ tối — Parchment chưa từng được axe chạm tới. Quét cả
// hai nhân đôi phạm vi cổng R30.6 mà gần như không tốn thêm hạ tầng.
const COLOR_MODES = (process.env.AXE_COLOR_MODES || 'dark,light')
  .split(',').map(s => s.trim()).filter(Boolean)

// Sweep chỉ gồm trang CÔNG KHAI, không cần đăng nhập, để chạy được trên CI mà
// không phải seed tài khoản.
//
// Mở rộng 2026-08-06: 14 trang danh sách ban đầu bỏ sót toàn bộ trang CHI TIẾT —
// loại trang người dùng xem nhiều nhất và cũng là nơi lỗi a11y hay nấp (ảnh,
// bảng thuộc tính, breadcrumb, tab). Thêm 6 trang chi tiết với id THẬT lấy từ DB,
// cố ý chọn cả entity CÓ ảnh lẫn entity KHÔNG ảnh (đường nhãn "Minh họa AI" là
// nhánh render khác hẳn), cộng 5 trang tĩnh còn thiếu.
const ROUTES = (process.env.AXE_ROUTES || [
  // trang danh sách
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
  // trang tĩnh còn thiếu
  '/danh-ba',
  '/gioi-thieu',
  '/lien-he',
  '/chinh-sach-bao-mat',
  '/dieu-khoan-su-dung',
  // trang chi tiết — id thật, có/không ảnh
  '/dia-diem/lang-nghe-san-xuat-chi-xo-dua-an-thanh',
  '/dia-diem/cu-lao-my-hoa',
  '/dia-diem/nha-tho-cai-mon-cho-lach',
  '/khu-vuc/vinh-long',
  '/kham-pha/thien-nhien',
  '/lich-trinh/mot-ngay-cu-lao-an-binh',
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

async function applyColorMode(cdp, mode) {
  // @nuxtjs/color-mode đọc localStorage['vl360-color-mode'] (nuxt.config.ts:25).
  // Phải đứng trên trang CÙNG ORIGIN mới ghi được, nên navigate về base trước.
  await cdp.send('Page.navigate', { url: baseUrl })
  await sleep(settleMs)
  await cdp.send('Runtime.evaluate', {
    expression: `localStorage.setItem('vl360-color-mode', ${JSON.stringify(mode)})`,
  })
  await cdp.send('Emulation.setEmulatedMedia', {
    features: [{ name: 'prefers-color-scheme', value: mode }],
  }).catch(() => {})
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
        // Giữ cả \`data\` của từng check: với color-contrast nó chứa fgColor/
        // bgColor/contrastRatio — số liệu DUY NHẤT cho phép phân biệt vi phạm
        // thật với false positive (axe không thấy được nền nằm dưới z-index âm
        // nên hay quy về nền tổ tiên). Không có nó thì artifact CI vô dụng lúc
        // chẩn đoán, đúng như lần chạy 31076418020.
        nodes: v.nodes.map(n => ({
          target: n.target,
          data: (n.any || []).map(c => c.data).filter(Boolean),
        })),
      })),
    }))`,
    awaitPromise: true,
    returnByValue: true,
    timeout: 120000,
  }, 150000)
  const payload = JSON.parse(result.result?.value || '{"violations":[]}')
  const violations = await dropScrimFalsePositives(cdp, payload.violations || [])
  return { url: route, violations }
}

/* Text nằm trên `.spread-scrim` bị axe chấm sai. Scrim ở `z-index:-1`, ngoài
 * stacking context của chữ, nên axe bỏ qua nó và quy nền về nền TRANG: ở chế độ
 * sáng nó đọc bgColor `#fdfcf9` rồi báo tỉ lệ 1.02 cho chữ trắng, trong khi nền
 * thật dưới chữ là `rgba(8,9,12,.84)` — trắng-trên-gần-đen, thừa AA.
 * Đo được bằng getComputedStyle nhưng axe không có đường nào thấy.
 *
 * Nên bỏ qua, NHƯNG chỉ khi scrim còn thật sự tối — nếu ai gỡ scrim hoặc làm nó
 * nhạt đi thì đó là vi phạm THẬT và phải nổi lên. Đó là điểm khác giữa hàm này
 * và một allowlist chết: nó tự kiểm điều kiện đã khiến nó hợp lệ.
 *
 * Chỉ áp cho color-contrast; mọi rule khác trên cùng phần tử vẫn được chấm.
 */
async function dropScrimFalsePositives(cdp, violations) {
  if (!violations.some(v => v.id === 'color-contrast')) return violations
  const probe = await cdp.send('Runtime.evaluate', {
    expression: `(() => {
      const scrim = document.querySelector('.spread-scrim')
      if (!scrim) return '[]'
      const shields = ${scrimShieldsText.toString()}
      return shields(getComputedStyle(scrim)) ? ${JSON.stringify(JSON.stringify(SCRIM_SELECTORS))} : '[]'
    })()`,
    returnByValue: true,
  })
  const covered = JSON.parse(probe.result?.value || '[]')
  if (!covered.length) return violations
  const onScrim = t => covered.some(sel => String(t).includes(sel))
  return violations
    .map(v => {
      if (v.id !== 'color-contrast') return v
      const kept = v.nodes.filter(n => ![].concat(n.target).some(onScrim))
      if (kept.length === v.nodes.length) return v
      const dropped = v.nodes.length - kept.length
      console.log(`    (bỏ ${dropped} node color-contrast trên .spread-scrim — nền thật rgba(8,9,12,.84), axe không thấy qua z-index âm)`)
      return kept.length ? { ...v, nodes: kept } : null
    })
    .filter(Boolean)
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
  const skipped = []
  let cdp
  try {
    await waitForChrome()
    cdp = new Cdp(await newTarget())
    await cdp.connect()
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    for (const mode of COLOR_MODES) {
      console.log(`\n— chế độ ${mode} —`)
      await applyColorMode(cdp, mode)
      for (const route of ROUTES) {
        // Một trang nặng làm axe.run vượt timeout KHÔNG được kéo sập cả lượt —
        // trước đây mất trắng 24 trang đã quét xong chỉ vì trang thứ 25.
        let entry
        try {
          entry = await scanRoute(cdp, axeSource, route)
        } catch (error) {
          console.log(`  ! ${route} — bỏ qua: ${error.message}`)
          skipped.push(`${route} [${mode}]: ${error.message}`)
          continue
        }
        // Gắn chế độ vào url để báo cáo phân biệt hai lượt của cùng một trang.
        entry.url = `${route} [${mode}]`
        report.push(entry)
        const severe = entry.violations.filter(v => ['serious', 'critical'].includes(v.impact))
        const mark = severe.length ? '✖' : '·'
        console.log(`  ${mark} ${route} — ${entry.violations.length} violation, ${severe.length} serious+`)
      }
    }
  } finally {
    cdp?.close()
    proc.kill()
    await rm(profile, { recursive: true, force: true }).catch(() => {})
  }

  await writeFile(OUT_FILE, JSON.stringify(report, null, 2), 'utf8')
  if (skipped.length) {
    // In ra chứ không nuốt: quét thiếu trang mà báo 'sạch' là thông tin sai.
    console.log(`
! ${skipped.length} trang KHÔNG quét được:`)
    for (const line of skipped) console.log(`    ${line}`)
  }
  const severe = report.flatMap(r => r.violations).filter(v => ['serious', 'critical'].includes(v.impact))
  console.log(`\n→ ${OUT_FILE} (${ROUTES.length} trang × ${COLOR_MODES.length} chế độ, ${severe.length} violation serious+)`)
  return 0
}

// Chỉ tự chạy khi được gọi trực tiếp — để test import được `scrimShieldsText`
// mà không kéo theo cả lượt quét (dựng Chrome, mở CDP, ghi axe-report.json).
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().then(code => process.exit(code)).catch(error => {
    console.error(`✖ axe scan lỗi: ${error.message}`)
    process.exit(2)
  })
}
