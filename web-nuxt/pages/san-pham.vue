<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Sản phẩm' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-product">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🍊</span>
        <div>
          <h1>Đặc sản địa phương</h1>
          <p>Trái cây theo mùa, đặc sản làm quà, sản phẩm OCOP — biết mùa nào ngon, mua ở đâu, ai sản xuất.</p>
        </div>
      </div>
      <div v-if="allEntities.length" class="catalog-stats">
        <div class="stat-item">
          <span class="stat-num">{{ allEntities.length }}</span>
          <span class="stat-label">sản phẩm</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ ocopCount }}</span>
          <span class="stat-label">OCOP</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ inSeasonCount }}</span>
          <span class="stat-label">đang mùa</span>
        </div>
      </div>
    </section>

    <!-- Đang vào mùa -->
    <section v-if="seasonalHighlights.length" class="block reveal">
      <div class="seasonal-banner">
        <span class="seasonal-banner-icon">🔥</span>
        <div>
          <strong>Tháng {{ currentMonth }} — đang vào mùa</strong>
          <p>Những sản phẩm đang chính vụ, ngon nhất thời điểm này.</p>
        </div>
      </div>
      <div class="scroll-row" role="region" aria-label="Đặc sản đang mùa">
        <EntityCard v-for="e in seasonalHighlights" :key="e.id" :entity="e" :season-filter="String(currentMonth)" />
      </div>
    </section>

    <!-- OCOP Spotlight -->
    <section v-if="ocopHighlights.length" class="block reveal">
      <div class="section-head">
        <h2>⭐ Sản phẩm OCOP</h2>
        <button type="button" class="see-all" @click="ocopOnly = true; scrollToGrid()">Xem tất cả →</button>
      </div>
      <p class="section-desc">Sản phẩm đạt chuẩn OCOP — Mỗi xã một sản phẩm, chất lượng được chứng nhận.</p>
      <div class="scroll-row" role="region" aria-label="Sản phẩm OCOP nổi bật">
        <EntityCard v-for="e in ocopHighlights" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Duyệt tất cả</span>
    </div>

    <!-- Full filterable grid -->
    <section ref="gridSection" class="block">
      <div class="controls">
        <div class="search-row">
          <input v-model="q" type="search" placeholder="Tìm trong sản phẩm…" aria-label="Tìm sản phẩm" />
        </div>
        <p class="control-label">Theo tháng</p>
        <div class="chip-row" role="group" aria-label="Lọc theo tháng">
          <button type="button" :class="['chip', 'season', { active: seasonFilter === 'all' }]" :aria-pressed="seasonFilter === 'all'" @click="seasonFilter = 'all'">Tất cả</button>
          <button type="button" v-for="m in 12" :key="m" :class="['chip', 'season', { active: seasonFilter === String(m) }]" :aria-pressed="seasonFilter === String(m)" @click="seasonFilter = String(m)">
            T{{ m }}
          </button>
          <button type="button" :class="['chip', 'season', { active: seasonFilter === 'flood' }]" :aria-pressed="seasonFilter === 'flood'" @click="seasonFilter = 'flood'">🌊 Mùa nước nổi</button>
        </div>
        <div class="chip-row chip-row-extra">
          <button type="button" :class="['chip', { active: ocopOnly }]" :aria-pressed="ocopOnly" @click="ocopOnly = !ocopOnly">⭐ Chỉ sản phẩm OCOP</button>
        </div>
      </div>
      <p class="result-meta" aria-live="polite">{{ filtered.length }} kết quả</p>
      <EmptyState v-if="fetchError" icon="⚠️" title="Không thể tải dữ liệu" message="Vui lòng thử lại sau." />
      <SkeletonGrid v-else-if="!data" :count="6" />
      <div v-else-if="filtered.length" class="grid">
        <EntityCard v-for="e in filtered" :key="e.id" :entity="e" :season-filter="seasonFilter" />
      </div>
      <EmptyState v-else icon="🍊" title="Không tìm thấy sản phẩm" message="Thử chọn tháng khác hoặc bỏ bộ lọc OCOP.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="seasonFilter = 'all'; ocopOnly = false; q = ''">Xóa bộ lọc</button>
          <NuxtLink to="/ocop" class="btn btn-outline">Xem sản phẩm OCOP</NuxtLink>
        </template>
      </EmptyState>
    </section>

    <!-- Cross-links -->
    <section class="block catalog-cross">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/ocop" class="cross-card">
          <span class="cross-icon">⭐</span>
          <div><strong>OCOP</strong><p>Sản phẩm đạt chuẩn</p></div>
        </NuxtLink>
        <NuxtLink to="/theo-mua" class="cross-card">
          <span class="cross-icon">📅</span>
          <div><strong>Theo mùa</strong><p>Lịch mùa vụ</p></div>
        </NuxtLink>
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm miệt vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/kham-pha/am-thuc" class="cross-card">
          <span class="cross-icon">🍲</span>
          <div><strong>Ẩm thực</strong><p>Món ngon miền Tây</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { inSeason, relevanceScore } from '~/composables/useSeason'

useReveal()
const currentMonth = new Date().getMonth() + 1

const q = ref('')
const seasonFilter = ref(String(currentMonth))
const ocopOnly = ref(false)
const gridSection = ref<HTMLElement | null>(null)

useFilterUrl({ mua: seasonFilter }, { mua: String(currentMonth) })

const { data, error: fetchError } = await useAsyncData('catalog-products', () =>
  $fetch<any>('/api/entities?type=product&limit=200')
)

const allEntities = computed(() => {
  const raw = data.value
  if (!raw) return []
  return raw.entities || []
})

const ocopCount = computed(() => allEntities.value.filter((e: any) => e.attributes?.ocop).length)
const inSeasonCount = computed(() => allEntities.value.filter((e: any) => inSeason(e, String(currentMonth))).length)

const seasonalHighlights = computed(() => {
  return allEntities.value
    .filter((e: any) => inSeason(e, String(currentMonth)))
    .sort((a: any, b: any) => relevanceScore(b, String(currentMonth)) - relevanceScore(a, String(currentMonth)))
    .slice(0, 8)
})

const ocopHighlights = computed(() => {
  return allEntities.value
    .filter((e: any) => e.attributes?.ocop)
    .slice(0, 8)
})

function scrollToGrid() {
  nextTick(() => gridSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

const filtered = computed(() => {
  let list = allEntities.value

  if (seasonFilter.value !== 'all') {
    list = list.filter((e: any) => inSeason(e, seasonFilter.value))
  }

  if (ocopOnly.value) {
    list = list.filter((e: any) => e.attributes?.ocop)
  }

  if (q.value.trim()) {
    const query = q.value.toLowerCase()
    list = list.filter((e: any) =>
      (e.name || '').toLowerCase().includes(query) ||
      (e.summary || '').toLowerCase().includes(query)
    )
  }

  list.sort((a: any, b: any) => relevanceScore(b, seasonFilter.value) - relevanceScore(a, seasonFilter.value))
  return list
})

useSeoMeta({
  title: 'Đặc sản & sản phẩm OCOP Vĩnh Long — vinhlong360',
  description: 'Đặc sản & sản phẩm OCOP Vĩnh Long theo mùa — biết mùa nào ngon, mua ở đâu, ai sản xuất. Lọc theo mùa vụ, sao OCOP và khu vực miền Tây.',
  ogTitle: 'Đặc sản Vĩnh Long theo mùa — vinhlong360',
  ogDescription: 'Sản phẩm OCOP, trái cây, đặc sản miệt vườn theo mùa vụ.',
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/san-pham') }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'Sản phẩm địa phương Vĩnh Long',
        description: 'Đặc sản & sản phẩm OCOP Vĩnh Long theo mùa.',
        url: 'https://vinhlong360.vn/san-pham',
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
          { '@type': 'ListItem', position: 2, name: 'Sản phẩm' },
        ],
      }),
    },
  ],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itemListJsonLd(
      'Sản phẩm địa phương Vĩnh Long',
      'Đặc sản và sản phẩm OCOP Vĩnh Long theo mùa.',
      '/san-pham',
      filtered.value,
    )),
  }],
}))
</script>
