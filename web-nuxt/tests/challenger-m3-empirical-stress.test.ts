// @ts-nocheck
// @vitest-environment node
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { describe, expect, it } from 'vitest'

const webNuxt = resolve(__dirname, '..')

const files = {
  showcase: resolve(webNuxt, 'components/home/HomeCuratedShowcase.vue'),
  culinary: resolve(webNuxt, 'components/home/HomeCulinaryTrail.vue'),
  stays: resolve(webNuxt, 'components/home/HomeRiversideStays.vue'),
  companion: resolve(webNuxt, 'components/home/HomeTravelCompanion.vue'),
  planner: resolve(webNuxt, 'components/home/HomeTravelPlanner.vue'),
  index: resolve(webNuxt, 'pages/index.vue'),
  homeNocturneCss: resolve(webNuxt, 'assets/css/home-nocturne.css'),
  baseCss: resolve(webNuxt, 'assets/css/base.css'),
  variablesCss: resolve(webNuxt, 'assets/css/variables.css'),
}

const showcaseContent = readFileSync(files.showcase, 'utf8')
const culinaryContent = readFileSync(files.culinary, 'utf8')
const staysContent = readFileSync(files.stays, 'utf8')
const companionContent = readFileSync(files.companion, 'utf8')
const indexContent = readFileSync(files.index, 'utf8')
const homeNocturneCss = readFileSync(files.homeNocturneCss, 'utf8')
const baseCss = readFileSync(files.baseCss, 'utf8')
const variablesCss = readFileSync(files.variablesCss, 'utf8')

describe('Challenger M3: Empirical Adversarial Stress Verification Suite', () => {
  // ─── STRESS TEST 1: Touch Targets on Interactive Elements (>= 44x44px) ───
  describe('Stress Test 1: Touch Targets on Interactive Elements (>= 44x44px)', () => {
    it('defines global --touch-min >= 44px in variables.css and enforces it in base.css', () => {
      const match = variablesCss.match(/--touch-min:\s*(\d+)px;/)
      expect(match).not.toBeNull()
      expect(parseInt(match![1], 10)).toBeGreaterThanOrEqual(44)
      expect(baseCss).toContain(':where(a[href], button, [role="button"], input:not([type="hidden"]), select, textarea, summary) { min-height: var(--touch-min); }')
    })

    it('enforces min-height >= 44px on HomeCuratedShowcase bookmarks and action buttons', () => {
      const leadBookmarkMatch = showcaseContent.match(/\.home-bookmark-btn\s*\{[\s\S]*?min-width:\s*(\d+)px;[\s\S]*?min-height:\s*(\d+)px;/)
      expect(leadBookmarkMatch).not.toBeNull()
      expect(parseInt(leadBookmarkMatch![1], 10)).toBeGreaterThanOrEqual(44)
      expect(parseInt(leadBookmarkMatch![2], 10)).toBeGreaterThanOrEqual(44)

      const satBookmarkMatch = showcaseContent.match(/\.home-bookmark-btn--sm\s*\{[\s\S]*?min-width:\s*(\d+)px;[\s\S]*?min-height:\s*(\d+)px;/)
      expect(satBookmarkMatch).not.toBeNull()
      expect(parseInt(satBookmarkMatch![1], 10)).toBeGreaterThanOrEqual(44)
      expect(parseInt(satBookmarkMatch![2], 10)).toBeGreaterThanOrEqual(44)

      const leadActionsMatch = showcaseContent.match(/\.home-curated-lead__actions\s+\.btn\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
      expect(leadActionsMatch).not.toBeNull()
      expect(parseInt(leadActionsMatch![1], 10)).toBeGreaterThanOrEqual(44)

      const satLinkMatch = showcaseContent.match(/\.home-curated-satellite__link\s*\{[\s\S]*?min-height:\s*(?:var\(--touch-min,\s*(\d+)px\)|(\d+)px);/)
      const val = parseInt(satLinkMatch?.[1] ?? satLinkMatch?.[2] ?? '0', 10)
      expect(val).toBeGreaterThanOrEqual(44)
    })

    it('enforces min-height >= 44px on HomeCulinaryTrail and HomeRiversideStays actions', () => {
      const culinaryBtnMatch = culinaryContent.match(/\.home-culinary-card__btn\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
      expect(culinaryBtnMatch).not.toBeNull()
      expect(parseInt(culinaryBtnMatch![1], 10)).toBeGreaterThanOrEqual(44)

      const staysBtnMatch = staysContent.match(/\.home-stay-card__action\s+\.btn\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
      expect(staysBtnMatch).not.toBeNull()
      expect(parseInt(staysBtnMatch![1], 10)).toBeGreaterThanOrEqual(44)
    })

    it('enforces min-height >= 44px (and >= 48px for hotlines) on HomeTravelCompanion', () => {
      const compLinkMatch = companionContent.match(/\.home-companion-card__link\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
      expect(compLinkMatch).not.toBeNull()
      expect(parseInt(compLinkMatch![1], 10)).toBeGreaterThanOrEqual(44)

      const compHotlineMatch = companionContent.match(/\.home-hotline-btn\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
      expect(compHotlineMatch).not.toBeNull()
      expect(parseInt(compHotlineMatch![1], 10)).toBeGreaterThanOrEqual(48)

      const compQuickHotlineMatch = companionContent.match(/\.home-hotline-btn--quick\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
      expect(compQuickHotlineMatch).not.toBeNull()
      expect(parseInt(compQuickHotlineMatch![1], 10)).toBeGreaterThanOrEqual(48)
    })

    it('enforces min-height >= 44px on pages/index.vue interactive filters and chips', () => {
      const heroFilterMatch = homeNocturneCss.match(/\.home\s+\.hero-filter-pill\s*\{[\s\S]*?min-height:\s*var\(--touch-min,\s*(\d+)px\);[\s\S]*?min-width:\s*(\d+)px;/)
      expect(heroFilterMatch).not.toBeNull()
      expect(parseInt(heroFilterMatch![1], 10)).toBeGreaterThanOrEqual(44)
      expect(parseInt(heroFilterMatch![2], 10)).toBeGreaterThanOrEqual(44)

      const terroirChipMatch = homeNocturneCss.match(/\[data-home-pilot="nocturne-b1"\]\s+\.hero-terroir-chip\s*\{[\s\S]*?min-height:\s*var\(--touch-min,\s*(\d+)px\);/)
      expect(terroirChipMatch).not.toBeNull()
      expect(parseInt(terroirChipMatch![1], 10)).toBeGreaterThanOrEqual(44)

      const heroNearbyMatch = indexContent.match(/\.home\s+\.hero-nearby\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
      expect(heroNearbyMatch).not.toBeNull()
      expect(parseInt(heroNearbyMatch![1], 10)).toBeGreaterThanOrEqual(44)
    })
  })

  // ─── STRESS TEST 2: 62/38 Asymmetric Grid Layout Rule in HomeCuratedShowcase ───
  describe('Stress Test 2: 62/38 Asymmetric Grid Layout Rule in HomeCuratedShowcase', () => {
    it('enforces minmax(0, 1.35fr) minmax(0, 1fr) asymmetric grid ratio on desktop (>= 960px)', () => {
      expect(showcaseContent).toMatch(/grid-template-columns:\s*minmax\(0,\s*1\.35fr\)\s*minmax\(0,\s*1fr\);/)
      expect(showcaseContent).toMatch(/@media\s*\(min-width:\s*960px\)\s*\{\s*\.home-curated-showcase__layout\s*\{/)
    })

    it('guarantees responsive single-column fallback on mobile viewports', () => {
      expect(showcaseContent).toMatch(/\.home-curated-showcase__layout\s*\{[\s\S]*?grid-template-columns:\s*1fr;/)
    })

    it('arranges satellite cards in a 2x2 grid on >= 640px viewport', () => {
      expect(showcaseContent).toMatch(/@media\s*\(min-width:\s*640px\)\s*\{\s*\.home-curated-satellites\s*\{\s*grid-template-columns:\s*repeat\(2,\s*1fr\);/)
    })
  })

  // ─── STRESS TEST 3: Description Lengths Across All Cards (<= 120 chars / 2 lines) ───
  describe('Stress Test 3: Description Lengths Across All Cards', () => {
    it('verifies HomeCuratedShowcase lead description and satellite summaries are <= 120 chars', () => {
      const leadDescMatch = showcaseContent.match(/desc:\s*['"]([^'"]+)['"]/)
      expect(leadDescMatch).not.toBeNull()
      expect(leadDescMatch![1].length).toBeLessThanOrEqual(120)

      const satSummaries = [...showcaseContent.matchAll(/summary:\s*['"]([^'"]+)['"]/g)].map(m => m[1])
      expect(satSummaries.length).toBe(4)
      for (const s of satSummaries) {
        expect(s.length).toBeLessThanOrEqual(120)
      }

      expect(showcaseContent).toMatch(/\.home-curated-satellite__summary\s*\{[\s\S]*?-webkit-line-clamp:\s*2;/)
    })

    it('verifies HomeCulinaryTrail cards maintain visual-first architecture with 0 text-wall descriptions', () => {
      expect(culinaryContent).not.toContain('home-culinary-card__desc')
    })

    it('verifies HomeRiversideStays homestay descriptions are <= 120 chars', () => {
      const stayDescs = [...staysContent.matchAll(/desc:\s*['"]([^'"]+)['"]/g)].map(m => m[1])
      expect(stayDescs.length).toBeGreaterThanOrEqual(3)
      for (const d of stayDescs) {
        expect(d.length).toBeLessThanOrEqual(120)
      }
    })
  })

  // ─── STRESS TEST 4: Prohibited Generic AI Slop Phrases ───
  describe('Stress Test 4: Prohibited Generic AI Slop Phrases', () => {
    const prohibitedPhrases = [
      'nâng tầm trải nghiệm',
      'hành trình vô tận',
      'vẻ đẹp bất tận',
      'khám phá không giới hạn',
      'trải nghiệm phong phú',
      'bứt phá mọi giới hạn',
      'tinh hoa hội tụ',
      'bản giao hưởng',
      'chạm vào cảm xúc',
      'đánh thức mọi giác quan',
    ]

    const components = [
      { name: 'HomeCuratedShowcase', content: showcaseContent },
      { name: 'HomeCulinaryTrail', content: culinaryContent },
      { name: 'HomeRiversideStays', content: staysContent },
      { name: 'HomeTravelCompanion', content: companionContent },
      { name: 'pages/index.vue', content: indexContent },
    ]

    for (const comp of components) {
      it(`verifies ${comp.name} is free of AI slop phrases and sparkles`, () => {
        const lower = comp.content.toLowerCase()
        for (const p of prohibitedPhrases) {
          expect(lower).not.toContain(p)
        }
        expect(comp.content).not.toMatch(/name=["']sparkles?["']|icon-name=["']sparkles?["']|auto_awesome/i)
      })
    }
  })

  // ─── STRESS TEST 5: Zero Audio/Video Autoplay Elements ───
  describe('Stress Test 5: Zero Audio/Video Autoplay Elements', () => {
    it('verifies 0 <audio>, 0 <video>, 0 autoplay, and 0 new Audio() across application source', () => {
      const audioRegex = /<audio\b/i
      const videoRegex = /<video\b/i
      const autoplayRegex = /\bautoplay\b/i
      const newAudioRegex = /new\s+Audio\s*\(/i

      function scan(dir: string): { file: string; type: string }[] {
        let violations: { file: string; type: string }[] = []
        const list = readdirSync(dir)
        for (const item of list) {
          if (['node_modules', '.nuxt', '.output', 'dist', '.git', 'tests', 'scripts'].includes(item)) continue
          const fullPath = join(dir, item)
          const stat = statSync(fullPath)
          if (stat.isDirectory()) {
            violations = violations.concat(scan(fullPath))
          } else if (/\.(vue|ts|js|mjs|html)$/.test(item)) {
            const src = readFileSync(fullPath, 'utf8')
            if (audioRegex.test(src)) violations.push({ file: fullPath, type: '<audio>' })
            if (videoRegex.test(src)) violations.push({ file: fullPath, type: '<video>' })
            if (autoplayRegex.test(src)) violations.push({ file: fullPath, type: 'autoplay' })
            if (newAudioRegex.test(src)) violations.push({ file: fullPath, type: 'new Audio()' })
          }
        }
        return violations
      }

      const violations = scan(webNuxt)
      expect(violations).toEqual([])
    })
  })

  // ─── STRESS TEST 6: Zero Raw Hex Colors (#...) in Newly Edited Components ───
  describe('Stress Test 6: Zero Raw Hex Colors (#...) in Newly Edited Components', () => {
    it('verifies zero raw hex colors across newly edited components', () => {
      const hexPattern = /#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b/g
      const components = [
        { name: 'HomeCuratedShowcase', content: showcaseContent },
        { name: 'HomeCulinaryTrail', content: culinaryContent },
        { name: 'HomeRiversideStays', content: staysContent },
        { name: 'HomeTravelCompanion', content: companionContent },
        { name: 'pages/index.vue', content: indexContent },
      ]

      for (const comp of components) {
        const matches = comp.content.match(hexPattern) || []
        expect(matches, `${comp.name} contains raw hex colors: ${matches.join(', ')}`).toEqual([])
      }
    })
  })
})
