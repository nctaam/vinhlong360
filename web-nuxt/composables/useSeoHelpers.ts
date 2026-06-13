export const SITE_URL = 'https://vinhlong360.vn'

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

export function itemListJsonLd(name: string, description: string, path: string, items: any[] = []) {
  return {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name,
    description,
    url: canonicalUrl(path),
    mainEntity: {
      '@type': 'ItemList',
      itemListElement: items.slice(0, 24).map((item: any, index: number) => ({
        '@type': 'ListItem',
        position: index + 1,
        name: item.name || item.title || item.id,
        url: item.id ? entityDetailUrl(String(item.id)) : undefined,
      })).map((item: Record<string, any>) => Object.fromEntries(Object.entries(item).filter(([, value]) => value !== undefined))),
    },
  }
}

export function itineraryItemListJsonLd(name: string, description: string, path: string, items: any[] = []) {
  return {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name,
    description,
    url: canonicalUrl(path),
    mainEntity: {
      '@type': 'ItemList',
      itemListElement: items.slice(0, 24).map((item: any, index: number) => ({
        '@type': 'ListItem',
        position: index + 1,
        name: item.title || item.name || item.id,
        url: item.id ? itineraryUrl(String(item.id)) : undefined,
      })).map((item: Record<string, any>) => Object.fromEntries(Object.entries(item).filter(([, value]) => value !== undefined))),
    },
  }
}
