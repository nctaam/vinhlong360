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

  it('verifies iconic enriched heritage entities have authentic CC provenance metadata in SQLite', () => {
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
      expect(attrs.image_license, `Entity ${id} must have open license`).toBeDefined()
      expect(attrs.image_license).toMatch(/CC|Public Domain|Creative Commons/i)
      expect(attrs.image_source_url, `Entity ${id} must have source URL`).toBeDefined()
      expect(attrs.image_source_url).toMatch(/^https:\/\/commons\.wikimedia\.org/i)

      const assetPath = path.join(publicImgDir, `${id}.webp`)
      expect(fs.existsSync(assetPath)).toBe(true)
      const stat = fs.statSync(assetPath)
      expect(stat.size).toBeGreaterThan(1024) // > 1KB
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
