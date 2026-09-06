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
    speakable: buildSpeakableSpecification(['.lead', 'h1', '.timeline-head']),
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
    speakable: buildSpeakableSpecification(['.about-intro', 'h1', '.about-mission-quote', '#ban-bien-tap']),
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
    speakable: buildSpeakableSpecification(['.bm-inner h1', '.bm-sub', '.bm-sla', '.contact-quote', '.contact-cards h2']),
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
    speakable: buildSpeakableSpecification(['.catalog-hero-inner h1', '.catalog-hero-inner p', '.almanac-stats']),
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
    speakable: buildSpeakableSpecification(['.bm-inner h1', '.bm-sub', '.section-intro', '#bat-dau h2']),
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
    speakable: buildSpeakableSpecification(['.bxh-h1', '.bxh-head p', '.bxh-eyebrow']),
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
    speakable: buildSpeakableSpecification(['.guide-hero h1', '.guide-hero p', '.guide-section h2', '.guide-intro']),
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




