import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readPage(relPath: string): string {
  return readFileSync(resolve(__dirname, '..', relPath), 'utf8')
}

describe('Guide, Member Guide, About, and Contact Hubs (Moc 132)', () => {
  describe('Contact Page (pages/lien-he.vue)', () => {
    it('integrates CatalogAeoPlaque for visitor support & editorial commitments', () => {
      const src = readPage('pages/lien-he.vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Cam kết tiếp nhận phản ánh & hỗ trợ du khách Vĩnh Long')
      expect(src).toContain('Thời gian phản hồi cam kết')
      expect(src).toContain('Kênh hỗ trợ khẩn cấp & thực địa')
      expect(src).toContain('Minh bạch & độc lập biên tập')
    })

    it('injects speakable AEO selectors into buildContactPageSchemaGraph', () => {
      const helperSrc = readPage('composables/useSeoHelpers.ts')
      expect(helperSrc).toContain('buildContactPageSchemaGraph')
      expect(helperSrc).toMatch(/buildContactPageSchemaGraph[\s\S]*?'.catalog-aeo-plaque__title'[\s\S]*?'.catalog-aeo-plaque__dek'/)
    })
  })

  describe('About Page (pages/gioi-thieu.vue)', () => {
    it('integrates CatalogAeoPlaque for non-commercial mission & field verification', () => {
      const src = readPage('pages/gioi-thieu.vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Tôn chỉ số hóa di sản & kiến thức bản địa Vĩnh Long')
      expect(src).toContain('Phi thương mại & Công tâm')
      expect(src).toContain('Dữ liệu đa nguồn & Kiểm chứng thực địa')
      expect(src).toContain('Đồng sáng tạo cùng cư dân địa hạt')
    })

    it('injects speakable AEO selectors into buildAboutPageSchemaGraph', () => {
      const helperSrc = readPage('composables/useSeoHelpers.ts')
      expect(helperSrc).toContain('buildAboutPageSchemaGraph')
      expect(helperSrc).toMatch(/buildAboutPageSchemaGraph[\s\S]*?'.catalog-aeo-plaque__title'[\s\S]*?'.catalog-aeo-plaque__dek'/)
    })
  })

  describe('User Guide Page (pages/huong-dan.vue)', () => {
    it('integrates CatalogAeoPlaque for system guide & navigation answers', () => {
      const src = readPage('pages/huong-dan.vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Hỏi đáp cốt lõi khi trải nghiệm nền tảng số vinhlong360')
      expect(src).toContain('Khám phá & Lưu điểm không cần đăng ký')
      expect(src).toContain('Công cụ lập lộ trình thông minh')
      expect(src).toContain('Đóng góp & Nâng hạng thành viên')
    })

    it('injects speakable AEO selectors into buildGuideSchemaGraph', () => {
      const helperSrc = readPage('composables/useSeoHelpers.ts')
      expect(helperSrc).toContain('buildGuideSchemaGraph')
      expect(helperSrc).toMatch(/buildGuideSchemaGraph[\s\S]*?'.catalog-aeo-plaque__title'[\s\S]*?'.catalog-aeo-plaque__dek'/)
    })
  })

  describe('Member Reputation Guide Page (pages/huong-dan-thanh-vien.vue)', () => {
    it('integrates CatalogAeoPlaque for reputation formulas & honor levels', () => {
      const src = readPage('pages/huong-dan-thanh-vien.vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Hỏi đáp danh tiếng & cơ chế vinh danh thành viên vinhlong360')
      expect(src).toContain('Hệ thống 4 cấp bậc danh dự')
      expect(src).toContain('Chống lạm phát & Giới hạn trần điểm')
      expect(src).toContain('Huy hiệu thành tích tự động')
    })

    it('injects speakable AEO selectors into buildMemberGuideSchemaGraph', () => {
      const helperSrc = readPage('composables/useSeoHelpers.ts')
      expect(helperSrc).toContain('buildMemberGuideSchemaGraph')
      expect(helperSrc).toMatch(/buildMemberGuideSchemaGraph[\s\S]*?'.catalog-aeo-plaque__title'[\s\S]*?'.catalog-aeo-plaque__dek'/)
    })
  })

  describe('Design System & Tone of Voice Guardrails', () => {
    const pages = [
      'pages/lien-he.vue',
      'pages/gioi-thieu.vue',
      'pages/huong-dan.vue',
      'pages/huong-dan-thanh-vien.vue',
    ]

    for (const page of pages) {
      it(`${page} respects purpose-based radius and has no raw hex debt`, () => {
        const src = readPage(page)
        const styleMatch = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)
        if (styleMatch) {
          const style = styleMatch[1]
          expect(style).not.toMatch(/--radius-(?:xs|sm|md|lg|xl)\b/)
        }
      })
    }
  })
})
