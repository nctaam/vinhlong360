<template>
  <section class="page">
    <div class="ocop-hero">
      <div class="ocop-hero-inner">
        <span class="ocop-badge-lg">⭐ OCOP</span>
        <h1>Sản phẩm OCOP</h1>
        <p>Mỗi xã một sản phẩm — sản phẩm đạt chuẩn OCOP từ Vĩnh Long, Bến Tre và Trà Vinh.</p>
      </div>
    </div>

    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Sản phẩm', to: '/san-pham' }, { label: 'OCOP' }]" />

    <div class="controls">
      <div class="search-row">
        <input v-model="q" type="search" placeholder="Tìm sản phẩm OCOP…" />
      </div>
      <p class="control-label">Hạng sao</p>
      <div class="chip-row">
        <button :class="['chip', { active: starFilter === 0 }]" @click="starFilter = 0">Tất cả</button>
        <button :class="['chip', { active: starFilter === 5 }]" @click="starFilter = 5">⭐⭐⭐⭐⭐ 5 sao</button>
        <button :class="['chip', { active: starFilter === 4 }]" @click="starFilter = 4">⭐⭐⭐⭐ 4 sao</button>
        <button :class="['chip', { active: starFilter === 3 }]" @click="starFilter = 3">⭐⭐⭐ 3 sao</button>
      </div>
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
      <p class="control-label">Theo tháng</p>
      <div class="chip-row">
        <button :class="['chip', 'season', { active: seasonFilter === 'all' }]" @click="seasonFilter = 'all'">Tất cả</button>
        <button v-for="m in 12" :key="m" :class="['chip', 'season', { active: seasonFilter === String(m) }]" @click="seasonFilter = String(m)">
          T{{ m }}
        </button>
      </div>
    </div>

    <p class="result-meta">{{ filtered.length }} sản phẩm OCOP</p>
    <SkeletonGrid v-if="!data" :count="6" />
    <div v-else-if="filtered.length" class="grid">
      <EntityCard v-for="e in filtered" :key="e.id" :entity="e" :season-filter="seasonFilter" />
    </div>
    <EmptyState v-else message="Không tìm thấy sản phẩm OCOP phù hợp." />
  </section>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'
import { inSeason, relevanceScore } from '~/composables/useSeason'

const q = ref('')
const starFilter = ref(0)
const areaFilter = ref('all')
const seasonFilter = ref('all')

const starFilterStr = computed({
  get: () => String(starFilter.value),
  set: (v: string) => { starFilter.value = parseInt(v) || 0 },
})
useFilterUrl({ sao: starFilterStr, vung: areaFilter, mua: seasonFilter }, { sao: '0', vung: 'all', mua: 'all' })

const { data } = await useAsyncData('catalog-ocop', () =>
  $fetch<any>('/api/entities?type=product&limit=200')
)

const allOcop = computed(() => {
  const raw = data.value
  if (!raw) return []
  return (raw.entities || []).filter((e: any) => e.attributes?.ocop)
})

const filtered = computed(() => {
  let list = allOcop.value

  if (starFilter.value > 0) {
    list = list.filter((e: any) => {
      const ocop = e.attributes?.ocop || ''
      const stars = parseInt(ocop) || 0
      return stars >= starFilter.value
    })
  }

  if (areaFilter.value !== 'all') {
    list = list.filter((e: any) => (e.place_area || e.area) === areaFilter.value)
  }

  if (seasonFilter.value !== 'all') {
    list = list.filter((e: any) => inSeason(e, seasonFilter.value))
  }

  if (q.value.trim()) {
    const query = q.value.toLowerCase()
    list = list.filter((e: any) =>
      (e.name || '').toLowerCase().includes(query) ||
      (e.summary || '').toLowerCase().includes(query)
    )
  }

  if (seasonFilter.value !== 'all') {
    list.sort((a: any, b: any) => relevanceScore(b, seasonFilter.value) - relevanceScore(a, seasonFilter.value))
  }

  return list
})

useSeoMeta({
  title: 'Sản phẩm OCOP Vĩnh Long — Mỗi xã một sản phẩm — vinhlong360',
  description: 'Sản phẩm đạt chuẩn OCOP (Mỗi xã một sản phẩm) từ Vĩnh Long, Bến Tre, Trà Vinh — đặc sản theo mùa, xếp hạng sao. Lọc theo số sao, khu vực và mùa vụ.',
  ogTitle: 'Sản phẩm OCOP miền Tây — vinhlong360',
  ogDescription: 'Sản phẩm đạt chuẩn OCOP 3-5 sao từ Vĩnh Long, Bến Tre, Trà Vinh.',
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/ocop') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'Sản phẩm OCOP Vĩnh Long',
      description: 'Sản phẩm đạt chuẩn OCOP từ Vĩnh Long, Bến Tre, Trà Vinh.',
      url: 'https://vinhlong360.vn/ocop',
    }),
  }],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itemListJsonLd(
      'Sản phẩm OCOP Vĩnh Long, Bến Tre, Trà Vinh',
      'Sản phẩm đạt chuẩn OCOP từ Vĩnh Long, Bến Tre và Trà Vinh.',
      '/ocop',
      filtered.value,
    )),
  }],
}))
</script>
