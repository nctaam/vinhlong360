import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'

const BASE_URL = 'https://vinhlong360.vn'
const CDP_PORT = 9228

function sleep(ms) { return new Promise(r => setTimeout(r, ms)) }

function findChrome() {
  const candidates = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA, 'Google\\Chrome\\Application\\chrome.exe') : '',
  ].filter(Boolean)
  return candidates.find(p => existsSync(p))
}

class CdpClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl
    this.seq = 0
    this.pending = new Map()
  }
  connect() {
    this.ws = new WebSocket(this.wsUrl)
    this.ws.onmessage = event => {
      const msg = JSON.parse(event.data)
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject, timer } = this.pending.get(msg.id)
        clearTimeout(timer)
        this.pending.delete(msg.id)
        if (msg.error) reject(new Error(msg.error.message))
        else resolve(msg.result || {})
      }
    }
    return new Promise((res, rej) => {
      this.ws.onopen = res
      this.ws.onerror = rej
    })
  }
  send(method, params = {}, timeoutMs = 25000) {
    const id = ++this.seq
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id)
        reject(new Error(`Timeout: ${method}`))
      }, timeoutMs)
      this.pending.set(id, { resolve, reject, timer })
      this.ws.send(JSON.stringify({ id, method, params }))
    })
  }
  close() { try { this.ws?.close() } catch {} }
}

async function run() {
  const chromePath = findChrome()
  const userDataDir = await mkdtemp(path.join(tmpdir(), 'vl360-diag-'))
  const chromeProcess = spawn(chromePath, [
    '--headless=new',
    `--remote-debugging-port=${CDP_PORT}`,
    `--user-data-dir=${userDataDir}`,
    '--disable-gpu',
    'about:blank',
  ], { stdio: 'ignore' })

  let cdp = null
  try {
    for (let i = 0; i < 40; i++) {
      try {
        const res = await fetch(`http://127.0.0.1:${CDP_PORT}/json/version`)
        if (res.ok) break
      } catch {}
      await sleep(200)
    }
    const res = await fetch(`http://127.0.0.1:${CDP_PORT}/json/new?about:blank`, { method: 'PUT' })
    const target = await res.json()
    cdp = new CdpClient(target.webSocketDebuggerUrl)
    await cdp.connect()

    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Network.enable')

    // Inject observer
    await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
      source: `(() => {
        window.__clsEntries = [];
        window.__clsScore = 0;
        try {
          const obs = new PerformanceObserver(list => {
            for (const e of list.getEntries()) {
              if (!e.hadRecentInput) {
                window.__clsScore += e.value;
                window.__clsEntries.push({
                  value: e.value,
                  sources: (e.sources || []).map(s => ({
                    tag: s.node ? s.node.tagName : 'unknown',
                    class: s.node ? s.node.className : '',
                    id: s.node ? s.node.id : '',
                    prev: s.previousRect,
                    curr: s.currentRect
                  }))
                });
              }
            }
          });
          obs.observe({ type: 'layout-shift', buffered: true });
        } catch(e) {}
      })();`
    })

    // 1. Emulate Poor 3G on Homepage and diagnose shifts
    console.log('--- Diagnosing Poor 3G on Homepage ---')
    await cdp.send('Network.emulateNetworkConditions', {
      offline: false,
      latency: 400,
      downloadThroughput: (400 * 1024) / 8,
      uploadThroughput: (150 * 1024) / 8,
      connectionType: 'cellular3g'
    })
    await cdp.send('Page.navigate', { url: BASE_URL + '/' })
    await sleep(4000)
    const shifts = await cdp.send('Runtime.evaluate', {
      expression: `(() => {
        return {
          totalCls: window.__clsScore,
          entries: window.__clsEntries
        };
      })()`,
      returnByValue: true
    })
    console.log('Poor 3G CLS Diagnosis:', JSON.stringify(shifts.result.value, null, 2))

    // Reset network
    await cdp.send('Network.emulateNetworkConditions', {
      offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1
    })

    // 2. Diagnose Contrast in Nocturne & Parchment
    console.log('--- Diagnosing Contrast Failures ---')
    for (const theme of ['nocturne', 'parchment']) {
      await cdp.send('Runtime.evaluate', {
        expression: `(() => {
          const cs = ${JSON.stringify(theme === 'parchment' ? 'light' : 'dark')};
          document.documentElement.setAttribute('data-theme', ${JSON.stringify(theme)});
          document.documentElement.classList.remove('theme-nocturne', 'theme-parchment', 'dark', 'light');
          document.documentElement.classList.add(${JSON.stringify('theme-' + theme)}, cs);
        })()`
      })
      await sleep(400)
      const contrastData = await cdp.send('Runtime.evaluate', {
        expression: `(() => {
          function parseRgb(colorStr) {
            if (!colorStr) return [0, 0, 0, 1];
            const m = colorStr.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/);
            if (m) return [parseInt(m[1]), parseInt(m[2]), parseInt(m[3]), m[4] !== undefined ? parseFloat(m[4]) : 1];
            return [0, 0, 0, 1];
          }
          function luminance([r, g, b]) {
            const a = [r, g, b].map(v => {
              v /= 255;
              return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
            });
            return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2];
          }
          function contrastRatio(rgb1, rgb2) {
            const l1 = luminance(rgb1);
            const l2 = luminance(rgb2);
            return Math.round(((Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)) * 100) / 100;
          }

          const elements = [
            { sel: 'h1', name: 'Hero H1' },
            { sel: 'h2', name: 'Section H2' },
            { sel: 'p', name: 'Paragraph' },
            { sel: '.btn-primary, button.btn', name: 'Button' },
            { sel: '.pill, .chip', name: 'Pill/Chip' },
            { sel: 'nav a', name: 'Nav A' }
          ];

          return elements.map(item => {
            const el = document.querySelector(item.sel);
            if (!el) return { name: item.name, missing: true };
            const s = getComputedStyle(el);
            let bg = s.backgroundColor;
            let p = el.parentElement;
            while (p && (bg === 'transparent' || bg === 'rgba(0, 0, 0, 0)')) {
              bg = getComputedStyle(p).backgroundColor;
              p = p.parentElement;
            }
            if (bg === 'transparent' || bg === 'rgba(0, 0, 0, 0)') {
              bg = getComputedStyle(document.body).backgroundColor;
            }
            return {
              name: item.name,
              sel: item.sel,
              color: s.color,
              bgColor: bg,
              ratio: contrastRatio(parseRgb(s.color), parseRgb(bg))
            };
          });
        })()`,
        returnByValue: true
      })
      console.log(`Contrast under ${theme}:`, JSON.stringify(contrastData.result.value, null, 2))
    }

    // 3. Diagnose Clipped Elements
    console.log('--- Diagnosing Clipped Elements ---')
    const clippedData = await cdp.send('Runtime.evaluate', {
      expression: `(() => {
        const textElements = Array.from(document.querySelectorAll('h1, h2, h3, h4, p, a, button, span, .pill, .chip'));
        const list = [];
        for (const el of textElements) {
          if (!el.isConnected || el.offsetWidth === 0 || el.offsetHeight === 0) continue;
          const s = getComputedStyle(el);
          if (s.display === 'none' || s.visibility === 'hidden') continue;
          const hasH = el.scrollWidth > el.clientWidth + 2;
          const hasV = el.scrollHeight > el.clientHeight + 2;
          const isOverflowHidden = s.overflow === 'hidden' || s.overflowX === 'hidden' || s.overflowY === 'hidden';
          const isEllipsis = s.textOverflow === 'ellipsis';
          if ((hasH || hasV) && isOverflowHidden && !isEllipsis) {
            list.push({
              tag: el.tagName,
              class: el.className,
              text: el.textContent.trim().slice(0, 50),
              scrollWidth: el.scrollWidth,
              clientWidth: el.clientWidth,
              scrollHeight: el.scrollHeight,
              clientHeight: el.clientHeight,
              hasH, hasV
            });
          }
        }
        return list;
      })()`,
      returnByValue: true
    })
    console.log(`Clipped Elements count: ${clippedData.result.value.length}`)
    console.log('Sample clipped:', JSON.stringify(clippedData.result.value.slice(0, 10), null, 2))

  } finally {
    if (cdp) cdp.close()
    chromeProcess.kill()
    try { await rm(userDataDir, { recursive: true, force: true }) } catch {}
  }
}

run()
