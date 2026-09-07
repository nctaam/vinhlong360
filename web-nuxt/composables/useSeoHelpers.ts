import type { ImageDescriptor } from '../types/image'
import { normalizeRenderableImageUrl } from '../utils/imageDescriptors'
import { entityPath, userPath } from '../utils/routePaths'

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
      ld.award = ocopLabel
      ld.category = 'Sản phẩm OCOP'
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
    speakable: buildSpeakableSpecification(['.lead', '.highlights', 'h1', '.desc-heading', '.detail-aeo-summary__highlight', '.detail-aeo-summary__tip']),
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

export interface HomeSchemaOptions {
  upcomingEvents?: Array<{
    id: string | number
    name: string
    attributes?: { date_start?: string; date_end?: string }
    place_name?: string
    area?: string
    place_area?: string
  }>
}

export function buildHomeSchemaGraph(options?: HomeSchemaOptions): Record<string, any> {
  const webpageNode = {
    '@type': 'WebPage',
    '@id': `${SITE_URL}/#webpage`,
    url: `${SITE_URL}/`,
    name: 'vinhlong360 — Cổng Thông Tin Du Lịch & Văn Hóa Vĩnh Long',
    description: 'Cổng thông tin du lịch thông minh, đặc sản OCOP, di tích văn hóa và làng nghề truyền thống Vĩnh Long.',
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: { '@id': `${SITE_URL}/#organization` },
    speakable: buildSpeakableSpecification(['.hero-title', '.hero-dek', '.home-aeo-plaque__title', '.home-aeo-plaque__dek', '.section-title', 'h1']),
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

  const nodes = [
    websiteNode,
    buildOrganizationSchema(),
    webpageNode,
    itemList,
    faqNode,
  ]

  if (options?.upcomingEvents && options.upcomingEvents.length > 0) {
    const eventItems = options.upcomingEvents.map((ev, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      item: {
        '@type': 'Event',
        name: ev.name,
        startDate: ev.attributes?.date_start,
        endDate: ev.attributes?.date_end || ev.attributes?.date_start,
        url: `${SITE_URL}/dia-diem/${encodeURIComponent(String(ev.id))}`,
        eventStatus: 'https://schema.org/EventScheduled',
        eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
        location: {
          '@type': 'Place',
          name: ev.place_name || 'Vĩnh Long',
          address: {
            '@type': 'PostalAddress',
            addressRegion: 'Vĩnh Long',
            addressCountry: 'VN',
          },
        },
      },
    }))
    nodes.push({
      '@type': 'ItemList',
      '@id': `${SITE_URL}/#upcoming-events`,
      name: 'Sự kiện sắp tới tại Vĩnh Long',
      numberOfItems: eventItems.length,
      itemListElement: eventItems,
    })
  }

  return buildUnifiedSchemaGraph(nodes)
}

export interface PostDetailSchemaOptions {
  post: {
    id: string | number
    display_name?: string
    content?: string
    post_type?: string
    created_at?: string
    updated_at?: string
    user_id?: string | number
    rating?: number
    comments_count?: number
  }
  bestAnswer?: {
    id?: string | number
    content?: string
    created_at?: string
    author?: { id?: string | number; display_name?: string }
  } | null
  commentsCount?: number
}

export function buildPostDetailSchemaGraph(options: PostDetailSchemaOptions): Record<string, any> {
  const p = options.post
  const postId = String(p.id)
  const postUrl = canonicalUrl(`/bai-viet/${encodeURIComponent(postId)}`)
  const postTitle = p.display_name || 'Bài viết'
  const postDesc = (p.content || '').substring(0, 160)
  const commentsCount = options.commentsCount ?? p.comments_count ?? 0

  const webpageNode = {
    '@type': p.post_type === 'question' ? 'QAPage' : 'WebPage',
    '@id': `${postUrl}#webpage`,
    url: postUrl,
    name: `${postTitle} — vinhlong360`,
    description: postDesc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    breadcrumb: { '@id': `${postUrl}#breadcrumb` },
    mainEntity: { '@id': `${postUrl}#post` },
    speakable: buildSpeakableSpecification(['.thread-detail', 'h1', '.thread-comments']),
    publisher: { '@id': `${SITE_URL}/#organization` },
  }

  const breadcrumbNode = {
    '@type': 'BreadcrumbList',
    '@id': `${postUrl}#breadcrumb`,
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Cộng đồng', item: `${SITE_URL}/cong-dong` },
      { '@type': 'ListItem', position: 3, name: postTitle, item: postUrl },
    ],
  }

  let postNode: Record<string, any>
  const authorNode = {
    '@type': 'Person',
    name: p.display_name || 'Người dùng',
    ...(p.user_id ? { url: canonicalUrl(`/nguoi-dung/${encodeURIComponent(String(p.user_id))}`) } : {}),
  }

  if (p.post_type === 'question') {
    const questionNode: Record<string, any> = {
      '@type': 'Question',
      '@id': `${postUrl}#post`,
      name: postTitle,
      text: p.content || postTitle,
      dateCreated: p.created_at,
      url: postUrl,
      answerCount: commentsCount,
      author: authorNode,
    }

    if (options.bestAnswer) {
      const ba = options.bestAnswer
      questionNode.acceptedAnswer = {
        '@type': 'Answer',
        text: ba.content,
        dateCreated: ba.created_at,
        url: `${postUrl}#comment-${ba.id}`,
        author: {
          '@type': 'Person',
          name: ba.author?.display_name || 'Người dùng',
          ...(ba.author?.id ? { url: canonicalUrl(`/nguoi-dung/${encodeURIComponent(String(ba.author.id))}`) } : {}),
        },
      }
    }
    postNode = questionNode
  } else if (p.post_type === 'review') {
    postNode = {
      '@type': 'Review',
      '@id': `${postUrl}#post`,
      headline: postTitle,
      reviewBody: p.content || postTitle,
      url: postUrl,
      datePublished: p.created_at,
      dateModified: p.updated_at || p.created_at,
      author: authorNode,
      publisher: { '@id': `${SITE_URL}/#organization` },
      ...(p.rating ? { reviewRating: { '@type': 'Rating', ratingValue: p.rating, bestRating: 5 } } : {}),
      itemReviewed: {
        '@type': 'TouristAttraction',
        name: 'Địa điểm du lịch Vĩnh Long',
        containedInPlace: { '@type': 'AdministrativeArea', name: 'Tỉnh Vĩnh Long' },
      },
    }
  } else {
    postNode = {
      '@type': 'DiscussionForumPosting',
      '@id': `${postUrl}#post`,
      headline: postTitle,
      articleBody: p.content || postTitle,
      description: postDesc,
      url: postUrl,
      datePublished: p.created_at,
      dateModified: p.updated_at || p.created_at,
      author: authorNode,
      publisher: { '@id': `${SITE_URL}/#organization` },
      interactionStatistic: {
        '@type': 'InteractionCounter',
        interactionType: 'https://schema.org/CommentAction',
        userInteractionCount: commentsCount,
      },
    }
  }

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumbNode,
    postNode,
  ])
}

export interface ItineraryDetailSchemaOptions {
  itinerary: {
    id?: string | number
    title?: string
    name?: string
    summary?: string
    description?: string
    duration?: string
    stops?: Array<{ id?: string | number; name?: string; entity_id?: string | number }>
  }
  itineraryTitle: string
  itineraryDesc?: string
  itineraryUrl: string
}

export function buildItineraryDetailSchemaGraph(options: ItineraryDetailSchemaOptions): Record<string, any> {
  const it = options.itinerary
  const itTitle = options.itineraryTitle
  const itDesc = options.itineraryDesc || it.summary || it.description || ''
  const itUrl = options.itineraryUrl

  const webpageNode = {
    '@type': 'WebPage',
    '@id': `${itUrl}#webpage`,
    url: itUrl,
    name: `${itTitle} — vinhlong360`,
    description: itDesc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    breadcrumb: { '@id': `${itUrl}#breadcrumb` },
    mainEntity: { '@id': `${itUrl}#trip` },
    speakable: buildSpeakableSpecification(['.lead', 'h1', '.timeline-head', '.catalog-aeo-plaque__title', '.catalog-aeo-plaque__dek', '.step-card strong', '.step-card .summary', '.step-note-callout']),
    publisher: { '@id': `${SITE_URL}/#organization` },
  }

  const breadcrumbNode = {
    '@type': 'BreadcrumbList',
    '@id': `${itUrl}#breadcrumb`,
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Lịch trình', item: `${SITE_URL}/lich-trinh` },
      { '@type': 'ListItem', position: 3, name: itTitle, item: itUrl },
    ],
  }

  const tripNode: Record<string, any> = {
    '@type': 'TouristTrip',
    '@id': `${itUrl}#trip`,
    name: itTitle,
    description: itDesc,
    touristType: 'Sightseeing',
    url: itUrl,
    spatialCoverage: {
      '@type': 'Place',
      name: 'Tỉnh Vĩnh Long',
      geo: { '@type': 'GeoShape', box: '9.8 105.8 10.4 106.7' },
    },
  }

  if (Array.isArray(it.stops) && it.stops.length) {
    tripNode.itinerary = {
      '@type': 'ItemList',
      numberOfItems: it.stops.length,
      itemListElement: it.stops.map((s, i: number) => {
        const stopId = String(s.entity_id || s.id || '')
        const item: Record<string, any> = {
          '@type': 'ListItem',
          position: i + 1,
          name: s.name || stopId || `Điểm dừng ${i + 1}`,
        }
        if (stopId) item.item = canonicalUrl(entityPath(stopId))
        return item
      }),
    }
  }

  const faqItems: FaqItem[] = []
  if (it.duration) {
    faqItems.push({
      q: `Lịch trình "${itTitle}" kéo dài bao lâu?`,
      a: `Thời gian trải nghiệm dự kiến cho toàn bộ lịch trình là ${it.duration}.`,
    })
  }
  if (it.stops?.length) {
    faqItems.push({
      q: `Lịch trình "${itTitle}" có bao nhiêu điểm dừng tham quan?`,
      a: `Lịch trình gồm ${it.stops.length} điểm dừng chân trải nghiệm tiêu biểu tại Vĩnh Long.`,
    })
  }
  const faqNode = faqItems.length ? buildFaqPageSchema(faqItems, `${itUrl}#faq`) : null

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumbNode,
    tripNode,
    faqNode,
  ])
}

export interface DirectorySchemaOptions {
  totalWards?: number
  selectedArea?: string
  dirTitle?: string
  dirDesc?: string
  dirUrl?: string
  facilities?: Array<{
    id: string
    name: string
    address?: string
    phone?: string
    hours?: string
    kind?: string
  }>
}

export function buildDirectorySchemaGraph(options: DirectorySchemaOptions = {}): Record<string, any> {
  const dirUrl = options.dirUrl || canonicalUrl('/danh-ba')
  const dirTitle = options.dirTitle || 'Danh bạ hành chính — vinhlong360'
  const dirDesc = options.dirDesc || 'Danh bạ 124 xã/phường, cơ quan hành chính tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025).'
  const total = options.totalWards || 124

  const webpageNode: Record<string, any> = {
    '@type': 'CollectionPage',
    '@id': `${dirUrl}#webpage`,
    url: dirUrl,
    name: dirTitle,
    description: dirDesc,
    inLanguage: 'vi',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    breadcrumb: { '@id': `${dirUrl}#breadcrumb` },
    mainEntity: {
      '@type': 'ItemList',
      numberOfItems: total,
    },
    speakable: buildSpeakableSpecification(['h1', '.catalog-hero p', '.ward-caveat']),
    publisher: { '@id': `${SITE_URL}/#organization` },
  }

  const breadcrumbNode = {
    '@type': 'BreadcrumbList',
    '@id': `${dirUrl}#breadcrumb`,
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Danh bạ', item: dirUrl },
    ],
  }

  const govServiceNode = {
    '@type': 'GovernmentService',
    '@id': `${dirUrl}#service`,
    name: 'Dịch vụ tra cứu danh bạ hành chính và hỗ trợ du khách Vĩnh Long',
    serviceType: 'Administrative Directory & Visitor Support',
    provider: { '@id': `${SITE_URL}/#organization` },
    serviceArea: {
      '@type': 'AdministrativeArea',
      name: 'Tỉnh Vĩnh Long',
      description: 'Bao gồm 124 xã/phường hợp nhất từ 3 vùng trước tháng 7-2025.',
    },
    availableChannel: {
      '@type': 'ServiceChannel',
      serviceUrl: dirUrl,
      servicePhone: {
        '@type': 'ContactPoint',
        telephone: '+84-270-3822182',
        contactType: 'customer support, emergency, administrative information',
        areaServed: 'VN-49',
        availableLanguage: ['vi', 'en'],
      },
    },
  }

  const facilityNodes = (options.facilities || [])
    .filter(f => f.address || f.phone)
    .slice(0, 20)
    .map(f => ({
      '@type': 'GovernmentOffice',
      '@id': `${dirUrl}#office-${f.id}`,
      name: f.name,
      ...(f.address ? {
        address: {
          '@type': 'PostalAddress',
          streetAddress: f.address,
          addressRegion: 'Vĩnh Long',
          addressCountry: 'VN',
        },
      } : {}),
      ...(f.phone ? { telephone: f.phone } : {}),
      ...(f.hours ? { openingHours: f.hours } : {}),
    }))

  const faqItems: FaqItem[] = [
    {
      q: 'Danh bạ hành chính vinhlong360 gồm những đơn vị nào?',
      a: 'Danh bạ tra cứu gồm 124 xã, phường và thị trấn thuộc tỉnh Vĩnh Long hợp nhất (bao gồm cả các địa phương của Bến Tre và Trà Vinh trước tháng 7-2025).',
    },
    {
      q: 'Làm thế nào để tra cứu số điện thoại UBND và Công an xã/phường?',
      a: 'Bạn có thể chọn khu vực vùng, sau đó chọn tên xã/phường để xem địa chỉ trụ sở, số điện thoại liên hệ trực tiếp và thời gian tiếp công dân.',
    },
    {
      q: 'Dữ liệu danh bạ cơ quan có được kiểm chứng từ nguồn chính thống không?',
      a: 'Các thông tin có huy hiệu xác minh được đối soát trực tiếp từ cổng thông tin điện tử của cơ quan nhà nước (.gov.vn).',
    },
  ]
  const faqNode = buildFaqPageSchema(faqItems, `${dirUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumbNode,
    govServiceNode,
    ...facilityNodes,
    faqNode,
  ])
}

export interface NewsArticleSchemaOptions {
  article: {
    id?: string | number
    title: string
    headline?: string
    description?: string
    summary?: string
    body?: string
    content?: string
    url?: string
    image?: string | ImageDescriptor
    datePublished?: string
    dateModified?: string
    author?: {
      name?: string
      url?: string
      avatar?: string
    } | string
    category?: string
    tags?: string[]
  }
  canonicalUrl?: string
}

export function buildNewsArticleSchemaGraph(options: NewsArticleSchemaOptions): Record<string, any> {
  const a = options.article
  const articleUrl = options.canonicalUrl || a.url || canonicalUrl(`/tin-tuc/${a.id || ''}`)
  const title = a.headline || a.title
  const desc = a.description || a.summary || ''
  const body = a.body || a.content || desc

  const webpageNode = {
    '@type': 'WebPage',
    '@id': `${articleUrl}#webpage`,
    url: articleUrl,
    name: `${title} — Tin tức Vĩnh Long 360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    breadcrumb: { '@id': `${articleUrl}#breadcrumb` },
    mainEntity: { '@id': `${articleUrl}#article` },
    speakable: buildSpeakableSpecification(['h1', '.news-summary', '.lead', 'article p']),
    publisher: { '@id': `${SITE_URL}/#organization` },
  }

  const breadcrumbNode = {
    '@type': 'BreadcrumbList',
    '@id': `${articleUrl}#breadcrumb`,
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Tin tức', item: `${SITE_URL}/tin-tuc` },
      { '@type': 'ListItem', position: 3, name: title, item: articleUrl },
    ],
  }

  const authorName = typeof a.author === 'string' ? a.author : (a.author?.name || 'Ban biên tập vinhlong360')
  const authorNode = {
    '@type': 'Person',
    name: authorName,
    ...(typeof a.author === 'object' && a.author?.url ? { url: a.author.url } : {}),
  }

  const articleMeta: Record<string, any> = {
    '@type': 'NewsArticle',
    '@id': `${articleUrl}#article`,
    isPartOf: { '@id': `${articleUrl}#webpage` },
    headline: title,
    description: desc,
    articleBody: body,
    url: articleUrl,
    mainEntityOfPage: { '@id': `${articleUrl}#webpage` },
    inLanguage: 'vi-VN',
    datePublished: a.datePublished || new Date().toISOString(),
    dateModified: a.dateModified || a.datePublished || new Date().toISOString(),
    author: authorNode,
    publisher: { '@id': `${SITE_URL}/#organization` },
  }

  if (a.image) {
    if (typeof a.image === 'string') {
      articleMeta.image = [a.image.startsWith('http') ? a.image : `${SITE_URL}${a.image}`]
    } else {
      const imgObj = descriptorToImageObject(a.image)
      if (imgObj) articleMeta.image = [imgObj.contentUrl]
    }
  }

  if (a.category) articleMeta.articleSection = a.category
  if (Array.isArray(a.tags) && a.tags.length) articleMeta.keywords = a.tags.join(', ')

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumbNode,
    articleMeta,
  ])
}

export interface AboutPageSchemaOptions {
  title?: string
  description?: string
  updatedDate?: string
  canonicalUrl?: string
}

export function buildAboutPageSchemaGraph(options: AboutPageSchemaOptions = {}): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/gioi-thieu')
  const title = options.title || 'Giới thiệu về vinhlong360'
  const desc = options.description || 'Về vinhlong360: Sứ mệnh, văn hóa, con người và phương pháp biên tập cổng du lịch Vĩnh Long.'

  const webpageNode = {
    '@type': 'AboutPage',
    '@id': `${pageUrl}#webpage`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    breadcrumb: { '@id': `${pageUrl}#breadcrumb` },
    mainEntity: { '@id': `${SITE_URL}/#organization` },
    about: { '@id': `${SITE_URL}/#organization` },
    speakable: buildSpeakableSpecification(['.about-intro', 'h1', '.about-mission-quote', '#ban-bien-tap', '.catalog-aeo-plaque__title', '.catalog-aeo-plaque__dek']),
  }

  const nodes: any[] = [
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
  ]

  if (options.canonicalUrl && options.updatedDate) {
    // optional extension hook
  }

  return buildUnifiedSchemaGraph(nodes)
}

export interface ContactPageSchemaOptions {
  title?: string
  description?: string
  email?: string
  claimEmail?: string
  hotline?: string
  canonicalUrl?: string
}

export function buildContactPageSchemaGraph(options: ContactPageSchemaOptions = {}): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/lien-he')
  const title = options.title || 'Liên hệ vinhlong360'
  const desc = options.description || 'Liên hệ vinhlong360.vn: yêu cầu sửa thông tin, hợp tác quảng bá, đăng ký quản lý trang.'
  const email = options.email || 'lienhe@vinhlong360.vn'
  const hotline = options.hotline || '+84-270-3822182'

  const webpageNode = {
    '@type': 'ContactPage',
    '@id': `${pageUrl}#webpage`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    breadcrumb: { '@id': `${pageUrl}#breadcrumb` },
    mainEntity: { '@id': `${SITE_URL}/#organization` },
    speakable: buildSpeakableSpecification(['.bm-inner h1', '.bm-sub', '.bm-sla', '.contact-quote', '.contact-cards h2', '.catalog-aeo-plaque__title', '.catalog-aeo-plaque__dek']),
  }

  const contactPointNode = {
    '@type': 'ContactPoint',
    '@id': `${pageUrl}#contact-point`,
    telephone: hotline,
    email,
    contactType: 'customer support',
    areaServed: { '@type': 'AdministrativeArea', name: 'Vĩnh Long' },
    availableLanguage: ['vi', 'en'],
  }

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    contactPointNode,
  ])
}

export interface CatalogDirectorySchemaOptions {
  total: number
  items?: Array<{ id: string | number; name: string; type?: string; place_name?: string }>
  activeType?: string
  activeArea?: string
  canonicalUrl?: string
}

export function buildCatalogDirectorySchemaGraph(options: CatalogDirectorySchemaOptions): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/dia-diem')
  const total = options.total || 0
  const title = 'Danh bạ địa điểm du lịch & văn hóa Vĩnh Long'
  const desc = 'Toàn bộ điểm đến, đặc sản OCOP, làng nghề, lưu trú và di tích lịch sử tỉnh Vĩnh Long. Lọc theo 3 vùng và loại hình.'

  const webpageNode = {
    '@type': 'CollectionPage',
    '@id': `${pageUrl}#collection`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    breadcrumb: { '@id': `${pageUrl}#breadcrumb` },
    about: {
      '@type': 'Thing',
      name: 'Địa điểm du lịch và đặc sản tỉnh Vĩnh Long',
    },
    speakable: buildSpeakableSpecification(['.catalog-hero-inner h1', '.catalog-hero-inner p', '.almanac-stats', '.catalog-aeo-plaque__title', '.catalog-aeo-plaque__dek']),
  }

  const breadcrumbNode = {
    '@type': 'BreadcrumbList',
    '@id': `${pageUrl}#breadcrumb`,
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Địa điểm', item: pageUrl },
    ],
  }

  const itemListElements = (options.items || []).slice(0, 30).map((item, index) => ({
    '@type': 'ListItem',
    position: index + 1,
    name: item.name,
    url: canonicalUrl(`/dia-diem/${encodeURIComponent(String(item.id))}`),
  }))

  const itemListNode = {
    '@type': 'ItemList',
    '@id': `${pageUrl}#items`,
    name: 'Danh sách địa điểm nổi bật tại Vĩnh Long',
    numberOfItems: total,
    itemListElement: itemListElements,
  }

  const faqItems = [
    {
      q: 'Danh bạ địa điểm Vĩnh Long 360 bao gồm những danh mục nào?',
      a: 'Danh bạ tổng hợp đầy đủ các điểm tham quan sinh thái, di tích lịch sử văn hóa, homestay nhà vườn, quán ăn đặc sản và cơ sở OCOP trên địa bàn toàn tỉnh Vĩnh Long.',
    },
    {
      q: 'Làm thế nào để lọc điểm đến theo khu vực hành chính hoặc khoảng cách?',
      a: 'Bạn có thể bấm chọn các con dấu khu vực (Vĩnh Long trung tâm, Trà Vinh ven biển, Bến Tre cù lao) hoặc lọc theo loại hình để tìm đúng địa điểm mong muốn.',
    },
    {
      q: 'Thông tin giờ mở cửa và số điện thoại trên danh bạ có được cập nhật thường xuyên không?',
      a: 'Dữ liệu được Ban biên tập đối soát thực địa và tiếp nhận phản hồi cập nhật liên tục từ các chủ cơ sở kinh doanh và người dùng bản địa.',
    },
  ]
  const faqNode = buildFaqPageSchema(faqItems, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumbNode,
    itemListNode,
    faqNode,
  ])
}

export interface GuideSchemaOptions {
  title?: string
  description?: string
  canonicalUrl?: string
  faqs?: Array<{ q: string; a: string }>
}

export function buildGuideSchemaGraph(options: GuideSchemaOptions = {}): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/huong-dan')
  const title = options.title || 'Hướng dẫn sử dụng vinhlong360'
  const desc = options.description || 'Cẩm nang đầy đủ mọi tính năng trên vinhlong360: tìm kiếm, bản đồ, tạo lịch trình, cộng đồng, điểm thưởng và xử lý sự cố.'

  const webpageNode = {
    '@type': 'WebPage',
    '@id': `${pageUrl}#webpage`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: { '@id': `${SITE_URL}/#organization` },
    mainEntity: { '@id': `${SITE_URL}/#organization` },
    speakable: buildSpeakableSpecification(['.bm-inner h1', '.bm-sub', '.section-intro', '#bat-dau h2', '.catalog-aeo-plaque__title', '.catalog-aeo-plaque__dek']),
  }

  const defaultFaqs = [
    {
      q: 'Làm thế nào để tìm kiếm địa điểm và sản phẩm OCOP trên vinhlong360?',
      a: 'Bạn chỉ cần nhập từ khóa vào thanh tìm kiếm ở đầu trang hoặc chọn các danh mục Du lịch, Ẩm thực, OCOP để duyệt nhanh mà không cần tạo tài khoản.',
    },
    {
      q: 'Tính năng tạo lịch trình du lịch thông minh hoạt động như thế nào?',
      a: 'Du khách có thể chọn các điểm đến yêu thích từ danh sách đã lưu, kéo thả sắp xếp thứ tự và hệ thống sẽ tự động tính toán lộ trình hiển thị trực quan trên bản đồ.',
    },
    {
      q: 'Bản đồ số du lịch vinhlong360 có hỗ trợ tìm điểm quanh tôi không?',
      a: 'Có, tính năng Tìm quanh tôi trên bản đồ số giúp bạn định vị vị trí hiện tại và lọc các điểm tham quan, ẩm thực, lưu trú gần nhất trong bán kính mong muốn.',
    },
    {
      q: 'Tham gia cộng đồng du lịch Vĩnh Long mang lại những quyền lợi gì?',
      a: 'Thành viên đăng nhập có thể viết bài chia sẻ kinh nghiệm, đánh giá địa điểm, lưu trữ hành trình đám mây và tích lũy điểm danh tiếng để thăng hạng huy hiệu.',
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    faqNode,
  ])
}

export interface LeaderboardSchemaOptions {
  title?: string
  description?: string
  canonicalUrl?: string
  totalCount?: number
  podium?: Array<{
    id?: string | number
    username?: string
    display_name?: string
    rank?: number
    points?: number
    level?: number
    level_label?: string
  }>
  faqs?: Array<{ q: string; a: string }>
}

export function buildLeaderboardSchemaGraph(options: LeaderboardSchemaOptions = {}): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/bang-xep-hang')
  const title = options.title || 'Thành viên tích cực — Bảng xếp hạng'
  const desc = options.description || 'Bảng xếp hạng thành viên đóng góp tích cực nhất cộng đồng vinhlong360: đánh giá, bài viết, ảnh và lượt theo dõi.'

  const webpageNode = {
    '@type': 'CollectionPage',
    '@id': `${pageUrl}#webpage`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: { '@id': `${SITE_URL}/#organization` },
    mainEntity: { '@id': `${pageUrl}#leaderboard` },
    speakable: buildSpeakableSpecification(['.bxh-h1', '.bxh-head p', '.bxh-eyebrow', '.catalog-aeo-plaque__title', '.catalog-aeo-plaque__dek']),
  }

  const podiumList = options.podium || []
  const itemListElements = podiumList.map((m, index) => {
    const position = m.rank ?? (index + 1)
    const name = m.display_name || 'Thành viên vinhlong360'
    const memberUrl = m.username || m.id ? canonicalUrl(userPath(m.username || m.id)) : pageUrl
    return {
      '@type': 'ListItem',
      position,
      name,
      url: memberUrl,
      item: {
        '@type': 'Person',
        name,
        url: memberUrl,
        ...(m.level_label ? { jobTitle: m.level_label } : {}),
      },
    }
  })

  const itemListNode = {
    '@type': 'ItemList',
    '@id': `${pageUrl}#leaderboard`,
    name: 'Bảng xếp hạng thành viên tích cực — vinhlong360',
    description: 'Danh sách các thành viên đóng góp tích cực nhất trong cộng đồng vinhlong360.',
    numberOfItems: options.totalCount ?? podiumList.length,
    itemListElement: itemListElements,
  }

  const defaultFaqs = [
    {
      q: 'Bảng xếp hạng thành viên vinhlong360 được tính điểm như thế nào?',
      a: 'Điểm danh tiếng được tính tự động từ các hoạt động đóng góp hữu ích: viết đánh giá địa điểm (tối đa 130 điểm), đăng bài viết (tối đa 45 điểm), chia sẻ ảnh (tối đa 40 điểm), lượt thích nhận được và người theo dõi.',
    },
    {
      q: 'Bao lâu thì bảng xếp hạng cộng đồng vinhlong360 được làm mới một lần?',
      a: 'Bảng xếp hạng được cập nhật liên tục theo thời gian thực khi các hoạt động đánh giá và bài viết được hệ thống kiểm duyệt và ghi nhận thành công.',
    },
    {
      q: 'Làm thế nào để xuất hiện trên bục vinh danh Top 3 thành viên tích cực?',
      a: 'Thành viên cần duy trì các đóng góp chất lượng và đều đặn ở nhiều danh mục (đánh giá, bài viết, ảnh thực địa) để tích lũy điểm danh tiếng trong tuần, tháng hoặc toàn thời gian.',
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    itemListNode,
    faqNode,
  ])
}

export interface MemberGuideSchemaOptions {
  title?: string
  description?: string
  canonicalUrl?: string
  faqs?: Array<{ q: string; a: string }>
}

export function buildMemberGuideSchemaGraph(options: MemberGuideSchemaOptions = {}): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/huong-dan-thanh-vien')
  const title = options.title || 'Hướng dẫn thành viên — Hệ thống cấp bậc & điểm danh tiếng'
  const desc = options.description || 'Tìm hiểu cách tính điểm danh tiếng, cấp bậc thành viên và huy hiệu trên cộng đồng vinhlong360.'

  const webpageNode = {
    '@type': 'WebPage',
    '@id': `${pageUrl}#webpage`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: { '@id': `${SITE_URL}/#organization` },
    mainEntity: { '@id': `${SITE_URL}/#organization` },
    speakable: buildSpeakableSpecification(['.guide-hero h1', '.guide-hero p', '.guide-section h2', '.guide-intro', '.catalog-aeo-plaque__title', '.catalog-aeo-plaque__dek']),
  }

  const defaultFaqs = [
    {
      q: 'Hệ thống cấp bậc thành viên trên vinhlong360 gồm những cấp độ nào?',
      a: 'Hệ thống gồm 4 cấp bậc chính: Cấp 1 (Người mới: 0–19 điểm), Cấp 2 (Người đóng góp: 20–79 điểm), Cấp 3 (Đóng góp tích cực: 80–199 điểm) và Cấp 4 (Đại sứ: từ 200 điểm trở lên).',
    },
    {
      q: 'Công thức tính điểm danh tiếng có bị giới hạn số lượng đóng góp không?',
      a: 'Có, mỗi loại hoạt động đều có mức trần điểm tối đa nhằm tránh lạm phát và khuyến khích đóng góp đa dạng. Tổng điểm tối đa lý thuyết là 315 điểm.',
    },
    {
      q: 'Làm thế nào để nhận huy hiệu thành tích trên vinhlong360?',
      a: 'Huy hiệu được trao tự động ngay khi thành viên hoàn thành điều kiện tương ứng, ví dụ: Đánh giá đầu tiên (1 đánh giá), Nhiếp ảnh cộng đồng (10 bài có ảnh), Người khám phá (10 địa điểm khác nhau), và Đa năng.',
    },
    {
      q: 'Đóng góp loại nào mang lại điểm danh tiếng cao nhất?',
      a: 'Đánh giá địa điểm trải nghiệm thực tế mang lại điểm cao nhất (5 điểm/bài cho 10 bài đầu tiên), tiếp theo là chia sẻ ảnh thực tế (3 điểm/bài cho 10 bài đầu tiên).',
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    faqNode,
  ])
}

export interface LegalDocumentSchemaOptions {
  title?: string
  description?: string
  canonicalUrl?: string
  policyVersion?: string
  updatedDate?: string
  faqs?: Array<{ q: string; a: string }>
}

export function buildPrivacyPolicySchemaGraph(options: LegalDocumentSchemaOptions = {}): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/chinh-sach-bao-mat')
  const title = options.title || 'Chính sách bảo mật'
  const desc = options.description || 'Chính sách bảo mật và quyền riêng tư dữ liệu trên vinhlong360.'

  const webpageNode = {
    '@type': 'WebPage',
    '@id': `${pageUrl}#webpage`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: { '@id': `${SITE_URL}/#organization` },
    mainEntity: { '@id': `${SITE_URL}/#organization` },
    speakable: buildSpeakableSpecification(['.bm-inner h1', '.bm-sub', '.legal-metadata', '.about-section-content h2']),
  }

  const defaultFaqs = [
    {
      q: 'Dữ liệu cá nhân nào được thu thập khi người dùng sử dụng vinhlong360?',
      a: 'vinhlong360 chỉ thu thập các thông tin cần thiết để xác thực tài khoản và tương tác cộng đồng (tên hiển thị, email/số điện thoại, bài viết, đánh giá) và thông tin kỹ thuật cơ bản (cookie phiên làm việc, tùy biến giao diện).',
    },
    {
      q: 'Người dùng có quyền yêu cầu trích xuất hoặc xóa dữ liệu tài khoản không?',
      a: 'Có, người dùng có đầy đủ quyền yêu cầu cung cấp bản sao dữ liệu cá nhân hoặc yêu cầu khóa và xóa dữ liệu tài khoản theo quy định bảo vệ dữ liệu cá nhân.',
    },
    {
      q: 'Cookie trên hệ thống vinhlong360 được phân loại và kiểm soát như thế nào?',
      a: 'Cookie bắt buộc dùng cho bảo mật phiên và xác thực biểu mẫu. Cookie tùy chọn lưu các cấu hình giao diện người dùng và có thể xóa bất cứ lúc nào qua trang cài đặt hoặc trình duyệt.',
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    faqNode,
  ])
}

export function buildTermsOfServiceSchemaGraph(options: LegalDocumentSchemaOptions = {}): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/dieu-khoan-su-dung')
  const title = options.title || 'Điều khoản sử dụng'
  const desc = options.description || 'Điều khoản sử dụng và quy định dịch vụ trên vinhlong360.'

  const webpageNode = {
    '@type': 'WebPage',
    '@id': `${pageUrl}#webpage`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: { '@id': `${SITE_URL}/#organization` },
    mainEntity: { '@id': `${SITE_URL}/#organization` },
    speakable: buildSpeakableSpecification(['.bm-inner h1', '.bm-sub', '.legal-metadata', '.about-section-content h2']),
  }

  const defaultFaqs = [
    {
      q: 'Quy định đối với việc chia sẻ bài viết, đánh giá và ảnh trên cộng đồng vinhlong360?',
      a: 'Nội dung chia sẻ phải là trải nghiệm thực tế, trung thực, tôn trọng văn hóa bản địa, không sao chép hình ảnh không thuộc quyền sở hữu, không phát tán thư rác hoặc thông tin sai lệch.',
    },
    {
      q: 'Bản quyền đối với tư liệu và đồ thị dữ liệu trên vinhlong360 thuộc về ai?',
      a: 'Cơ sở dữ liệu biên tập, hình ảnh bản quyền và đồ thị dữ liệu số thuộc sở hữu của vinhlong360 và các đối tác ủy quyền. Tác giả giữ quyền đối với các bài viết và đánh giá đóng góp cá nhân.',
    },
    {
      q: 'Quy trình xử lý khi phát hiện nội dung có dấu hiệu vi phạm điều khoản?',
      a: 'Thành viên có thể sử dụng nút Báo cáo trực tiếp trên bài viết hoặc liên hệ ban quản trị. Hệ thống sẽ tiếp nhận, đối soát và xử lý trong vòng 24–48 giờ.',
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    faqNode,
  ])
}

export interface InterestCategorySchemaOptions {
  interestKey: string
  title?: string
  description?: string
  canonicalUrl?: string
  totalCount?: number
  items?: Array<{
    id: string | number
    name: string
    type?: string
  }>
  faqs?: Array<{ q: string; a: string }>
}

export function buildInterestCategorySchemaGraph(options: InterestCategorySchemaOptions): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl(`/kham-pha/${encodeURIComponent(options.interestKey)}`)
  const title = options.title || 'Khám phá Vĩnh Long'
  const desc = options.description || 'Chuyên mục khám phá du lịch, ẩm thực và văn hóa tỉnh Vĩnh Long.'

  const webpageNode = {
    '@type': 'CollectionPage',
    '@id': `${pageUrl}#webpage`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: { '@id': `${SITE_URL}/#organization` },
    mainEntity: { '@id': `${pageUrl}#items` },
    speakable: buildSpeakableSpecification(['.catalog-hero-inner h1', '.catalog-lead', '.int-cross-sub', '.catalog-aeo-plaque__title', '.catalog-aeo-plaque__dek']),
  }

  const itemListElements = (options.items || []).slice(0, 30).map((item, index) => ({
    '@type': 'ListItem',
    position: index + 1,
    name: item.name,
    url: canonicalUrl(entityPath(item.id)),
  }))

  const itemListNode = {
    '@type': 'ItemList',
    '@id': `${pageUrl}#items`,
    name: `Danh sách ${title}`,
    description: desc,
    numberOfItems: options.totalCount ?? (options.items?.length || 0),
    itemListElement: itemListElements,
  }

  const defaultFaqs = [
    {
      q: `Chuyên mục ${title} trên vinhlong360 bao gồm những trải nghiệm gì?`,
      a: `Chuyên mục tổng hợp các địa điểm, hoạt động văn hóa, ẩm thực đặc sản và trải nghiệm thực địa tiêu biểu nhất tại tỉnh Vĩnh Long và các cù lao lân cận.`,
    },
    {
      q: `Làm thế nào để lọc kết quả theo vùng hoặc loại hình trải nghiệm?`,
      a: `Du khách có thể sử dụng bộ lọc danh mục và bộ lọc 3 vùng địa lý (Vĩnh Long trung tâm, Trà Vinh ven biển, Bến Tre cù lao) để thu hẹp kết quả tìm kiếm.`,
    },
    {
      q: `Thông tin về giờ mở cửa, địa chỉ và số điện thoại liên hệ có chính xác không?`,
      a: `Mọi địa điểm trong danh mục đều được Ban biên tập đối soát thực địa, xác minh tọa độ số và cập nhật liên tục từ cộng đồng địa phương.`,
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    itemListNode,
    faqNode,
  ])
}

export interface SeasonalitySchemaOptions {
  month: number
  quarterTag?: string
  quarterNote?: string
  totalInSeason?: number
  items?: Array<{ id: string | number; name: string; type?: string; summary?: string }>
  canonicalUrl?: string
  faqs?: Array<{ q: string; a: string }>
}

export function buildSeasonalitySchemaGraph(options: SeasonalitySchemaOptions): Record<string, any> {
  const m = options.month || 1
  const pageUrl = options.canonicalUrl || canonicalUrl('/theo-mua')
  const title = `Tháng ${m}: đi đâu, ăn gì ở Vĩnh Long — Lịch mùa vụ nông sản & sông nước`
  const desc = `Những sản vật đang mùa, ngon nhất vào tháng ${m} tại Vĩnh Long — trái cây, nông sản miệt vườn, và nhịp nước sông Mekong.`

  const webpageNode = {
    '@type': 'CollectionPage',
    '@id': `${pageUrl}#collection`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: {
      '@type': 'Place',
      name: 'Tỉnh Vĩnh Long',
      geo: { '@type': 'GeoShape', box: '9.8 105.8 10.4 106.7' },
    },
    speakable: buildSpeakableSpecification([
      '.catalog-hero h1',
      '.season-moment-text strong',
      '.season-moment-text p',
      '.season-tide-cue',
      '.catalog-aeo-plaque__title',
      '.catalog-aeo-plaque__dek',
    ]),
  }

  const breadcrumbNode = {
    '@type': 'BreadcrumbList',
    '@id': `${pageUrl}#breadcrumb`,
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Theo mùa', item: pageUrl },
    ],
  }

  const itemListElements = (options.items || []).slice(0, 30).map((item, index) => ({
    '@type': 'ListItem',
    position: index + 1,
    name: item.name,
    url: canonicalUrl(entityPath(item.id)),
  }))

  const itemListNode = {
    '@type': 'ItemList',
    '@id': `${pageUrl}#items`,
    name: `Đặc sản và điểm đến tháng ${m} tại Vĩnh Long`,
    description: `Danh mục sản vật và điểm đến ngon nhất vào tháng ${m}.`,
    numberOfItems: options.totalInSeason ?? (options.items?.length || 0),
    itemListElement: itemListElements,
  }

  const defaultFaqs = [
    {
      q: 'Mùa trái cây rộ nhất tại Vĩnh Long diễn ra vào những tháng nào?',
      a: 'Thời điểm trái cây trĩu cành ngon nhất là từ tháng 5 đến tháng 8, tiêu biểu với chôm chôm, sầu riêng, bưởi năm roi, măng cụt và nhãn xuồng cơm vàng tại các vườn cù lao An Bình.',
    },
    {
      q: 'Đến Vĩnh Long vào mùa nước nổi (tháng 9 đến tháng 11) có gì đặc sắc?',
      a: 'Mùa nước nổi đem lại nguồn thủy sản phong phú với cá linh non, bông điên điển, cá lóc đồng cùng các trải nghiệm giăng lưới, chèo xuồng ngắm cảnh sông nước phù sa.',
    },
    {
      q: `Nhịp con nước và nông vụ Vĩnh Long trong tháng ${m} ra sao?`,
      a: options.quarterNote || 'Khám phá các sản vật và hành trình miệt vườn phong phú theo chu kỳ con nước sông Mekong.',
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumbNode,
    itemListNode,
    faqNode,
  ])
}

export interface FestivalEventSchemaOptions {
  events?: Array<{
    id: string | number
    name: string
    summary?: string
    place_name?: string
    date_start?: string
    date_end?: string
  }>
  totalCount?: number
  todayLunarLabel?: string
  canonicalUrl?: string
  faqs?: Array<{ q: string; a: string }>
}

export function buildFestivalEventSchemaGraph(options: FestivalEventSchemaOptions = {}): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/le-hoi')
  const total = options.totalCount ?? (options.events?.length || 0)
  const title = 'Lễ hội truyền thống Vĩnh Long — Giao thoa văn hóa Kinh - Khmer - Hoa'
  const desc = 'Lễ hội đình miếu Kỳ Yên, lễ hội Ok Om Bok cúng trăng, Chôl Chnăm Thmây và Nghinh Ông miền duyên hải — truyền thống văn hóa tỉnh Vĩnh Long.'

  const webpageNode = {
    '@type': 'CollectionPage',
    '@id': `${pageUrl}#collection`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: {
      '@type': 'Place',
      name: 'Tỉnh Vĩnh Long',
      geo: { '@type': 'GeoShape', box: '9.8 105.8 10.4 106.7' },
    },
    speakable: buildSpeakableSpecification([
      '.catalog-hero h1',
      '.dateline-eyebrow',
      '.now-banner',
      '.sediment-head h2',
      '.catalog-aeo-plaque__title',
      '.catalog-aeo-plaque__dek',
    ]),
  }

  const breadcrumbNode = {
    '@type': 'BreadcrumbList',
    '@id': `${pageUrl}#breadcrumb`,
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Lễ hội', item: pageUrl },
    ],
  }

  const eventListElements = (options.events || []).slice(0, 30).map((e, index) => {
    const eventUrl = canonicalUrl(entityPath(e.id))
    const itemNode: Record<string, any> = {
      '@type': 'Event',
      '@id': `${eventUrl}#event`,
      name: e.name,
      description: e.summary || e.name,
      url: eventUrl,
      eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
      eventStatus: 'https://schema.org/EventScheduled',
    }
    if (e.date_start) itemNode.startDate = e.date_start
    if (e.date_end) itemNode.endDate = e.date_end
    if (e.place_name) {
      itemNode.location = {
        '@type': 'Place',
        name: e.place_name,
        address: { '@type': 'PostalAddress', addressRegion: 'Vĩnh Long', addressCountry: 'VN' },
      }
    }
    return {
      '@type': 'ListItem',
      position: index + 1,
      item: itemNode,
    }
  })

  const itemListNode = {
    '@type': 'ItemList',
    '@id': `${pageUrl}#events`,
    name: 'Danh sách lễ hội truyền thống tiêu biểu tại Vĩnh Long',
    description: 'Các sự kiện văn hóa, lễ hội dân gian và nghi thức tâm linh.',
    numberOfItems: total,
    itemListElement: eventListElements,
  }

  const defaultFaqs = [
    {
      q: 'Văn hóa lễ hội Vĩnh Long có những nét đặc trưng gì?',
      a: 'Vĩnh Long là nơi giao thoa văn hóa độc đáo của ba dân tộc Kinh, Khmer và Hoa với các lễ hội đình miếu Kỳ Yên, lễ hội Ok Om Bok cúng trăng, Chôl Chnăm Thmây và lễ hội Nghinh Ông miền duyên hải.',
    },
    {
      q: 'Du khách tham gia lễ hội ở Vĩnh Long cần lưu ý những quy tắc gì?',
      a: 'Hầu hết các lễ hội truyền thống mở cửa tự do không thu phí. Du khách nên mặc trang phục lịch sự khi vào chánh điện; tháo giày dép khi vào chùa Khmer và nên tham dự các nghi thức chính vào buổi sáng.',
    },
    {
      q: 'Làm thế nào để theo dõi lịch diễn ra các lễ hội theo cả âm lịch và dương lịch?',
      a: 'Trang Lễ hội trên VinhLong360 tích hợp bảng chuyển đổi âm - dương lịch, chu kỳ trăng và tải lịch nhắc sự kiện dạng tập tin .ics về điện thoại tiện lợi.',
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumbNode,
    itemListNode,
    faqNode,
  ])
}

export interface OcopLedgerSchemaOptions {
  items?: Array<{
    id: string | number
    name: string
    summary?: string
    stars?: number
    category?: string
  }>
  totalCount?: number
  topStarTier?: number
  canonicalUrl?: string
  faqs?: Array<{ q: string; a: string }>
}

export function buildOcopLedgerSchemaGraph(options: OcopLedgerSchemaOptions = {}): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/ocop')
  const total = options.totalCount ?? (options.items?.length || 0)
  const title = 'Sản phẩm OCOP Vĩnh Long — Sổ vàng vinh danh đặc sản quốc gia'
  const desc = 'Chương trình Mỗi xã một sản phẩm (OCOP) tỉnh Vĩnh Long xếp hạng 3 đến 5 sao — nông sản sạch, thủ công mỹ nghệ và ẩm thực miệt vườn kiểm định chất lượng cao.'

  const webpageNode = {
    '@type': 'CollectionPage',
    '@id': `${pageUrl}#collection`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: {
      '@type': 'Thing',
      name: 'Chương trình Mỗi xã Một sản phẩm (OCOP)',
      description: 'Chương trình phát triển kinh tế nông thôn nâng cao giá trị đặc sản địa phương tỉnh Vĩnh Long.',
    },
    speakable: buildSpeakableSpecification([
      '.catalog-hero h1',
      '.ledger-kicker',
      '.ledger-dek',
      '.hero-creds',
      '.catalog-aeo-plaque__title',
      '.catalog-aeo-plaque__dek',
    ]),
  }

  const breadcrumbNode = {
    '@type': 'BreadcrumbList',
    '@id': `${pageUrl}#breadcrumb`,
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Sản phẩm', item: `${SITE_URL}/san-pham` },
      { '@type': 'ListItem', position: 3, name: 'OCOP', item: pageUrl },
    ],
  }

  const itemListElements = (options.items || []).slice(0, 30).map((e, index) => {
    const itemUrl = canonicalUrl(entityPath(e.id))
    const itemNode: Record<string, any> = {
      '@type': 'Product',
      '@id': `${itemUrl}#product`,
      name: e.name,
      description: e.summary || e.name,
      url: itemUrl,
      category: 'OCOP Certified Products',
    }
    if (e.stars) {
      itemNode.award = `Chứng nhận OCOP ${e.stars} sao Tỉnh Vĩnh Long`
    }
    return {
      '@type': 'ListItem',
      position: index + 1,
      item: itemNode,
    }
  })

  const itemListNode = {
    '@type': 'ItemList',
    '@id': `${pageUrl}#items`,
    name: 'Sổ vàng sản phẩm OCOP Vĩnh Long',
    description: 'Danh mục sản phẩm nông nghiệp và làng nghề đạt chuẩn OCOP từ 3 đến 5 sao.',
    numberOfItems: total,
    itemListElement: itemListElements,
  }

  const defaultFaqs = [
    {
      q: 'Sản phẩm OCOP Vĩnh Long là gì?',
      a: 'Chương trình Mỗi xã một sản phẩm (OCOP) tại Vĩnh Long tôn vinh và chứng nhận các đặc sản nông nghiệp, làng nghề thủ công và ẩm thực truyền thống đạt tiêu chuẩn chất lượng cao từ 3 sao đến 5 sao.',
    },
    {
      q: 'Vĩnh Long hiện có những sản phẩm OCOP 5 sao nào tiêu biểu?',
      a: 'Vĩnh Long sở hữu các sản phẩm OCOP đạt hạng cao tiêu biểu như bưởi năm roi Bình Minh, khoai lang Bình Tân, bánh tráng cù lao Mây, các sản phẩm chế biến từ dừa và gốm đỏ Mang Thít.',
    },
    {
      q: 'Làm thế nào để tìm và mua đặc sản OCOP Vĩnh Long chính gốc?',
      a: 'Du khách và người tiêu dùng có thể tra cứu thông tin nhà sản xuất, địa chỉ điểm bán, số điện thoại liên hệ và định vị bản đồ trực tiếp trên hệ thống VinhLong360.',
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumbNode,
    itemListNode,
    faqNode,
  ])
}

export interface ProductCatalogSchemaOptions {
  items?: Array<{
    id: string | number
    name: string
    summary?: string
    ocop_stars?: number
    category?: string
  }>
  totalCount?: number
  inSeasonCount?: number
  currentMonth?: number
  canonicalUrl?: string
  faqs?: Array<{ q: string; a: string }>
}

export function buildProductCatalogSchemaGraph(options: ProductCatalogSchemaOptions = {}): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/san-pham')
  const total = options.totalCount ?? (options.items?.length || 0)
  const month = options.currentMonth || new Date().getMonth() + 1
  const title = `Đặc sản & Sản phẩm Vĩnh Long — Chợ phiên tháng ${month} đất phù sa`
  const desc = 'Trái cây nhiệt đới tươi ngon chính vụ, nông sản thượng hạng, đặc sản OCOP và quà quê bản địa tỉnh Vĩnh Long.'

  const webpageNode = {
    '@type': 'CollectionPage',
    '@id': `${pageUrl}#collection`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: {
      '@type': 'Thing',
      name: 'Đặc sản và Sản phẩm địa phương Vĩnh Long',
      description: 'Trái cây nhiệt đới, nông sản chất lượng cao, sản phẩm OCOP và làng nghề truyền thống Vĩnh Long.',
    },
    speakable: buildSpeakableSpecification([
      '.catalog-hero h1',
      '.market-kicker',
      '.market-dek',
      '.seasonal-banner-title',
      '.catalog-aeo-plaque__title',
      '.catalog-aeo-plaque__dek',
    ]),
  }

  const breadcrumbNode = {
    '@type': 'BreadcrumbList',
    '@id': `${pageUrl}#breadcrumb`,
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Sản phẩm', item: pageUrl },
    ],
  }

  const itemListElements = (options.items || []).slice(0, 30).map((e, index) => {
    const itemUrl = canonicalUrl(entityPath(e.id))
    const itemNode: Record<string, any> = {
      '@type': 'Product',
      '@id': `${itemUrl}#product`,
      name: e.name,
      description: e.summary || e.name,
      url: itemUrl,
      category: e.category || 'Nông sản đặc sản Vĩnh Long',
    }
    if (e.ocop_stars) {
      itemNode.award = `Chứng nhận OCOP ${e.ocop_stars} sao`
    }
    return {
      '@type': 'ListItem',
      position: index + 1,
      item: itemNode,
    }
  })

  const itemListNode = {
    '@type': 'ItemList',
    '@id': `${pageUrl}#items`,
    name: `Danh mục đặc sản Vĩnh Long phiên chợ tháng ${month}`,
    description: 'Sản phẩm nông nghiệp và đặc sản địa phương đang chính vụ.',
    numberOfItems: total,
    itemListElement: itemListElements,
  }

  const defaultFaqs = [
    {
      q: 'Vĩnh Long có những loại đặc sản nào nổi tiếng nhất để mua làm quà?',
      a: 'Các đặc sản nức tiếng gồm bưởi năm roi Bình Minh, khoai lang Bình Tân, sầu riêng Ri6, bánh tráng cù lao Mây, cam sành Tam Bình và các sản phẩm thủ công gốm đỏ Mang Thít.',
    },
    {
      q: 'Làm thế nào để chọn mua được trái cây và đặc sản Vĩnh Long đúng nguồn gốc?',
      a: 'Du khách nên ghé trực tiếp các nhà vườn tại cù lao An Bình, các hợp tác xã đạt chứng nhận OCOP hoặc các điểm trưng bày có tem truy xuất nguồn gốc rõ ràng.',
    },
    {
      q: 'Các cơ sở sản xuất tại Vĩnh Long có hỗ trợ đóng gói trái cây gửi đi xa không?',
      a: 'Nhiều nhà vườn và cơ sở chế biến hỗ trợ đóng thùng chống sốc cho trái cây tươi, hút chân không cho bánh tráng và nông sản khô để du khách tiện mang theo đường dài.',
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumbNode,
    itemListNode,
    faqNode,
  ])
}

export interface RoutesCatalogSchemaOptions {
  routes?: Array<{
    id: string
    name: string
    description?: string
    duration?: string
    distance?: string
    area?: string
    stops?: Array<{ name: string; type?: string }>
  }>
  totalCount?: number
  canonicalUrl?: string
  faqs?: Array<{ q: string; a: string }>
}

export function buildRoutesCatalogSchemaGraph(options: RoutesCatalogSchemaOptions = {}): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/tuyen-duong')
  const total = options.totalCount ?? (options.routes?.length || 0)
  const title = 'Tuyến đường gợi ý Vĩnh Long — Lộ trình du lịch miệt vườn & sông nước'
  const desc = 'Các cung đường du lịch tự khám phá bằng xe máy và ô tô kết nối cù lao An Bình, lò gốm Mang Thít và sông nước Cửu Long.'

  const webpageNode = {
    '@type': 'CollectionPage',
    '@id': `${pageUrl}#collection`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: {
      '@type': 'TouristTrip',
      name: 'Hành trình du lịch khám phá Vĩnh Long',
      description: 'Tuyến đường gợi ý khám phá miệt vườn, di sản gốm đỏ Mang Thít và cù lao sông Tiền.',
      spatialCoverage: {
        '@type': 'Place',
        name: 'Tỉnh Vĩnh Long',
        geo: { '@type': 'GeoShape', box: '9.8 105.8 10.4 106.7' },
      },
    },
    speakable: buildSpeakableSpecification([
      '.catalog-hero h1',
      '.hero-lede',
      '.route-header',
      '.route-stops-head',
      '.catalog-aeo-plaque__title',
      '.catalog-aeo-plaque__dek',
    ]),
  }

  const breadcrumbNode = {
    '@type': 'BreadcrumbList',
    '@id': `${pageUrl}#breadcrumb`,
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Tuyến đường gợi ý', item: pageUrl },
    ],
  }

  const itemListElements = (options.routes || []).map((r, index) => {
    const routeUrl = `${pageUrl}#route-${r.id}`
    const itemNode: Record<string, any> = {
      '@type': 'TouristTrip',
      '@id': routeUrl,
      name: r.name,
      description: r.description || `${r.duration || ''} · ${r.distance || ''}`,
      url: pageUrl,
      touristType: ['RoadTrip', 'CulturalTourism', 'Ecotourism'],
    }
    if (r.distance) itemNode.distance = r.distance
    if (r.duration) itemNode.typicalAgeRange = r.duration
    if (r.stops && r.stops.length > 0) {
      itemNode.itinerary = {
        '@type': 'ItemList',
        numberOfItems: r.stops.length,
        itemListElement: r.stops.map((s, si) => ({
          '@type': 'ListItem',
          position: si + 1,
          name: s.name,
        })),
      }
    }
    return {
      '@type': 'ListItem',
      position: index + 1,
      item: itemNode,
    }
  })

  const itemListNode = {
    '@type': 'ItemList',
    '@id': `${pageUrl}#items`,
    name: 'Danh sách các tuyến đường du lịch gợi ý tại Vĩnh Long',
    description: 'Lộ trình khám phá tự túc qua các danh lam, làng nghề và cù lao.',
    numberOfItems: total,
    itemListElement: itemListElements,
  }

  const defaultFaqs = [
    {
      q: 'Nên chọn phương tiện gì để đi các tuyến đường khám phá Vĩnh Long?',
      a: 'Xe máy phù hợp nhất cho các cung đường miệt vườn ngõ nhỏ, cù lao và phà sông. Ô tô thuận tiện cho các tuyến trục quốc lộ và liên tỉnh kết nối Bến Tre, Trà Vinh.',
    },
    {
      q: 'Thời điểm nào trong năm thích hợp nhất để trải nghiệm các cung đường này?',
      a: 'Từ tháng 5 đến tháng 8 là mùa trái cây chín rộ tại cù lao An Bình; từ tháng 9 đến tháng 11 là mùa phù sa ven sông Tiền - sông Hậu với nhiều trải nghiệm đồng quê sông nước đặc sắc.',
    },
    {
      q: 'Các cung đường gợi ý có dễ tìm trạm xăng và điểm dừng chân nghỉ ngơi không?',
      a: 'Dọc các trục đường tỉnh lộ và quốc lộ đều có trạm xăng và quán cà phê võng ven sông mát mẻ. Khi vào sâu đường làng cù lao An Bình, nên đổ đầy bình xăng trước khi qua phà.',
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumbNode,
    itemListNode,
    faqNode,
  ])
}

export interface ContemporaryEventSchemaOptions {
  events?: Array<{
    id: string | number
    name: string
    summary?: string
    place_name?: string
    date_start?: string
    date_end?: string
  }>
  totalCount?: number
  todayGregorianLabel?: string
  todayLunarLabel?: string
  canonicalUrl?: string
  faqs?: Array<{ q: string; a: string }>
}

export function buildContemporaryEventSchemaGraph(options: ContemporaryEventSchemaOptions = {}): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/su-kien')
  const total = options.totalCount ?? (options.events?.length || 0)
  const title = 'Sự kiện & Hội chợ Vĩnh Long — Nhịp đập văn hóa & xúc tiến thương mại'
  const desc = 'Hội chợ, triển lãm nông nghiệp OCOP, ngày hội du lịch sông nước và festival gốm đỏ Mang Thít tại Vĩnh Long.'

  const webpageNode = {
    '@type': 'CollectionPage',
    '@id': `${pageUrl}#collection`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: {
      '@type': 'Thing',
      name: 'Sự kiện văn hóa và hội chợ thương mại Vĩnh Long',
      description: 'Các hoạt động sự kiện xúc tiến thương mại, ngày hội văn hóa và festival nghệ thuật tại Vĩnh Long.',
    },
    speakable: buildSpeakableSpecification([
      '.catalog-hero h1',
      '.dateline-eyebrow',
      '.now-banner',
      '.register-toggle',
      '.catalog-aeo-plaque__title',
      '.catalog-aeo-plaque__dek',
    ]),
  }

  const breadcrumbNode = {
    '@type': 'BreadcrumbList',
    '@id': `${pageUrl}#breadcrumb`,
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Sự kiện', item: pageUrl },
    ],
  }

  const eventListElements = (options.events || []).slice(0, 30).map((e, index) => {
    const eventUrl = canonicalUrl(entityPath(e.id))
    const itemNode: Record<string, any> = {
      '@type': 'Event',
      '@id': `${eventUrl}#event`,
      name: e.name,
      description: e.summary || e.name,
      url: eventUrl,
      eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
      eventStatus: 'https://schema.org/EventScheduled',
    }
    if (e.date_start) itemNode.startDate = e.date_start
    if (e.date_end) itemNode.endDate = e.date_end
    if (e.place_name) {
      itemNode.location = {
        '@type': 'Place',
        name: e.place_name,
        address: { '@type': 'PostalAddress', addressRegion: 'Vĩnh Long', addressCountry: 'VN' },
      }
    }
    return {
      '@type': 'ListItem',
      position: index + 1,
      item: itemNode,
    }
  })

  const itemListNode = {
    '@type': 'ItemList',
    '@id': `${pageUrl}#events`,
    name: 'Danh sách sự kiện và hội chợ tiêu biểu tại Vĩnh Long',
    description: 'Các sự kiện văn hóa, ngày hội du lịch và triển lãm thương mại.',
    numberOfItems: total,
    itemListElement: eventListElements,
  }

  const defaultFaqs = [
    {
      q: 'Vĩnh Long thường tổ chức những sự kiện hoặc hội chợ lớn nào trong năm?',
      a: 'Các sự kiện tiêu biểu gồm Ngày hội Du lịch Vĩnh Long, Ngày đồng hành cùng gốm đỏ Mang Thít, Hội chợ Xúc tiến Thương mại - Nông nghiệp cùng các giải đua ghe Ngo truyền thống trên sông.',
    },
    {
      q: 'Người dân và du khách có thể theo dõi lịch sự kiện sắp diễn ra ở đâu?',
      a: 'Trang Sự Kiện trên VinhLong360 cập nhật liên tục các sự kiện đang diễn ra và sắp khai mạc, kèm tiện ích xuất file .ics nhắc hẹn trực tiếp vào điện thoại.',
    },
    {
      q: 'Tham gia các sự kiện văn hóa và hội chợ tại Vĩnh Long có cần mua vé không?',
      a: 'Đa số các sự kiện văn hóa cộng đồng, hội chợ xúc tiến thương mại và ngày hội du lịch tại Vĩnh Long đều mở cửa miễn phí phục vụ nhân dân và du khách.',
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumbNode,
    itemListNode,
    faqNode,
  ])
}

export interface TourismCatalogSchemaOptions {
  items?: Array<{
    id: string | number
    name: string
    summary?: string
    type?: string
  }>
  totalCount?: number
  currentMonth?: number
  canonicalUrl?: string
  faqs?: Array<{ q: string; a: string }>
}

export function buildTourismCatalogSchemaGraph(options: TourismCatalogSchemaOptions = {}): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/du-lich')
  const total = options.totalCount ?? (options.items?.length || 0)
  const title = 'Du lịch Vĩnh Long — Chỉ mục khám phá 3 vùng sông nước Cửu Long'
  const desc = 'Trải nghiệm bản địa, điểm tham quan sinh thái, làng nghề gốm đỏ Mang Thít, cù lao An Bình và ẩm thực miệt vườn Vĩnh Long.'

  const webpageNode = {
    '@type': 'CollectionPage',
    '@id': `${pageUrl}#collection`,
    url: pageUrl,
    name: `${title} — vinhlong360`,
    description: desc,
    inLanguage: 'vi-VN',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    about: {
      '@type': 'TouristDestination',
      name: 'Điểm đến du lịch Vĩnh Long',
      description: 'Du lịch sinh thái, di sản làng nghề gốm Mang Thít và cù lao sông Tiền.',
      geo: { '@type': 'GeoShape', box: '9.8 105.8 10.4 106.7' },
    },
    speakable: buildSpeakableSpecification([
      '.atlas-hero-title',
      '.atlas-hero-eyebrow',
      '.catalog-route-trace',
      '.catalog-filter-ledger__header',
      '.catalog-aeo-plaque__title',
      '.catalog-aeo-plaque__dek',
    ]),
  }

  const breadcrumbNode = {
    '@type': 'BreadcrumbList',
    '@id': `${pageUrl}#breadcrumb`,
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Du lịch', item: pageUrl },
    ],
  }

  const itemListElements = (options.items || []).slice(0, 30).map((e, index) => {
    const itemUrl = canonicalUrl(entityPath(e.id))
    return {
      '@type': 'ListItem',
      position: index + 1,
      item: {
        '@type': 'TouristAttraction',
        '@id': `${itemUrl}#attraction`,
        name: e.name,
        description: e.summary || e.name,
        url: itemUrl,
      },
    }
  })

  const itemListNode = {
    '@type': 'ItemList',
    '@id': `${pageUrl}#items`,
    name: 'Danh mục điểm đến và trải nghiệm du lịch Vĩnh Long',
    description: 'Trải nghiệm bản địa, điểm tham quan, lưu trú, làng nghề và ẩm thực Vĩnh Long.',
    numberOfItems: total,
    itemListElement: itemListElements,
  }

  const defaultFaqs = [
    {
      q: 'Đi du lịch Vĩnh Long mùa nào trong năm là đẹp nhất?',
      a: 'Mùa trái cây chín rộ từ tháng 5 đến tháng 8 tại các vườn cù lao An Bình là thời điểm nhộn nhịp nhất. Ngoài ra, mùa phù sa từ tháng 9 đến tháng 11 mang đến trải nghiệm cảnh quan sông nước đặc sắc.',
    },
    {
      q: 'Những điểm đến du lịch nổi bật nhất tại Vĩnh Long gồm những nơi nào?',
      a: 'Du khách nên ghé thăm di sản đương đại lò gạch gốm đỏ Mang Thít, hệ thống nhà vườn cù lao An Bình, chùa Phật Ngọc Xá Lợi, làng bánh tráng cù lao Mây và các điểm sinh thái ven sông.',
    },
    {
      q: 'Phương tiện di chuyển phổ biến và thuận tiện nhất khi du lịch Vĩnh Long là gì?',
      a: 'Xe máy và ô tô thuận tiện để kết nối các tuyến đường liên huyện, kết hợp trải nghiệm đò ngang, phà sông hoặc xuồng chèo len lỏi qua các rạch nhỏ miệt vườn.',
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumbNode,
    itemListNode,
    faqNode,
  ])
}

export interface StayCatalogItem {
  id: string
  name: string
  summary?: string
  place_name?: string
  type?: string
}

export interface StayCatalogSchemaOptions {
  items: StayCatalogItem[]
  totalCount?: number
  typeCounts?: Record<string, number>
  canonicalUrl?: string
  faqs?: FaqItem[]
}

/**
 * Đồ thị tri thức hợp nhất danh mục Lưu trú & Nghỉ dưỡng Vĩnh Long (Mốc 145):
 * CollectionPage + LodgingBusiness/BedAndBreakfast ItemList + BreadcrumbList + GeoShape + FAQPage
 */
export function buildStayCatalogSchemaGraph(options: StayCatalogSchemaOptions): Record<string, any> {
  const pageUrl = options.canonicalUrl || canonicalUrl('/luu-tru')
  const total = options.totalCount ?? options.items.length

  const webpageNode: Record<string, any> = {
    '@type': 'CollectionPage',
    '@id': `${pageUrl}#collection`,
    url: pageUrl,
    name: 'Lưu trú Tỉnh Vĩnh Long',
    description: 'Hệ thống homestay miệt vườn cù lao, khách sạn trung tâm và khu nghỉ dưỡng sinh thái ven sông Tiền, Cổ Chiên.',
    inLanguage: 'vi',
    isPartOf: { '@id': `${SITE_URL}/#website` },
    breadcrumb: { '@id': `${pageUrl}#breadcrumb` },
    numberOfItems: total,
    about: [
      {
        '@type': 'Thing',
        name: 'Dịch vụ lưu trú và Homestay Vĩnh Long',
        description: 'Hệ thống homestay nhà vườn cù lao An Bình, khách sạn tiện nghi và khu nghỉ dưỡng ven sông tại Vĩnh Long.',
      },
      {
        '@type': 'TouristDestination',
        name: 'Vĩnh Long',
        description: 'Điểm đến du lịch sinh thái sông nước miệt vườn Mekong.',
      },
    ],
    spatialCoverage: {
      '@type': 'Place',
      name: 'Tỉnh Vĩnh Long',
      geo: {
        '@type': 'GeoShape',
        box: '10.0 105.8 10.4 106.2',
      },
    },
    speakable: buildSpeakableSpecification([
      '.catalog-hero h1',
      '.catalog-lead',
      '.catalog-type-breakdown',
      '.catalog-aeo-plaque__title',
      '.catalog-aeo-plaque__dek',
    ]),
  }

  const breadcrumbNode = {
    '@type': 'BreadcrumbList',
    '@id': `${pageUrl}#breadcrumb`,
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Lưu trú', item: pageUrl },
    ],
  }

  const itemListNode = {
    '@type': 'ItemList',
    '@id': `${pageUrl}#items`,
    name: 'Danh sách cơ sở lưu trú Vĩnh Long',
    description: 'Homestay miệt vườn cù lao An Bình, khách sạn trung tâm và khu nghỉ dưỡng sinh thái Vĩnh Long.',
    numberOfItems: total,
    itemListElement: options.items.slice(0, 30).map((item, index) => {
      const isHomestay = (item.type || '').toLowerCase().includes('homestay') || item.name.toLowerCase().includes('homestay')
      return {
        '@type': 'ListItem',
        position: index + 1,
        item: {
          '@type': isHomestay ? 'BedAndBreakfast' : 'LodgingBusiness',
          name: item.name,
          description: item.summary || undefined,
          url: `${SITE_URL}${entityPath(item.id)}`,
          ...(item.place_name ? {
            address: {
              '@type': 'PostalAddress',
              addressLocality: item.place_name,
              addressRegion: 'Vĩnh Long',
              addressCountry: 'VN',
            },
          } : {}),
        },
      }
    }),
  }

  const defaultFaqs: FaqItem[] = [
    {
      q: 'Vĩnh Long có những loại hình lưu trú nào phổ biến nhất?',
      a: 'Nổi bật nhất là các homestay miệt vườn tại cù lao An Bình với trải nghiệm ngủ nhà gỗ truyền thống Nam Bộ, sinh hoạt cùng gia đình chủ nhà và hái trái cây tại vườn. Ngoài ra còn có hệ thống khách sạn trung tâm thành phố và nhà nghỉ tiện nghi.',
    },
    {
      q: 'Du khách nên lưu ý điều gì khi đặt phòng homestay cù lao tại Vĩnh Long?',
      a: 'Nên liên hệ đặt trước vào các dịp cuối tuần, mùa lễ hội hoặc mùa trái cây rộ (tháng 5 đến tháng 8). Kiểm tra trước khung giờ hoạt động của phà hoặc đò sang cù lao để chủ động lịch trình di chuyển.',
    },
    {
      q: 'Các cơ sở lưu trú tại Vĩnh Long có cung cấp dịch vụ ẩm thực bản địa không?',
      a: 'Đa số các homestay sinh thái Vĩnh Long đều phục vụ bữa cơm gia đình nấu theo hương vị truyền thống địa phương với cá tai tượng chiên xù, canh chua cá lóc bông điên điển, cá kèo kho tộ và bánh xèo giòn rụm.',
    },
  ]

  const faqs = options.faqs && options.faqs.length > 0 ? options.faqs : defaultFaqs
  const faqNode = buildFaqPageSchema(faqs, `${pageUrl}#faq`)

  return buildUnifiedSchemaGraph([
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    webpageNode,
    breadcrumbNode,
    itemListNode,
    faqNode,
  ])
}
