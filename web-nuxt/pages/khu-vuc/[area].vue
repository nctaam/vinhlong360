<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: areaMeta?.name || 'Khu vực' }]" />

    <!-- Hero -->
    <section v-if="areaMeta" class="catalog-hero" :class="'cat-area-' + areaKey">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">{{ areaMeta.emoji }}</span>
        <div>
          <h1>{{ areaMeta.name }}</h1>
          <p>{{ areaMeta.blurb }}</p>
        </div>
      </div>
      <div v-if="entities.length" class="catalog-stats">
        <div class="stat-item">
          <span class="stat-num">{{ entities.length }}</span>
          <span class="stat-label">địa điểm</span>
        </div>
        <div v-for="s in typeStats" :key="s.type" class="stat-item">
          <span class="stat-num">{{ s.count }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>
    </section>

    <!-- Error state -->
    <EmptyState v-if="fetchError && !entities.length" icon="⚠️" title="Không thể tải dữ liệu" message="Vui lòng thử lại sau.">
      <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData(`area-${areaKey}`)">Thử lại</button>
    </EmptyState>

    <!-- Featured -->
    <section v-if="featured.length" class="block reveal">
      <div class="section-head">
        <h2>Nổi bật {{ areaMeta?.name }}</h2>
      </div>
      <div class="scroll-row" role="region" :aria-label="'Nổi bật ' + areaMeta?.name">
        <EntityCard v-for="e in featured" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Type sections -->
    <section v-for="cat in typeSections" :key="cat.type" class="block reveal">
      <div class="section-head">
        <h2>{{ cat.emoji }} {{ cat.label }}</h2>
        <span class="see-all-count">{{ cat.items.length }} mục</span>
      </div>
      <div class="scroll-row" role="region" :aria-label="cat.label">
        <EntityCard v-for="e in cat.items.slice(0, 8)" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Wards -->
    <section v-if="wards.length" class="block reveal">
      <div class="section-head">
        <h2>Xã / phường ({{ wards.length }})</h2>
      </div>
      <p class="section-desc">Mỗi xã/phường có trang riêng: du lịch · lưu trú · đặc sản · danh bạ hành chính.</p>
      <div class="chip-row wrap-mobile">
        <NuxtLink v-for="w in wards" :key="w.id" :to="`/xa-phuong/${w.id}`" class="chip">{{ w.name }}</NuxtLink>
      </div>
    </section>

    <!-- Divider -->
    <div v-if="entities.length" class="catalog-divider">
      <span class="catalog-divider-text">Tất cả {{ entities.length }} mục</span>
    </div>

    <!-- Full grid -->
    <section v-if="entities.length" class="block">
      <div class="grid">
        <EntityCard v-for="e in entities" :key="e.id" :entity="e" />
      </div>
    </section>
    <EmptyState v-else icon="📍" title="Chưa có dữ liệu" message="Chưa có dữ liệu cho khu vực này. Dữ liệu đang được cập nhật.">
      <template #actions>
        <NuxtLink to="/du-lich" class="btn btn-outline">Khám phá du lịch</NuxtLink>
        <NuxtLink to="/" class="btn btn-outline">Về trang chủ</NuxtLink>
      </template>
    </EmptyState>

    <!-- Cross-links -->
    <section v-if="areaMeta" class="block catalog-cross">
      <h2>Khám phá thêm {{ areaMeta.name }}</h2>
      <div class="cross-links">
        <NuxtLink :to="`/du-lich?type=experience&mua=all`" class="cross-card">
          <span class="cross-icon">🌾</span>
          <div><strong>Trải nghiệm</strong><p>Miệt vườn sông nước</p></div>
        </NuxtLink>
        <NuxtLink to="/san-pham" class="cross-card">
          <span class="cross-icon">🍊</span>
          <div><strong>Sản phẩm</strong><p>Đặc sản địa phương</p></div>
        </NuxtLink>
        <NuxtLink to="/luu-tru" class="cross-card">
          <span class="cross-icon">🏡</span>
          <div><strong>Lưu trú</strong><p>Homestay, nhà vườn</p></div>
        </NuxtLink>
        <NuxtLink :to="`/danh-ba?area=${areaKey}`" class="cross-card">
          <span class="cross-icon">🏛️</span>
          <div><strong>Danh bạ</strong><p>Hành chính xã/phường</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { AREA_META, CARD_TYPES, TYPE_META } from '~/composables/useConstants'

useReveal()
const route = useRoute()
const areaKey = route.params.area as string
const areaMeta = AREA_META[areaKey]

const { data, error: fetchError } = await useAsyncData(`area-${areaKey}`, () =>
  $fetch<any>(`/api/entities?area=${areaKey}&limit=200`)
)

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

const typeStats = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of entities.value) counts[e.type] = (counts[e.type] || 0) + 1
  return (CARD_TYPES as readonly string[])
    .filter(t => counts[t])
    .map(t => ({ type: t, label: TYPE_META[t]?.label || t, count: counts[t] }))
})

const featured = computed(() =>
  entities.value.filter((e: any) => e.images?.length).slice(0, 6)
)

const typeSections = computed(() =>
  (CARD_TYPES as readonly string[])
    .map(t => ({
      type: t,
      emoji: TYPE_META[t]?.emoji || '📍',
      label: TYPE_META[t]?.label || t,
      items: entities.value.filter((e: any) => e.type === t),
    }))
    .filter(c => c.items.length > 0)
)

if (areaMeta) {
  useSeoMeta({
    title: `Khu vực ${areaMeta.name} — vinhlong360`,
    description: areaMeta.blurb,
    ogTitle: `${areaMeta.emoji} ${areaMeta.name} — vinhlong360`,
    ogDescription: areaMeta.blurb,
    ogImage: '/icons/icon-512.png',
  })

  useHead({
    link: [{ rel: 'canonical', href: canonicalUrl(`/khu-vuc/${areaKey}`) }],
    script: [{
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
          { '@type': 'ListItem', position: 2, name: areaMeta.name },
        ],
      }),
    }],
  })

  useHead(() => ({
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

<style scoped>
.see-all-count { font-size: var(--text-sm); color: var(--muted); }
</style>
