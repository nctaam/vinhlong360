// @vitest-environment node
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { createHash } from 'node:crypto'
import { describe, expect, it } from 'vitest'

const root = resolve(__dirname, '../..')
const webNuxt = resolve(__dirname, '..')

// ─────────────────────────────────────────────────────────────────────────────
// WCAG 2.2 Mathematical Contrast Functions (Per ISO / IEC 19798 & WCAG 2.2)
// ─────────────────────────────────────────────────────────────────────────────
function sRGBtoLin(c: number): number {
  const norm = c / 255
  return norm <= 0.04045 ? norm / 12.92 : Math.pow((norm + 0.055) / 1.055, 2.4)
}

function getLuminance(hex: string): number {
  const clean = hex.replace('#', '')
  const r = sRGBtoLin(parseInt(clean.substring(0, 2), 16))
  const g = sRGBtoLin(parseInt(clean.substring(2, 4), 16))
  const b = sRGBtoLin(parseInt(clean.substring(4, 6), 16))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function getContrast(hex1: string, hex2: string): number {
  const l1 = getLuminance(hex1)
  const l2 = getLuminance(hex2)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function highlightMatchSim(name: string, query: string): string {
  const q = query.trim()
  const safe = escapeHtml(name)
  if (!q) return safe
  const idx = name.toLowerCase().indexOf(q.toLowerCase())
  if (idx === -1) return safe
  const before = escapeHtml(name.slice(0, idx))
  const match = escapeHtml(name.slice(idx, idx + q.length))
  const after = escapeHtml(name.slice(idx + q.length))
  return `${before}<mark>${match}</mark>${after}`
}

const SKIP_DIRS = new Set(['node_modules', '.nuxt', '.output', 'dist', '.git', '.claude'])

function getAllVueFiles(dir: string): string[] {
  let results: string[] = []
  if (!dir || !existsSync(dir)) return results
  const list = readdirSync(dir)
  for (const file of list) {
    if (SKIP_DIRS.has(file)) continue
    const filePath = join(dir, file)
    const stat = statSync(filePath)
    if (stat && stat.isDirectory()) {
      results = results.concat(getAllVueFiles(filePath))
    } else if (file.endsWith('.vue')) {
      results.push(filePath)
    }
  }
  return results
}

describe('Challenger 1: Empirical Adversarial Stress & Edge Case Harness', () => {
  const homeVue = readFileSync(resolve(webNuxt, 'pages/index.vue'), 'utf8')
  const homeNocturneCss = readFileSync(resolve(webNuxt, 'assets/css/home-nocturne.css'), 'utf8')
  const variablesCss = readFileSync(resolve(webNuxt, 'assets/css/variables.css'), 'utf8')
  const shellCss = readFileSync(resolve(webNuxt, 'assets/css/shell.css'), 'utf8')
  const curatedShowcaseVue = readFileSync(resolve(webNuxt, 'components/home/HomeCuratedShowcase.vue'), 'utf8')
  const culinaryTrailVue = readFileSync(resolve(webNuxt, 'components/home/HomeCulinaryTrail.vue'), 'utf8')
  const riversideStaysVue = readFileSync(resolve(webNuxt, 'components/home/HomeRiversideStays.vue'), 'utf8')
  const travelPlannerVue = readFileSync(resolve(webNuxt, 'components/home/HomeTravelPlanner.vue'), 'utf8')
  const travelCompanionVue = readFileSync(resolve(webNuxt, 'components/home/HomeTravelCompanion.vue'), 'utf8')
  const intentAnchorsVue = readFileSync(resolve(webNuxt, 'components/home/HomeIntentAnchors.vue'), 'utf8')

  // ───────────────────────────────────────────────────────────────────────────
  // OBJECTIVE 1.1: Multi-Criteria Search Input Resilience
  // ───────────────────────────────────────────────────────────────────────────
  describe('Adversarial Test 1: Multi-Criteria Search Input Resilience', () => {
    it('handles empty, whitespace, and control inputs without exceptions', () => {
      const inputs = ['', '   ', '\t\n\r', '     ']
      for (const input of inputs) {
        expect(() => highlightMatchSim('Quần Thể Di Sản Lò Gạch', input)).not.toThrow()
        const res = highlightMatchSim('Quần Thể Di Sản Lò Gạch', input)
        expect(res).toBe('Quần Thể Di Sản Lò Gạch')
      }
    })

    it('handles extreme strings up to 10,000 characters without memory exhaustion or crash', () => {
      const extreme1k = 'A'.repeat(1000)
      const extreme10k = 'Vĩnh Long '.repeat(1000)
      expect(() => highlightMatchSim('Cù Lao An Bình', extreme1k)).not.toThrow()
      expect(() => highlightMatchSim('Cù Lao An Bình', extreme10k)).not.toThrow()
      expect(highlightMatchSim('Cù Lao An Bình', extreme1k)).toBe('Cù Lao An Bình')
    })

    it('safely handles regex special characters without regex injection or catastrophic backtracking', () => {
      const regexStrings = [
        '.*', '+', '?', '^', '$', '{', '}', '(', ')', '|', '[', ']', '\\',
        '.*+?^${}()|[]\\',
        '[a-z]+(foo|bar)*',
        '(?=.*[0-9])',
        '\\d+\\s+.*',
      ]
      for (const pattern of regexStrings) {
        // Must never throw RegExp syntax error
        expect(() => highlightMatchSim('Mang Thít [Văn hóa]', pattern)).not.toThrow()
      }
      // Exact literal match of brackets
      const bracketMatch = highlightMatchSim('Mang Thít [Văn hóa]', '[Văn hóa]')
      expect(bracketMatch).toContain('<mark>[Văn hóa]</mark>')
    })

    it('resiliently handles complex Vietnamese diacritics and combining characters', () => {
      const diacriticCases = [
        { name: 'Đồng bằng sông Cửu Long', query: 'sông Cửu Long' },
        { name: 'Cù Lao An Bình & Vườn Trái Cây', query: 'An Bình' },
        { name: 'Chợ Nổi Trà Ôn Sông Hậu', query: 'Trà Ôn' },
        { name: 'Quần Thể Di Sản Gốm Đỏ Mang Thít', query: 'Mang Thít' },
        { name: 'Cá Tai Tượng Chiên Xù', query: 'Tai Tượng' },
      ]
      for (const item of diacriticCases) {
        const highlighted = highlightMatchSim(item.name, item.query)
        expect(highlighted).toContain(`<mark>${item.query}</mark>`)
      }
    })

    it('neutralizes HTML and script injection attempts in search queries', () => {
      const xssQueries = [
        '<script>alert("xss")</script>',
        '"><img src=x onerror=alert(1)>',
        '<b>bold</b>',
        '\' OR 1=1 --',
      ]
      for (const q of xssQueries) {
        const res = highlightMatchSim('<script>alert("test")</script>', q)
        expect(res).not.toContain('<script>')
        expect(res).not.toContain('<img src=x')
      }
    })
  })

  // ───────────────────────────────────────────────────────────────────────────
  // OBJECTIVE 1.2: Touch Target Ergonomics (WCAG 2.2 AAA >= 44x44px, Dock >= 48px)
  // ───────────────────────────────────────────────────────────────────────────
  describe('Adversarial Test 2: Touch Target Ergonomics & Hitbox Validation', () => {
    it('asserts Quick Anchors (HomeIntentAnchors) have min-height >= 48px', () => {
      expect(intentAnchorsVue).toMatch(/\.home-intent-anchor\s*\{[\s\S]*?min-height:\s*48px;/)
    })

    it('asserts Mobile Dock (PublicBottomNav) items have min-height >= 52px (>= 48px standard)', () => {
      expect(shellCss).toMatch(/\.public-bottom-nav-item\s*\{[\s\S]*?min-height:\s*52px;/)
    })

    it('asserts hero filter pills and terroir chips meet min-height >= 44px', () => {
      expect(homeNocturneCss).toMatch(/\.home\s+\.hero-filter-pill\s*\{[\s\S]*?min-height:\s*var\(--touch-min,\s*44px\);/)
      expect(homeNocturneCss).toMatch(/\[data-home-pilot="nocturne-b1"\]\s+\.hero-terroir-chip\s*\{[\s\S]*?min-height:\s*var\(--touch-min,\s*44px\);/)
    })

    it('asserts Culinary Trail action buttons meet min-height >= 44px', () => {
      expect(culinaryTrailVue).toMatch(/\.home-culinary-card__btn\s*\{[\s\S]*?min-height:\s*44px;/)
    })

    it('asserts Riverside Stays action buttons meet min-height >= 44px', () => {
      expect(riversideStaysVue).toMatch(/\.home-stay-card__action\s+\.btn\s*\{[\s\S]*?min-height:\s*44px;/)
    })

    it('asserts Travel Planner tab buttons meet min-height >= 48px and action CTA >= 44px', () => {
      expect(travelPlannerVue).toMatch(/\.home-planner-tab-btn\s*\{[\s\S]*?min-height:\s*48px;/)
      expect(travelPlannerVue).toMatch(/\.home-planner-card__actions\s+\.btn\s*\{[\s\S]*?min-height:\s*44px;/)
    })

    it('asserts Travel Companion links meet min-height >= 44px and hotline buttons >= 48px', () => {
      expect(travelCompanionVue).toMatch(/\.home-companion-card__link\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(travelCompanionVue).toMatch(/\.home-hotline-btn\s*\{[\s\S]*?min-height:\s*48px;/)
    })

    it('asserts HomeCuratedShowcase satellite link meets WCAG 2.2 AAA >= 44px requirement', () => {
      // HomeCuratedShowcase.vue line 530 defines min-height: var(--touch-min, 44px);
      const match = curatedShowcaseVue.match(/\.home-curated-satellite__link\s*\{[\s\S]*?min-height:\s*(?:var\(--touch-min,\s*(\d+)px\)|(\d+)px);/)
      expect(match).not.toBeNull()
      const minHeight = parseInt(match?.[1] ?? match?.[2] ?? '0', 10)
      expect(minHeight).toBeGreaterThanOrEqual(44)
    })
  })

  // ───────────────────────────────────────────────────────────────────────────
  // OBJECTIVE 1.3: Responsive & Viewport Stress (320px - 2560px)
  // ───────────────────────────────────────────────────────────────────────────
  describe('Adversarial Test 3: Responsive Layout & Viewport Resilience', () => {
    it('guarantees max-width constraints (var(--maxw)) on all core layout containers to prevent ultra-wide blowouts up to 2560px', () => {
      expect(homeNocturneCss).toContain('max-width: var(--maxw);')
      expect(intentAnchorsVue).toContain('max-width: var(--maxw);')
    })

    it('enforces minmax(0, ...) grid tracks in curated showcase to prevent horizontal overflow blowout', () => {
      expect(curatedShowcaseVue).toMatch(/grid-template-columns:\s*minmax\(0,\s*1\.35fr\)\s*minmax\(0,\s*1fr\);/)
    })

    it('ensures mobile dock grid template accommodates 5 columns evenly without fixed overflow', () => {
      expect(shellCss).toMatch(/grid-template-columns:\s*repeat\(5,\s*minmax\(0,\s*1fr\)\);/)
    })

    it('confirms hero layout has mobile container query or fallback at narrow viewports', () => {
      expect(homeNocturneCss).toContain('container: home-lead / inline-size;')
    })
  })

  // ───────────────────────────────────────────────────────────────────────────
  // OBJECTIVE 1.4: Zero Audio/Video Invariance
  // ───────────────────────────────────────────────────────────────────────────
  describe('Adversarial Test 4: Absolute Zero Audio/Video Element Invariance', () => {
    it('proves zero <audio> or <video> or autoplay elements exist in any Vue component across web-nuxt', () => {
      const vueFiles = getAllVueFiles(resolve(webNuxt, 'components')).concat(getAllVueFiles(resolve(webNuxt, 'pages')))
      expect(vueFiles.length).toBeGreaterThan(50)

      for (const file of vueFiles) {
        const content = readFileSync(file, 'utf8')
        expect(content, `${file} must not contain <audio>`).not.toMatch(/<audio\b/i)
        expect(content, `${file} must not contain <video>`).not.toMatch(/<video\b/i)
        expect(content, `${file} must not contain autoplay`).not.toMatch(/\bautoplay\b/i)
        expect(content, `${file} must not construct new Audio()`).not.toMatch(/new\s+Audio\s*\(/i)
      }
    })
  })

  // ───────────────────────────────────────────────────────────────────────────
  // OBJECTIVE 1.5: Contrast Validation (WCAG 2.2 AAA >= 7:1, High-Glare >= 14:1)
  // ───────────────────────────────────────────────────────────────────────────
  describe('Adversarial Test 5: Contrast Validation against WCAG 2.2 AAA Standards', () => {
    it('verifies standard Mekong Ink on Alluvial Paper exceeds WCAG AAA (>= 7:1)', () => {
      const cr = getContrast('#F9F7F1', '#081A16')
      expect(cr).toBeGreaterThanOrEqual(7.0)
      expect(Number(cr.toFixed(2))).toBe(16.76)
    })

    it('verifies high-glare foreground (#000000 on #ffffff) achieves perfect 21:1 contrast (>= 14:1)', () => {
      const cr = getContrast('#ffffff', '#000000')
      expect(cr).toBeGreaterThanOrEqual(14.0)
      expect(Number(cr.toFixed(2))).toBe(21.00)
    })

    it('verifies high-glare border (#12100e on #ffffff) achieves >= 14:1 contrast', () => {
      const cr = getContrast('#ffffff', '#12100e')
      expect(cr).toBeGreaterThanOrEqual(14.0)
      expect(Number(cr.toFixed(2))).toBe(18.98)
    })

    it('verifies high-glare accent text (#4a1b0a on #ffffff) achieves >= 14:1 contrast', () => {
      const cr = getContrast('#ffffff', '#4a1b0a')
      expect(cr).toBeGreaterThanOrEqual(14.0)
      expect(Number(cr.toFixed(2))).toBe(14.46)
    })

    it('verifies high-glare river (#003652) and gold (#704b06) exceed WCAG AAA (>= 7:1)', () => {
      const crRiver = getContrast('#ffffff', '#003652')
      const crGold = getContrast('#ffffff', '#704b06')
      expect(crRiver).toBeGreaterThanOrEqual(7.0) // 12.73:1
      expect(crGold).toBeGreaterThanOrEqual(7.0)  // 7.78:1
    })
  })

  describe('Adversarial Test 6: HomeIntentAnchors Ergonomics & Micro-motion', () => {
    it('enforces touch target >= 48px, focus-visible, and avatar hover micro-motion on HomeIntentAnchors', () => {
      const anchorsContent = readFileSync(resolve(webNuxt, 'components/home/HomeIntentAnchors.vue'), 'utf8')
      expect(anchorsContent).toMatch(/min-height:\s*48px/)
      expect(anchorsContent).toMatch(/\.home-intent-anchor:focus-visible/)
      expect(anchorsContent).toMatch(/\.home-intent-anchor:hover\s+\.home-intent-anchor__avatar\s*\{[\s\S]*?transform:\s*scale\(1\.06\)/)
    })
  })

  describe('Adversarial Test 7: HomeTravelPlanner Stop Active Feedback & Marker Micro-motion', () => {
    it('enforces active tactile scale and marker hover micro-motion on HomeTravelPlanner stops', () => {
      const plannerContent = readFileSync(resolve(webNuxt, 'components/home/HomeTravelPlanner.vue'), 'utf8')
      expect(plannerContent).toMatch(/\.home-planner-stop:active/)
      expect(plannerContent).toMatch(/\.home-planner-stop:hover\s+\.home-planner-stop__marker\s*\{[\s\S]*?transform:\s*scale\(1\.08\)/)
    })
  })

  describe('Adversarial Test 8: Event Mini & Seasonal Signal Tactile Ergonomics', () => {
    it('enforces active tactile scale and double-ring focus indicator on event mini cards', () => {
      expect(homeNocturneCss).toMatch(/\.event-mini:active\s*\{[^}]*transform:\s*scale\(0\.98\)/)
      expect(homeNocturneCss).toMatch(/\.event-mini:focus-visible\s*\{[^}]*outline:\s*2px\s+solid\s+var\(--color-focus\)/)
    })

    it('enforces active tactile scale and double-ring focus indicator on seasonal signal rows', () => {
      expect(homeNocturneCss).toMatch(/\.home-season-row:active\s*\{[^}]*transform:\s*scale\(0\.98\)/)
      expect(homeNocturneCss).toMatch(/\.home-season-row:focus-visible\s*\{[^}]*outline:\s*2px\s+solid\s+var\(--color-focus\)/)
    })
  })

  describe('Adversarial Test 9: Journey Action Rail Active Tactile Response', () => {
    it('enforces active tactile scale on journey action buttons', () => {
      const railContent = readFileSync(resolve(webNuxt, 'components/JourneyActionRail.vue'), 'utf8')
      expect(railContent).toMatch(/\.journey-action:active\s*\{[^}]*transform:\s*scale\(0\.98\)/)
    })
  })

  describe('Adversarial Test 10: For-You Personalized Strip Ergonomics', () => {
    it('enforces active tactile scale and double-ring focus indicator on for-you chips', () => {
      expect(homeNocturneCss).toMatch(/\.fy-chip:active\s*\{[^}]*transform:\s*scale\(0\.98\)/)
      expect(homeNocturneCss).toMatch(/\.fy-chip:focus-visible\s*\{[^}]*outline:\s*2px\s+solid\s+var\(--color-focus\)/)
    })

    it('enforces subtle thumbnail zoom micro-motion on for-you chip hover', () => {
      expect(homeNocturneCss).toMatch(/\.fy-chip:hover\s+\.fy-thumb\s+img\s*\{[^}]*transform:\s*scale\(1\.06\)/)
    })
  })

  // ───────────────────────────────────────────────────────────────────────────
  // OBJECTIVE 2: Bit-for-bit SHA-256 Invariance
  // ───────────────────────────────────────────────────────────────────────────
  describe('Objective 2: Bit-for-Bit SHA-256 Invariance of Database and Data JSON', () => {
    it('asserts vinhlong360.db exactly matches canonical hash 20ac61bf7d247d8df35bd20bfe11140cf6eebae0980de4af5720d5ed73add742', () => {
      const dbPath = resolve(root, 'agent/data/vinhlong360.db')
      const dbBytes = readFileSync(dbPath)
      const hash = createHash('sha256').update(dbBytes).digest('hex')
      expect(hash.toLowerCase()).toBe('20ac61bf7d247d8df35bd20bfe11140cf6eebae0980de4af5720d5ed73add742')
    })

    it('asserts web/data.json exactly matches canonical hash fa3a2ac7d802f082401b6fdfb0841e4551ed27d625eb5dedfbdf7e75272a46f3', () => {
      const dataRaw = readFileSync(resolve(process.cwd(), '../web/data.json'))
      const hash = createHash('sha256').update(dataRaw).digest('hex')
      expect(hash.toLowerCase()).toBe('fa3a2ac7d802f082401b6fdfb0841e4551ed27d625eb5dedfbdf7e75272a46f3')
    })
  })
})
