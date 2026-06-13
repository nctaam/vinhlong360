<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lưu trú' }]" />
    <div class="page-head">
      <h1>🏡 Lưu trú</h1>
      <p>Homestay, nhà vườn, khách sạn và chỗ ở khắp miền Tây — chọn nơi nghỉ phù hợp cho chuyến đi của bạn.</p>
    </div>

    <div class="controls">
      <div class="search-row">
        <input v-model="q" type="search" placeholder="Tìm nơi lưu trú…" />
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
    </div>

    <p class="result-meta">{{ filtered.length }} nơi lưu trú</p>
    <SkeletonGrid v-if="!data" :count="6" />
    <div v-else-if="filtered.length" class="grid">
      <EntityCard v-for="e in filtered" :key="e.id" :entity="e" />
    </div>
    <EmptyState v-else message="Không tìm thấy nơi lưu trú phù hợp." />
  </section>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'

const q = ref('')
const areaFilter = ref('all')

const { data } = await useAsyncData('catalog-accommodation', () =>
  $fetch<any>('/api/entities?type=accommodation&limit=200')
)

const allEntities = computed(() => {
  const raw = data.value
  if (!raw) return []
  return raw.entities || []
})

const filtered = computed(() => {
  let list = allEntities.value

  if (areaFilter.value !== 'all') {
    list = list.filter((e: any) => (e.place_area || e.area) === areaFilter.value)
  }

  if (q.value.trim()) {
    const query = q.value.toLowerCase()
    list = list.filter((e: any) =>
      (e.name || '').toLowerCase().includes(query) ||
      (e.summary || '').toLowerCase().includes(query) ||
      (e.place_name || '').toLowerCase().includes(query)
    )
  }

  return list
})

useSeoMeta({
  title: 'Lưu trú Vĩnh Long — Homestay, nhà vườn, khách sạn — vinhlong360',
  description: 'Homestay, nhà vườn, khách sạn và nơi nghỉ ở Vĩnh Long, Bến Tre, Trà Vinh — chọn chỗ ở phù hợp cho chuyến đi.',
  ogTitle: 'Lưu trú miền Tây — vinhlong360',
  ogDescription: 'Homestay, nhà vườn, khách sạn và nơi nghỉ ở Vĩnh Long, Bến Tre, Trà Vinh.',
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/luu-tru') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'Lưu trú Vĩnh Long',
      description: 'Homestay, nhà vườn, khách sạn và nơi nghỉ ở Vĩnh Long, Bến Tre, Trà Vinh.',
      url: 'https://vinhlong360.vn/luu-tru',
    }),
  }],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itemListJsonLd(
      'Lưu trú Vĩnh Long, Bến Tre, Trà Vinh',
      'Homestay, nhà vườn, khách sạn và nơi nghỉ ở miền Tây.',
      '/luu-tru',
      filtered.value,
    )),
  }],
}))
</script>
