// A2 — Per-page content manifest.
// Single source of truth for: (1) the default hero/SEO text of each content
// page, and (2) the admin field metadata that drives the reusable page editor
// at /admin/cai-dat/trang/[slug]. Adding a page = one entry here + one
// usePageContent() call in the page. No new admin component, no new backend.
//
// The CMS stores overrides under the single key `page.<slug>` (a JSON object of
// {field: value}). usePageContent(slug).f(field) returns the override when set,
// else the `default` below. So these defaults stay the canonical content and
// the site renders identically when no override exists / Postgres is down.

export type PageFieldType = 'text' | 'textarea' | 'url'

export interface PageField {
  field: string
  label: string
  input_type: PageFieldType
  description?: string
  default: string
}

export interface PageManifest {
  slug: string        // settings slug → key `page.<slug>`
  title: string       // admin display name
  icon: string        // hub card emoji
  route: string       // public route (for the "view page" link)
  fields: PageField[]
}

/** Standard hero + SEO field set shared by catalog pages. */
function heroSeoFields(o: {
  heroTitle: string
  heroSubtitle: string
  seoTitle: string
  seoDescription: string
  ogTitle?: string
  ogDescription?: string
}): PageField[] {
  return [
    { field: 'hero_title', label: 'Tiêu đề hero (H1)', input_type: 'text', default: o.heroTitle, description: 'Tiêu đề lớn đầu trang' },
    { field: 'hero_subtitle', label: 'Mô tả hero', input_type: 'textarea', default: o.heroSubtitle, description: 'Dòng mô tả dưới tiêu đề' },
    { field: 'seo_title', label: 'SEO title', input_type: 'text', default: o.seoTitle, description: 'Thẻ <title> cho công cụ tìm kiếm' },
    { field: 'seo_description', label: 'SEO description', input_type: 'textarea', default: o.seoDescription, description: 'Meta description' },
    { field: 'og_title', label: 'OG title (chia sẻ MXH)', input_type: 'text', default: o.ogTitle ?? o.seoTitle, description: 'Tiêu đề khi chia sẻ link' },
    { field: 'og_description', label: 'OG description', input_type: 'textarea', default: o.ogDescription ?? o.seoDescription, description: 'Mô tả khi chia sẻ link' },
  ]
}

export const PAGE_MANIFESTS: Record<string, PageManifest> = {
  du_lich: {
    slug: 'du_lich', title: 'Du lịch & trải nghiệm', icon: '🌿', route: '/du-lich',
    fields: heroSeoFields({
      heroTitle: 'Du lịch & trải nghiệm',
      heroSubtitle: 'Miệt vườn sông nước, cù lao xanh mát, làng nghề trăm năm — khám phá miền Tây theo cách của người bản địa.',
      seoTitle: 'Du lịch Vĩnh Long, Bến Tre, Trà Vinh — vinhlong360',
      seoDescription: 'Trải nghiệm bản địa, điểm tham quan, lưu trú, làng nghề và ẩm thực khắp Vĩnh Long, Bến Tre, Trà Vinh. Lọc theo loại hình, mùa vụ và khu vực.',
      ogTitle: 'Du lịch miền Tây — vinhlong360',
      ogDescription: 'Trải nghiệm miệt vườn, điểm tham quan, làng nghề và ẩm thực khắp Vĩnh Long.',
    }),
  },
}

export const PAGE_MANIFEST_LIST: PageManifest[] = Object.values(PAGE_MANIFESTS)

export function getPageManifest(slug: string): PageManifest | undefined {
  return PAGE_MANIFESTS[slug]
}

export function pageFieldDefault(slug: string, field: string): string {
  return PAGE_MANIFESTS[slug]?.fields.find(f => f.field === field)?.default ?? ''
}
