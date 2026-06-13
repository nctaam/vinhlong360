<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Du lịch' }]" />
    <div class="page-head">
      <h1>Du lịch</h1>
      <p>Trải nghiệm bản địa, điểm tham quan, lưu trú, làng nghề và ẩm thực khắp Vĩnh Long.</p>
    </div>
    <div class="controls">
      <div class="search-row">
        <input v-model="q" type="search" placeholder="Tìm trong du lịch…" />
      </div>
      <p class="control-label">Loại</p>
      <div class="chip-row">
        <button :class="['chip', { active: typeFilter === 'all' }]" @click="typeFilter = 'all'">Tất cả</button>
        <button v-for="t in typeChips" :key="t.value" :class="['chip', { active: typeFilter === t.value }]" @click="typeFilter = t.value">
          {{ t.label }}
        </button>
      </div>
      <p class="control-label">Theo tháng</p>
      <div class="chip-row">
        <button :class="['chip', 'season', { active: seasonFilter === 'all' }]" @click="seasonFilter = 'all'">Tất cả</button>
        <button v-for="m in 12" :key="m" :class="['chip', 'season', { active: seasonFilter === String(m) }]" @click="seasonFilter = String(m)">
          T{{ m }}
        </button>
        <button :class="['chip', 'season', { active: seasonFilter === 'flood' }]" @click="seasonFilter = 'flood'">🌊 Mùa nước nổi</button>
      </div>
    </div>
    <p class="result-meta">{{ filtered.length }} kết quả</p>
    <SkeletonGrid v-if="!data" :count="6" />
    <div v-else-if="filtered.length" class="grid">
      <EntityCard v-for="e in filtered" :key="e.id" :entity="e" :season-filter="seasonFilter" />
    </div>
    <EmptyState v-else message="Không tìm thấy kết quả phù hợp. Thử thay đổi bộ lọc." />
  </section>
</template>

<script setup lang="ts">
import { TYPE_META, TOURISM_TYPES } from '~/composables/useConstants'
import { inSeason, relevanceScore } from '~/composables/useSeason'

const TYPES = TOURISM_TYPES as readonly string[]

const typeChips = TYPES.map(t => ({
  value: t,
  label: `${TYPE_META[t].emoji} ${TYPE_META[t].label}`,
}))

const q = ref('')
const typeFilter = ref('all')
const seasonFilter = ref('all')

useFilterUrl({ type: typeFilter, mua: seasonFilter }, { type: 'all', mua: 'all' })

const { data } = await useAsyncData('catalog-tourism', () =>
  $fetch<any>('/api/entities?limit=200')
)

const allEntities = computed(() => {
  const raw = data.value
  if (!raw) return []
  return (raw.entities || []).filter((e: any) => TYPES.includes(e.type))
})

const filtered = computed(() => {
  let list = allEntities.value

  if (typeFilter.value !== 'all') {
    list = list.filter((e: any) => e.type === typeFilter.value)
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

  list.sort((a: any, b: any) => relevanceScore(b, seasonFilter.value) - relevanceScore(a, seasonFilter.value))
  return list
})

useSeoMeta({
  title: 'Du lịch Vĩnh Long, Bến Tre, Trà Vinh — vinhlong360',
  description: 'Trải nghiệm bản địa, điểm tham quan, lưu trú, làng nghề và ẩm thực khắp Vĩnh Long, Bến Tre, Trà Vinh. Lọc theo loại hình, mùa vụ và khu vực.',
  ogTitle: 'Du lịch miền Tây — vinhlong360',
  ogDescription: 'Trải nghiệm miệt vườn, điểm tham quan, làng nghề và ẩm thực khắp Vĩnh Long.',
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/du-lich') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'Du lịch Vĩnh Long',
      description: 'Trải nghiệm bản địa, điểm tham quan, lưu trú, làng nghề và ẩm thực khắp Vĩnh Long.',
      url: 'https://vinhlong360.vn/du-lich',
    }),
  }],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itemListJsonLd(
      'Du lịch Vĩnh Long, Bến Tre, Trà Vinh',
      'Trải nghiệm bản địa, điểm tham quan, lưu trú, làng nghề và ẩm thực miền Tây.',
      '/du-lich',
      filtered.value,
    )),
  }],
}))
</script>
