<template>
  <section class="page threads-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cộng đồng' }]" />
    <h1 class="sr-only">{{ pc('hero_title') }}</h1>

    <div class="threads-layout">
      <div class="threads-feed">

        <!-- Report entity (if from ?report=id) -->
        <div v-if="reportEntityId" class="report-entity-card">
          <div>
            <p class="report-kicker">Báo sai dữ liệu</p>
            <h2>{{ reportEntity?.name || reportEntityId }}</h2>
            <p>{{ isLoggedIn ? 'Mô tả ngắn điểm sai để admin kiểm tra.' : 'Đăng nhập để gửi báo cáo.' }}</p>
          </div>
          <div v-if="isLoggedIn" class="report-form-inline">
            <div class="report-reasons">
              <button type="button"
                v-for="reason in reportReasons"
                :key="reason"
                :class="['chip', { active: reportReason === reason }]"
                :aria-pressed="reportReason === reason"
                @click="reportReason = reason"
              >{{ reason }}</button>
            </div>
            <textarea
              v-model="reportReason"
              class="textarea"
              rows="3"
              placeholder="Ví dụ: địa chỉ sai, thiếu nguồn, tọa độ không đúng…"
              aria-label="Mô tả báo cáo"
            ></textarea>
            <button type="button" class="btn btn-primary" :disabled="reportSubmitting || reportReason.trim().length < 5" @click="submitEntityReport">
              {{ reportSubmitting ? 'Đang gửi…' : 'Gửi báo cáo' }}
            </button>
          </div>
        </div>

        <!-- Create post (Threads style) -->
        <div v-if="isLoggedIn" ref="composeEl" class="threads-compose">
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
              >{{ pt.label }}</button>
            </div>

            <textarea
              ref="composeInputEl"
              v-model="newContent"
              class="compose-input"
              :placeholder="typePlaceholder"
              :maxlength="MAX_CHARS"
              rows="2"
              aria-label="Nội dung bài viết"
              @input="autoGrow"
            ></textarea>

            <div v-if="previewImages.length" class="img-preview-row">
              <div v-for="(src, i) in previewImages" :key="i" class="img-preview-item">
                <img :src="src" alt="Ảnh xem trước" width="120" height="120" loading="lazy" />
                <button type="button" class="remove" aria-label="Xóa ảnh" @click="removeImage(i)">&times;</button>
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
              <button type="button" class="btn btn-primary btn-sm" :disabled="!canSubmit || posting" @click="submitPost">
                {{ posting ? 'Đang đăng…' : 'Đăng' }}
              </button>
            </div>
          </div>
        </div>

        <div v-else class="threads-compose-guest">
          <div class="guest-avatar">
            <span class="avatar thread-avatar guest">?</span>
          </div>
          <div class="guest-content">
            <p>Có trải nghiệm muốn chia sẻ?</p>
            <NuxtLink to="/dang-nhap" class="btn btn-outline btn-sm">Đăng nhập</NuxtLink>
          </div>
        </div>

        <!-- Main tabs -->
        <div class="threads-filter" role="region" aria-label="Bộ lọc bảng tin">
          <button type="button" :class="['threads-tab', { active: activeTab === 'latest' }]" :aria-pressed="activeTab === 'latest'" @click="setTab('latest')">Mới nhất</button>
          <button type="button" :class="['threads-tab', { active: activeTab === 'trending' }]" :aria-pressed="activeTab === 'trending'" @click="setTab('trending')">Nổi bật</button>
          <button type="button" v-if="isLoggedIn" :class="['threads-tab', { active: activeTab === 'bookmarks' }]" :aria-pressed="activeTab === 'bookmarks'" @click="setTab('bookmarks')">
            <svg class="icon-inline" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>Đã lưu
          </button>
        </div>

        <!-- Post type filter (only for feed tabs, not bookmarks) -->
        <div v-if="activeTab !== 'bookmarks'" class="type-filter-row" role="region" aria-label="Lọc loại bài viết">
          <button type="button"
            :class="['chip chip-filter', { active: filterType === '' }]"
            :aria-pressed="filterType === ''"
            @click="filterType = ''"
          >Tất cả</button>
          <button type="button"
            v-for="pt in postTypes"
            :key="pt.value"
            :class="['chip chip-filter', { active: filterType === pt.value }]"
            :aria-pressed="filterType === pt.value"
            @click="filterType = pt.value"
          >{{ pt.label }}</button>
        </div>

        <!-- Posts -->
        <SkeletonGrid v-if="(loading || bookmarksLoading) && !displayPosts.length" :count="3" />

        <TransitionGroup name="post-list" tag="div" class="post-list-container">
          <PostCard
            v-for="post in displayPosts"
            :key="post.id"
            :post="post"
            :has-replies="(post.comments_count || 0) > 0"
            @like="toggleLike"
            @comment="goToPost"
            @bookmark="toggleBookmark"
            @report="reportPost"
          />
        </TransitionGroup>

        <div v-if="feedError && !displayPosts.length" class="feed-error">
          <p>Không thể tải bảng tin.</p>
          <button type="button" class="btn btn-outline btn-sm" @click="fetchFeed(true)">Thử lại</button>
        </div>

        <EmptyState
          v-else-if="activeTab === 'bookmarks' && !bookmarks.length && !bookmarksLoading"
          icon="🔖" title="Chưa lưu bài viết nào"
          message="Nhấn biểu tượng bookmark trên bài viết để lưu lại và xem sau."
        />

        <EmptyState
          v-else-if="activeTab !== 'bookmarks' && !posts.length && !loading && !feedError"
          icon="💬" title="Cộng đồng đang chờ bạn"
          message="Chưa có bài viết nào. Hãy là người đầu tiên chia sẻ!"
          hint="Chia sẻ ảnh chuyến đi, đặt câu hỏi, hay để lại đánh giá của bạn."
        >
          <template v-if="isLoggedIn" #actions>
            <button type="button" class="btn btn-primary btn-sm" @click="focusComposer">Viết bài đầu tiên</button>
          </template>
          <template v-else #actions>
            <NuxtLink to="/dang-nhap" class="btn btn-primary btn-sm">Đăng nhập để chia sẻ</NuxtLink>
          </template>
        </EmptyState>

        <button type="button" v-if="canLoadMore" class="btn btn-ghost threads-load-more" @click="loadMore">
          Xem thêm
        </button>
        <div v-if="(loading && posts.length) || bookmarksLoading" class="feed-loading" role="status" aria-live="polite" aria-label="Đang tải bài viết"><div class="spinner"></div></div>
      </div>

      <aside class="threads-sidebar">
        <div class="sidebar-card sidebar-about">
          <h3>Cộng đồng vinhlong360</h3>
          <p>Nơi chia sẻ trải nghiệm du lịch, đánh giá đặc sản và kết nối với cộng đồng yêu miền Tây.</p>
          <div class="sidebar-stats">
            <div class="sidebar-stat">
              <span class="stat-num">{{ feedStats.postCount }}</span>
              <span class="stat-label">bài viết</span>
            </div>
            <div class="sidebar-stat">
              <span class="stat-num">{{ feedStats.reviewCount }}</span>
              <span class="stat-label">đánh giá</span>
            </div>
          </div>
        </div>

        <div class="sidebar-card">
          <h3>Cách tham gia</h3>
          <ul class="sidebar-list">
            <li>
              <span class="sl-icon">📸</span>
              <div><strong>Chia sẻ</strong><br><span class="sl-desc">Kể lại chuyến đi, khám phá của bạn</span></div>
            </li>
            <li>
              <span class="sl-icon">⭐</span>
              <div><strong>Đánh giá</strong><br><span class="sl-desc">Chấm điểm địa điểm, dịch vụ đã trải nghiệm</span></div>
            </li>
            <li>
              <span class="sl-icon">❓</span>
              <div><strong>Hỏi đáp</strong><br><span class="sl-desc">Đặt câu hỏi về 3 tỉnh VL–BT–TV</span></div>
            </li>
            <li>
              <span class="sl-icon">👍</span>
              <div><strong>Gợi ý</strong><br><span class="sl-desc">Giới thiệu nơi hay, món ngon cho mọi người</span></div>
            </li>
          </ul>
        </div>

        <div class="sidebar-card sidebar-rules">
          <h3>Quy tắc cộng đồng</h3>
          <ol class="sidebar-rules-list">
            <li>Tôn trọng lẫn nhau</li>
            <li>Chia sẻ thông tin chính xác</li>
            <li>Không quảng cáo, spam</li>
            <li>Bảo vệ quyền riêng tư</li>
          </ol>
        </div>
      </aside>
    </div>

    <!-- Scroll to top FAB -->
    <Transition name="fab-fade">
      <button type="button"
        v-if="showScrollTop"
        class="scroll-top-fab"
        aria-label="Lên đầu trang"
        @click="scrollToTop"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="18 15 12 9 6 15"/></svg>
      </button>
    </Transition>
  </section>
</template>

<script setup lang="ts">
import type { Post, Entity} from '~/types'
useReveal()
const { f: pc } = usePageContent('cong_dong')

const MAX_CHARS = 500

const { isLoggedIn, authHeaders, user } = useAuth()
const route = useRoute()
const router = useRouter()

const { show: showToast } = useToast()
const postTypes = [
  { value: 'share', label: '📸 Chia sẻ' },
  { value: 'review', label: '⭐ Đánh giá' },
  { value: 'question', label: '❓ Hỏi đáp' },
  { value: 'recommend', label: '👍 Gợi ý' },
]

const userInitial = computed(() => {
  const name = user.value?.display_name || user.value?.phone || '?'
  return name.charAt(0).toUpperCase()
})

// ── Tabs & filtering ──
const activeTab = ref<'latest' | 'trending' | 'bookmarks'>('latest')
const sort = computed(() => activeTab.value === 'trending' ? 'trending' : 'latest')
const filterType = ref('')
const page = ref(1)
const posts = ref<Entity[]>([])
const hasMore = ref(false)
const loading = ref(false)
const feedError = ref(false)
const newContent = ref('')
const newType = ref('share')
const posting = ref(false)
const imageFiles = ref<File[]>([])
const previewImages = ref<string[]>([])
const charRatio = computed(() => newContent.value.length / MAX_CHARS)

// ── Bookmarks ──
const bookmarks = ref<Entity[]>([])
const bookmarksLoading = ref(false)
const bookmarksPage = ref(1)
const bookmarksHasMore = ref(false)

// ── Feed stats (computed from loaded data) ──
const feedStats = computed(() => {
  const all = posts.value
  return {
    postCount: all.length || '—',
    reviewCount: all.filter(p => p.post_type === 'review').length || '—',
  }
})

// ── Display posts (with type filter) ──
const displayPosts = computed(() => {
  if (activeTab.value === 'bookmarks') return bookmarks.value
  if (!filterType.value) return posts.value
  return posts.value.filter(p => p.post_type === filterType.value)
})

const canLoadMore = computed(() => {
  if (activeTab.value === 'bookmarks') return bookmarksHasMore.value && !bookmarksLoading.value
  return hasMore.value && !loading.value
})

// ── Report entity ──
const reportEntityId = computed(() => String(route.query.report || ''))
const reportEntity = ref<Record<string, unknown> | null>(null)
const reportReason = ref('')
const reportSubmitting = ref(false)
const reportReasons = ['Thiếu nguồn xác minh', 'Tọa độ chưa đúng', 'Sai địa chỉ/khu vực', 'Nội dung cần cập nhật']

const typePlaceholder = computed(() => {
  const map: Record<string, string> = {
    share: 'Kể về trải nghiệm du lịch của bạn…',
    review: 'Đánh giá một địa điểm, sản phẩm…',
    question: 'Bạn muốn hỏi gì về miền Tây?',
    recommend: 'Gợi ý một địa điểm, món ăn…',
  }
  return map[newType.value] || map.share
})

const canSubmit = computed(() => newContent.value.trim().length > 0 && newContent.value.length <= MAX_CHARS)

// ── Scroll-to-top ──
const showScrollTop = ref(false)
function onScroll() {
  showScrollTop.value = window.scrollY > 600
}
function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// ── Composer focus (from empty-state CTA) ──
const composeEl = ref<HTMLElement | null>(null)
const composeInputEl = ref<HTMLTextAreaElement | null>(null)
function focusComposer() {
  const prefersReduced = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  composeEl.value?.scrollIntoView({ behavior: prefersReduced ? 'auto' : 'smooth', block: 'center' })
  nextTick(() => composeInputEl.value?.focus())
}

function autoGrow(e: Event) {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files) return
  const newFiles = Array.from(input.files).slice(0, 5 - imageFiles.value.length)
  for (const file of newFiles) {
    if (file.size > 10 * 1024 * 1024) { showToast('Ảnh quá lớn (tối đa 10MB)', 'warning'); continue }
    imageFiles.value.push(file)
    const reader = new FileReader()
    reader.onload = () => { previewImages.value.push(reader.result as string) }
    reader.onerror = () => { showToast('Không thể đọc ảnh', 'error') }
    reader.readAsDataURL(file)
  }
  input.value = ''
}

function removeImage(idx: number) {
  imageFiles.value.splice(idx, 1)
  previewImages.value.splice(idx, 1)
}

function setTab(tab: 'latest' | 'trending' | 'bookmarks') {
  if (activeTab.value === tab) return
  activeTab.value = tab
  filterType.value = ''
  if (tab === 'bookmarks') {
    if (!bookmarks.value.length) fetchBookmarks(true)
  } else {
    fetchFeed(true)
  }
}

async function fetchFeed(reset = false) {
  if (reset) { page.value = 1; posts.value = []; feedError.value = false }
  loading.value = true
  try {
    const params = new URLSearchParams({
      page: String(page.value),
      limit: '20',
      sort: sort.value,
    })
    if (filterType.value) params.set('post_type', filterType.value)
    const res = await $fetch<{ posts: Post[] }>(`/api/feed?${params}`, {
      headers: authHeaders(),
    })
    const newPosts = res.posts || res || []
    if (reset) {
      posts.value = newPosts
    } else {
      posts.value.push(...newPosts)
    }
    hasMore.value = newPosts.length === 20
  } catch {
    if (reset && !posts.value.length) feedError.value = true
    showToast(reset ? 'Không thể tải bảng tin' : 'Không thể tải thêm', 'error')
  }
  loading.value = false
}

async function fetchBookmarks(reset = false) {
  if (reset) { bookmarksPage.value = 1; bookmarks.value = [] }
  bookmarksLoading.value = true
  try {
    const res = await $fetch<{ bookmarks: Post[] }>(`/api/me/bookmarks?page=${bookmarksPage.value}&limit=20`, {
      headers: authHeaders(),
    })
    const newPosts = res.posts || res || []
    if (reset) {
      bookmarks.value = newPosts
    } else {
      bookmarks.value.push(...newPosts)
    }
    bookmarksHasMore.value = newPosts.length === 20
  } catch {
    showToast('Không thể tải bài viết đã lưu', 'error')
  }
  bookmarksLoading.value = false
}

function loadMore() {
  if (activeTab.value === 'bookmarks') {
    bookmarksPage.value++
    fetchBookmarks()
  } else {
    page.value++
    fetchFeed()
  }
}

watch(filterType, () => {
  if (activeTab.value !== 'bookmarks') fetchFeed(true)
})

async function submitPost() {
  if (!canSubmit.value) return
  posting.value = true
  try {
    const body: Record<string, any> = {
      content: newContent.value.trim(),
      post_type: newType.value,
    }
    if (previewImages.value.length) {
      body.images = previewImages.value
    }
    await $fetch('/api/posts', {
      method: 'POST',
      headers: authHeaders(),
      body,
    })
    newContent.value = ''
    newType.value = 'share'
    imageFiles.value = []
    previewImages.value = []
    showToast('Đã đăng bài viết', 'success')
    activeTab.value = 'latest'
    await fetchFeed(true)
  } catch (e: unknown) {
    showToast(e.data?.detail || 'Gửi bài thất bại', 'error')
  }
  posting.value = false
}

async function fetchReportEntity() {
  reportEntity.value = null
  if (!reportEntityId.value) return
  try {
    reportEntity.value = await $fetch<Entity>(`/api/entities/${reportEntityId.value}`)
    if (!reportReason.value) {
      reportReason.value = reportEntity.value?.quality?.has_source ? 'Nội dung cần cập nhật' : 'Thiếu nguồn xác minh'
    }
  } catch {
    reportEntity.value = { id: reportEntityId.value, name: reportEntityId.value }
  }
}

async function submitEntityReport() {
  if (!isLoggedIn.value || !reportEntityId.value || reportReason.value.trim().length < 5) return
  reportSubmitting.value = true
  try {
    await $fetch('/api/report', {
      method: 'POST',
      headers: authHeaders(),
      body: {
        target_type: 'entity',
        target_id: reportEntityId.value,
        reason: reportReason.value.trim(),
      },
    })
    showToast('Đã gửi báo cáo. Cảm ơn bạn!', 'success')
    reportReason.value = ''
    const nextQuery = { ...route.query }
    delete nextQuery.report
    router.replace({ query: nextQuery })
  } catch (e: unknown) {
    showToast(e.data?.detail || 'Không thể gửi báo cáo', 'error')
  }
  reportSubmitting.value = false
}

const { reportPost } = useReport()

async function toggleLike(postId: string) {
  if (!isLoggedIn.value) {
    showToast('Đăng nhập để thích bài viết', 'info')
    return
  }
  const post = posts.value.find(p => p.id === postId) || bookmarks.value.find(p => p.id === postId)
  if (post) {
    post.user_liked = !post.user_liked
    post.likes = (post.likes || 0) + (post.user_liked ? 1 : -1)
  }
  try {
    await $fetch(`/api/posts/${postId}/like`, { method: 'POST', headers: authHeaders() })
  } catch {
    if (post) {
      post.user_liked = !post.user_liked
      post.likes = (post.likes || 0) + (post.user_liked ? 1 : -1)
    }
    showToast('Không thể thích bài viết', 'error')
  }
}

async function toggleBookmark(postId: string) {
  if (!isLoggedIn.value) {
    showToast('Đăng nhập để lưu bài viết', 'info')
    return
  }
  const post = posts.value.find(p => p.id === postId) || bookmarks.value.find(p => p.id === postId)
  if (post) post.user_bookmarked = !post.user_bookmarked
  try {
    await $fetch(`/api/posts/${postId}/bookmark`, { method: 'POST', headers: authHeaders() })
  } catch {
    if (post) post.user_bookmarked = !post.user_bookmarked
    showToast('Không thể lưu bài viết', 'error')
  }
}

function goToPost(postId: string) {
  navigateTo(`/bai-viet/${postId}`)
}

watch(reportEntityId, () => fetchReportEntity())

onMounted(() => {
  fetchReportEntity()
  fetchFeed(true)
  window.addEventListener('scroll', onScroll, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
})

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/cong-dong') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'Cộng đồng vinhlong360',
      description: 'Bảng tin cộng đồng chia sẻ trải nghiệm du lịch, đánh giá và báo cáo dữ liệu cho Vĩnh Long, Bến Tre, Trà Vinh.',
      url: canonicalUrl('/cong-dong'),
    }),
  }],
})
</script>

<style scoped>
.threads-page { max-width: 960px; margin: 0 auto; }
.threads-layout { display: grid; grid-template-columns: 1fr 280px; gap: var(--space-6); align-items: start; }
.threads-feed { display: flex; flex-direction: column; }

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
.compose-input::placeholder { color: var(--muted); }
.threads-compose {
  transition: background .3s var(--ease-out), border-color .3s var(--ease-out), border-radius .3s var(--ease-out), box-shadow .3s var(--ease-out-expo);
  border-radius: var(--radius-md); margin: 0 calc(var(--space-2) * -1);
  padding: var(--space-5) var(--space-3) var(--space-4);
  background: rgba(var(--accent-rgb), .04);
  border-bottom: none; box-shadow: var(--shadow-xs);
}
.threads-compose:focus-within { background: rgba(var(--accent-rgb), .07); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); }
/* Composer post-type chips — micro feedback on selection (signature) */
.post-type-selector { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.post-type-selector .chip-sm { transition: background .2s, color .2s, border-color .2s, transform .3s var(--ease-spring-gentle); }
.post-type-selector .chip-sm.active { transform: scale(1.04) rotate(-1deg); }
.post-type-selector .chip-sm:active { transform: scale(.95); transition-duration: .08s; }
.compose-footer { display: flex; justify-content: space-between; align-items: center; gap: var(--space-3); padding-top: var(--space-1); }
.compose-footer-left { display: flex; align-items: center; gap: var(--space-3); }
.compose-attach {
  display: inline-flex; align-items: center; justify-content: center;
  width: 44px; height: 44px; min-width: 44px; min-height: 44px; border-radius: var(--radius-full);
  cursor: pointer; color: var(--muted); transition: background .3s var(--ease-out), color .3s var(--ease-out), transform .35s var(--ease-spring-gentle);
}
.compose-attach:hover { background: var(--bg-alt); color: var(--ink); transform: scale(1.08); }
.compose-attach:active { transform: scale(.88); transition-duration: .08s; }
.compose-attach:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.char-count { font-size: var(--text-xs); color: var(--muted); font-variant-numeric: tabular-nums; transition: color .2s; }
.char-count.warn { color: var(--accent-dark); }
.char-count.full { color: var(--error); font-weight: var(--weight-semibold); }
.chip-sm { font-size: var(--text-xs); padding: var(--space-2) 10px; min-height: 44px; display: inline-flex; align-items: center; }

.threads-compose-guest {
  display: flex; gap: var(--space-3); padding: var(--space-4) 0;
  border-bottom: .5px solid var(--line); align-items: center;
}
.guest-avatar { width: 40px; flex-shrink: 0; display: flex; justify-content: center; }
.guest-avatar .avatar.guest { opacity: .5; }
.guest-content { flex: 1; display: flex; align-items: center; gap: var(--space-3); }
.guest-content p { margin: 0; color: var(--muted); font-size: var(--text-sm); flex: 1; }

/* ── Filter tabs ── */
.threads-filter {
  display: flex; border-bottom: .5px solid var(--line);
  margin-top: var(--space-5);
  position: sticky; top: 78px; z-index: 20;
  background: var(--surface-translucent, var(--bg));
  backdrop-filter: var(--glass, saturate(160%) blur(12px));
  -webkit-backdrop-filter: var(--glass, saturate(160%) blur(12px));
}
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
  transform: scaleX(0); transition: transform .3s var(--ease-spring-gentle);
}
.threads-tab:hover { color: var(--ink); }
.threads-tab:hover::after { transform: scaleX(.5); }
.threads-tab:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.threads-tab.active { color: var(--ink); border-bottom-color: transparent; }
.threads-tab.active::after { transform: scaleX(1); }
.dark .threads-tab.active { color: var(--ink); }

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
  white-space: nowrap; min-height: 44px; display: inline-flex; align-items: center;
  transition: background .2s, color .2s, border-color .2s, transform .25s var(--ease-spring-gentle);
}
.chip-filter:hover { border-color: var(--ink); color: var(--ink); }
.chip-filter:active { transform: scale(.95); transition-duration: .08s; }
.chip-filter:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.chip-filter.active { background: var(--ink); color: var(--bg); border-color: var(--ink); font-weight: var(--weight-semibold); }

/* ── Post list transitions ── */
.post-list-container { display: flex; flex-direction: column; }
.post-list-enter-active { transition: opacity .3s var(--ease-out), transform .3s var(--ease-spring-gentle); }
.post-list-leave-active { transition: opacity .2s var(--ease-out); }
.post-list-enter-from { opacity: 0; transform: translateY(8px); }
.post-list-leave-to { opacity: 0; }
.post-list-move { transition: transform .3s var(--ease-spring-gentle); }

/* ── Load more ── */
.threads-load-more {
  width: 100%; margin-top: var(--space-3); min-height: 44px;
  font-weight: var(--weight-semibold);
  transition: background .25s var(--ease-out), transform .25s var(--ease-spring-gentle), box-shadow .25s var(--ease-out);
}
.threads-load-more:hover { transform: translateY(-1px); box-shadow: var(--shadow-xs); }
.threads-load-more:active { transform: scale(.98); transition-duration: .08s; }
.threads-load-more:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
/* Section rhythm — quiet divider between compose and feed */
.type-filter-row + .post-list-container { margin-top: var(--space-1); }

/* ── Sidebar ── */
.threads-sidebar { position: sticky; top: 78px; display: flex; flex-direction: column; gap: var(--space-4); }
.sidebar-card {
  background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-lg); padding: var(--space-4);
  box-shadow: var(--shadow-xs);
  transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out);
}
.sidebar-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--border, var(--ink)); }
.sidebar-card:focus-within { border-color: var(--border, var(--ink)); }
.sidebar-card h3 { margin: 0 0 var(--space-3); font-size: var(--text-sm); font-weight: var(--weight-bold); }
.sidebar-card p { margin: 0; font-size: var(--text-sm); color: var(--muted); line-height: var(--leading-relaxed); }

.sidebar-stats { display: flex; gap: var(--space-4); margin-top: var(--space-3); padding-top: var(--space-3); border-top: .5px solid var(--line); }
.sidebar-stat { display: flex; flex-direction: column; gap: 2px; padding: var(--space-2) var(--space-3); border-radius: var(--radius-sm); transition: background .3s var(--ease-out); cursor: default; }
.sidebar-stat:hover { background: var(--overlay-subtle); }
.stat-num { font-size: var(--text-lg); font-weight: var(--weight-bold); color: var(--ink); font-variant-numeric: tabular-nums; transition: color .3s var(--ease-out); }
.sidebar-stat:hover .stat-num { color: var(--primary-fg); }
.stat-label { font-size: var(--text-xs); color: var(--muted); }

.sidebar-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.sidebar-list li { display: flex; gap: var(--space-3); align-items: flex-start; font-size: var(--text-sm); line-height: var(--leading-snug); padding: var(--space-2); border-radius: var(--radius-sm); transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle); }
.sidebar-list li:hover { background: var(--overlay-subtle); transform: translateX(2px); }
.sl-icon { font-size: var(--text-lg); flex-shrink: 0; width: 24px; text-align: center; transition: transform .3s var(--ease-spring-gentle); }
.sidebar-list li:hover .sl-icon { transform: scale(1.15); }
.sl-desc { font-size: var(--text-xs); color: var(--muted); }
.sidebar-list strong { font-weight: var(--weight-semibold); }

.sidebar-rules-list {
  padding: 0; margin: 0; list-style: none;
  counter-reset: rule-counter;
  font-size: var(--text-sm); color: var(--ink-secondary);
  display: flex; flex-direction: column; gap: var(--space-2);
  line-height: var(--leading-relaxed);
}
.sidebar-rules-list li {
  counter-increment: rule-counter;
  display: flex; align-items: flex-start; gap: var(--space-2);
}
.sidebar-rules-list li::before {
  content: counter(rule-counter);
  flex-shrink: 0;
  width: 20px; height: 20px; border-radius: var(--radius-full);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: var(--text-xs); font-weight: var(--weight-bold);
  background: rgba(var(--accent-rgb), .14); color: var(--accent-dark);
  margin-top: 1px;
}

/* ── Report card ── */
.report-entity-card {
  display: grid; gap: var(--space-3); margin-bottom: 0;
  padding: var(--space-5) var(--space-4) var(--space-4);
  border: .5px solid rgba(var(--accent-rgb), .2); border-radius: var(--radius-lg);
  background: rgba(var(--accent-rgb), .06); box-shadow: var(--shadow-xs);
  animation: slideDown .35s var(--ease-spring-gentle);
  transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo);
}
.report-entity-card:focus-within { border-color: var(--accent-dark); box-shadow: 0 0 0 4px rgba(var(--accent-rgb), .1), var(--shadow-sm); }
.report-entity-card:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
@keyframes slideDown { from { opacity: 0; transform: translateY(-8px) scale(.99); } }
.report-entity-card h2 { margin: 2px 0 var(--space-1); font-size: var(--text-base); font-weight: var(--weight-semibold); }
.report-entity-card p { margin: 0; color: var(--muted); font-size: var(--text-sm); }
.report-kicker { font-size: var(--text-xs); text-transform: uppercase; letter-spacing: .04em; font-weight: var(--weight-extrabold); color: var(--accent-dark); }
.report-form-inline { display: grid; gap: var(--space-3); }
.report-reasons { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.report-form-inline .btn { justify-self: start; }

.img-preview-row { display: flex; gap: var(--space-2); flex-wrap: wrap; animation: fadeIn .25s var(--ease-out); }
.img-preview-item { position: relative; width: 64px; height: 64px; border-radius: var(--radius-sm); overflow: hidden; transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out); }
.img-preview-item:hover { transform: scale(1.08); box-shadow: var(--shadow-sm); }
.img-preview-item img { width: 100%; height: 100%; object-fit: cover; }
.img-preview-item .remove { position: absolute; top: 2px; right: 2px; width: 20px; height: 20px; border-radius: 50%; background: var(--overlay-dark); color: var(--text-on-dark, #fff); border: none; cursor: pointer; font-size: .7rem; display: flex; align-items: center; justify-content: center; transition: background .2s, transform .25s var(--ease-spring-gentle); }
.img-preview-item .remove:hover { background: var(--error); transform: scale(1.1); }
.img-preview-item .remove:focus-visible { outline: 2px solid var(--text-on-dark, #fff); outline-offset: 1px; }
@keyframes fadeIn { from { opacity: 0; } }

.feed-error { text-align: center; padding: var(--space-5); color: var(--error); }
.feed-error p { margin: 0 0 var(--space-3); }
.feed-loading { text-align: center; padding: var(--space-5); }
.feed-loading .spinner { margin: 0 auto; }

/* ── Scroll to top FAB ── */
.scroll-top-fab {
  position: fixed; bottom: var(--space-6); right: var(--space-6); z-index: 50;
  width: 48px; height: 48px; border-radius: var(--radius-full);
  background: var(--card); border: .5px solid var(--line);
  box-shadow: var(--shadow-lg); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: var(--ink); transition: transform .25s var(--ease-spring-gentle), box-shadow .2s;
}
.scroll-top-fab:hover { transform: translateY(-2px); box-shadow: var(--shadow-xl, 0 12px 40px rgba(0,0,0,.15)); }
.scroll-top-fab:active { transform: scale(.9); transition-duration: .08s; }
.scroll-top-fab:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.fab-fade-enter-active { transition: opacity .25s var(--ease-out), transform .3s var(--ease-spring-gentle); }
.fab-fade-leave-active { transition: opacity .15s var(--ease-out), transform .15s var(--ease-out); }
.fab-fade-enter-from { opacity: 0; transform: translateY(16px) scale(.8); }
.fab-fade-leave-to { opacity: 0; transform: translateY(8px) scale(.9); }

/* ── Dark mode ── */
.dark .sidebar-card { background: var(--card); border-color: var(--line); }
.dark .sidebar-card:hover { box-shadow: var(--shadow-sm); border-color: rgba(255,255,255,.14); }
.dark .chip-filter { background: var(--bg-alt); border-color: var(--line); }
.dark .chip-filter.active { background: var(--ink); color: var(--bg); border-color: var(--ink); }
.dark .scroll-top-fab { background: var(--card); border-color: rgba(255,255,255,.1); box-shadow: 0 8px 32px rgba(0,0,0,.5); }
.dark .sidebar-stat:hover { background: rgba(255,255,255,.03); }
.dark .sidebar-list li:hover { background: rgba(255,255,255,.03); }
.dark .report-entity-card { background: rgba(232,163,61,.08); border-color: rgba(232,163,61,.22); }
.dark .compose-attach:hover { background: rgba(255,255,255,.08); }
.dark .threads-compose { background: rgba(232,163,61,.06); }
.dark .threads-compose:focus-within { background: rgba(232,163,61,.1); }
.dark .threads-filter { background: var(--surface-translucent, rgba(0,0,0,.72)); }
.dark .sidebar-rules-list li::before { background: rgba(232,163,61,.2); color: var(--accent); }

@media (max-width: 820px) {
  .threads-layout { grid-template-columns: 1fr; }
  .threads-sidebar { display: none; }
  .threads-page { max-width: 100%; }
  .threads-feed { padding-inline: var(--space-1); }
  .threads-compose { padding-inline: var(--space-3); }
  .scroll-top-fab { bottom: var(--space-4); right: var(--space-4); }
}

@media (prefers-reduced-motion: reduce) {
  .report-entity-card { animation: none; }
  .img-preview-row { animation: none; }
  .post-list-enter-active,
  .post-list-leave-active,
  .post-list-move,
  .fab-fade-enter-active,
  .fab-fade-leave-active { transition: none; }
  .sidebar-card { transition: none; }
  .sidebar-card:hover { transform: none; }
  .sidebar-list li:hover { transform: none; }
  .sidebar-list li:hover .sl-icon { transform: none; }
  .img-preview-item:hover { transform: none; }
  .compose-attach:hover { transform: none; }
  .compose-attach:active { transform: none; }
  .threads-tab::after { transition: none; }
  .post-type-selector .chip-sm.active { transform: none; }
  .post-type-selector .chip-sm:active { transform: none; }
  .chip-filter:active { transform: none; }
  .threads-load-more:hover { transform: none; }
  .threads-load-more:active { transform: none; }
  .scroll-top-fab:hover { transform: none; }
  .scroll-top-fab:active { transform: none; }
}
</style>
