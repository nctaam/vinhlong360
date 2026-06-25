<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lịch trình' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-itinerary">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🗓️</span>
        <div>
          <h1>Lịch trình</h1>
          <p>Tuyến tham quan Vĩnh Long, Bến Tre, Trà Vinh được thiết kế sẵn — chỉ cần chọn và đi. Hoặc tự tạo lịch trình cá nhân theo sở thích.</p>
        </div>
      </div>
      <div v-if="itineraries?.length" class="catalog-stats">
        <div class="stat-item">
          <span class="stat-num">{{ itineraries.length }}</span>
          <span class="stat-label">lịch trình</span>
        </div>
        <div v-for="a in areaCounts" :key="a.key" class="stat-item">
          <span class="stat-num">{{ a.count }}</span>
          <span class="stat-label">{{ a.name }}</span>
        </div>
      </div>
    </section>

    <!-- Đã lưu (client-only, từ localStorage) -->
    <ClientOnly>
      <section v-if="count > 0" class="block saved-section">
        <div class="section-head">
          <h2>❤️ Đã lưu <span class="saved-count">({{ count }})</span></h2>
          <button type="button" class="btn btn-sm btn-ghost danger" @click="clearAll">Xóa tất cả</button>
        </div>
        <div class="journey-stats">
          <div v-for="(items, type) in byType" :key="type" class="js-item">
            <span class="js-emoji">{{ getTypeMeta(type).emoji }}</span>
            <strong>{{ items.length }}</strong>
            <span>{{ getTypeMeta(type).label }}</span>
          </div>
        </div>
        <div class="scroll-row saved-row" role="region" aria-label="Mục đã lưu">
          <NuxtLink v-for="fav in recentSaved" :key="fav.id" :to="`/dia-diem/${fav.id}`" class="card">
            <div v-if="fav.image" class="cover cover-img">
              <NuxtImg v-if="isRemoteUrl(fav.image)" :src="fav.image" :alt="fav.name" loading="lazy" decoding="async" width="400" height="160" sizes="sm:100vw md:50vw lg:400px" />
              <img v-else :src="fav.image" :alt="fav.name" loading="lazy" decoding="async" width="400" height="160" />
            </div>
            <div class="card-b">
              <span class="card-type">{{ getTypeMeta(fav.type).label }}</span>
              <h3>{{ fav.name }}</h3>
              <p v-if="fav.place_name" class="place">{{ fav.place_name }}</p>
            </div>
          </NuxtLink>
        </div>
        <div class="saved-cta">
          <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-primary">📋 Tạo lịch trình từ danh sách đã lưu</NuxtLink>
        </div>
      </section>
    </ClientOnly>

    <!-- Region quick-picks -->
    <section class="block">
      <div class="section-head">
        <h2>Chọn theo khu vực</h2>
      </div>
      <div class="quick-picks">
        <button type="button"
          v-for="(meta, key) in AREA_META" :key="key"
          :class="['quick-pick', { active: areaFilter === key }]"
          @click="areaFilter = areaFilter === key ? 'all' : (key as string)"
        >
          <span class="quick-pick-icon">{{ meta.emoji }}</span>
          <span class="quick-pick-label">{{ meta.name }}</span>
          <span class="quick-pick-count">{{ countByArea(key as string) }} lịch trình</span>
        </button>
      </div>
    </section>

    <!-- Editorial -->
    <section class="page-article reveal">
      <h2>Lịch trình có sẵn — đi ngay không cần lên kế hoạch</h2>
      <p>Mỗi lịch trình được thiết kế dựa trên kinh nghiệm thực tế, sắp xếp các điểm đến theo thứ tự hợp lý về khoảng cách và thời gian. Bạn chỉ cần chọn lịch trình phù hợp với số ngày đi, sở thích (văn hoá, ẩm thực, thiên nhiên) và phương tiện (xe máy, ô tô, xuồng). Mỗi điểm dừng đều có thông tin thực tế: giờ mở cửa, giá tham khảo, mẹo di chuyển.</p>
      <p>Có thể kết hợp nhiều lịch trình hoặc tuỳ chỉnh — bỏ bớt điểm dừng, thêm điểm mới, thay đổi thứ tự. Tất cả lịch trình đều miễn phí và có thể lưu vào tài khoản để xem lại khi đi.</p>
    </section>

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Lịch trình gợi ý</span>
    </div>

    <!-- Suggested itineraries -->
    <section class="block reveal">
      <div class="controls">
        <div class="chip-row" role="group" aria-label="Lọc theo khu vực">
          <button type="button" :class="['chip', { active: areaFilter === 'all' }]" :aria-pressed="areaFilter === 'all'" @click="areaFilter = 'all'">Tất cả</button>
          <button type="button"
            v-for="(meta, key) in AREA_META" :key="key"
            :class="['chip', { active: areaFilter === key }]"
            :aria-pressed="areaFilter === key"
            @click="areaFilter = key as string"
          >{{ meta.emoji }} {{ meta.name }}</button>
        </div>
      </div>

      <p class="result-meta" aria-live="polite">{{ filtered.length }} lịch trình</p>

      <div v-if="fetchError" class="fetch-error" role="alert">
        <p>Không tải được lịch trình. Có thể mạng đang chập chờn.</p>
        <button type="button" class="btn btn-outline" @click="refreshNuxtData('itineraries')">Thử lại</button>
      </div>
      <SkeletonGrid v-else-if="!itineraries" :count="4" />
      <div v-else-if="filtered.length" class="grid itin">
        <ItineraryCard v-for="it in filtered" :key="it.id" :itinerary="it" />
      </div>
      <div v-else class="block empty-state itin-empty">
        <EmptyState icon="🗺️" title="Khám phá từ vùng khác" :message="emptyMessage">
          <template #actions>
            <button type="button" class="btn btn-outline" @click="areaFilter = 'all'">Xem tất cả khu vực</button>
            <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-primary">Tạo lịch trình</NuxtLink>
          </template>
        </EmptyState>
      </div>

      <div class="block-cta">
        <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-primary">+ Tự tạo lịch trình</NuxtLink>
      </div>
    </section>

    <!-- Cross-links -->
    <section class="block reveal catalog-cross">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm miệt vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/luu-tru" class="cross-card">
          <span class="cross-icon">🏡</span>
          <div><strong>Lưu trú</strong><p>Homestay, nhà vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/san-pham" class="cross-card">
          <span class="cross-icon">🍊</span>
          <div><strong>Đặc sản</strong><p>Mua quà miền Tây</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { Itinerary } from '~/types'
import { TYPE_META, AREA_META } from '~/composables/useConstants'

useReveal()

const { favorites, byType, count, clear } = useFavorites()
const { confirmDialog } = useConfirm()
const recentSaved = computed(() => favorites.value.slice(0, 8))
const isRemoteUrl = (url: string) => /^https?:\/\//.test(url)

function getTypeMeta(type: string) {
  return TYPE_META[type] || { emoji: '📍', label: type, cat: 'place' }
}

async function clearAll() {
  if (await confirmDialog('Xóa tất cả mục đã lưu?', { danger: true, confirmText: 'Xóa' })) clear()
}

const areaFilter = ref('all')
useFilterUrl({ vung: areaFilter }, { vung: 'all' })

const { data: itineraries, error: fetchError } = await useAsyncData('itineraries', () =>
  apiFetch<any[]>('/api/itineraries')
)

const areaCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const it of (itineraries.value || [])) {
    const area = (it as any).area || ''
    if (area) counts[area] = (counts[area] || 0) + 1
  }
  return Object.entries(AREA_META)
    .filter(([key]) => counts[key])
    .map(([key, meta]) => ({ key, name: meta.name, count: counts[key] }))
})

function countByArea(key: string) {
  return (itineraries.value || []).filter((it: Itinerary) => it.area === key).length
}

const filtered = computed(() => {
  const list = itineraries.value || []
  if (areaFilter.value === 'all') return list
  return list.filter((it: Itinerary) => it.area === areaFilter.value)
})

const emptyMessage = computed(() => {
  const meta = AREA_META[areaFilter.value as keyof typeof AREA_META]
  const regionName = meta?.name || 'Khu vực này'
  return `${regionName} chưa có lịch trình gợi ý, nhưng các vùng khác đang chờ bạn khám phá — hoặc tự tạo một lịch trình riêng theo sở thích.`
})

useSeoMeta({
  title: 'Lịch trình — vinhlong360',
  description: 'Tuyến tham quan Vĩnh Long, Bến Tre, Trà Vinh được thiết kế sẵn — chỉ cần chọn và đi. Hoặc tự tạo lịch trình cá nhân theo sở thích.',
  ogTitle: 'Lịch trình — vinhlong360',
  ogDescription: 'Tuyến tham quan miền Tây được thiết kế sẵn — chỉ cần chọn và đi.',
  ogImage: '/icons/icon-512.png',
})
useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/lich-trinh') }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'Lịch trình gợi ý',
        description: 'Tuyến tham quan Vĩnh Long, Bến Tre, Trà Vinh được thiết kế sẵn.',
        url: 'https://vinhlong360.vn/lich-trinh',
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
          { '@type': 'ListItem', position: 2, name: 'Lịch trình' },
        ],
      }),
    },
  ],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itineraryItemListJsonLd(
      'Lịch trình gợi ý',
      'Tuyến tham quan Vĩnh Long, Bến Tre, Trà Vinh được thiết kế sẵn.',
      '/lich-trinh',
      filtered.value,
    )),
  }],
}))
</script>

<style scoped>
.saved-section { margin-bottom: var(--space-4); padding-bottom: var(--space-6); border-bottom: .5px solid var(--line); }
.saved-count { font-weight: var(--weight-normal); color: var(--muted); font-size: var(--text-base); }
.saved-cta { text-align: center; margin-top: var(--space-4); }
.saved-cta .btn:active { transform: scale(.97); transition-duration: .08s; }
.saved-row { margin-top: var(--space-3); }
.saved-row .card { transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo); }
.saved-row .card:hover { transform: translateY(-5px); box-shadow: var(--shadow-lg); }
.saved-row .card:active { transform: translateY(-1px) scale(.98); transition-duration: .08s; }

.journey-stats { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-3); }
.js-item { display: flex; align-items: center; gap: var(--space-1); padding: var(--space-2) var(--space-3); background: var(--bg-alt); border-radius: var(--radius-md); font-size: var(--text-sm); transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out); }
.js-item:hover { background: var(--card); transform: translateY(-2px); box-shadow: var(--shadow-xs); }
.js-item:active { transform: scale(.97); transition-duration: .08s; }
.js-emoji { font-size: var(--text-lg); }

/* Premium hero stat-items: brand-tinted surface + accent border */
.catalog-hero .stat-item {
  background: rgba(var(--secondary-rgb), .04);
  border-left: 3px solid var(--secondary);
  border-radius: var(--radius-sm);
  transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle);
}
.catalog-hero .stat-item:hover {
  background: rgba(var(--secondary-rgb), .08);
  transform: translateY(-2px);
}
.catalog-hero .stat-item:hover .stat-num { letter-spacing: .02em; }
.dark .catalog-hero .stat-item { background: rgba(var(--secondary-rgb), .08); }
.dark .catalog-hero .stat-item:hover { background: rgba(var(--secondary-rgb), .14); }

/* Itinerary empty-state wrapper rhythm */
.itin-empty { margin-top: var(--space-2); }

.fetch-error { color: var(--error); text-align: center; padding: var(--space-5); display: flex; flex-direction: column; align-items: center; gap: var(--space-3); }
.block-cta { margin-top: var(--space-6); text-align: center; }
.block-cta .btn:active { transform: scale(.97); transition-duration: .08s; }
.danger { color: var(--error); }

/* Dark mode */
.dark .saved-section { border-bottom-color: var(--line); }
.dark .js-item { background: rgba(255,255,255,.04); }
.dark .js-item:hover { background: rgba(255,255,255,.07); }
.dark .saved-row .card { background: var(--bg-alt); border-color: var(--line); }
.dark .saved-row .card:hover { box-shadow: var(--shadow-lg); border-color: rgba(255,255,255,.1); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .saved-row .card:hover { transform: none; }
  .saved-row .card:active { transform: none; }
  .js-item:hover { transform: none; }
  .js-item:active { transform: none; }
  .saved-cta .btn:active { transform: none; }
  .block-cta .btn:active { transform: none; }
  .catalog-hero .stat-item:hover { transform: none; }
}
</style>
