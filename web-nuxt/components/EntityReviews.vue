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
      <div class="rf-images">
        <div v-if="formImages.length" class="rf-image-grid">
          <div v-for="(img, i) in formImages" :key="img" class="rf-image-thumb">
            <img :src="img" :alt="`Ảnh đính kèm ${i + 1}`" loading="lazy" decoding="async" width="64" height="64" />
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
        <p v-if="uploadError" class="rf-error">{{ uploadError }}</p>
      </div>

      <button type="button"
        class="btn btn-primary"
        :disabled="submitting || uploadingImage || formRating === 0 || formContent.trim().length < 10"
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
          <div v-if="isOwner(r)" class="ri-actions">
            <button
              type="button"
              class="ri-action-btn ri-delete"
              :disabled="deletingId === r.id"
              :aria-label="`Xóa đánh giá của bạn`"
              @click="deleteReview(r)"
            >{{ deletingId === r.id ? 'Đang xóa…' : 'Xóa' }}</button>
            <span v-if="deleteErrorId === r.id" class="rf-error" role="alert">{{ deleteError }}</span>
          </div>
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
import type { Entity } from '~/types'
const props = defineProps<{
  entityId: string
  entityName?: string
}>()

const { user, authHeaders } = useAuth()

const reviews = ref<Entity[]>([])
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

// Image attach state
const formImages = ref<string[]>([])
const uploadingImage = ref(false)
const uploadError = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

// Own-review actions
const deletingId = ref<string | number | null>(null)

const hasMore = computed(() => reviews.value.length < total.value)

function isOwner(r: Entity) {
  const uid = (r as unknown as { user_id?: string | number }).user_id
  return !!user.value && uid != null && String(uid) === String(user.value.id)
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
    const e = err as { data?: { detail?: string }; message?: string }
    uploadError.value = e.data?.detail || e.message || 'Tải ảnh thất bại'
  }
  uploadingImage.value = false
  input.value = ''
}

function removeImage(i: number) {
  formImages.value.splice(i, 1)
}

async function deleteReview(r: Entity) {
  if (!isOwner(r)) return
  if (!confirm('Xóa đánh giá này?')) return
  deletingId.value = r.id
  deleteError.value = ''
  deleteErrorId.value = ''
  try {
    await $fetch(`/api/posts/${r.id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    page.value = 1
    await fetchReviews()
  } catch (err: unknown) {
    const e = err as { data?: { detail?: string }; message?: string }
    deleteError.value = e.data?.detail || e.message || 'Xóa thất bại'
    deleteErrorId.value = r.id
  }
  deletingId.value = null
}

async function fetchReviews(append = false) {
  loading.value = true
  try {
    const res = await $fetch<Entity>(`/api/entities/${props.entityId}/feed?page=${page.value}&limit=10`)
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
        images: formImages.value,
      },
    })
    formContent.value = ''
    formRating.value = 0
    formImages.value = []
    page.value = 1
    await fetchReviews()
  } catch (e: unknown) {
    submitError.value = e.data?.detail || e.message || 'Gửi thất bại'
  }
  submitting.value = false
}

const { timeAgo } = useTimeAgo()

onMounted(() => fetchReviews())
</script>

<style scoped>
.rf-rating-hint { font-size: var(--text-sm); color: var(--muted); font-weight: var(--weight-semibold); margin-inline-start: var(--space-2); align-self: center; font-variant-numeric: tabular-nums; }
.review-textarea { resize: vertical; }
.review-error { font-size: var(--text-sm); color: var(--error, #D94F3D); }
.review-retry-btn { margin-inline-start: var(--space-2); }
.review-empty { font-size: var(--text-sm); }
.review-load-more { margin-top: var(--space-3); }

/* Image attach */
.rf-images { display: flex; flex-direction: column; gap: var(--space-2); margin-block: var(--space-2); }
.rf-image-grid { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.rf-image-thumb { position: relative; width: 64px; height: 64px; border-radius: var(--radius-md); overflow: hidden; border: .5px solid var(--line); }
.rf-image-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.rf-image-remove {
  position: absolute; top: 2px; inset-inline-end: 2px;
  width: 20px; height: 20px; line-height: 1;
  display: inline-flex; align-items: center; justify-content: center;
  border: none; border-radius: var(--radius-full);
  background: rgba(0, 0, 0, .6); color: #fff; font-size: 14px;
  cursor: pointer; padding: 0;
  transition: background .15s cubic-bezier(.2, 1, .4, 1);
}
.rf-image-remove:hover { background: rgba(0, 0, 0, .8); }
.rf-image-remove:focus-visible { outline: 2px solid var(--brand, currentColor); outline-offset: 1px; }
.rf-image-add {
  display: inline-flex; align-items: center; gap: var(--space-2);
  min-height: 36px; padding-inline: var(--space-3);
  border: 1px dashed var(--line); border-radius: var(--radius-md);
  font-size: var(--text-sm); color: var(--muted); cursor: pointer;
  align-self: flex-start;
  transition: border-color .15s cubic-bezier(.2, 1, .4, 1), color .15s cubic-bezier(.2, 1, .4, 1);
}
.rf-image-add:hover { border-color: var(--brand, var(--muted)); color: var(--ink, var(--muted)); }
.rf-image-add:focus-within { outline: 2px solid var(--brand, currentColor); outline-offset: 2px; }
.rf-image-add.disabled { opacity: .55; cursor: not-allowed; }
.rf-image-input { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
.rf-error { font-size: var(--text-sm); color: var(--error, #D94F3D); margin-top: var(--space-1); }

/* Own-review actions */
.ri-actions { margin-inline-start: auto; display: inline-flex; gap: var(--space-2); }
.ri-action-btn {
  min-height: 28px; padding-inline: var(--space-2);
  border: .5px solid var(--line); border-radius: var(--radius-sm);
  background: transparent; font-size: var(--text-xs); color: var(--muted);
  cursor: pointer;
  transition: color .15s cubic-bezier(.2, 1, .4, 1), border-color .15s cubic-bezier(.2, 1, .4, 1);
}
.ri-action-btn:hover { color: var(--error, #D94F3D); border-color: var(--error, #D94F3D); }
.ri-action-btn:focus-visible { outline: 2px solid var(--error, currentColor); outline-offset: 1px; }
.ri-action-btn:disabled { opacity: .55; cursor: not-allowed; }

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
