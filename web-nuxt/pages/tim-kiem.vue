<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Tìm kiếm' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-search">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon">🔍</span>
        <div>
          <h1>Tìm kiếm</h1>
          <p>Tìm đặc sản, trải nghiệm, lưu trú, lễ hội — mọi thứ về Vĩnh Long, Bến Tre, Trà Vinh.</p>
        </div>
      </div>
    </section>

    <div class="search-row search-row-spaced">
      <input v-model="searchInput" type="search" placeholder="Tìm đặc sản, trải nghiệm…" @keyup.enter="doSearch" />
      <button class="btn btn-primary" @click="doSearch">Tìm</button>
    </div>

    <NuxtErrorBoundary>
      <ClientOnly>
        <AISearchAssist v-if="q" :query="q" />
      </ClientOnly>
    </NuxtErrorBoundary>

    <p v-if="hasError" class="fetch-error">Lỗi tìm kiếm. Vui lòng thử lại.</p>
    <template v-else-if="results.length">
      <p class="result-meta" aria-live="polite">{{ results.length }} kết quả cho "{{ q }}"</p>
      <div class="grid">
        <EntityCard v-for="e in results" :key="e.id" :entity="e" />
      </div>
    </template>
    <template v-else-if="q">
      <EmptyState icon="🔍" title="Không tìm thấy kết quả" message="Thử từ khóa khác hoặc khám phá danh mục bên dưới.">
        <template #actions>
          <NuxtLink to="/du-lich" class="btn btn-outline">Khám phá du lịch</NuxtLink>
          <NuxtLink to="/san-pham" class="btn btn-outline">Xem sản phẩm</NuxtLink>
        </template>
      </EmptyState>
      <NuxtErrorBoundary>
        <ClientOnly>
          <AIRecommendations title="Gợi ý cho bạn" :limit="6" />
        </ClientOnly>
      </NuxtErrorBoundary>
    </template>

    <!-- Quick explore when no query -->
    <template v-if="!q">
      <section class="block reveal">
        <div class="section-head">
          <h2>Khám phá theo danh mục</h2>
        </div>
        <div class="quick-picks">
          <NuxtLink to="/du-lich" class="quick-pick">
            <span class="quick-pick-icon">🌿</span>
            <span class="quick-pick-label">Du lịch</span>
          </NuxtLink>
          <NuxtLink to="/san-pham" class="quick-pick">
            <span class="quick-pick-icon">🍊</span>
            <span class="quick-pick-label">Đặc sản</span>
          </NuxtLink>
          <NuxtLink to="/luu-tru" class="quick-pick">
            <span class="quick-pick-icon">🏡</span>
            <span class="quick-pick-label">Lưu trú</span>
          </NuxtLink>
          <NuxtLink to="/ocop" class="quick-pick">
            <span class="quick-pick-icon">⭐</span>
            <span class="quick-pick-label">OCOP</span>
          </NuxtLink>
          <NuxtLink to="/le-hoi" class="quick-pick">
            <span class="quick-pick-icon">🎊</span>
            <span class="quick-pick-label">Lễ hội</span>
          </NuxtLink>
          <NuxtLink to="/lich-trinh" class="quick-pick">
            <span class="quick-pick-icon">🗓️</span>
            <span class="quick-pick-label">Lịch trình</span>
          </NuxtLink>
        </div>
      </section>

      <section class="block reveal">
        <div class="section-head">
          <h2>Tìm theo khu vực</h2>
        </div>
        <div class="quick-picks">
          <NuxtLink to="/khu-vuc/vinh-long" class="quick-pick">
            <span class="quick-pick-icon">🍊</span>
            <span class="quick-pick-label">Vĩnh Long</span>
          </NuxtLink>
          <NuxtLink to="/khu-vuc/ben-tre" class="quick-pick">
            <span class="quick-pick-icon">🥥</span>
            <span class="quick-pick-label">Bến Tre</span>
          </NuxtLink>
          <NuxtLink to="/khu-vuc/tra-vinh" class="quick-pick">
            <span class="quick-pick-icon">🛕</span>
            <span class="quick-pick-label">Trà Vinh</span>
          </NuxtLink>
        </div>
      </section>
    </template>

    <!-- Cross-links -->
    <section class="block catalog-cross reveal">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/theo-mua" class="cross-card">
          <span class="cross-icon">🌸</span>
          <div><strong>Theo mùa</strong><p>Đúng mùa thưởng thức</p></div>
        </NuxtLink>
        <NuxtLink to="/cong-dong" class="cross-card">
          <span class="cross-icon">💬</span>
          <div><strong>Cộng đồng</strong><p>Hỏi đáp & chia sẻ</p></div>
        </NuxtLink>
        <NuxtLink to="/danh-ba" class="cross-card">
          <span class="cross-icon">🏛️</span>
          <div><strong>Danh bạ</strong><p>Hành chính xã/phường</p></div>
        </NuxtLink>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
useReveal()
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

<style scoped>
.search-row-spaced { margin-bottom: var(--space-5); }
.fetch-error { color: var(--error); text-align: center; padding: var(--space-5); }
.result-meta { font-size: var(--text-sm); color: var(--muted); margin-bottom: var(--space-4); }

.quick-picks { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: var(--space-3); }
.quick-pick { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); padding: var(--space-4); background: var(--card); border: 1px solid var(--line); border-radius: var(--radius-lg); text-align: center; transition: transform var(--duration-normal) var(--ease-spring), box-shadow var(--duration-normal) var(--ease-out), border-color var(--duration-fast); }
.quick-pick:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--primary-fg); }
.quick-pick:active { transform: scale(.97); transition-duration: .08s; }
.quick-pick-icon { font-size: var(--text-2xl); transition: transform var(--duration-normal) var(--ease-spring); }
.quick-pick:hover .quick-pick-icon { transform: scale(1.15); }
.quick-pick-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--ink); }

</style>
