export const SITE_URL = 'https://vinhlong360.vn'
const DEFAULT_OG = `${SITE_URL}/img/og-default.jpg`

export function entityOgImage(images?: string[] | null, fallback = DEFAULT_OG): string {
  if (Array.isArray(images) && images.length && images[0]) {
    const src = images[0]
    return src.startsWith('http') ? src : `${SITE_URL}${src.startsWith('/') ? '' : '/'}${src}`
  }
  return fallback
}

export function safeJsonLd(obj: unknown): string {
  return JSON.stringify(obj).replace(/<\//g, '<\\/')
}

export function canonicalUrl(path = '/') {
  const clean = path.split('#')[0].split('?')[0] || '/'
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
