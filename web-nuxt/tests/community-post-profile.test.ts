import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { buildPostDetailSchemaGraph } from '../composables/useSeoHelpers'

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
    it('maintains a distraction-free post reading experience without intrusive plaques', () => {
      const src = readPage('pages/bai-viet/[id].vue')
      expect(src).not.toContain('<CatalogAeoPlaque')
      expect(src).toContain('thread-detail')
      expect(src).toContain('thread-comments')
    })

    it('injects lean speakable selectors into buildPostDetailSchemaGraph', () => {
      const graph = buildPostDetailSchemaGraph({ post: { id: '123', display_name: 'Test Post', content: 'Sample' } })
      const webpage = graph['@graph'].find((n: any) => n['@type'] === 'WebPage')
      expect(webpage.speakable.cssSelector).toContain('.thread-detail')
      expect(webpage.speakable.cssSelector).toContain('h1')
      expect(webpage.speakable.cssSelector).toContain('.thread-comments')
      expect(webpage.speakable.cssSelector).not.toContain('.catalog-aeo-plaque__title')
    })
  })

  describe('User Profile Hub (pages/nguoi-dung/[id].vue)', () => {
    it('keeps personal profile view focused without generic catalog plaques', () => {
      const src = readPage('pages/nguoi-dung/[id].vue')
      expect(src).not.toContain('<CatalogAeoPlaque')
      expect(src).toContain('user-profile reveal')
      expect(src).toContain('profile-info')
    })

    it('injects structured ProfilePage schema with accurate profile speakable specification', () => {
      const src = readPage('pages/nguoi-dung/[id].vue')
      expect(src).toContain('userProfileSchema')
      expect(src).toContain("'@type': 'ProfilePage'")
      expect(src).toContain("'@type': 'Person'")
      expect(src).toContain("'.profile-name'")
      expect(src).toContain("'.profile-bio'")
      expect(src).not.toContain("'.catalog-aeo-plaque__title'")
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
