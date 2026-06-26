<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Tìm kiếm' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-search">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🔍</span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
    </section>

    <div class="search-row search-row-spaced" :class="{ error: hasError }" role="search" aria-label="Tìm kiếm địa điểm">
      <div class="search-input-wrap" role="combobox" :aria-expanded="showSuggestions" aria-haspopup="listbox" aria-owns="search-suggestions">
        <input v-model="searchInput" type="search" enterkeyhint="search" placeholder="Tìm đặc sản, trải nghiệm…" aria-label="Tìm kiếm" :aria-invalid="hasError || undefined" autocomplete="off" aria-autocomplete="list" :aria-activedescendant="activeSuggestionId" @input="onTypeahead" @keyup.enter="onEnter" @keydown.down.prevent="sugNext" @keydown.up.prevent="sugPrev" @keydown.escape="sugClose" @blur="sugBlur" />
        <Transition name="sug-fade">
          <ul v-if="showSuggestions && suggestions.length" id="search-suggestions" class="search-suggestions" role="listbox" aria-label="Gợi ý tìm kiếm">
            <li v-for="(s, i) in suggestions" :key="s.id" :id="`sug-${s.id}`" role="option" :aria-selected="i === sugIdx" :class="['sug-item', { active: i === sugIdx }]" @mousedown.prevent="goToSuggestion(s)">
              <span class="sug-emoji" aria-hidden="true">{{ TYPE_META[s.type]?.emoji || '📍' }}</span>
              <span class="sug-name">{{ s.name }}</span>
              <span v-if="s.place_name" class="sug-place">{{ s.place_name }}</span>
            </li>
            <li id="sug-search-all" class="sug-item sug-all" role="option" :aria-selected="sugIdx === suggestions.length" :class="{ active: sugIdx === suggestions.length }" @mousedown.prevent="doSearch">
              🔍 Tìm tất cả "{{ searchInput.trim() }}"
            </li>
          </ul>
        </Transition>
      </div>
      <button type="button" class="btn btn-primary" @click="doSearch">Tìm</button>
    </div>

    <NuxtErrorBoundary>
      <ClientOnly>
        <AISearchAssist v-if="q" :query="q" />
      </ClientOnly>
    </NuxtErrorBoundary>

    <SkeletonGrid v-if="searching" :count="6" />
    <EmptyState v-else-if="hasError" icon="⚠️" title="Lỗi tìm kiếm" message="Không thể tải kết quả. Vui lòng thử lại.">
      <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData('search-results')">Thử lại</button>
    </EmptyState>
    <template v-else-if="q">
      <!-- Địa điểm / sản phẩm -->
      <template v-if="results.length">
        <div class="result-summary" aria-live="polite">
          <p class="result-meta">
            <strong class="result-query">"{{ q }}"</strong>
            <span class="result-count">{{ results.length }} địa điểm</span>
          </p>
          <ul v-if="typeBreakdown.length" class="result-types" aria-label="Phân loại kết quả">
            <li v-for="t in typeBreakdown" :key="t.type" class="result-type-badge">
              <span aria-hidden="true">{{ t.emoji }}</span>
              <span>{{ t.label }}</span>
              <span class="result-type-count">{{ t.count }}</span>
            </li>
          </ul>
        </div>
        <div class="grid">
          <EntityCard v-for="e in results" :key="e.id" :entity="e" />
        </div>
      </template>

      <!-- Người dùng -->
      <section v-if="userResults.length" class="block search-section reveal">
        <div class="section-head"><h2>Người dùng</h2></div>
        <div class="people-list">
          <NuxtLink v-for="u in userResults" :key="u.id" :to="`/nguoi-dung/${u.username || u.id}`" class="person-chip">
            <span class="avatar person-avatar">{{ (u.display_name || '?').charAt(0).toUpperCase() }}</span>
            <span class="person-name">{{ u.display_name }}</span>
            <span v-if="u.post_count" class="person-meta">{{ u.post_count }} bài</span>
          </NuxtLink>
        </div>
      </section>

      <!-- Bài viết cộng đồng -->
      <section v-if="postResults.length" class="block search-section reveal">
        <div class="section-head"><h2>Bài viết cộng đồng</h2></div>
        <div class="search-post-list">
          <NuxtLink v-for="p in postResults" :key="p.id" :to="`/bai-viet/${p.id}`" class="search-post-item">
            <div class="spi-head">
              <strong>{{ p.display_name || 'Người dùng' }}</strong>
              <span v-if="p.post_type_label" class="spi-type">{{ p.post_type_label }}</span>
            </div>
            <p class="spi-content">{{ p.content }}</p>
          </NuxtLink>
        </div>
      </section>

      <!-- Không có kết quả nào -->
      <template v-if="!results.length && !postResults.length && !userResults.length">
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
    </template>

    <!-- Quick explore when no query -->
    <template v-if="!q">
      <ClientOnly>
        <section v-if="recentItems.length" class="block reveal">
          <div class="section-head">
            <h2>Đã xem gần đây</h2>
          </div>
          <div class="recent-grid">
            <NuxtLink v-for="r in recentItems" :key="r.id" :to="`/dia-diem/${r.id}`" class="recent-card">
              <img v-if="r.image" :src="r.image" :alt="r.name" class="recent-img" loading="lazy" />
              <span v-else class="recent-img recent-placeholder" aria-hidden="true">{{ TYPE_META[r.type]?.emoji || '📍' }}</span>
              <span class="recent-name">{{ r.name }}</span>
              <span class="recent-type">{{ TYPE_META[r.type]?.label || r.type }}</span>
            </NuxtLink>
          </div>
        </section>
      </ClientOnly>

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
import { TYPE_META } from '~/composables/useConstants'
useReveal()
const { f: pc } = usePageContent('tim_kiem')
const { recentItems } = useRecentlyViewed()
const route = useRoute()
const q = computed(() => (route.query.q as string) || '')
const searchInput = ref(q.value)

const { data, error: searchError, status } = await useAsyncData(
  'search-results',
  () => q.value ? apiFetch<any>(`/api/entities?q=${encodeURIComponent(q.value)}&limit=100`) : Promise.resolve({ entities: [] }),
  { watch: [q] }
)
const searching = computed(() => status.value === 'pending' && !!q.value)

const results = computed(() => data.value?.entities || [])
const hasError = computed(() => !!searchError.value)

// Tìm hợp nhất: bài viết cộng đồng + người dùng (song song, không chặn entity).
const { data: extra } = await useAsyncData(
  'search-extra',
  () => q.value
    ? Promise.all([
        apiFetch<any>(`/api/search/posts?q=${encodeURIComponent(q.value)}`).catch(() => ({ posts: [] })),
        apiFetch<any>(`/api/search/users?q=${encodeURIComponent(q.value)}`).catch(() => ({ users: [] })),
      ]).then(([p, u]) => ({ posts: (p.posts || []).slice(0, 6), users: (u.users || []).slice(0, 8) }))
    : Promise.resolve({ posts: [], users: [] }),
  { watch: [q] },
)
const postResults = computed(() => extra.value?.posts || [])
const userResults = computed(() => extra.value?.users || [])

// SERPs-style type distribution badges (e.g. 5 Trải nghiệm · 4 Đặc sản · 3 Lưu trú).
const typeBreakdown = computed(() => {
  const counts = new Map<string, number>()
  for (const e of results.value as any[]) {
    const t = e?.type
    if (t) counts.set(t, (counts.get(t) || 0) + 1)
  }
  return [...counts.entries()]
    .map(([type, count]) => ({
      type,
      count,
      label: TYPE_META[type]?.label || type,
      emoji: TYPE_META[type]?.emoji || '📍',
    }))
    .sort((a, b) => b.count - a.count)
})

function doSearch() {
  sugClose()
  if (searchInput.value.trim()) {
    navigateTo(`/tim-kiem?q=${encodeURIComponent(searchInput.value.trim())}`)
  }
}

const suggestions = ref<any[]>([])
const sugIdx = ref(-1)
const showSuggestions = ref(false)
let sugTimer: ReturnType<typeof setTimeout> | null = null
const activeSuggestionId = computed(() => {
  if (sugIdx.value < 0 || !showSuggestions.value) return undefined
  if (sugIdx.value < suggestions.value.length) return `sug-${suggestions.value[sugIdx.value].id}`
  if (sugIdx.value === suggestions.value.length) return 'sug-search-all'
  return undefined
})

function onTypeahead() {
  const term = searchInput.value.trim()
  if (sugTimer) clearTimeout(sugTimer)
  if (term.length < 2) { sugClose(); return }
  sugTimer = setTimeout(async () => {
    try {
      const res = await $fetch<any>(`/api/entities?q=${encodeURIComponent(term)}&limit=5`)
      suggestions.value = res.entities || []
      sugIdx.value = -1
      showSuggestions.value = suggestions.value.length > 0
    } catch { suggestions.value = []; showSuggestions.value = false }
  }, 300)
}
function sugNext() {
  if (!showSuggestions.value) return
  sugIdx.value = Math.min(sugIdx.value + 1, suggestions.value.length)
}
function sugPrev() {
  if (!showSuggestions.value) return
  sugIdx.value = Math.max(sugIdx.value - 1, -1)
}
function sugClose() { showSuggestions.value = false; sugIdx.value = -1 }
function sugBlur() { setTimeout(sugClose, 150) }
function goToSuggestion(s: any) {
  sugClose()
  navigateTo(`/dia-diem/${s.id}`)
}
function onEnter() {
  if (showSuggestions.value && sugIdx.value >= 0 && sugIdx.value < suggestions.value.length) {
    goToSuggestion(suggestions.value[sugIdx.value])
  } else {
    doSearch()
  }
}

watch(q, (v) => { searchInput.value = v; sugClose() })

useSeoMeta({
  title: () => q.value.trim() ? `"${q.value.trim()}" — Tìm kiếm — vinhlong360` : pc('seo_title'),
  description: () => q.value.trim() ? `Kết quả tìm kiếm cho "${q.value.trim()}" trên vinhlong360.` : pc('seo_description'),
  ogTitle: () => q.value.trim() ? `"${q.value.trim()}" — vinhlong360` : pc('og_title'),
  ogDescription: () => pc('og_description'),
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

/* Result summary header (SERPs-style query echo + type breakdown) */
.result-summary { margin-bottom: var(--space-4); }
.result-meta { display: flex; align-items: baseline; flex-wrap: wrap; gap: var(--space-2); font-size: var(--text-sm); color: var(--muted); margin-bottom: var(--space-2); }
.result-query { color: var(--ink); font-weight: var(--weight-semibold); }
.result-count { color: var(--muted); }
.result-types { display: flex; flex-wrap: wrap; gap: var(--space-2); list-style: none; padding: 0; margin: 0; }
.result-type-badge {
  display: inline-flex; align-items: center; gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  background: var(--bg-alt); border: .5px solid var(--line);
  border-radius: var(--radius-full);
  font-size: var(--text-xs); font-weight: var(--weight-medium); color: var(--ink);
}
.result-type-count { color: var(--primary-fg); font-weight: var(--weight-semibold); }

/* Search input error feedback */
.search-row.error input { border-color: var(--error); box-shadow: 0 0 0 3px rgba(var(--error-rgb, 217, 79, 61), .12); }

/* Unified search: người dùng + bài viết */
.search-section { margin-top: var(--space-5); }
.people-list { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.person-chip { display: inline-flex; align-items: center; gap: var(--space-2); padding: var(--space-1) var(--space-3) var(--space-1) var(--space-1); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-full); text-decoration: none; color: var(--ink); transition: border-color .25s var(--ease-out), transform .25s var(--ease-spring-gentle); }
.person-chip:hover { border-color: var(--primary-fg); transform: translateY(-1px); }
.person-avatar { width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary); color: var(--primary-fg, #fff); font-size: var(--text-xs); font-weight: var(--weight-semibold); }
.person-name { font-size: var(--text-sm); font-weight: var(--weight-medium); }
.person-meta { font-size: var(--text-xs); color: var(--muted); }
.search-post-list { display: flex; flex-direction: column; gap: var(--space-2); }
.search-post-item { display: block; padding: var(--space-3); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-lg); text-decoration: none; color: var(--ink); transition: border-color .25s var(--ease-out); }
.search-post-item:hover { border-color: var(--primary-fg); }
.spi-head { display: flex; align-items: center; gap: var(--space-2); margin-bottom: .2rem; }
.spi-head strong { font-size: var(--text-sm); }
.spi-type { font-size: var(--text-xs); color: var(--muted); background: var(--bg-alt); padding: 1px 8px; border-radius: var(--radius-full); }
.spi-content { font-size: var(--text-sm); color: var(--ink-700); margin: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

.quick-picks { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: var(--space-3); }
.quick-pick { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); padding: var(--space-4); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-lg); text-align: center; box-shadow: var(--shadow-xs); transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out); }
.quick-pick:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--primary-fg); background: rgba(var(--primary-rgb), .04); }
.quick-pick:active { transform: scale(.97); transition-duration: .08s; }
.quick-pick:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.quick-pick-icon { font-size: var(--text-2xl); transition: transform .35s var(--ease-spring-gentle); }
.quick-pick:hover .quick-pick-icon { transform: scale(1.15); }
.quick-pick-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--ink); }

/* Autocomplete suggestions */
.search-input-wrap { position: relative; flex: 1; min-width: 0; }
.search-suggestions {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 20;
  margin: var(--space-1) 0 0; padding: var(--space-1); list-style: none;
  background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-lg);
  max-height: 320px; overflow-y: auto;
}
.sug-item {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-3); border-radius: var(--radius-md);
  cursor: pointer; font-size: var(--text-sm); color: var(--ink);
  transition: background .15s;
}
.sug-item:hover, .sug-item.active { background: var(--bg-alt); }
.sug-emoji { flex-shrink: 0; }
.sug-name { font-weight: var(--weight-medium); }
.sug-place { color: var(--muted); font-size: var(--text-xs); margin-left: auto; flex-shrink: 0; }
.sug-all { color: var(--primary-fg); font-weight: var(--weight-semibold); border-top: .5px solid var(--line); margin-top: var(--space-1); padding-top: var(--space-2); }
.sug-fade-enter-active { transition: opacity .15s, transform .15s; }
.sug-fade-leave-active { transition: opacity .1s; }
.sug-fade-enter-from { opacity: 0; transform: translateY(-4px); }
.sug-fade-leave-to { opacity: 0; }
.dark .search-suggestions { background: var(--card); border-color: rgba(255,255,255,.1); }
.dark .sug-item:hover, .dark .sug-item.active { background: rgba(255,255,255,.06); }

/* Search input polish */
.search-row-spaced input {
  transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo);
}
.search-row-spaced input:focus-visible {
  border-color: var(--primary-fg);
  box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .12);
}

/* Grid results stagger */
.grid { animation: fadeInGrid .4s var(--ease-out) both; }
@keyframes fadeInGrid { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }

/* Dark mode */
.dark .quick-pick { background: var(--bg-alt); border-color: var(--line); }
.dark .quick-pick:hover { border-color: rgba(255,255,255,.15); box-shadow: var(--shadow-md); background: rgba(255,255,255,.04); }
.dark .result-meta { color: var(--ink-tertiary); }
.dark .result-query { color: var(--ink); }
.dark .result-type-badge { background: rgba(255,255,255,.05); border-color: rgba(255,255,255,.1); }
.dark .fetch-error { color: var(--error); }

/* Recently viewed */
.recent-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: var(--space-3);
}
.recent-card {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-3); background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-lg); text-decoration: none; color: var(--ink); text-align: center;
  transition: transform .3s var(--ease-spring-gentle), box-shadow .3s var(--ease-out), border-color .3s;
}
.recent-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--primary-fg); }
.recent-card:active { transform: scale(.97); transition-duration: .08s; }
.recent-card:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.recent-img {
  width: 56px; height: 56px; border-radius: var(--radius-md); object-fit: cover;
}
.recent-placeholder {
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-alt); font-size: var(--text-xl);
}
.recent-name { font-size: var(--text-xs); font-weight: var(--weight-semibold); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.3; }
.recent-type { font-size: 10px; color: var(--muted); }
.dark .recent-card { background: var(--bg-alt); border-color: var(--line); }
.dark .recent-card:hover { border-color: rgba(255,255,255,.15); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .quick-pick:hover { transform: none; }
  .quick-pick:active { transform: none; }
  .quick-pick:hover .quick-pick-icon { transform: none; }
  .recent-card:hover { transform: none; }
  .recent-card:active { transform: none; }
  .grid { animation: none; opacity: 1; transform: none; }
}
</style>
