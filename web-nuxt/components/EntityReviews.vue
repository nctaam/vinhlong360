<template>
  <div class="reviews-section">
    <div class="reviews-header">
      <h2>Đánh giá cộng đồng</h2>
      <div v-if="rating.count" class="reviews-summary">
        <span class="star-rating-inline" role="img" :aria-label="`${rating.avg} trên 5 sao`">
          <span v-for="s in 5" :key="s" class="star" :class="{ active: s <= Math.round(rating.avg) }" aria-hidden="true">★</span>
        </span>
        <strong>{{ rating.avg }}</strong>
        <span class="review-count">({{ rating.count }} đánh giá)</span>
      </div>
    </div>

    <!-- Review Form -->
    <div v-if="user" class="review-form">
      <div class="rf-rating">
        <span class="rf-label">Đánh giá của bạn:</span>
        <span class="star-rating" role="radiogroup" aria-label="Số sao đánh giá">
          <button
            v-for="s in 5"
            :key="s"
            type="button"
            class="star"
            :class="{ active: s <= formRating }"
            role="radio"
            :aria-checked="s === formRating"
            :aria-label="`${s} sao`"
            @click="formRating = s"
            @keydown.arrow-right.prevent="formRating = Math.min(5, (formRating || 0) + 1)"
            @keydown.arrow-left.prevent="formRating = Math.max(1, (formRating || 2) - 1)"
          >★</button>
        </span>
      </div>
      <textarea
        v-model="formContent"
        class="input review-textarea"
        rows="3"
        aria-label="Viết đánh giá"
        placeholder="Chia sẻ trải nghiệm của bạn (tối thiểu 10 ký tự)…"
      ></textarea>
      <button type="button"
        class="btn btn-primary"
        :disabled="submitting || formRating === 0 || formContent.trim().length < 10"
        @click="submitReview"
      >
        {{ submitting ? 'Đang gửi…' : 'Gửi đánh giá' }}
      </button>
      <p v-if="submitError" class="rf-error">{{ submitError }}</p>
    </div>
    <p v-else class="review-login-hint">
      Đăng nhập (nút phía trên) để viết đánh giá.
    </p>

    <!-- Loading state -->
    <div v-if="loading && !reviews.length" class="review-loading" role="status" aria-label="Đang tải đánh giá">
      <div v-for="i in 3" :key="i" class="review-skeleton">
        <div class="rsk-head"><div class="rsk-avatar"></div><div class="rsk-name"></div></div>
        <div class="rsk-line"></div>
        <div class="rsk-line short"></div>
      </div>
    </div>

    <!-- Review List -->
    <div v-if="reviews.length" class="review-list">
      <div v-for="r in reviews" :key="r.id" class="review-item">
        <div class="ri-head">
          <NuxtLink :to="`/nguoi-dung/${r.user_id}`" class="ri-author">
            <img v-if="r.avatar_url" :src="r.avatar_url" class="ri-avatar" :alt="r.display_name" loading="lazy" decoding="async" width="32" height="32" @error="(e) => ((e.target as HTMLImageElement).style.display = 'none')" />
            <span v-else class="ri-avatar-placeholder">{{ (r.display_name || '?')[0] }}</span>
            <strong>{{ r.display_name || 'Ẩn danh' }}</strong>
          </NuxtLink>
          <span v-if="r.rating" class="star-rating-inline">
            <span v-for="s in 5" :key="s" class="star" :class="{ active: s <= r.rating }">★</span>
          </span>
          <time class="ri-date" :datetime="r.created_at">{{ timeAgo(r.created_at) }}</time>
        </div>
        <p class="ri-content">{{ r.content }}</p>
        <div v-if="r.images?.length" class="ri-images">
          <img v-for="(img, i) in r.images" :key="i" :src="img" :alt="`Ảnh đánh giá ${i + 1}`" loading="lazy" decoding="async" width="200" height="200" @error="(e) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
        </div>
      </div>
    </div>
    <p v-else-if="fetchFailed" class="empty review-error">Không thể tải đánh giá. <button type="button" class="btn btn-outline btn-sm review-retry-btn" @click="fetchFailed = false; fetchReviews()">Thử lại</button></p>
    <p v-else-if="!loading" class="empty review-empty">Chưa có đánh giá nào. Hãy là người đầu tiên!</p>

    <!-- Load more -->
    <button type="button" v-if="hasMore" class="btn btn-outline review-load-more" @click="loadMore">
      Xem thêm đánh giá
    </button>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  entityId: string
  entityName?: string
}>()

const { user, authHeaders } = useAuth()

const reviews = ref<any[]>([])
const rating = ref({ avg: 0, count: 0 })
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const fetchFailed = ref(false)
const formRating = ref(0)
const formContent = ref('')
const submitting = ref(false)
const submitError = ref('')

const hasMore = computed(() => reviews.value.length < total.value)

async function fetchReviews(append = false) {
  loading.value = true
  try {
    const res = await $fetch<any>(`/api/entities/${props.entityId}/feed?page=${page.value}&limit=10`)
    if (append) {
      reviews.value.push(...(res.posts || []))
    } else {
      reviews.value = res.posts || []
    }
    rating.value = res.rating || { avg: 0, count: 0 }
    total.value = res.total || 0
  } catch { fetchFailed.value = true }
  loading.value = false
}

function loadMore() {
  page.value++
  fetchReviews(true)
}

async function submitReview() {
  submitting.value = true
  submitError.value = ''
  try {
    await $fetch('/api/posts', {
      method: 'POST',
      headers: authHeaders(),
      body: {
        content: formContent.value.trim(),
        entity_id: props.entityId,
        post_type: 'review',
        rating: formRating.value,
      },
    })
    formContent.value = ''
    formRating.value = 0
    page.value = 1
    await fetchReviews()
  } catch (e: any) {
    submitError.value = e.data?.detail || e.message || 'Gửi thất bại'
  }
  submitting.value = false
}

const { timeAgo } = useTimeAgo()

onMounted(() => fetchReviews())
</script>

<style scoped>
.review-textarea { resize: vertical; }
.review-error { font-size: var(--text-sm); color: var(--error, #D94F3D); }
.review-retry-btn { margin-inline-start: var(--space-2); }
.review-empty { font-size: var(--text-sm); }
.review-load-more { margin-top: var(--space-3); }

.review-loading { display: flex; flex-direction: column; gap: var(--space-4); }
.review-skeleton { padding: var(--space-4); border-radius: var(--radius-md); background: var(--card); border: .5px solid var(--line); }
.rsk-head { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-3); }
.rsk-avatar { width: 32px; height: 32px; border-radius: var(--radius-full); background: var(--bg-warm); animation: rskShimmer 1.5s infinite; }
.rsk-name { width: 100px; height: 14px; border-radius: var(--radius-sm); background: var(--bg-warm); animation: rskShimmer 1.5s infinite; }
.rsk-line { width: 100%; height: 12px; border-radius: var(--radius-sm); background: var(--bg-warm); margin-bottom: var(--space-2); animation: rskShimmer 1.5s infinite; }
.rsk-line.short { width: 60%; }
@keyframes rskShimmer {
  0%, 100% { opacity: .6; }
  50% { opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  .rsk-avatar, .rsk-name, .rsk-line { animation: none; }
}
</style>
