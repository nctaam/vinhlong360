import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import CatalogInterstitial from '../components/CatalogInterstitial.vue'

describe('Phase 1 Remediation Audit Verification', () => {
  const root = resolve(process.cwd())

  describe('DEF-UX-01: Hero Terroir Chips Dead Link Resolution', () => {
    it('ensures hero terroir chips navigate to /tim-kiem?q= instead of dead 404 route /kham-pha?q=', () => {
      const indexVue = readFileSync(resolve(root, 'pages/index.vue'), 'utf8')
      expect(indexVue).not.toContain('/kham-pha?q=')
      expect(indexVue).toContain("`/tim-kiem?q=${encodeURIComponent(chip.q)}`")
    })
  })

  describe('DEF-ART-01: Anti-Slop Raw Emoji Eradication in CatalogInterstitial', () => {
    const interstitialVue = readFileSync(resolve(root, 'components/CatalogInterstitial.vue'), 'utf8')

    it('contains zero raw bulb emoji in source or props default', () => {
      expect(interstitialVue).not.toContain('💡')
      expect(interstitialVue).toContain('iconName?: string')
      expect(interstitialVue).toContain('effectiveIconName')
    })

    it('renders IconLine with specified iconName and contains no emoji in DOM', async () => {
      const wrapper = await mountSuspended(CatalogInterstitial, {
        props: {
          fact: 'Chương trình OCOP kiểm chứng chất lượng nghiêm ngặt.',
          iconName: 'trophy',
        },
      })
      expect(wrapper.text()).not.toContain('💡')
      expect(wrapper.find('.line-icon').exists()).toBe(true)
      expect(wrapper.find('.line-icon').classes()).toContain('li-trophy')
    })

    it('falls back gracefully to bulb IconLine when iconName is omitted', async () => {
      const wrapper = await mountSuspended(CatalogInterstitial, {
        props: {
          fact: 'Thông tin bổ ích cho chuyến đi.',
        },
      })
      expect(wrapper.text()).not.toContain('💡')
      expect(wrapper.find('.line-icon').exists()).toBe(true)
      expect(wrapper.find('.line-icon').classes()).toContain('li-bulb')
    })
  })

  describe('DEF-A11Y-01: Keyboard Accessibility on Search Autocomplete Remove Button', () => {
    it('equips ac-remove-recent with both click and keydown handlers for full keyboard control', () => {
      const searchVue = readFileSync(resolve(root, 'components/SearchAutocomplete.vue'), 'utf8')
      expect(searchVue).toContain('@click.stop="removeRecent(i)"')
      expect(searchVue).toContain('@keydown.enter.stop.prevent="removeRecent(i)"')
      expect(searchVue).toContain('@keydown.space.stop.prevent="removeRecent(i)"')
    })
  })

  describe('DEF-UX-02: Route Disambiguation and Canonical 301 Redirects', () => {
    it('redirects /events, /map, and /explore to canonical Vietnamese pages and frees backend proxy', () => {
      const nuxtConfig = readFileSync(resolve(root, 'nuxt.config.ts'), 'utf8')
      expect(nuxtConfig).toContain("'/api/events/**': { proxy:")
      expect(nuxtConfig).toMatch(/'\/events':\s*\{\s*redirect:\s*\{\s*to:\s*'\/su-kien',\s*statusCode:\s*301\s*\}\s*\}/)
      expect(nuxtConfig).toMatch(/'\/map':\s*\{\s*redirect:\s*\{\s*to:\s*'\/ban-do',\s*statusCode:\s*301\s*\}\s*\}/)
      expect(nuxtConfig).toMatch(/'\/explore':\s*\{\s*redirect:\s*\{\s*to:\s*'\/du-lich',\s*statusCode:\s*301\s*\}\s*\}/)
    })
  })

  describe('DEF-UX-04 & DEF-UX-05: SourceMark Evidence Chain & OCOP Color Recipe', () => {
    it('equips HomeFeatureDossier with sourceTitle, sourceUrl, and verifiedAt props forwarded to SourceMark', () => {
      const dossierVue = readFileSync(resolve(root, 'components/home/HomeFeatureDossier.vue'), 'utf8')
      expect(dossierVue).toContain('sourceTitle?: string | null')
      expect(dossierVue).toContain('sourceUrl?: string | null')
      expect(dossierVue).toContain('verifiedAt?: string | null')
      expect(dossierVue).toContain(':source-title="sourceTitle"')
      expect(dossierVue).toContain(':source-url="sourceUrl"')
      expect(dossierVue).toContain(':verified-at="verifiedAt"')

      const indexVue = readFileSync(resolve(root, 'pages/index.vue'), 'utf8')
      expect(indexVue).toContain(':source-title="eventSourceTitle(heroFeature)"')
      expect(indexVue).toContain(':source-url="eventSourceUrl(heroFeature)"')
      expect(indexVue).toContain(':verified-at="eventVerifiedAt(heroFeature)"')
    })

    it('enables SourceMark and tri-region color recipe on all OCOP entity cards in pages/ocop.vue', () => {
      const ocopVue = readFileSync(resolve(root, 'pages/ocop.vue'), 'utf8')
      // All four EntityCard occurrences must have color-recipe="tri-region-v1"
      const entityCardMatches = ocopVue.match(/<EntityCard[^>]*>/g) || []
      expect(entityCardMatches.length).toBeGreaterThanOrEqual(4)
      for (const tag of entityCardMatches) {
        expect(tag).toContain('color-recipe="tri-region-v1"')
      }

      const entityCardVue = readFileSync(resolve(root, 'components/EntityCard.vue'), 'utf8')
      expect(entityCardVue).toContain(':source-title="sourceTitle"')
      expect(entityCardVue).toContain(':source-url="sourceUrl"')
      expect(entityCardVue).toContain(':verified-at="verifiedAt"')
    })
  })
})
