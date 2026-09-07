import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readPage(relPath: string): string {
  return readFileSync(resolve(__dirname, '..', relPath), 'utf8')
}

describe('Community Forum, Posts & User Profiles (Moc 131)', () => {
  describe('Community Forum Hub (pages/cong-dong.vue)', () => {
    it('integrates CatalogAeoPlaque with co-creation and etiquette guidelines', () => {
      const src = readPage('pages/cong-dong.vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Diễn Đàn Đồng Sáng Tạo &amp; Lan Tỏa Văn Hóa Bản Địa')
      expect(src).toContain('Không Gian Chia Sẻ Thực Chất &amp; Khách Quan')
      expect(src).toContain('Quy Chuẩn Gắn Thẻ &amp; Xác Thực Địa Điểm')
      expect(src).toContain('Tôn Trọng Sự Thật &amp; Gìn Giữ Cảnh Quan Bản Địa')
    })

    it('includes speakable selectors in CollectionPage schema', () => {
      const src = readPage('pages/cong-dong.vue')
      expect(src).toContain("'.catalog-aeo-plaque__title'")
      expect(src).toContain("'.catalog-aeo-plaque__dek'")
    })
  })

  describe('Post Detail Hub (pages/bai-viet/[id].vue)', () => {
    it('integrates CatalogAeoPlaque for forum verification & civil discussion', () => {
      const src = readPage('pages/bai-viet/[id].vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Góc Nhìn Thực Địa &amp; Thảo Luận Văn Minh Bản Xứ')
      expect(src).toContain('Bài Viết Chia Sẻ Trải Nghiệm Thực Tế')
      expect(src).toContain('Tương Tác &amp; Hỏi Đáp Chân Thành')
      expect(src).toContain('Bảo Vệ Tính Xác Thực &amp; Tôn Trọng Bản Địa')
    })

    it('injects speakable AEO selectors into buildPostDetailSchemaGraph', () => {
      const helperSrc = readPage('composables/useSeoHelpers.ts')
      expect(helperSrc).toContain('buildPostDetailSchemaGraph')
      expect(helperSrc).toContain("'.catalog-aeo-plaque__title'")
      expect(helperSrc).toContain("'.catalog-aeo-plaque__dek'")
    })
  })

  describe('User Profile Hub (pages/nguoi-dung/[id].vue)', () => {
    it('integrates CatalogAeoPlaque with member passport highlights', () => {
      const src = readPage('pages/nguoi-dung/[id].vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Sổ Hành Trình Thành Viên &amp; Đóng Góp Bản Địa')
      expect(src).toContain('Hồ Sơ Xác Thực &amp; Dấu Ấn Đóng Góp')
      expect(src).toContain('Hệ Thống Cấp Bậc &amp; Điểm Danh Tiếng')
      expect(src).toContain('Kết Nối Du Khách &amp; Cư Dân Địa Phương')
    })

    it('injects structured ProfilePage schema with speakable specification', () => {
      const src = readPage('pages/nguoi-dung/[id].vue')
      expect(src).toContain("userProfileSchema")
      expect(src).toContain("'@type': 'ProfilePage'")
      expect(src).toContain("'@type': 'Person'")
      expect(src).toContain("'.catalog-aeo-plaque__title'")
      expect(src).toContain("'.catalog-aeo-plaque__dek'")
    })
  })

  describe('Design Token & Color Compliance', () => {
    it('has zero raw hex colors across all modified pages', () => {
      const rawHexPattern = /(?<![&w-])#[0-9a-fA-F]{3,8}\b/g
      const files = [
        'pages/cong-dong.vue',
        'pages/bai-viet/[id].vue',
        'pages/nguoi-dung/[id].vue',
      ]

      for (const f of files) {
        const src = readPage(f)
        const styleMatches = [...src.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)]
        for (const m of styleMatches) {
          const hexes = m[1].match(rawHexPattern) || []
          expect(hexes, `Found raw hex in ${f}`).toEqual([])
        }
      }
    })

    it('complies with R30.8 purpose-based radius tokens', () => {
      const legacyRadiusPattern = /var\(--radius-(xs|sm|md|lg|xl)\)/g
      const files = [
        'pages/cong-dong.vue',
        'pages/bai-viet/[id].vue',
        'pages/nguoi-dung/[id].vue',
      ]

      for (const f of files) {
        const src = readPage(f)
        const styleMatches = [...src.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)]
        for (const m of styleMatches) {
          const legacyRadii = m[1].match(legacyRadiusPattern) || []
          expect(legacyRadii, `Found legacy radius token in ${f}`).toEqual([])
        }
      }
    })
  })
})
