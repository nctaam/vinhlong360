<template>
  <section class="block band catalog-cross reveal" :aria-label="title || 'Khám phá thêm'">
    <h2>{{ title || 'Khám phá thêm' }}</h2>
    <p v-if="subtitle" class="cross-sub">{{ subtitle }}</p>
    <div class="cross-links">
      <NuxtLink
        v-for="c in computedLinks"
        :key="c.to"
        :to="c.to"
        :no-prefetch="c.noPrefetch"
        class="cross-card"
      >
        <span class="cross-icon" aria-hidden="true">
          <IconLine :name="c.icon" />
        </span>
        <div>
          <strong>{{ c.label }}</strong>
          <p>{{ c.desc }}</p>
        </div>
      </NuxtLink>
    </div>
  </section>
</template>

<script setup lang="ts">
export interface CatalogCrossLinkItem {
  to: string
  label: string
  desc: string
  icon: string
  noPrefetch?: boolean
}

const props = withDefaults(defineProps<{
  title?: string
  subtitle?: string
  links?: CatalogCrossLinkItem[]
}>(), {
  title: 'Khám phá thêm',
  subtitle: '',
  links: undefined,
})

const route = useRoute()

const DEFAULT_CATALOG_CROSS_LINKS: Record<string, CatalogCrossLinkItem[]> = {
  '/danh-ba': [
    { to: '/du-lich', label: 'Du lịch', desc: 'Trải nghiệm miệt vườn', icon: 'leaf' },
    { to: '/ban-do', label: 'Bản đồ', desc: 'Xem trên bản đồ', icon: 'map', noPrefetch: true },
    { to: '/lich-trinh', label: 'Lịch trình', desc: 'Tuyến đi sẵn', icon: 'calendar' },
    { to: '/lien-he', label: 'Liên hệ', desc: 'Góp ý & báo sai', icon: 'message' },
  ],
  '/le-hoi': [
    { to: '/su-kien', label: 'Sự kiện', desc: 'Festival, hội chợ', icon: 'lantern' },
    { to: '/du-lich', label: 'Du lịch', desc: 'Trải nghiệm miệt vườn', icon: 'leaf' },
    { to: '/lich-trinh', label: 'Lịch trình', desc: 'Tuyến đi sẵn', icon: 'calendar' },
    { to: '/ban-do', label: 'Bản đồ', desc: 'Xem trên bản đồ', icon: 'map', noPrefetch: true },
  ],
  '/su-kien': [
    { to: '/le-hoi', label: 'Lễ hội', desc: 'Truyền thống văn hóa', icon: 'lantern' },
    { to: '/du-lich', label: 'Du lịch', desc: 'Trải nghiệm miệt vườn', icon: 'leaf' },
    { to: '/lich-trinh', label: 'Lịch trình', desc: 'Tuyến đi sẵn', icon: 'calendar' },
    { to: '/ban-do', label: 'Bản đồ', desc: 'Xem trên bản đồ', icon: 'map', noPrefetch: true },
  ],
  '/tuyen-duong': [
    { to: '/ban-do', label: 'Bản đồ', desc: 'Xem trên bản đồ', icon: 'map', noPrefetch: true },
    { to: '/lich-trinh', label: 'Lịch trình', desc: 'Tuyến đi sẵn', icon: 'calendar' },
    { to: '/du-lich', label: 'Du lịch', desc: 'Trải nghiệm miệt vườn', icon: 'leaf' },
    { to: '/luu-tru', label: 'Lưu trú', desc: 'Homestay, nhà vườn', icon: 'home' },
  ],
  '/theo-mua': [
    { to: '/san-pham', label: 'Đặc sản', desc: 'Tất cả sản phẩm', icon: 'fruit' },
    { to: '/ocop', label: 'OCOP', desc: 'Sản phẩm đạt chuẩn', icon: 'star' },
    { to: '/du-lich', label: 'Du lịch', desc: 'Trải nghiệm miệt vườn', icon: 'leaf' },
    { to: '/kham-pha/am-thuc', label: 'Ẩm thực', desc: 'Món ngon Vĩnh Long', icon: 'bowl' },
  ],
  '/lich-trinh': [
    { to: '/du-lich', label: 'Du lịch', desc: 'Trải nghiệm miệt vườn', icon: 'leaf' },
    { to: '/luu-tru', label: 'Lưu trú', desc: 'Homestay, nhà vườn', icon: 'home' },
    { to: '/ban-do', label: 'Bản đồ', desc: 'Xem trên bản đồ', icon: 'map', noPrefetch: true },
    { to: '/san-pham', label: 'Đặc sản', desc: 'Mua quà Vĩnh Long', icon: 'fruit' },
  ],
  '/luu-tru': [
    { to: '/san-pham', label: 'Đặc sản', desc: 'Trái cây, bánh kẹo miệt vườn', icon: 'fruit' },
    { to: '/lich-trinh', label: 'Lịch trình', desc: 'Tuyến đi sẵn khám phá nhanh', icon: 'calendar' },
    { to: '/ban-do', label: 'Bản đồ', desc: 'Xem địa điểm quanh nơi nghỉ', icon: 'map', noPrefetch: true },
  ],
  '/san-pham': [
    { to: '/ocop', label: 'OCOP', desc: 'Sản phẩm đã đánh giá sao OCOP', icon: 'star' },
    { to: '/theo-mua', label: 'Theo mùa', desc: 'Nông sản theo mùa vụ Vĩnh Long', icon: 'calendar' },
    { to: '/lich-trinh', label: 'Lịch trình', desc: 'Điểm mua sắm trong tour', icon: 'calendar' },
    { to: '/ban-do', label: 'Bản đồ', desc: 'Điểm bán, vựa trái cây quanh bạn', icon: 'map', noPrefetch: true },
  ],
  '/ocop': [
    { to: '/san-pham', label: 'Đặc sản', desc: 'Toàn bộ sản phẩm quà tặng', icon: 'fruit' },
    { to: '/lich-trinh', label: 'Lịch trình', desc: 'Ghé điểm OCOP trong tour', icon: 'calendar' },
    { to: '/ban-do', label: 'Bản đồ', desc: 'Xem điểm bán OCOP trên bản đồ', icon: 'map', noPrefetch: true },
  ],
  '/tim-kiem': [
    { to: '/ban-do', label: 'Bản đồ', desc: 'Xem trên bản đồ', icon: 'map', noPrefetch: true },
    { to: '/theo-mua', label: 'Theo mùa', desc: 'Đúng mùa thưởng thức', icon: 'calendar' },
    { to: '/cong-dong', label: 'Cộng đồng', desc: 'Hỏi đáp & chia sẻ', icon: 'message' },
    { to: '/danh-ba', label: 'Danh bạ', desc: 'Hành chính xã/phường', icon: 'bookmark' },
  ],
}

const FALLBACK_LINKS: CatalogCrossLinkItem[] = [
  { to: '/du-lich', label: 'Du lịch', desc: 'Trải nghiệm miệt vườn', icon: 'leaf' },
  { to: '/ban-do', label: 'Bản đồ', desc: 'Xem trên bản đồ', icon: 'map', noPrefetch: true },
  { to: '/lich-trinh', label: 'Lịch trình', desc: 'Tuyến đi sẵn', icon: 'calendar' },
  { to: '/san-pham', label: 'Đặc sản', desc: 'Mua quà Vĩnh Long', icon: 'fruit' },
]

const computedLinks = computed<CatalogCrossLinkItem[]>(() => {
  if (props.links && props.links.length > 0) return props.links

  const path = route.path.replace(/\/$/, '') || '/'
  const matched = DEFAULT_CATALOG_CROSS_LINKS[path]
  if (matched) return matched

  return FALLBACK_LINKS.filter(link => link.to !== path).slice(0, 4)
})
</script>
