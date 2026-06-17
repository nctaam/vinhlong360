<template>
  <div class="reviews-section">
    <div class="reviews-header">
      <h2>Đánh giá cộng đồng</h2>
      <div v-if="rating.count" class="reviews-summary">
        <span class="star-rating-inline">
          <span v-for="s in 5" :key="s" class="star" :class="{ active: s <= Math.round(rating.avg) }">★</span>
        </span>
        <strong>{{ rating.avg }}</strong>
        <span class="review-count">({{ rating.count }} đánh giá)</span>
      </div>
    </div>

    <!-- Review Form -->
    <div v-if="user" class="review-form">
      <div class="rf-rating">
        <span class="rf-label">Đánh giá của bạn:</span>
        <span class="star-rating">
          <span
            v-for="s in 5"
            :key="s"
            class="star"
            :class="{ active: s <= formRating }"
            @click="formRating = s"
          >★</span>
        </span>
      </div>
      <textarea
        v-model="formContent"
        class="input review-textarea"
        rows="3"
        placeholder="Chia sẻ trải nghiệm của bạn (tối thiểu 10 ký tự)…"
      ></textarea>
      <button
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

    <!-- Review List -->
    <div v-if="reviews.length" class="review-list">
      <div v-for="r in reviews" :key="r.id" class="review-item">
        <div class="ri-head">
          <NuxtLink :to="`/nguoi-dung/${r.user_id}`" class="ri-author">
            <img v-if="r.avatar_url" :src="r.avatar_url" class="ri-avatar" :alt="r.display_name" />
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
          <img v-for="(img, i) in r.images" :key="i" :src="img" :alt="`Ảnh đánh giá ${i + 1}`" loading="lazy" />
        </div>
      </div>
    </div>
    <p v-else-if="fetchFailed" class="empty review-error">Không thể tải đánh giá. <button class="btn btn-outline btn-sm review-retry-btn" @click="fetchFailed = false; fetchReviews()">Thử lại</button></p>
    <p v-else-if="!loading" class="empty review-empty">Chưa có đánh giá nào. Hãy là người đầu tiên!</p>

    <!-- Load more -->
    <button v-if="hasMore" class="btn btn-outline review-load-more" @click="loadMore">
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

function timeAgo(dateStr: string) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Vừa xong'
  if (mins < 60) return `${mins} phút trước`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} giờ trước`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days} ngày trước`
  return new Date(dateStr).toLocaleDateString('vi-VN')
}

onMounted(() => fetchReviews())
</script>

<style scoped>
.review-textarea { resize: vertical; }
.review-error { font-size: var(--text-sm); color: var(--error, #D94F3D); }
.review-retry-btn { margin-left: var(--space-2); }
.review-empty { font-size: var(--text-sm); }
.review-load-more { margin-top: var(--space-3); }
</style>
