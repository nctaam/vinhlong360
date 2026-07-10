<template>
  <section class="page saved-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Đã lưu' }]" />

    <div v-if="!isLoggedIn" class="saved-guest card">
      <h1>Đã lưu</h1>
      <p>Đăng nhập để xem nội dung đã lưu.</p>
      <button type="button" class="btn btn-primary" @click="openAuth()">Đăng nhập</button>
    </div>

    <template v-else>
      <header class="saved-header">
        <div>
          <p class="saved-kicker">Kho cá nhân</p>
          <h1 class="saved-title">Đã lưu</h1>
        </div>
        <button type="button" class="btn btn-ghost btn-sm" :disabled="activeLoading" @click="refreshCurrentTab">
          {{ activeLoading ? 'Đang đồng bộ...' : 'Đồng bộ' }}
        </button>
      </header>

      <section class="saved-overview" aria-label="Tổng quan đã lưu">
        <div class="saved-overview-item">
          <span>Tổng mục</span>
          <strong>{{ totalSaved }}</strong>
        </div>
        <div class="saved-overview-item">
          <span>Đang xem</span>
          <strong>{{ activeTabMeta.label }}</strong>
        </div>
        <div class="saved-overview-item">
          <span>Kết quả</span>
          <strong>{{ visibleCount }}</strong>
        </div>
      </section>

      <!-- declutter-2 A7: rail chỉ hiện ở EMPTY-state (builder khi trống trả
           "Tìm điểm để lưu"/"Mở bộ lập lịch trình" — đúng vai onboarding); khi đã có
           mục lưu, danh sách chính là nội dung, rail always-on là nhiễu. -->
      <JourneyActionRail
        v-if="totalSaved === 0 && savedJourneyActions.length"
        :actions="savedJourneyActions"
        title="Việc nên làm tiếp"
        compact
        aria-label="Gợi ý hành động cho mục đã lưu"
      />

      <div class="saved-tools">
        <label class="saved-search">
          <span class="sr-only">Tìm trong mục đã lưu</span>
          <input v-model.trim="savedQuery" type="search" placeholder="Tìm trong mục đã lưu" autocomplete="off" />
        </label>
        <NuxtLink :to="savedMapLink" class="btn btn-secondary btn-sm">Mở bản đồ</NuxtLink>
      </div>

      <!-- Tabs -->
      <div class="saved-tabs" role="tablist" aria-label="Mục đã lưu" aria-orientation="horizontal" @keydown="onSavedTabKeydown">
        <button v-for="t in tabs" :key="t.key" type="button" role="tab"
                :id="`saved-tab-${t.key}`"
                :class="['saved-tab', { active: tab === t.key }]"
                :aria-selected="tab === t.key"
                :aria-controls="`saved-panel-${t.key}`"
                :tabindex="tab === t.key ? 0 : -1"
                @click="setSavedTab(t.key)">
          {{ t.label }}
          <span v-if="t.count != null" class="saved-tab-count">{{ t.count }}</span>
        </button>
      </div>

      <!-- Saved entities -->
      <div v-if="tab === 'entities'" id="saved-panel-entities" class="saved-panel" role="tabpanel" aria-labelledby="saved-tab-entities">
        <div v-if="entitiesError && !entitiesLoading" class="saved-inline-warning" role="status">
          Không thể đồng bộ từ hệ thống, đang hiển thị dữ liệu khả dụng trên thiết bị này.
        </div>
        <div v-if="entitiesLoading" class="saved-skeletons">
          <div v-for="i in 4" :key="i" class="skeleton-box saved-card-skel"></div>
        </div>
        <div v-else-if="filteredEntities.length" class="saved-grid">
          <SavedEntityCard v-for="item in filteredEntities" :key="item.id" :item="item">
            <template #action>
              <button type="button" class="saved-remove" aria-label="Bỏ lưu" @click="removeEntity(item.id)">✕</button>
            </template>
          </SavedEntityCard>
        </div>
        <div v-else class="saved-empty">
          <p>{{ savedQuery ? 'Không tìm thấy địa điểm phù hợp trong mục đã lưu.' : 'Chưa lưu địa điểm nào. Khi duyệt các trang địa điểm, nhấn nút lưu để thêm vào đây.' }}</p>
          <NuxtLink :to="savedQuery ? searchLink : '/dia-diem'" class="btn btn-ghost btn-sm">{{ savedQuery ? 'Tìm trên hệ thống' : 'Khám phá địa điểm' }}</NuxtLink>
        </div>
      </div>

      <!-- Bookmarked posts -->
      <div v-if="tab === 'posts'" id="saved-panel-posts" class="saved-panel" role="tabpanel" aria-labelledby="saved-tab-posts">
        <div v-if="postsError && !postsLoading" class="saved-inline-warning" role="status">
          Chưa thể tải bookmark bài viết. Bạn có thể thử đồng bộ lại.
        </div>
        <div v-if="postsLoading" class="saved-skeletons">
          <div v-for="i in 4" :key="i" class="skeleton-box saved-card-skel"></div>
        </div>
        <div v-else-if="filteredPosts.length" class="saved-posts-list">
          <div v-for="post in filteredPosts" :key="post.id" class="saved-post card">
            <NuxtLink :to="postPath(post.id)" class="saved-post-link">
              <span class="saved-post-title">{{ post.content?.slice(0, 100) || 'Bài viết' }}{{ post.content?.length > 100 ? '…' : '' }}</span>
              <span class="saved-post-meta">
                {{ post.author_name || 'Người dùng' }} · {{ timeAgo(post.bookmarked_at || post.created_at) }}
              </span>
            </NuxtLink>
            <button type="button" class="saved-remove" aria-label="Bỏ lưu" @click="removeBookmark(post.id)">✕</button>
          </div>
        </div>
        <div v-else class="saved-empty">
          <p>{{ savedQuery ? 'Không tìm thấy bài viết phù hợp trong bookmark.' : 'Chưa bookmark bài viết nào.' }}</p>
          <NuxtLink to="/cong-dong" class="btn btn-ghost btn-sm">Xem bài viết cộng đồng</NuxtLink>
        </div>
        <button v-if="!savedQuery && postsHasMore && bookmarkedPosts.length" type="button" class="btn btn-secondary saved-load-more" @click="loadMorePosts">
          Xem thêm
        </button>
      </div>

      <!-- Itineraries -->
      <div v-if="tab === 'itineraries'" id="saved-panel-itineraries" class="saved-panel" role="tabpanel" aria-labelledby="saved-tab-itineraries">
        <div v-if="itinerariesError && !itinerariesLoading" class="saved-inline-warning" role="status">
          Chưa thể tải lịch trình. Bạn có thể thử đồng bộ lại.
        </div>
        <div v-if="itinerariesLoading" class="saved-skeletons">
          <div v-for="i in 3" :key="i" class="skeleton-box saved-card-skel"></div>
        </div>
        <div v-else-if="filteredItineraries.length" class="saved-posts-list">
          <div v-for="plan in filteredItineraries" :key="plan.id" class="saved-post card">
            <NuxtLink :to="itineraryPath(plan.id)" class="saved-post-link">
              <span class="saved-post-title">{{ plan.title || `Lịch trình ${plan.days || ''}` }}</span>
              <span class="saved-post-meta">{{ timeAgo(plan.savedAt || plan.created_at) }}</span>
            </NuxtLink>
            <button type="button" class="saved-remove" aria-label="Xóa lịch trình" @click="removeItinerary(plan.id)">✕</button>
          </div>
        </div>
        <div v-else class="saved-empty">
          <p>{{ savedQuery ? 'Không tìm thấy lịch trình phù hợp.' : 'Chưa có lịch trình nào.' }}</p>
          <NuxtLink to="/lich-trinh" class="btn btn-ghost btn-sm">Tạo lịch trình mới</NuxtLink>
        </div>
      </div>
      <NuxtErrorBoundary>
        <ClientOnly>
          <LazySmartRecommendations context="saved" title="Gợi ý thêm cho chuyến đi" :limit="6" />
        </ClientOnly>
      </NuxtErrorBoundary>
    </template>
  </section>
</template>

<script setup lang="ts">
import { useJourneyActions } from '~/composables/useJourneyActions'

const { isLoggedIn, authHeaders, handleSessionExpired } = useAuth()
const { openAuth } = useAuthModal()
const { timeAgo } = useTimeAgo()
const { favorites, remove: removeFavoriteLocal } = useFavorites()
const { show: showToast } = useToast()
const { trackSave } = useUserEvents()
const { savedWorkspaceActions } = useJourneyActions()
const route = useRoute()
const router = useRouter()

useHead({
  title: 'Đã lưu',
  meta: [{ name: 'robots', content: 'noindex,nofollow' }],
  link: [{ rel: 'canonical', href: canonicalUrl('/da-luu') }],
})

type SavedTab = 'entities' | 'posts' | 'itineraries'

function firstQueryValue(value: unknown) {
  return Array.isArray(value) ? String(value[0] || '') : String(value || '')
}

function normalizeSavedTab(value: unknown): SavedTab {
  const text = firstQueryValue(value)
  return text === 'posts' || text === 'itineraries' ? text : 'entities'
}

const tab = ref<SavedTab>(normalizeSavedTab(route.query.tab))
const savedQuery = ref(firstQueryValue(route.query.q))
const entitiesLoading = ref(true)
const entitiesError = ref(false)
const savedEntities = ref<any[]>([])
const postsLoading = ref(false)
const postsError = ref(false)
const postsLoaded = ref(false)
const bookmarkedPosts = ref<any[]>([])
const postsPage = ref(1)
const postsHasMore = ref(false)
const itinerariesLoading = ref(false)
const itinerariesError = ref(false)
const itinerariesLoaded = ref(false)
const itineraries = ref<any[]>([])

const tabs = computed(() => [
  { key: 'entities' as const, label: 'Địa điểm', count: savedEntities.value.length || favorites.value.length || null },
  { key: 'posts' as const, label: 'Bài viết', count: bookmarkedPosts.value.length || null },
  { key: 'itineraries' as const, label: 'Lịch trình', count: itineraries.value.length || null },
])
const activeTabMeta = computed(() => tabs.value.find(t => t.key === tab.value) || { key: 'entities' as const, label: 'Địa điểm', count: null })
const totalSaved = computed(() => savedEntities.value.length + bookmarkedPosts.value.length + itineraries.value.length)
const activeLoading = computed(() => {
  if (tab.value === 'entities') return entitiesLoading.value
  if (tab.value === 'posts') return postsLoading.value
  return itinerariesLoading.value
})
const normalizedQuery = computed(() => savedQuery.value.trim().toLocaleLowerCase('vi-VN'))
const searchLink = computed(() => `/tim-kiem?q=${encodeURIComponent(savedQuery.value.trim())}`)
const savedMapLink = computed(() => {
  const q = savedQuery.value.trim()
  return q ? `/ban-do?source=saved&q=${encodeURIComponent(q)}` : '/ban-do?source=saved'
})

function setSavedTab(next: SavedTab) {
  tab.value = next
}

function syncSavedRoute() {
  if (!import.meta.client) return
  const nextQuery = { ...route.query }
  if (tab.value === 'entities') delete nextQuery.tab
  else nextQuery.tab = tab.value
  const q = savedQuery.value.trim()
  if (q) nextQuery.q = q
  else delete nextQuery.q
  const sameTab = firstQueryValue(route.query.tab) === firstQueryValue(nextQuery.tab)
  const sameQ = firstQueryValue(route.query.q) === firstQueryValue(nextQuery.q)
  if (sameTab && sameQ) return
  router.replace({ query: nextQuery }).catch(() => {})
}

watch(() => [route.query.tab, route.query.q], ([tabQuery, qQuery]) => {
  const nextTab = normalizeSavedTab(tabQuery)
  const nextQ = firstQueryValue(qQuery)
  if (nextTab !== tab.value) tab.value = nextTab
  if (nextQ !== savedQuery.value) savedQuery.value = nextQ
})

watch([tab, savedQuery], syncSavedRoute)

function resetSavedRemoteData() {
  savedEntities.value = []
  bookmarkedPosts.value = []
  itineraries.value = []
  postsLoaded.value = false
  itinerariesLoaded.value = false
  postsHasMore.value = false
  postsPage.value = 1
  entitiesLoading.value = false
  postsLoading.value = false
  itinerariesLoading.value = false
  entitiesError.value = false
  postsError.value = false
  itinerariesError.value = false
}

function matchesSavedQuery(parts: Array<unknown>) {
  const q = normalizedQuery.value
  if (!q) return true
  return parts.some(part => String(part || '').toLocaleLowerCase('vi-VN').includes(q))
}

const filteredEntities = computed(() => savedEntities.value.filter(item => matchesSavedQuery([
  item.name, item.type, item.place_name, item.place_area, item.summary,
])))
const filteredPosts = computed(() => bookmarkedPosts.value.filter(post => matchesSavedQuery([
  post.content, post.author_name, post.display_name,
])))
const filteredItineraries = computed(() => itineraries.value.filter(plan => matchesSavedQuery([
  plan.title, plan.days, plan.summary,
])))
const visibleCount = computed(() => {
  if (tab.value === 'entities') return filteredEntities.value.length
  if (tab.value === 'posts') return filteredPosts.value.length
  return filteredItineraries.value.length
})
const savedJourneyActions = computed(() => savedWorkspaceActions({
  entityCount: savedEntities.value.length || favorites.value.length,
  itineraryCount: itineraries.value.length,
  query: savedQuery.value,
  activeTab: tab.value,
}))

onMounted(async () => {
  if (!isLoggedIn.value) return
  await loadEntities()
})

watch(isLoggedIn, async (loggedIn) => {
  if (!loggedIn) {
    resetSavedRemoteData()
    return
  }
  await loadEntities()
})

watch(tab, (t) => {
  if (t === 'posts' && !postsLoaded.value && !postsLoading.value) loadPosts()
  if (t === 'itineraries' && !itinerariesLoaded.value && !itinerariesLoading.value) loadItineraries()
})

function onSavedTabKeydown(e: KeyboardEvent) {
  const keys = ['ArrowRight', 'ArrowLeft', 'Home', 'End']
  if (!keys.includes(e.key)) return
  e.preventDefault()
  const current = tabs.value.findIndex(t => t.key === tab.value)
  const nextIndex = e.key === 'Home'
    ? 0
    : e.key === 'End'
      ? tabs.value.length - 1
      : e.key === 'ArrowRight'
        ? (current + 1) % tabs.value.length
        : (current - 1 + tabs.value.length) % tabs.value.length
  const nextKey = tabs.value[nextIndex]!.key
  tab.value = nextKey
  nextTick(() => document.getElementById(`saved-tab-${nextKey}`)?.focus())
}

async function refreshCurrentTab() {
  if (tab.value === 'entities') await loadEntities()
  else if (tab.value === 'posts') await loadPosts()
  else await loadItineraries()
}

async function loadEntities() {
  entitiesLoading.value = true
  entitiesError.value = false
  try {
    const res = await $fetch<{ items: any[] }>('/api/saved', { headers: authHeaders() })
    savedEntities.value = res.items || []
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    entitiesError.value = true
  } finally {
    if (!savedEntities.value.length && favorites.value.length) {
      savedEntities.value = favorites.value
    }
    entitiesLoading.value = false
  }
}

async function loadPosts() {
  postsLoading.value = true
  postsError.value = false
  try {
    const params = new URLSearchParams({ page: '1', limit: '20' })
    const res = await $fetch<{ items: any[]; total: number }>(`/api/me/bookmarks?${params}`, { headers: authHeaders() })
    bookmarkedPosts.value = res.items || []
    postsHasMore.value = (res.total || 0) > bookmarkedPosts.value.length
    postsPage.value = 1
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    postsError.value = true
  } finally {
    postsLoaded.value = true
    postsLoading.value = false
  }
}

async function loadMorePosts() {
  postsPage.value++
  postsLoading.value = true
  try {
    const params = new URLSearchParams({ page: String(postsPage.value), limit: '20' })
    const res = await $fetch<{ items: any[]; total: number }>(`/api/me/bookmarks?${params}`, { headers: authHeaders() })
    const existing = new Set(bookmarkedPosts.value.map(post => String(post.id || '')))
    bookmarkedPosts.value.push(...(res.items || []).filter(post => !existing.has(String(post.id || ''))))
    postsHasMore.value = (res.total || 0) > bookmarkedPosts.value.length
  } catch (e: unknown) {
    postsPage.value--
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    postsError.value = true
  } finally {
    postsLoading.value = false
  }
}

async function loadItineraries() {
  itinerariesLoading.value = true
  itinerariesError.value = false
  try {
    const res = await $fetch<{ plans: any[] }>('/api/my-plans', { headers: authHeaders() })
    itineraries.value = res.plans || []
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    itinerariesError.value = true
  } finally {
    itinerariesLoaded.value = true
    itinerariesLoading.value = false
  }
}

function removeEntity(id: string) {
  const removed = savedEntities.value.find(e => e.id === id)
  savedEntities.value = savedEntities.value.filter(e => e.id !== id)
  removeFavoriteLocal(id)
  if (removed) trackSave(removed, false, 'saved')
  showToast('Đã bỏ lưu địa điểm', 'success')
}

async function removeBookmark(postId: string) {
  const prev = [...bookmarkedPosts.value]
  bookmarkedPosts.value = bookmarkedPosts.value.filter(p => p.id !== postId)
  try {
    await $fetch(`/api/posts/${encodePathId(postId)}/bookmark`, { method: 'DELETE', headers: authHeaders() })
    showToast('Đã bỏ lưu bài viết', 'success')
  } catch (e: unknown) {
    bookmarkedPosts.value = prev
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể bỏ lưu bài viết', 'error')
  }
}

async function removeItinerary(planId: string) {
  const prev = [...itineraries.value]
  itineraries.value = itineraries.value.filter(p => p.id !== planId)
  try {
    await $fetch(`/api/my-plans/${encodePathId(planId)}`, { method: 'DELETE', headers: authHeaders() })
    showToast('Đã xóa lịch trình', 'success')
  } catch (e: unknown) {
    itineraries.value = prev
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể xóa lịch trình', 'error')
  }
}
</script>

<style scoped>
.saved-page { max-width: 920px; margin: 0 auto; }
.saved-guest { padding: 2rem; text-align: center; }
.saved-guest h1 { margin: 0 0 1rem; font-size: 1.5rem; }
.saved-guest p { color: var(--ink-700); margin-bottom: 1rem; }
.saved-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1rem; }
.saved-kicker { margin: 0 0 .2rem; color: var(--ink-700); font-size: .8rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.saved-title { font-size: 1.5rem; margin: 0; }
.saved-overview {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .75rem; margin-bottom: 1rem;
}
.saved-overview-item {
  min-height: 88px; padding: .85rem 1rem; border: 1px solid var(--line);
  border-radius: var(--radius-lg); background: var(--card); display: flex; flex-direction: column; justify-content: space-between;
}
.saved-overview-item span { color: var(--ink-700); font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.saved-overview-item strong { font-size: 1.25rem; line-height: 1.1; }
.saved-tools { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: .75rem; align-items: center; margin-bottom: 1rem; }
.saved-search input {
  width: 100%; min-height: 44px; padding: .65rem .85rem; border: 1px solid var(--border-input);
  border-radius: var(--radius-md); background: var(--card); color: var(--ink); font: inherit;
}
.saved-search input:focus-visible { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .12); }

/* Tabs */
.saved-tabs {
  display: flex; gap: .25rem; margin-bottom: 1.25rem;
  border-bottom: 2px solid var(--line); padding-bottom: 0;
  overflow-x: auto; -webkit-overflow-scrolling: touch;
}
.saved-tab {
  padding: .5rem 1rem; background: none; border: none; cursor: pointer;
  font-weight: 500; font-size: .9rem; color: var(--ink-700);
  border-bottom: 2px solid transparent; margin-bottom: -2px;
  transition: color .15s, border-color .15s;
}
.saved-tab:hover { color: var(--ink); }
.saved-tab:focus-visible { outline: 2px solid var(--primary); outline-offset: -2px; border-radius: 4px; }
.saved-tab.active { color: var(--primary); border-bottom-color: var(--primary); font-weight: 600; }
.saved-tab-count {
  display: inline-block; margin-left: .35rem;
  background: var(--bg-alt); padding: 0 5px; border-radius: var(--radius-full);
  font-size: .75rem; font-weight: 600; color: var(--ink-700);
}
.saved-tab.active .saved-tab-count { background: var(--primary-light); color: var(--primary); }

/* Entity grid — rows use the shared <SavedEntityCard> for the Story-Card
   treatment (serif title, dateline eyebrow, tri-province card-rule, grain
   overlay); this page just supplies the remove-button action + grid layout. */
.saved-grid { display: flex; flex-direction: column; gap: .5rem; }
.saved-remove {
  flex-shrink: 0; width: 28px; height: 28px; border: none; background: none;
  color: var(--ink-700); cursor: pointer; font-size: .85rem;
  border-radius: var(--radius-full); transition: background .15s;
}
.saved-remove:hover { background: var(--bg-alt); color: var(--error); }

/* Posts list */
.saved-posts-list { display: flex; flex-direction: column; gap: .5rem; }
.saved-post { padding: .75rem 1rem; display: flex; align-items: center; gap: .5rem; }
.saved-post-link { text-decoration: none; color: var(--ink); display: block; flex: 1; min-width: 0; }
.saved-post-title { display: block; font-weight: 500; font-size: .92rem; line-height: 1.4; }
.saved-post-meta { display: block; font-size: .78rem; color: var(--ink-700); margin-top: .2rem; }
.saved-load-more { margin-top: .75rem; width: 100%; }
.saved-inline-warning {
  margin-bottom: .75rem; padding: .65rem .75rem; border-radius: var(--radius-md);
  background: color-mix(in oklab, var(--accent-container) 72%, var(--card));
  color: var(--ink-700); font-size: .85rem; line-height: 1.4;
}

/* Skeletons & empty */
.saved-skeletons { display: flex; flex-direction: column; gap: .5rem; }
.saved-card-skel { height: 64px; border-radius: var(--radius-md); }
.saved-empty { color: var(--ink-700); font-size: .9rem; text-align: center; padding: 2rem 1rem; display: flex; flex-direction: column; align-items: center; gap: .75rem; }
.saved-empty p { margin: 0; }

/* Dark */
.dark .saved-overview-item, .dark .saved-search input { background: var(--bg-alt); border-color: var(--line); }
.dark .saved-post { background: var(--bg-alt); }

/* Mobile */
@media (max-width: 600px) {
  .saved-page { padding: var(--space-4) var(--space-3); }
  .saved-header { flex-direction: column; }
  .saved-header .btn { width: 100%; justify-content: center; }
  .saved-overview { grid-template-columns: 1fr; }
  .saved-tools { grid-template-columns: 1fr; }
  .saved-tools .btn { width: 100%; justify-content: center; }
  .saved-tab { padding: .5rem .6rem; font-size: .82rem; }
}
</style>
