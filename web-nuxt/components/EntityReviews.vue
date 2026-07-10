<template>
  <div class="reviews-section">
    <ReviewStats :rating="rating" :reviews="reviews" v-model:selected-mentions="selectedMentions" />

    <!-- Review Form -->
    <div v-if="user" class="review-form">
      <div class="rf-rating">
        <span class="rf-label">Đánh giá của bạn:</span>
        <span class="star-rating" role="radiogroup" aria-label="Số sao đánh giá" @mouseleave="hoverRating = 0">
          <button
            v-for="s in 5"
            :key="s"
            type="button"
            class="star"
            :class="{ active: s <= (hoverRating || formRating) }"
            role="radio"
            :aria-checked="s === formRating"
            :aria-label="`${s} sao`"
            @click="formRating = s"
            @mouseenter="hoverRating = s"
            @focus="hoverRating = s"
            @blur="hoverRating = 0"
            @keydown.arrow-right.prevent="formRating = Math.min(5, (formRating || 0) + 1)"
            @keydown.arrow-left.prevent="formRating = Math.max(1, (formRating || 2) - 1)"
          >★</button>
          <span v-if="hoverRating || formRating" class="rf-rating-hint" aria-hidden="true">{{ hoverRating || formRating }}/5</span>
        </span>
      </div>
      <textarea
        v-model="formContent"
        class="input review-textarea"
        rows="3"
        aria-label="Viết đánh giá"
        placeholder="Chia sẻ trải nghiệm của bạn (tối thiểu 10 ký tự)…"
      ></textarea>

      <!-- Image attach -->
      <p v-if="!formImages.length" class="rf-photo-hint"><IconLine name="camera" class="rf-photo-icon" /> Thêm ảnh thật để giúp cộng đồng + nhận huy hiệu <strong>Nhiếp ảnh</strong></p>
      <div class="rf-images">
        <div v-if="formImages.length" class="rf-image-grid">
          <div v-for="(img, i) in formImages" :key="img" class="rf-image-thumb">
            <img :src="img" :alt="`Ảnh đính kèm ${i + 1}`" loading="lazy" decoding="async" width="64" height="64" @error="(e: Event) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
            <button type="button" class="rf-image-remove" :aria-label="`Xóa ảnh ${i + 1}`" @click="removeImage(i)">×</button>
          </div>
        </div>
        <label class="rf-image-add" :class="{ disabled: uploadingImage || formImages.length >= 4 }">
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            class="rf-image-input"
            :disabled="uploadingImage || formImages.length >= 4"
            @change="onPickImage"
          />
          <span>{{ uploadingImage ? 'Đang tải ảnh…' : (formImages.length >= 4 ? 'Tối đa 4 ảnh' : '+ Thêm ảnh') }}</span>
        </label>
        <p v-if="uploadError" class="rf-error" role="alert">{{ uploadError }}</p>
      </div>

      <button type="button"
        class="btn btn-primary"
        :disabled="submitting || uploadingImage || formRating === 0 || formContent.trim().length < 10"
        @click="submitReview"
      >
        {{ submitting ? 'Đang gửi…' : 'Gửi đánh giá' }}
      </button>
      <p v-if="submitError" class="rf-error" role="alert">{{ submitError }}</p>
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
      <ReviewCard
        v-for="r in filteredReviews"
        :key="r.id"
        :review="r"
        :owned="isOwner(r)"
        :featured="r.id === featuredId"
        :deleting="deletingId === r.id"
        :delete-error="deleteErrorId === r.id ? deleteError : ''"
        @delete="deleteReview"
        @toggle-helpful="toggleHelpful"
      />
    </div>
    <p v-else-if="fetchFailed" class="empty review-error">Không thể tải đánh giá. <button type="button" class="btn btn-outline btn-sm review-retry-btn" @click="fetchFailed = false; fetchReviews()">Thử lại</button></p>
    <p v-else-if="!loading" class="empty review-empty">Chưa có đánh giá nào. Hãy là người đầu tiên!</p>

    <!-- Auto-load more on scroll -->
    <div v-if="hasMore" ref="sentinel" class="review-sentinel">
      <div v-if="infiniteLoading" class="spinner spinner-sm" role="status" aria-label="Đang tải thêm đánh giá"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Review, ReviewFeedResponse } from '~/types'

const props = defineProps<{
  entityId: string
  entityName?: string
}>()

const { user, authHeaders, handleSessionExpired } = useAuth()
const { confirmDialog } = useConfirm()
const { openAuth } = useAuthModal()

const reviews = ref<Review[]>([])
const rating = ref({ avg: 0, count: 0 })
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const fetchFailed = ref(false)
const formRating = ref(0)
const hoverRating = ref(0)
const formContent = ref('')
const submitting = ref(false)
const submitError = ref('')
const deleteError = ref('')
const deleteErrorId = ref('')
const selectedMentions = ref<string[]>([])

const formImages = ref<string[]>([])
const uploadingImage = ref(false)
const uploadError = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

const deletingId = ref<string | number | null>(null)
const helpfulPending = reactive(new Set<string>())
const encodedEntityId = computed(() => encodePathId(props.entityId))

const hasMore = computed(() => reviews.value.length < total.value)

const featuredId = computed(() => {
  if (reviews.value.length < 3) return null
  const [first, ...rest] = reviews.value
  if (!first) return null
  const best = rest.reduce((a, b) => ((b.likes || 0) > (a.likes || 0) ? b : a), first)
  return (best.likes || 0) >= 2 ? best.id : null
})

const filteredReviews = computed(() => {
  if (!selectedMentions.value.length) return reviews.value
  return reviews.value.filter(r => {
    const text = (r.content || '').toLowerCase()
    return selectedMentions.value.every(m => text.includes(m))
  })
})

function isOwner(r: Review) {
  const uid = (r as unknown as { user_id?: string | number }).user_id
  return !!user.value && uid != null && String(uid) === String(user.value.id)
}

async function toggleHelpful(r: Review) {
  if (!user.value) { openAuth(() => toggleHelpful(r)); return }
  const reviewId = encodePathId(r.id)
  if (!reviewId || helpfulPending.has(reviewId)) return
  helpfulPending.add(reviewId)
  const previous = { user_liked: r.user_liked, likes: r.likes }
  r.user_liked = !r.user_liked
  r.likes = Math.max(0, (r.likes || 0) + (r.user_liked ? 1 : -1))
  try {
    await $fetch(`/api/posts/${reviewId}/like`, { method: 'POST', headers: authHeaders() })
  } catch (e: unknown) {
    r.user_liked = previous.user_liked
    r.likes = previous.likes
    if (getStatusCode(e) === 401) handleSessionExpired()
  } finally {
    helpfulPending.delete(reviewId)
  }
}

async function onPickImage(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploadError.value = ''
  if (!file.type.startsWith('image/')) {
    uploadError.value = 'Chỉ chấp nhận file ảnh'
    input.value = ''
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    uploadError.value = 'Ảnh tối đa 5MB'
    input.value = ''
    return
  }
  uploadingImage.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await $fetch<{ url: string }>('/api/upload/image', {
      method: 'POST',
      headers: authHeaders(),
      body: fd,
    })
    if (res.url) formImages.value.push(res.url)
  } catch (err: unknown) {
    if (getStatusCode(err) === 401) {
      handleSessionExpired()
      return
    }
    const e = err as { data?: { detail?: string }; message?: string }
    uploadError.value = e.data?.detail || e.message || 'Tải ảnh thất bại'
  } finally {
    uploadingImage.value = false
    input.value = ''
  }
}

function removeImage(i: number) {
  formImages.value.splice(i, 1)
}

async function deleteReview(r: Review) {
  if (!isOwner(r)) return
  if (!await confirmDialog('Xóa đánh giá này?', { danger: true, confirmText: 'Xóa' })) return
  deletingId.value = r.id
  deleteError.value = ''
  deleteErrorId.value = ''
  const reviewId = encodePathId(r.id)
  if (!reviewId) {
    deletingId.value = null
    return
  }
  try {
    await $fetch(`/api/posts/${reviewId}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    page.value = 1
    await fetchReviews()
  } catch (err: unknown) {
    if (getStatusCode(err) === 401) {
      handleSessionExpired()
      return
    }
    const e = err as { data?: { detail?: string }; message?: string }
    deleteError.value = e.data?.detail || e.message || 'Xóa thất bại'
    deleteErrorId.value = r.id
  } finally {
    deletingId.value = null
  }
}

async function fetchReviews(append = false) {
  loading.value = true
  fetchFailed.value = false
  try {
    const params = new URLSearchParams({ page: String(page.value), limit: '10' })
    const res = await $fetch<ReviewFeedResponse>(`/api/entities/${encodedEntityId.value}/feed?${params}`)
    if (append) {
      const seen = new Set(reviews.value.map(r => String(r.id)))
      reviews.value.push(...(res.posts || []).filter(r => !seen.has(String(r.id))))
    } else {
      reviews.value = res.posts || []
    }
    rating.value = res.rating || { avg: 0, count: 0 }
    total.value = res.total || 0
  } catch { fetchFailed.value = true }
  finally { loading.value = false }
}

function loadMore() {
  if (loading.value || !hasMore.value) return
  page.value++
  fetchReviews(true)
}

const { sentinel, loading: infiniteLoading } = useInfiniteScroll(loadMore, { enabled: hasMore })

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
        images: formImages.value,
      },
    })
    formContent.value = ''
    formRating.value = 0
    formImages.value = []
    page.value = 1
    await fetchReviews()
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) {
      handleSessionExpired()
      return
    }
    submitError.value = extractErrorMessage(e, 'Gửi thất bại')
  } finally {
    submitting.value = false
  }
}

onMounted(() => fetchReviews())
</script>

<style scoped>
.rf-rating-hint { font-size: var(--text-sm); color: var(--muted); font-weight: var(--weight-semibold); margin-inline-start: var(--space-2); align-self: center; font-variant-numeric: tabular-nums; }
.review-textarea { resize: vertical; }
.review-error { font-size: var(--text-sm); color: var(--error, #D94F3D); }
.review-retry-btn { margin-inline-start: var(--space-2); }
.review-empty { font-size: var(--text-sm); }
.review-sentinel { display: flex; justify-content: center; padding: var(--space-3) 0; min-height: 40px; }

.rf-photo-hint { margin: var(--space-2) 0 0; font-size: var(--text-sm); color: var(--ink-700); }
/* emoji lives in a small designed chip, never bare beside serif text (anti-slop) */
.rf-photo-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.4em; height: 1.4em; margin-inline-end: var(--space-1);
  border-radius: var(--radius-sm); background: var(--bg-warm, var(--bg-alt));
  font-size: .85em; vertical-align: -0.25em;
}
.dark .rf-photo-icon { background: rgba(255, 255, 255, .06); }
.rf-images { display: flex; flex-direction: column; gap: var(--space-2); margin-block: var(--space-2); }
.rf-image-grid { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.rf-image-thumb { position: relative; width: 64px; height: 64px; border-radius: var(--radius-md); overflow: hidden; border: .5px solid var(--line); }
.rf-image-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.rf-image-remove {
  position: absolute; top: 2px; inset-inline-end: 2px;
  width: 20px; height: 20px; line-height: 1;
  display: inline-flex; align-items: center; justify-content: center;
  border: none; border-radius: var(--radius-full);
  background: rgba(0, 0, 0, .6); color: var(--text-on-dark, var(--white)); font-size: var(--text-sm);
  cursor: pointer; padding: 0;
  transition: background .15s var(--ease-soft);
}
.rf-image-remove:hover { background: rgba(0, 0, 0, .8); }
.rf-image-remove:focus-visible { outline: 2px solid var(--brand, currentColor); outline-offset: 1px; }
.rf-image-add {
  display: inline-flex; align-items: center; gap: var(--space-2);
  min-height: 44px; padding-inline: var(--space-3);
  border: 1px dashed var(--line); border-radius: var(--radius-md);
  font-size: var(--text-sm); color: var(--muted); cursor: pointer; align-self: flex-start;
  transition: border-color .15s var(--ease-soft), color .15s var(--ease-soft);
}
.rf-image-add:hover { border-color: var(--brand, var(--muted)); color: var(--ink, var(--muted)); }
.rf-image-add:focus-within { outline: 2px solid var(--brand, currentColor); outline-offset: 2px; }
.rf-image-add.disabled { opacity: .55; cursor: not-allowed; }
.rf-image-input { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
.rf-error { font-size: var(--text-sm); color: var(--error, #D94F3D); margin-top: var(--space-1); }

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

<style>
.reviews-section { margin-top: var(--space-8); }
.reviews-header { display: flex; align-items: baseline; gap: var(--space-3); flex-wrap: wrap; margin-bottom: var(--space-4); }
.reviews-header h2 { font-size: var(--text-xl); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); margin: 0; }
.reviews-summary { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-sm); }
.review-count { color: var(--muted); }

.review-form {
  background: var(--season-tint, rgba(185, 219, 198, .04));
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: var(--space-5);
  margin-bottom: var(--space-5);
  box-shadow: 0 0 0 1px rgba(var(--secondary-rgb), .08);
}
.rf-rating { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-3); }
.rf-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--muted); }
.review-form .btn { margin-top: var(--space-2); }
.review-login-hint { font-size: var(--text-sm); color: var(--muted); margin-bottom: var(--space-4); }
.review-login-hint a { color: var(--primary-fg); font-weight: var(--weight-semibold); }

.review-form { transition: border-color .35s var(--ease-out), box-shadow .35s var(--ease-out-expo); }
.review-form:focus-within { border-color: var(--primary-fg); box-shadow: 0 0 0 4px rgba(var(--primary-rgb), .12), var(--shadow-sm); }
.review-form .btn:active { transform: scale(.95); transition-duration: .08s; }

.review-list { display: flex; flex-direction: column; gap: var(--space-4); }
.review-item { border-bottom: .5px solid var(--line); padding: var(--space-3) var(--space-3) var(--space-4); margin: 0 calc(var(--space-3) * -1); transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle); border-radius: var(--radius-sm); }
.review-item:hover { background: var(--overlay-subtle); transform: translateX(2px); }
.review-item:last-child { border-bottom: none; }
.ri-head { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; margin-bottom: var(--space-2); }
.ri-author { display: flex; align-items: center; gap: var(--space-2); text-decoration: none; color: inherit; min-height: 44px; }
.ri-author strong { font-size: var(--text-sm); font-weight: var(--weight-semibold); font-family: var(--font-editorial); }
.ri-avatar { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; }
.ri-avatar-placeholder { width: 32px; height: 32px; border-radius: 50%; background: var(--secondary); color: var(--text-on-dark, var(--white)); display: flex; align-items: center; justify-content: center; font-weight: var(--weight-bold); font-size: var(--text-sm); }
.ri-date { font-size: var(--text-xs); color: var(--muted); margin-inline-start: auto; }
.ri-content { margin: 0; font-size: var(--text-sm); line-height: var(--leading-relaxed); }
.ri-images { display: flex; gap: var(--space-2); margin-top: var(--space-2); overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: none; scroll-snap-type: x proximity; overscroll-behavior-x: contain; }
.ri-images::-webkit-scrollbar { display: none; }
.ri-images img { width: 120px; height: 90px; object-fit: cover; border-radius: var(--radius-sm); flex-shrink: 0; cursor: pointer; scroll-snap-align: start; transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out); }
.ri-images img:hover { transform: scale(var(--img-hover-scale)); box-shadow: var(--shadow-md); }
.ri-images img:active { transform: scale(.96); transition-duration: .08s; }
@media (prefers-reduced-motion: reduce) {
  .ri-images img:hover { transform: none; }
  .review-item:hover { transform: none; }
}
@media (max-width: 768px) {
  .reviews-header { flex-direction: column; gap: var(--space-1); }
  .ri-date { margin-inline-start: 0; }
}
.dark .review-form {
  background: var(--season-tint, rgba(75, 169, 125, .04));
  border-color: rgba(255, 255, 255, .06);
}
.dark .review-form:focus-within { box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .15); }
.dark .review-item:hover { background: rgba(255,255,255,.03); }
.dark .ri-avatar-placeholder { background: rgba(var(--primary-rgb), .3); }
</style>
