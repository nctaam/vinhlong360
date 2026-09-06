import type { ImageDescriptor } from '../types/image'
import { normalizeRenderableImageUrl } from '../utils/imageDescriptors'

export const SITE_URL = 'https://vinhlong360.vn'
const DEFAULT_OG = `${SITE_URL}/img/og-default.jpg`

export interface ImageMeta {
  ogImage?: string
  ogImageAlt?: string
  twitterImage?: string
  twitterImageAlt?: string
}

function absoluteMetadataImageUrl(descriptor?: ImageDescriptor | null): string | null {
  if (!descriptor?.url || descriptor.source_class === 'placeholder') return null
  const normalized = normalizeRenderableImageUrl(descriptor.url)
  if (!normalized) return null
  return normalized.startsWith('/') ? `${SITE_URL}${normalized}` : normalized
}

export function appendImageDisclosureToShareText(
  text: string,
  descriptor?: ImageDescriptor | null,
): string {
  return descriptor?.url ? `${text}\n\n${descriptor.full_disclosure}` : text
}

export function buildImageMeta(descriptor?: ImageDescriptor | null): ImageMeta {
  const url = absoluteMetadataImageUrl(descriptor)
  if (!url || !descriptor) return {}
  const alt = `${descriptor.alt} — ${descriptor.full_disclosure}`
  return {
    ogImage: url,
    ogImageAlt: alt,
    twitterImage: url,
    twitterImageAlt: alt,
  }
}

export function descriptorToImageObject(descriptor?: ImageDescriptor | null) {
  const contentUrl = absoluteMetadataImageUrl(descriptor)
  if (!contentUrl || !descriptor || descriptor.source_class === 'placeholder') return null
  return {
    '@type': 'ImageObject',
    contentUrl,
    caption: descriptor.full_disclosure,
    description: `${descriptor.alt} — ${descriptor.full_disclosure}`,
  }
}

/** @deprecated Non-entity compatibility only; entity metadata must use ImageDescriptor helpers. */
export function entityOgImage(images?: string[] | null, fallback = DEFAULT_OG): string {
  if (Array.isArray(images) && images.length && images[0]) {
    const src = images[0]
    return src.startsWith('http') ? src : `${SITE_URL}${src.startsWith('/') ? '' : '/'}${src}`
  }
  return fallback
}

/** Profile cover/avatar metadata is intentionally separate from entity media. */
export function profileOgImage(images?: string[] | null, fallback = DEFAULT_OG): string {
  return entityOgImage(images, fallback)
}

export function safeJsonLd(obj: unknown): string {
  return JSON.stringify(obj).replace(/<\//g, '<\\/')
}

export function canonicalUrl(path = '/') {
  const clean = path.split('#')[0]?.split('?')[0] || '/'
  const normalized = clean.startsWith('/') ? clean : `/${clean}`
  return `${SITE_URL}${normalized === '/' ? '' : normalized}`
}

export function entityDetailUrl(id: string) {
  return canonicalUrl(`/dia-diem/${encodeURIComponent(id)}`)
}

export function itineraryUrl(id: string) {
  return canonicalUrl(`/lich-trinh/${encodeURIComponent(id)}`)
}

interface ListableItem {
  id?: string
  name?: string
  title?: string
}

export function itemListJsonLd(name: string, description: string, path: string, items: ListableItem[] = []) {
  return {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name,
    description,
    url: canonicalUrl(path),
    mainEntity: {
      '@type': 'ItemList',
      itemListElement: items.slice(0, 24).map((item, index) => ({
        '@type': 'ListItem',
        position: index + 1,
        name: item.name || item.title || item.id,
        url: item.id ? entityDetailUrl(String(item.id)) : undefined,
      })).map((item) => Object.fromEntries(Object.entries(item).filter(([, value]) => value !== undefined))),
    },
  }
}

export function itineraryItemListJsonLd(name: string, description: string, path: string, items: ListableItem[] = []) {
  return {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name,
    description,
    url: canonicalUrl(path),
    mainEntity: {
      '@type': 'ItemList',
      itemListElement: items.slice(0, 24).map((item, index) => ({
        '@type': 'ListItem',
        position: index + 1,
        name: item.title || item.name || item.id,
        url: item.id ? itineraryUrl(String(item.id)) : undefined,
      })).map((item) => Object.fromEntries(Object.entries(item).filter(([, value]) => value !== undefined))),
    },
  }
}

export interface FaqItem {
  q: string
  a: string
}

export function buildFaqPageSchema(faqItems: FaqItem[], id?: string): Record<string, any> | null {
  if (!Array.isArray(faqItems) || faqItems.length === 0) return null
  return {
    '@type': 'FAQPage',
    ...(id ? { '@id': id } : {}),
    mainEntity: faqItems.map((f) => ({
      '@type': 'Question',
      name: f.q,
      acceptedAnswer: {
        '@type': 'Answer',
        text: f.a,
      },
    })),
  }
}

export function buildSpeakableSpecification(cssSelectors: string[] = ['.lead', 'h1', '.desc-heading']): Record<string, any> {
  return {
    '@type': 'SpeakableSpecification',
    cssSelector: cssSelectors,
  }
}

export function buildWebSiteSchema(): Record<string, any> {
  return {
    '@type': 'WebSite',
    '@id': `${SITE_URL}/#website`,
    url: SITE_URL,
    name: 'vinhlong360',
    description: 'Cổng du lịch và sản phẩm địa phương Vĩnh Long.',
    inLanguage: 'vi-VN',
    publisher: { '@id': `${SITE_URL}/#organization` },
  }
}

export function buildOrganizationSchema(): Record<string, any> {
  return {
    '@type': 'Organization',
    '@id': `${SITE_URL}/#organization`,
    name: 'vinhlong360',
    url: SITE_URL,
    logo: `${SITE_URL}/icons/icon-512.png`,
    description: 'Cổng du lịch và sản phẩm địa phương Vĩnh Long.',
    inLanguage: 'vi-VN',
    areaServed: {
      '@type': 'AdministrativeArea',
      name: 'Tỉnh Vĩnh Long',
      '@id': `${SITE_URL}/#province`,
    },
    knowsAbout: [
      'Du lịch Vĩnh Long',
      'Văn hóa Khmer',
      'Đặc sản OCOP Vĩnh Long',
      'Làng nghề gốm Mang Thít',
      'Cù lao An Bình',
      'Lễ hội truyền thống Vĩnh Long',
    ],
  }
}

export function buildUnifiedSchemaGraph(nodes: Array<Record<string, any> | null | undefined>): Record<string, any> {
  return {
    '@context': 'https://schema.org',
    '@graph': nodes.filter(Boolean),
  }
}

import { normalizeCoords } from './useCoords'
import { ocopBadgeLabel } from '../utils/ocop'

export const TYPE_TO_SCHEMA: Record<string, string> = {
  product: 'Product',
  accommodation: 'LodgingBusiness',
  dish: 'FoodEstablishment',
  craft_village: 'LocalBusiness',
  organization: 'LocalBusiness',
  attraction: 'TouristAttraction',
  experience: 'TouristAttraction',
  event: 'Event',
  place: 'Place',
}

export interface EntityDetailSchemaOptions {
  entity: any
  typeLabel?: string
  areaName?: string
  adminUnitBreadcrumb?: { label: string; to?: string } | null
  heroDescriptor?: ImageDescriptor | null
  typeBreadcrumbUrl?: string
}

export function buildEntityDetailSchemaGraph(options: EntityDetailSchemaOptions): Record<string, any> | null {
  const e = options.entity
  if (!e) return null

  const ldType = TYPE_TO_SCHEMA[e.type] || 'TouristAttraction'
  const entityUrl = entityDetailUrl(e.id)
  const areaName = options.areaName || ''
  const typeLabel = options.typeLabel || ''
  const typeBreadcrumbUrl = options.typeBreadcrumbUrl || '/du-lich'

  const ld: Record<string, any> = {
    '@context': 'https://schema.org',
    '@type': ldType,
    '@id': `${entityUrl}#entity`,
    name: e.name,
    description: e.description || e.summary,
    inLanguage: 'vi-VN',
    url: entityUrl,
    address: {
      '@type': 'PostalAddress',
      addressLocality: e.place_name || '',
      addressRegion: areaName,
      addressCountry: 'VN',
    },
  }

  const imageObject = descriptorToImageObject(options.heroDescriptor)
  if (imageObject) ld.image = imageObject
  if (e.attributes?.phone) ld.telephone = e.attributes.phone
  const sameAs = [e.attributes?.website, e.quality?.source_url].filter(Boolean)
  if (sameAs.length) ld.sameAs = sameAs.length === 1 ? sameAs[0] : sameAs
  if (e.quality?.source_url) {
    ld.citation = {
      '@type': 'CreativeWork',
      name: e.quality?.source_title || e.quality.source_url,
      url: e.quality.source_url,
    }
  }
  if (e.attributes?.address) ld.address.streetAddress = e.attributes.address
  const geoCoords = normalizeCoords(e.coordinates)
  if (geoCoords) {
    ld.geo = { '@type': 'GeoCoordinates', latitude: geoCoords[0], longitude: geoCoords[1] }
    ld.hasMap = `https://www.google.com/maps/search/?api=1&query=${geoCoords[0]},${geoCoords[1]}`
  }
  if (e.attributes?.hours) ld.openingHours = e.attributes.hours

  // isAccessibleForFree
  const fee = e.attributes?.fee || e.attributes?.price_range || ''
  const isFree = /miễn phí|free|không mất phí|0\s*đ/i.test(fee)
    || (e.attributes?.amenities && Array.isArray(e.attributes.amenities) && e.attributes.amenities.includes('free_entry'))
  if (isFree) ld.isAccessibleForFree = true

  // LocalBusiness/LodgingBusiness/FoodEstablishment enrichment
  if (['LocalBusiness', 'LodgingBusiness', 'FoodEstablishment'].includes(ldType)) {
    if (e.attributes?.price_range) ld.priceRange = e.attributes.price_range
  }
  if (ldType === 'LodgingBusiness') {
    if (e.attributes?.checkin) ld.checkinTime = e.attributes.checkin
    if (e.attributes?.checkout) ld.checkoutTime = e.attributes.checkout
  }

  if (ldType === 'Event') {
    if (e.attributes?.date_start) ld.startDate = e.attributes.date_start
    if (e.attributes?.date_end) ld.endDate = e.attributes.date_end
    if (e.place_name || areaName) {
      ld.location = {
        '@type': 'Place',
        name: e.place_name || areaName,
        address: { '@type': 'PostalAddress', addressRegion: areaName, addressCountry: 'VN' },
      }
      if (geoCoords) {
        ld.location.geo = { '@type': 'GeoCoordinates', latitude: geoCoords[0], longitude: geoCoords[1] }
      }
    }
    ld.eventStatus = 'https://schema.org/EventScheduled'
    ld.eventAttendanceMode = 'https://schema.org/OfflineEventAttendanceMode'
    if (isFree) {
      ld.offers = { '@type': 'Offer', price: '0', priceCurrency: 'VND', availability: 'https://schema.org/InStock' }
    }
  }

  if (ldType === 'Product') {
    if (e.attributes?.price) {
      ld.offers = {
        '@type': 'Offer',
        price: String(e.attributes.price).replace(/[^\d]/g, '') || '0',
        priceCurrency: 'VND',
        availability: 'https://schema.org/InStock',
        url: entityUrl,
      }
    }
    const ocopLabel = ocopBadgeLabel(e as any)
    if (ocopLabel) {
      ld.brand = { '@type': 'Brand', name: ocopLabel }
    }
  }

  // Geographic containment (all entity types)
  if (e.place_name) {
    ld.containedInPlace = {
      '@type': 'AdministrativeArea',
      name: e.place_name,
      ...(areaName ? { containedInPlace: { '@type': 'AdministrativeArea', name: areaName } } : {}),
    }
  }

  // BreadcrumbList
  const bcItems: any[] = [
    { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
    { '@type': 'ListItem', position: 2, name: typeLabel, item: `${SITE_URL}${typeBreadcrumbUrl}` },
  ]
  const unitCrumb = options.adminUnitBreadcrumb
  if (unitCrumb) {
    bcItems.push({
      '@type': 'ListItem',
      position: bcItems.length + 1,
      name: unitCrumb.label,
      ...(unitCrumb.to ? { item: `${SITE_URL}${unitCrumb.to}` } : {}),
    })
  }
  bcItems.push({ '@type': 'ListItem', position: bcItems.length + 1, name: e.name, item: entityUrl })

  const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    '@id': `${entityUrl}#breadcrumb`,
    itemListElement: bcItems,
  }

  // FAQPage from entity attributes
  const faqItems: FaqItem[] = []
  if (e.attributes?.hours)
    faqItems.push({ q: `${e.name} mở cửa lúc mấy giờ?`, a: `Giờ mở cửa: ${e.attributes.hours}` })
  if (e.attributes?.fee)
    faqItems.push({ q: `Phí vào ${e.name} bao nhiêu?`, a: e.attributes.fee })
  if (e.attributes?.transport)
    faqItems.push({ q: `Đi đến ${e.name} bằng cách nào?`, a: e.attributes.transport })
  if (e.attributes?.parking)
    faqItems.push({ q: `${e.name} có chỗ đậu xe không?`, a: e.attributes.parking })
  if (e.attributes?.best_time)
    faqItems.push({ q: `Thời điểm nào đẹp nhất để đến ${e.name}?`, a: e.attributes.best_time })

  const webpageNode = {
    '@type': 'WebPage',
    '@id': `${entityUrl}#webpage`,
    url: entityUrl,
    name: `${e.name} — ${typeLabel} — vinhlong360`,
    description: e.summary || e.description,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    breadcrumb: { '@id': `${entityUrl}#breadcrumb` },
    mainEntity: { '@id': `${entityUrl}#entity` },
    speakable: buildSpeakableSpecification(['.lead', '.highlights', 'h1', '.desc-heading']),
    publisher: { '@id': `${SITE_URL}/#organization` },
  }

  const faqNode = faqItems.length >= 2 ? buildFaqPageSchema(faqItems, `${entityUrl}#faq`) : null

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumb,
    ld,
    faqNode,
  ])
}

export function buildHomeSchemaGraph(): Record<string, any> {
  const webpageNode = {
    '@type': 'WebPage',
    '@id': `${SITE_URL}/#webpage`,
    url: `${SITE_URL}/`,
    name: 'vinhlong360 — Cổng Thông Tin Du Lịch & Văn Hóa Vĩnh Long',
    description: 'Cổng thông tin du lịch thông minh, đặc sản OCOP, di tích văn hóa và làng nghề truyền thống Vĩnh Long.',
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: { '@id': `${SITE_URL}/#organization` },
    speakable: buildSpeakableSpecification(['.hero-title', '.hero-dek', '.section-title', 'h1']),
  }

  const websiteNode = {
    ...buildWebSiteSchema(),
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: `${SITE_URL}/tim-kiem?q={search_term_string}`,
      },
      'query-input': 'required name=search_term_string',
    },
  }

  const catalogHubs = [
    { name: 'Điểm đến du lịch', url: `${SITE_URL}/du-lich` },
    { name: 'Khách sạn & Lưu trú', url: `${SITE_URL}/luu-tru` },
    { name: 'Sản phẩm địa phương', url: `${SITE_URL}/san-pham` },
    { name: 'Đặc sản OCOP Vĩnh Long', url: `${SITE_URL}/ocop` },
    { name: 'Lễ hội truyền thống', url: `${SITE_URL}/le-hoi` },
    { name: 'Sự kiện nổi bật', url: `${SITE_URL}/su-kien` },
    { name: 'Du lịch theo mùa Mekong', url: `${SITE_URL}/theo-mua` },
    { name: 'Tuyến đường du lịch', url: `${SITE_URL}/tuyen-duong` },
    { name: 'Bản đồ số du lịch', url: `${SITE_URL}/ban-do` },
    { name: 'Danh bạ cơ sở dịch vụ', url: `${SITE_URL}/danh-ba` },
  ]

  const itemList = {
    '@type': 'ItemList',
    '@id': `${SITE_URL}/#catalog-hubs`,
    name: 'Danh mục Khám phá Du lịch & Đặc sản Vĩnh Long',
    numberOfItems: catalogHubs.length,
    itemListElement: catalogHubs.map((hub, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: hub.name,
      url: hub.url,
    })),
  }

  const faqNode = buildFaqPageSchema([
    {
      q: 'Cổng thông tin vinhlong360 cung cấp những tiện ích du lịch gì?',
      a: 'vinhlong360 cung cấp thông tin tra cứu điểm đến, cơ sở lưu trú, sản phẩm OCOP đạt chuẩn, tuyến đường du lịch, lịch vạn niên và công cụ tạo lịch trình thông minh tại tỉnh Vĩnh Long.',
    },
    {
      q: 'Du lịch Vĩnh Long vào mùa nào đẹp nhất trong năm?',
      a: 'Vĩnh Long đẹp quanh năm với miệt vườn sông nước Mekong. Mùa trái cây rộ từ tháng 5 đến tháng 8, mùa nước nổi từ tháng 9 đến tháng 11, và mùa hoa xuân lễ hội từ tháng 12 đến tháng 2 âm lịch.',
    },
    {
      q: 'Làm thế nào để tìm mua sản phẩm OCOP chính gốc tại Vĩnh Long?',
      a: 'Du khách có thể tra cứu danh mục OCOP trên vinhlong360 để xem hạng sao (3-5 sao), địa chỉ cơ sở sản xuất đạt chuẩn, và số điện thoại liên hệ trực tiếp với chủ thể sản phẩm.',
    },
    {
      q: 'vinhlong360 có hỗ trợ lập kế hoạch và lịch trình tham quan không?',
      a: 'Có, tính năng Tạo Lịch Trình trên vinhlong360 giúp du khách gợi ý lộ trình tự động theo sở thích, số ngày lưu trú và kết nối bản đồ số thông minh.',
    },
  ], `${SITE_URL}/#faq`)

  return buildUnifiedSchemaGraph([
    websiteNode,
    buildOrganizationSchema(),
    webpageNode,
    itemList,
    faqNode,
  ])
}

