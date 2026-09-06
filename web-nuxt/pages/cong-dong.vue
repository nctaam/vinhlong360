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

    <div class="threads-layout">
      <div class="threads-feed">
        <h2 class="sr-only">Bảng tin cộng đồng</h2>

        <!-- Vệt phù sa mới — bài đăng trong phiên này, im lặng cho tới khi có tín hiệu -->
        <button
          v-if="showNewPostHint"
          type="button"
          class="new-post-thread-hint"
          @click="scrollToNewest"
        >Vừa có chuyện mới — cuộn lên xem ↑</button>

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

            <div v-if="quotingPost" class="quote-preview">
              <div class="quote-preview-body">
                <span class="qp-head"><IconLine name="file-text" /> Trích dẫn <strong>{{ quotingPost.author || quotingPost.display_name || 'Người dùng' }}</strong></span>
                <span class="qp-content">{{ quotingPost.content || '(bài viết)' }}</span>
              </div>
              <button type="button" class="qp-remove" aria-label="Bỏ trích dẫn" @click="cancelQuote"><IconLine name="x" /></button>
            </div>

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
              <ul v-if="mentionOpen && mentionResults.length" class="mention-menu" role="listbox" aria-label="Gợi ý @nhắc">
                <li
                  v-for="(m, mi) in mentionResults"
                  :key="m.type + m.id"
                  :class="['mention-item', { active: mi === mentionActive }]"
                  role="option"
                  :aria-selected="mi === mentionActive"
                  @mousedown.prevent="pickMention(m)"
                >
                  <span class="mention-ic" aria-hidden="true"><IconLine :name="m.type === 'user' ? 'user' : 'pin'" /></span>
                  <span class="mention-label">{{ m.label }}</span>
                  <span class="mention-sub">{{ m.sub }}</span>
                </li>
              </ul>
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

            <div v-if="!quotingPost" class="schedule-option">
              <label class="schedule-toggle">
                <input type="checkbox" v-model="schedulePost" class="cd-toggle" />
                <span>Lên lịch đăng bài</span>
              </label>
              <div v-if="schedulePost" class="schedule-picker">
                <input type="datetime-local" v-model="scheduledAt" class="cd-input" :min="minScheduleDate" required aria-label="Thời gian đăng bài" />
                <span class="cd-hint">Bài sẽ tự động đăng vào thời gian này.</span>
              </div>
            </div>

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

        <div v-else-if="!ugcUnavailable" class="threads-compose-guest">
          <div class="guest-avatar">
            <span class="avatar thread-avatar guest">?</span>
          </div>
          <div class="guest-content">
            <p>Có trải nghiệm muốn chia sẻ?</p>
            <button type="button" class="btn btn-outline btn-sm" @click="openAuth()">Đăng nhập</button>
          </div>
        </div>

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

        <!-- Main tabs -->
        <div v-if="!searchMode && !ugcUnavailable" class="threads-filter-bar">
          <div class="threads-filter" role="tablist" aria-label="Bộ lọc bảng tin" @keydown="onFeedTabKeydown">
            <button
              v-for="tab in visibleFeedTabs"
              :key="tab.key"
              type="button"
              role="tab"
              :class="['threads-tab', { active: activeTab === tab.key }]"
              :aria-selected="activeTab === tab.key"
              :tabindex="activeTab === tab.key ? 0 : -1"
              :data-tab="tab.key"
              @click="setTab(tab.key)"
            >
              <svg v-if="tab.key === 'bookmarks'" class="icon-inline" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>{{ tab.label }}
            </button>
          </div>
          <button type="button" class="threads-refresh" :disabled="loading" aria-label="Tải lại bảng tin" @click="refreshFeed">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" :class="{ spinning: loading }"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          </button>
        </div>

        <!-- Mobile discovery strip (sidebar content for small screens) -->
        <CommunityMobileDiscovery
          :top-members="topMembers"
          :trending-tags="trendingTags"
          :search-mode="searchMode"
        />

        <!-- Đang lọc theo hashtag -->
        <div v-if="activeTag" class="tag-banner" role="status">
          <span>Đang xem <strong>#{{ activeTag }}</strong></span>
          <button type="button" class="tag-clear" @click="clearTag"><IconLine name="x" /> Bỏ lọc</button>
        </div>

        <!-- Post type filter (only for feed tabs, not bookmarks/search) -->
        <div v-if="activeTab !== 'bookmarks' && !searchMode" class="type-filter-row" role="tablist" aria-label="Lọc loại bài viết" @keydown="onTypeFilterKeydown">
          <button
            v-for="pt in filterTypeOptions"
            :key="pt.value || 'all'"
            type="button"
            role="tab"
            :class="['chip chip-filter', { active: filterType === pt.value }]"
            :aria-selected="filterType === pt.value"
            :tabindex="filterType === pt.value ? 0 : -1"
            :data-type="pt.value || 'all'"
            @click="setFilterType(pt.value)"
          ><IconLine v-if="pt.icon" :name="pt.icon" aria-hidden="true" /> <span>{{ pt.label }}</span></button>
        </div>

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

        <EmptyState
          v-else-if="activeTab === 'bookmarks' && !bookmarks.length && !bookmarksLoading"
          icon-name="bookmark" title="Chưa lưu bài viết nào"
          message="Nhấn biểu tượng bookmark trên bài viết để lưu lại và xem sau."
        />

        <EmptyState
          v-else-if="activeTab === 'following' && !posts.length && !loading && !feedError"
          icon-name="users" title="Chưa có bài từ người bạn theo dõi"
          message="Theo dõi người dùng và địa điểm để xem bài viết của họ ở đây."
          hint="Mở hồ sơ người dùng hoặc trang địa điểm rồi nhấn “Theo dõi”."
        >
          <!-- declutter-1 T10: khối onboard-follows đã bỏ — sidebar "Gợi ý kết bạn" là
               nguồn gợi-ý-theo-dõi duy nhất trên trang. -->
          <template #actions>
            <NuxtLink to="/tim-kiem" class="btn btn-outline btn-sm">Tìm người để theo dõi</NuxtLink>
          </template>
        </EmptyState>

        <EmptyState
          v-else-if="activeTab !== 'bookmarks' && activeTab !== 'following' && !posts.length && !loading && !feedError"
          icon-name="message" title="Cộng đồng đang chờ bạn"
          message="Chưa có bài viết nào. Hãy là người đầu tiên chia sẻ!"
          hint="Chia sẻ ảnh chuyến đi, đặt câu hỏi, hay để lại đánh giá của bạn."
        >
          <template v-if="isLoggedIn" #actions>
            <button type="button" class="btn btn-primary btn-sm" @click="focusComposer">Viết bài đầu tiên</button>
          </template>
          <template v-else #actions>
            <button type="button" class="btn btn-primary btn-sm" @click="openAuth()">Đăng nhập để chia sẻ</button>
          </template>
        </EmptyState>

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

    <!-- Save momentum cue — keeps bookmarking from dead-ending -->
    <Transition name="momentum-fade">
      <div v-if="showBookmarkMomentum && !hiddenNotice" class="bookmark-momentum" role="status">
        <span class="bm-icon" aria-hidden="true"><IconLine name="bookmark" /></span>
        <button type="button" class="bm-link" @click="setTab('bookmarks'); bookmarkBannerDismissed = true">Xem mục đã lưu</button>
        <button type="button" class="bm-dismiss" aria-label="Đóng" @click="bookmarkBannerDismissed = true"><IconLine name="x" /></button>
      </div>
    </Transition>

    <!-- Ẩn bài: lối hoàn tác NGAY tại chỗ. Ẩn là thao tác đảo-ngược-được nên
         không chặn bằng hộp thoại xác nhận — đổi lại phải luôn có đường lùi
         (ở đây + tab "Bài đã ẩn" trong /cai-dat). -->
    <Transition name="momentum-fade">
      <div v-if="hiddenNotice" class="bookmark-momentum hide-undo" role="status" data-testid="hide-undo">
        <span class="bm-icon" aria-hidden="true"><IconLine name="eye-off" /></span>
        <span class="hu-text">Đã ẩn bài này khỏi bảng tin của bạn.</span>
        <button type="button" class="bm-link" data-post-action="undo-hide" :disabled="undoingHide" @click="undoHide">Hoàn tác</button>
        <button type="button" class="bm-dismiss" aria-label="Đóng" @click="dismissHiddenNotice"><IconLine name="x" /></button>
      </div>
    </Transition>

    <!-- Scroll to top — uses global ScrollToTop from layout -->

    <!-- declutter-3 T14 (A3c): ReportModal page-level — reportPost (PostCard @report) mở modal này -->
    <ClientOnly><LazyReportModal /></ClientOnly>
  </section>
</template>

<script setup lang="ts">
import type { Post, Entity } from '~/types'
import ImageDisclosure from '~/components/ImageDisclosure.vue'
import { describePostPreviewRows } from '~/utils/imageDescriptors'
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
const postTypes = [
  { value: 'share', label: 'Chia sẻ', icon: 'camera' },
  { value: 'review', label: 'Đánh giá', icon: 'star' },
  { value: 'question', label: 'Hỏi đáp', icon: 'circle-help' },
  { value: 'recommend', label: 'Gợi ý', icon: 'thumbs-up' },
]
type FeedTab = 'latest' | 'trending' | 'following' | 'bookmarks'
type PostTypeValue = '' | 'share' | 'review' | 'question' | 'recommend'

const feedTabs: Array<{ key: FeedTab; label: string; requiresAuth?: boolean }> = [
  { key: 'latest', label: 'Mới nhất' },
  { key: 'trending', label: 'Nổi bật' },
  { key: 'following', label: 'Đang theo dõi', requiresAuth: true },
  { key: 'bookmarks', label: 'Đã lưu', requiresAuth: true },
]
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
// ── Tìm bài viết cộng đồng ──
const searchInput = ref('')
const searchQuery = ref('')          // truy vấn đang áp dụng (rỗng = không ở chế-độ tìm)
const searchResults = ref<Post[]>([])
const searchPage = ref(1)
const searchHasMore = ref(false)
const searchLoading = ref(false)
const searchMode = computed(() => !!searchQuery.value)
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

// ── Bookmarks ──
const bookmarks = ref<Post[]>([])
const bookmarksLoading = ref(false)
const bookmarksPage = ref(1)
const bookmarksHasMore = ref(false)
// Session momentum: after first save this session, surface a "view saved" cue
// so bookmarking has a next action instead of dead-ending.
const sessionBookmarked = ref(false)
const bookmarkBannerDismissed = ref(false)
const showBookmarkMomentum = computed(() =>
  sessionBookmarked.value && !bookmarkBannerDismissed.value && activeTab.value !== 'bookmarks'
)

type PostListResponse = import('~/composables/useCommunityPostFilters').PostListResponse<Post>
const {
  filterCommunityPosts,
  mergeCommunityPosts,
  extractPostArray,
  responseHasMore,
} = useCommunityPostFilters<Post>()

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

// ── Sổ tay hôm nay — masthead sống động (thuần trình bày lại dữ liệu đã có, không API mới) ──
const todayLabel = computed(() =>
  new Date().toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'long' }),
)

// Bài mới nhất trong feed 'latest' — nguồn cho cả H1 động và tín hiệu "vừa có bài mới".
const latestPost = computed(() => posts.value[0])

const almanacHeadline = computed(() => {
  const p = latestPost.value
  if (p?.entity_name) return `Hôm nay, ai đó vừa kể chuyện về ${p.entity_name}.`
  if (p?.display_name) return `Hôm nay, ${p.display_name} vừa kể một chuyện mới.`
  return 'Chuyện kể mỗi ngày của người miền sông nước.'
})

// "Vừa có bài mới" — chỉ tính bài đăng trong 10 phút gần nhất, không phải bài cũ tải lại.
const hasFreshPost = computed(() => {
  const p = latestPost.value
  if (!p?.created_at) return false
  const ageMs = Date.now() - new Date(p.created_at).getTime()
  return ageMs >= 0 && ageMs < 10 * 60 * 1000
})

// Vệt phù sa "bài mới": xuất hiện khi bài đầu feed đổi SAU lần tải đầu tiên của phiên
// (không phải mọi lần feed rỗng→có, tránh hiện ngay khi mới vào trang).
const sessionFirstPostId = ref<string | null>(null)
const newestSeenPostId = ref<string | null>(null)
const newPostHintDismissed = ref(false)
watch(() => posts.value[0]?.id, (id) => {
  if (!id) return
  if (sessionFirstPostId.value === null) { sessionFirstPostId.value = id; newestSeenPostId.value = id; return }
  if (id !== newestSeenPostId.value) { newestSeenPostId.value = id; newPostHintDismissed.value = false }
})
const showNewPostHint = computed(() =>
  activeTab.value === 'latest' && !searchMode.value &&
  !newPostHintDismissed.value &&
  !!newestSeenPostId.value && newestSeenPostId.value !== sessionFirstPostId.value,
)
function scrollToNewest() {
  newPostHintDismissed.value = true
  if (typeof window === 'undefined') return
  const prefersReduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  window.scrollTo({ top: 0, behavior: prefersReduced ? 'auto' : 'smooth' })
}

// "Nhắc tới gần đây" — địa danh được nhắc nhiều nhất trong feed đã tải (client-side tally,
// không gọi API mới). Cầu nối UGC → catalog.
const recentMentions = computed(() => {
  const tally = new Map<string, { entity_id: string; entity_name: string; count: number }>()
  for (const p of posts.value) {
    if (!p.entity_id || !p.entity_name) continue
    const existing = tally.get(p.entity_id)
    if (existing) existing.count++
    else tally.set(p.entity_id, { entity_id: p.entity_id, entity_name: p.entity_name, count: 1 })
  }
  return [...tally.values()].sort((a, b) => b.count - a.count).slice(0, 4)
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

// ── Composer focus (from empty-state CTA) ──
const composeEl = ref<HTMLElement | null>(null)
const composeInputEl = ref<HTMLTextAreaElement | null>(null)
function focusComposer() {
  const prefersReduced = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  composeEl.value?.scrollIntoView({ behavior: prefersReduced ? 'auto' : 'smooth', block: 'center' })
  nextTick(() => composeInputEl.value?.focus())
}

// ── Trích dẫn (quote) ──
async function startQuote(postId: string) {
  if (!isLoggedIn.value) { openAuth(() => startQuote(postId)); return }
  let p: any = posts.value.find((x: any) => x.id === postId)
  if (!p) {
    try { const r = await $fetch<any>(`/api/posts/${encodePathId(postId)}`, { headers: authHeaders() }); p = r?.post } catch { /* post may be deleted */ }
  }
  quotingPost.value = p || { id: postId, content: '(Bài viết không khả dụng)' }
  schedulePost.value = false
  scheduledAt.value = ''
  activeTab.value = 'latest'
  focusComposer()
}
function cancelQuote() { quotingPost.value = null }

function autoGrow(e: Event) {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}

// ── @-mention: gõ @ để nhắc người dùng / địa điểm (composable chung) ──
const {
  mentionResults, mentionOpen, mentionActive,
  onInput: onMentionInput, pick: pickMention,
  onKeydown: onMentionKeydownComposer, closeMention, reset: resetMention, activeMentions,
} = useMentionAutocomplete(newContent, composeInputEl)

function onComposerKeydown(e: KeyboardEvent) {
  if (onMentionKeydownComposer(e)) return
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); submitPost() }
}

function onComposerInput(e: Event) {
  autoGrow(e)
  onMentionInput(e)
}

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

function focusFeedTab(tab: FeedTab) {
  if (typeof document === 'undefined') return
  nextTick(() => document.querySelector<HTMLElement>(`.threads-filter [data-tab="${tab}"]`)?.focus())
}

function focusTypeFilter(value: PostTypeValue) {
  if (typeof document === 'undefined') return
  const key = value || 'all'
  nextTick(() => document.querySelector<HTMLElement>(`.type-filter-row [data-type="${key}"]`)?.focus())
}

function nextIndex(current: number, total: number, key: string) {
  if (key === 'Home') return 0
  if (key === 'End') return total - 1
  if (key === 'ArrowRight' || key === 'ArrowDown') return (current + 1) % total
  if (key === 'ArrowLeft' || key === 'ArrowUp') return (current - 1 + total) % total
  return current
}

function onFeedTabKeydown(e: KeyboardEvent) {
  if (!['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) return
  const tabs = visibleFeedTabs.value.map(tab => tab.key)
  if (!tabs.length) return
  e.preventDefault()
  const current = Math.max(0, tabs.indexOf(normalizeFeedTab(activeTab.value)))
  const tab = tabs[nextIndex(current, tabs.length, e.key)] || 'latest'
  setTab(tab)
  focusFeedTab(tab)
}

function onTypeFilterKeydown(e: KeyboardEvent) {
  if (!['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) return
  const options = filterTypeOptions.value.map(option => option.value)
  e.preventDefault()
  const current = Math.max(0, options.indexOf(normalizeFilterType(filterType.value)))
  const value = options[nextIndex(current, options.length, e.key)] || ''
  setFilterType(value)
  focusTypeFilter(value)
}

function setFilterType(value: PostTypeValue) {
  filterType.value = normalizeFilterType(value)
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

async function fetchBookmarks(reset = false) {
  if (reset) { bookmarksPage.value = 1; bookmarks.value = [] }
  bookmarksLoading.value = true
  try {
    const res = await $fetch<PostListResponse>(`/api/me/bookmarks?page=${bookmarksPage.value}&limit=20`, {
      headers: authHeaders(),
    })
    const rawPosts = extractPostArray(res, 'bookmarks')
    const newPosts = filterCommunityPosts(rawPosts)
    bookmarks.value = reset ? newPosts : mergeCommunityPosts(bookmarks.value, newPosts)
    bookmarksHasMore.value = responseHasMore(res, rawPosts)
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể tải bài viết đã lưu', 'error')
  } finally {
    bookmarksLoading.value = false
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

// ── Tìm bài viết ──
const searchUsers = ref<Array<{ id: string; display_name: string; avatar_url: string; username: string; post_count: number }>>([])

async function fetchSearchUsers(query: string) {
  if (!query || query.length < 2) { searchUsers.value = []; return }
  try {
    const res = await $fetch<{ users: typeof searchUsers.value }>('/api/search/users', {
      params: { q: query, page: 1 },
      headers: authHeaders(),
    })
    searchUsers.value = (res.users || []).slice(0, 5)
  } catch {
    searchUsers.value = []
  }
}

async function fetchSearch(reset = false) {
  if (reset) { searchPage.value = 1; searchResults.value = [] }
  searchLoading.value = true
  try {
    const res = await $fetch<PostListResponse>(
      `/api/search/posts?q=${encodeURIComponent(searchQuery.value)}&page=${searchPage.value}`,
      { headers: authHeaders() },
    )
    const rawPosts = extractPostArray(res)
    const newPosts = filterCommunityPosts(rawPosts)
    searchResults.value = reset ? newPosts : mergeCommunityPosts(searchResults.value, newPosts)
    searchHasMore.value = responseHasMore(res, rawPosts)
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể tìm bài viết', 'error')
  } finally {
    searchLoading.value = false
  }
}

function runSearch() {
  const q = searchInput.value.trim()
  if (q.length < 2) { showToast('Nhập ít nhất 2 ký tự để tìm kiếm', 'info'); return }
  searchQuery.value = q
  syncCommunitySearchQuery(q)
  fetchSearchUsers(q)
  fetchSearch(true)
}

function clearSearch() {
  searchInput.value = ''
  searchQuery.value = ''
  searchResults.value = []
  searchUsers.value = []
  syncCommunitySearchQuery('')
}

function syncCommunitySearchQuery(q: string) {
  if (!import.meta.client) return
  const query = { ...route.query }
  const term = q.trim()
  if (term) query.q = term
  else delete query.q
  if (firstQueryValue(route.query.q) === firstQueryValue(query.q)) return
  router.replace({ query }).catch(() => {})
}

function applyRouteSearchQuery() {
  const q = firstQueryValue(route.query.q).trim()
  if (q.length < 2) {
    if (searchQuery.value) {
      searchInput.value = ''
      searchQuery.value = ''
      searchResults.value = []
    }
    return
  }
  if (q === searchQuery.value) return
  searchInput.value = q
  searchQuery.value = q
  fetchSearch(true)
}

function focusComposerFromRoute() {
  const composeIntent = firstQueryValue(route.query.compose).trim().toLowerCase()
  if (composeIntent !== 'draft' && route.hash !== '#compose') return
  nextTick(() => {
    composeEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    composeInputEl.value?.focus()
  })
}

watch(activeTab, (tab) => {
  const normalized = normalizeFeedTab(tab)
  if (normalized !== tab) { activeTab.value = normalized; return }
  if (normalized === 'bookmarks' && filterType.value) setFilterType('')
})

watch(isLoggedIn, (loggedIn) => {
  if (loggedIn) {
    loadSuggested()
    loadScheduledPosts()
    return
  }
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
  newContent.value = ''
  newType.value = 'share'
  imageFiles.value = []
  previewImages.value = []
  clearDraft()
  resetMention()
  quotingPost.value = null
  schedulePost.value = false
  scheduledAt.value = ''
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

// cùng 1 post có thể nằm ở CẢ feed + tab bookmark → cập-nhật MỌI bản để không lệch.
function _copies(postId: string) {
  return [...posts.value, ...bookmarks.value, ...searchResults.value].filter(p => p.id === postId)
}

const { toggleLike: _like, toggleBookmark: _bookmark, deletePost: _delete } = usePostActions()

function toggleLike(postId: string) {
  _like(postId, _copies(postId))
}
function toggleBookmark(postId: string) {
  _bookmark(postId, _copies(postId), () => {
    if (!sessionBookmarked.value) sessionBookmarked.value = true
  })
}
function deletePost(postId: string) {
  _delete(postId, () => {
    posts.value = posts.value.filter(p => p.id !== postId)
    bookmarks.value = bookmarks.value.filter(p => p.id !== postId)
    searchResults.value = searchResults.value.filter(p => p.id !== postId)
  })
}

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
    try {
      saveDraft(v, newType.value)
    } catch {
      showToast('Không thể lưu bản nháp', 'warning')
    }
  }, 3000)
})

function onClickOutsideMention(e: MouseEvent) {
  if (mentionOpen.value && !(e.target as HTMLElement)?.closest('.compose-mention-wrap')) {
    closeMention()
  }
}

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
  loadCommunityStats()
  loadTrendingTags()
  loadLeaderboard()
  loadSuggested()
  loadScheduledPosts()
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
    }),
  }],
})
</script>

<style scoped>


/* ── Vệt phù sa mới — hairline river→amber, click-to-scroll, session-only ── */
.new-post-thread-hint {
  display: block; width: 100%; margin: 0 0 var(--space-4); padding: var(--space-2) var(--space-3);
  border: none; border-radius: var(--radius-surface); cursor: pointer; text-align: center;
  font-family: var(--font-sans); font-size: var(--text-xs); font-weight: 600;
  letter-spacing: .02em; color: var(--muted);
  background:
    linear-gradient(90deg, transparent, var(--river-600) 15%, var(--amber-600) 85%, transparent) bottom/100% 1.5px no-repeat,
    rgba(var(--accent-rgb), .05);
  transition: color .25s var(--ease-out), background-color .25s var(--ease-out);
  animation: hint-settle .4s var(--ease-out-expo) both;
}
.new-post-thread-hint:hover { color: var(--ink); background-color: rgba(var(--accent-rgb), .09); }
.new-post-thread-hint:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
@keyframes hint-settle { from { opacity: 0; transform: translateY(-4px); } }
.dark .new-post-thread-hint { background-color: rgba(var(--accent-rgb), .08); }
.dark .new-post-thread-hint:hover { background-color: rgba(var(--accent-rgb), .13); }
@media (prefers-reduced-motion: reduce) {
  .new-post-thread-hint { animation: none; }
}

/* ── Section rhythm — khoảng thở giữa compose/search/tabs và feed bên dưới ── */
.threads-filter-bar { margin-bottom: var(--space-2); }
.type-filter-row { margin-top: var(--space-2); }
.threads-compose,
.threads-compose-guest { margin-bottom: var(--space-2); }
.threads-page { max-width: 960px; margin: 0 auto; }
.threads-layout { display: grid; grid-template-columns: 1fr 280px; gap: var(--space-6); align-items: start; }
/* min-width: 0 — grid items default to min-width:auto, which floors this track at its
   content's intrinsic width (the 5 type-filter-row chips, ~430px) instead of shrinking to
   the 1fr track size. That silently widened .threads-page/.threads-layout past the viewport
   on mobile (~84px horizontal overflow at 375px) even though .type-filter-row already has
   overflow-x:auto — the scroll never engaged because the container itself had grown to fit. */
.threads-feed { display: flex; flex-direction: column; min-width: 0; }

/* ── Compose (Threads style) ── */
.threads-compose { display: flex; gap: var(--space-3); padding: var(--space-4) 0; border-bottom: .5px solid var(--line); }
.compose-left { width: 40px; flex-shrink: 0; display: flex; justify-content: center; }
.compose-right { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.compose-input {
  width: 100%; border: none; background: transparent; color: var(--ink);
  font-size: var(--text-base); line-height: var(--leading-relaxed);
  resize: none; outline: none; font-family: inherit;
  min-height: 44px; padding: 0;
}
.compose-input:focus-visible { outline: 2px solid var(--color-focus); outline-offset: -2px; }
.compose-input::placeholder { color: var(--muted); }
.threads-compose {
  transition: background .3s var(--ease-out), border-color .3s var(--ease-out), border-radius .3s var(--ease-out), box-shadow .3s var(--ease-out-expo);
  border-radius: var(--radius-surface); margin: 0 calc(var(--space-2) * -1);
  padding: var(--space-5) var(--space-3) var(--space-4);
  background: rgba(var(--accent-rgb), .04);
  border-bottom: none; box-shadow: var(--shadow-xs);
}
.threads-compose:focus-within { background: rgba(var(--accent-rgb), .07); border-radius: var(--radius-sheet); box-shadow: var(--shadow-sm); }
/* Composer post-type chips — micro feedback on selection (signature) */
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

.threads-compose-guest {
  display: flex; gap: var(--space-3); padding: var(--space-4) 0;
  border-bottom: .5px solid var(--line); align-items: center;
}
.guest-avatar { width: 40px; flex-shrink: 0; display: flex; justify-content: center; }
.guest-avatar .avatar.guest { opacity: .5; }
.guest-content { flex: 1; display: flex; align-items: center; gap: var(--space-3); }
.guest-content p { margin: 0; color: var(--muted); font-size: var(--text-sm); flex: 1; }

/* ── Filter tabs ── */
.threads-filter-bar {
  display: flex; align-items: stretch;
  border-bottom: .5px solid var(--line);
  margin-top: var(--space-5);
  position: sticky; top: 78px; z-index: 20;
  background: var(--surface-translucent, var(--bg));
  backdrop-filter: var(--glass);
  -webkit-backdrop-filter: var(--glass);
}
.threads-filter { display: flex; flex: 1; min-width: 0; }
.threads-tab {
  flex: 1; text-align: center; padding: var(--space-3) var(--space-4);
  background: none; border: none; border-bottom: 2px solid transparent;
  font-size: var(--text-sm); font-weight: var(--weight-semibold);
  color: var(--muted); cursor: pointer; min-height: 44px;
  transition: color .25s var(--ease-out);
  position: relative;
}
.threads-tab::after {
  content: ''; position: absolute; bottom: -1px; left: 20%; right: 20%;
  height: 2px; background: var(--ink); border-radius: 1px;
  transform: scaleX(0); transition: transform .25s var(--ease-out-expo);
}
.threads-tab:hover { color: var(--ink); }
.threads-tab:hover::after { transform: scaleX(.5); }
.threads-tab:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.threads-tab.active { color: var(--ink); border-bottom-color: transparent; }
.threads-tab.active::after { transform: scaleX(1); }
.dark .threads-tab.active { color: var(--ink); }
.threads-refresh {
  flex-shrink: 0; width: 44px; min-height: 44px;
  display: inline-flex; align-items: center; justify-content: center;
  padding: .5rem; background: none; border: none;
  color: var(--muted); cursor: pointer;
  transition: color .25s var(--ease-out), background .25s var(--ease-out);
}
.threads-refresh:hover { color: var(--ink); background: var(--overlay-subtle); }
.threads-refresh:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.threads-refresh svg { display: block; }
.threads-refresh .spinning { animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Type filter ── */
.type-filter-row {
  display: flex; gap: var(--space-2); padding: var(--space-3) 0;
  overflow-x: auto; -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.type-filter-row::-webkit-scrollbar { display: none; }
.chip-filter {
  font-size: var(--text-xs); padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-full); border: .5px solid var(--line);
  background: var(--card); color: var(--muted); cursor: pointer;
  white-space: nowrap; min-height: 44px; display: inline-flex; align-items: center; gap: var(--space-1);
  transition: background .2s, color .2s, border-color .2s, transform .25s var(--ease-out-expo);
}
.chip-filter:hover { border-color: var(--ink); color: var(--ink); }
.chip-filter:active { transform: scale(.95); transition-duration: .08s; }
.chip-filter:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.chip-filter.active { background: var(--ink); color: var(--bg); border-color: var(--ink); font-weight: var(--weight-semibold); }

/* ── Post list transitions ── */
.post-list-container { display: flex; flex-direction: column; }
.post-list-enter-active { transition: opacity .3s var(--ease-out), transform .3s var(--ease-out-expo); }
.post-list-leave-active { transition: opacity .2s var(--ease-out); }
.post-list-enter-from { opacity: 0; transform: translateY(8px); }
.post-list-leave-to { opacity: 0; }
.post-list-move { transition: transform .3s var(--ease-out-expo); }

/* ── Load more ── */
.threads-load-more {
  width: 100%; margin-top: var(--space-3); min-height: 44px;
  font-weight: var(--weight-semibold);
  transition: background .25s var(--ease-out), transform .25s var(--ease-out-expo), box-shadow .25s var(--ease-out);
}
.threads-load-more:hover { transform: translateY(-1px); box-shadow: var(--shadow-xs); }
.threads-load-more:active { transform: scale(.98); transition-duration: .08s; }
.threads-load-more:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
/* Section rhythm — quiet divider between compose and feed */
.type-filter-row + .post-list-container { margin-top: var(--space-1); }



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


/* ── Bookmark momentum cue (bottom-center, clears the right-side FAB) ── */
.bookmark-momentum {
  position: fixed; z-index: var(--z-dropdown);
  bottom: calc(var(--space-6) + env(safe-area-inset-bottom));
  left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-2) var(--space-2) var(--space-4);
  background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-full); box-shadow: var(--shadow-lg);
  max-width: calc(100vw - var(--space-6) * 2);
}
.bm-icon { font-size: 1.05rem; flex-shrink: 0; }
.bm-link {
  background: none; border: none; cursor: pointer; padding: 0;
  color: var(--color-action); font-size: var(--text-sm); font-weight: var(--weight-semibold);
  min-height: 44px; display: inline-flex; align-items: center;
  transition: color .2s var(--ease-out);
}
.bm-link:hover { color: var(--ink); text-decoration: underline; }
.bm-link:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; border-radius: var(--radius-control); }
.bm-dismiss {
  flex-shrink: 0; width: 44px; height: 44px; min-width: 44px; border-radius: var(--radius-full);
  background: none; border: none; cursor: pointer; color: var(--muted);
  font-size: 1.25rem; line-height: 1; display: inline-flex; align-items: center; justify-content: center;
  transition: background .2s var(--ease-out), color .2s var(--ease-out), transform .2s var(--ease-out-expo);
}
.bm-dismiss:hover { background: var(--bg-alt); color: var(--ink); }
.bm-dismiss:active { transform: scale(.9); transition-duration: .08s; }
.bm-dismiss:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
/* Dải "Đã ẩn — Hoàn tác": mượn nguyên hình khối của .bookmark-momentum, chỉ
   thêm câu giải thích ngắn ở giữa. Chỉ 1 trong 2 dải hiện tại một thời điểm. */
.hide-undo { padding-left: var(--space-3); }
.hu-text { font-size: var(--text-sm); color: var(--ink); }
.bm-link:disabled { opacity: .55; cursor: progress; }
.momentum-fade-enter-active { transition: opacity .25s var(--ease-out), transform .25s var(--ease-out-expo); }
.momentum-fade-leave-active { transition: opacity .15s var(--ease-out), transform .15s var(--ease-out); }
.momentum-fade-enter-from { opacity: 0; transform: translate(-50%, 16px); }
.momentum-fade-leave-to { opacity: 0; transform: translate(-50%, 8px); }

/* ── Dark mode ── */
.dark .chip-filter { background: var(--bg-alt); border-color: var(--line); }
.dark .chip-filter.active { background: var(--ink); color: var(--bg); border-color: var(--ink); }
.dark .bookmark-momentum { background: var(--card); border-color: rgba(var(--white-rgb),.1); box-shadow: 0 8px 32px rgba(var(--black-rgb),.5); }
.dark .bm-dismiss:hover { background: rgba(var(--white-rgb),.08); }
.dark .compose-attach:hover { background: rgba(var(--white-rgb),.08); }
.dark .threads-compose { background: rgba(var(--accent-rgb),.06); }
.dark .threads-compose:focus-within { background: rgba(var(--accent-rgb),.1); }
.dark .threads-filter-bar { background: var(--surface-translucent, rgba(var(--black-rgb),.72)); }

/* ── Bạn bè: hoạt động gần đây (tab "Đang theo dõi") ── */

@media (max-width: 820px) {
  .threads-layout { grid-template-columns: 1fr; }
  .threads-sidebar { display: none; }
  .threads-page { max-width: 100%; }
  .threads-feed { padding-inline: var(--space-1); }
  .threads-compose { padding-inline: var(--space-3); }
  .compose-input { min-height: 48px; font-size: var(--text-base); }
  /* --text-sm clamps to ~14px under ~640px viewport — below the 16px iOS auto-zoom
     threshold. Force 16px on mobile only for the two real text inputs that use it
     (community search box, schedule datetime picker); desktop keeps --text-sm as-is. */
  .cd-input { font-size: var(--text-base, 16px); }
}

@media (prefers-reduced-motion: reduce) {
  .img-preview-row { animation: none; }
  .post-list-enter-active,
  .post-list-leave-active,
  .post-list-move,
  .fab-fade-enter-active,
  .fab-fade-leave-active { transition: none; }
  .img-preview-item:hover { transform: none; }
  .compose-attach:hover { transform: none; }
  .compose-attach:active { transform: none; }
  .threads-tab::after { transition: none; }
  .post-type-selector .chip-sm.active { transform: none; }
  .post-type-selector .chip-sm:active { transform: none; }
  .chip-filter:active { transform: none; }
  .threads-load-more:hover { transform: none; }
  .threads-load-more:active { transform: none; }
  .momentum-fade-enter-active,
  .momentum-fade-leave-active { transition: none; }
  .bm-dismiss:active { transform: none; }
  .threads-refresh .spinning { animation: none; }
}
.btn-xs { padding: var(--space-1) var(--space-2h); font-size: .72rem; border-radius: var(--radius-control); }

/* ── Lên lịch đăng bài ── */
.schedule-option { margin-top: var(--space-1); }
.schedule-toggle { display: flex; align-items: center; gap: var(--space-2); cursor: pointer; font-size: var(--text-sm); color: var(--ink); width: fit-content; }
.schedule-picker { margin-top: var(--space-2); display: flex; flex-direction: column; gap: var(--space-1); align-items: flex-start; }
.cd-toggle { appearance: none; width: 40px; height: 22px; background: var(--muted); border-radius: 11px; position: relative; cursor: pointer; transition: background .25s var(--ease-out); flex-shrink: 0; min-height: 44px; padding: 11px 0; box-sizing: content-box; margin: 0; }
.cd-toggle::after { content: ''; position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; background: var(--white, var(--white)); border-radius: 50%; transition: transform .25s var(--ease-out-expo); box-shadow: 0 1px 3px rgba(var(--black-rgb),.15); }
.cd-toggle:checked { background: var(--color-action); }
.cd-toggle:checked::after { transform: translateX(18px); }
.cd-toggle:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.cd-input {
  padding: var(--space-2) var(--space-3); border: 1px solid var(--line); border-radius: var(--radius-surface);
  background: var(--bg-alt); color: var(--ink); font-size: var(--text-sm); font-family: inherit; min-height: 44px;
}
.cd-input:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 1px; border-color: var(--color-focus); box-shadow: 0 0 0 3px rgba(var(--accent-rgb), .15); }
.cd-hint { font-size: var(--text-xs); color: var(--muted); }

@media (prefers-reduced-motion: reduce) {
  .cd-toggle, .cd-toggle::after { transition: none; }
}
</style>
