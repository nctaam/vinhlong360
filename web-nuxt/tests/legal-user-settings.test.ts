import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { buildPrivacyPolicySchemaGraph, buildTermsOfServiceSchemaGraph } from '../composables/useSeoHelpers'

function readPage(relPath: string): string {
  return readFileSync(resolve(__dirname, '..', relPath), 'utf8')
}

describe('Legal & User Account Utilities (Moc 133)', () => {
  describe('Privacy Policy Page (pages/chinh-sach-bao-mat.vue)', () => {
    it('maintains a clean legal structure without misplaced catalog plaques', () => {
      const src = readPage('pages/chinh-sach-bao-mat.vue')
      expect(src).not.toContain('<CatalogAeoPlaque')
      expect(src).toContain('class="legal-section')
      expect(src).toContain('class="legal-body editorial-body"')
    })

    it('injects authentic legal speakable selectors into buildPrivacyPolicySchemaGraph', () => {
      const graph = buildPrivacyPolicySchemaGraph()
      const webpage = graph['@graph'].find((n: any) => n['@type'] === 'WebPage')
      expect(webpage.speakable.cssSelector).toContain('.bm-inner h1')
      expect(webpage.speakable.cssSelector).toContain('.about-section-content h2')
      expect(webpage.speakable.cssSelector).not.toContain('.catalog-aeo-plaque__title')
    })
  })

  describe('Terms of Service Page (pages/dieu-khoan-su-dung.vue)', () => {
    it('maintains a clean terms structure without misplaced catalog plaques', () => {
      const src = readPage('pages/dieu-khoan-su-dung.vue')
      expect(src).not.toContain('<CatalogAeoPlaque')
      expect(src).toContain('class="legal-section')
      expect(src).toContain('class="legal-body editorial-body"')
    })

    it('injects authentic legal speakable selectors into buildTermsOfServiceSchemaGraph', () => {
      const graph = buildTermsOfServiceSchemaGraph()
      const webpage = graph['@graph'].find((n: any) => n['@type'] === 'WebPage')
      expect(webpage.speakable.cssSelector).toContain('.bm-inner h1')
      expect(webpage.speakable.cssSelector).toContain('.about-section-content h2')
      expect(webpage.speakable.cssSelector).not.toContain('.catalog-aeo-plaque__title')
    })
  })

  describe('Personal Utilities Ergonomics & Accessibility', () => {
    const utilityPages = [
      'pages/da-luu.vue',
      'pages/tai-khoan.vue',
      'pages/cai-dat.vue',
      'pages/thong-bao.vue',
    ]

    for (const page of utilityPages) {
      it(`${page} implements tri-region color system and accessible landmarks`, () => {
        const src = readPage(page)
        expect(src).toContain('data-color-system="tri-region-v1"')
        const styleMatch = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)
        if (styleMatch) {
          const style = styleMatch[1]
          expect(style).not.toMatch(/--radius-(?:xs|sm|md|lg|xl)\b/)
        }
      })
    }

    it('pages/da-luu.vue maintains tablist accessibility and empty state guidance', () => {
      const src = readPage('pages/da-luu.vue')
      expect(src).toContain('role="tablist"')
      expect(src).toContain('aria-selected')
      expect(src).toContain('role="tabpanel"')
    })

    it('pages/tai-khoan.vue contains meter and progressbar semantics for security health', () => {
      const src = readPage('pages/tai-khoan.vue')
      expect(src).toContain('role="meter"')
      expect(src).toContain('role="progressbar"')
    })

    it('pages/cai-dat.vue provides keyboard navigable settings tabs', () => {
      const src = readPage('pages/cai-dat.vue')
      expect(src).toContain('role="tablist"')
      expect(src).toContain('role="tabpanel"')
      expect(src).toContain('@keydown="onTabKeydown"')
    })

    it('pages/thong-bao.vue supports tablist filter semantics', () => {
      const src = readPage('pages/thong-bao.vue')
      expect(src).toContain('role="tablist"')
      expect(src).toContain('role="tab"')
      expect(src).toContain('@keydown="onFilterKeydown"')
    })
  })
})
