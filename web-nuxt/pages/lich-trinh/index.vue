<template>
  <section class="page">
    <div class="page-head">
      <h1>Lịch trình gợi ý</h1>
      <p>Tuyến tham quan được thiết kế sẵn — chỉ cần chọn và đi.</p>
    </div>

    <div class="controls">
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

    <p v-if="fetchError" style="color: #D94F3D; text-align: center; padding: 20px">Không thể tải lịch trình. Vui lòng thử lại.</p>
    <SkeletonGrid v-else-if="!itineraries" :count="4" />
    <div v-else-if="filtered.length" class="grid itin">
      <ItineraryCard v-for="it in filtered" :key="it.id" :itinerary="it" />
    </div>
    <EmptyState v-else message="Không có lịch trình nào cho khu vực này." />

    <div style="margin-top: 28px; text-align: center">
        <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-primary">+ Tự tạo lịch trình</NuxtLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'

const areaFilter = ref('all')

const { data: itineraries, error: fetchError } = await useAsyncData('itineraries', () =>
  $fetch<any[]>('/api/itineraries')
)

const filtered = computed(() => {
  const list = itineraries.value || []
  if (areaFilter.value === 'all') return list
  return list.filter((it: any) => it.area === areaFilter.value)
})

useSeoMeta({
  title: 'Lịch trình gợi ý — vinhlong360',
  description: 'Tuyến tham quan Vĩnh Long, Bến Tre, Trà Vinh được thiết kế sẵn — chỉ cần chọn và đi. Hoặc tự tạo lịch trình cá nhân theo sở thích.',
  ogTitle: 'Lịch trình gợi ý — vinhlong360',
  ogDescription: 'Tuyến tham quan miền Tây được thiết kế sẵn — chỉ cần chọn và đi.',
  ogImage: '/icons/icon-512.png',
})
useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/lich-trinh') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'Lịch trình gợi ý',
      description: 'Tuyến tham quan Vĩnh Long, Bến Tre, Trà Vinh được thiết kế sẵn.',
      url: 'https://vinhlong360.vn/lich-trinh',
    }),
  }],
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
