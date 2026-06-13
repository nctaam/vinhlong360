<template>
  <section class="page ward">
    <Breadcrumb :items="crumbs" />

    <div v-if="!data?.place" class="muted" style="padding:40px 0">Không tìm thấy xã/phường này.</div>

    <template v-else>
      <header class="ward-head">
        <div>
          <h1>{{ data.place.name }}</h1>
          <p class="ward-area">
            <span class="ward-emoji">{{ areaMeta.emoji }}</span>
            Khu vực <NuxtLink :to="`/khu-vuc/${data.place.area}`">{{ areaMeta.name }}</NuxtLink>
            <span v-if="totalContent"> · {{ totalContent }} mục</span>
          </p>
          <p v-if="data.place.summary" class="ward-summary">{{ data.place.summary }}</p>
        </div>
      </header>

      <!-- 1) Danh bạ hành chính -->
      <section class="ward-sec">
        <h2>🏛️ Danh bạ hành chính</h2>
        <ul v-if="data.facilities?.length" class="fac-list">
          <li v-for="f in data.facilities" :key="f.id" class="fac">
            <div class="fac-head">
              <span class="fac-kind">{{ kindMeta(f).emoji }} {{ kindMeta(f).label }}</span>
              <strong>{{ f.name }}</strong>
            </div>
            <div v-if="attr(f,'address')" class="fac-row">📍 {{ attr(f,'address') }}</div>
            <div v-if="attr(f,'phone')" class="fac-row">📞 <a :href="`tel:${attr(f,'phone')}`">{{ attr(f,'phone') }}</a></div>
          </li>
        </ul>
        <p v-else class="sec-empty">
          Chưa có dữ liệu danh bạ cho xã/phường này — đang bổ sung từ nguồn chính thống.
          <NuxtLink :to="`/danh-ba?area=${data.place.area}`">Mở danh bạ</NuxtLink>
        </p>
      </section>

      <!-- 2) Địa điểm du lịch -->
      <section class="ward-sec">
        <h2>🗺️ Địa điểm &amp; trải nghiệm du lịch <span class="cnt">{{ (data.tourism || []).length }}</span></h2>
        <div v-if="(data.tourism || []).length" class="grid">
          <EntityCard v-for="e in (data.tourism || [])" :key="e.id" :entity="e" />
        </div>
        <p v-else class="sec-empty">Chưa có địa điểm du lịch.</p>
      </section>

      <!-- 3) Lưu trú -->
      <section class="ward-sec">
        <h2>🏡 Lưu trú <span class="cnt">{{ (data.lodging || []).length }}</span></h2>
        <div v-if="(data.lodging || []).length" class="grid">
          <EntityCard v-for="e in (data.lodging || [])" :key="e.id" :entity="e" />
        </div>
        <p v-else class="sec-empty">Chưa có cơ sở lưu trú.</p>
      </section>

      <!-- 4) Sản phẩm địa phương -->
      <section class="ward-sec">
        <h2>🍊 Sản phẩm &amp; đặc sản địa phương <span class="cnt">{{ (data.products || []).length }}</span></h2>
        <div v-if="(data.products || []).length" class="grid">
          <EntityCard v-for="e in (data.products || [])" :key="e.id" :entity="e" />
        </div>
        <p v-else class="sec-empty">Chưa có sản phẩm địa phương.</p>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { AREA_META, OFFICE_KIND } from '~/composables/useConstants'

const route = useRoute()
const id = computed(() => route.params.id as string)

const { data } = await useAsyncData(`ward-${id.value}`, () =>
  $fetch<any>(`/api/places/${id.value}/overview`).catch(() => null))

const areaMeta = computed(() => AREA_META[data.value?.place?.area] || { name: '', emoji: '📍' })
const totalContent = computed(() => {
  const c = data.value?.counts || {}
  return (c.tourism || 0) + (c.lodging || 0) + (c.products || 0)
})
const crumbs = computed(() => [
  { label: 'Trang chủ', to: '/' },
  ...(data.value?.place?.area ? [{ label: areaMeta.value.name, to: `/khu-vuc/${data.value.place.area}` }] : []),
  { label: data.value?.place?.name || 'Xã/Phường' },
])

function attr(f: any, k: string) { return (f.attributes || {})[k] }
function kindMeta(f: any) { return OFFICE_KIND[attr(f, 'office_kind')] || OFFICE_KIND.khac }

const placeName = computed(() => data.value?.place?.name || 'Xã/Phường')
useSeoMeta({
  title: () => `${placeName.value} — du lịch, lưu trú, đặc sản & danh bạ | vinhlong360`,
  description: () => `Tổng hợp địa điểm du lịch, cơ sở lưu trú, sản phẩm đặc sản và danh bạ hành chính của ${placeName.value}, tỉnh Vĩnh Long.`,
})
useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl(`/xa-phuong/${id.value}`) }],
  script: data.value?.place ? [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org', '@type': 'Place',
      name: data.value.place.name,
      ...(data.value.place.summary ? { description: data.value.place.summary } : {}),
      address: { '@type': 'PostalAddress', addressRegion: areaMeta.value.name, addressCountry: 'VN' },
    }),
  }] : [],
}))
</script>

<style scoped>
.ward { max-width: 1080px; margin: 0 auto; padding: 16px 16px 64px; }
.muted { color: var(--muted, #888); }
.ward-head { margin: 12px 0 8px; }
.ward-head h1 { margin: 0 0 4px; }
.ward-area { color: var(--muted, #777); margin: 0 0 8px; }
.ward-area a { color: var(--primary, #9C3D22); font-weight: 600; }
.ward-emoji { margin-right: 4px; }
.ward-summary { max-width: 70ch; }
.ward-sec { margin-top: 28px; }
.ward-sec h2 { font-size: 1.15rem; margin: 0 0 12px; border-bottom: 1px solid rgba(0,0,0,.08); padding-bottom: 6px; }
.ward-sec h2 .cnt { color: var(--muted, #999); font-weight: 400; font-size: .9rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }
.sec-empty { color: var(--muted, #999); font-size: .92rem; }
.sec-empty a { color: var(--primary, #9C3D22); }
.fac-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(260px,1fr)); }
.fac { border: 1px solid rgba(0,0,0,.1); border-radius: 10px; padding: 12px; }
.fac-kind { font-size: .78rem; color: var(--primary, #9C3D22); display: block; }
.fac-row { font-size: .9rem; margin: 2px 0; }
</style>
