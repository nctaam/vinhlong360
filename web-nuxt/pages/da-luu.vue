<template>
  <section class="page saved-page" data-color-system="tri-region-v1">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Đã lưu' }]" :json-ld="true" />

    <div v-if="!isLoggedIn" class="saved-guest">
      <EmptyState
        icon-name="bookmark"
        title="Đã lưu — Kho hành trình cá nhân"
        message="Đăng nhập để đồng bộ và xem danh sách địa điểm, bài viết và lịch trình bạn đã lưu giữ trên mọi thiết bị."
        color-recipe="tri-region-v1"
        :heading-level="1"
      >
        <template #actions>
          <button type="button" class="btn btn-primary" @click="openAuth()">Đăng nhập</button>
        </template>
      </EmptyState>
    </div>

    <template v-else>
      <header class="saved-header">
        <div>
          <p class="saved-kicker dateline-eyebrow">Kho cá nhân</p>
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
          <input v-model.trim="savedQuery" type="search" placeholder="Tìm trong mục đã lưu" aria-label="Tìm trong mục đã lưu" autocomplete="off" />
        </label>
        <NuxtLink :to="savedMapLink" class="btn btn-secondary btn-sm">Mở bản đồ</NuxtLink>
        <p class="sr-only" role="status" aria-live="polite">
          Hiển thị {{ visibleCount }} mục {{ activeTabMeta.label.toLowerCase() }}
        </p>
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
              <button
                type="button"
                class="saved-remove"
                :aria-label="`Bỏ lưu địa điểm ${item.name || ''}`"
                @click="removeEntity(item.id)"
              >
                <IconLine name="x" />
              </button>
            </template>
          </SavedEntityCard>
        </div>
        <div v-else :class="['saved-empty', { 'saved-empty-catalyst': !savedQuery }]">
          <div v-if="!savedQuery" class="saved-catalyst-box">
            <span class="saved-catalyst-icon" aria-hidden="true"><IconLine name="bookmark" /></span>
            <h3 class="saved-catalyst-title">Hành trình sông nước của bạn chưa được đánh dấu</h3>
            <p class="saved-catalyst-desc">Khi dạo quanh các cẩm nang, bấm biểu tượng trái tim để lưu lại những điểm đến, làng nghề và quán ngon bạn muốn ghé thăm.</p>
            
            <div class="saved-suggestions-block">
              <span class="saved-suggestions-title">Gợi ý khám phá khởi đầu Tam giác Phù sa:</span>
              <div class="saved-suggestions-grid">
                <NuxtLink to="/dia-diem?q=Mang+Thít" class="saved-sugg-card">
                  <span class="sugg-badge sugg-clay">Mang Thít</span>
                  <strong>Lò gạch gốm đỏ ven sông</strong>
                  <span class="sugg-sub">Di sản làng nghề · ~14km</span>
                </NuxtLink>
                <NuxtLink to="/dia-diem?q=An+Bình" class="saved-sugg-card">
                  <span class="sugg-badge sugg-leaf">Long Hồ</span>
                  <strong>Cù lao An Bình miệt vườn</strong>
                  <span class="sugg-sub">Vườn sinh thái · 10p phà</span>
                </NuxtLink>
                <NuxtLink to="/dia-diem?q=Trà+Ôn" class="saved-sugg-card">
                  <span class="sugg-badge sugg-river">Trà Ôn</span>
                  <strong>Chợ nổi ngã ba sông Hậu</strong>
                  <span class="sugg-sub">Giao thương sông nước · ~38km</span>
                </NuxtLink>
              </div>
            </div>
          </div>
          <p v-else>{{ 'Không tìm thấy địa điểm phù hợp trong mục đã lưu.' }}</p>
          <div class="saved-empty-actions">
            <button v-if="savedQuery" type="button" class="btn btn-ghost btn-sm" @click="savedQuery = ''">
              <IconLine name="repeat" /> Xóa bộ lọc
            </button>
            <NuxtLink :to="savedQuery ? searchLink : '/dia-diem'" class="btn btn-primary btn-sm">
              <IconLine name="compass" /> {{ savedQuery ? 'Tìm trên hệ thống' : 'Khám phá 1.500+ địa điểm' }}
            </NuxtLink>
            <NuxtLink v-if="!savedQuery" to="/du-lich" class="btn btn-ghost btn-sm">
              <IconLine name="calendar" /> Cẩm nang theo mùa
            </NuxtLink>
          </div>
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
            <button
              type="button"
              class="saved-remove"
              :aria-label="`Bỏ lưu bài viết của ${post.author_name || 'tác giả'}`"
              @click="removeBookmark(post.id)"
            >
              <IconLine name="x" />
            </button>
          </div>
        </div>
        <div v-else class="saved-empty">
          <p>{{ savedQuery ? 'Không tìm thấy bài viết phù hợp trong bookmark.' : 'Chưa bookmark bài viết nào.' }}</p>
          <div v-if="savedQuery" class="saved-empty-actions">
            <button type="button" class="btn btn-ghost btn-sm" @click="savedQuery = ''">
              <IconLine name="repeat" /> Xóa bộ lọc
            </button>
          </div>
          <NuxtLink v-else to="/cong-dong" class="btn btn-ghost btn-sm">Xem bài viết cộng đồng</NuxtLink>
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
            <button
              type="button"
              class="saved-remove"
              :aria-label="`Xóa lịch trình ${plan.title || ''}`"
              @click="removeItinerary(plan.id)"
            >
              <IconLine name="x" />
            </button>
          </div>
        </div>
        <div v-else class="saved-empty">
          <p>{{ savedQuery ? 'Không tìm thấy lịch trình phù hợp.' : 'Chưa có lịch trình nào.' }}</p>
          <div v-if="savedQuery" class="saved-empty-actions">
            <button type="button" class="btn btn-ghost btn-sm" @click="savedQuery = ''">
              <IconLine name="repeat" /> Xóa bộ lọc
            </button>
          </div>
          <NuxtLink v-else to="/lich-trinh" class="btn btn-ghost btn-sm">Tạo lịch trình mới</NuxtLink>
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

const { isLoggedIn, authFetch, handleSessionExpired } = useAuth()
const { openAuth } = useAuthModal()
const { timeAgo } = useTimeAgo()
const { favorites, remove: removeFavoriteLocal } = useFavorites()
const { show: showToast } = useToast()
const { trackSave } = useUserEvents()
const { savedWorkspaceActions } = useJourneyActions()
const route = useRoute()
const router = useRouter()

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
    const res = await authFetch<{ items: any[] }>('/api/saved')
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
    const res = await authFetch<{ items: any[]; total: number }>(`/api/me/bookmarks?${params}`)
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
    const res = await authFetch<{ items: any[]; total: number }>(`/api/me/bookmarks?${params}`)
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
    const res = await authFetch<{ plans: any[] }>('/api/my-plans')
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
    await authFetch(`/api/posts/${encodePathId(postId)}/bookmark`, { method: 'DELETE' })
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
    await authFetch(`/api/my-plans/${encodePathId(planId)}`, { method: 'DELETE' })
    showToast('Đã xóa lịch trình', 'success')
  } catch (e: unknown) {
    itineraries.value = prev
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể xóa lịch trình', 'error')
  }
}

useSeoMeta({
  title: 'Mục đã lưu — Kho cá nhân — vinhlong360',
  description: 'Kho nội dung cá nhân: địa điểm, bài viết và lịch trình đã lưu trên vinhlong360.',
  ogTitle: 'Mục đã lưu — vinhlong360',
  ogDescription: 'Kho nội dung cá nhân trên vinhlong360.',
  ogUrl: () => canonicalUrl('/da-luu'),
  twitterCard: 'summary_large_image',
  robots: 'noindex, nofollow',
})

useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/da-luu') }],
}))
</script>

<style scoped>
.saved-page { max-width: 920px; margin: 0 auto; }
.saved-guest { padding: var(--space-6) 0; }
.saved-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1rem; }
.saved-kicker { margin: 0 0 .2rem; color: var(--muted); font-size: .8rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.dateline-eyebrow {
  display: flex; align-items: center; gap: .4rem;
  font-family: var(--font-sans); font-size: .78rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .06em; color: var(--muted);
}
.dateline-eyebrow::before { content: ""; width: 14px; height: 1.5px; background: var(--color-brand); flex-shrink: 0; }
.saved-title { font-size: 1.5rem; margin: 0; }
.saved-overview {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .75rem; margin-bottom: 1rem;
}
.saved-overview-item {
  min-height: 88px; padding: .85rem 1rem; border: 1px solid var(--line);
  border-radius: var(--radius-sheet); background: var(--card); display: flex; flex-direction: column; justify-content: space-between;
}
.saved-overview-item span { color: var(--muted); font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.saved-overview-item strong { font-size: 1.25rem; line-height: 1.1; }
.saved-tools { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: .75rem; align-items: center; margin-bottom: 1rem; }
.saved-search input {
  width: 100%; min-height: 44px; padding: .65rem .85rem; border: 1px solid var(--border-input);
  border-radius: var(--radius-surface); background: var(--card); color: var(--ink); font: inherit;
}
.saved-search input:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 1px; }

/* Tabs */
.saved-tabs {
  display: flex; gap: .25rem; margin-bottom: 1.25rem;
  border-bottom: 2px solid var(--line); padding-bottom: 0;
  overflow-x: auto; -webkit-overflow-scrolling: touch;
}
.saved-tab {
  min-height: 44px; display: inline-flex; align-items: center;
  padding: .5rem 1rem; background: none; border: none; cursor: pointer;
  font-weight: 500; font-size: .9rem; color: var(--muted);
  border-bottom: 2px solid transparent; margin-bottom: -2px;
  transition: color var(--duration-fast) var(--ease-out),
              border-color var(--duration-fast) var(--ease-out),
              transform var(--duration-fast) var(--ease-out);
}
.saved-tab:hover { color: var(--ink); }
.saved-tab:active { transform: scale(.98); }
.saved-tab:focus-visible { outline: 2px solid var(--color-focus); outline-offset: -2px; border-radius: var(--radius-control); }
.saved-tab.active { color: var(--color-action); border-bottom-color: var(--color-action); font-weight: 600; }
.saved-tab-count {
  display: inline-block; margin-left: .35rem;
  background: var(--bg-alt); padding: 0 5px; border-radius: var(--radius-full);
  font-size: .75rem; font-weight: 600; color: var(--muted);
}
.saved-tab.active .saved-tab-count { background: rgba(var(--color-action-rgb), .12); color: var(--color-action); }

/* Entity grid — rows use the shared <SavedEntityCard> for the Story-Card
   treatment (serif title, dateline eyebrow, tri-province card-rule, grain
   overlay); this page just supplies the remove-button action + grid layout. */
.saved-grid { display: flex; flex-direction: column; gap: .5rem; }
.saved-remove {
  flex-shrink: 0; width: 44px; height: 44px; min-width: 44px; min-height: 44px;
  display: inline-flex; align-items: center; justify-content: center;
  border: none; background: none;
  color: var(--muted); cursor: pointer; font-size: .95rem;
  border-radius: var(--radius-full);
  transition: background var(--duration-fast) var(--ease-out),
              color var(--duration-fast) var(--ease-out),
              transform var(--duration-fast) var(--ease-out);
}
.saved-remove:hover { background: var(--bg-alt); color: var(--error); }
.saved-remove:active { transform: scale(.92); }
.saved-remove:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }

/* Posts list */
.saved-posts-list { display: flex; flex-direction: column; gap: .5rem; }
.saved-post { padding: .75rem 1rem; display: flex; align-items: center; gap: .5rem; }
.saved-post-link {
  text-decoration: none; color: var(--ink); display: block; flex: 1; min-width: 0;
  border-radius: var(--radius-control);
  transition: opacity var(--duration-fast) var(--ease-out);
}
.saved-post-link:hover { opacity: .85; }
.saved-post-link:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 3px; }
.saved-post-title { display: block; font-weight: 500; font-size: .92rem; line-height: 1.4; }
.saved-post-meta { display: block; font-size: .78rem; color: var(--muted); margin-top: .2rem; }
.saved-load-more { margin-top: .75rem; width: 100%; min-height: 44px; }
.saved-inline-warning {
  margin-bottom: .75rem; padding: .65rem .75rem; border-radius: var(--radius-surface);
  background: color-mix(in oklab, var(--accent-container) 72%, var(--card));
  color: var(--muted); font-size: .85rem; line-height: 1.4;
}

/* Skeletons & empty */
.saved-skeletons { display: flex; flex-direction: column; gap: .5rem; }
.saved-card-skel { height: 64px; border-radius: var(--radius-surface); }
.saved-empty { color: var(--muted); font-size: .9rem; text-align: center; padding: 2rem 1rem; display: flex; flex-direction: column; align-items: center; gap: .75rem; }
.saved-empty p { margin: 0; }

.saved-empty-catalyst {
  padding: var(--space-6) var(--space-4);
  background: var(--card);
  border: 1px dashed var(--line);
  border-radius: var(--radius-sheet);
  max-width: 680px;
  margin: 0 auto;
}
.saved-catalyst-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  text-align: center;
}
.saved-catalyst-icon {
  font-size: 2rem;
  color: var(--color-brand);
  background: var(--color-brand-surface);
  width: 48px;
  height: 48px;
  border-radius: var(--radius-full);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.saved-catalyst-title {
  font-family: var(--font-editorial);
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--ink);
  margin: 0;
}
.saved-catalyst-desc {
  font-size: var(--text-sm);
  color: var(--muted);
  max-width: 480px;
  line-height: var(--leading-relaxed);
}
.saved-suggestions-block {
  width: 100%;
  margin-top: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.saved-suggestions-title {
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--muted);
  text-align: left;
}
.saved-suggestions-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  width: 100%;
}
.saved-sugg-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-height: 44px;
  padding: var(--space-3);
  background: var(--bg-alt);
  border: 1px solid var(--line);
  border-radius: var(--radius-surface);
  text-decoration: none;
  text-align: left;
  transition: transform var(--duration-fast) var(--ease-out),
              border-color var(--duration-fast) var(--ease-out);
}
.saved-sugg-card:hover {
  transform: translateY(-2px);
  border-color: var(--color-action);
}
.saved-sugg-card:active {
  transform: scale(.98);
}
.saved-sugg-card:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
.saved-sugg-card strong {
  font-size: var(--text-xs);
  color: var(--ink);
  line-height: 1.3;
}
.sugg-sub {
  font-size: var(--text-2xs, 10px);
  color: var(--muted);
}
.sugg-badge {
  align-self: flex-start;
  font-size: var(--text-2xs, 10px);
  font-weight: var(--weight-bold);
  padding: 1px 6px;
  border-radius: var(--radius-full);
}
.sugg-clay { background: var(--color-brand-surface); color: var(--color-brand); }
.sugg-leaf { background: color-mix(in srgb, var(--color-material-leaf) 14%, transparent); color: var(--color-material-leaf); }
.sugg-river { background: var(--color-action-surface); color: var(--color-action); }
.saved-empty-actions {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-3);
  flex-wrap: wrap;
  justify-content: center;
}

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
  .saved-suggestions-grid { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  .saved-tab,
  .saved-remove,
  .saved-post-link,
  .saved-sugg-card {
    transition: none !important;
    transform: none !important;
  }
}
</style>
