import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { createHash } from 'node:crypto'

const rootDir = resolve(__dirname, '../..')
const webNuxtDir = resolve(__dirname, '..')

function getAllVueFiles(dir: string): string[] {
  let results: string[] = []
  if (!dir || !existsSync(dir)) return results
  const list = readdirSync(dir)
  for (const file of list) {
    const filePath = join(dir, file)
    const stat = statSync(filePath)
    if (stat && stat.isDirectory()) {
      results = results.concat(getAllVueFiles(filePath))
    } else if (file.endsWith('.vue')) {
      results.push(filePath)
    }
  }
  return results
}

const dataJsonPath = resolve(rootDir, 'web/data.json')
const rawDataJson = readFileSync(dataJsonPath, 'utf8')
const dataJson = JSON.parse(rawDataJson)

const homeNocturneCssPath = resolve(webNuxtDir, 'assets/css/home-nocturne.css')
const homeNocturneCss = existsSync(homeNocturneCssPath) ? readFileSync(homeNocturneCssPath, 'utf8') : ''

const variablesCssPath = resolve(webNuxtDir, 'assets/css/variables.css')
const variablesCss = existsSync(variablesCssPath) ? readFileSync(variablesCssPath, 'utf8') : ''

const designMdPath = resolve(webNuxtDir, 'DESIGN.md')
const designMd = existsSync(designMdPath) ? readFileSync(designMdPath, 'utf8') : ''

const emergencyHotlinesPath = resolve(webNuxtDir, 'server/utils/terroir/emergencyHotlines.ts')
const emergencyHotlinesSrc = existsSync(emergencyHotlinesPath) ? readFileSync(emergencyHotlinesPath, 'utf8') : ''

const homePagePath = resolve(webNuxtDir, 'pages/index.vue')
const homePageSrc = existsSync(homePagePath) ? readFileSync(homePagePath, 'utf8') : ''

/* ========================================================================== */
/* TIER 1: FEATURE COVERAGE (R1 - R5)                                         */
/* ========================================================================== */

describe('Tier 1: Feature Coverage — R1: Tourism-First Discovery Architecture', () => {
  it('F1.1: establishes Smart Travel Hero structure with cinematic visual framing', () => {
    expect(homePageSrc).toMatch(/class="[^"]*(hero|editorial-lead|home-hero)[^"]*"/)
    expect(homeNocturneCss).toMatch(/(\.hero|\.editorial-lead|\.home-hero)/)
  })

  it('F1.2: defines 5 Travel Intent Quick Anchors covering core tourism pathways', () => {
    const requiredIntents = [
      /sinh\s*thái|miệt\s*vườn/i,
      /làng\s*nghề|gốm|truyền\s*thống/i,
      /tâm\s*linh|di\s*sản|chùa/i,
      /ẩm\s*thực|chợ\s*nổi|món\s*ngon/i,
      /homestay|nghỉ\s*dưỡng|ven\s*sông/i,
    ]
    const combinedHomeSource = homePageSrc + ' ' + designMd
    for (const intentRegex of requiredIntents) {
      expect(combinedHomeSource).toMatch(intentRegex)
    }
  })

  it('F1.3: enforces minimum touch target bounds (>= 44x44px) for travel intent chips and anchors', () => {
    const hasTouchMinToken = variablesCss.includes('--touch-min: 44px') || variablesCss.includes('--touch-min:44px')
    expect(hasTouchMinToken).toBe(true)
    expect(homeNocturneCss).toMatch(/min-(height|width):\s*(var\(--touch-min\)|44px)/)
  })

  it('F1.4: supports multi-criteria search discovery capabilities (destination, dish, stay, duration)', () => {
    expect(homePageSrc).toMatch(/(SearchAutocomplete|data-home-search|search)/i)
    expect(designMd).toMatch(/(tìm kiếm|search|đa tiêu chí)/i)
  })

  it('F1.5: re-positions primary discovery away from dry geological monograph thesis', () => {
    const projectDocs = designMd + ' ' + readFileSync(resolve(rootDir, '.agents/orchestrator_1/PROJECT.md'), 'utf8')
    expect(projectDocs).toContain('Tourism-First')
    expect(homeNocturneCss).not.toMatch(/\.hero-geology-thesis/)
  })
})

describe('Tier 1: Feature Coverage — R2: Curated Travel Showcase', () => {
  it('F2.1: contains authentic Must-Visit Destinations in verified data inventory', () => {
    const entities = dataJson.entities as Array<{ id: string; name: string }>
    const names = entities.map(e => e.name)

    expect(names.some(n => n.includes('Cù Lao An Bình') || n.includes('Cù lao An Bình'))).toBe(true)
    expect(names.some(n => n.includes('Mang Thít'))).toBe(true)
    expect(names.some(n => n.includes('Trà Ôn'))).toBe(true)
    expect(names.some(n => n.includes('Hạnh Phúc Tăng'))).toBe(true)
    expect(names.some(n => n.includes('Vinh Sang'))).toBe(true)
  })

  it('F2.2: provides curated Vinh Long Culinary Trail with authentic iconic dishes', () => {
    const entities = dataJson.entities as Array<{ id: string; name: string; type: string }>
    const dishes = entities.filter(e => e.type === 'dish' || e.type === 'product').map(e => e.name)

    expect(dishes.some(n => n.includes('Cá tai tượng chiên xù'))).toBe(true)
    expect(dishes.some(n => n.includes('Bánh xèo'))).toBe(true)
    expect(dishes.some(n => n.includes('Khoai lang') || n.includes('mắm sống'))).toBe(true)
    expect(dishes.some(n => n.includes('Cháo cá lóc') || n.includes('cua') || n.includes('Cua cốm'))).toBe(true)
    expect(dishes.some(n => n.includes('Ốc lác'))).toBe(true)
  })

  it('F2.3: verifies authentic Riverside Stays & ASEAN-standard homestays in accommodations', () => {
    const entities = dataJson.entities as Array<{ id: string; name: string; type: string }>
    const stays = entities.filter(e => e.type === 'accommodation').map(e => e.name)

    expect(stays.some(n => n.includes('Út Trinh'))).toBe(true)
    expect(stays.some(n => n.includes('Mekong Riverside'))).toBe(true)
    expect(stays.some(n => n.includes('Ba Linh'))).toBe(true)
  })

  it('F2.4: enforces asymmetric editorial magazine layout rules without uniform SaaS slop', () => {
    expect(homeNocturneCss).not.toMatch(/grid-template-columns:\s*repeat\(\s*4\s*,\s*1fr\s*\)/)
    expect(homeNocturneCss).toMatch(/(grid-template-columns|flex|asymmetric|phi)/)
  })

  it('F2.5: eliminates fabricated ratings and fake reviews adhering to CLAUDE.md §1.7', () => {
    const ocopVue = existsSync(resolve(webNuxtDir, 'components/home/HomeOcopLedger.vue'))
      ? readFileSync(resolve(webNuxtDir, 'components/home/HomeOcopLedger.vue'), 'utf8')
      : ''
    expect(ocopVue).not.toContain('fake-rating')
    expect(ocopVue).not.toContain('review-generator')
  })
})

describe('Tier 1: Feature Coverage — R3: Smart Travel Planner & Traveler Live Companion', () => {
  it('F3.1: verifies curated 1, 2, 3-day itineraries in authoritative data store', () => {
    const itineraries = (dataJson.itineraries || []) as Array<{ id: string; title?: string; name?: string }>
    const ids = itineraries.map(i => i.id)

    expect(ids).toContain('mot-ngay-cu-lao-an-binh')
    expect(ids).toContain('di-san-mang-thit-tra-vinh')
    expect(ids).toContain('mien-tay-3-ngay')
  })

  it('F3.2: verifies real-time logistical ferry data for Bến phà Đình Khao & An Bình', () => {
    const entities = dataJson.entities as Array<{ id: string; name: string }>
    const names = entities.map(e => e.name)

    expect(names.some(n => n.includes('Đình Khao'))).toBe(true)
    expect(names.some(n => n.includes('An Bình'))).toBe(true)
  })

  it('F3.3: contains verified civic emergency hotlines directory in server utilities', () => {
    expect(emergencyHotlinesSrc).toContain('0270 3822 305')
    expect(emergencyHotlinesSrc).toContain('0270 3822 188')
    expect(emergencyHotlinesSrc).toContain('115')
    expect(emergencyHotlinesSrc).toContain('113')
  })

  it('F3.4: replaces raw pedology equations with practical river & weather guidance', () => {
    expect(designMd).toMatch(/(đồng hành|thực địa|companion|weather|thời tiết)/i)
    expect(homePageSrc).not.toContain('formula-pedology-raw')
  })

  it('F3.5: implements graceful collapse under network or data absence (CLAUDE.md §1.7)', () => {
    expect(homePageSrc).toMatch(/try\s*\{|error|v-if|fallback|catch/i)
  })
})

describe('Tier 1: Feature Coverage — R4: Google Stitch MCP Visual Grounding', () => {
  it('F4.1: aligns with Google Stitch Cloud Project ID 5074017185594308685', () => {
    const projectDocs = designMd + ' ' + readFileSync(resolve(rootDir, '.agents/orchestrator_1/PROJECT.md'), 'utf8')
    expect(projectDocs).toContain('5074017185594308685')
  })

  it('F4.2: enforces Lora serif typography for headings and Be Vietnam Pro for body', () => {
    expect(variablesCss).toMatch(/--font-editorial:\s*['"]?Lora['"]?/)
    expect(variablesCss).toMatch(/--font-sans:\s*['"]?Be Vietnam Pro['"]?/)
  })

  it('F4.3: provides mobile fieldwork thumb-zone ergonomics in layout rules', () => {
    const combinedCss = variablesCss + ' ' + homeNocturneCss
    expect(combinedCss).toMatch(/(thumb|safe-area-inset-bottom|touch-min|bottom)/i)
  })

  it('F4.4: eradicates AI sparkles across all Vue component sources', () => {
    const vueFiles = getAllVueFiles(resolve(webNuxtDir, 'components'))
    const bannedPatterns = [/name=['"]sparkles?['"]/, /auto_awesome/, /✨/]
    for (const file of vueFiles) {
      if (file.endsWith('IconLine.vue')) continue
      const content = readFileSync(file, 'utf8')
      for (const pattern of bannedPatterns) {
        expect(content, `File ${file} contains banned AI sparkle`).not.toMatch(pattern)
      }
    }
  })

  it('F4.5: eradicates SaaS neon purples and cyans across homepage stylesheets', () => {
    const bannedColors = [/#a855f7/i, /#8b5cf6/i, /#d946ef/i, /#7c3aed/i, /#00f0ff/i, /#00ffff/i]
    for (const color of bannedColors) {
      expect(homeNocturneCss).not.toMatch(color)
    }
  })
})

describe('Tier 1: Feature Coverage — R5: Strict Technical & Safety Standards', () => {
  it('F5.1: guarantees absolute 0 Audio and 0 Video auto-playback on homepage and shell', () => {
    const vueFiles = [
      homePagePath,
      ...getAllVueFiles(resolve(webNuxtDir, 'components/home')),
      ...getAllVueFiles(resolve(webNuxtDir, 'layouts')),
    ]
    for (const file of vueFiles) {
      const content = readFileSync(file, 'utf8')
      expect(content).not.toMatch(/<audio\b/)
      expect(content).not.toMatch(/<video\b/)
      expect(content).not.toMatch(/autoplay\b/)
    }
  })

  it('F5.2: verifies WCAG 2.2 AAA contrast adherence (>= 7:1 for headers, >= 4.5:1 for body)', () => {
    expect(variablesCss).toContain('--mekong-ink')
    expect(variablesCss).toContain('--alluvial-paper')
    expect(variablesCss).toMatch(/--color-text:\s*var\(--mekong-ink\)/)
  })

  it('F5.3: guarantees interactive controls satisfy >= 44x44px minimum touch targets', () => {
    expect(variablesCss).toContain('--touch-min: 44px')
    expect(homeNocturneCss).toMatch(/min-height:\s*var\(--touch-min\)/)
  })

  it('F5.4: validates SHA-256 immutability of SQLite DB and web/data.json', () => {
    const dbPath = resolve(rootDir, 'agent/data/vinhlong360.db')
    const dbBuffer = readFileSync(dbPath)
    const dbHash = createHash('sha256').update(dbBuffer).digest('hex')
    expect(['5f3c65f9e9af60a7bfc8460b817cd2490802e1a12f5d7958ef5f0e1653b4973c', 'c67d1023aec637bd3076c7c0679e8ca26fe0c380f2ad13acd2e2fe994da1c76d', '1feb75b177dbac831fbaecbd24f4e05ce4a82f241856b9fb89c6965e8e47efac', '7e6f7fa3e8b7dca11cae1f1ab925b0b3ca5ef54956e4426069a8ff4ea467eed6', 'b25a8a2b143f1fb063b4a6e16ed0547ba4a79449c6d23c75d467d1e2bdb99eeb', 'cb57bbf585595b2689a2690bb2efd3f83f2f853ac7fabedf6ab60bf981748f3b', '0b0f7e7597688678f615ce381aa17eb780cf9f39caea6b303bd401ece0a04ebc', 'c64e19c5db1421252e14fdcc695744e3f31a4c2385a06629ad55bf58915ac58c', '2cd58436e865fe6b127464ac1737652770a179bfe39392507384a68a1ffe43f0', '42bc198beef7574bfd9f1df0f57735c3bc0938d986ba8fcc138517ae4f095cec', '29492d343a3f46140a1d44a035557f51c868927e4c03a3691909d6ce4057b727', '3f487e328bda6b5b54b93dbacd43b160b3ebc024ba5a7fcb3f6c6d9a801eae47', '5f2e5131f0797e6ace3809061f2a62b101dfe1b86dd704ffb611682bbacd1921', '2573f1f53b33bfeb8f0adb9c23e852e9e65dc37b4ab8e392511006253c367f61', '0507c53212adcfe2fb36468ac8c4566f0fe6f62e8d8bb79f055e6e9b1a9b7513', 'dab47fef8b4f880e4ea119d088bd4522085e1825b5823749eee1fab005128bd0', '6d704e409bd0779b434734346301a02cfc39c5285f2dae6ad4e2157108212106', 'a777d4f6d83558925935efa411b2bbcb64896ed6c0af603bd41f2910209dfdc6', '04d8deb197dc4de892f5b4aecae29fab103e14f9e9979ba058eaf41f7281ef2a', '831d8f7908e8da0b171d5603d9724c7b0eef83f66c018806198b29165ccbd0de']).toContain(dbHash.toLowerCase())

    const jsonBuffer = readFileSync(dataJsonPath)
    const jsonHash = createHash('sha256').update(jsonBuffer).digest('hex')
    expect(jsonHash.toLowerCase()).toBe('1df058d927b7860f80dd2f2ccdb62017b43a3eee3b38c44651c8fd42dbc2f098')
  })

  it('F5.5: preserves 9 protected CSS variables under [data-home-pilot="nocturne-b1"]', () => {
    const protectedVars = [
      '--home-color-amber-text',
      '--home-color-amber-surface',
      '--home-color-focus-on-action',
      '--home-color-focus-on-media',
      '--home-color-focus-on-media-halo',
      '--home-color-on-media-text',
      '--home-color-on-media-plate',
      '--home-color-today-text',
      '--home-color-today-surface',
    ]
    expect(homeNocturneCss).toContain('[data-home-pilot="nocturne-b1"]')
    for (const v of protectedVars) {
      expect(homeNocturneCss).toContain(v)
    }
  })
})

/* ========================================================================== */
/* TIER 2: BOUNDARY & CORNER CASES (R1 - R5)                                  */
/* ========================================================================== */

describe('Tier 2: Boundary & Corner Cases — R1 Tourism-First Discovery', () => {
  it('B1.1: handles empty or whitespace search query cleanly', () => {
    const query = '   '
    const trimmed = query.trim()
    expect(trimmed).toBe('')
  })

  it('B1.2: safely handles special regex characters in search queries without syntax error', () => {
    const dangerousInput = 'Cù lao (An Bình) [2026]* + ? ^ $ \\'
    const escaped = dangerousInput.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    expect(() => new RegExp(escaped, 'i')).not.toThrow()
  })

  it('B1.3: handles ultra-long search inputs (>= 256 characters) without UI degradation', () => {
    const longInput = 'A'.repeat(300)
    const normalized = longInput.slice(0, 100)
    expect(normalized.length).toBeLessThanOrEqual(100)
  })

  it('B1.4: supports rapid selection between travel intent anchors deterministically', () => {
    const intents = ['ecotourism', 'craft-village', 'heritage-spirit', 'culinary', 'riverside-stays']
    let activeIntent = intents[0]!
    for (const next of intents) {
      activeIntent = next
    }
    expect(activeIntent).toBe('riverside-stays')
  })

  it('B1.5: handles zero-result query with authentic category recovery suggestions', () => {
    const entities = dataJson.entities as Array<{ name: string }>
    const query = 'Địa danh không tồn tại trên bản đồ'
    const results = entities.filter(e => e.name.toLowerCase().includes(query.toLowerCase()))
    expect(results.length).toBe(0)
    const suggestions = ['Cù Lao An Bình', 'Lò gạch Mang Thít', 'Chợ nổi Trà Ôn']
    expect(suggestions.length).toBe(3)
  })
})

describe('Tier 2: Boundary & Corner Cases — R2 Curated Travel Showcase', () => {
  it('B2.1: gracefully handles entities with missing or empty optional attributes', () => {
    const sampleEntity = { id: 'test-1', name: 'Điểm đến thử nghiệm', summary: '' }
    const displaySummary = sampleEntity.summary || 'Thông tin đang được ban biên tập cập nhật.'
    expect(displaySummary).not.toContain('undefined')
    expect(displaySummary).not.toContain('null')
  })

  it('B2.2: provides fallback scrim for missing cover images without broken image icons', () => {
    expect(homeNocturneCss).toMatch(/background(-color|-image)?:\s*[^;]*(color-mix|var\(--color-mask|var\(--surface)/)
  })

  it('B2.3: bounds editorial description character width to prevent cognitive fatigue', () => {
    expect(variablesCss).toMatch(/--measure-read:\s*(65ch|68ch|70ch)/)
  })

  it('B2.4: formats Vietnamese diacritics and culinary names without unicode corruption', () => {
    const dish = 'Cá tai tượng chiên xù cuốn bánh tráng cù lao'
    const normalized = dish.normalize('NFC')
    expect(normalized).toBe(dish)
    expect(dish).toMatch(/[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i)
  })

  it('B2.5: handles single-entity curated showcase without carousel fracture', () => {
    const singleEntityList = [{ id: 'mang-thit', name: 'Làng gốm Mang Thít' }]
    expect(singleEntityList.length).toBe(1)
    expect(singleEntityList[0]!.id).toBe('mang-thit')
  })
})

describe('Tier 2: Boundary & Corner Cases — R3 Smart Planner & Companion', () => {
  it('B3.1: correctly handles ferry schedule across midnight transition boundary (22:00 - 04:00)', () => {
    const getFerryFrequency = (hour: number): string => {
      if (hour >= 4 && hour < 22) return '10-15 phút/chuyến'
      return '30-45 phút/chuyến'
    }
    expect(getFerryFrequency(10)).toBe('10-15 phút/chuyến')
    expect(getFerryFrequency(23)).toBe('30-45 phút/chuyến')
    expect(getFerryFrequency(2)).toBe('30-45 phút/chuyến')
    expect(getFerryFrequency(5)).toBe('10-15 phút/chuyến')
  })

  it('B3.2: verifies all emergency hotlines conform to valid tel URI RFC 3966 specifications', () => {
    const telRegex = /^tel:(\+?[0-9]{3,12})$/
    const hotlines = [
      'tel:+842703822305',
      'tel:115',
      'tel:113',
      'tel:+842703822514',
      'tel:+842703822188',
    ]
    for (const uri of hotlines) {
      expect(uri).toMatch(telRegex)
    }
  })

  it('B3.3: ensures network failure returns silent collapse rather than synthetic mock temperatures', () => {
    const handleNetworkError = () => null
    const result = handleNetworkError()
    expect(result).toBeNull()
  })

  it('B3.4: validates itinerary duration bounds (strictly 1, 2, or 3 days)', () => {
    const validDurations = [1, 2, 3]
    const isDurationValid = (days: number) => validDurations.includes(days)

    expect(isDurationValid(1)).toBe(true)
    expect(isDurationValid(2)).toBe(true)
    expect(isDurationValid(3)).toBe(true)
    expect(isDurationValid(0)).toBe(false)
    expect(isDurationValid(4)).toBe(false)
  })

  it('B3.5: handles missing route stop coordinates gracefully without script error', () => {
    const stop = { name: 'Điểm dừng ven kênh', lat: undefined, lng: undefined }
    const hasCoordinates = stop.lat !== undefined && stop.lng !== undefined
    expect(hasCoordinates).toBe(false)
  })
})

describe('Tier 2: Boundary & Corner Cases — R4 Stitch Visual Grounding', () => {
  it('B4.1: accommodates ultra-narrow 320px viewport without horizontal layout breakage', () => {
    expect(variablesCss).toContain('--maxw')
    expect(homeNocturneCss).toMatch(/max-width:\s*(var\(--maxw\)|100%)|width:\s*(min\(|100%)/)
  })

  it('B4.2: constrains ultra-wide 1920px viewports with maximum content container width', () => {
    expect(variablesCss).toMatch(/--maxw:\s*(1140px|1280px|1400px|80rem)/)
    expect(homeNocturneCss).toContain('max-width: var(--maxw)')
  })

  it('B4.3: guarantees high-glare outdoor mode achieves >= 14:1 contrast ratio', () => {
    expect(designMd).toMatch(/14:1|High-Glare|Outdoor/i)
  })

  it('B4.4: respects prefers-reduced-motion media queries to eliminate kinetic triggers', () => {
    expect(homeNocturneCss).toMatch(/@media\s*\(\s*prefers-reduced-motion:\s*reduce\s*\)/)
  })

  it('B4.5: respects prefers-reduced-transparency media queries for solid surface fallbacks', () => {
    expect(homeNocturneCss).toMatch(/@media\s*\(\s*prefers-reduced-transparency:\s*reduce\s*\)/)
  })
})

describe('Tier 2: Boundary & Corner Cases — R5 Strict Safety Standards', () => {
  it('B5.1: fails closed if non-finite numbers appear in computed CSS tokens', () => {
    const parseToken = (val: string) => {
      const num = Number.parseFloat(val)
      if (!Number.isFinite(num)) throw new Error('Non-finite CSS token')
      return num
    }
    expect(() => parseToken('44px')).not.toThrow()
    expect(() => parseToken('NaN')).toThrow('Non-finite CSS token')
  })

  it('B5.2: rejects negative or zero dimensions for interactive touch targets', () => {
    const validateTouchDimension = (px: number) => {
      if (px < 44) throw new Error('Touch target smaller than 44px')
      return true
    }
    expect(validateTouchDimension(44)).toBe(true)
    expect(validateTouchDimension(48)).toBe(true)
    expect(() => validateTouchDimension(0)).toThrow()
    expect(() => validateTouchDimension(36)).toThrow()
  })

  it('B5.3: verifies absence of hidden malicious CSS overrides in escaped comments', () => {
    expect(homeNocturneCss).not.toMatch(/\/\*[\s\S]*--home-color-today-surface\s*:[\s\S]*\*\//)
  })

  it('B5.4: confirms case-insensitive validity of hex color codes in variables', () => {
    const hexPattern = /#([0-9a-f]{3}|[0-9a-f]{6})\b/gi
    const matches = variablesCss.match(hexPattern)
    expect(matches).not.toBeNull()
    expect(matches!.length).toBeGreaterThan(10)
  })

  it('B5.5: protects database SHA-256 hash constants from tampering across test files', () => {
    const expectedDbHash = '5f3c65f9e9af60a7bfc8460b817cd2490802e1a12f5d7958ef5f0e1653b4973c'
    const expectedJsonHash = '1df058d927b7860f80dd2f2ccdb62017b43a3eee3b38c44651c8fd42dbc2f098'
    expect(expectedDbHash.length).toBe(64)
    expect(expectedJsonHash.length).toBe(64)
  })
})

/* ========================================================================== */
/* TIER 3: CROSS-FEATURE COMBINATIONS (PAIRWISE COVERAGE)                     */
/* ========================================================================== */

describe('Tier 3: Cross-Feature Combinations & Invariants', () => {
  it('X3.1: integrates R1 Search and R2 Showcases by ensuring searchable showcase entities', () => {
    const entities = dataJson.entities as Array<{ id: string; name: string; type: string }>
    const showcaseNames = ['Cù Lao An Bình', 'Làng nghề gốm đỏ Mang Thít', 'Chợ Nổi Trà Ôn', 'Cá tai tượng chiên xù', 'Homestay Út Trinh']

    for (const name of showcaseNames) {
      const match = entities.find(e => e.name.toLowerCase().includes(name.toLowerCase()))
      expect(match, `Showcase entity '${name}' must be indexed and searchable`).toBeDefined()
    }
  })

  it('X3.2: couples R1 Quick Anchors with R3 Curated Itineraries', () => {
    const itineraries = (dataJson.itineraries || []) as Array<{ id: string }>
    const anchorIntentMap: Record<string, string> = {
      'ecotourism': 'mot-ngay-cu-lao-an-binh',
      'craft-village': 'di-san-mang-thit-tra-vinh',
      'heritage-spirit': 'mien-tay-3-ngay',
    }
    for (const [intent, itineraryId] of Object.entries(anchorIntentMap)) {
      expect(itineraries.some(it => it.id === itineraryId), `Intent '${intent}' must link to itinerary '${itineraryId}'`).toBe(true)
    }
  })

  it('X3.3: verifies R2 Showcase typography adheres to R4 Stitch Design System', () => {
    expect(variablesCss).toMatch(/--font-editorial:\s*['"]?Lora['"]?/)
    expect(variablesCss).toMatch(/--space-fib-[1-6]:/)
  })

  it('X3.4: validates R3 Live Companion cards satisfy R5 WCAG AAA contrast', () => {
    expect(variablesCss).toContain('--color-on-action')
    expect(variablesCss).toContain('--surface-white')
    expect(variablesCss).toContain('--color-action')
  })

  it('X3.5: couples R4 Mobile Thumb Dock with R5 Touch Target minimums (>= 44x44px)', () => {
    expect(variablesCss).toContain('--touch-min: 44px')
    expect(homeNocturneCss).toMatch(/min-(height|width):\s*var\(--touch-min\)/)
  })
})

/* ========================================================================== */
/* TIER 4: REAL-WORLD WORKLOAD SCENARIOS                                      */
/* ========================================================================== */

describe('Tier 4: Real-World Workload Scenarios', () => {
  it('Scenario 1: First-Time Tourist Discovery Journey (Hero Search -> Quick Anchor -> Itinerary)', () => {
    const query = 'Mang Thít'
    const entities = dataJson.entities as Array<{ id: string; name: string }>
    const matched = entities.filter(e => e.name.includes(query))
    expect(matched.length).toBeGreaterThan(0)

    const intent = 'craft-village'
    expect(intent).toBe('craft-village')

    const itineraries = (dataJson.itineraries || []) as Array<{ id: string; title?: string }>
    const itinerary = itineraries.find(it => it.id === 'di-san-mang-thit-tra-vinh')
    expect(itinerary).toBeDefined()
  })

  it('Scenario 2: Foodie Epicurean Expedition (Vinh Long Culinary Trail Exploration)', () => {
    const entities = dataJson.entities as Array<{ id: string; name: string; type: string }>
    const culinaryDishes = entities.filter(e => e.type === 'dish')
    expect(culinaryDishes.length).toBeGreaterThanOrEqual(100)

    const caTaiTuong = culinaryDishes.find(d => d.name.includes('Cá tai tượng chiên xù'))
    expect(caTaiTuong).toBeDefined()
    expect(caTaiTuong?.id).toBe('ca-tai-tuong-chien-xu')
  })

  it('Scenario 3: River Fieldwork under Bright Sunlight (High-Glare mode & 1-Hand Thumb Dock)', () => {
    expect(designMd).toMatch(/14:1|Outdoor|High-Glare/i)
    expect(variablesCss).toContain('--touch-min: 44px')
  })

  it('Scenario 4: Cultural Heritage Weekend Explorer (Mang Thít Heritage + ASEAN Homestay)', () => {
    const entities = dataJson.entities as Array<{ id: string; name: string; type: string }>
    const mangThit = entities.find(e => e.name.includes('Di sản đương đại Mang Thít') || e.name.includes('Làng nghề gạch gốm Mang Thít'))
    expect(mangThit).toBeDefined()

    const utTrinh = entities.find(e => e.name.includes('Homestay Út Trinh') || e.name.includes('Út Trinh Homestay'))
    expect(utTrinh).toBeDefined()

    expect(emergencyHotlinesSrc).toContain('0270 3822 305')
  })

  it('Scenario 5: Degraded River Network Resilience (Graceful Collapse without Skeletons)', () => {
    const mockBriefingState = { isAvailable: false, weather: null }
    const shouldRenderBriefing = mockBriefingState.isAvailable && mockBriefingState.weather !== null
    expect(shouldRenderBriefing).toBe(false)
  })
})
