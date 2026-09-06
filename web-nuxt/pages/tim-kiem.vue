<template>
  <div
    class="page"
    data-color-system="tri-region-v1"
    data-page-recipe="search"
    data-material-accent="neutral"
  >
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Tìm kiếm' }]" :json-ld="true" />

    <!-- Hero: masthead + hero-scale input, with one Clay editorial tick. -->
    <section class="catalog-hero cat-search search-hero">
      <span class="dateline-eyebrow">Tìm kiếm · Tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025)</span>
      <h1>{{ pc('hero_title') }}</h1>
      <p class="search-ticker-line" aria-live="off">
        <span class="search-ticker-word" :key="tickerIdx">{{ tickerPhrase }}<span class="search-ticker-q">?</span></span>
      </p>

      <div class="search-row search-row-spaced search-row-hero" :class="{ error: hasError }" role="search" aria-label="Tìm kiếm địa điểm">
        <div class="search-input-wrap" role="combobox" :aria-expanded="showSuggestions" aria-haspopup="listbox" aria-owns="search-suggestions">
          <input ref="heroInputEl" v-model="searchInput" type="search" enterkeyhint="search" :placeholder="inputPlaceholder" aria-label="Tìm kiếm" :aria-invalid="hasError || undefined" :aria-describedby="hasError && !totalSearchResults ? 'search-error-state' : undefined" autocomplete="off" aria-autocomplete="list" :aria-activedescendant="activeSuggestionId" @input="onTypeahead" @keyup.enter="onEnter" @keydown.down.prevent="sugNext" @keydown.up.prevent="sugPrev" @keydown.escape="sugClose" @focus="inputFocused = true" @blur="onInputBlur" />
          <div v-if="sugLoading" class="sug-loading" aria-hidden="true"><span class="spinner spinner-xs"></span></div>
          <Transition name="sug-fade">
            <ul v-if="showSuggestions && suggestions.length" id="search-suggestions" class="search-suggestions" role="listbox" aria-label="Gợi ý tìm kiếm">
              <li v-for="(s, i) in suggestions" :key="s.id" :id="`sug-${s.id}`" role="option" :aria-selected="i === sugIdx" :class="['sug-item', `sug-cat-${TYPE_META[s.type]?.cat || 'place'}`, { active: i === sugIdx }]" @mousedown.prevent="goToSuggestion(s)">
                <span class="sug-icon" aria-hidden="true"><IconLine :name="typeIcon(s.type)" /></span>
                <span class="sug-name" v-html="highlightMatch(s.name)"></span>
                <span v-if="s.place_name" class="sug-place">{{ s.place_name }}</span>
              </li>
              <li id="sug-search-all" class="sug-item sug-all" role="option" :aria-selected="sugIdx === suggestions.length" :class="{ active: sugIdx === suggestions.length }" @mousedown.prevent="doSearch">
                <span class="sug-icon" aria-hidden="true"><IconLine name="search" /></span>
                <span class="sug-all-label">Tìm tất cả „{{ searchInput.trim() }}"</span>
                <IconLine name="arrow-right" class="sug-all-arrow" aria-hidden="true" />
              </li>
            </ul>
          </Transition>
        </div>
        <button type="button" class="btn btn-primary" data-color-role="action-primary" @click="doSearch">Tìm</button>
      </div>
    </section>

    <NuxtErrorBoundary>
      <ClientOnly>
        <LazyAISearchAssist v-if="q" :query="q" color-recipe="tri-region-v1" />
        <template #fallback>
          <div v-if="q" class="ai-loading ai-loading-padded" role="status" aria-label="Đang tải gợi ý AI"><div class="spinner spinner-center"></div></div>
        </template>
      </ClientOnly>
    </NuxtErrorBoundary>

    <p v-if="searchView.hasMalformedUrl.value" class="search-state-notice" role="status">
      {{ searchView.malformedNotice.value }}
    </p>

    <SkeletonGrid v-if="searching" :count="6" />
    <EmptyState
      v-else-if="hasError && !totalSearchResults"
      id="search-error-state"
      title="Lỗi tìm kiếm"
      message="Không thể tìm kiếm lúc này. Vui lòng thử lại."
      tone="error"
      icon-name="alert-triangle"
      color-recipe="tri-region-v1"
      role="alert"
      data-color-role="status-error"
    >
      <template #actions>
        <button type="button" class="btn btn-outline btn-sm" @click="refreshSearch"><IconLine name="repeat" aria-hidden="true" /> Thử lại</button>
      </template>
    </EmptyState>
    <PageState v-else-if="q" :state="searchSurfaceState" :retry="refreshSearch">
      <!-- Địa điểm / sản phẩm -->
      <template v-if="results.length">
        <h2 class="sr-only">Kết quả tìm kiếm cho "{{ q }}"</h2>
        <p class="result-strap" aria-live="polite">
          <span class="result-strap-query">„{{ q }}"</span> — {{ resultStrapLine }}
        </p>
        <MapListSurface
          :results="results"
          :selected-id="searchView.state.value.selectedId"
          :viewport="searchView.state.value.viewport"
          :viewport-pending="searchView.viewportPending.value"
          :map-state="mapNetworkState"
          :panel="searchView.state.value.panel"
          :scroll-key="searchView.state.value.scrollKey"
          @select="searchView.selectResult"
          @viewport-change="searchView.setViewport"
          @search-area="searchView.commitViewport"
          @panel-change="searchView.openPanel"
          @scroll-key-change="searchView.setScrollKey"
        >
          <template #result="{ result }">
            <div class="search-map-entity-card" data-entity-contract="entity-row">
              <EntityCard :entity="result" color-recipe="tri-region-v1" />
              <p class="map-result-row__address">{{ result.attributes?.address || result.place_name || result.place_area || result.area || 'Chưa có địa chỉ chi tiết' }}</p>
              <FreshnessLine
                v-if="result.source_freshness?.updated_at"
                :status="resolveFreshnessStatus(result.source_freshness?.freshness_status)"
                :updated-label="String(result.source_freshness.updated_at)"
              />
            </div>
          </template>
        </MapListSurface>
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
          <LazySmartRecommendations context="search" :query="q" title="Gợi ý tiếp theo" :limit="6" color-recipe="tri-region-v1" />
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
        <EmptyState title="Chưa thấy đúng ý bạn" message="Nhưng biết đâu những gợi ý dưới đây lại hợp — phù sa vẫn còn nhiều thứ để kể." color-recipe="tri-region-v1">
          <template #actions>
            <button
              v-for="action in zeroResultRecoverySteps"
              :key="action.id"
              type="button"
              class="btn btn-outline"
              :data-recovery-action="action.id"
              @click="activateZeroResultRecovery(action)"
            >
              {{ action.label }}
            </button>
          </template>
        </EmptyState>
        <div class="zero-result-curated-wrap" aria-label="Gợi ý tìm kiếm phổ biến">
          <p class="zero-result-curated-label"><IconLine name="sparkles" aria-hidden="true" /> Gợi ý chủ đề phổ biến:</p>
          <div class="scroll-row trending-row">
            <button
              v-for="(chip, i) in trendingChips"
              :key="'zr-' + i"
              type="button"
              class="trending-chip"
              @click="goTrending(chip)"
            >
              <span class="trending-dot" aria-hidden="true"></span>
              <span>{{ chip }}</span>
            </button>
          </div>
        </div>
        <NuxtErrorBoundary>
          <ClientOnly>
            <LazySmartRecommendations context="search" :query="q" title="Có phải bạn muốn tìm…" :limit="6" color-recipe="tri-region-v1" />
          </ClientOnly>
        </NuxtErrorBoundary>
      </template>
    </PageState>

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
          <LazySmartRecommendations context="search" title="Đáng chú ý lúc này" :limit="3" color-recipe="tri-region-v1" />
        </ClientOnly>
      </NuxtErrorBoundary>

      <!-- Row C: Tiếp tục nơi bạn dừng lại — filmstrip, không phải lưới phẳng -->
      <ClientOnly>
        <section v-if="recentItems.length" class="block reveal">
          <div class="section-head sediment-head"><h2>Tiếp tục nơi bạn dừng lại</h2></div>
          <div class="scroll-row recent-filmstrip">
            <NuxtLink v-for="(r, index) in recentItems" :key="r.id" :to="entityPath(r.id)" class="recent-card">
              <span class="recent-image-wrap">
                <NuxtImg v-if="recentImageDescriptor(r).url && isRemoteUrl(recentImageDescriptor(r).url || '')" :src="recentImageDescriptor(r).url || ''" :alt="recentImageDescriptor(r).alt" :aria-describedby="recentDisclosureId(r, index)" class="recent-img" width="56" height="56" sizes="56px" loading="lazy" decoding="async" @error="markRecentImageError(r.id)" />
                <img v-else-if="recentImageDescriptor(r).url" :src="recentImageDescriptor(r).url || ''" :alt="recentImageDescriptor(r).alt" :aria-describedby="recentDisclosureId(r, index)" class="recent-img" width="56" height="56" loading="lazy" decoding="async" @error="markRecentImageError(r.id)" />
                <span v-else class="recent-img recent-placeholder" aria-hidden="true" :style="{ backgroundImage: categoryPlaceholderBg(r.id, TYPE_META[r.type]?.cat) }"><span class="recent-placeholder-glyph" v-html="categoryGlyph(TYPE_META[r.type]?.cat)"></span></span>
                <span class="recent-image-disclosure"><ImageDisclosure :id="recentDisclosureId(r, index)" :descriptor="recentImageDescriptor(r)" presentation="short" /></span>
              </span>
              <span class="recent-name">{{ r.name }}</span>
              <span class="recent-type">{{ TYPE_META[r.type]?.label || r.type }}</span>
            </NuxtLink>
          </div>
        </section>
      </ClientOnly>

      <!-- Row D: Khám phá theo chủ đề — glyph thay emoji, cùng ngôn ngữ với EntityCard -->
      <section class="block reveal">
        <div class="section-head sediment-head"><h2>Bạn đang tò mò điều gì?</h2></div>
        <div class="quick-picks">
          <NuxtLink v-for="qp in quickPicks" :key="qp.to" :to="qp.to" class="quick-pick">
            <span class="quick-pick-icon" :style="{ backgroundImage: categoryPlaceholderBg(qp.to, qp.cat) }">
              <span class="quick-pick-glyph" v-html="categoryGlyph(qp.cat)"></span>
            </span>
            <span class="quick-pick-label">{{ qp.label }}</span>
          </NuxtLink>
        </div>
      </section>

      <!-- declutter-2 B4: Row E "Tìm theo khu vực" đã bỏ — 2 grid quick-picks xếp
           chồng với Row D; intent khu-vực đã có ở footer + /khu-vuc/*. -->
    </template>

    <!-- Cross-links -->
    <section class="block band catalog-cross reveal">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink :to="mapContinuityPath" class="cross-card" no-prefetch>
          <span class="quick-pick-icon cross-glyph-icon" :style="{ backgroundImage: categoryPlaceholderBg('cross-ban-do', 'place') }">
            <span class="quick-pick-glyph" v-html="categoryGlyph('place')"></span>
          </span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/theo-mua" class="cross-card">
          <span class="quick-pick-icon cross-glyph-icon" :style="{ backgroundImage: categoryPlaceholderBg('cross-theo-mua', 'nature') }">
            <span class="quick-pick-glyph" v-html="categoryGlyph('nature')"></span>
          </span>
          <div><strong>Theo mùa</strong><p>Đúng mùa thưởng thức</p></div>
        </NuxtLink>
        <NuxtLink to="/cong-dong" class="cross-card">
          <span class="quick-pick-icon cross-glyph-icon" :style="{ backgroundImage: categoryPlaceholderBg('cross-cong-dong', 'person') }">
            <span class="quick-pick-glyph" v-html="categoryGlyph('person')"></span>
          </span>
          <div><strong>Cộng đồng</strong><p>Hỏi đáp & chia sẻ</p></div>
        </NuxtLink>
        <NuxtLink to="/danh-ba" class="cross-card">
          <span class="quick-pick-icon cross-glyph-icon" :style="{ backgroundImage: categoryPlaceholderBg('cross-danh-ba', 'org') }">
            <span class="quick-pick-glyph" v-html="categoryGlyph('org')"></span>
          </span>
          <div><strong>Danh bạ</strong><p>Hành chính xã/phường</p></div>
        </NuxtLink>
      </div>
    </section>
    <!-- declutter-3 T14 (A3c): JourneyBar page-level — trang thuộc luồng lập-kế-hoạch -->
    <ClientOnly><LazyJourneyBar /></ClientOnly>
  </div>
</template>

<script setup lang="ts">
import { TYPE_META } from '~/composables/useConstants'
import { useJourneyActions } from '~/composables/useJourneyActions'
import type { ZeroResultRecoveryAction } from '~/composables/useUnifiedSearch'
import MapListSurface from '~/components/public/MapListSurface.vue'
import PageState from '~/components/public/PageState.vue'
import { generateCategoryIcon, generateCategoryPlaceholder } from '~/composables/useCategoryPlaceholder'
import type { ImageDescriptor } from '~/types/image'
import type { RecentItem } from '~/composables/useRecentlyViewed'
import { describeEntityPlaceholder } from '~/utils/imageDescriptors'
import { normalizeCoords } from '~/composables/useCoords'
import { viewportTileBounds } from '~/utils/publicStateUrl'
import { resolveFreshnessStatus } from '~/utils/regionalColor'
import { escapeHtml } from '~/utils/safe'
useReveal()
const { f: pc } = usePageContent('tim_kiem')
const { recentItems } = useRecentlyViewed()
const { trackSearch } = useUserEvents()
const { searchAll, fetchEntitySuggestions, zeroResultRecoveryActions } = useUnifiedSearch()
const { searchSuccessActions } = useJourneyActions()
const searchView = useSearchViewState()
const { user, isLoggedIn } = useAuth()
const journeyThread = useJourneyThread({
  ownerScope: () => isLoggedIn.value ? String(user.value?.id || 'authenticated') : 'guest',
})
const journeyOwner = computed(() => isLoggedIn.value ? String(user.value?.id || 'authenticated') : 'guest')
const recentImageErrors = ref<Record<string, boolean>>({})

function snapshotSearchJourney() {
  const returnPath = searchView.url.value
  journeyThread.restore()
  journeyThread.snapshot({ intent: 'explore', returnPath, currentPath: returnPath })
}

if (import.meta.client) watch([searchView.url, journeyOwner], snapshotSearchJourney, { immediate: true })

function recentImageDescriptor(item: RecentItem): ImageDescriptor {
  return recentImageErrors.value[item.id] ? describeEntityPlaceholder(item) : item.image_descriptor
}

function markRecentImageError(id: string) {
  recentImageErrors.value = { ...recentImageErrors.value, [id]: true }
}

function recentDisclosureId(item: { id: string }, index: number): string {
  const token = String(item.id || 'recent').replace(/[^A-Za-z0-9_-]+/g, '-')
  return `recent-search-${token}-${index}`
}

// Same pairing EntityCard uses: glyph (currentColor/white-watermark strokes) is only
// legible over its matching seeded gradient — never drop the glyph on a bare card.
function categoryGlyph(cat?: string) {
  return generateCategoryIcon(cat || 'place')
}
function categoryPlaceholderBg(seedId: string, cat?: string) {
  return generateCategoryPlaceholder(seedId, cat || 'place')
}

// Câu hỏi thật, đặc trưng Vĩnh Long — danh sách tĩnh đã tuyển chọn (không gọi LLM,
// không backend trending — đúng tinh thần §B8: đây là copy trình bày, không phải
// dữ liệu sống). Dùng làm cả ticker hero lẫn placeholder input khi rảnh gõ.
const TICKER_PHRASES = [
  'bún nước lèo ở đâu chuẩn vị Khmer',
  'mùa này bưởi Năm Roi ngọt chưa',
  'ngủ đêm giữa vườn dừa, ở đâu',
  'chợ nổi Trà Ôn còn họp giờ nào',
  'dừa xiêm xứ dừa (Bến Tre cũ) uống tại vườn',
  'đờn ca tài tử nghe ở đâu',
  'cù lao nào yên tĩnh nhất',
]
const tickerIdx = ref(0)
const tickerPhrase = computed(() => TICKER_PHRASES[tickerIdx.value % TICKER_PHRASES.length])
const inputFocused = ref(false)
const inputPlaceholder = computed(() =>
  inputFocused.value || searchInput.value ? 'Tìm đặc sản, trải nghiệm…' : `${tickerPhrase.value}…`
)
const heroInputEl = ref<HTMLInputElement | null>(null)
function onHeroGlobalKey(e: KeyboardEvent) {
  if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName) && !(e.target as HTMLElement)?.isContentEditable) {
    e.preventDefault()
    heroInputEl.value?.focus()
    heroInputEl.value?.select()
  }
}
let tickerTimer: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  if (!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    tickerTimer = setInterval(() => { tickerIdx.value++ }, 4000)
  }
  document.addEventListener('keydown', onHeroGlobalKey)
})
onBeforeUnmount(() => {
  if (tickerTimer) clearInterval(tickerTimer)
  document.removeEventListener('keydown', onHeroGlobalKey)
})

// Row A — "Đang được hỏi nhiều": chip tĩnh dẫn thẳng vào một câu tìm kiếm thật.
const trendingChips = [
  'bún nước lèo',
  'bưởi Năm Roi',
  'homestay vườn dừa',
  'chợ nổi Trà Ôn',
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
const q = computed(() => searchView.state.value.query)
const searchInput = ref(q.value)
const mapNetworkState = ref<'ready' | 'offline'>('ready')
const mapContinuityPath = computed(() => searchView.url.value.replace(/^\/tim-kiem/, '/ban-do'))
const recoveryQueryAliases: Record<string, string> = {
  'gom do': 'gốm đỏ',
  'bun nuoc leo': 'bún nước lèo',
  'buoi nam roi': 'bưởi Năm Roi',
  'dua sap': 'dừa sáp',
  homestay: 'lưu trú miệt vườn',
}
const suggestedRecoveryQuery = computed(() => recoveryQueryAliases[q.value.trim().toLocaleLowerCase('vi-VN')])

const emptySearchData = () => ({ entities: [], posts: [], users: [], totals: { entities: 0, posts: 0, users: 0 } })
type SearchData = Awaited<ReturnType<typeof searchAll>>
type SearchDataCarrier = { readonly key: string; readonly data: SearchData }

const searchAsyncData = useAsyncData<SearchDataCarrier>(
  'search-results',
  async () => {
    const key = q.value
    const value = key ? await searchAll(q.value, 100) : emptySearchData()
    return { key, data: value as SearchData }
  },
  { watch: [q] }
)
const { data, error: searchError, status, refresh } = searchAsyncData
const lastSuccessfulSearchData = ref<SearchDataCarrier | null>(null)
watch(data, (value) => {
  if (value) lastSuccessfulSearchData.value = value
}, { immediate: true })
const currentSearchData = computed(() => data.value?.key === q.value ? data.value.data : null)
const retainedSearchData = computed(() => lastSuccessfulSearchData.value?.key === q.value
  ? lastSuccessfulSearchData.value.data
  : null)
const effectiveSearchData = computed(() => currentSearchData.value || (searchError.value ? retainedSearchData.value : null))
const searching = computed(() => status.value === 'pending' && !!q.value && !effectiveSearchData.value)
const refreshSearch = () => refresh()

const rawResults = computed(() => effectiveSearchData.value?.entities || effectiveSearchData.value?.results || [])
const committedBounds = computed(() => searchView.committedViewport.value ? viewportTileBounds(searchView.committedViewport.value) : undefined)
const results = computed(() => rawResults.value.filter((entity: any) => {
  const bounds = committedBounds.value
  if (!bounds) return true
  const coordinates = normalizeCoords(entity.coordinates || { lat: entity.lat, lng: entity.lng })
  if (!coordinates) return false
  const [lat, lng] = coordinates
  return lng >= bounds.west && lng <= bounds.east && lat >= bounds.south && lat <= bounds.north
}))
const hasError = computed(() => status.value !== 'pending' && !!searchError.value)
const postResults = computed(() => (effectiveSearchData.value?.posts || []).slice(0, 6))
const userResults = computed(() => (effectiveSearchData.value?.users || []).slice(0, 8))
const totalSearchResults = computed(() => results.value.length + postResults.value.length + userResults.value.length)
const searchSurfaceState = computed(() => {
  if (mapNetworkState.value === 'offline' && effectiveSearchData.value) {
    return { kind: 'offline' as const, cached: effectiveSearchData.value }
  }
  if (hasError.value && effectiveSearchData.value) {
    return { kind: 'partial' as const, data: effectiveSearchData.value, failedPanels: ['results'] }
  }
  return { kind: 'ready' as const, data: effectiveSearchData.value || emptySearchData() }
})
const searchNextActions = computed(() => q.value && totalSearchResults.value ? searchSuccessActions(q.value, results.value.length) : [])
const zeroResultRecoverySteps = computed(() => zeroResultRecoveryActions(searchView.state.value, {
  suggestedQuery: suggestedRecoveryQuery.value,
  hasRecentOrSaved: recentItems.value.length > 0,
}))

function activateZeroResultRecovery(action: ZeroResultRecoveryAction) {
  if (action.to) {
    navigateTo(action.to)
    return
  }
  if (action.id === 'remove-filter' && action.patch?.filters) {
    for (const key of Object.keys(searchView.state.value.filters)) {
      if (!(key in action.patch.filters)) searchView.setFilter(key, undefined)
    }
    return
  }
  if (action.id === 'widen-area') {
    searchView.setArea(undefined)
    return
  }
  if (action.patch?.query !== undefined) searchView.setQuery(action.patch.query)
  if (action.patch?.intent) searchView.setIntent(action.patch.intent)
}

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
    navigateTo(searchView.urlForQuery(searchInput.value))
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

function typeIcon(type?: string): string {
  return (type && TYPE_META[type]?.icon) || 'pin'
}

function highlightMatch(name: string): string {
  const q = searchInput.value.trim()
  const safe = escapeHtml(name)
  if (!q) return safe
  const idx = name.toLowerCase().indexOf(q.toLowerCase())
  if (idx === -1) return safe
  const before = escapeHtml(name.slice(0, idx))
  const match = escapeHtml(name.slice(idx, idx + q.length))
  const after = escapeHtml(name.slice(idx + q.length))
  return `${before}<mark class="sug-mark">${match}</mark>${after}`
}

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

function updateNetworkState() {
  mapNetworkState.value = navigator.onLine ? 'ready' : 'offline'
}

onMounted(() => {
  updateNetworkState()
  window.addEventListener('online', updateNetworkState)
  window.addEventListener('offline', updateNetworkState)
})

onBeforeUnmount(() => {
  if (sugTimer) clearTimeout(sugTimer)
  if (blurTimer) clearTimeout(blurTimer)
  sugAbort?.abort()
  window.removeEventListener('online', updateNetworkState)
  window.removeEventListener('offline', updateNetworkState)
})

await searchAsyncData

useSeoMeta({
  title: () => q.value.trim() ? `"${q.value.trim()}" — Tìm kiếm — vinhlong360` : pc('seo_title'),
  description: () => q.value.trim() ? `Kết quả tìm kiếm cho "${q.value.trim()}" trên vinhlong360.` : pc('seo_description'),
  ogTitle: () => q.value.trim() ? `"${q.value.trim()}" — vinhlong360` : pc('og_title'),
  ogDescription: () => pc('og_description'),
  ogUrl: () => canonicalUrl('/tim-kiem'),
  twitterCard: 'summary_large_image',
  robots: () => q.value.trim() ? 'noindex, follow' : 'index, follow',
})
useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/tim-kiem') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: safeJsonLd({
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
.search-row.error input { border-color: var(--error); box-shadow: 0 0 0 3px rgba(var(--color-error-rgb), .12); }

/* Unified search: người dùng + bài viết — secondary strip, smaller than the primary entity grid */
.search-section-secondary { padding-top: var(--space-6); padding-bottom: var(--space-3); }
.search-section-secondary .section-head { margin-bottom: var(--space-4); }
.search-section-secondary .section-head h2 { font-size: var(--text-lg); }
.search-section-secondary .people-list { margin-bottom: var(--space-3); }
.people-list { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.person-chip { display: inline-flex; align-items: center; gap: var(--space-2); padding: var(--space-1) var(--space-3) var(--space-1) var(--space-1); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-full); text-decoration: none; color: var(--ink); transition: border-color .25s var(--ease-out), transform .25s var(--ease-out-expo); }
.person-chip:hover { border-color: var(--color-action); transform: translateY(-1px); }
.person-avatar { width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--color-action); color: var(--color-on-action); font-size: var(--text-xs); font-weight: var(--weight-semibold); }
.person-name { font-size: var(--text-sm); font-weight: var(--weight-medium); }
.person-meta { font-size: var(--text-xs); color: var(--muted); }
.search-post-list { display: flex; flex-direction: column; gap: var(--space-2); }
.search-post-item { display: block; padding: var(--space-3); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-sheet); text-decoration: none; color: var(--ink); transition: border-color .25s var(--ease-out); }
.search-post-item:hover { border-color: var(--color-action); }
.spi-head { display: flex; align-items: center; gap: var(--space-2); margin-bottom: .2rem; }
.spi-head strong { font-size: var(--text-sm); }
.spi-type { font-size: var(--text-xs); color: var(--muted); background: var(--bg-alt); padding: var(--space-half) var(--space-2); border-radius: var(--radius-full); }
.spi-content { font-size: var(--text-sm); color: var(--ink-700); margin: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

.quick-picks { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: var(--space-3); }
.quick-pick { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); padding: var(--space-4); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-sheet); text-align: center; box-shadow: var(--shadow-xs); transition: transform .35s var(--ease-out-expo), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out); }
.quick-pick:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--color-action); background: var(--color-action-surface); }
.quick-pick:active { transform: scale(.97); transition-duration: .08s; }
.quick-pick:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 3px; }
/* Glyph swap: same pairing EntityCard uses — seeded gradient swatch (generateCategoryPlaceholder)
   behind the white-watermark glyph (generateCategoryIcon), never the bare glyph alone (its fills
   are translucent-white, illegible without the saturated backdrop). Small size, rounded tile. */
.quick-pick-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 44px; height: 44px; border-radius: var(--radius-surface);
  background-size: cover; background-position: center;
  transition: transform .35s var(--ease-out-expo);
}
.quick-pick-glyph { display: inline-flex; width: 24px; height: 24px; color: rgba(var(--white-rgb),.85); }
.quick-pick-glyph :deep(svg) { width: 100%; height: 100%; }
.quick-pick:hover .quick-pick-icon { transform: scale(1.1); }
.quick-pick-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--ink); }

/* Cross-link band ("Khám phá thêm"): reuses the .quick-pick-icon/.quick-pick-glyph pairing
   above instead of catalog.css's bare .cross-icon emoji (anti-slop tell — designed chip,
   not a loose glyph next to serif). .cross-card itself stays untouched (shared catalog.css). */
.cross-glyph-icon { flex-shrink: 0; }
.cross-card:hover .cross-glyph-icon { transform: scale(1.1); }
@media (prefers-reduced-motion: reduce) {
  .cross-card:hover .cross-glyph-icon { transform: none; }
}

/* Autocomplete suggestions */
.search-input-wrap { position: relative; flex: 1; min-width: 0; }
.search-suggestions {
  position: absolute; top: 100%; left: 0; right: 0; z-index: var(--z-dropdown);
  margin: var(--space-1) 0 0; padding: var(--space-1); list-style: none;
  background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-sheet); box-shadow: var(--shadow-lg);
  max-height: 320px; overflow-y: auto;
}
.sug-item {
  display: flex; align-items: center; gap: var(--space-2);
  min-height: 44px;
  padding: var(--space-2) var(--space-3); border-radius: var(--radius-surface);
  cursor: pointer; font-size: var(--text-sm); color: var(--ink);
  border-left: 3px solid transparent;
  transition: background .2s var(--ease-out), border-color .2s var(--ease-out);
}
.sug-item:hover, .sug-item.active { background: var(--bg-alt); }
/* Keyboard selection stays explicit in structure and gains one restrained Clay marker. */
.sug-item[aria-selected="true"] { border-left-color: var(--color-material-clay); background: var(--color-brand-surface); }
.sug-icon {
  display: inline-flex; align-items: center; justify-content: center;
  font-size: var(--text-base); color: var(--muted); flex-shrink: 0;
  transition: color .2s var(--ease-out);
}
.sug-item:hover .sug-icon, .sug-item.active .sug-icon, .sug-item[aria-selected="true"] .sug-icon {
  color: var(--color-action);
}
.sug-name { font-weight: var(--weight-medium); flex: 1; min-width: 0; }
:deep(.sug-mark) {
  background: var(--color-action-surface, var(--color-brand-surface));
  color: var(--color-action);
  font-weight: var(--weight-bold);
  border-radius: var(--radius-control);
  padding: 0 var(--space-half);
}
.sug-place { color: var(--muted); font-size: var(--text-xs); margin-left: auto; flex-shrink: 0; }
.sug-all {
  color: var(--color-action); font-weight: var(--weight-semibold);
  border-top: .5px solid var(--line); margin-top: var(--space-1); padding-top: var(--space-2);
  display: flex; align-items: center; gap: var(--space-2);
}
.sug-all-label { flex: 1; min-width: 0; }
.sug-all-arrow {
  flex-shrink: 0; margin-left: auto;
  transition: transform .25s var(--ease-out-expo);
}
.sug-all:hover .sug-all-arrow, .sug-all.active .sug-all-arrow, .sug-all[aria-selected="true"] .sug-all-arrow {
  transform: translateX(3px);
}
.sug-fade-enter-active { transition: opacity .15s, transform .15s; }
.sug-fade-leave-active { transition: opacity .1s; }
.sug-fade-enter-from { opacity: 0; transform: translateY(-4px); }
.sug-fade-leave-to { opacity: 0; }
.dark .search-suggestions { background: var(--card); border-color: rgba(var(--white-rgb),.1); }
.dark .sug-item:hover, .dark .sug-item.active { background: rgba(var(--white-rgb),.06); }
@media (prefers-reduced-motion: reduce) {
  .sug-all-arrow,
  .sug-all:hover .sug-all-arrow,
  .sug-all.active .sug-all-arrow,
  .sug-all[aria-selected="true"] .sug-all-arrow { transform: none; }
}

/* Search input polish */
.search-row-spaced input {
  transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo);
}
.search-row-spaced input:focus-visible {
  border-color: var(--color-focus);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-focus) 12%, transparent);
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

/* Hero-scale input: oversized, sits on a hairline underline (not a boxed input), with a
   single Clay editorial tick at the left edge. */
.search-row-hero {
  position: relative;
  padding-left: var(--space-4);
  max-width: 640px;
}
.search-row-hero::before {
  content: "";
  position: absolute; left: 0; top: 6px; bottom: 6px;
  width: 2px; border-radius: var(--radius-full);
  background: var(--color-material-clay);
}
.search-row-hero .search-input-wrap input {
  width: 100%;
  min-width: 0;
  font-size: var(--text-2xl);
  font-style: normal;
  padding: var(--space-2) 0;
  background: transparent;
  border: none;
  border-bottom: 1.5px solid var(--line);
  border-radius: 0;
  box-shadow: none;
}
.search-row-hero .search-input-wrap input::placeholder {
  font-style: italic;
  color: var(--muted);
  opacity: .75;
}
.search-row-hero .search-input-wrap input:focus-visible {
  border-bottom-color: var(--color-focus);
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
  transition: border-color .25s var(--ease-out), transform .25s var(--ease-out-expo), background .25s var(--ease-out);
}
.trending-chip:hover { border-color: var(--color-action); transform: translateY(-1px); background: var(--color-action-surface); }
.trending-chip:active { transform: scale(.97); transition-duration: .08s; }
.trending-chip:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.trending-row > * { flex: 0 0 auto; }
/* "Hot right now" dot — reuses the same restrained pulse token as EntityCard's peak-dot,
   settles after one breathing cycle rather than looping forever (motion-budget discipline). */
.trending-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--color-material-neutral);
  box-shadow: 0 0 0 0 color-mix(in srgb, var(--color-material-neutral) 50%, transparent);
  animation: trendingPulse 2.4s var(--ease-out) 1;
}
@keyframes trendingPulse {
  0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--color-material-neutral) 50%, transparent); }
  70% { box-shadow: 0 0 0 6px transparent; }
  100% { box-shadow: 0 0 0 0 transparent; }
}
.dark .trending-chip { background: var(--bg-alt); border-color: var(--line); }
.dark .trending-chip:hover { border-color: var(--color-action); background: var(--color-action-surface); }

/* Curated recovery chips in zero-result state */
.zero-result-curated-wrap {
  margin-top: var(--space-4);
  margin-bottom: var(--space-4);
  padding: var(--space-4);
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius-surface);
}
.zero-result-curated-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--muted);
}
.zero-result-curated-label :deep(svg) {
  width: 16px;
  height: 16px;
  color: var(--color-action);
}
.dark .zero-result-curated-wrap {
  background: var(--bg-alt);
  border-color: var(--line);
}

/* Grid results stagger */
.grid { animation: fadeInGrid .4s var(--ease-out) both; }
@keyframes fadeInGrid { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }

/* Dark mode */
.dark .quick-pick { background: var(--bg-alt); border-color: var(--line); }
.dark .quick-pick:hover { border-color: var(--color-action); box-shadow: var(--shadow-md); background: var(--color-action-surface); }

/* Recently viewed */
/* Row C filmstrip — narrower flex-basis than the shared .scroll-row default (260px is
   sized for entity cards; recent-card is a small tile), reusing .scroll-row's snap+edge-mask. */
.recent-filmstrip > * { flex: 0 0 128px; }
.recent-card {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-3); background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-sheet); text-decoration: none; color: var(--ink); text-align: center;
  transition: transform .3s var(--ease-out-expo), box-shadow .3s var(--ease-out), border-color .3s;
}
.recent-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--color-action); }
.recent-card:active { transform: scale(.97); transition-duration: .08s; }
.recent-card:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 3px; }
.recent-img {
  width: 56px; height: 56px; border-radius: var(--radius-surface); object-fit: cover;
}
.recent-image-wrap { position: relative; display: block; width: 56px; height: 56px; }
.recent-image-disclosure { position: absolute; inset: auto 1px 1px; display: flex; justify-content: flex-end; }
.recent-image-disclosure :deep([data-image-disclosure]) { font-size: var(--text-2xs, 11px); padding: var(--space-half) var(--space-1); }
/* Same EntityCard pairing: seeded gradient (inline style) + white-watermark glyph on top. */
.recent-placeholder {
  display: flex; align-items: center; justify-content: center;
  background-size: cover; background-position: center;
}
.recent-placeholder-glyph { display: inline-flex; width: 28px; height: 28px; color: rgba(var(--white-rgb),.85); }
.recent-placeholder-glyph :deep(svg) { width: 100%; height: 100%; }
.recent-name { font-size: var(--text-xs); font-weight: var(--weight-semibold); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.3; }
.recent-type { font-size: var(--text-xs, 12px); color: var(--muted); }
.dark .recent-card { background: var(--bg-alt); border-color: var(--line); }
.dark .recent-card:hover { border-color: var(--color-action); background: var(--color-action-surface); }

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
  .trending-dot { animation: none; box-shadow: none; }
  .trending-chip:hover { transform: none; }
  .trending-chip:active { transform: none; }
}
</style>
