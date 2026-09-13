import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { DatabaseSync } from 'node:sqlite'
import path from 'node:path'
import fs from 'node:fs'

const repoRoot = fs.existsSync(path.resolve('agent/data/vinhlong360.db'))
  ? path.resolve('.')
  : path.resolve('..')
const dbPath = path.join(repoRoot, 'agent/data/vinhlong360.db')
const dataJsonPath = path.join(repoRoot, 'web/data.json')

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

describe('Phase 3: Comprehensive Data Standardization Suite', () => {
  it('verifies 100% of entities have non-empty description', () => {
    const stmt = db.prepare(`
      SELECT count(*) as count
      FROM entities
      WHERE description IS NULL OR trim(description) = ''
    `)
    const missingDesc = stmt.get() as { count: number }
    expect(missingDesc.count).toBe(0)
  })

  it('verifies the 5 enriched entities have authentic, high-quality descriptions without AI fillers', () => {
    const enrichedIds = [
      'khu-du-lich-bien-con-bung',
      'khu-di-tich-ao-ba-om',
      'bun-nuoc-leo-cho-ba-tri-ben-tre',
      'hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre',
      'prov-1',
    ]

    const forbiddenFillers = [
      'miền Tây',
      'sông nước hữu tình',
      'thiên đường',
      'hidden gem',
      'must-see',
      'không thể bỏ lỡ',
      'đắm chìm',
      'hòa mình vào',
      'điểm đến lý tưởng',
    ]

    const forbiddenOldProvinces = [
      'tỉnh Bến Tre',
      'tỉnh Trà Vinh',
    ]

    for (const eid of enrichedIds) {
      const stmt = db.prepare(`SELECT description FROM entities WHERE id = ?`)
      const row = stmt.get(eid) as { description: string } | undefined
      expect(row).toBeDefined()
      expect(row?.description.length).toBeGreaterThan(150)

      for (const filler of forbiddenFillers) {
        expect(row?.description.toLowerCase()).not.toContain(filler.toLowerCase())
      }

      for (const prov of forbiddenOldProvinces) {
        expect(row?.description).not.toContain(prov)
      }
    }
  })

  it('verifies 100% of entities have standardized sub_category across all types', () => {
    const stmtMissing = db.prepare(`
      SELECT count(*) as count
      FROM entities
      WHERE sub_category IS NULL OR trim(sub_category) = ''
    `)
    const missingSubCat = stmtMissing.get() as { count: number }
    expect(missingSubCat.count).toBe(0)

    // Check places taxonomy
    const placeSubCats = db.prepare(`
      SELECT DISTINCT sub_category FROM entities WHERE type = 'place'
    `).all() as Array<{ sub_category: string }>
    const validPlaceCats = new Set(['ward', 'commune', 'province'])
    for (const r of placeSubCats) {
      expect(validPlaceCats.has(r.sub_category)).toBe(true)
    }

    // Check facility taxonomy
    const facilitySubCats = db.prepare(`
      SELECT DISTINCT sub_category FROM entities WHERE type = 'facility'
    `).all() as Array<{ sub_category: string }>
    const validFacilityCats = new Set(['transport', 'medical', 'utility'])
    for (const r of facilitySubCats) {
      expect(validFacilityCats.has(r.sub_category)).toBe(true)
    }

    // Check person taxonomy
    const personSubCats = db.prepare(`
      SELECT DISTINCT sub_category FROM entities WHERE type = 'person'
    `).all() as Array<{ sub_category: string }>
    const validPersonCats = new Set(['historical-figure', 'artisan', 'cultural-figure', 'notable-person', 'military-leader'])
    for (const r of personSubCats) {
      expect(validPersonCats.has(r.sub_category)).toBe(true)
    }
  })

  it('verifies 100% of entities have valid season schema conforming to Season integrity', () => {
    const stmtMissing = db.prepare(`
      SELECT count(*) as count
      FROM entities
      WHERE season IS NULL OR trim(season) = ''
    `)
    const missingSeason = stmtMissing.get() as { count: number }
    expect(missingSeason.count).toBe(0)

    const allSeasons = db.prepare(`SELECT id, season FROM entities`).all() as Array<{ id: string; season: string }>
    for (const row of allSeasons) {
      let parsed: any
      expect(() => {
        parsed = JSON.parse(row.season)
      }).not.toThrow()

      expect(typeof parsed).toBe('object')
      if (parsed.months) {
        expect(Array.isArray(parsed.months)).toBe(true)
        for (const m of parsed.months) {
          expect(typeof m).toBe('number')
          expect(m).toBeGreaterThanOrEqual(1)
          expect(m).toBeLessThanOrEqual(12)
        }
      }
      if (parsed.peak && parsed.months) {
        expect(Array.isArray(parsed.peak)).toBe(true)
        const monthSet = new Set(parsed.months)
        for (const p of parsed.peak) {
          expect(monthSet.has(p)).toBe(true)
        }
      }
    }
  })

  it('verifies missing placeIds were resolved and 0 entities lack placeId', () => {
    const targetEntities = ['xa-thanh-phong', 'xa-hau-loc', 'ben-xe-mien-tay-hcm']
    for (const eid of targetEntities) {
      const stmt = db.prepare(`SELECT placeId FROM entities WHERE id = ?`)
      const row = stmt.get(eid) as { placeId: string } | undefined
      expect(row).toBeDefined()
      expect(row?.placeId).toBeTruthy()
    }

    const stmtMissing = db.prepare(`
      SELECT count(*) as count
      FROM entities
      WHERE placeId IS NULL OR trim(placeId) = ''
    `)
    const missingPlaceId = stmtMissing.get() as { count: number }
    expect(missingPlaceId.count).toBe(0)
  })

  it('verifies 100% of entities are indexed in entities_fts virtual search index', () => {
    const stmtEntities = db.prepare(`SELECT count(*) as c FROM entities`)
    const entityCount = stmtEntities.get() as { c: number }

    const stmtFts = db.prepare(`SELECT count(*) as c FROM entities_fts`)
    const ftsCount = stmtFts.get() as { c: number }

    expect(ftsCount.c).toBe(entityCount.c)
    expect(ftsCount.c).toBe(1772)

    // Test FTS search on enriched entities
    const searchStmt = db.prepare(`
      SELECT id, name FROM entities_fts WHERE entities_fts MATCH 'Ao Bà Om'
    `)
    const searchAoBaOm = searchStmt.all()
    expect(searchAoBaOm.length).toBeGreaterThan(0)
  })

  it('verifies web/data.json matches database synchronization with zero corrupt JSON', () => {
    const dataRaw = fs.readFileSync(dataJsonPath, 'utf-8')
    const data = JSON.parse(dataRaw)

    expect(data.entities.length).toBe(1772)
    expect(data.relationships.length).toBe(13343)
    expect(data.itineraries.length).toBe(33)

    // Validate no entity has empty description, attributes.sub_category, or placeId in web/data.json
    for (const e of data.entities) {
      expect(e.description).toBeTruthy()
      expect(e.attributes?.sub_category).toBeTruthy()
      expect(e.placeId).toBeTruthy()
      expect(e.season).toBeDefined()
    }
  })
})
