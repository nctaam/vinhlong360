import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readPage(relPath: string): string {
  return readFileSync(resolve(__dirname, '..', relPath), 'utf8')
}

describe('Secondary Discovery Hubs — AEO Plaque & Visual Depth (Moc 125)', () => {
  it('integrates CatalogAeoPlaque with PGI and terroir entries in san-pham.vue', () => {
    const product = readPage('pages/san-pham.vue')
    const helper = readPage('composables/useSeoHelpers.ts')
    expect(product).toContain('<CatalogAeoPlaque')
    expect(product).toContain('Chỉ dẫn địa lý & Đặc sản Vĩnh Long — Nông sản thượng hạng đất phù sa')
    expect(product).toContain('Chỉ dẫn địa lý PGI & Bảo hộ thương hiệu')
    expect(product).toContain('Bưởi Năm Roi Bình Minh & Sầu riêng Ri6 Quới Thiện')
    expect(helper).toMatch(/buildProductCatalogSchemaGraph[\s\S]*?\.catalog-aeo-plaque__title/)
    expect(helper).toMatch(/buildProductCatalogSchemaGraph[\s\S]*?\.catalog-aeo-plaque__dek/)
  })

  it('integrates CatalogAeoPlaque with riverine and homestay entries in luu-tru.vue', () => {
    const lodging = readPage('pages/luu-tru.vue')
    const helper = readPage('composables/useSeoHelpers.ts')
    expect(lodging).toContain('<CatalogAeoPlaque')
    expect(lodging).toContain('Chỉ dẫn lưu trú Vĩnh Long — Thức dậy cùng nhịp sống cù lao')
    expect(lodging).toContain('Mẹo chọn chỗ nghỉ · Thực địa miệt vườn')
    expect(lodging).toContain('Homestay nhà vườn Cù lao An Bình & Bình Hòa Phước')
    expect(helper).toMatch(/buildStayCatalogSchemaGraph[\s\S]*?\.catalog-aeo-plaque__title/)
    expect(helper).toMatch(/buildStayCatalogSchemaGraph[\s\S]*?\.catalog-aeo-plaque__dek/)
  })

  it('integrates CatalogAeoPlaque with harvest calendar entries in theo-mua.vue', () => {
    const season = readPage('pages/theo-mua.vue')
    const helper = readPage('composables/useSeoHelpers.ts')
    expect(season).toContain('<CatalogAeoPlaque')
    expect(season).toContain('Nhịp điệu mùa vụ sông nước — Lịch nông sản & con nước nổi Vĩnh Long')
    expect(season).toContain('Chu kỳ tự nhiên · Thời điểm vàng trải nghiệm')
    expect(season).toContain('Tháng 5 – 7: Đại tiệc trái cây hè chính vụ')
    expect(helper).toMatch(/buildSeasonalitySchemaGraph[\s\S]*?\.catalog-aeo-plaque__title/)
    expect(helper).toMatch(/buildSeasonalitySchemaGraph[\s\S]*?\.catalog-aeo-plaque__dek/)
  })

  it('strictly adheres to design tokens with zero raw hex in style blocks of all 3 hubs', () => {
    const pages = ['pages/san-pham.vue', 'pages/luu-tru.vue', 'pages/theo-mua.vue']
    for (const page of pages) {
      const src = readPage(page)
      const styleMatch = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)
      const styleContent = styleMatch ? styleMatch[1] : ''
      const rawHexPattern = /(?<![&w-])#[0-9a-fA-F]{3,8}\b/g
      const matches = styleContent.match(rawHexPattern) || []
      expect(matches).toEqual([])
    }
  })
})
