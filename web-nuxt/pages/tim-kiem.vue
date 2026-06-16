<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Tìm kiếm' }]" />
    <div class="page-head">
      <h1>Tìm kiếm</h1>
      <p v-if="q">Kết quả cho "{{ q }}"</p>
    </div>
    <div class="search-row" style="margin-bottom: 16px">
      <input v-model="searchInput" type="search" placeholder="Tìm đặc sản, trải nghiệm…" @keyup.enter="doSearch" />
      <button class="btn btn-primary" @click="doSearch">Tìm</button>
    </div>

    <ClientOnly>
      <AISearchAssist v-if="q" :query="q" />
    </ClientOnly>

    <p v-if="hasError" style="color: #D94F3D; text-align: center; padding: 20px">Lỗi tìm kiếm. Vui lòng thử lại.</p>
    <template v-else-if="results.length">
      <p class="result-meta">{{ results.length }} kết quả</p>
      <div class="grid">
        <EntityCard v-for="e in results" :key="e.id" :entity="e" />
      </div>
    </template>
    <template v-else-if="q">
      <EmptyState message="Không tìm thấy kết quả nào." />
      <ClientOnly>
        <AIRecommendations title="Gợi ý cho bạn" :limit="6" />
      </ClientOnly>
    </template>
  </section>
</template>

<script setup lang="ts">
const route = useRoute()
const q = computed(() => (route.query.q as string) || '')
const searchInput = ref(q.value)

const { data, error: searchError } = await useAsyncData(
  'search-results',
  () => q.value ? $fetch<any>(`/api/entities?q=${encodeURIComponent(q.value)}&limit=100`) : Promise.resolve({ entities: [] }),
  { watch: [q] }
)

const results = computed(() => data.value?.entities || [])
const hasError = computed(() => !!searchError.value)

function doSearch() {
  if (searchInput.value.trim()) {
    navigateTo(`/tim-kiem?q=${encodeURIComponent(searchInput.value.trim())}`)
  }
}

watch(q, (v) => { searchInput.value = v })

useSeoMeta({
  title: q.value ? `"${q.value}" — Tìm kiếm — vinhlong360` : 'Tìm kiếm — vinhlong360',
  description: q.value ? `Kết quả tìm kiếm cho "${q.value}" trên vinhlong360.` : 'Tìm kiếm đặc sản, trải nghiệm, lưu trú tại Vĩnh Long.',
  ogTitle: q.value ? `"${q.value}" — vinhlong360` : 'Tìm kiếm — vinhlong360',
})
useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/tim-kiem') }],
  meta: [{ name: 'robots', content: 'noindex,follow' }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      name: 'vinhlong360',
      url: 'https://vinhlong360.vn',
      potentialAction: {
        '@type': 'SearchAction',
        target: { '@type': 'EntryPoint', urlTemplate: 'https://vinhlong360.vn/tim-kiem?q={search_term_string}' },
        'query-input': 'required name=search_term_string',
      },
    }),
  }],
})
</script>
