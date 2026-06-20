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
  ocop: {
    slug: 'ocop', title: 'Sản phẩm OCOP', icon: '⭐', route: '/ocop',
    fields: heroSeoFields({
      heroTitle: 'Sản phẩm OCOP',
      heroSubtitle: 'Mỗi xã một sản phẩm — sản phẩm đạt chuẩn OCOP từ Vĩnh Long, Bến Tre và Trà Vinh, chất lượng được chứng nhận.',
      seoTitle: 'Sản phẩm OCOP Vĩnh Long — Mỗi xã một sản phẩm — vinhlong360',
      seoDescription: 'Sản phẩm đạt chuẩn OCOP (Mỗi xã một sản phẩm) từ Vĩnh Long, Bến Tre, Trà Vinh — đặc sản theo mùa, xếp hạng sao. Lọc theo số sao, khu vực và mùa vụ.',
      ogTitle: 'Sản phẩm OCOP miền Tây — vinhlong360',
      ogDescription: 'Sản phẩm đạt chuẩn OCOP 3-5 sao từ Vĩnh Long, Bến Tre, Trà Vinh.',
    }),
  },
  san_pham: {
    slug: 'san_pham', title: 'Đặc sản địa phương', icon: '🧺', route: '/san-pham',
    fields: heroSeoFields({
      heroTitle: 'Đặc sản địa phương',
      heroSubtitle: 'Trái cây theo mùa, đặc sản làm quà, sản phẩm OCOP — biết mùa nào ngon, mua ở đâu, ai sản xuất.',
      seoTitle: 'Đặc sản & sản phẩm OCOP Vĩnh Long — vinhlong360',
      seoDescription: 'Đặc sản & sản phẩm OCOP Vĩnh Long theo mùa — biết mùa nào ngon, mua ở đâu, ai sản xuất. Lọc theo mùa vụ, sao OCOP và khu vực miền Tây.',
      ogTitle: 'Đặc sản Vĩnh Long theo mùa — vinhlong360',
      ogDescription: 'Sản phẩm OCOP, trái cây, đặc sản miệt vườn theo mùa vụ.',
    }),
  },
  luu_tru: {
    slug: 'luu_tru', title: 'Lưu trú', icon: '🏡', route: '/luu-tru',
    fields: heroSeoFields({
      heroTitle: 'Lưu trú',
      heroSubtitle: 'Homestay miệt vườn, nhà nghỉ ven sông, khách sạn phố — chọn nơi nghỉ phù hợp cho chuyến đi miền Tây.',
      seoTitle: 'Lưu trú Vĩnh Long — Homestay, nhà vườn, khách sạn — vinhlong360',
      seoDescription: 'Homestay, nhà vườn, khách sạn và nơi nghỉ ở Vĩnh Long, Bến Tre, Trà Vinh — chọn chỗ ở phù hợp cho chuyến đi.',
      ogTitle: 'Lưu trú miền Tây — vinhlong360',
      ogDescription: 'Homestay, nhà vườn, khách sạn và nơi nghỉ ở Vĩnh Long, Bến Tre, Trà Vinh.',
    }),
  },
  le_hoi: {
    slug: 'le_hoi', title: 'Lễ hội truyền thống', icon: '🎭', route: '/le-hoi',
    fields: heroSeoFields({
      heroTitle: 'Lễ hội truyền thống',
      heroSubtitle: 'Lễ hội đình miếu, lễ Khmer, Nghinh Ông, giỗ danh nhân — truyền thống văn hóa ba vùng Vĩnh Long, Bến Tre, Trà Vinh.',
      seoTitle: 'Lễ hội truyền thống — vinhlong360',
      seoDescription: 'Lễ hội đình miếu, lễ Khmer, Nghinh Ông, giỗ danh nhân — truyền thống văn hóa Vĩnh Long, Bến Tre, Trà Vinh.',
      ogTitle: 'Lễ hội truyền thống — vinhlong360',
      ogDescription: 'Lịch lễ hội truyền thống miền Tây: Kỳ Yên, Ok Om Bok, Nghinh Ông, giỗ danh nhân và hơn thế.',
    }),
  },
  su_kien: {
    slug: 'su_kien', title: 'Sự kiện', icon: '📅', route: '/su-kien',
    fields: heroSeoFields({
      heroTitle: 'Sự kiện',
      heroSubtitle: 'Sự kiện văn hóa, hội chợ, festival và hoạt động sắp diễn ra tại Vĩnh Long, Bến Tre, Trà Vinh.',
      seoTitle: 'Sự kiện — vinhlong360',
      seoDescription: 'Sự kiện văn hóa, hội chợ, festival và hoạt động sắp diễn ra tại Vĩnh Long, Bến Tre, Trà Vinh.',
      ogTitle: 'Sự kiện — vinhlong360',
      ogDescription: 'Lịch sự kiện miền Tây: hội chợ, festival, marathon và hơn thế.',
    }),
  },
  theo_mua: {
    slug: 'theo_mua', title: 'Theo mùa', icon: '🗓️', route: '/theo-mua',
    fields: [
      { field: 'hero_title', label: 'Tiêu đề hero (H1)', input_type: 'text', default: 'Tháng {month} — đi đâu, ăn gì?', description: 'Để trống = tự điền tháng hiện tại. Nhập text = cố định (mất số tháng động).' },
      { field: 'hero_subtitle', label: 'Mô tả hero', input_type: 'textarea', default: 'Trải nghiệm, đặc sản & món ăn đang vào mùa ở Vĩnh Long, Bến Tre, Trà Vinh.' },
      { field: 'seo_title', label: 'SEO title', input_type: 'text', default: 'Theo mùa: đi đâu, ăn gì ở Vĩnh Long — vinhlong360', description: 'Để trống = tự điền tháng hiện tại.' },
      { field: 'seo_description', label: 'SEO description', input_type: 'textarea', default: 'Trải nghiệm, đặc sản và món ăn đang vào mùa theo từng tháng tại Vĩnh Long, Bến Tre, Trà Vinh.' },
      { field: 'og_title', label: 'OG title (chia sẻ MXH)', input_type: 'text', default: 'Bản đồ trải nghiệm theo mùa — vinhlong360' },
      { field: 'og_description', label: 'OG description', input_type: 'textarea', default: 'Tháng này miền Tây có gì? Khám phá đặc sản & trải nghiệm đúng mùa.' },
    ],
  },
  danh_ba: {
    slug: 'danh_ba', title: 'Danh bạ hành chính', icon: '🏛️', route: '/danh-ba',
    fields: heroSeoFields({
      heroTitle: 'Danh bạ hành chính',
      heroSubtitle: 'Địa chỉ & liên hệ UBND, công an và cơ quan công vụ theo từng xã/phường của tỉnh Vĩnh Long (sau hợp nhất: Vĩnh Long · Bến Tre · Trà Vinh).',
      seoTitle: 'Danh bạ hành chính xã/phường — vinhlong360',
      seoDescription: 'Địa chỉ, số điện thoại UBND, công an và cơ quan công vụ theo xã/phường tỉnh Vĩnh Long (Vĩnh Long, Bến Tre, Trà Vinh).',
      ogTitle: 'Danh bạ hành chính xã/phường — vinhlong360',
      ogDescription: 'Địa chỉ, số điện thoại UBND, công an và cơ quan công vụ theo xã/phường tỉnh Vĩnh Long (Vĩnh Long, Bến Tre, Trà Vinh).',
    }),
  },
  tuyen_duong: {
    slug: 'tuyen_duong', title: 'Tuyến đường gợi ý', icon: '🛣️', route: '/tuyen-duong',
    fields: heroSeoFields({
      heroTitle: 'Tuyến đường gợi ý',
      heroSubtitle: 'Các vòng khám phá tự lái / xe máy qua miệt vườn, làng nghề và văn hóa bản địa — chọn vòng, lên xe và đi.',
      seoTitle: 'Tuyến đường gợi ý — Vòng khám phá miền Tây — vinhlong360',
      seoDescription: 'Các tuyến đường tự khám phá qua miệt vườn, làng nghề và văn hóa Vĩnh Long, Bến Tre, Trà Vinh. Vòng trái cây, vòng dừa, vòng chùa Khmer.',
      ogTitle: 'Tuyến đường gợi ý — vinhlong360',
      ogDescription: 'Vòng trái cây, vòng dừa, vòng chùa Khmer — tuyến tự khám phá miền Tây.',
    }),
  },
  cong_dong: {
    slug: 'cong_dong', title: 'Cộng đồng', icon: '💬', route: '/cong-dong',
    fields: [
      { field: 'hero_title', label: 'Tiêu đề (ẩn, cho screen-reader & SEO)', input_type: 'text', default: 'Cộng đồng vinhlong360' },
      { field: 'seo_title', label: 'SEO title', input_type: 'text', default: 'Cộng đồng du lịch Vĩnh Long — vinhlong360' },
      { field: 'seo_description', label: 'SEO description', input_type: 'textarea', default: 'Chia sẻ trải nghiệm, đánh giá và kết nối với cộng đồng yêu du lịch Vĩnh Long, Bến Tre, Trà Vinh.' },
      { field: 'og_title', label: 'OG title (chia sẻ MXH)', input_type: 'text', default: 'Cộng đồng — vinhlong360' },
      { field: 'og_description', label: 'OG description', input_type: 'textarea', default: 'Chia sẻ trải nghiệm, đánh giá và kết nối với cộng đồng yêu du lịch miền Tây.' },
    ],
  },
  tim_kiem: {
    slug: 'tim_kiem', title: 'Tìm kiếm', icon: '🔍', route: '/tim-kiem',
    fields: heroSeoFields({
      heroTitle: 'Tìm kiếm',
      heroSubtitle: 'Tìm đặc sản, trải nghiệm, lưu trú, lễ hội — mọi thứ về Vĩnh Long, Bến Tre, Trà Vinh.',
      seoTitle: 'Tìm kiếm — vinhlong360',
      seoDescription: 'Tìm kiếm đặc sản, trải nghiệm, lưu trú tại Vĩnh Long.',
      ogTitle: 'Tìm kiếm — vinhlong360',
      ogDescription: 'Tìm kiếm đặc sản, trải nghiệm, lưu trú tại Vĩnh Long.',
    }),
  },
  lien_he: {
    slug: 'lien_he', title: 'Liên hệ', icon: '📬', route: '/lien-he',
    fields: heroSeoFields({
      heroTitle: 'Liên hệ',
      heroSubtitle: 'vinhlong360.vn — Mạng xã hội du lịch & đặc sản Vĩnh Long · Bến Tre · Trà Vinh',
      seoTitle: 'Liên hệ — vinhlong360',
      seoDescription: 'Liên hệ vinhlong360.vn: yêu cầu dữ liệu cá nhân, báo cáo vi phạm, khiếu nại bản quyền, đăng ký quản lý trang.',
      ogTitle: 'Liên hệ — vinhlong360',
      ogDescription: 'Liên hệ vinhlong360.vn: yêu cầu, báo cáo vi phạm, hợp tác quảng bá.',
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
