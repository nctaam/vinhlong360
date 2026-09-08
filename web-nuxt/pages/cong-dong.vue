<template>
  <section class="page threads-page" data-color-system="tri-region-v1">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cộng đồng' }]" :json-ld="true" />

    <!-- Sổ tay hôm nay — masthead sống, không phải catalog-hero -->
    <CommunityAlmanacMasthead
      :has-fresh-post="hasFreshPost"
      :today-label="todayLabel"
      :title="pc('hero_title', almanacHeadline)"
      :stats="communityStats"
    />

    <!-- AEO Plaque: Community Co-Creation & Responsible Storytelling -->
    <CatalogAeoPlaque
      title="Diễn Đàn Đồng Sáng Tạo &amp; Lan Tỏa Văn Hóa Bản Địa"
      kicker="Góc nhìn cộng đồng · Trải nghiệm thực địa từ người bản xứ"
      accent="river"
      icon="users"
      :entries="[
        {
          heading: 'Không Gian Chia Sẻ Thực Chất &amp; Khách Quan',
          text: 'Cộng đồng du khách và người dân cùng ghi nhận những góc quán mộc mạc, con đò quen và nếp sống hào sảng.',
        },
        {
          heading: 'Quy Chuẩn Gắn Thẻ &amp; Xác Thực Địa Điểm',
          text: 'Sử dụng ký tự @ để liên kết chính xác địa chỉ danh thắng, nhà vườn sinh thái hoặc nghệ nhân làng nghề trong tỉnh.',
        },
        {
          heading: 'Tôn Trọng Sự Thật &amp; Gìn Giữ Cảnh Quan Bản Địa',
          text: 'Khuyến khích các đánh giá trung thực, văn minh, bảo vệ môi trường và tôn vinh phong tục tập quán truyền thống.',
        },
      ]"
      cta-to="/huong-dan-thanh-vien"
      cta-label="Quy tắc ứng xử &amp; hướng dẫn cộng đồng"
    />

    <div class="threads-layout">
      <div class="threads-feed">
        <h2 class="sr-only">Bảng tin cộng đồng</h2>

        <!-- Vệt phù sa mới — bài đăng trong phiên này, im lặng cho tới khi có tín hiệu -->
        <CommunityNewPostHint :show="showNewPostHint" @scroll="scrollToNewest" />

        <!-- Report entity (if from ?report=id) -->
        <CommunityReportCard />

        <!-- Create post (Threads style) -->
        <div v-if="isLoggedIn && !ugcUnavailable" id="compose" ref="composeEl" class="threads-compose" role="form" aria-label="Viết bài mới">
          <div class="compose-left">
            <span class="avatar thread-avatar">{{ userInitial }}</span>
          </div>
          <div class="compose-right">
            <div class="post-type-selector">
              <button type="button"
                v-for="pt in postTypes"
                :key="pt.value"
                :class="['chip chip-sm', { active: newType === pt.value }]"
                :aria-pressed="newType === pt.value"
                @click="newType = pt.value"
              ><IconLine :name="pt.icon" aria-hidden="true" /> <span>{{ pt.label }}</span></button>
            </div>

            <CommunityQuotePreview :post="quotingPost" @cancel="cancelQuote" />

            <div class="compose-mention-wrap">
              <textarea
                ref="composeInputEl"
                v-model="newContent"
                class="compose-input"
                :placeholder="typePlaceholder"
                :maxlength="MAX_CHARS"
                rows="2"
                aria-label="Nội dung bài viết (gõ @ để nhắc người dùng hoặc địa điểm)"
                @input="onComposerInput"
                @keydown="onComposerKeydown"
              ></textarea>
              <CommunityMentionDropdown
                :open="mentionOpen"
                :results="mentionResults"
                :active-index="mentionActive"
                @pick="pickMention"
              />
            </div>

            <div v-if="previewImageRows.length" class="img-preview-row">
              <figure
                v-for="row in previewImageRows"
                :key="row.rawIndex"
                class="img-preview-item"
                :data-preview-status="row.status"
                :data-source-class="row.descriptor?.source_class || undefined"
              >
                <div v-if="row.descriptor?.url" class="img-preview-thumb">
                  <img :src="row.descriptor.url" :alt="row.descriptor.alt" :aria-describedby="communityUploadDisclosureId(row.rawIndex)" width="120" height="120" loading="lazy" decoding="async" @error="(e: Event) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
                </div>
                <p v-else class="img-preview-invalid" role="status">{{ row.auditText }}</p>
                <button type="button" class="remove" :aria-label="`Xóa ảnh ${row.rawIndex + 1}`" @click="removeImage(row.rawIndex)"><IconLine name="x" /></button>
                <ImageDisclosure v-if="row.descriptor" :id="communityUploadDisclosureId(row.rawIndex)" :descriptor="row.descriptor" presentation="short" />
              </figure>
            </div>

            <CommunitySchedulePicker
              v-if="!quotingPost"
              v-model="schedulePost"
              v-model:scheduled-at="scheduledAt"
              :min-schedule-date="minScheduleDate"
            />

            <div class="compose-footer">
              <div class="compose-footer-left">
                <label class="compose-attach" title="Thêm ảnh">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    class="sr-only"
                    aria-label="Thêm ảnh"
                    @change="onFileSelect"
                  />
                </label>
                <span v-if="newContent.length > 0" :class="['char-count', { warn: charRatio > .8, full: charRatio >= 1 }]">
                  {{ newContent.length }}/{{ MAX_CHARS }}
                </span>
              </div>
              <button type="button" class="btn btn-primary btn-sm" :disabled="!canSubmit || posting || (schedulePost && !scheduledAt)" @click="submitPost">
                {{ posting ? (schedulePost ? 'Đang lên lịch…' : 'Đang đăng…') : (schedulePost ? 'Lên lịch' : 'Đăng') }}
              </button>
            </div>
          </div>
        </div>

        <CommunityComposeGuest v-else-if="!ugcUnavailable" @login="openAuth()" />

        <!-- Bài đã lên lịch -->
        <CommunityScheduledPosts
          v-if="isLoggedIn && scheduledPosts.length"
          :posts="scheduledPosts"
          @cancel="cancelScheduled"
        />

        <CommunitySearchSection
          v-model="searchInput"
          :search-mode="searchMode"
          :search-query="searchQuery"
          :display-posts-count="displayPosts.length"
          :search-users="searchUsers"
          :ugc-unavailable="ugcUnavailable"
          @search="runSearch"
          @clear="clearSearch"
        />

        <!-- Feed tabs contracted via :data-tab="tab.key" -->
        <CommunityFeedTabs
          v-if="!searchMode && !ugcUnavailable"
          :visible-feed-tabs="visibleFeedTabs"
          :active-tab="activeTab"
          :loading="loading"
          :active-tag="activeTag"
          :filter-type="filterType"
          :filter-type-options="filterTypeOptions"
          @select-tab="setTab"
          @refresh="refreshFeed"
          @clear-tag="clearTag"
          @select-type="setFilterType"
          @tab-keydown="onFeedTabKeydown"
          @type-keydown="onTypeFilterKeydown"
        >
          <template #discovery>
            <!-- Mobile discovery strip (sidebar content for small screens) -->
            <CommunityMobileDiscovery
              :top-members="topMembers"
              :trending-tags="trendingTags"
              :search-mode="searchMode"
            />
          </template>
        </CommunityFeedTabs>

        <!-- Posts -->
        <SkeletonGrid v-if="(loading || bookmarksLoading || searchLoading) && !displayPosts.length" :count="3" />

        <TransitionGroup name="post-list" tag="div" class="post-list-container">
          <PostCard
            v-for="post in displayPosts"
            :key="post.id"
            :post="post"
            :has-replies="(post.comments_count || 0) > 0"
            :can-hide="canHidePosts"
            @like="toggleLike"
            @comment="goToPost"
            @bookmark="toggleBookmark"
            @report="reportPost"
            @repost="repostPost"
            @quote="startQuote"
            @edit="(id) => navigateTo(`${postPath(id)}?edit=1`)"
            @delete="deletePost"
            @hide="hidePost"
          />
        </TransitionGroup>

        <EmptyState
          v-if="searchMode && !searchResults.length && !searchLoading"
          icon-name="search" title="Không tìm thấy bài viết"
          :message="`Không có bài viết nào khớp “${searchQuery}”.`"
        />

        <div v-else-if="ugcUnavailable" class="feed-error" data-service-state="503">
          <p>Dịch vụ cộng đồng đang tạm thời gián đoạn (503). Vui lòng thử lại sau ít phút.</p>
          <button type="button" class="btn btn-outline btn-sm" @click="fetchFeed(true)">Thử lại</button>
        </div>

        <div v-else-if="feedError && !displayPosts.length" class="feed-error">
          <p>Không thể tải bảng tin.</p>
          <button type="button" class="btn btn-outline btn-sm" @click="fetchFeed(true)">Thử lại</button>
        </div>

        <CommunityFeedEmptyStates
          :active-tab="activeTab"
          :bookmarks-length="bookmarks.length"
          :bookmarks-loading="bookmarksLoading"
          :posts-length="posts.length"
          :loading="loading"
          :feed-error="feedError"
          :is-logged-in="isLoggedIn"
          @focus-composer="focusComposer"
          @login="openAuth()"
        />

        <!-- Cuộn vô hạn: observer tự nạp khi sentinel vào tầm; nút là fallback (no-JS/observer fail) -->
        <div ref="loadSentinel" class="load-sentinel" aria-hidden="true"></div>
        <button type="button" v-if="canLoadMore" class="btn btn-ghost threads-load-more" @click="loadMore">
          Xem thêm
        </button>
        <div v-if="(loading && posts.length) || bookmarksLoading || (searchLoading && searchResults.length)" class="feed-loading" role="status" aria-live="polite" aria-label="Đang tải bài viết"><div class="spinner"></div></div>
      </div>

      <CommunitySidebar
        :feed-stats="feedStats"
        :recent-mentions="recentMentions"
        :top-members="topMembers"
        :suggested-users="suggestedUsers"
        :trending-tags="trendingTags"
        :is-logged-in="isLoggedIn"
        @follow="followSuggested"
      />
    </div>

    <!-- Save momentum & undo-hide notifications (data-testid="hide-undo", data-post-action="undo-hide") -->
    <CommunityFloatingNotices
      :show-bookmark-momentum="showBookmarkMomentum"
      :hidden-notice="hiddenNotice"
      :undoing-hide="undoingHide"
      @view-bookmarks="setTab('bookmarks'); bookmarkBannerDismissed = true"
      @dismiss-bookmark="bookmarkBannerDismissed = true"
      @undo-hide="undoHide"
      @dismiss-hide="dismissHiddenNotice"
    />

    <!-- Scroll to top — uses global ScrollToTop from layout -->

    <!-- declutter-3 T14 (A3c): ReportModal page-level — reportPost (PostCard @report) mở modal này -->
    <ClientOnly><LazyReportModal /></ClientOnly>
  </section>
</template>

<script setup lang="ts">
import type { Post, Entity } from '~/types'
import ImageDisclosure from '~/components/ImageDisclosure.vue'
import { describePostPreviewRows } from '~/utils/imageDescriptors'
import {
  COMMUNITY_POST_TYPES as postTypes,
  COMMUNITY_FEED_TABS as feedTabs,
  type FeedTab,
  type PostTypeValue,
} from '~/composables/useCommunityFeedNavigation'
useReveal()
const { f: pc } = usePageContent('cong_dong')

const MAX_CHARS = 500

const { isLoggedIn, authHeaders, user, handleSessionExpired } = useAuth()
const { openAuth } = useAuthModal()
const { repost } = useRepost()
function repostPost(postId: string) {
  repost(postId, () => { activeTab.value = 'latest'; fetchFeed(true) })
}
const route = useRoute()
const router = useRouter()

const { show: showToast } = useToast()
const { trackEvent } = useUserEvents()

const privateFeedTabs = new Set<FeedTab>(['following', 'bookmarks'])
const postTypeValues = new Set(postTypes.map(pt => pt.value))

function firstQueryValue(value: unknown) {
  return Array.isArray(value) ? String(value[0] || '') : String(value || '')
}

function normalizeTagQuery(value: unknown) {
  return firstQueryValue(value).trim().replace(/^#/, '').toLowerCase()
}

const userInitial = computed(() => {
  const name = user.value?.display_name || user.value?.phone || '?'
  return name.charAt(0).toUpperCase()
})

// ── Tabs & filtering ──
const activeTab = ref<FeedTab>('latest')
const sort = computed(() => activeTab.value === 'trending' ? 'trending' : 'latest')
const filterType = ref<PostTypeValue>('')
const activeTag = ref(normalizeTagQuery(route.query.tag))
const visibleFeedTabs = computed(() => feedTabs.filter(tab => !tab.requiresAuth || isLoggedIn.value))
const filterTypeOptions = computed<Array<{ value: PostTypeValue; label: string; icon?: string }>>(() => [
  { value: '', label: 'Tất cả' },
  ...postTypes.map(pt => ({ value: pt.value as PostTypeValue, label: pt.label, icon: pt.icon })),
])
const { syncToUrl: syncFeedFiltersToUrl } = useFilterUrl({ tab: activeTab, type: filterType }, { tab: 'latest', type: '' })

function isFeedTab(value: unknown): value is FeedTab {
  return typeof value === 'string' && feedTabs.some(tab => tab.key === value)
}
function isPrivateFeedTab(value: unknown) {
  return isFeedTab(value) && privateFeedTabs.has(value)
}
function normalizeFeedTab(value: unknown): FeedTab {
  if (!isFeedTab(value)) return 'latest'
  if (privateFeedTabs.has(value) && !isLoggedIn.value) return 'latest'
  return value
}
function normalizeFilterType(value: unknown): PostTypeValue {
  const next = typeof value === 'string' ? value : ''
  return (next === '' || postTypeValues.has(next)) ? next as PostTypeValue : ''
}
function normalizeCommunityRouteState() {
  const nextTab = normalizeFeedTab(activeTab.value)
  const nextType = activeTab.value === 'bookmarks' ? '' : normalizeFilterType(filterType.value)
  let changed = false
  if (nextTab !== activeTab.value) { activeTab.value = nextTab; changed = true }
  if (nextType !== filterType.value) { filterType.value = nextType; changed = true }
  if (changed) syncFeedFiltersToUrl()
}
normalizeCommunityRouteState()

watch(() => route.query.tag, (t) => {
  const newTag = normalizeTagQuery(t)
  if (newTag !== activeTag.value) { activeTag.value = newTag; fetchFeed(true) }
})
watch(() => route.query.q, () => applyRouteSearchQuery())
watch(() => route.query.compose, () => focusComposerFromRoute())
function clearTag() {
  activeTag.value = ''
  const { tag: _, ...rest } = route.query
  router.replace({ query: rest })
  fetchFeed(true)
}
const page = ref(1)
const posts = ref<Post[]>([])
const hasMore = ref(false)
const loading = ref(false)
const feedError = ref(false)
const ugcUnavailable = ref(false)
let feedAbort: AbortController | null = null
type PostListResponse = import('~/composables/useCommunityPostFilters').PostListResponse<Post>
const {
  filterCommunityPosts,
  mergeCommunityPosts,
  extractPostArray,
  responseHasMore,
} = useCommunityPostFilters<Post>()

// ── Bookmarks ──
const {
  bookmarks,
  bookmarksLoading,
  bookmarksPage,
  bookmarksHasMore,
  sessionBookmarked,
  bookmarkBannerDismissed,
  fetchBookmarks,
} = useCommunityBookmarks({
  authHeaders,
  handleSessionExpired,
  showToast,
  filterCommunityPosts,
  mergeCommunityPosts,
  extractPostArray,
  responseHasMore,
})
const showBookmarkMomentum = computed(() =>
  sessionBookmarked.value && !bookmarkBannerDismissed.value && activeTab.value !== 'bookmarks'
)

// ── Tìm bài viết cộng đồng ──
function syncCommunitySearchQuery(q: string) {
  if (!import.meta.client) return
  const query = { ...route.query }
  const term = q.trim()
  if (term) query.q = term
  else delete query.q
  if (firstQueryValue(route.query.q) === firstQueryValue(query.q)) return
  router.replace({ query }).catch(() => {})
}

const {
  searchInput,
  searchQuery,
  searchResults,
  searchPage,
  searchHasMore,
  searchLoading,
  searchMode,
  searchUsers,
  fetchSearch,
  runSearch,
  clearSearch,
  applyRouteSearchQuery,
} = useCommunitySearch({
  authHeaders,
  handleSessionExpired,
  showToast,
  filterCommunityPosts,
  mergeCommunityPosts,
  extractPostArray,
  responseHasMore,
  syncSearchQuery: syncCommunitySearchQuery,
  firstQueryValue,
  getRouteQueryQ: () => route.query.q,
})

const { saveDraft, loadDraft, clearDraft } = useDrafts()
const newContent = ref('')
const newType = ref('share')
const posting = ref(false)
const imageFiles = ref<File[]>([])
const previewImages = ref<string[]>([])
const previewImageRows = computed(() => describePostPreviewRows({
  display_name: user.value?.display_name || 'Bài viết',
  images: previewImages.value,
}))
const charRatio = computed(() => newContent.value.length / MAX_CHARS)
const quotingPost = ref<Record<string, any> | null>(null)

// ── Lên lịch đăng bài ──
const {
  schedulePost,
  scheduledAt,
  minScheduleDate,
  scheduledPosts,
  loadScheduledPosts,
  cancelScheduled,
} = useCommunityScheduledPosts()

// ── Community discovery (stats, leaderboard, trending tags, suggested follows) ──
const {
  communityStats,
  feedStats,
  loadCommunityStats,
  trendingTags,
  loadTrendingTags,
  topMembers,
  loadLeaderboard,
  suggestedUsers,
  loadSuggested,
  followSuggested,
} = useCommunityDiscovery({ openAuth })

// ── Display posts (with type filter) ──
const displayPosts = computed(() => {
  if (searchMode.value) return searchResults.value
  if (activeTab.value === 'bookmarks') return bookmarks.value
  if (!filterType.value) return posts.value
  return posts.value.filter(p => p.post_type === filterType.value)
})

// ── Sổ tay hôm nay & Vệt phù sa mới (Composable useCommunityAlmanac) ──
const {
  todayLabel,
  latestPost,
  almanacHeadline,
  hasFreshPost,
  showNewPostHint,
  scrollToNewest,
  recentMentions,
} = useCommunityAlmanac({
  posts,
  activeTab,
  searchMode,
})

const canLoadMore = computed(() => {
  if (searchMode.value) return searchHasMore.value && !searchLoading.value
  if (activeTab.value === 'bookmarks') return bookmarksHasMore.value && !bookmarksLoading.value
  return hasMore.value && !loading.value
})

// ── Báo sai dữ liệu địa điểm (?report=<id>) ──
const reportEntityId = computed(() => firstQueryValue(route.query.report).trim())
const reportEntityApiPath = computed(() => reportEntityId.value ? `/api/entities/${encodeURIComponent(reportEntityId.value)}` : '')


const typePlaceholder = computed(() => {
  const map: Record<string, string> = {
    share: 'Kể về trải nghiệm du lịch của bạn…',
    review: 'Đánh giá một địa điểm, sản phẩm…',
    question: 'Bạn muốn hỏi gì về Vĩnh Long?',
    recommend: 'Gợi ý một địa điểm, món ăn…',
  }
  return map[newType.value] || map.share
})

const canSubmit = computed(() => {
  if (newContent.value.length > MAX_CHARS) return false
  if (quotingPost.value) return true   // rỗng = đăng lại, có chữ = trích dẫn
  return newContent.value.trim().length > 0
})

const loadSentinel = ref<HTMLElement | null>(null)
let loadObserver: IntersectionObserver | null = null
let suppressFilterFetch = false

// ── Composer & Quote (Composable useCommunityQuoteAndComposer) ──
const composeInputEl = ref<HTMLTextAreaElement | null>(null)
const {
  mentionResults, mentionOpen, mentionActive,
  onInput: onMentionInput, pick: pickMention,
  onKeydown: onMentionKeydownComposer, closeMention, reset: resetMention, activeMentions,
} = useMentionAutocomplete(newContent, composeInputEl)

const {
  composeEl,
  focusComposer,
  startQuote,
  cancelQuote,
  autoGrow,
  onComposerKeydown,
  onComposerInput,
  focusComposerFromRoute,
  onClickOutsideMention,
} = useCommunityQuoteAndComposer({
  posts,
  isLoggedIn,
  openAuth,
  authHeaders,
  activeTab,
  schedulePost,
  scheduledAt,
  onMentionInput,
  onMentionKeydownComposer,
  submitPost,
  closeMention,
  mentionOpen,
  firstQueryValue,
  route,
  quotingPost,
})

// Thu nhỏ ảnh trước khi gửi (max 1280px, JPEG q0.82) — base64 nhẹ đi nhiều lần (trước đây
// gửi full-size → payload có thể tới hàng chục MB).
function downscaleImage(file: File, maxDim = 1280, quality = 0.82): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      let { width, height } = img
      if (Math.max(width, height) > maxDim) {
        const s = maxDim / Math.max(width, height)
        width = Math.round(width * s); height = Math.round(height * s)
      }
      const canvas = document.createElement('canvas')
      canvas.width = width; canvas.height = height
      const ctx = canvas.getContext('2d')
      if (!ctx) return reject(new Error('no-ctx'))
      ctx.drawImage(img, 0, 0, width, height)
      const result = canvas.toDataURL('image/jpeg', quality)
      canvas.width = 0; canvas.height = 0
      resolve(result)
    }
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('img-load')) }
    img.src = url
  })
}

async function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files) return
  const newFiles = Array.from(input.files).slice(0, 5 - imageFiles.value.length)
  for (const file of newFiles) {
    if (!file.type.startsWith('image/') || file.type === 'image/svg+xml') { showToast(`${file.name} không phải ảnh hợp lệ`, 'warning'); continue }
    if (file.size > 10 * 1024 * 1024) { showToast('Ảnh quá lớn (tối đa 10MB)', 'warning'); continue }
    try {
      const dataUrl = await downscaleImage(file)
      imageFiles.value.push(file)
      previewImages.value.push(dataUrl)
    } catch {
      showToast('Không thể đọc ảnh', 'error')
    }
  }
  input.value = ''
}

function removeImage(idx: number) {
  imageFiles.value.splice(idx, 1)
  previewImages.value.splice(idx, 1)
}

function communityUploadDisclosureId(index: number): string {
  return `community-upload-image-${index}-disclosure`
}

function setTab(tab: FeedTab) {
  if (isPrivateFeedTab(tab) && !isLoggedIn.value) {
    activeTab.value = 'latest'
    openAuth()
    return
  }
  const nextTab = normalizeFeedTab(tab)
  if (searchMode.value) clearSearch()
  if (activeTab.value === nextTab) return
  feedAbort?.abort()
  activeTab.value = nextTab
  suppressFilterFetch = true
  filterType.value = ''
  nextTick(() => { suppressFilterFetch = false })
  if (nextTab === 'bookmarks') {
    if (!bookmarks.value.length) fetchBookmarks(true)
  } else {
    fetchFeed(true)
  }
  nextTick(() => {
    if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

// ── Feed navigation & A11y phím tắt (Composable useCommunityFeedNavigation) ──
const {
  focusFeedTab,
  focusTypeFilter,
  onFeedTabKeydown,
  onTypeFilterKeydown,
  setFilterType,
} = useCommunityFeedNavigation({
  activeTab,
  filterType,
  visibleFeedTabs,
  filterTypeOptions,
  setTab,
  normalizeFeedTab,
  normalizeFilterType,
})

async function fetchFeed(reset = false) {
  normalizeCommunityRouteState()
  if (activeTab.value === 'bookmarks') { await fetchBookmarks(reset); return }
  if (reset) { page.value = 1; posts.value = []; feedError.value = false; ugcUnavailable.value = false }
  feedAbort?.abort()
  feedAbort = new AbortController()
  loading.value = true
  try {
    const url = activeTab.value === 'following'
      ? `/api/feed/following?page=${page.value}&limit=20`
      : (() => {
          const params = new URLSearchParams({ page: String(page.value), limit: '20', sort: sort.value })
          if (filterType.value) params.set('post_type', filterType.value)
          if (activeTag.value) params.set('tag', activeTag.value)
          return `/api/feed?${params}`
        })()
    const res = await $fetch<PostListResponse>(url, {
      headers: authHeaders(),
      signal: feedAbort.signal,
    })
    const rawPosts = extractPostArray(res)
    const newPosts = filterCommunityPosts(rawPosts)
    posts.value = reset ? newPosts : mergeCommunityPosts(posts.value, newPosts)
    hasMore.value = responseHasMore(res, rawPosts)
  } catch (e: unknown) {
    if (e instanceof DOMException && e.name === 'AbortError') return
    const status = (e as any)?.response?.status || (e as any)?.status || (e as any)?.statusCode
    if (status === 503) {
      ugcUnavailable.value = true
      return
    }
    if (reset && !posts.value.length) feedError.value = true
    showToast(reset ? 'Không thể tải bảng tin' : 'Không thể tải thêm', 'error')
  } finally {
    loading.value = false
  }
}

function refreshFeed() {
  if (searchMode.value) { fetchSearch(true); return }
  if (activeTab.value === 'bookmarks') { fetchBookmarks(true); return }
  fetchFeed(true)
}

function loadMore() {
  if (loading.value || searchLoading.value || bookmarksLoading.value) return
  if (searchMode.value) {
    searchPage.value++
    fetchSearch()
  } else if (activeTab.value === 'bookmarks') {
    bookmarksPage.value++
    fetchBookmarks()
  } else {
    page.value++
    fetchFeed()
  }
}

watch(activeTab, (tab) => {
  const normalized = normalizeFeedTab(tab)
  if (normalized !== tab) { activeTab.value = normalized; return }
  if (normalized === 'bookmarks' && filterType.value) setFilterType('')
})

watch(isLoggedIn, (loggedIn) => {
  if (loggedIn) { loadSuggested(); loadScheduledPosts(); return }
  suggestedUsers.value = []
  scheduledPosts.value = []
  if (isPrivateFeedTab(activeTab.value)) setTab('latest')
})

watch(filterType, (value) => {
  const normalized = normalizeFilterType(value)
  if (normalized !== value) { filterType.value = normalized; return }
  if (suppressFilterFetch || searchMode.value || activeTab.value === 'bookmarks') return
  fetchFeed(true)
})

if (import.meta.client) {
  watch([activeTab, filterType, activeTag], ([tab, type, tag]) => {
    trackEvent('community_view', {
      context: 'community',
      metadata: { tab, type, tag },
    }, { dedupeMs: 30_000 })
  })
}

function resetComposer() {
  newContent.value = ''; newType.value = 'share'; imageFiles.value = []; previewImages.value = []
  clearDraft(); resetMention(); quotingPost.value = null; schedulePost.value = false; scheduledAt.value = ''
}

async function submitScheduledPost() {
  const draftBody: Record<string, any> = {
    content: newContent.value.trim(),
    post_type: newType.value,
  }
  if (previewImages.value.length) draftBody.images = previewImages.value
  const { draft } = await $fetch<{ draft: { id: string } }>('/api/drafts', {
    method: 'POST',
    headers: authHeaders(),
    body: draftBody,
  })
  const isoScheduledAt = new Date(scheduledAt.value).toISOString()
  await $fetch(`/api/drafts/${encodePathId(draft.id)}/schedule?scheduled_at=${encodeURIComponent(isoScheduledAt)}`, {
    method: 'POST',
    headers: authHeaders(),
  })
  resetComposer()
  showToast('Đã lên lịch đăng bài', 'success')
  await loadScheduledPosts()
}

async function submitPost() {
  if (!canSubmit.value) return
  if (schedulePost.value && !scheduledAt.value) return
  if (draftTimer) { clearTimeout(draftTimer); draftTimer = null }
  posting.value = true
  try {
    if (schedulePost.value) {
      await submitScheduledPost()
      return
    }
    const body: Record<string, any> = {
      content: newContent.value.trim(),
      post_type: newType.value,
    }
    if (quotingPost.value) body.repost_of = quotingPost.value.id
    if (previewImages.value.length) {
      body.images = previewImages.value
    }
    // chỉ gửi mention còn xuất hiện trong nội dung (user có thể đã xoá)
    const mentions = activeMentions()
    if (mentions.length) body.mentions = mentions
    await $fetch('/api/posts', {
      method: 'POST',
      headers: authHeaders(),
      body,
    })
    const wasQuote = !!quotingPost.value
    resetComposer()
    showToast(wasQuote ? 'Đã đăng trích dẫn' : 'Đã đăng bài viết', 'success')
    activeTab.value = 'latest'
    await fetchFeed(true)
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) handleSessionExpired()
    else showToast(extractErrorMessage(e, schedulePost.value ? 'Không thể lên lịch — vui lòng thử lại' : 'Gửi bài thất bại — vui lòng thử lại'), 'error')
  } finally {
    posting.value = false
  }
}



const { reportPost } = useReport()

// ── Tương tác bài viết đa bộ sưu tập (Composable useCommunityPostInteractions) ──
const {
  _copies,
  toggleLike,
  toggleBookmark,
  deletePost,
} = useCommunityPostInteractions({
  posts,
  bookmarks,
  searchResults,
  sessionBookmarked,
})

// ── Tự dọn bảng tin: ẩn bài (riêng tư, không phải kiểm duyệt) ──
// CHỈ bật ở tab feed thật (latest / trending / following). Tab "Đã lưu" và chế-độ
// tìm kiếm đọc /api/me/bookmarks và /api/search/posts — hai endpoint KHÔNG lọc
// `user_hidden_posts`, nên bài ẩn ở đó sẽ quay lại sau khi tải lại trang.
const canHidePosts = computed(() => !searchMode.value && activeTab.value !== 'bookmarks')

const { hidePost: _hide, unhidePost: _unhide } = useHiddenPosts()
const hiddenNotice = ref<{ id: string } | null>(null)
const undoingHide = ref(false)
let hiddenNoticeTimer: ReturnType<typeof setTimeout> | null = null

function dismissHiddenNotice() {
  if (hiddenNoticeTimer) { clearTimeout(hiddenNoticeTimer); hiddenNoticeTimer = null }
  hiddenNotice.value = null
}

async function hidePost(postId: string) {
  // Lạc quan + hoàn nguyên nằm trong useHiddenPosts: API lỗi thì bài quay lại
  // ĐÚNG vị trí cũ kèm toast lỗi, và `ok=false` nên không hiện dải "Hoàn tác".
  const ok = await _hide(postId, [posts, bookmarks, searchResults])
  if (!ok) return
  dismissHiddenNotice()
  hiddenNotice.value = { id: postId }
  hiddenNoticeTimer = setTimeout(() => { hiddenNotice.value = null; hiddenNoticeTimer = null }, 8000)
}

async function undoHide() {
  const notice = hiddenNotice.value
  if (!notice || undoingHide.value) return
  undoingHide.value = true
  try {
    const ok = await _unhide(notice.id)
    if (!ok) return
    dismissHiddenNotice()
    showToast('Đã bỏ ẩn bài viết', 'success')
    // Nạp lại feed để bài về đúng thứ tự backend trả, không phải vị trí đoán.
    await fetchFeed(true)
  } finally {
    undoingHide.value = false
  }
}

onUnmounted(dismissHiddenNotice)

function goToPost(postId: string) {
  navigateTo(postPath(postId))
}

let draftTimer: ReturnType<typeof setTimeout> | null = null
watch(newContent, (v) => {
  if (draftTimer) clearTimeout(draftTimer)
  draftTimer = setTimeout(() => {
    try { saveDraft(v, newType.value) } catch { showToast('Không thể lưu bản nháp', 'warning') }
  }, 3000)
})

onMounted(() => {
  document.addEventListener('click', onClickOutsideMention)
  trackEvent('community_view', {
    context: 'community',
    metadata: { tab: activeTab.value, type: filterType.value, tag: activeTag.value },
  })
  const draft = loadDraft()
  if (draft && draft.content) { newContent.value = draft.content; newType.value = draft.postType }
  applyRouteSearchQuery()
  focusComposerFromRoute()
  normalizeCommunityRouteState()
  refreshFeed()
  // Vào thẳng ?tab=following (link chia sẻ, back/forward) — activeTab đã là
  // 'following' TRƯỚC KHI watch(activeTab, …) bên dưới kịp đăng ký (useFilterUrl
  // gán ref đồng bộ lúc setup), nên watcher sẽ không bắt được lần đổi tab đó.
  if (activeTab.value === 'following' && isLoggedIn.value) fetchFeed(true)
  loadCommunityStats(); loadTrendingTags(); loadLeaderboard(); loadSuggested(); loadScheduledPosts()
  // Trích dẫn từ trang khác điều hướng tới: ?quote=<post_id>
  const q = firstQueryValue(route.query.quote).trim()
  if (q) {
    startQuote(q)
    const { quote, ...rest } = route.query
    router.replace({ query: rest })
  }
  // Cuộn vô hạn: tự nạp trang kế khi sentinel gần vào tầm nhìn
  if (typeof IntersectionObserver !== 'undefined' && loadSentinel.value) {
    loadObserver = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting && canLoadMore.value) loadMore()
    }, { rootMargin: '500px' })
    loadObserver.observe(loadSentinel.value)
  }
})

onUnmounted(() => {
  if (draftTimer) { clearTimeout(draftTimer); draftTimer = null }
  feedAbort?.abort()
  loadObserver?.disconnect()
  document.removeEventListener('click', onClickOutsideMention)
})

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
  ogUrl: () => canonicalUrl('/cong-dong'),
  twitterCard: 'summary_large_image',
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/cong-dong') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: safeJsonLd({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'Cộng đồng vinhlong360',
      description: 'Bảng tin cộng đồng chia sẻ trải nghiệm du lịch, đánh giá và báo cáo dữ liệu cho tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025).',
      url: canonicalUrl('/cong-dong'),
      speakable: buildSpeakableSpecification(['h1', '.threads-layout h2', '.catalog-aeo-plaque__title', '.catalog-aeo-plaque__dek']),
    }),
  }],
})
</script>

<style scoped>
/* ── Section rhythm & layout ── */
.threads-page { max-width: 960px; margin: 0 auto; }
.threads-layout { display: grid; grid-template-columns: 1fr 280px; gap: var(--space-6); align-items: start; }
.threads-feed { display: flex; flex-direction: column; min-width: 0; }

/* ── Compose (Threads style) ── */
.threads-compose {
  display: flex; gap: var(--space-3); border-radius: var(--radius-surface);
  margin: 0 calc(var(--space-2) * -1) var(--space-2);
  padding: var(--space-5) var(--space-3) var(--space-4);
  background: rgba(var(--accent-rgb), .04); box-shadow: var(--shadow-xs);
  transition: background .3s var(--ease-out), border-color .3s var(--ease-out), border-radius .3s var(--ease-out), box-shadow .3s var(--ease-out-expo);
}
.threads-compose:focus-within { background: rgba(var(--accent-rgb), .07); border-radius: var(--radius-sheet); box-shadow: var(--shadow-sm); }
.compose-left { width: 40px; flex-shrink: 0; display: flex; justify-content: center; }
.compose-right { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.compose-input {
  width: 100%; border: none; background: transparent; color: var(--ink);
  font-size: var(--text-base); line-height: var(--leading-relaxed);
  resize: none; outline: none; font-family: inherit; min-height: 44px; padding: 0;
}
.compose-input:focus-visible { outline: 2px solid var(--color-focus); outline-offset: -2px; }
.compose-input::placeholder { color: var(--muted); }
.post-type-selector { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.post-type-selector .chip-sm { transition: background .2s, color .2s, border-color .2s, transform .25s var(--ease-out-expo); }
.post-type-selector .chip-sm.active { transform: scale(1.04); }
.post-type-selector .chip-sm:active { transform: scale(.95); transition-duration: .08s; }
.compose-footer { display: flex; justify-content: space-between; align-items: center; gap: var(--space-3); padding-top: var(--space-1); }
.compose-footer-left { display: flex; align-items: center; gap: var(--space-3); }
.compose-attach {
  display: inline-flex; align-items: center; justify-content: center;
  width: 44px; height: 44px; min-width: 44px; min-height: 44px; border-radius: var(--radius-full);
  cursor: pointer; color: var(--muted); transition: background .3s var(--ease-out), color .3s var(--ease-out), transform .25s var(--ease-out-expo);
}
.compose-attach:hover { background: var(--bg-alt); color: var(--ink); transform: scale(1.08); }
.compose-attach:active { transform: scale(.88); transition-duration: .08s; }
.compose-attach:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.char-count { font-size: var(--text-xs); color: var(--muted); font-variant-numeric: tabular-nums; transition: color .2s; }
.char-count.warn { color: var(--accent-dark); }
.char-count.full { color: var(--error); font-weight: var(--weight-semibold); }
.chip-sm { font-size: var(--text-xs); padding: var(--space-2) var(--space-2h); min-height: 44px; display: inline-flex; align-items: center; gap: var(--space-1); }

/* ── Post list transitions & controls ── */
.post-list-container { display: flex; flex-direction: column; margin-top: var(--space-1); }
.post-list-enter-active { transition: opacity .3s var(--ease-out), transform .3s var(--ease-out-expo); }
.post-list-leave-active { transition: opacity .2s var(--ease-out); }
.post-list-enter-from { opacity: 0; transform: translateY(8px); }
.post-list-leave-to { opacity: 0; }
.post-list-move { transition: transform .3s var(--ease-out-expo); }
.threads-load-more {
  width: 100%; margin-top: var(--space-3); min-height: 44px; font-weight: var(--weight-semibold);
  transition: background .25s var(--ease-out), transform .25s var(--ease-out-expo), box-shadow .25s var(--ease-out);
}
.threads-load-more:hover { transform: translateY(-1px); box-shadow: var(--shadow-xs); }
.threads-load-more:active { transform: scale(.98); transition-duration: .08s; }
.threads-load-more:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }

.img-preview-row { display: flex; gap: var(--space-2); flex-wrap: wrap; animation: fadeIn .25s var(--ease-out); }
.img-preview-item { position: relative; width: 120px; margin: 0; display: flex; flex-direction: column; gap: var(--space-1); transition: transform .3s var(--ease-out-expo), box-shadow .3s var(--ease-out); }
.img-preview-thumb { position: relative; width: 64px; height: 64px; border-radius: var(--radius-control); overflow: hidden; }
.img-preview-item:hover { transform: scale(1.08); box-shadow: var(--shadow-sm); }
.img-preview-thumb img { width: 100%; height: 100%; object-fit: cover; }
.img-preview-invalid { min-height: 64px; margin: 0; padding: var(--space-2) var(--space-8) var(--space-2) var(--space-2); border: 1px dashed var(--line); border-radius: var(--radius-control); color: var(--error); font-size: var(--text-xs); line-height: 1.35; }
.img-preview-item .remove { position: absolute; top: -4px; right: -4px; width: 28px; height: 28px; border-radius: 50%; background: var(--overlay-dark); color: var(--text-on-dark, var(--white)); border: none; cursor: pointer; font-size: .7rem; display: flex; align-items: center; justify-content: center; padding: var(--space-2); box-sizing: content-box; transition: background .2s, transform .2s var(--ease-out-expo); }
.img-preview-item .remove:hover { background: var(--error); transform: scale(1.1); }
.img-preview-item .remove:focus-visible { outline: 2px solid var(--text-on-dark, var(--white)); outline-offset: 1px; }
@keyframes fadeIn { from { opacity: 0; } }

.feed-error { text-align: center; padding: var(--space-5); color: var(--error); }
.feed-error p { margin: 0 0 var(--space-3); }
.feed-loading { text-align: center; padding: var(--space-5); }
.feed-loading .spinner { margin: 0 auto; }

/* ── Dark mode & Responsive ── */
.dark .compose-attach:hover { background: rgba(var(--white-rgb),.08); }
.dark .threads-compose { background: rgba(var(--accent-rgb),.06); }
.dark .threads-compose:focus-within { background: rgba(var(--accent-rgb),.1); }
@media (max-width: 820px) {
  .threads-layout { grid-template-columns: 1fr; }
  .threads-sidebar { display: none; }
  .threads-page { max-width: 100%; }
  .threads-feed { padding-inline: var(--space-1); }
  .threads-compose { padding-inline: var(--space-3); }
  .compose-input { min-height: 48px; font-size: var(--text-base); }
  .cd-input { font-size: var(--text-base, 16px); }
}
@media (prefers-reduced-motion: reduce) {
  .img-preview-row { animation: none; }
  .post-list-enter-active, .post-list-leave-active, .post-list-move,
  .fab-fade-enter-active, .fab-fade-leave-active { transition: none; }
  .img-preview-item:hover, .compose-attach:hover, .compose-attach:active,
  .post-type-selector .chip-sm.active, .post-type-selector .chip-sm:active,
  .threads-load-more:hover, .threads-load-more:active { transform: none; }
}
.btn-xs { padding: var(--space-1) var(--space-2h); font-size: .72rem; border-radius: var(--radius-control); }
</style>
