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

