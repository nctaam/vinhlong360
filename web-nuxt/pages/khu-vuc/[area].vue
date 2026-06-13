<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: areaMeta?.name || 'Khu vực' }]" />
    <div v-if="areaMeta" class="region-head" style="margin-top: 12px">
      <span class="rc-emoji">{{ areaMeta.emoji }}</span>
      <div>
        <h1>Khu vực {{ areaMeta.name }}</h1>
        <p>{{ areaMeta.blurb }}</p>
      </div>
    </div>
    <p class="result-meta">{{ entities.length }} mục</p>
    <div v-if="entities.length" class="grid">
      <EntityCard v-for="e in entities" :key="e.id" :entity="e" />
    </div>
    <EmptyState v-else message="Chưa có dữ liệu cho khu vực này." />

    <div v-if="wards.length" class="area-links">
      <h2>Xã / phường ({{ wards.length }})</h2>
      <p class="muted" style="margin:4px 0 8px; font-size:.9rem">Mỗi xã/phường có trang riêng: du lịch · lưu trú · đặc sản · danh bạ hành chính.</p>
      <div class="chip-row" style="margin-top: 4px">
        <NuxtLink v-for="w in wards" :key="w.id" :to="`/xa-phuong/${w.id}`" class="chip">{{ w.name }}</NuxtLink>
      </div>
    </div>

    <div v-if="areaMeta" class="area-links">
      <h2>Khám phá thêm {{ areaMeta.name }}</h2>
      <div class="chip-row" style="margin-top: 8px">
        <NuxtLink :to="`/du-lich?type=experience&mua=all`" class="chip">🌾 Trải nghiệm</NuxtLink>
        <NuxtLink :to="`/san-pham`" class="chip">🍊 Sản phẩm</NuxtLink>
        <NuxtLink :to="`/luu-tru`" class="chip">🏡 Lưu trú</NuxtLink>
        <NuxtLink to="/tuyen-duong" class="chip">🛤️ Tuyến đường</NuxtLink>
      <NuxtLink to="/ban-do" no-prefetch class="chip">🗺️ Bản đồ</NuxtLink>
      <NuxtLink :to="`/danh-ba?area=${areaKey}`" class="chip">🏛️ Danh bạ hành chính</NuxtLink>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { AREA_META, CARD_TYPES } from '~/composables/useConstants'

const route = useRoute()
const areaKey = route.params.area as string
const areaMeta = AREA_META[areaKey]

const { data } = await useAsyncData(`area-${areaKey}`, () =>
  $fetch<any>(`/api/entities?area=${areaKey}&limit=200`)
)

// Danh sách xã/phường của khu vực → link sang trang hub từng xã/phường.
const ADMIN_LEVELS = ['phuong', 'xa', 'tinh']
const { data: placesData } = await useAsyncData(`area-wards-${areaKey}`, () =>
  $fetch<any>('/api/places').catch(() => [])
)
const wards = computed(() =>
  (placesData.value || [])
    .filter((p: any) => p.area === areaKey && ADMIN_LEVELS.includes(p.level))
    .sort((a: any, b: any) => a.name.localeCompare(b.name, 'vi'))
)

const entities = computed(() => {
  const raw = data.value
  if (!raw) return []
  const types = CARD_TYPES as readonly string[]
  return (raw.entities || []).filter((e: any) => types.includes(e.type))
})

if (areaMeta) {
  useSeoMeta({
    title: `Khu vực ${areaMeta.name} — vinhlong360`,
    description: areaMeta.blurb,
    ogTitle: `${areaMeta.emoji} ${areaMeta.name} — vinhlong360`,
    ogDescription: areaMeta.blurb,
    ogImage: '/icons/icon-512.png',
  })

  useHead(() => ({
    link: [{ rel: 'canonical', href: canonicalUrl(`/khu-vuc/${areaKey}`) }],
    script: [{
      type: 'application/ld+json',
      innerHTML: JSON.stringify(itemListJsonLd(
        `Khu vực ${areaMeta.name}`,
        areaMeta.blurb,
        `/khu-vuc/${areaKey}`,
        entities.value,
      )),
    }],
  }))
}
</script>
