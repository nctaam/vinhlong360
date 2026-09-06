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
      'pages/bang-xep-hang.vue',
      'pages/gioi-thieu.vue',
      'pages/lien-he.vue',
      'pages/da-luu.vue',
      'pages/cai-dat.vue',
      'pages/tai-khoan.vue',
      'pages/lich-trinh/index.vue',
      'pages/lich-van-nien.vue',
      'pages/chinh-sach-bao-mat.vue',
      'pages/dieu-khoan-su-dung.vue',
      'pages/huong-dan-thanh-vien.vue',
      'pages/thong-bao.vue',
      'pages/tao-lich-trinh.vue',
      'pages/yeu-cau/sua-thong-tin.vue',
      'pages/yeu-cau/tra-cuu.vue',
      'pages/yeu-cau/trang-thai.vue',
      'pages/nguoi-dung/[id].vue',
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
    const seoHelpers = doc('composables/useSeoHelpers.ts')
    expect(detail).toContain("twitterCard: 'summary_large_image'")
    expect(detail).toContain("ogUrl: () => entity.value ? entityDetailUrl(entity.value.id) : canonicalUrl('/dia-diem')")
    expect(detail).toContain('buildEntityDetailSchemaGraph')
    expect(seoHelpers).toContain("ld.hasMap = `https://www.google.com/maps/search/?api=1&query=${geoCoords[0]},${geoCoords[1]}`")
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
    expect(itinerary).toContain('<IconLine name="plus"')
    expect(itinerary).not.toContain('+ Tự tạo lịch trình')
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
    expect(post).toContain("p.post_type === 'question'")
    expect(post).toContain("'@type': 'QAPage'")
    expect(post).toContain("'@type': 'Question'")
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

  it('Directory hub has BreadcrumbList JSON-LD, CollectionPage schema, vector arrow, and Twitter card', () => {
    const danhba = doc('pages/danh-ba.vue')
    expect(danhba).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(danhba).toContain('<IconLine name="arrow-right" class="danhba-arrow"')
    expect(danhba).not.toContain('(du lịch · lưu trú · đặc sản) →')
    expect(danhba).toContain("'@type': 'CollectionPage'")
    expect(danhba).toContain('safeJsonLd(directorySchema.value)')
    expect(danhba).toContain("ogUrl: () => canonicalUrl('/danh-ba')")
    expect(danhba).toContain("twitterCard: 'summary_large_image'")
  })

  it('Leaderboard hub has BreadcrumbList JSON-LD, CollectionPage schema, Twitter card, and no duplicate breadcrumbs', () => {
    const leaderboard = doc('pages/bang-xep-hang.vue')
    expect(leaderboard).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(leaderboard).toContain("'@type': 'CollectionPage'")
    expect(leaderboard).toContain('safeJsonLd(leaderboardSchema.value)')
    expect(leaderboard).not.toContain("'@type': 'BreadcrumbList'")
    expect(leaderboard).toContain("ogUrl: () => canonicalUrl('/bang-xep-hang')")
    expect(leaderboard).toContain("twitterCard: 'summary_large_image'")
  })

  it('Private and account hubs guard crawl budget with noindex, nofollow and use vector checkmarks', () => {
    const saved = doc('pages/da-luu.vue')
    expect(saved).toContain("robots: 'noindex, nofollow'")
    expect(saved).toContain("twitterCard: 'summary_large_image'")
    expect(saved).toContain("ogUrl: () => canonicalUrl('/da-luu')")

    const settings = doc('pages/cai-dat.vue')
    expect(settings).toContain("robots: 'noindex, nofollow'")
    expect(settings).toContain("twitterCard: 'summary_large_image'")
    expect(settings).toContain("ogUrl: () => canonicalUrl('/cai-dat')")

    const account = doc('pages/tai-khoan.vue')
    expect(account).toContain("robots: 'noindex, nofollow'")
    expect(account).toContain("twitterCard: 'summary_large_image'")
    expect(account).toContain("ogUrl: () => canonicalUrl('/tai-khoan')")
    expect(account).toContain('<IconLine v-if="item.done" name="check" class="cp-check-icon"')
    expect(account).toContain('<span v-else class="cp-check-dot"')
    expect(account).not.toContain("item.done ? '✓' : '•'")
  })

  it('About and Contact hubs have safeJsonLd schema, Twitter cards, vector icons, and no duplicate breadcrumbs', () => {
    const about = doc('pages/gioi-thieu.vue')
    expect(about).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(about).toContain("'@type': 'AboutPage'")
    expect(about).toContain('safeJsonLd(aboutJsonLd)')
    expect(about).not.toContain("'@type': 'BreadcrumbList'")
    expect(about).toContain("ogUrl: () => canonicalUrl('/gioi-thieu')")
    expect(about).toContain("twitterCard: 'summary_large_image'")

    const contact = doc('pages/lien-he.vue')
    expect(contact).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(contact).toContain("'@type': 'ContactPage'")
    expect(contact).toContain('safeJsonLd(contactJsonLd.value)')
    expect(contact).not.toContain("'@type': 'BreadcrumbList'")
    expect(contact).toContain("ogUrl: () => canonicalUrl('/lien-he')")
    expect(contact).toContain("twitterCard: 'summary_large_image'")
    expect(contact).toContain('<IconLine name="tag"')
    expect(contact).toContain('<IconLine name="pencil"')
    expect(contact).toContain('<IconLine name="message"')
    expect(contact).toContain('<IconLine name="users"')
    expect(contact).toContain('<IconLine name="flag"')
    expect(contact).toContain('<IconLine name="shield-check"')
    expect(contact).not.toContain('card-icon-glyph')
  })

  it('Modals, search, and admin eliminate raw times, arrows, and chevron glyphs', () => {
    const sidebar = doc('components/community/CommunitySidebar.vue')
    expect(sidebar).toContain('<IconLine name="arrow-right" class="sidebar-more-arrow"')
    expect(sidebar).not.toContain('Xem quy tắc cộng đồng →')
    expect(sidebar).not.toContain('Xem bảng xếp hạng →')

    const reportModal = doc('components/ReportModal.vue')
    expect(reportModal).toContain('<IconLine name="x"')
    expect(reportModal).not.toContain('&times;')

    const lightbox = doc('components/ImageLightbox.vue')
    expect(lightbox).toContain('<IconLine name="x"')
    expect(lightbox).not.toContain('&times;')
    expect(lightbox).not.toContain('&#8249;')
    expect(lightbox).not.toContain('&#8250;')

    const onboarding = doc('components/OnboardingSheet.vue')
    expect(onboarding).toContain('<IconLine name="x"')
    expect(onboarding).not.toContain('&times;')

    const commSearch = doc('components/community/CommunitySearchSection.vue')
    expect(commSearch).toContain('<IconLine name="x"')
    expect(commSearch).not.toContain('&times;')

    const adminSettings = doc('components/admin/SettingsPage.vue')
    expect(adminSettings).toContain('<IconLine name="arrow-left" class="cs-back-icon"')
    expect(adminSettings).not.toContain('← Cài đặt')

    const adminRoutes = doc('pages/admin/cai-dat/tuyen-duong.vue')
    expect(adminRoutes).toContain('<IconLine name="arrow-up" class="cs-view-icon"')
    expect(adminRoutes).not.toContain('>↗<')

    const adminEntities = doc('pages/admin/entities.vue')
    expect(adminEntities).not.toContain('&times;')
    expect(adminEntities).not.toContain('&#10003;')
    expect(adminEntities).not.toContain('&rarr;')

    const adminLogs = doc('pages/admin/nhat-ky.vue')
    expect(adminLogs).not.toContain('&larr;')
    expect(adminLogs).not.toContain('&rarr;')
  })

  it('OCOP hub uses vector see-all-arrow and eliminates raw unicode arrows in section links', () => {
    const ocop = doc('pages/ocop.vue')
    expect(ocop).toContain('<IconLine name="arrow-right" class="see-all-arrow"')
    expect(ocop).not.toContain('Xem tất cả →')
  })

  it('Seasonal hub uses vector icons for B2B callout, calendar, and cross-links without raw emojis', () => {
    const season = doc('pages/theo-mua.vue')
    expect(season).toContain('<IconLine name="users"')
    expect(season).toContain('<IconLine name="arrow-right" class="b2b-arrow"')
    expect(season).toContain('<IconLine name="calendar" class="season-when-icon"')
    expect(season).toContain('<IconLine name="fruit"')
    expect(season).toContain('<IconLine name="star"')
    expect(season).toContain('<IconLine name="leaf"')
    expect(season).toContain('<IconLine name="bowl"')
    expect(season).not.toContain('b2b-callout-icon">🤝')
    expect(season).not.toContain('b2b-callout-link">Liên hệ hợp tác →')
  })

  it('Itinerary index hub has CollectionPage schema with safeJsonLd, IconLine plus, vector cross-links, and no duplicate breadcrumbs', () => {
    const itinerary = doc('pages/lich-trinh/index.vue')
    expect(itinerary).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(itinerary).toContain('<IconLine name="plus"')
    expect(itinerary).not.toContain('+ Tự tạo lịch trình')
    expect(itinerary).toContain('<IconLine name="leaf"')
    expect(itinerary).toContain('<IconLine name="home"')
    expect(itinerary).toContain('<IconLine name="map"')
    expect(itinerary).toContain('<IconLine name="fruit"')
    expect(itinerary).toContain("'@type': 'CollectionPage'")
    expect(itinerary).toContain('safeJsonLd(itineraryCollectionSchema.value)')
    expect(itinerary).not.toContain("'@type': 'BreadcrumbList'")
    expect(itinerary).toContain("ogUrl: () => canonicalUrl('/lich-trinh')")
    expect(itinerary).toContain("twitterCard: 'summary_large_image'")
  })

  it('Perpetual calendar hub has WebApplication schema with safeJsonLd, arrow-right vector, and no duplicate breadcrumbs', () => {
    const lvn = doc('pages/lich-van-nien.vue')
    expect(lvn).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(lvn).toContain('data-lvn-next')
    expect(lvn).toContain('name="arrow-right"')
    expect(lvn).not.toContain('transform: rotate(180deg)')
    expect(lvn).toContain("'@type': 'WebApplication'")
    expect(lvn).toContain('safeJsonLd(lvnSchema.value)')
    expect(lvn).not.toContain("'@type': 'BreadcrumbList'")
    expect(lvn).toContain("ogUrl: () => canonicalUrl('/lich-van-nien')")
    expect(lvn).toContain("twitterCard: 'summary_large_image'")
  })

  it('Privacy and Terms hubs have WebPage schema with safeJsonLd, Twitter card, and no duplicate breadcrumbs', () => {
    const privacy = doc('pages/chinh-sach-bao-mat.vue')
    expect(privacy).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(privacy).toContain("'@type': 'WebPage'")
    expect(privacy).toContain('safeJsonLd(privacySchema.value)')
    expect(privacy).not.toContain("'@type': 'BreadcrumbList'")
    expect(privacy).toContain("ogUrl: () => canonicalUrl('/chinh-sach-bao-mat')")
    expect(privacy).toContain("twitterCard: 'summary_large_image'")

    const terms = doc('pages/dieu-khoan-su-dung.vue')
    expect(terms).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(terms).toContain("'@type': 'WebPage'")
    expect(terms).toContain('safeJsonLd(termsSchema.value)')
    expect(terms).not.toContain("'@type': 'BreadcrumbList'")
    expect(terms).toContain("ogUrl: () => canonicalUrl('/dieu-khoan-su-dung')")
    expect(terms).toContain("twitterCard: 'summary_large_image'")
  })

  it('Member guide hub has WebPage schema with safeJsonLd, vector award hero, vector categories/badges, and no duplicate breadcrumbs', () => {
    const guide = doc('pages/huong-dan-thanh-vien.vue')
    expect(guide).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(guide).toContain('<span class="guide-hero-icon" aria-hidden="true"><IconLine name="award" /></span>')
    expect(guide).toContain("icon: 'sprout'")
    expect(guide).toContain("icon: 'users'")
    expect(guide).toContain("icon: 'star'")
    expect(guide).toContain("icon: 'pencil'")
    expect(guide).toContain("icon: 'file-text'")
    expect(guide).toContain("icon: 'camera'")
    expect(guide).toContain("icon: 'pin'")
    expect(guide).toContain("icon: 'heart'")
    expect(guide).toContain("icon: 'trophy'")
    expect(guide).toContain("'@type': 'WebPage'")
    expect(guide).toContain('safeJsonLd(guideSchema.value)')
    expect(guide).not.toContain("'@type': 'BreadcrumbList'")
    expect(guide).toContain("ogUrl: () => canonicalUrl('/huong-dan-thanh-vien')")
    expect(guide).toContain("twitterCard: 'summary_large_image'")
  })

  it('Notification hub guards crawl budget with noindex, uses vector icons in filters and item chips', () => {
    const notif = doc('pages/thong-bao.vue')
    expect(notif).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(notif).toContain("robots: 'noindex, nofollow'")
    expect(notif).toContain("ogUrl: () => canonicalUrl('/thong-bao')")
    expect(notif).toContain("twitterCard: 'summary_large_image'")
    expect(notif).toContain("<IconLine :name=\"f.icon\" class=\"tb-filter-icon\" />")
    expect(notif).toContain("<span class=\"tb-icon-chip\" aria-hidden=\"true\"><IconLine :name=\"icon(n)\" /></span>")
    expect(notif).not.toContain("{{ f.icon }} {{ f.label }}")
  })

  it('Itinerary planner guards crawl budget with noindex, has WebApplication schema, and vector plus icon', () => {
    const planner = doc('pages/tao-lich-trinh.vue')
    expect(planner).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(planner).toContain("robots: 'noindex, nofollow'")
    expect(planner).toContain("ogUrl: () => canonicalUrl('/tao-lich-trinh')")
    expect(planner).toContain("twitterCard: 'summary_large_image'")
    expect(planner).toContain("'@type': 'WebApplication'")
    expect(planner).toContain('safeJsonLd(plannerSchema.value)')
    expect(planner).toContain('<span class="btn btn-sm btn-ghost" aria-hidden="true"><IconLine name="plus" /></span>')
    expect(planner).not.toContain('<span class="btn btn-sm btn-ghost" aria-hidden="true">+</span>')
  })

  it('Correction intake and status hubs guard crawl budget with noindex and enable json-ld on Breadcrumb', () => {
    const intake = doc('pages/yeu-cau/sua-thong-tin.vue')
    expect(intake).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(intake).toContain("robots: 'noindex, nofollow'")
    expect(intake).toContain("ogUrl: () => canonicalUrl('/yeu-cau/sua-thong-tin')")
    expect(intake).toContain("twitterCard: 'summary_large_image'")

    const lookup = doc('pages/yeu-cau/tra-cuu.vue')
    expect(lookup).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(lookup).toContain("robots: 'noindex, nofollow'")
    expect(lookup).toContain("ogUrl: () => canonicalUrl('/yeu-cau/tra-cuu')")
    expect(lookup).toContain("twitterCard: 'summary_large_image'")

    const status = doc('pages/yeu-cau/trang-thai.vue')
    expect(status).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(status).toContain("robots: 'noindex, nofollow'")
    expect(status).toContain("ogUrl: () => canonicalUrl('/yeu-cau/trang-thai')")
    expect(status).toContain("twitterCard: 'summary_large_image'")
  })

  it('User profile hub has dynamic robots guarding private profiles, ProfilePage schema, and vector icons', () => {
    const profile = doc('pages/nguoi-dung/[id].vue')
    expect(profile).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(profile).toContain("robots: () => (profile.value?.is_private || profileNotFound.value) ? 'noindex, nofollow' : 'index, follow'")
    expect(profile).toContain("ogUrl: () => canonicalUrl(publicProfilePath.value)")
    expect(profile).toContain("twitterCard: 'summary_large_image'")
    expect(profile).toContain("'@type': 'ProfilePage'")
    expect(profile).toContain('safeJsonLd(profileSchema.value)')
    expect(profile).toContain('<IconLine name="more-horizontal" />')
    expect(profile).not.toContain('&#8226;&#8226;&#8226;')
    expect(profile).toContain('<IconLine name="pencil" class="icon-inline" /> Sửa hồ sơ')
    expect(profile).toContain('<IconLine name="share" />')
  })

  it('Accommodation and Events hubs have ogUrl, twitterCard, and clean vector icons without raw emojis', () => {
    const luuTru = doc('pages/luu-tru.vue')
    expect(luuTru).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(luuTru).toContain("ogUrl: () => canonicalUrl('/luu-tru')")
    expect(luuTru).toContain("twitterCard: 'summary_large_image'")
    expect(luuTru).toContain('<span class="rw-motif" :class="`rw-${key}`" aria-hidden="true"><IconLine :name="meta.icon || \'pin\'" /></span>')
    expect(luuTru).not.toContain('<span class="rw-motif" :class="`rw-${key}`" aria-hidden="true">{{ meta.emoji }}</span>')

    const suKien = doc('pages/su-kien.vue')
    expect(suKien).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(suKien).toContain("ogUrl: () => canonicalUrl('/su-kien')")
    expect(suKien).toContain("twitterCard: 'summary_large_image'")
    expect(suKien).toContain('<span class="quick-pick-icon"><IconLine :name="meta.icon || \'pin\'" /></span>')
    expect(suKien).not.toContain('<span class="quick-pick-icon">{{ meta.emoji }}</span>')
    expect(suKien).toContain('<IconLine name="lantern" />')
    expect(suKien).toContain('<IconLine name="leaf" />')
    expect(suKien).toContain('<IconLine name="calendar" />')
    expect(suKien).toContain('<IconLine name="map" />')
    expect(suKien).not.toContain('<span class="cross-icon" aria-hidden="true">🗓️</span>')
  })

  it('Routes hub has ogUrl, twitterCard, routeIcon vector rendering, and clean area chips', () => {
    const routes = doc('pages/tuyen-duong.vue')
    expect(routes).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(routes).toContain("ogUrl: () => canonicalUrl('/tuyen-duong')")
    expect(routes).toContain("twitterCard: 'summary_large_image'")
    expect(routes).toContain('<span class="route-emoji" aria-hidden="true"><IconLine :name="routeIcon(r)" /></span>')
    expect(routes).not.toContain('<span class="route-emoji">{{ r.emoji }}</span>')
    expect(routes).toContain('<IconLine :name="meta.icon || \'pin\'" class="chip-area-icon" /> {{ meta.name }}')
  })

  it('Error, 403, and fallback 404 routes strictly guard crawl budget with noindex and provide empathetic discovery vectors', () => {
    const p403 = doc('pages/403.vue')
    expect(p403).toContain("robots: 'noindex, nofollow'")
    expect(p403).toContain("ogTitle: 'Không đủ quyền truy cập — vinhlong360'")
    expect(p403).toContain("twitterCard: 'summary_large_image'")

    const fallback404 = doc('pages/[...slug].vue')
    expect(fallback404).toContain("robots: 'noindex, nofollow'")
    expect(fallback404).toContain("twitterCard: 'summary_large_image'")
    expect(fallback404).toContain('discoveryLinks')
    expect(fallback404).toContain('<IconLine :name="item.icon" class="nf-pill__icon" />')
    expect(fallback404).not.toContain('→')

    const errorPage = doc('error.vue')
    expect(errorPage).toContain("robots: 'noindex, nofollow'")
    expect(errorPage).toContain("twitterCard: 'summary_large_image'")
    expect(errorPage).toContain('<IconLine v-if="l.icon" :name="l.icon" class="error-link-pill__icon" />')
    expect(errorPage).not.toContain('🌿')
  })

  it('Shared itinerary hub and HomeProductLead feature clean vector arrows, Breadcrumb JSON-LD, and TouristTrip Schema.org', () => {
    const productLead = doc('components/home/HomeProductLead.vue')
    expect(productLead).toContain('<IconLine name="arrow-right" class="home-product-lead__arrow" aria-hidden="true" />')
    expect(productLead).not.toContain('<span class="home-product-lead__arrow" aria-hidden="true">→</span>')

    const sharedPlan = doc('pages/lich-trinh-chia-se/[id].vue')
    expect(sharedPlan).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    expect(sharedPlan).toContain("ogUrl: () => canonicalUrl(`/lich-trinh-chia-se/${encodedPlanId}`)")
    expect(sharedPlan).toContain("twitterCard: 'summary_large_image'")
    expect(sharedPlan).toContain("'@type': 'ItemPage'")
    expect(sharedPlan).toContain("'@type': 'TouristTrip'")
    expect(sharedPlan).toContain('safeJsonLd(s)')
    expect(sharedPlan).toContain('copyShareLink')
    expect(sharedPlan).not.toContain('--on-primary')
    expect(sharedPlan).not.toContain('--ink-700')
    expect(sharedPlan).not.toContain('--ink-900')
  })

  it('Admin shell layout protects all admin pages with noindex; account hub uses vector icons and authFetch without legacy ink-700', () => {
    const adminLayout = doc('layouts/admin.vue')
    expect(adminLayout).toContain("robots: 'noindex, nofollow'")

    const account = doc('pages/tai-khoan.vue')
    expect(account).toContain("robots: 'noindex, nofollow'")
    expect(account).toContain('authFetch')
    expect(account).toContain('<IconLine :name="item.icon" />')
    expect(account).toContain('<IconLine :name="actionIcon(a.action)" />')
    expect(account).not.toContain("post: '✍️'")
    expect(account).not.toContain("like: '❤️'")
    expect(account).not.toContain("icon: '🔒'")
    expect(account).not.toContain('--ink-700')
  })

  it('Saved items, map, search, community, and home hubs strictly enforce safeJsonLd, ogUrl, and authFetch', () => {
    const saved = doc('pages/da-luu.vue')
    expect(saved).toContain("robots: 'noindex, nofollow'")
    expect(saved).toContain('authFetch')
    expect(saved).not.toContain('--ink-700')

    const map = doc('pages/ban-do.vue')
    expect(map).toContain('safeJsonLd({')
    expect(map).toContain("ogUrl: () => canonicalUrl('/ban-do')")
    expect(map).toContain("twitterCard: 'summary_large_image'")

    const community = doc('pages/cong-dong.vue')
    expect(community).toContain('safeJsonLd({')
    expect(community).toContain("ogUrl: () => canonicalUrl('/cong-dong')")
    expect(community).toContain("twitterCard: 'summary_large_image'")

    const search = doc('pages/tim-kiem.vue')
    expect(search).toContain('safeJsonLd({')
    expect(search).toContain("ogUrl: () => canonicalUrl('/tim-kiem')")
    expect(search).toContain("twitterCard: 'summary_large_image'")

    const home = doc('pages/index.vue')
    expect(home).toContain('safeJsonLd({')
    expect(home).not.toContain('innerHTML: JSON.stringify({')

    const planner = doc('pages/tao-lich-trinh.vue')
    const plannerLines = planner.split('\n').length
    expect(plannerLines).toBeLessThan(1500)
  })
})


