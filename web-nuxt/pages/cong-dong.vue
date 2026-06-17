<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cộng đồng' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-community">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon">💬</span>
        <div>
          <h1>Cộng đồng</h1>
          <p>Chia sẻ trải nghiệm, đánh giá địa điểm, hỏi đáp và kết nối với những người yêu du lịch miền Tây.</p>
        </div>
      </div>
    </section>

    <div class="feed-layout">
      <div class="feed-main">
        <div v-if="reportEntityId" class="report-entity-card">
          <div>
            <p class="report-kicker">Báo sai dữ liệu</p>
            <h2>{{ reportEntity?.name || reportEntityId }}</h2>
            <p>{{ isLoggedIn ? 'Mô tả ngắn điểm sai để admin kiểm tra nguồn và cập nhật dữ liệu.' : 'Đăng nhập để gửi báo cáo dữ liệu cho admin.' }}</p>
          </div>
          <div v-if="isLoggedIn" class="report-form-inline">
            <div class="report-reasons">
              <button
                v-for="reason in reportReasons"
                :key="reason"
                type="button"
                :class="['chip', { active: reportReason === reason }]"
                @click="reportReason = reason"
              >{{ reason }}</button>
            </div>
            <textarea
              v-model="reportReason"
              class="textarea"
              rows="3"
              placeholder="Ví dụ: địa chỉ sai, thiếu nguồn, tọa độ không đúng, nội dung cần cập nhật…"
            ></textarea>
            <button class="btn btn-primary" :disabled="reportSubmitting || reportReason.trim().length < 5" @click="submitEntityReport">
              {{ reportSubmitting ? 'Đang gửi…' : 'Gửi báo cáo' }}
            </button>
          </div>
        </div>

        <!-- Create post -->
        <div v-if="isLoggedIn" class="create-post">
          <div class="create-post-header"><h3>Chia sẻ trải nghiệm</h3></div>

          <div class="post-type-selector">
            <button
              v-for="pt in postTypes"
              :key="pt.value"
              :class="['chip', { active: newType === pt.value }]"
              @click="newType = pt.value"
            >{{ pt.label }}</button>
          </div>

          <textarea
            v-model="newContent"
            class="textarea"
            :placeholder="typePlaceholder"
            rows="3"
          ></textarea>

          <div v-if="previewImages.length" class="img-preview-row">
            <div v-for="(src, i) in previewImages" :key="i" class="img-preview-item">
              <img :src="src" alt="" />
              <button class="remove" @click="removeImage(i)">&times;</button>
            </div>
          </div>

          <div class="create-post-footer">
            <label class="btn btn-ghost btn-sm create-img-btn">
              📷 Thêm ảnh
              <input
                type="file"
                accept="image/*"
                multiple
                class="sr-only"
                @change="onFileSelect"
              />
            </label>
            <button class="btn btn-primary" :disabled="!canSubmit || posting" @click="submitPost">
              {{ posting ? 'Đang đăng…' : 'Đăng bài' }}
            </button>
          </div>
        </div>

        <div v-else class="create-post create-post-guest">
          <p class="guest-cta">Đăng nhập để chia sẻ trải nghiệm với cộng đồng.</p>
        </div>

        <!-- Filter -->
        <div class="feed-filters">
          <div class="chip-row">
            <button :class="['chip', { active: sort === 'latest' }]" @click="sort = 'latest'">Mới nhất</button>
            <button :class="['chip', { active: sort === 'trending' }]" @click="sort = 'trending'">Nổi bật</button>
          </div>
        </div>

        <!-- Posts -->
        <SkeletonGrid v-if="loading && !posts.length" :count="3" />

        <PostCard
          v-for="post in posts"
          :key="post.id"
          :post="post"
          @like="toggleLike"
          @comment="goToPost"
          @bookmark="toggleBookmark"
          @report="reportPost"
        />

        <div v-if="feedError && !posts.length" class="feed-error">
          <p>Không thể tải bảng tin.</p>
          <button class="btn btn-outline btn-sm" @click="fetchFeed(true)">Thử lại</button>
        </div>
        <EmptyState v-else-if="!posts.length && !loading && !feedError" message="Chưa có bài viết nào. Hãy là người đầu tiên chia sẻ!" />

        <button v-if="hasMore && !loading" class="btn btn-outline feed-load-more" @click="loadMore">
          Xem thêm
        </button>
        <div v-if="loading && posts.length" class="feed-loading"><div class="spinner"></div></div>
      </div>

      <aside class="feed-sidebar">
        <div class="sidebar-card">
          <h3>Về cộng đồng</h3>
          <p>Nơi chia sẻ trải nghiệm du lịch, đánh giá đặc sản và kết nối với cộng đồng yêu Vĩnh Long.</p>
        </div>
        <div class="sidebar-card">
          <h3>Hướng dẫn</h3>
          <ul class="sidebar-list">
            <li>📝 Chia sẻ trải nghiệm du lịch</li>
            <li>⭐ Đánh giá địa điểm, sản phẩm</li>
            <li>❓ Hỏi đáp về Vĩnh Long</li>
            <li>📷 Đăng ảnh kèm bài viết</li>
          </ul>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
useReveal()

const { isLoggedIn, authHeaders } = useAuth()
const route = useRoute()
const router = useRouter()

const { show: showToast } = useToast()
const postTypes = [
  { value: 'share', label: '📸 Chia sẻ' },
  { value: 'review', label: '⭐ Đánh giá' },
  { value: 'question', label: '❓ Hỏi đáp' },
  { value: 'recommend', label: '👍 Gợi ý' },
]

const sort = ref('latest')
const page = ref(1)
const posts = ref<any[]>([])
const hasMore = ref(false)
const loading = ref(false)
const feedError = ref(false)
const newContent = ref('')
const newType = ref('share')
const posting = ref(false)
const imageFiles = ref<File[]>([])
const previewImages = ref<string[]>([])
const reportEntityId = computed(() => String(route.query.report || ''))
const reportEntity = ref<any>(null)
const reportReason = ref('')
const reportSubmitting = ref(false)
const reportReasons = ['Thiếu nguồn xác minh', 'Tọa độ chưa đúng', 'Sai địa chỉ/khu vực', 'Nội dung cần cập nhật']

const typePlaceholder = computed(() => {
  const map: Record<string, string> = {
    share: 'Kể về trải nghiệm du lịch của bạn…',
    review: 'Đánh giá một địa điểm, sản phẩm hoặc trải nghiệm…',
    question: 'Bạn muốn hỏi gì về Vĩnh Long?',
    recommend: 'Gợi ý một địa điểm, món ăn, sản phẩm…',
  }
  return map[newType.value] || map.share
})

const canSubmit = computed(() => newContent.value.trim().length > 0)

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

async function fetchFeed(reset = false) {
  if (reset) { page.value = 1; posts.value = []; feedError.value = false }
  loading.value = true
  try {
    const res = await $fetch<any>(`/api/feed?page=${page.value}&limit=20&sort=${sort.value}`, {
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
    showToast(reset ? 'Không thể tải bảng tin' : 'Không thể tải thêm bài viết', 'error')
  }
  loading.value = false
}

function loadMore() {
  page.value++
  fetchFeed()
}

watch(sort, () => fetchFeed(true))

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
    await fetchFeed(true)
  } catch (e: any) {
    showToast(e.data?.detail || 'Gửi bài thất bại', 'error')
  }
  posting.value = false
}

async function fetchReportEntity() {
  reportEntity.value = null
  if (!reportEntityId.value) return
  try {
    reportEntity.value = await $fetch<any>(`/api/entities/${reportEntityId.value}`)
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
    showToast('Đã gửi báo cáo dữ liệu. Cảm ơn bạn!', 'success')
    reportReason.value = ''
    const nextQuery = { ...route.query }
    delete nextQuery.report
    router.replace({ query: nextQuery })
  } catch (e: any) {
    showToast(e.data?.detail || 'Không thể gửi báo cáo', 'error')
  }
  reportSubmitting.value = false
}

// GĐ5.4 / GĐ13.6f: báo cáo bài đăng vi phạm -> /api/report (admin gỡ trong 24/48h). DRY qua useReport.
const { reportPost } = useReport()

async function toggleLike(postId: string) {
  if (!isLoggedIn.value) return
  try {
    await $fetch(`/api/posts/${postId}/like`, { method: 'POST', headers: authHeaders() })
    const post = posts.value.find(p => p.id === postId)
    if (post) {
      post.user_liked = !post.user_liked
      post.likes = (post.likes || 0) + (post.user_liked ? 1 : -1)
    }
  } catch { /* ignore */ }
}

async function toggleBookmark(postId: string) {
  if (!isLoggedIn.value) return
  try {
    await $fetch(`/api/posts/${postId}/bookmark`, { method: 'POST', headers: authHeaders() })
    const post = posts.value.find(p => p.id === postId)
    if (post) post.user_bookmarked = !post.user_bookmarked
  } catch { /* ignore */ }
}

function goToPost(postId: string) {
  navigateTo(`/bai-viet/${postId}`)
}

watch(reportEntityId, () => fetchReportEntity())

onMounted(() => {
  fetchReportEntity()
  fetchFeed(true)
})

useSeoMeta({
  title: 'Cộng đồng du lịch Vĩnh Long — vinhlong360',
  description: 'Chia sẻ trải nghiệm, đánh giá và kết nối với cộng đồng yêu du lịch Vĩnh Long, Bến Tre, Trà Vinh.',
  ogTitle: 'Cộng đồng — vinhlong360',
  ogDescription: 'Chia sẻ trải nghiệm, đánh giá và kết nối với cộng đồng yêu du lịch miền Tây.',
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
.create-post {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg, 16px);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
  transition: border-color var(--duration-fast), box-shadow var(--duration-normal);
}
.create-post:focus-within {
  border-color: var(--primary-fg);
  box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .08);
}
.create-post-header h3 { margin: 0 0 var(--space-3); font-size: var(--text-base); }
.create-post-footer { display: flex; justify-content: space-between; align-items: center; margin-top: var(--space-3); gap: var(--space-3); }
.create-img-btn { cursor: pointer; }
.post-type-selector { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-3); }
.img-preview-item { position: relative; border-radius: var(--radius-sm); overflow: hidden; }
.img-preview-item img { transition: transform var(--duration-fast); }
.img-preview-item:hover img { transform: scale(1.05); }
.img-preview-item .remove { transition: background var(--duration-fast), transform var(--duration-fast); }
.img-preview-item .remove:hover { background: var(--error); transform: scale(1.1); }

.sidebar-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg, 16px);
  padding: var(--space-4);
  margin-bottom: var(--space-3);
  transition: transform var(--duration-normal) var(--ease-spring), box-shadow var(--duration-normal);
}
.sidebar-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.sidebar-card h3 { margin: 0 0 var(--space-2); font-size: var(--text-sm); font-weight: var(--weight-semibold); }
.sidebar-card p { margin: 0; font-size: var(--text-sm); color: var(--muted); line-height: var(--leading-relaxed); }
.sidebar-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.sidebar-list li { font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); padding: 4px 0; }

.feed-filters { margin-bottom: var(--space-4); }


.report-entity-card {
  display: grid;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--clay-100);
  border-radius: var(--radius-lg, 16px);
  background: var(--clay-50);
  animation: slideDown .3s var(--ease-spring);
}
@keyframes slideDown { from { opacity: 0; transform: translateY(-8px); } }
.report-entity-card h2 { margin: 2px 0 var(--space-1); font-size: var(--text-base); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); }
.report-entity-card p { margin: 0; color: var(--muted); font-size: var(--text-sm); }
.report-kicker { font-size: var(--text-xs); text-transform: uppercase; letter-spacing: .04em; font-weight: var(--weight-extrabold); color: var(--accent-dark); }
.report-form-inline { display: grid; gap: var(--space-3); }
.report-reasons { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.report-form-inline .btn { justify-self: start; }

.guest-cta { margin: 0; color: var(--muted); text-align: center; font-size: var(--text-sm); line-height: var(--leading-relaxed); }
.feed-error { text-align: center; padding: var(--space-5); color: var(--error); }
.feed-error p { margin: 0 0 var(--space-3); }
.feed-load-more { width: 100%; min-height: 44px; transition: transform var(--duration-fast) var(--ease-spring); }
.feed-load-more:active { transform: scale(.97); }
.feed-loading { text-align: center; padding: var(--space-5); }
.feed-loading .spinner { margin: 0 auto; }
.img-preview-row { animation: fadeIn .25s var(--ease-out); }
@keyframes fadeIn { from { opacity: 0; } }
</style>
