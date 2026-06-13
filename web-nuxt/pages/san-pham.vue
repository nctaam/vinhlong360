<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Sản phẩm' }]" />
    <div class="page-head">
      <h1>Sản phẩm địa phương</h1>
      <p>Đặc sản &amp; sản phẩm OCOP theo mùa — biết mùa nào ngon, mua ở đâu, ai sản xuất.</p>
    </div>
    <div class="controls">
      <div class="search-row">
        <input v-model="q" type="search" placeholder="Tìm trong sản phẩm…" />
      </div>
      <p class="control-label">Theo tháng</p>
      <div class="chip-row">
        <button :class="['chip', 'season', { active: seasonFilter === 'all' }]" @click="seasonFilter = 'all'">Tất cả</button>
        <button v-for="m in 12" :key="m" :class="['chip', 'season', { active: seasonFilter === String(m) }]" @click="seasonFilter = String(m)">
          T{{ m }}
        </button>
        <button :class="['chip', 'season', { active: seasonFilter === 'flood' }]" @click="seasonFilter = 'flood'">🌊 Mùa nước nổi</button>
      </div>
      <div class="chip-row" style="margin-top: 8px">
        <button :class="['chip', { active: ocopOnly }]" @click="ocopOnly = !ocopOnly">⭐ Chỉ sản phẩm OCOP</button>
      </div>
    </div>
    <p class="result-meta">{{ filtered.length }} kết quả</p>
    <SkeletonGrid v-if="!data" :count="6" />
    <div v-else-if="filtered.length" class="grid">
      <EntityCard v-for="e in filtered" :key="e.id" :entity="e" :season-filter="seasonFilter" />
    </div>
    <EmptyState v-else message="Không tìm thấy sản phẩm phù hợp. Thử thay đổi bộ lọc." />
  </section>
</template>

<script setup lang="ts">
import { inSeason, relevanceScore } from '~/composables/useSeason'

const currentMonth = new Date().getMonth() + 1

const q = ref('')
const seasonFilter = ref(String(currentMonth))
const ocopOnly = ref(false)

useFilterUrl({ mua: seasonFilter }, { mua: String(currentMonth) })

const { data } = await useAsyncData('catalog-products', () =>
  $fetch<any>('/api/entities?type=product&limit=200')
)

const allEntities = computed(() => {
  const raw = data.value
  if (!raw) return []
  return raw.entities || []
})

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
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'Sản phẩm địa phương Vĩnh Long',
      description: 'Đặc sản & sản phẩm OCOP Vĩnh Long theo mùa.',
      url: 'https://vinhlong360.vn/san-pham',
    }),
  }],
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
