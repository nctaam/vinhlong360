import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT_DIR = path.resolve(__dirname, '..')
const LLMS_TXT_PATH = path.join(ROOT_DIR, 'web-nuxt', 'public', 'llms.txt')
const LLMS_FULL_TXT_PATH = path.join(ROOT_DIR, 'web-nuxt', 'public', 'llms-full.txt')
const DATA_JSON_PATH = path.join(ROOT_DIR, 'web', 'data.json')

describe('LLMs Machine-Readable Specification Compliance (llmstxt.org)', () => {
  const data = JSON.parse(fs.readFileSync(DATA_JSON_PATH, 'utf8'))
  const verifiedEntities = data.entities.filter((e: any) => e.attributes?.is_verified_photo)
  const itineraries = data.itineraries || []
  const wards = data.entities.filter((e: any) => e.type === 'place' && e.id !== 'prov-1' && e.id !== 'vinh-long')

  it('verifies llms.txt exists, follows llmstxt.org format and references llms-full.txt', () => {
    expect(fs.existsSync(LLMS_TXT_PATH)).toBe(true)
    const content = fs.readFileSync(LLMS_TXT_PATH, 'utf8')
    expect(content.length).toBeGreaterThan(500)
    expect(content).toContain('# vinhlong360.vn')
    expect(content).toContain('/llms-full.txt')
    expect(content).toContain('1619')
    expect(content).toContain('33')
    expect(content).toContain('124')
    expect(content).toContain('GET /api/v1/entities')
  })

  it('verifies llms-full.txt exists and contains exhaustive data for all 1619 verified photo entities', () => {
    expect(fs.existsSync(LLMS_FULL_TXT_PATH)).toBe(true)
    const content = fs.readFileSync(LLMS_FULL_TXT_PATH, 'utf8')
    expect(content.length).toBeGreaterThan(100000)

    expect(verifiedEntities.length).toBe(1619)
    for (const e of verifiedEntities) {
      expect(content).toContain(e.id)
      expect(content).toContain('/img/entities/' + e.id + '.webp')
      if (e.attributes?.image_author) {
        expect(content).toContain(e.attributes.image_author)
      }
    }
  })

  it('verifies llms-full.txt covers all 33 thematic itineraries and 124 communes/wards', () => {
    const content = fs.readFileSync(LLMS_FULL_TXT_PATH, 'utf8')
    expect(itineraries.length).toBe(33)
    for (const itin of itineraries) {
      expect(content).toContain('/lich-trinh/' + itin.id)
    }

    expect(wards.length).toBe(124)
    for (const w of wards) {
      expect(content).toContain('/xa-phuong/' + w.id)
    }
  })

  it('ensures rule R10.7 compliance without forbidden province references', () => {
    const content = fs.readFileSync(LLMS_FULL_TXT_PATH, 'utf8')
    const lines = content.split('\n')
    for (const line of lines) {
      if (line.includes('tỉnh Bến Tre') || line.includes('tỉnh Trà Vinh')) {
        expect(line.toLowerCase()).toMatch(/(trước|cũ|hợp nhất|lịch sử|không còn|tuyệt đối không|quy chuẩn|nhiệm kỳ|ghpgvn|giáo hội|thời kỳ|nguyên|hội thi|giải|liên hoan)/i)
      }
    }
  })
})
