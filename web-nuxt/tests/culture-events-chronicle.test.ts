import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

describe('R4: Mekong Cultural Chronicle, Water Badges & Editorial Craft', () => {
  const badgePath = resolve(__dirname, '../components/MekongWaterBadge.vue')
  const postCardVue = readFileSync(resolve(__dirname, '../components/PostCard.vue'), 'utf8')
  const theoMuaVue = readFileSync(resolve(__dirname, '../pages/theo-mua.vue'), 'utf8')

  describe('Tier 1 & Tier 4: Mekong Water Flow Badges (MekongWaterBadge.vue)', () => {
    it('provides MekongWaterBadge component supporting key tidal cycle states', () => {
      expect(existsSync(badgePath), 'MekongWaterBadge.vue must exist').toBe(true)
      const badgeVue = readFileSync(badgePath, 'utf8')

      // Verifies semantic markers and tidal cycle states
      expect(badgeVue).toContain('data-water-badge')
      expect(badgeVue).toContain('data-tide-state')
      expect(badgeVue).toContain('Con nước rong')
      expect(badgeVue).toContain('Con nước kém')
      expect(badgeVue).toContain('Nước lớn')
      expect(badgeVue).toContain('Nước ròng')

      // Verifies lunar date integration
      expect(badgeVue).toContain('formattedLunarDate')

      // Verifies touch target >= 44x44px with ::before expansion
      expect(badgeVue).toMatch(/\.mekong-water-badge\s*\{[\s\S]*?min-height:\s*44px/)
      expect(badgeVue).toMatch(/\.mekong-water-badge\s*\{[\s\S]*?min-width:\s*44px/)
      expect(badgeVue).toMatch(/\.mekong-water-badge::before\s*\{[\s\S]*?min-width:\s*44px[\s\S]*?min-height:\s*44px/)
    })

    it('integrates MekongWaterBadge into seasonal cultural chronicle (theo-mua.vue)', () => {
      expect(theoMuaVue).toContain('<MekongWaterBadge')
    })
  })

  describe('Tier 1 & Tier 3: Classic Lora Pull-Quotes with <cite> Source Attribution', () => {
    it('styles pull-quotes with Lora serif italic and Gold Phù Sa accent border', () => {
      expect(theoMuaVue).toContain('pull-quote')
      expect(theoMuaVue).toMatch(/\.pull-quote\s*\{[\s\S]*?font-family:\s*var\(--font-editorial\)/)
      expect(theoMuaVue).toMatch(/\.pull-quote\s*\{[\s\S]*?font-style:\s*italic/)
      expect(theoMuaVue).toMatch(/\.pull-quote\s*\{[\s\S]*?border-left:\s*3px\s+solid\s+var\(--(?:color-material-gold|alluvial-gold)/)
    })

    it('enforces mandatory <cite> attribution inside pull-quotes in theo-mua.vue', () => {
      expect(theoMuaVue).toMatch(/<blockquote\s+class="pull-quote">[\s\S]*?<cite>[\s\S]*?<\/cite>[\s\S]*?<\/blockquote>/)
      expect(theoMuaVue).toMatch(/Ban biên tập vinhlong360/)
    })
  })

  describe('Tier 1 & Tier 3: Field Author Badges & Anti-Slop Discipline in PostCard', () => {
    it('replaces anonymous avatars with verified field author badge for editorial posts', () => {
      expect(postCardVue).toContain('isVerifiedAuthor')
      expect(postCardVue).toContain('thread-author-badge')
      expect(postCardVue).toContain('SourceMark')
      expect(postCardVue).toContain('SourceMark: Ban biên tập vinhlong360')
    })

    it('strictly bans raw emoji salad in PostCard, replacing with vector IconLine', () => {
      // Must not contain raw repost emoji (🔁) or raw edit emoji (✍️)
      expect(postCardVue).not.toContain('🔁')
      expect(postCardVue).not.toContain('✍️')

      // Must use vector icons for actions
      expect(postCardVue).toMatch(/<IconLine\s+name="repeat"\s*\/>/)
      expect(postCardVue).toMatch(/<IconLine\s+name="pencil"\s*\/>/)
    })
  })

  describe('Tier 1 & Tier 2: Ergonomic Touch Targets on Seasonal Controls (>= 44px)', () => {
    it('enforces minimum 44x44px touch targets on season wheel notches (.ring-notch)', () => {
      expect(theoMuaVue).toMatch(/\.ring-notch\s*\{[\s\S]*?min-width:\s*44px[\s\S]*?min-height:\s*44px/)
      expect(theoMuaVue).toMatch(/\.ring-notch::before\s*\{[\s\S]*?min-width:\s*44px[\s\S]*?min-height:\s*44px/)
    })

    it('enforces minimum 44x44px touch targets on season timeline cells (.stl-cell)', () => {
      expect(theoMuaVue).toMatch(/\.stl-cell\s*\{[\s\S]*?min-height:\s*44px[\s\S]*?min-width:\s*44px/)
      expect(theoMuaVue).toMatch(/\.stl-cell::before\s*\{[\s\S]*?min-width:\s*44px[\s\S]*?min-height:\s*44px/)
    })
  })
})
