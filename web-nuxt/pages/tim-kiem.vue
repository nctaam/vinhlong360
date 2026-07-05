<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Tìm kiếm' }]" />

    <!-- Hero: masthead + hero-scale input, sediment tick as the search's vertical accent -->
    <section class="catalog-hero cat-search search-hero">
      <span class="dateline-eyebrow">Tìm kiếm · Vĩnh Long · Bến Tre · Trà Vinh</span>
      <h1>{{ pc('hero_title') }}</h1>
      <p class="search-ticker-line" aria-live="off">
        <span class="search-ticker-word" :key="tickerIdx">{{ tickerPhrase }}<span class="search-ticker-q">?</span></span>
      </p>

      <div class="search-row search-row-spaced search-row-hero" :class="{ error: hasError }" role="search" aria-label="Tìm kiếm địa điểm">
        <div class="search-input-wrap" role="combobox" :aria-expanded="showSuggestions" aria-haspopup="listbox" aria-owns="search-suggestions">
          <input v-model="searchInput" type="search" enterkeyhint="search" :placeholder="inputPlaceholder" aria-label="Tìm kiếm" :aria-invalid="hasError || undefined" autocomplete="off" aria-autocomplete="list" :aria-activedescendant="activeSuggestionId" @input="onTypeahead" @keyup.enter="onEnter" @keydown.down.prevent="sugNext" @keydown.up.prevent="sugPrev" @keydown.escape="sugClose" @focus="inputFocused = true" @blur="onInputBlur" />
          <div v-if="sugLoading" class="sug-loading" aria-hidden="true"><span class="spinner spinner-xs"></span></div>
          <Transition name="sug-fade">
            <ul v-if="showSuggestions && suggestions.length" id="search-suggestions" class="search-suggestions" role="listbox" aria-label="Gợi ý tìm kiếm">
              <li v-for="(s, i) in suggestions" :key="s.id" :id="`sug-${s.id}`" role="option" :aria-selected="i === sugIdx" :class="['sug-item', `sug-cat-${TYPE_META[s.type]?.cat || 'place'}`, { active: i === sugIdx }]" @mousedown.prevent="goToSuggestion(s)">
                <span class="sug-name">{{ s.name }}</span>
                <span v-if="s.place_name" class="sug-place">{{ s.place_name }}</span>
              </li>
              <li id="sug-search-all" class="sug-item sug-all" role="option" :aria-selected="sugIdx === suggestions.length" :class="{ active: sugIdx === suggestions.length }" @mousedown.prevent="doSearch">
                Tìm tất cả „{{ searchInput.trim() }}"
              </li>
            </ul>
          </Transition>
        </div>
        <button type="button" class="btn btn-primary" @click="doSearch">Tìm</button>
      </div>
    </section>

    <NuxtErrorBoundary>
      <ClientOnly>
        <LazyAISearchAssist v-if="q" :query="q" />
        <template #fallback>
          <div v-if="q" class="ai-loading ai-loading-padded" role="status" aria-label="Đang tải gợi ý AI"><div class="spinner spinner-center"></div></div>
        </template>
      </ClientOnly>
    </NuxtErrorBoundary>

    <SkeletonGrid v-if="searching" :count="6" />
    <EmptyState v-else-if="hasError" title="Lỗi tìm kiếm" message="Không thể tải kết quả. Vui lòng thử lại.">
      <template #actions>
        <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData('search-results')">Thử lại</button>
      </template>
    </EmptyState>
    <template v-else-if="q">
      <!-- Địa điểm / sản phẩm -->
      <template v-if="results.length">
        <p class="result-strap" aria-live="polite">
          <span class="result-strap-query">„{{ q }}"</span> — {{ resultStrapLine }}
        </p>
        <div class="grid">
          <EntityCard v-for="e in results" :key="e.id" :entity="e" />
        </div>
      </template>

      <!-- Cũng có trong cộng đồng: người dùng + bài viết, thứ yếu so với kết quả địa điểm -->
      <section v-if="userResults.length || postResults.length" class="block search-section-secondary reveal">
        <div class="section-head sediment-head"><h2>Cũng có trong cộng đồng</h2></div>
        <div v-if="userResults.length" class="people-list">
          <NuxtLink v-for="u in userResults" :key="u.id" :to="userPath(u.username || u.id)" class="person-chip">
            <span class="avatar person-avatar">{{ (u.display_name || '?').charAt(0).toUpperCase() }}</span>
            <span class="person-name">{{ u.display_name }}</span>
            <span v-if="u.post_count" class="person-meta">{{ u.post_count }} bài</span>
          </NuxtLink>
        </div>
        <div v-if="postResults.length" class="search-post-list">
          <NuxtLink v-for="p in postResults" :key="p.id" :to="postPath(p.id)" class="search-post-item">
            <div class="spi-head">
              <strong>{{ p.display_name || 'Người dùng' }}</strong>
              <span v-if="p.post_type_label" class="spi-type">{{ p.post_type_label }}</span>
            </div>
            <p class="spi-content">{{ p.content }}</p>
          </NuxtLink>
        </div>
      </section>

      <NuxtErrorBoundary v-if="results.length || postResults.length || userResults.length">
        <ClientOnly>
          <LazySmartRecommendations context="search" :query="q" title="Gợi ý tiếp theo" :limit="6" />
        </ClientOnly>
      </NuxtErrorBoundary>
      <JourneyActionRail
        v-if="searchNextActions.length"
        :actions="searchNextActions"
        title="Bước tiếp theo"
        compact
      />

      <!-- Không có kết quả nào — đây là khoảnh khắc phục hồi, không phải ngõ cụt -->
      <template v-if="!results.length && !postResults.length && !userResults.length">
        <EmptyState title="Chưa thấy đúng ý bạn" message="Nhưng biết đâu những gợi ý dưới đây lại hợp — phù sa vẫn còn nhiều thứ để kể.">
          <template #actions>
            <NuxtLink to="/du-lich" class="btn btn-outline">Khám phá du lịch</NuxtLink>
            <NuxtLink to="/san-pham" class="btn btn-outline">Xem sản phẩm</NuxtLink>
          </template>
        </EmptyState>
        <NuxtErrorBoundary>
          <ClientOnly>
            <LazySmartRecommendations context="search" :query="q" title="Có phải bạn muốn tìm…" :limit="6" />
          </ClientOnly>
        </NuxtErrorBoundary>
        <JourneyActionRail
          :actions="zeroResultActions"
          title="Có thể đi tiếp theo hướng này"
          compact
        />
      </template>
    </template>

    <!-- Trước khi gõ: tầng khám phá — trọng tâm thật sự của trang này -->
    <template v-if="!q">
      <!-- Row A: Đang được hỏi nhiều — chip tĩnh, đã tuyển chọn -->
      <section class="block reveal">
        <div class="section-head sediment-head"><h2>Đang được hỏi nhiều</h2></div>
        <div class="scroll-row trending-row">
          <button
            v-for="(chip, i) in trendingChips"
            :key="i"
            type="button"
            class="trending-chip"
            @click="goTrending(chip)"
          >
            <span class="trending-dot" aria-hidden="true"></span>
            <span>{{ chip }}</span>
          </button>
        </div>
      </section>

      <!-- Row B: gợi ý đáng chú ý — recommendation engine sẵn có (context hợp lệ, không tự chế) -->
      <NuxtErrorBoundary>
        <ClientOnly>
          <LazySmartRecommendations context="search" title="Đáng chú ý lúc này" :limit="3" />
        </ClientOnly>
      </NuxtErrorBoundary>

      <!-- Row C: Tiếp tục nơi bạn dừng lại — filmstrip, không phải lưới phẳng -->
      <ClientOnly>
        <section v-if="recentItems.length" class="block reveal">
          <div class="section-head sediment-head"><h2>Tiếp tục nơi bạn dừng lại</h2></div>
          <div class="scroll-row recent-filmstrip">
            <NuxtLink v-for="r in recentItems" :key="r.id" :to="entityPath(r.id)" class="recent-card">
              <img v-if="r.image" :src="r.image" :alt="r.name" class="recent-img" width="56" height="56" loading="lazy" decoding="async" @error="(e: Event) => ((e.target as HTMLImageElement).style.display = 'none')" />
              <span v-else class="recent-img recent-placeholder" aria-hidden="true" :style="{ backgroundImage: categoryPlaceholderBg(r.id, TYPE_META[r.type]?.cat) }"><span class="recent-placeholder-glyph" v-html="categoryGlyph(TYPE_META[r.type]?.cat)"></span></span>
              <span class="recent-name">{{ r.name }}</span>
              <span class="recent-type">{{ TYPE_META[r.type]?.label || r.type }}</span>
            </NuxtLink>
          </div>
        </section>
      </ClientOnly>

      <!-- Row D: Khám phá theo chủ đề — glyph thay emoji, cùng ngôn ngữ với EntityCard -->
      <section class="block reveal">
        <div class="section-head sediment-head"><h2>Khám phá theo chủ đề</h2></div>
        <div class="quick-picks">
          <NuxtLink v-for="qp in quickPicks" :key="qp.to" :to="qp.to" class="quick-pick">
            <span class="quick-pick-icon" :style="{ backgroundImage: categoryPlaceholderBg(qp.to, qp.cat) }">
              <span class="quick-pick-glyph" v-html="categoryGlyph(qp.cat)"></span>
            </span>
            <span class="quick-pick-label">{{ qp.label }}</span>
          </NuxtLink>
        </div>
      </section>

      <section class="block reveal">
        <div class="section-head sediment-head"><h2>Tìm theo khu vực</h2></div>
        <div class="quick-picks">
          <NuxtLink to="/khu-vuc/vinh-long" class="quick-pick">
            <span class="quick-pick-label">Vĩnh Long</span>
          </NuxtLink>
          <NuxtLink to="/khu-vuc/ben-tre" class="quick-pick">
            <span class="quick-pick-label">Bến Tre</span>
          </NuxtLink>
          <NuxtLink to="/khu-vuc/tra-vinh" class="quick-pick">
            <span class="quick-pick-label">Trà Vinh</span>
          </NuxtLink>
        </div>
      </section>
    </template>

    <!-- Cross-links -->
    <section class="block band catalog-cross reveal">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon" aria-hidden="true">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/theo-mua" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🌸</span>
          <div><strong>Theo mùa</strong><p>Đúng mùa thưởng thức</p></div>
        </NuxtLink>
        <NuxtLink to="/cong-dong" class="cross-card">
          <span class="cross-icon" aria-hidden="true">💬</span>
          <div><strong>Cộng đồng</strong><p>Hỏi đáp & chia sẻ</p></div>
        </NuxtLink>
        <NuxtLink to="/danh-ba" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🏛️</span>
          <div><strong>Danh bạ</strong><p>Hành chính xã/phường</p></div>
        </NuxtLink>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { TYPE_META } from '~/composables/useConstants'
import { useJourneyActions } from '~/composables/useJourneyActions'
import { generateCategoryIcon, generateCategoryPlaceholder } from '~/composables/useCategoryPlaceholder'
useReveal()
const { f: pc } = usePageContent('tim_kiem')
const { recentItems } = useRecentlyViewed()
const { trackSearch } = useUserEvents()
const { searchAll, fetchEntitySuggestions } = useUnifiedSearch()
const { searchRecoveryActions, searchSuccessActions } = useJourneyActions()
const route = useRoute()

// Same pairing EntityCard uses: glyph (currentColor/white-watermark strokes) is only
// legible over its matching seeded gradient — never drop the glyph on a bare card.
function categoryGlyph(cat?: string) {
  return generateCategoryIcon(cat || 'place')
}
function categoryPlaceholderBg(seedId: string, cat?: string) {
  return generateCategoryPlaceholder(seedId, cat || 'place')
}

// Câu hỏi thật, đặc trưng miền Tây — danh sách tĩnh đã tuyển chọn (không gọi LLM,
// không backend trending — đúng tinh thần §B8: đây là copy trình bày, không phải
// dữ liệu sống). Dùng làm cả ticker hero lẫn placeholder input khi rảnh gõ.
const TICKER_PHRASES = [
  'bún nước lèo ở đâu chuẩn vị Khmer',
  'mùa này bưởi Năm Roi ngọt chưa',
  'ngủ đêm giữa vườn dừa, ở đâu',
  'chợ nổi Cái Bè còn họp giờ nào',
  'dừa xiêm Bến Tre uống tại vườn',
  'đờn ca tài tử nghe ở đâu',
  'cù lao nào yên tĩnh nhất',
]
const tickerIdx = ref(0)
const tickerPhrase = computed(() => TICKER_PHRASES[tickerIdx.value % TICKER_PHRASES.length])
const inputFocused = ref(false)
const inputPlaceholder = computed(() =>
  inputFocused.value || searchInput.value ? 'Tìm đặc sản, trải nghiệm…' : `${tickerPhrase.value}…`
)
let tickerTimer: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
  tickerTimer = setInterval(() => { tickerIdx.value++ }, 4000)
})
onBeforeUnmount(() => { if (tickerTimer) clearInterval(tickerTimer) })

// Row A — "Đang được hỏi nhiều": chip tĩnh dẫn thẳng vào một câu tìm kiếm thật.
const trendingChips = [
  'bún nước lèo',
  'bưởi Năm Roi',
  'homestay vườn dừa',
  'chợ nổi Cái Bè',
  'dừa sáp Cầu Kè',
  'đờn ca tài tử',
]
function goTrending(term: string) {
  trackSearch(term, { context: 'search_trending' })
  navigateTo(`/tim-kiem?q=${encodeURIComponent(term)}`)
}

// Row D — "Khám phá theo chủ đề": cat khớp CATEGORY_HUE/generateCategoryIcon để
// glyph + màu đồng nhất với EntityCard placeholder trên toàn site.
const quickPicks = [
  { to: '/du-lich', label: 'Du lịch', cat: 'nature' },
  { to: '/san-pham', label: 'Đặc sản', cat: 'product' },
  { to: '/luu-tru', label: 'Lưu trú', cat: 'accommodation' },
  { to: '/ocop', label: 'OCOP', cat: 'craft' },
  { to: '/le-hoi', label: 'Lễ hội', cat: 'event' },
  { to: '/lich-trinh', label: 'Lịch trình', cat: 'itinerary' },
]
function firstQueryValue(value: unknown) {
  return Array.isArray(value) ? String(value[0] || '') : String(value || '')
}
const q = computed(() => firstQueryValue(route.query.q))
const searchInput = ref(q.value)

const { data, error: searchError, status } = await useAsyncData(
  'search-results',
  () => q.value ? searchAll(q.value, 100) : Promise.resolve({ entities: [], posts: [], users: [], totals: { entities: 0, posts: 0, users: 0 } }),
  { watch: [q] }
)
const searching = computed(() => status.value === 'pending' && !!q.value)

const results = computed(() => data.value?.entities || data.value?.results || [])
const hasError = computed(() => !!searchError.value)
const postResults = computed(() => (data.value?.posts || []).slice(0, 6))
const userResults = computed(() => (data.value?.users || []).slice(0, 8))
const totalSearchResults = computed(() => results.value.length + postResults.value.length + userResults.value.length)
const searchNextActions = computed(() => q.value && totalSearchResults.value ? searchSuccessActions(q.value, results.value.length) : [])
const zeroResultActions = computed(() => q.value ? searchRecoveryActions(q.value) : [])

if (import.meta.client) {
  watch([q, results, postResults, userResults], ([term, entityList, postList, userList]) => {
    if (!term.trim() || searching.value) return
    const total = entityList.length + postList.length + userList.length
    trackSearch(term, {
      context: 'search',
      metadata: {
        result_count: entityList.length,
        post_count: postList.length,
        user_count: userList.length,
        total_result_count: total,
        zero_result: total === 0,
      },
    })
  }, { flush: 'post' })
}

// Type distribution — real counts from the actual result set, used to compose
// the curatorial strap-line (e.g. "4 món ăn, 3 điểm đến và 1 lễ hội").
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
    }))
    .sort((a, b) => b.count - a.count)
})

// Narrator's-voice strap-line — reframes the SERP meta line as a curated sentence.
// Built purely from typeBreakdown (real data), never invented counts.
function pluralLabel(label: string, count: number) {
  return `${count} ${label.toLowerCase()}`
}
const resultStrapLine = computed(() => {
  const n = results.value.length
  if (!n) return ''
  const parts = typeBreakdown.value.map(t => pluralLabel(t.label, t.count))
  if (parts.length <= 1) return `phù sa mang về ${parts[0] || `${n} kết quả`} quanh câu hỏi này.`
  const last = parts[parts.length - 1]
  const head = parts.slice(0, -1).join(', ')
  return `phù sa mang về ${head} và ${last} quanh câu hỏi này.`
})

function doSearch() {
  sugClose()
  if (searchInput.value.trim()) {
    trackSearch(searchInput.value, { context: 'search_submit' })
    navigateTo(`/tim-kiem?q=${encodeURIComponent(searchInput.value.trim())}`)
  }
}

const suggestions = ref<any[]>([])
const sugIdx = ref(-1)
const showSuggestions = ref(false)
const sugLoading = ref(false)
let sugTimer: ReturnType<typeof setTimeout> | null = null
let sugAbort: AbortController | null = null
const activeSuggestionId = computed(() => {
  if (sugIdx.value < 0 || !showSuggestions.value) return undefined
  if (sugIdx.value < suggestions.value.length) return `sug-${suggestions.value[sugIdx.value].id}`
  if (sugIdx.value === suggestions.value.length) return 'sug-search-all'
  return undefined
})

function onTypeahead() {
  const term = searchInput.value.trim()
  if (sugTimer) clearTimeout(sugTimer)
  if (term.length < 2) { sugClose(); sugLoading.value = false; return }
  sugLoading.value = true
  sugTimer = setTimeout(async () => {
    sugAbort?.abort()
    const ctrl = new AbortController()
    sugAbort = ctrl
    try {
      const res = await fetchEntitySuggestions(term, 5, { signal: ctrl.signal })
      if (ctrl.signal.aborted) return
      suggestions.value = res || []
      sugIdx.value = -1
      showSuggestions.value = suggestions.value.length > 0
    } catch { if (!ctrl.signal.aborted) { suggestions.value = []; showSuggestions.value = false } }
    sugLoading.value = false
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
let blurTimer: ReturnType<typeof setTimeout> | null = null
function sugBlur() { blurTimer = setTimeout(sugClose, 150) }
function onInputBlur() { inputFocused.value = false; sugBlur() }
function goToSuggestion(s: any) {
  sugClose()
  navigateTo(entityPath(s.id))
}
function onEnter() {
  if (showSuggestions.value && sugIdx.value >= 0 && sugIdx.value < suggestions.value.length) {
    goToSuggestion(suggestions.value[sugIdx.value])
  } else {
    doSearch()
  }
}

watch(q, (v) => { searchInput.value = v; sugClose() })

onBeforeUnmount(() => {
  if (sugTimer) clearTimeout(sugTimer)
  if (blurTimer) clearTimeout(blurTimer)
  sugAbort?.abort()
})

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
.sug-loading { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); pointer-events: none; }
.fetch-error { color: var(--error); text-align: center; padding: var(--space-5); }

/* Result strap-line — narrator's-voice reframe of the old SERP meta line + type-badge row. */
.result-strap {
  margin: 0 0 var(--space-4);
  font-family: var(--font-editorial);
  font-style: italic;
  font-size: var(--text-lg);
  line-height: var(--leading-snug);
  color: var(--ink-700);
}
.result-strap-query { color: var(--ink); font-weight: var(--weight-semibold); font-style: normal; }
.dark .result-strap { color: var(--ink-tertiary); }
.dark .result-strap-query { color: var(--ink); }

/* Search input error feedback */
.search-row.error input { border-color: var(--error); box-shadow: 0 0 0 3px rgba(var(--error-rgb, 217, 79, 61), .12); }

/* Unified search: người dùng + bài viết — secondary strip, smaller than the primary entity grid */
.search-section { margin-top: var(--space-5); }
.search-section-secondary { padding-top: var(--space-6); padding-bottom: var(--space-3); }
.search-section-secondary .section-head { margin-bottom: var(--space-4); }
.search-section-secondary .section-head h2 { font-size: var(--text-lg); }
.search-section-secondary .people-list { margin-bottom: var(--space-3); }
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
/* Glyph swap: same pairing EntityCard uses — seeded gradient swatch (generateCategoryPlaceholder)
   behind the white-watermark glyph (generateCategoryIcon), never the bare glyph alone (its fills
   are translucent-white, illegible without the saturated backdrop). Small size, rounded tile. */
.quick-pick-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 44px; height: 44px; border-radius: var(--radius-md);
  background-size: cover; background-position: center;
  transition: transform .35s var(--ease-spring-gentle);
}
.quick-pick-glyph { display: inline-flex; width: 24px; height: 24px; color: rgba(255,255,255,.85); }
.quick-pick-glyph :deep(svg) { width: 100%; height: 100%; }
.quick-pick:hover .quick-pick-icon { transform: scale(1.1); }
.quick-pick-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--ink); }

/* Autocomplete suggestions */
.search-input-wrap { position: relative; flex: 1; min-width: 0; }
.search-suggestions {
  position: absolute; top: 100%; left: 0; right: 0; z-index: var(--z-dropdown);
  margin: var(--space-1) 0 0; padding: var(--space-1); list-style: none;
  background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-lg);
  max-height: 320px; overflow-y: auto;
}
.sug-item {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-3); border-radius: var(--radius-md);
  cursor: pointer; font-size: var(--text-sm); color: var(--ink);
  border-left: 3px solid transparent;
  transition: background .15s, border-color .15s;
}
.sug-item:hover, .sug-item.active { background: var(--bg-alt); }
/* Category-color left-border strip — turns the dropdown into a tiny preview of the
   tri-province palette (leaf/amber/river/clay family) instead of a plain emoji list. */
.sug-cat-nature, .sug-cat-experience { border-left-color: var(--secondary); }
.sug-cat-dish, .sug-cat-product, .sug-cat-craft, .sug-cat-economy { border-left-color: var(--accent-dark); }
.sug-cat-attraction, .sug-cat-history, .sug-cat-place, .sug-cat-facility, .sug-cat-org { border-left-color: var(--river-600); }
.sug-cat-accommodation { border-left-color: var(--clay-400); }
.sug-cat-event, .sug-cat-person { border-left-color: var(--clay-600); }
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

/* ── Masthead: search is a mid-conversation moment, not an empty box ──
   .dateline-eyebrow is defined locally (not imported from assets/css/events.css,
   which is opted-in per-page only by le-hoi.vue/su-kien.vue) — same convention as the
   dateline eyebrow used elsewhere, kept scoped here per this unit's edit boundary. */
.search-hero { display: flex; flex-direction: column; }
.search-hero .dateline-eyebrow {
  position: relative;
  display: block;
  font-family: var(--font-sans);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--muted);
  margin: 0 0 var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: .5px solid var(--line);
}
.search-hero h1 { max-width: 18ch; }

/* Ticker — murmur distinct from the authoritative serif h1: sans, italic-ish via
   letter-spacing/opacity, small, muted. Cross-fades every 4s (JS index-cycle), freezes
   under reduced-motion (interval never starts — see script onMounted guard). */
.search-ticker-line {
  margin: var(--space-2) 0 var(--space-6);
  font-family: var(--font-sans);
  font-style: italic;
  font-size: var(--text-base);
  color: var(--muted);
  min-height: 1.4em;
}
.search-ticker-word {
  display: inline-block;
  animation: tickerIn .5s var(--ease-out) both;
}
.search-ticker-q { opacity: .6; margin-left: 1px; }
@keyframes tickerIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: none; }
}

/* Hero-scale input: oversized, sits on a hairline underline (not a boxed input), sediment
   tick to the left as the vertical accent echoing the section-head signature. */
.search-row-hero {
  position: relative;
  padding-left: var(--space-4);
  max-width: 640px;
}
.search-row-hero::before {
  content: "";
  position: absolute; left: 0; top: 2px; bottom: 2px;
  width: 4px; border-radius: var(--radius-full);
  background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .search-row-hero::before {
  background: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%);
}
.search-row-hero .search-input-wrap input {
  font-size: var(--text-2xl);
  font-style: normal;
  padding: var(--space-2) 0;
  background: transparent;
  border: none;
  border-bottom: 1.5px solid var(--line);
  border-radius: 0;
  box-shadow: none !important;
}
.search-row-hero .search-input-wrap input::placeholder {
  font-style: italic;
  color: var(--muted);
  opacity: .75;
}
.search-row-hero .search-input-wrap input:focus-visible {
  border-bottom-color: var(--primary-fg);
  box-shadow: none;
}
@media (max-width: 640px) {
  .search-row-hero { padding-left: var(--space-3); max-width: none; }
  .search-row-hero .search-input-wrap input { font-size: var(--text-xl); }
  .search-ticker-line { font-size: var(--text-sm); }
}

/* Row A: trending chips — reuses .scroll-row (catalog.css) for snap + edge-mask. */
.trending-chip {
  display: inline-flex; align-items: center; gap: var(--space-2);
  flex: 0 0 auto; padding: var(--space-2) var(--space-4);
  background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-full);
  font-size: var(--text-sm); font-weight: var(--weight-medium); color: var(--ink);
  cursor: pointer; white-space: nowrap;
  transition: border-color .25s var(--ease-out), transform .25s var(--ease-spring-gentle), background .25s var(--ease-out);
}
.trending-chip:hover { border-color: var(--primary-fg); transform: translateY(-1px); background: rgba(var(--primary-rgb), .04); }
.trending-chip:active { transform: scale(.97); transition-duration: .08s; }
.trending-chip:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.trending-row > * { flex: 0 0 auto; }
/* "Hot right now" dot — reuses the same restrained pulse token as EntityCard's peak-dot,
   settles after one breathing cycle rather than looping forever (motion-budget discipline). */
.trending-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent-dark);
  box-shadow: 0 0 0 0 rgba(var(--accent-rgb), .5);
  animation: trendingPulse 2.4s var(--ease-out) 1;
}
@keyframes trendingPulse {
  0% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), .5); }
  70% { box-shadow: 0 0 0 6px rgba(var(--accent-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0); }
}
.dark .trending-chip { background: var(--bg-alt); border-color: var(--line); }
.dark .trending-chip:hover { border-color: rgba(255,255,255,.15); background: rgba(255,255,255,.04); }

/* Grid results stagger */
.grid { animation: fadeInGrid .4s var(--ease-out) both; }
@keyframes fadeInGrid { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }

/* Dark mode */
.dark .quick-pick { background: var(--bg-alt); border-color: var(--line); }
.dark .quick-pick:hover { border-color: rgba(255,255,255,.15); box-shadow: var(--shadow-md); background: rgba(255,255,255,.04); }
.dark .fetch-error { color: var(--error); }

/* Recently viewed */
/* Row C filmstrip — narrower flex-basis than the shared .scroll-row default (260px is
   sized for entity cards; recent-card is a small tile), reusing .scroll-row's snap+edge-mask. */
.recent-filmstrip > * { flex: 0 0 128px; }
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
/* Same EntityCard pairing: seeded gradient (inline style) + white-watermark glyph on top. */
.recent-placeholder {
  display: flex; align-items: center; justify-content: center;
  background-size: cover; background-position: center;
}
.recent-placeholder-glyph { display: inline-flex; width: 28px; height: 28px; color: rgba(255,255,255,.85); }
.recent-placeholder-glyph :deep(svg) { width: 100%; height: 100%; }
.recent-name { font-size: var(--text-xs); font-weight: var(--weight-semibold); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.3; }
.recent-type { font-size: 10px; color: var(--muted); }
.dark .recent-card { background: var(--bg-alt); border-color: var(--line); }
.dark .recent-card:hover { border-color: rgba(255,255,255,.15); }

/* Reduced motion — ticker interval itself never starts (see onMounted guard in script);
   these rules cover the remaining CSS-driven motion so nothing depends on JS alone. */
@media (prefers-reduced-motion: reduce) {
  .quick-pick:hover { transform: none; }
  .quick-pick:active { transform: none; }
  .quick-pick:hover .quick-pick-icon { transform: none; }
  .recent-card:hover { transform: none; }
  .recent-card:active { transform: none; }
  .grid { animation: none; opacity: 1; transform: none; }
  .search-ticker-word { animation: none; opacity: 1; transform: none; }
  .trending-dot { animation: none; box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0); }
  .trending-chip:hover { transform: none; }
  .trending-chip:active { transform: none; }
}
</style>
