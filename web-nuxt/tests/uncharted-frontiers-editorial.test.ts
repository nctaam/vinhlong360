import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { guideSections, guideTroubleshooting } from '../utils/guideContent'

describe('Uncharted Frontiers — Editorial Di sản Cửu Long', () => {
  it('0 emoji entities trong toàn bộ các trang Quản trị (pages/admin/*)', () => {
    const adminDir = path.resolve(__dirname, '../pages/admin')
    const files = fs.readdirSync(adminDir).filter(f => f.endsWith('.vue'))
    expect(files.length).toBeGreaterThanOrEqual(14)

    const entityRegex = /&#(?:12\d{4}|9\d{3}|8\d{3}|x[0-9a-fA-F]+);/g
    const violations: Array<{ file: string; match: string }> = []

    for (const file of files) {
      const content = fs.readFileSync(path.join(adminDir, file), 'utf-8')
      const matches = content.match(entityRegex)
      if (matches) {
        for (const m of matches) {
          violations.push({ file, match: m })
        }
      }
    }

    expect(violations).toEqual([])
  })

  it('0 raw emojis hoặc ký tự misc symbol trong utils/guideContent.ts', () => {
    const filePath = path.resolve(__dirname, '../utils/guideContent.ts')
    const text = fs.readFileSync(filePath, 'utf-8')

    // High codepoints (Unicode surrogate / SMP emojis)
    const emojiRegex = /[\uD800-\uDBFF][\uDC00-\uDFFF]/g
    const emojiMatches = text.match(emojiRegex) || []
    expect(emojiMatches).toEqual([])

    // Misc symbols (0x2600 - 0x27BF, including heart, cross, etc.)
    const miscSymbols = [...text].filter(c => {
      const code = c.charCodeAt(0)
      return code >= 0x2600 && code <= 0x27BF
    })
    expect(miscSymbols).toEqual([])
  })

  it('Mọi icon trong guideSections và guideTroubleshooting đều là chuỗi định danh vector', () => {
    for (const s of guideSections) {
      expect(s.icon).toMatch(/^[a-z0-9-]+$/)
      for (const t of s.topics) {
        expect(t.icon).toMatch(/^[a-z0-9-]+$/)
      }
    }

    for (const item of guideTroubleshooting) {
      expect(item.icon).toMatch(/^[a-z0-9-]+$/)
    }
  })

  it('pages/huong-dan.vue không chứa emoji thô và sử dụng IconLine', () => {
    const filePath = path.resolve(__dirname, '../pages/huong-dan.vue')
    const text = fs.readFileSync(filePath, 'utf-8')

    const emojiRegex = /[\uD800-\uDBFF][\uDC00-\uDFFF]/g
    const emojiMatches = text.match(emojiRegex) || []
    expect(emojiMatches).toEqual([])

    expect(text).toContain('<IconLine name="compass" class="gs-icon"')
    expect(text).toContain('<IconLine name="settings" class="gs-icon"')
    expect(text).toContain('<IconLine :name="s.icon"')
    expect(text).toContain('<IconLine :name="t.icon"')
  })

  it('pages/xa-phuong/[id].vue tích hợp TufteSidenote và VernacularGlyph', () => {
    const filePath = path.resolve(__dirname, '../pages/xa-phuong/[id].vue')
    const text = fs.readFileSync(filePath, 'utf-8')

    expect(text).toContain('TufteSidenote')
    expect(text).toContain('VernacularGlyph')
    expect(text).toContain('terroirGlyphName')
    expect(text).toContain('wardAcademicMarginalia')
    expect(text).toContain('<TufteSidenote')
    expect(text).toContain('<VernacularGlyph')
  })
})
