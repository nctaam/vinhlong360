// @vitest-environment node
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(process.cwd())
const doc = (rel: string) => readFileSync(resolve(root, rel), 'utf8')

describe('SEO & Editorial Craft Guardrails', () => {
  it('Google Sitelinks Searchbox uses EntryPoint schema on home and search hubs', () => {
    const home = doc('pages/index.vue')
    const search = doc('pages/tim-kiem.vue')

    expect(home).toContain("@type': 'EntryPoint'")
    expect(home).toContain("urlTemplate: 'https://vinhlong360.vn/tim-kiem?q={search_term_string}'")
    expect(home).toContain("ogType: 'website'")
    expect(home).toContain("twitterCard: 'summary_large_image'")

    expect(search).toContain("@type': 'EntryPoint'")
    expect(search).toContain("urlTemplate: 'https://vinhlong360.vn/tim-kiem?q={search_term_string}'")
  })

  it('Search results dynamically guard crawl budget with noindex, follow', () => {
    const search = doc('pages/tim-kiem.vue')
    expect(search).toMatch(/robots:\s*\(\)\s*=>\s*q\.value\.trim\(\)\s*\?\s*'noindex,\s*follow'\s*:\s*'index,\s*follow'/)
  })

  it('All key public navigation hubs pass :json-ld="true" to Breadcrumb', () => {
    const hubs = [
      'pages/tim-kiem.vue',
      'pages/ban-do.vue',
      'pages/danh-ba.vue',
      'pages/tuyen-duong.vue',
      'pages/dia-diem/index.vue',
      'pages/cong-dong.vue',
      'pages/huong-dan.vue',
      'pages/kham-pha/[interest].vue',
      'pages/luu-tru.vue',
      'pages/su-kien.vue',
      'pages/khu-vuc/[area].vue',
      'pages/du-lich.vue',
      'pages/san-pham.vue',
      'pages/le-hoi.vue',
      'pages/theo-mua.vue',
      'pages/ocop.vue',
      'pages/lich-trinh/[id].vue',
      'pages/bai-viet/[id].vue',
      'pages/xa-phuong/[id].vue',
    ]

    for (const hub of hubs) {
      const src = doc(hub)
      expect(src, `${hub} should enable :json-ld="true" on Breadcrumb`).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    }
  })

  it('Exploration category title does not prepend decorative emojis in SEO title', () => {
    const interest = doc('pages/kham-pha/[interest].vue')
    expect(interest).not.toMatch(/title:\s*`\$\{interestMeta\.value\.emoji\}/)
    expect(interest).toContain('title: `${interestMeta.value.label} — Khám phá Vĩnh Long — vinhlong360`')
  })

  it('AI search assistant has stroke-consistent vectors and purpose-driven radius-control', () => {
    const assist = doc('components/AISearchAssist.vue')
    expect(assist).toContain('<IconLine name="alert-triangle"')
    expect(assist).toContain('<IconLine name="repeat"')
    expect(assist).toContain('var(--radius-control)')
    expect(assist).not.toContain('var(--radius-sm)')
  })

  it('AI best-time and travel-tips panels eliminate raw glyphs and use purpose-driven radius-control', () => {
    const bestTime = doc('components/AIBestTime.vue')
    expect(bestTime).toContain('<IconLine name="sparkles" class="btn-sparkle"')
    expect(bestTime).toContain('<IconLine name="alert-triangle"')
    expect(bestTime).toContain('<IconLine name="repeat"')
    expect(bestTime).toContain('var(--radius-control)')

    const tips = doc('components/AITravelTips.vue')
    expect(tips).toContain('<IconLine :name="expanded ? \'chevron-up\' : \'chevron-down\'"')
    expect(tips).not.toContain('{{ expanded ? \'▲\' : \'▼\' }}')
    expect(tips).toContain('<IconLine name="alert-triangle"')
    expect(tips).toContain('<IconLine name="repeat"')
    expect(tips).toContain('var(--radius-control)')
  })

  it('Home local briefing uses IconLine vector for season link with hover micro-interaction', () => {
    const briefing = doc('components/home/HomeLocalBriefing.vue')
    expect(briefing).toContain('<IconLine name="arrow-right" class="hlb-arrow"')
    expect(briefing).not.toContain('Lịch mùa vụ tháng {{ currentMonth }} →')
  })

  it('Admin sortable controls use stroke-consistent vector chevrons instead of raw triangle glyphs', () => {
    const sortable = doc('components/admin/SortableList.vue')
    expect(sortable).toContain('<IconLine name="chevron-up"')
    expect(sortable).toContain('<IconLine name="chevron-down"')
    expect(sortable).not.toContain('>▲</button>')
    expect(sortable).not.toContain('>▼</button>')

    const entities = doc('pages/admin/entities.vue')
    expect(entities).toContain('<IconLine v-if="sortIcon(\'id\')" :name="sortIcon(\'id\')"')
    expect(entities).not.toContain("return sortDir.value === 'asc' ? '▲' : '▼'")
  })

  it('ChatWidget uses vector repeat and send/stop icons without raw unicode glyphs', () => {
    const chat = doc('components/ChatWidget.vue')
    expect(chat).toContain('<IconLine name="repeat" class="retry-icon"')
    expect(chat).not.toContain('↻ Thử lại')
    expect(chat).toContain('<IconLine name="square"')
    expect(chat).toContain('<IconLine name="arrow-up"')
  })

  it('ToastContainer uses stroke-consistent IconLine vectors for all status levels and dismiss', () => {
    const toast = doc('components/ToastContainer.vue')
    expect(toast).toContain('<IconLine :name="iconNameFor(t.type)"')
    expect(toast).toContain('<IconLine name="x" aria-hidden="true"')
    expect(toast).not.toContain('&times;')
    expect(toast).not.toContain("'✓'")
    expect(toast).not.toContain("'✕'")
    expect(toast).not.toContain("'⚠'")
  })

  it('Admin itinerary editor uses stroke-consistent vectors and purpose-driven radius tokens', () => {
    const itinerary = doc('pages/admin/lich-trinh.vue')
    expect(itinerary).not.toContain('&#128205;')
    expect(itinerary).not.toContain('&#9650;')
    expect(itinerary).not.toContain('&#9660;')
    expect(itinerary).not.toContain('&#10005;')
    expect(itinerary).toContain('<IconLine name="pin" class="lt-stops-empty-icon"')
    expect(itinerary).toContain('<IconLine name="chevron-up"')
    expect(itinerary).toContain('<IconLine name="chevron-down"')
    expect(itinerary).toContain('var(--radius-control)')
    expect(itinerary).toContain('var(--radius-surface)')
  })

  it('Entity detail page includes full OpenGraph metadata, Twitter card, and Schema.org hasMap', () => {
    const detail = doc('pages/dia-diem/[id].vue')
    expect(detail).toContain("twitterCard: 'summary_large_image'")
    expect(detail).toContain("ogUrl: () => entity.value ? entityDetailUrl(entity.value.id) : canonicalUrl('/dia-diem')")
    expect(detail).toContain("ld.hasMap = `https://www.google.com/maps/search/?api=1&query=${geoCoords[0]},${geoCoords[1]}`")
  })

  it('Public forms and helpers use standard Vietnamese typographic curly quotes', () => {
    const correction = doc('pages/yeu-cau/sua-thong-tin.vue')
    expect(correction).toContain('“Báo thông tin chưa đúng”')
    expect(correction).not.toContain('«Báo thông tin chưa đúng»')

    const assisted = doc('components/admin/cases/AssistedCorrectionForm.vue')
    expect(assisted).toContain('“chỉ dùng để xử lý yêu cầu sửa”')
    expect(assisted).not.toContain('«chỉ dùng để xử lý yêu cầu sửa»')
  })

  it('Itinerary detail page has BreadcrumbList JSON-LD, vector transport modes, safeJsonLd, and Twitter card', () => {
    const itinerary = doc('pages/lich-trinh/[id].vue')
    expect(itinerary).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(itinerary).toContain("icon: 'car'")
    expect(itinerary).toContain("icon: 'bike'")
    expect(itinerary).toContain("icon: 'foot'")
    expect(itinerary).not.toContain("icon: '🚗'")
    expect(itinerary).toContain('<IconLine name="bulb" class="tnc-icon"')
    expect(itinerary).toContain('<IconLine name="arrow-right" class="rl-arrow"')
    expect(itinerary).toContain("twitterCard: 'summary_large_image'")
    expect(itinerary).toContain("ogUrl: () => itineraryUrl(String(it.id || id))")
    expect(itinerary).toContain('safeJsonLd(ld)')
  })

  it('Post detail page has BreadcrumbList JSON-LD, IconLine replies-icon, ogType article, and Twitter card', () => {
    const post = doc('pages/bai-viet/[id].vue')
    expect(post).toContain('<Breadcrumb :items="breadcrumbItems" :json-ld="true" />')
    expect(post).toContain('<IconLine name="message" class="replies-icon"')
    expect(post).not.toContain('svg class="replies-icon"')
    expect(post).toContain("ogType: 'article'")
    expect(post).toContain("twitterCard: 'summary_large_image'")
    expect(post).toContain("ogUrl: () => canonicalUrl(postPath(postId.value))")
    expect(post).toContain('safeJsonLd(articleLd)')
  })

  it('Ward detail page has BreadcrumbList JSON-LD, AdministrativeArea schema with hasMap, and Twitter card', () => {
    const ward = doc('pages/xa-phuong/[id].vue')
    expect(ward).toContain('<Breadcrumb :items="breadcrumbItems" :json-ld="true">')
    expect(ward).toContain("twitterCard: 'summary_large_image'")
    expect(ward).toContain("'@type': 'AdministrativeArea'")
    expect(ward).toContain('schema.hasMap = `https://www.google.com/maps/search/?api=1&query=${c[0]},${c[1]}`')
  })

  it('OCOP hub has BreadcrumbList JSON-LD, Twitter card, safeJsonLd, and no duplicate BreadcrumbList schema', () => {
    const ocop = doc('pages/ocop.vue')
    expect(ocop).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(ocop).toContain("twitterCard: 'summary_large_image'")
    expect(ocop).toContain("ogUrl: () => canonicalUrl('/ocop')")
    expect(ocop).toContain('safeJsonLd({')
    expect(ocop).not.toContain("'@type': 'BreadcrumbList',\n        itemListElement: [")
  })

  it('Regional hub has BreadcrumbList JSON-LD, AdministrativeArea schema, vector cross-links, safeJsonLd, and Twitter card', () => {
    const area = doc('pages/khu-vuc/[area].vue')
    expect(area).toContain('<Breadcrumb :items="breadcrumbItems" :json-ld="true" />')
    expect(area).toContain("twitterCard: 'summary_large_image'")
    expect(area).toContain("ogUrl: canonicalUrl(`/khu-vuc/${areaKey}`)")
    expect(area).toContain("'@type': 'AdministrativeArea'")
    expect(area).toContain('safeJsonLd({')
    expect(area).not.toContain("'@type': 'BreadcrumbList'")
    expect(area).toContain('<IconLine name="sprout" />')
    expect(area).toContain('<IconLine name="fruit" />')
    expect(area).toContain('<IconLine name="home" />')
    expect(area).not.toContain('ogTitle: `${areaMeta.emoji}')
  })

  it('Tourism hub has BreadcrumbList JSON-LD, CollectionPage schema, safeJsonLd, and no duplicate BreadcrumbList schema', () => {
    const tourism = doc('pages/du-lich.vue')
    expect(tourism).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(tourism).toContain("twitterCard: 'summary_large_image'")
    expect(tourism).toContain("ogUrl: canonicalUrl('/du-lich')")
    expect(tourism).toContain("'@type': 'CollectionPage'")
    expect(tourism).toContain('safeJsonLd({')
    expect(tourism).not.toContain("'@type': 'BreadcrumbList'")
  })

  it('Product hub has BreadcrumbList JSON-LD, vector arrow, safeJsonLd, reduced-motion guard, and no duplicate BreadcrumbList schema', () => {
    const product = doc('pages/san-pham.vue')
    expect(product).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(product).toContain("twitterCard: 'summary_large_image'")
    expect(product).toContain("ogUrl: canonicalUrl('/san-pham')")
    expect(product).toContain('<IconLine name="arrow-right" class="ocop-teaser-arrow"')
    expect(product).not.toContain('<span class="ocop-teaser-arrow" aria-hidden="true">→</span>')
    expect(product).toContain('safeJsonLd({')
    expect(product).not.toContain("'@type': 'BreadcrumbList'")
    expect(product).toContain('.seasonal-banner-live .seasonal-banner-icon { animation: none; }')
  })

  it('Festival hub has BreadcrumbList JSON-LD, safeJsonLd festivalListSchema, Twitter card, and no duplicate BreadcrumbList schema', () => {
    const festival = doc('pages/le-hoi.vue')
    expect(festival).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(festival).toContain("twitterCard: 'summary_large_image'")
    expect(festival).toContain("ogUrl: canonicalUrl('/le-hoi')")
    expect(festival).toContain('safeJsonLd({')
    expect(festival).not.toContain("'@type': 'BreadcrumbList'")
  })

  it('Seasonal hub has BreadcrumbList JSON-LD, CollectionPage schema, safeJsonLd, and no duplicate BreadcrumbList schema', () => {
    const season = doc('pages/theo-mua.vue')
    expect(season).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(season).toContain("twitterCard: 'summary_large_image'")
    expect(season).toContain("ogUrl: canonicalUrl('/theo-mua')")
    expect(season).toContain('safeJsonLd({')
    expect(season).not.toContain("'@type': 'BreadcrumbList'")
  })

  it('Place directory hub has clean loadMoreLabel, safeJsonLd CollectionPage schema, Twitter card, and arrow-down vector', () => {
    const directory = doc('pages/dia-diem/index.vue')
    expect(directory).toContain("twitterCard: 'summary_large_image'")
    expect(directory).toContain("ogUrl: canonicalUrl('/dia-diem')")
    expect(directory).toContain('safeJsonLd({')
    expect(directory).toContain('<IconLine v-if="!loadingMore" name="arrow-down" class="dd-more-icon"')
    expect(directory).not.toContain('kể cả gần ${teaseName} →')
  })

  it('Home community section uses IconLine vector arrows with hover transition instead of raw unicode glyphs', () => {
    const home = doc('pages/index.vue')
    expect(home).toContain('<IconLine name="arrow-right" class="inline-arrow"')
    expect(home).not.toContain('Đọc thêm chuyện người đi trước →')
    expect(home).not.toContain('Xem thành viên tích cực →')
  })

  it('Guide page uses IconLine chevron-down, arrow-right, and bulb/message icons instead of raw unicode glyphs and emojis', () => {
    const guide = doc('pages/huong-dan.vue')
    expect(guide).toContain('<IconLine name="chevron-down" class="topic-chevron"')
    expect(guide).not.toContain('<span class="topic-chevron" aria-hidden="true">▾</span>')
    expect(guide).toContain('<IconLine name="arrow-right" class="topic-link-icon"')
    expect(guide).not.toContain("{{ t.linkLabel || 'Đi tới trang' }} →")
    expect(guide).toContain('<IconLine name="bulb" class="callout-icon"')
    expect(guide).toContain('<IconLine name="message" class="inline-chat-icon"')
  })
})

