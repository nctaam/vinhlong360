import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { DatabaseSync } from 'node:sqlite'
import path from 'node:path'
import fs from 'node:fs'
import { generateCategoryPlaceholder } from '../web-nuxt/composables/useCategoryPlaceholder'

const repoRoot = fs.existsSync(path.resolve('agent/data/vinhlong360.db'))
  ? path.resolve('.')
  : path.resolve('..')
const dbPath = path.join(repoRoot, 'agent/data/vinhlong360.db')
const dataJsonPath = path.join(repoRoot, 'web/data.json')
const publicImgDir = path.join(repoRoot, 'web-nuxt/public/img/entities')

let db: DatabaseSync

beforeAll(() => {
  expect(fs.existsSync(dbPath), `Database file must exist at ${dbPath}`).toBe(true)
  db = new DatabaseSync(dbPath, { readOnly: true })
})

afterAll(() => {
  if (db) {
    db.close()
  }
})

describe('Image Governance & Visual Asset Suite (100% Full Coverage)', () => {
  it('verifies 100% of entities in SQLite have valid images array and 0 broken local references', () => {
    const allEntities = db.prepare(`SELECT id, images FROM entities`).all() as { id: string; images: string }[]
    
    expect(allEntities.length).toBe(1772)

    for (const row of allEntities) {
      expect(row.images, `Entity ${row.id} must have non-empty images`).toBeDefined()
      expect(row.images).not.toBe('')
      expect(row.images).not.toBe('[]')

      let imageList: string[] = []
      try {
        imageList = JSON.parse(row.images)
      } catch (err) {
        throw new Error(`Entity ${row.id} has invalid JSON in images: ${row.images}`)
      }

      expect(imageList.length, `Entity ${row.id} must have at least 1 image`).toBeGreaterThan(0)

      for (const img of imageList) {
        // Must not contain mock/dummy URLs
        expect(img).not.toContain('example.test')
        expect(img).not.toContain('localhost')

        if (img.startsWith('/img/entities/')) {
          const filename = path.basename(img)
          const physicalPath = path.join(publicImgDir, filename)
          expect(fs.existsSync(physicalPath), `Local image ${img} referenced by entity ${row.id} must exist at ${physicalPath}`).toBe(true)
          
          const stat = fs.statSync(physicalPath)
          expect(stat.size, `Image ${filename} should be > 500 bytes`).toBeGreaterThan(500)
        }
      }
    }
  })

  it('verifies 100% of entities in web/data.json have valid images array matching SQLite', () => {
    expect(fs.existsSync(dataJsonPath)).toBe(true)
    const raw = fs.readFileSync(dataJsonPath, 'utf-8')
    const data = JSON.parse(raw)
    const entities = data.entities || []

    expect(entities.length).toBe(1772)

    const dummyEntities = entities.filter((e: any) => {
      const imgs = Array.isArray(e.images) ? e.images : []
      return imgs.some((img: string) => img.includes('example.test') || img.includes('localhost'))
    })
    expect(dummyEntities.length).toBe(0)

    const missingImages = entities.filter((e: any) => !Array.isArray(e.images) || e.images.length === 0)
    expect(missingImages.length).toBe(0)
  })

  it('verifies iconic enriched heritage entities have authentic provenance metadata in SQLite', () => {
    const enrichedIconicIds = [
      'khu-di-tich-ao-ba-om',
      'cau-my-thuan',
      'van-thanh-mieu',
      'chua-hang-kompong-chray',
      'con-phung-con-ong-dao-dua',
      'den-tho-bac-ho-tra-vinh',
      'chua-ong-met-botum-vong-sa-som-rong',
      'lo-gach-mang-thit',
      'nha-tho-cai-mon',
      'sau-rieng-cai-mon',
      'chua-nodol-tra-vinh',
    ]

    for (const id of enrichedIconicIds) {
      const row = db.prepare(`SELECT id, images, attributes FROM entities WHERE id = ?`).get(id) as { id: string; images: string; attributes: string }
      expect(row, `Entity ${id} must exist in DB`).toBeDefined()

      const images = JSON.parse(row.images)
      expect(images.length, `Entity ${id} must have at least 1 image`).toBeGreaterThan(0)
      expect(images[0]).toBe(`/img/entities/${id}.webp`)

      const attrs = JSON.parse(row.attributes || '{}')
      expect(attrs.image_author, `Entity ${id} must have author`).toBeDefined()
      expect(attrs.image_author.length).toBeGreaterThan(1)
      expect(attrs.image_license, `Entity ${id} must have license`).toBeDefined()
      expect(attrs.image_license).toMatch(/CC|Public Domain|Creative Commons|Tư liệu|Báo|Cổng TTĐT/i)
      const hasSource = Boolean(attrs.image_source || attrs.image_source_url)
      expect(hasSource, `Entity ${id} must have image_source or image_source_url`).toBe(true)

      const assetPath = path.join(publicImgDir, `${id}.webp`)
      expect(fs.existsSync(assetPath)).toBe(true)
      const stat = fs.statSync(assetPath)
      expect(stat.size).toBeGreaterThan(1024) // > 1KB
    }
  })

  it('verifies documentary journalistic photos have local WebP and authentic author/source attribution', () => {
    const documentaryIds = [
      // 16 Pilot Cultural / Terroir Entities
      'van-thanh-mieu',
      'dinh-long-ho',
      'chua-tien-chau-tien-chau-tu',
      'lo-gach-mang-thit',
      'khu-luu-niem-thu-tuong-vo-van-kiet',
      'khu-luu-niem-tran-dai-nghia-vinh-long',
      'chua-phat-ngoc-xa-loi',
      'khu-di-tich-ao-ba-om',
      'chua-ang-angkorajaborey',
      'den-tho-bac-ho-tra-vinh',
      'chua-hang-kompong-chray',
      'lang-nghe-banh-trang-my-long',
      'lang-nghe-banh-phong-son-doc',
      'con-phung-con-ong-dao-dua',
      'nha-tho-cai-mon',
      'lang-nghe-det-chieu-ca-hon',
      // 25 Culinary Heritage & Craft Entities (Batch 2)
      'banh-canh-ben-co',
      'banh-canh-bot-xat-ben-tre',
      'banh-tet-tra-cuon-co-huong',
      'bun-suong-tra-vinh',
      'chao-am-tra-vinh',
      'ca-chay-tra-on-rim-kho',
      'chuoi-dap-nuoc-cot-dua',
      'banh-xeo-oc-gao-con-phu-da',
      'hu-tieu-pate-ben-tre',
      'tau-hu-ky-my-hoa-chien-gion',
      'bun-nuoc-leo-tra-vinh',
      'bun-mam-vinh-long',
      'banh-dua-giong-luong',
      'banh-ray-khmer-la-dua',
      'khoai-lang-mam-song-cuon-la-cach',
      'com-hap-trai-dua',
      'che-chuoi-nuong',
      'ca-chay-song-hau',
      'lang-keo-dua-mo-cay',
      'lang-nghe-banh-tet-tra-cuon',
      'lang-hoa-kieng-cai-mon-cho-lach',
      'lang-det-chieu-cu-lao-dai',
      'banh-trang-cu-lao-may-lang-nghe-banh-trang',
      'lang-det-chieu-ca-hom-ham-tan',
      'hop-tac-xa-buoi-nam-roi-my-hoa',
      // 30 Heritage Communal Houses, Ancient Pagodas & Memorials (Batch 3)
      'dinh-long-thanh-long-thanh-vo-mieu',
      'chua-ong-that-phu-mieu',
      'chua-ba-thien-hau-vinh-long',
      'chua-shanghamangala-khmer-vung-liem',
      'dinh-tan-hoa',
      'dinh-tan-giai-vinh-long',
      'khu-luu-niem-thu-tuong-chinh-phu-vo-van-kiet',
      'chua-giac-thien-vinh-long',
      'dinh-cai-von',
      'chua-khmer-phu-ly',
      'chua-ang',
      'ao-ba-om-ao-vuong',
      'chua-hang-wat-kompong-chray',
      'chua-kompong-ong-met',
      'chua-co-chua-nodol-chua-phno-don',
      'chua-vam-ray',
      'phuoc-minh-cung-chua-ong-tra-vinh',
      'chua-giac-linh-tra-vinh',
      'dinh-long-duc-tra-vinh',
      'chua-o-mich-hung-hoa',
      'dinh-phu-le-ben-tre',
      'dinh-binh-hoa-ben-tre',
      'dinh-tan-thach',
      'dinh-dai-dien',
      'dinh-ran-dinh-thuy',
      'chua-van-phuoc-binh-dai',
      'chua-tuyen-linh-ben-tre',
      'chua-hoi-ton-co-tu',
      'khu-luu-niem-nguyen-dinh-chieu',
      'khu-luu-niem-nu-tuong-nguyen-thi-dinh',
    ]

    for (const id of documentaryIds) {
      const row = db.prepare(`SELECT id, images, attributes FROM entities WHERE id = ?`).get(id) as { id: string; images: string; attributes: string }
      expect(row, `Entity ${id} must exist in DB`).toBeDefined()

      const images = JSON.parse(row.images)
      expect(images[0]).toBe(`/img/entities/${id}.webp`)

      const attrs = JSON.parse(row.attributes || '{}')
      expect(attrs.image_author, `Entity ${id} must have author`).toBeDefined()
      expect(attrs.image_author.length).toBeGreaterThan(1)
      expect(attrs.image_source, `Entity ${id} must have publication source`).toBeDefined()
      expect(attrs.image_source.length).toBeGreaterThan(1)
      expect(attrs.image_type).toBe('documentary')
      expect(attrs.is_verified_photo).toBe(true)

      const assetPath = path.join(publicImgDir, `${id}.webp`)
      expect(fs.existsSync(assetPath), `WebP for ${id} must exist locally`).toBe(true)
      const stat = fs.statSync(assetPath)
      expect(stat.size, `WebP for ${id} must be > 1KB`).toBeGreaterThan(1024)
    }
  })

  it('verifies artisanal terroir visual engine generates valid SVG with river waves and watermark', () => {
    const categories = ['attraction', 'history', 'craft', 'dish', 'nature', 'itinerary']
    
    for (const cat of categories) {
      const bgValue = generateCategoryPlaceholder(`item-${cat}`, cat)
      expect(bgValue.startsWith("url('data:image/svg+xml,")).toBe(true)
      expect(bgValue.endsWith("')")).toBe(true)

      const encoded = bgValue.slice("url('data:image/svg+xml,".length, -2)
      const svg = decodeURIComponent(encoded)

      // Must be valid SVG structure
      expect(svg).toContain('<svg')
      expect(svg).toContain('xmlns="http://www.w3.org/2000/svg"')
      expect(svg).toContain('viewBox="0 0 400 240"')
      expect(svg).toContain('</svg>')

      // Must include Alluvial Mekong River wave paths
      expect(svg).toContain('M0,')
      expect(svg).toContain('L400,240 L0,240 Z')

      // Must include Cultural Typography Watermark
      expect(svg).toContain('BẢN SẮC NAM BỘ')
    }
  })

  it('verifies category-specific terroir motifs are rendered in SVG', () => {
    // Craft category should render Mang Thit kiln dome outline (stroke-dasharray="4 3")
    const craftBg = generateCategoryPlaceholder('craft-test', 'craft')
    const craftSvg = decodeURIComponent(craftBg.slice("url('data:image/svg+xml,".length, -2))
    expect(craftSvg).toContain('stroke-dasharray="4 3"')

    // Attraction / history should render heritage pagoda eave arc
    const attractionBg = generateCategoryPlaceholder('attraction-test', 'attraction')
    const attractionSvg = decodeURIComponent(attractionBg.slice("url('data:image/svg+xml,".length, -2))
    expect(attractionSvg).toContain('C190,68 270,68 350,40')

    // Itinerary should render exploration trail waypoint curve
    const itineraryBg = generateCategoryPlaceholder('itinerary-test', 'itinerary')
    const itinerarySvg = decodeURIComponent(itineraryBg.slice("url('data:image/svg+xml,".length, -2))
    expect(itinerarySvg).toContain('stroke-dasharray="5 4"')
  })
})
