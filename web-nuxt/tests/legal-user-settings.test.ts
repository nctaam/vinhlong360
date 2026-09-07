import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readPage(relPath: string): string {
  return readFileSync(resolve(__dirname, '..', relPath), 'utf8')
}

describe('Legal & User Account Utilities (Moc 133)', () => {
  describe('Privacy Policy Page (pages/chinh-sach-bao-mat.vue)', () => {
    it('integrates CatalogAeoPlaque for privacy guarantees & data rights', () => {
      const src = readPage('pages/chinh-sach-bao-mat.vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Cam kết bảo vệ dữ liệu cá nhân & quyền kiểm soát của du khách')
      expect(src).toContain('Thu thập tối thiểu & Đúng mục đích')
      expect(src).toContain('Quyền trích xuất & Xóa dữ liệu hoàn toàn')
      expect(src).toContain('Kiểm soát cookie & Lưu trữ an toàn')
    })

    it('injects speakable AEO selectors into buildPrivacyPolicySchemaGraph', () => {
      const helperSrc = readPage('composables/useSeoHelpers.ts')
      expect(helperSrc).toContain('buildPrivacyPolicySchemaGraph')
      expect(helperSrc).toMatch(/buildPrivacyPolicySchemaGraph[\s\S]*?'.catalog-aeo-plaque__title'[\s\S]*?'.catalog-aeo-plaque__dek'/)
    })
  })

  describe('Terms of Service Page (pages/dieu-khoan-su-dung.vue)', () => {
    it('integrates CatalogAeoPlaque for community etiquette & content ownership', () => {
      const src = readPage('pages/dieu-khoan-su-dung.vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Quy tắc ứng xử & bản quyền thông tin trên vinhlong360')
      expect(src).toContain('Trải nghiệm chân thực & Tôn trọng địa phương')
      expect(src).toContain('Bản quyền tri thức & Cơ sở dữ liệu')
      expect(src).toContain('Cơ chế báo cáo & Kiểm duyệt công minh')
    })

    it('injects speakable AEO selectors into buildTermsOfServiceSchemaGraph', () => {
      const helperSrc = readPage('composables/useSeoHelpers.ts')
      expect(helperSrc).toContain('buildTermsOfServiceSchemaGraph')
      expect(helperSrc).toMatch(/buildTermsOfServiceSchemaGraph[\s\S]*?'.catalog-aeo-plaque__title'[\s\S]*?'.catalog-aeo-plaque__dek'/)
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
