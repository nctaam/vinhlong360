import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readPage(relPath: string): string {
  return readFileSync(resolve(__dirname, '..', relPath), 'utf8')
}

describe('/tim-kiem — Smart Cultural Chips & Zero-Result Recovery (Moc 126)', () => {
  it('renders quick cultural search chips across 3 Mekong sub-regions', () => {
    const search = readPage('pages/tim-kiem.vue')
    expect(search).toContain('search-quick-culture')
    expect(search).toContain('Cù lao An Bình')
    expect(search).toContain('Lò gốm Mang Thít')
    expect(search).toContain('Bưởi Năm Roi')
    expect(search).toContain('Phà & Đò sông')
    expect(search).toContain('Chùa Khmer')
  })

  it('renders smart category shortcuts upon zero-result recovery', () => {
    const search = readPage('pages/tim-kiem.vue')
    expect(search).toContain('zero-result-hub-shortcuts')
    expect(search).toContain('Khám phá Du lịch')
    expect(search).toContain('to="/du-lich"')
    expect(search).toContain('Đặc sản & OCOP')
    expect(search).toContain('to="/san-pham"')
    expect(search).toContain('Bản đồ số thực địa')
    expect(search).toContain('to="/ban-do"')
  })

  it('strictly adheres to design tokens with zero raw hex in style blocks of tim-kiem.vue', () => {
    const src = readPage('pages/tim-kiem.vue')
    const styleMatch = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)
    const styleContent = styleMatch ? styleMatch[1] : ''
    const rawHexPattern = /(?<![&w-])#[0-9a-fA-F]{3,8}\b/g
    const matches = styleContent!.match(rawHexPattern) || []
    expect(matches).toEqual([])
  })
})
