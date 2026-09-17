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
      // 36 Homestays, Farmstays & Eco-Resorts across Tam Vùng (Batch 4)
      'homestay-ut-trinh',
      'phuong-thao-homestay',
      'nam-thanh-homestay',
      'ut-thuy-homestay',
      'ngoc-phuong-homestay',
      'vinh-sang-resort',
      'mekong-pottery-homestay',
      'somo-farm-cuu-long',
      'riverside-park-eco-resort',
      'homestay-bay-thoi',
      'homestay-cu-lao-may',
      'diem-du-lich-nha-dua-cocohome',
      'forever-green-resort',
      'homestay-nam-ham-luong',
      'homestay-dua-ben-tre',
      'homestay-lang-be',
      'homestay-nguoi-giu-rung',
      'mango-home-ben-tre',
      'mekong-home',
      'maison-du-pays-de-ben-tre',
      'nhon-thanh-homestay',
      'rooster-mekong-resort',
      'farmstay-sinh-thai-nguyen-gia',
      'khach-san-ham-luong',
      'con-chim-homestay',
      'homestay-bep-nam-bo-xua-con-chim',
      'homestay-tu-pha-con-chim',
      'suonsia-homestay',
      'mekong-garden-homestay',
      'homestay-sokfram',
      'homestay-khmer-tra-vinh',
      'khu-du-lich-bien-ba-dong',
      'duyen-hai-homestay',
      'le-ngan-homestay',
      'nha-nghi-nha-co-dai-an',
      'khach-san-hai-duong-i',
      // 36 OCOP 3-5 Star Products & Terroir Specialties (Batch 5)
      'buoi-nam-roi-binh-minh',
      'cam-sanh-tam-binh',
      'khoai-lang-binh-tan',
      'sau-rieng-ri6',
      'gom-do-mang-thit',
      'banh-trang-nem-cu-lao-may',
      'nhan-xuong-com-vang',
      'chom-chom-binh-hoa-phuoc-rambutan',
      'xoai-cat-num-vung-liem',
      'chao-dua-thuan-duyen-tam-binh',
      'cuu-long-my-tuu-ruou-ocop-mang-thit',
      'sau-rieng-say-thang-hoa-sau-ri',
      'buoi-da-xanh-ben-tre',
      'keo-dua-ben-tre',
      'ruou-phu-le-ba-tri',
      'dua-xiem-xanh',
      'ngheu-thanh-hai',
      'cua-bien-thanh-phu',
      'sau-rieng-cai-mon',
      'chom-chom-cho-lach',
      'mut-dua-non',
      'tinh-dau-dua',
      'tranh-dua-cocohand',
      'ruou-dua-ben-tre',
      'dua-sap-cau-ke',
      'mat-hoa-dua-va-duong-hoa-dua-tra-vinh-ocop-5-sao',
      'vicosap-keo-dua-sap-ocop-5-sao',
      'cha-hoa-nam-thuy',
      'tom-kho-vinh-kim',
      'nuoc-mam-ruoi-long-vinh',
      'banh-tet-tra-cuon',
      'chuoi-ta-qua',
      'chu-u-ba-dong',
      'ruou-quach-cau-ngang',
      'mam-bo-hoc-tra-vinh',
      'tom-kho-cham-mam-chua-ngot-duyen-hai',
      // 36 Cultural Luminaries, Historical Figures & Master Artisans (Batch 6)
      'thoai-ngoc-hau',
      'phan-thanh-gian',
      'vo-van-kiet',
      'tran-dai-nghia',
      'tran-dai-nghia-pham-quang-le',
      'pham-hung',
      'pham-hung-pham-van-thien',
      'nguyen-thong',
      'tong-huu-dinh',
      'tran-quang-quon',
      'nghe-nhan-chau-xuong',
      'nghe-nhan-nguyen-thi-thoi',
      'ut-tra-on',
      'le-thuy',
      'tong-phuoc-hiep',
      'chau-van-sanh-cong-tu-loi',
      'nguyen-dinh-chieu',
      'nguyen-thi-dinh',
      'suong-nguyet-anh',
      'nguyen-ngoc-thang',
      'dong-van-cong',
      'huynh-ngoc-khiem-huong-liem',
      'truong-duy-toan',
      'thanh-ton',
      'ba-du',
      'thanh-huong',
      'nguyen-van-ton-thach-duong',
      'tuong-quan-nguyen-van-ton',
      'vien-chau-huynh-tri-ba',
      'nguyen-thi-ut',
      'nguyen-thien-thanh',
      'thach-boi',
      'thach-oai',
      'thach-sok-xane',
      'thanh-loan',
      'truong-xuan',
      // 25 Festival & Cultural Event Entities (Batch 7)
      'le-hoi-ok-om-bok',
      'le-hoi-chol-chnam-thmay-tai-chua-ky-son',
      'le-hoi-chol-chnam-thmay-va-sen-dolta',
      'sen-dolta',
      'le-hoi-dom-long-neak-ta',
      'hoi-thi-ghe-ngo-mo-rong-tinh-tra-vinh-dua-ghe-ngo-truyen-thong-tra-vinh',
      'tuan-le-van-hoa-du-lich-gan-voi-le-hoi-ok-om-bok',
      'le-hoi-nghinh-ong-duyen-hai',
      'le-hoi-nghinh-ong-binh-thang',
      'le-hoi-cung-bien-my-long',
      'le-cung-bien-dong-cao',
      'le-hoi-nghinh-ong-lang-con-tau',
      'le-hoi-ky-yen-dinh-phu-le',
      'le-hoi-ky-yen',
      'le-hoi-ky-yen-ha-dien-dinh-tan-giai',
      'lang-ong-tien-quan-thong-che-dieu-bat-tuong-quan-nguyen-van-',
      'le-hoi-van-thanh-mieu',
      'le-via-quoc-cong-tong-phuoc-hiep',
      'le-gio-phan-thanh-gian-tai-van-thanh-mieu',
      'le-gio-nguyen-dinh-chieu',
      'festival-dua-ben-tre',
      'festival-dua-sap-cau-ke-tra-vinh',
      'festival-gach-gom-do-kinh-te-xanh-tinh-vinh-long-vinh-long',
      'ngay-hoi-van-hoa-the-thao-va-du-lich-huyen-cho-lach-ben-tre',
      'ngay-hoi-banh-dan-gian-nam-bo-ket-hop-hoi-cho-ocop-vinh-long-vinh-long',
      // 25 Islands, Revolutionary Relics & Museums across Tam Vùng (Batch 8)
      'can-cu-cach-mang-cai-ngang-vinh-long',
      'di-tich-can-cu-khu-uy-sai-gon-gia-dinh',
      'di-tich-duong-ho-chi-minh-tren-bien-thanh-phu',
      'khu-di-tich-can-cu-tinh-uy-tra-vinh',
      'cau-my-thuan',
      'bao-tang-vinh-long',
      'bao-tang-ben-tre',
      'bao-tang-van-hoa-dan-toc-khmer-tra-vinh',
      'mo-va-khu-luu-niem-nha-giao-vo-truong-toan',
      'cho-noi-tra-on-dc',
      'cho-noi-dua-song-thom-mo-cay',
      'nha-tho-chinh-toa-vinh-long',
      'nha-tho-cai-mon-cho-lach',
      'cu-lao-dai-cu-lao-thanh-binh-quoi-thien',
      'cu-lao-my-hoa',
      'con-chim',
      'con-tan-qui',
      'con-oc-hung-phong',
      'con-quy-song-tien-chau-thanh-ben-tre',
      'con-tam-hiep-dao-tam-hiep',
      'bai-bien-con-bung-thanh-hai',
      'bai-bien-mo-o-truong-long-hoa-tra-vinh',
      'rung-duoc-long-khanh',
      'rung-ngap-man-phong-ho-binh-dai-ben-tre',
      'canh-dong-muoi-bao-thanh',
      // 35 Cultural Attractions, Ancient Pagodas & Historical Relics (Batch 9)
      'can-cu-khu-uy-sai-gon-gia-dinh-tai-tan-phu-tay',
      'can-cu-tinh-uy-ben-tre-rung-la-thanh-phu',
      'cang-thi-ba-vat-di-chi-khao-co',
      'bung-lac-dia',
      'ben-tiep-nhan-vu-khi-con-tau',
      'chua-ba-thien-hau-tra-vinh',
      'chua-ong-vinh-long',
      'chua-luong-xuyen',
      'chua-ky-son-khmer-loan-my',
      'chua-hoi-tong-ben-tre',
      'chua-khmer-vinh-long',
      'chua-bang-trau-song-loc',
      'chua-can-tho-ngu-lac',
      'chua-long-quang-chua-dua',
      'chua-o-mich-ratanadiparamkoskeo',
      'chua-phno-don-chua-giong-lon',
      'chua-phno-om-pung-chua-long-truong',
      'chua-kompong-tung-hung-my',
      'cay-da-cua-huu',
      'dinh-an-hoi',
      'dinh-tan-ngai',
      'dinh-tien-thuy',
      'dinh-hoa-ninh',
      'dinh-hau-thanh',
      'dinh-lang-thien-my',
      'dinh-loc-thuan',
      'dinh-long-duc',
      'dinh-binh-hoa-giong-trom',
      'dinh-vang-quoi',
      'dinh-vinh-xuan',
      'bia-chien-thang-loc-thuan',
      'bia-chien-thang-thanh-phuoc',
      'di-san-duong-dai-mang-thit',
      'bao-tang-tinh-vinh-long',
      'dinh-mieu-con-trung',
    ]

    expect(documentaryIds.length).toBe(264)

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
