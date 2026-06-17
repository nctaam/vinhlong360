<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Tuyến đường gợi ý' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-route">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon">🛤️</span>
        <div>
          <h1>Tuyến đường gợi ý</h1>
          <p>Các vòng khám phá tự lái / xe máy qua miệt vườn, làng nghề và văn hóa bản địa — chọn vòng, lên xe và đi.</p>
        </div>
      </div>
      <div class="catalog-stats">
        <div class="stat-item">
          <span class="stat-num">{{ ROUTES.length }}</span>
          <span class="stat-label">tuyến đường</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">3</span>
          <span class="stat-label">khu vực</span>
        </div>
      </div>
    </section>

    <div class="controls">
      <p class="control-label">Khu vực</p>
      <div class="chip-row">
        <button :class="['chip', { active: areaFilter === 'all' }]" @click="areaFilter = 'all'">Tất cả</button>
        <button
          v-for="(meta, key) in AREA_META"
          :key="key"
          :class="['chip', { active: areaFilter === key }]"
          @click="areaFilter = key as string"
        >{{ meta.emoji }} {{ meta.name }}</button>
      </div>
    </div>

    <div class="route-grid">
      <div v-for="r in filtered" :key="r.id" class="route-card">
        <div :class="['route-header', `area-${r.area}`]">
          <span class="route-emoji">{{ r.emoji }}</span>
          <div>
            <h2>{{ r.name }}</h2>
            <span class="route-meta">{{ r.duration }} · {{ r.distance }}</span>
          </div>
        </div>
        <div class="route-body">
          <p>{{ r.description }}</p>
          <h3>Điểm dừng chân</h3>
          <ol class="route-stops">
            <li v-for="(stop, i) in r.stops" :key="i">
              <strong>{{ stop.name }}</strong>
              <span v-if="stop.note"> — {{ stop.note }}</span>
            </li>
          </ol>
          <div class="route-tips" v-if="r.tips">
            <strong>💡 Mẹo:</strong> {{ r.tips }}
          </div>
          <div class="route-links">
            <NuxtLink :to="`/khu-vuc/${r.area}`" class="btn btn-outline btn-sm">📍 {{ AREA_META[r.area]?.name }}</NuxtLink>
            <NuxtLink to="/ban-do" no-prefetch class="btn btn-ghost btn-sm">🗺️ Xem bản đồ</NuxtLink>
          </div>
        </div>
      </div>
    </div>

    <!-- Cross-links -->
    <section class="block catalog-cross reveal">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon">🗓️</span>
          <div><strong>Lịch trình</strong><p>Tuyến đi sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm miệt vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/luu-tru" class="cross-card">
          <span class="cross-icon">🏡</span>
          <div><strong>Lưu trú</strong><p>Homestay, nhà vườn</p></div>
        </NuxtLink>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'

useReveal()

const areaFilter = ref('all')

const ROUTES = [
  {
    id: 'vong-trai-cay-vinh-long',
    name: 'Vòng trái cây Vĩnh Long',
    emoji: '🍊',
    area: 'vinh-long',
    duration: '1 ngày',
    distance: '~40 km',
    description: 'Vòng lặp qua các vườn trái cây dọc cù lao An Bình và Bình Hòa Phước — thưởng thức trái cây tại vườn, ghé homestay miệt vườn và tận hưởng sông nước.',
    stops: [
      { name: 'Bến phà An Bình', note: 'Xuất phát từ TP Vĩnh Long' },
      { name: 'Vườn chôm chôm cù lao An Bình', note: 'Hái và thưởng thức tại vườn' },
      { name: 'Vườn nhãn Bình Hòa Phước', note: 'Mùa nhãn T5-T7' },
      { name: 'Homestay miệt vườn', note: 'Nghỉ trưa, ăn cơm vườn' },
      { name: 'Vườn bưởi Năm Roi', note: 'Đặc sản Vĩnh Long' },
      { name: 'Chợ Vĩnh Long', note: 'Mua đặc sản mang về' },
    ],
    tips: 'Đi vào mùa chôm chôm (T5-T7) để tận hưởng trọn vẹn. Mang theo mũ, kem chống nắng.',
  },
  {
    id: 'vong-dua-ben-tre',
    name: 'Vòng dừa Bến Tre',
    emoji: '🥥',
    area: 'ben-tre',
    duration: '1 ngày',
    distance: '~35 km',
    description: 'Khám phá xứ dừa từ gốc đến thành phẩm — thăm rẫy dừa, cơ sở kẹo dừa, xưởng mật hoa dừa và thưởng thức ẩm thực dừa.',
    stops: [
      { name: 'Cồn Phụng', note: 'Di tích + vườn dừa' },
      { name: 'Cơ sở kẹo dừa', note: 'Xem quy trình làm kẹo, mua sỉ' },
      { name: 'Xưởng mật hoa dừa', note: 'Sản phẩm OCOP 4 sao' },
      { name: 'Vườn bưởi da xanh', note: 'Trái cây đặc trưng Bến Tre' },
      { name: 'Chợ Bến Tre', note: 'Đặc sản: bánh tráng, bánh phồng' },
    ],
    tips: 'Kết hợp chèo xuồng trên rạch dừa. Nên đi sáng sớm để tránh nắng.',
  },
  {
    id: 'vong-chua-khmer-tra-vinh',
    name: 'Vòng chùa Khmer Trà Vinh',
    emoji: '🛕',
    area: 'tra-vinh',
    duration: '1–2 ngày',
    distance: '~60 km',
    description: 'Tuyến văn hóa Khmer độc đáo — ghé thăm các chùa cổ hàng trăm năm, ao Bà Om huyền thoại và thưởng thức bún nước lèo chính gốc.',
    stops: [
      { name: 'Ao Bà Om', note: 'Di tích lịch sử, cây cổ thụ' },
      { name: 'Chùa Âng', note: 'Chùa Khmer cổ nhất Trà Vinh' },
      { name: 'Chùa Hang', note: 'Kiến trúc hang động độc đáo' },
      { name: 'Làng Khmer', note: 'Tìm hiểu đời sống văn hóa' },
      { name: 'Quán bún nước lèo', note: 'Món đặc trưng Trà Vinh' },
      { name: 'Vườn dừa sáp Cầu Kè', note: 'Dừa sáp chỉ có ở đây' },
    ],
    tips: 'Mặc trang phục lịch sự khi vào chùa. Nên thuê xe máy cho linh hoạt.',
  },
  {
    id: 'vong-lang-nghe-mang-thit',
    name: 'Vòng làng nghề Mang Thít',
    emoji: '🏺',
    area: 'vinh-long',
    duration: 'Nửa ngày',
    distance: '~20 km',
    description: 'Khám phá "vương quốc gạch gốm" — thăm các lò gốm truyền thống, xem nghệ nhân tạo hình và mua gốm thủ công mang về.',
    stops: [
      { name: 'Làng gốm Mang Thít', note: 'Hàng trăm lò gốm dọc sông' },
      { name: 'Xưởng gốm truyền thống', note: 'Xem nghệ nhân làm gốm' },
      { name: 'Lò gạch cổ', note: 'Chụp ảnh, tìm hiểu lịch sử' },
      { name: 'Chợ gốm', note: 'Mua sản phẩm gốm thủ công' },
    ],
    tips: 'Kết hợp với Vòng trái cây cho chuyến đi trọn ngày. Đi buổi sáng khi lò đang hoạt động.',
  },
  {
    id: 'vong-am-thuc-mien-tay',
    name: 'Vòng ẩm thực miền Tây',
    emoji: '🍲',
    area: 'vinh-long',
    duration: '1–2 ngày',
    distance: '~50 km',
    description: 'Tour ẩm thực xuyên 3 tỉnh — từ bánh xèo Vĩnh Long, kẹo dừa Bến Tre đến bún nước lèo Trà Vinh.',
    stops: [
      { name: 'Quán cháo cá lóc Vĩnh Long', note: 'Bữa sáng đậm chất miền Tây' },
      { name: 'Bánh xèo miệt vườn', note: 'Cuốn rau vườn, chấm nước mắm' },
      { name: 'Chợ Vĩnh Long', note: 'Ăn vặt: hủ tiếu, bánh tầm' },
      { name: 'Kẹo dừa Bến Tre', note: 'Nếm + mua về làm quà' },
      { name: 'Bún nước lèo Trà Vinh', note: 'Món Khmer không thể bỏ qua' },
    ],
    tips: 'Đi vào cuối tuần để trải nghiệm chợ phiên. Mang dạ dày trống!',
  },
  {
    id: 'vong-mua-nuoc-noi',
    name: 'Vòng mùa nước nổi',
    emoji: '🌊',
    area: 'vinh-long',
    duration: '1 ngày',
    distance: '~30 km',
    description: 'Trải nghiệm mùa nước nổi (T8-T11) — hái bông điên điển, bắt cá linh, thưởng thức lẩu cá linh bông điên điển giữa đồng nước.',
    stops: [
      { name: 'Cánh đồng mùa nước nổi', note: 'Hái bông điên điển, bông súng' },
      { name: 'Điểm bắt cá linh', note: 'Trải nghiệm đánh bắt cùng nông dân' },
      { name: 'Quán lẩu cá linh', note: 'Món đặc trưng mùa nước nổi' },
      { name: 'Đồng sen', note: 'Chụp ảnh, hái sen (nếu có)' },
    ],
    tips: 'Chỉ có từ tháng 8 đến tháng 11. Mang áo mưa và giày chống nước.',
  },
]

const filtered = computed(() => {
  if (areaFilter.value === 'all') return ROUTES
  return ROUTES.filter(r => r.area === areaFilter.value)
})

useFilterUrl({ vung: areaFilter }, { vung: 'all' })

useSeoMeta({
  title: 'Tuyến đường gợi ý — Vòng khám phá miền Tây — vinhlong360',
  description: 'Các tuyến đường tự khám phá qua miệt vườn, làng nghề và văn hóa Vĩnh Long, Bến Tre, Trà Vinh. Vòng trái cây, vòng dừa, vòng chùa Khmer.',
  ogTitle: 'Tuyến đường gợi ý — vinhlong360',
  ogDescription: 'Vòng trái cây, vòng dừa, vòng chùa Khmer — tuyến tự khám phá miền Tây.',
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/tuyen-duong') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'Tuyến đường gợi ý miền Tây',
      description: 'Các tuyến đường tự khám phá qua miệt vườn, làng nghề và văn hóa Vĩnh Long, Bến Tre, Trà Vinh.',
      url: 'https://vinhlong360.vn/tuyen-duong',
    }),
  }],
})
</script>

<style scoped>
.route-grid { display: flex; flex-direction: column; gap: var(--space-6); }
.route-card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow); transition: transform var(--duration-normal) var(--ease-spring), box-shadow var(--duration-normal) var(--ease-out), border-color var(--duration-fast); }
.route-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--border); }
.route-card:active { transform: translateY(0) scale(.99); transition-duration: .08s; }
.route-header { display: flex; gap: var(--space-3); align-items: center; padding: var(--space-5) var(--space-6); color: #fff; }
.route-header h2 { margin: 0; font-size: var(--text-lg); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); }
.route-meta { font-size: var(--text-sm); opacity: .9; }
.route-emoji { font-size: var(--text-3xl); }
.route-header.area-vinh-long { background: var(--cat-experience); }
.route-header.area-ben-tre { background: var(--cat-product); }
.route-header.area-tra-vinh { background: var(--cat-attraction); }
.route-body { padding: var(--space-5) var(--space-6); }
.route-body p { margin: 0 0 var(--space-3); line-height: var(--leading-relaxed); color: var(--ink); }
.route-body h3 { font-size: var(--text-base); font-weight: var(--weight-semibold); margin: var(--space-4) 0 var(--space-2); }
.route-stops { margin: 0 0 var(--space-3); padding-left: var(--space-5); }
.route-stops li { margin-bottom: var(--space-2); line-height: var(--leading-normal); transition: transform var(--duration-fast) var(--ease-out); }
.route-stops li:hover { transform: translateX(2px); }
.route-stops strong { color: var(--ink); }
.route-stops span { color: var(--muted); font-size: var(--text-sm); }
.route-tips { background: var(--badge-season-bg); padding: var(--space-3) var(--space-4); border-radius: var(--radius-sm); font-size: var(--text-sm); margin-bottom: var(--space-3); line-height: var(--leading-normal); }
.route-links { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.route-links .btn { transition: all var(--duration-fast) var(--ease-out); }
.route-links .btn:active { transform: scale(.95); transition-duration: .08s; }

</style>
