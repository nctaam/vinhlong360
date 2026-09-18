import { spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(__dirname, '..')

const BASE_URL = process.env.AUDIT_BASE_URL || 'https://vinhlong360.vn'
const CDP_PORT = parseInt(process.env.AUDIT_CDP_PORT || '9231', 10)
const OUTPUT_DIR = path.resolve(REPO_ROOT, 'outputs', 'm4_challenger_1')
const SCREENSHOT_DIR = path.resolve(OUTPUT_DIR, 'screenshots')

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function sha256(buffer) {
  return createHash('sha256').update(buffer).digest('hex')
}

function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA, 'Google\\Chrome\\Application\\chrome.exe') : '',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  ].filter(Boolean)
  return candidates.find(p => existsSync(p))
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
      throw new Error('Node.js with global WebSocket support is required')
    }
    this.ws = new WebSocket(this.wsUrl)
    this.ws.onmessage = event => {
      const msg = JSON.parse(event.data)
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject, timer } = this.pending.get(msg.id)
        clearTimeout(timer)
        this.pending.delete(msg.id)
        if (msg.error) reject(new Error(`${msg.error.message || 'CDP error'}: ${JSON.stringify(msg.error.data || '')}`))
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

  send(method, params = {}, timeoutMs = 35000) {
    const id = ++this.seq
    const payload = JSON.stringify({ id, method, params })
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id)
        reject(new Error(`CDP timeout: ${method} (${timeoutMs}ms)`))
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

  waitFor(method, timeoutMs = 35000) {
    return new Promise((resolve, reject) => {
      let timer = null
      const off = this.on(method, params => {
        if (timer) clearTimeout(timer)
        off()
        resolve(params)
      })
      timer = setTimeout(() => {
        off()
        reject(new Error(`Timed out waiting for ${method}`))
      }, timeoutMs)
    })
  }

  close() {
    try { this.ws?.close() } catch {}
  }
}

async function waitForChrome(port) {
  const versionUrl = `http://127.0.0.1:${port}/json/version`
  for (let i = 0; i < 80; i++) {
    try {
      const res = await fetch(versionUrl)
      if (res.ok) {
        const data = await res.json()
        if (data.webSocketDebuggerUrl) return data
      }
    } catch {}
    await sleep(250)
  }
  throw new Error(`Chrome did not open CDP endpoint on port ${port} in time`)
}

async function createPageTarget(port) {
  const endpoint = `http://127.0.0.1:${port}/json/new?about:blank`
  let res = await fetch(endpoint, { method: 'PUT' })
  if (!res.ok) res = await fetch(endpoint)
  if (!res.ok) throw new Error(`Cannot create Chrome target: ${res.status}`)
  const data = await res.json()
  return data.webSocketDebuggerUrl
}

async function evaluateValue(cdp, expression) {
  const result = await cdp.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  return result.result?.value
}

async function setViewport(cdp, width, height, mobile = false) {
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile,
    screenOrientation: mobile ? { type: 'portraitPrimary', angle: 0 } : { type: 'landscapePrimary', angle: 0 },
  })
  await sleep(150)
}

async function navigate(cdp, route, settleMs = 1200) {
  const fullUrl = new URL(route, BASE_URL).toString()
  const load = cdp.waitFor('Page.loadEventFired', 35000)
  await cdp.send('Page.navigate', { url: fullUrl })
  await load
  await sleep(settleMs)
}

async function takeScreenshot(cdp, filePath) {
  const result = await cdp.send('Page.captureScreenshot', { format: 'png', fromSurface: true })
  const buffer = Buffer.from(result.data, 'base64')
  writeFileSync(filePath, buffer)
  return {
    bytes: buffer.length,
    sha256: sha256(buffer),
  }
}

// -------------------------------------------------------------
// ADVERSARIAL STRESS SUITES
// -------------------------------------------------------------

async function probeHitboxOcclusion(cdp) {
  return evaluateValue(cdp, `(() => {
    function getDesc(el) {
      if (!el) return 'null';
      const tag = el.tagName.toLowerCase();
      const id = el.id ? '#' + el.id : '';
      const cls = el.className && typeof el.className === 'string'
        ? '.' + el.className.trim().replace(/\\s+/g, '.')
        : '';
      const text = (el.textContent || '').trim().slice(0, 24);
      return \`<\${tag}\${id}\${cls}>[\${text}]\`;
    }

    const interactiveSelectors = [
      'a[href]', 'button', 'input:not([type="hidden"])', 'select', 'summary',
      '[role="button"]', '[role="tab"]', '.public-bottom-nav-item',
      '.detail-primary-action', '[data-action-dock] button', '[data-action-dock] a',
      '.sticky-cta-bar a', '.cw-btn'
    ].join(',');

    const candidates = Array.from(document.querySelectorAll(interactiveSelectors));
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    const visibleElements = candidates.filter(el => {
      if (!el.isConnected) return false;
      if (el.closest('[aria-hidden="true"], [inert]')) return false;
      const s = getComputedStyle(el);
      if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0) return false;
      if (s.pointerEvents === 'none') return false;
      const rect = el.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return false;
      return rect.bottom > 0 && rect.top < vh && rect.right > 0 && rect.left < vw;
    });

    const results = [];
    let severeOcclusions = 0;
    let partialOcclusions = 0;

    for (const el of visibleElements) {
      const rect = el.getBoundingClientRect();
      const probePoints = [
        { name: 'center', x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 },
        { name: 'top-left', x: Math.min(rect.right - 2, Math.max(rect.left + 2, rect.left + 4)), y: Math.min(rect.bottom - 2, Math.max(rect.top + 2, rect.top + 4)) },
        { name: 'top-right', x: Math.max(rect.left + 2, Math.min(rect.right - 2, rect.right - 4)), y: Math.min(rect.bottom - 2, Math.max(rect.top + 2, rect.top + 4)) },
        { name: 'bottom-left', x: Math.min(rect.right - 2, Math.max(rect.left + 2, rect.left + 4)), y: Math.max(rect.top + 2, Math.min(rect.bottom - 2, rect.bottom - 4)) },
        { name: 'bottom-right', x: Math.max(rect.left + 2, Math.min(rect.right - 2, rect.right - 4)), y: Math.max(rect.top + 2, Math.min(rect.bottom - 2, rect.bottom - 4)) }
      ];

      const probeHits = [];
      let pointsOccluded = 0;

      for (const pt of probePoints) {
        const px = Math.max(0, Math.min(vw - 1, pt.x));
        const py = Math.max(0, Math.min(vh - 1, pt.y));
        const hitEl = document.elementFromPoint(px, py);

        const ownsHit = Boolean(hitEl && (hitEl === el || el.contains(hitEl) || hitEl.contains(el)));
        if (!ownsHit) pointsOccluded++;

        probeHits.push({
          point: pt.name,
          x: Math.round(px),
          y: Math.round(py),
          ownsHit,
          hitElement: getDesc(hitEl)
        });
      }

      const isCenterOccluded = !probeHits[0].ownsHit;
      const isCompletelyOccluded = pointsOccluded === probePoints.length;
      const isPartiallyOccluded = pointsOccluded > 0 && !isCompletelyOccluded;

      if (isCenterOccluded) severeOcclusions++;
      else if (isPartiallyOccluded) partialOcclusions++;

      results.push({
        descriptor: getDesc(el),
        rect: {
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          width: Math.round(rect.width * 10) / 10,
          height: Math.round(rect.height * 10) / 10
        },
        meetsMinTarget: rect.width >= 43.5 && rect.height >= 43.5,
        isCenterOccluded,
        isCompletelyOccluded,
        isPartiallyOccluded,
        pointsOccluded,
        probeHits
      });
    }

    return {
      totalAudited: visibleElements.length,
      severeOcclusions,
      partialOcclusions,
      fullyClearCount: visibleElements.length - severeOcclusions - partialOcclusions,
      clearRate: visibleElements.length ? Math.round(((visibleElements.length - severeOcclusions) / visibleElements.length) * 10000) / 100 : 100,
      occlusions: results.filter(r => r.pointsOccluded > 0)
    };
  })()`)
}

async function stressDynamicScrollingCollision(cdp) {
  return evaluateValue(cdp, `(async () => {
    function sleep(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    }

    const root = document.documentElement;
    const maxScroll = Math.max(0, root.scrollHeight - window.innerHeight);

    const fixedSelectors = [
      '.public-bottom-nav',
      '.sticky-cta-bar',
      '.detail-contact-widget',
      '.cw',
      '.journey-bar',
      '[data-fixed-action-rail]'
    ];

    const safeAreaSelectors = [
      '[data-detail-action-safe-area]',
      '.detail-action-dock',
      '[data-action-dock]',
      '[data-planner-action-safe-area]',
      '.ward-action-dock'
    ];

    const sampleFrames = [];
    let maxCollisionPx = 0;
    let collisionFramesCount = 0;

    const scrollSteps = [
      0, 40, 80, 140, 220, 320, 450, 600, 800, 1100, 1500, 2000, 2600, 3300, 4100, 5000,
      maxScroll * 0.5, maxScroll * 0.75, maxScroll * 0.9, maxScroll,
      maxScroll - 50, maxScroll, maxScroll - 100, maxScroll,
      maxScroll * 0.7, maxScroll * 0.4, 200, 0,
      maxScroll
    ];

    for (let i = 0; i < scrollSteps.length; i++) {
      const targetScroll = Math.max(0, Math.min(maxScroll, scrollSteps[i]));
      window.scrollTo({ top: targetScroll, behavior: 'instant' });
      await sleep(15);

      const currentY = window.scrollY;
      const fixedElements = fixedSelectors
        .flatMap(sel => Array.from(document.querySelectorAll(sel)))
        .filter(el => {
          const s = getComputedStyle(el);
          return s.position === 'fixed' && s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity) > 0;
        });

      const safeAreas = safeAreaSelectors
        .flatMap(sel => Array.from(document.querySelectorAll(sel)))
        .filter(el => {
          const s = getComputedStyle(el);
          return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity) > 0;
        });

      let frameMaxOverlap = 0;
      const frameCollisions = [];

      for (const safe of safeAreas) {
        const a = safe.getBoundingClientRect();
        if (a.bottom < 0 || a.top > window.innerHeight) continue;

        for (const fixed of fixedElements) {
          const b = fixed.getBoundingClientRect();
          const overlapX = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
          const overlapY = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));

          if (overlapX > 0 && overlapY > 0) {
            frameMaxOverlap = Math.max(frameMaxOverlap, overlapY);
            frameCollisions.push({
              safeAreaClass: safe.className,
              fixedClass: fixed.className,
              overlapX: Math.round(overlapX * 10) / 10,
              overlapY: Math.round(overlapY * 10) / 10,
              safeRect: { top: Math.round(a.top), bottom: Math.round(a.bottom), left: Math.round(a.left), right: Math.round(a.right) },
              fixedRect: { top: Math.round(b.top), bottom: Math.round(b.bottom), left: Math.round(b.left), right: Math.round(b.right) }
            });
          }
        }
      }

      if (frameMaxOverlap > 0) {
        collisionFramesCount++;
        maxCollisionPx = Math.max(maxCollisionPx, frameMaxOverlap);
      }

      sampleFrames.push({
        stepIndex: i,
        scrollY: Math.round(currentY),
        frameMaxOverlap: Math.round(frameMaxOverlap * 10) / 10,
        collisionCount: frameCollisions.length,
        collisions: frameCollisions
      });
    }

    window.scrollTo(0, maxScroll);
    await sleep(50);
    const finalDock = document.querySelector('[data-detail-action-safe-area], .detail-action-dock');
    const finalBottomNav = document.querySelector('.public-bottom-nav');
    let bottomGapPx = null;
    let safeAreaPaddingBottom = '';
    if (finalDock && finalBottomNav) {
      const dockRect = finalDock.getBoundingClientRect();
      const navRect = finalBottomNav.getBoundingClientRect();
      bottomGapPx = Math.round((navRect.top - dockRect.bottom) * 10) / 10;
      safeAreaPaddingBottom = getComputedStyle(finalDock).paddingBottom;
    }

    return {
      totalFramesAudited: scrollSteps.length,
      collisionFramesCount,
      maxCollisionPx: Math.round(maxCollisionPx * 10) / 10,
      holdsZeroPixelCollision: maxCollisionPx === 0,
      bottomGapPx,
      safeAreaPaddingBottom,
      maxScrollHeight: Math.round(root.scrollHeight),
      sampleFrames: sampleFrames.filter(f => f.collisionCount > 0).slice(0, 10)
    };
  })()`)
}

async function testBottomThumbZoneClickability(cdp) {
  return evaluateValue(cdp, `(() => {
    function getDesc(el) {
      if (!el) return 'null';
      const tag = el.tagName.toLowerCase();
      const id = el.id ? '#' + el.id : '';
      const cls = el.className && typeof el.className === 'string'
        ? '.' + el.className.trim().replace(/\\s+/g, '.')
        : '';
      const text = (el.textContent || '').trim().slice(0, 24);
      return \`<\${tag}\${id}\${cls}>[\${text}]\`;
    }

    const vh = window.innerHeight;
    const vw = window.innerWidth;
    const thumbZoneTop = Math.max(0, vh - 130);

    const selectors = [
      '.public-bottom-nav .public-bottom-nav-item',
      '.sticky-cta-bar a',
      '.cw-btn',
      '.detail-primary-action'
    ].join(',');

    const candidates = Array.from(document.querySelectorAll(selectors));
    const thumbZoneElements = candidates.filter(el => {
      if (!el.isConnected) return false;
      const s = getComputedStyle(el);
      if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0) return false;
      const rect = el.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return false;
      return rect.bottom > thumbZoneTop && rect.top < vh && rect.right > 0 && rect.left < vw;
    });

    const results = [];
    let fullyClickableCount = 0;

    for (const el of thumbZoneElements) {
      const rect = el.getBoundingClientRect();
      const cx = Math.round(rect.left + rect.width / 2);
      const cy = Math.round(rect.top + rect.height / 2);

      const hitEl = document.elementFromPoint(cx, cy);
      const ownsCenterHit = Boolean(hitEl && (hitEl === el || el.contains(hitEl) || hitEl.contains(el)));
      const s = getComputedStyle(el);

      if (ownsCenterHit && s.pointerEvents !== 'none') {
        fullyClickableCount++;
      }

      results.push({
        descriptor: getDesc(el),
        centerPoint: { x: cx, y: cy },
        rect: {
          width: Math.round(rect.width * 10) / 10,
          height: Math.round(rect.height * 10) / 10,
          top: Math.round(rect.top),
          bottom: Math.round(rect.bottom),
          left: Math.round(rect.left),
          right: Math.round(rect.right)
        },
        pointerEvents: s.pointerEvents,
        zIndex: s.zIndex,
        ownsCenterHit,
        hitElement: getDesc(hitEl),
        isClickable: ownsCenterHit && s.pointerEvents !== 'none',
        meetsMinTarget: rect.width >= 43.5 && rect.height >= 43.5
      });
    }

    return {
      totalThumbZoneControls: thumbZoneElements.length,
      fullyClickableCount,
      allUnobstructed: fullyClickableCount === thumbZoneElements.length,
      clickabilityRate: thumbZoneElements.length ? Math.round((fullyClickableCount / thumbZoneElements.length) * 10000) / 100 : 100,
      controls: results
    };
  })()`)
}

async function auditExtremeBoundary320px(cdp) {
  return evaluateValue(cdp, `(() => {
    const root = document.documentElement;
    const body = document.body;
    const scrollWidth = Math.max(root.scrollWidth, body?.scrollWidth || 0);
    const clientWidth = root.clientWidth;
    const horizontalOverflow = Math.max(0, scrollWidth - clientWidth);

    const bottomNav = document.querySelector('.public-bottom-nav');
    const bottomNavItems = Array.from(document.querySelectorAll('.public-bottom-nav-item'));

    const navMetrics = bottomNav ? (() => {
      const rect = bottomNav.getBoundingClientRect();
      const s = getComputedStyle(bottomNav);
      return {
        height: Math.round(rect.height * 10) / 10,
        heightPercentageOfViewport: Math.round((rect.height / window.innerHeight) * 1000) / 10,
        display: s.display,
        position: s.position,
        gridTemplateColumns: s.gridTemplateColumns,
        itemCount: bottomNavItems.length,
        items: bottomNavItems.map(item => {
          const r = item.getBoundingClientRect();
          return {
            text: (item.textContent || '').trim(),
            width: Math.round(r.width * 10) / 10,
            height: Math.round(r.height * 10) / 10,
            meets44px: r.width >= 43.5 && r.height >= 43.5
          };
        })
      };
    })() : null;

    const stickyCta = document.querySelector('.sticky-cta-bar');
    const stickyMetrics = stickyCta ? (() => {
      const rect = stickyCta.getBoundingClientRect();
      const s = getComputedStyle(stickyCta);
      return {
        height: Math.round(rect.height * 10) / 10,
        display: s.display,
        position: s.position,
        bottom: s.bottom
      };
    })() : null;

    return {
      viewport: { width: window.innerWidth, height: window.innerHeight },
      horizontalOverflow,
      hasHorizontalOverflow: horizontalOverflow > 0,
      navMetrics,
      stickyMetrics
    };
  })()`)
}

// -------------------------------------------------------------
// MAIN ENTRY
// -------------------------------------------------------------
async function run() {
  console.log(`[Challenger 1] Adversarial Ergonomics & Dock Safety Harness Starting...`)
  console.log(`Target: ${BASE_URL}`)
  console.log(`CDP Port: ${CDP_PORT}`)

  mkdirSync(OUTPUT_DIR, { recursive: true })
  mkdirSync(SCREENSHOT_DIR, { recursive: true })

  const chromePath = findChrome()
  if (!chromePath) throw new Error('Chrome binary not found')
  console.log(`Using Chrome binary: ${chromePath}`)

  const userDataDir = await mkdtemp(path.join(tmpdir(), 'vl360-c1-'))
  const chromeProcess = spawn(chromePath, [
    '--headless=new',
    `--remote-debugging-port=${CDP_PORT}`,
    `--user-data-dir=${userDataDir}`,
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    'about:blank',
  ], { stdio: 'ignore' })

  let cdp = null
  const auditReport = {
    testSession: 'CHALLENGER-1-M4-ERGONOMICS-DOCK-STRESS',
    startedAt: new Date().toISOString(),
    baseUrl: BASE_URL,
    viewportsAudited: ['390x844', '375x812', '320x568'],
    evidence: {
      dynamicScrollCollision: {},
      hitboxOcclusion: {},
      thumbZoneClickability: {},
      boundary320pxStress: {},
    },
    screenshots: [],
    findings: [],
    verdict: 'PENDING'
  }

  try {
    await waitForChrome(CDP_PORT)
    const wsUrl = await createPageTarget(CDP_PORT)
    cdp = new CdpClient(wsUrl)
    await cdp.connect()
    console.log(`Connected to Chrome CDP WebSocket`)

    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')

    const viewports = [
      { name: 'iPhone12_390x844', width: 390, height: 844, mobile: true },
      { name: 'iPhoneX_375x812', width: 375, height: 812, mobile: true },
      { name: 'iPhoneSE_320x568', width: 320, height: 568, mobile: true }
    ]

    for (const vp of viewports) {
      console.log(`\n=== Testing Viewport: ${vp.name} (${vp.width}x${vp.height}) on /dia-diem/gom-do-mang-thit ===`)
      await setViewport(cdp, vp.width, vp.height, vp.mobile)
      await navigate(cdp, '/dia-diem/gom-do-mang-thit', 1500)

      // Dynamic scroll collision
      const scrollResult = await stressDynamicScrollingCollision(cdp)
      auditReport.evidence.dynamicScrollCollision[vp.name] = scrollResult
      console.log(`Dynamic Scroll Overlap: ${scrollResult.maxCollisionPx}px (Holds 0px: ${scrollResult.holdsZeroPixelCollision})`)
      console.log(`Collision frames: ${scrollResult.collisionFramesCount} / ${scrollResult.totalFramesAudited}`)

      // Hitbox Top
      await evaluateValue(cdp, `window.scrollTo(0, 0)`)
      await sleep(150)
      const hitTop = await probeHitboxOcclusion(cdp)
      auditReport.evidence.hitboxOcclusion[`${vp.name}__top`] = hitTop
      console.log(`Top Hitbox Clear Rate: ${hitTop.clearRate}% (Severe: ${hitTop.severeOcclusions})`)

      // Hitbox Bottom
      await evaluateValue(cdp, `window.scrollTo(0, document.documentElement.scrollHeight)`)
      await sleep(150)
      const hitBottom = await probeHitboxOcclusion(cdp)
      auditReport.evidence.hitboxOcclusion[`${vp.name}__bottom`] = hitBottom
      console.log(`Bottom Hitbox Clear Rate: ${hitBottom.clearRate}% (Severe: ${hitBottom.severeOcclusions})`)

      // Thumb zone
      const thumbZone = await testBottomThumbZoneClickability(cdp)
      auditReport.evidence.thumbZoneClickability[vp.name] = thumbZone
      console.log(`Thumb Zone Controls: ${thumbZone.totalThumbZoneControls}, Clickable: ${thumbZone.fullyClickableCount} (Rate: ${thumbZone.clickabilityRate}%)`)

      // Screenshot at bottom state
      const shotName = `dock_bottom_stress_${vp.width}x${vp.height}.png`
      const shotPath = path.join(SCREENSHOT_DIR, shotName)
      const shotInfo = await takeScreenshot(cdp, shotPath)
      auditReport.screenshots.push({
        name: shotName,
        path: shotPath,
        width: vp.width,
        height: vp.height,
        bytes: shotInfo.bytes,
        sha256: shotInfo.sha256
      })
      console.log(`Saved screenshot: ${shotName} (${shotInfo.bytes} bytes)`)

      if (!scrollResult.holdsZeroPixelCollision) {
        auditReport.findings.push({
          severity: 'HIGH',
          viewport: vp.name,
          issue: 'DYNAMIC_SCROLL_COLLISION',
          message: `Dynamic scrolling causes up to ${scrollResult.maxCollisionPx}px collision overlap with fixed bottom bars (.public-bottom-nav & .sticky-cta-bar).`
        })
      }
    }

    // 320px boundary stress
    console.log(`\n=== 320x568 Extreme Boundary Density Stress ===`)
    await setViewport(cdp, 320, 568, true)
    await navigate(cdp, '/dia-diem/gom-do-mang-thit', 1200)
    const boundaryDetail = await auditExtremeBoundary320px(cdp)
    auditReport.evidence.boundary320pxStress['detail'] = boundaryDetail
    console.log(`Detail 320px Horizontal Overflow: ${boundaryDetail.horizontalOverflow}px`)

    await navigate(cdp, '/', 1500)
    const boundaryHome = await auditExtremeBoundary320px(cdp)
    auditReport.evidence.boundary320pxStress['homepage'] = boundaryHome
    console.log(`Home 320px Horizontal Overflow: ${boundaryHome.horizontalOverflow}px`)

    const shot320 = `extreme_boundary_320x568_home.png`
    const shotPath320 = path.join(SCREENSHOT_DIR, shot320)
    const shotInfo320 = await takeScreenshot(cdp, shotPath320)
    auditReport.screenshots.push({
      name: shot320,
      path: shotPath320,
      width: 320,
      height: 568,
      bytes: shotInfo320.bytes,
      sha256: shotInfo320.sha256
    })

    if (boundaryDetail.horizontalOverflow > 0 || boundaryHome.horizontalOverflow > 0) {
      auditReport.findings.push({
        severity: 'MEDIUM',
        viewport: '320x568',
        issue: 'HORIZONTAL_OVERFLOW_320PX',
        message: `Horizontal overflow detected at 320px (Detail: ${boundaryDetail.horizontalOverflow}px, Home: ${boundaryHome.horizontalOverflow}px).`
      })
    }

    auditReport.completedAt = new Date().toISOString()
    const hasHigh = auditReport.findings.some(f => f.severity === 'HIGH')
    auditReport.verdict = hasHigh ? 'CHALLENGE_FAILED' : 'APPROVE'

    const evidenceFile = path.join(OUTPUT_DIR, 'evidence.json')
    writeFileSync(evidenceFile, JSON.stringify(auditReport, null, 2))
    console.log(`\nSaved evidence to ${evidenceFile}`)

    console.log(`\n======================================================`)
    console.log(`ADVERSARIAL STRESS VERDICT: ${auditReport.verdict}`)
    console.log(`Total Findings: ${auditReport.findings.length}`)
    console.log(`======================================================\n`)

    return auditReport
  } finally {
    if (cdp) cdp.close()
    if (chromeProcess) chromeProcess.kill()
    try { await rm(userDataDir, { recursive: true, force: true }) } catch {}
  }
}

run().catch(err => {
  console.error('Fatal error:', err)
  process.exit(1)
})
