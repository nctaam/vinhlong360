import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('R2: Heritage Detail & Editorial Monocle Craftsmanship', () => {
  const detailCss = readFileSync(resolve(__dirname, '../assets/css/detail.css'), 'utf8')
  const variablesCss = readFileSync(resolve(__dirname, '../assets/css/variables.css'), 'utf8')
  const detailVue = readFileSync(resolve(__dirname, '../pages/dia-diem/[id].vue'), 'utf8')
  const aeoSummaryVue = readFileSync(resolve(__dirname, '../components/DetailAeoSummary.vue'), 'utf8')

  describe('Tier 1 & Tier 3: Editorial Typography — Lora Serif Hierarchy', () => {
    it('enforces Lora serif on content section headings (.desc-heading, .desc-subheading)', () => {
      expect(detailCss).toMatch(/\.desc-heading\s*\{[^}]*font-family:\s*var\(--font-editorial\)/)
      expect(detailCss).toMatch(/\.desc-subheading\s*\{[^}]*font-family:\s*var\(--font-editorial\)/)
    })

    it('enforces Lora serif on hero title and drop-cap lead openings', () => {
      expect(detailCss).toMatch(/\.detail-cover\s+h1\s*\{[^}]*font-family:\s*var\(--font-editorial\)/)
      expect(detailCss).toMatch(/\.detail-main\s+\.lead::first-letter\s*\{[^}]*font-family:\s*var\(--font-editorial\)/)
    })

    it('guarantees --font-editorial token priority begins with Lora', () => {
      expect(variablesCss).toMatch(/--font-editorial:\s*'Lora'/)
    })
  })

  describe('Tier 1 & Tier 2: Reading Column Measure (65-70ch Ergonomics)', () => {
    it('defines standard reading measure token within optimal 65-70ch range', () => {
      expect(variablesCss).toMatch(/--measure-read:\s*68ch/)
    })

    it('constrains entity description and extra content to --measure-read', () => {
      expect(detailCss).toMatch(/\.entity-description\s*\{[^}]*max-width:\s*var\(--measure-read\)/)
      expect(detailCss).toMatch(/\.extra-content\s*\{[^}]*max-width:\s*var\(--measure-read\)/)
      expect(detailCss).toMatch(/\.detail-main\s+\.lead\s*\{[^}]*max-width:\s*var\(--measure-read\)/)
    })
  })

  describe('Tier 1 & Tier 3: AEO Provenance Plaque (#c99446 Gold Phù Sa Border)', () => {
    it('verifies that --alluvial-gold token resolves to #c99446 Phù Sa Cổ Chiên', () => {
      expect(variablesCss).toMatch(/--alluvial-gold:\s*#c99446/i)
    })

    it('enforces Gold Phù Sa border and subtle warm background on AEO Plaque', () => {
      expect(aeoSummaryVue).toMatch(/border:\s*1\.5px\s+solid\s+var\(--alluvial-gold\)/)
      expect(aeoSummaryVue).toMatch(/background:\s*rgba\((?:201,\s*148,\s*70|var\(--alluvial-gold-rgb\)),\s*0\.05\)/)
    })

    it('supports Nocturne dark mode with adjusted background opacity and liquid glass border', () => {
      expect(aeoSummaryVue).toMatch(/\.dark\s+\.detail-aeo-summary\s*\{[\s\S]*?background:\s*rgba\((?:201,\s*148,\s*70|var\(--alluvial-gold-rgb\)),\s*0\.08\)/)
    })
  })

  describe('Tier 1 & Tier 3: SourceMark Attribution & Anti-AI-Slop Governance', () => {
    it('displays official SourceMark attribution to Ban biên tập vinhlong360', () => {
      expect(detailVue).toContain('article-sourcemark-bar')
      expect(detailVue).toMatch(/SourceMark:\s*<strong>Ban biên tập vinhlong360<\/strong>/)
    })

    it('strictly avoids unverified claims in article and sidebar per CLAUDE.md §1.7', () => {
      // CẤM: Banned claim check without attributes.verifiedAt timestamp
      const unverifiedTagPattern = new RegExp('>\\s*' + 'đã ' + 'xác minh' + '\\s*<', 'i')
      expect(detailVue).not.toMatch(unverifiedTagPattern)
    })
  })

  describe('Tier 1 & Tier 2: Anti-Synthetic Data Integrity & Graceful Collapse', () => {
    it('eliminates fabricated placeholder strings in DetailAeoSummary', () => {
      // Rejects previous synthetic fallback clichés
      expect(aeoSummaryVue).not.toContain('Buổi sáng dịu mát 7h30')
      expect(aeoSummaryVue).not.toContain('Đường nhựa ô tô vào tận nơi')
      expect(aeoSummaryVue).not.toContain('Nên xin phép trước khi chụp ảnh thợ lò gốm')
    })

    it('gracefully collapses empty AEO fields using v-if conditions', () => {
      expect(aeoSummaryVue).toMatch(/v-if="goldenHour"/)
      expect(aeoSummaryVue).toMatch(/v-if="transitInfo"/)
      expect(aeoSummaryVue).toMatch(/v-if="durationAndCost"/)
      expect(aeoSummaryVue).toMatch(/v-if="localTip"/)
    })
  })
})
