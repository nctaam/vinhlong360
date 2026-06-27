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

    <!-- Rating distribution -->
    <div v-if="rating.count && reviews.length" class="er-distribution" aria-label="Phân bố đánh giá">
      <div v-for="star in 5" :key="star" class="er-dist-row">
        <span class="er-dist-label">{{ 6 - star }}★</span>
        <div class="er-dist-track">
          <div class="er-dist-fill" :style="{ width: distPercent(6 - star) + '%' }" />
        </div>
        <span class="er-dist-count">{{ distCount(6 - star) }}</span>
      </div>
    </div>

    <!-- Category breakdown (placeholder — API not available yet) -->
    <div v-if="rating.count" class="er-categories">
      <div v-for="cat in REVIEW_CATEGORIES" :key="cat.key" class="er-cat-item">
        <span class="er-cat-label">{{ cat.label }}</span>
        <div class="er-cat-track"><div class="er-cat-fill er-cat-placeholder" /></div>
        <span class="er-cat-score">—</span>
      </div>
      <p class="er-cat-hint">Sắp có đánh giá chi tiết theo từng chiều</p>
    </div>

    <!-- Popular mention chips -->
    <div v-if="mentionChips.length" class="er-mentions">
      <h3 class="er-mentions-title">Mọi người hay nhắc đến</h3>
      <FilterChips :filters="mentionChips" v-model="selectedMentions" />
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
      <p v-if="!formImages.length" class="rf-photo-hint">📸 Thêm ảnh thật để giúp cộng đồng + nhận huy hiệu <strong>Nhiếp ảnh</strong></p>
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
      <div v-for="r in filteredReviews" :key="r.id" class="review-item">
        <div class="ri-head">
          <NuxtLink :to="`/nguoi-dung/${r.username || r.user_id}`" class="ri-author">
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
          <template v-for="(img, i) in r.images" :key="i">
            <NuxtImg v-if="isRemoteUrl(img)" :src="img" :alt="`Ảnh đánh giá ${i + 1}`" loading="lazy" decoding="async" width="200" height="200" sizes="200px" @error="(e: Event) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
            <img v-else :src="img" :alt="`Ảnh đánh giá ${i + 1}`" loading="lazy" decoding="async" width="200" height="200" @error="(e) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
          </template>
        </div>
        <button type="button" :class="['ri-helpful', { active: r.user_liked }]" :aria-pressed="!!r.user_liked" @click="toggleHelpful(r)">
          👍 Hữu ích<span v-if="r.likes" class="ri-helpful-count">{{ r.likes }}</span>
        </button>
      </div>
    </div>
    <p v-else-if="fetchFailed" class="empty review-error">Không thể tải đánh giá. <button type="button" class="btn btn-outline btn-sm review-retry-btn" @click="fetchFailed = false; fetchReviews()">Thử lại</button></p>
    <p v-else-if="!loading" class="empty review-empty">Chưa có đánh giá nào. Hãy là người đầu tiên!</p>

    <!-- Auto-load more on scroll -->
    <div v-if="hasMore" ref="sentinel" class="review-sentinel">
      <div v-if="infiniteLoading" class="spinner spinner-sm"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'

const REVIEW_CATEGORIES = [
  { key: 'atmosphere', label: 'Không khí' },
  { key: 'quality', label: 'Chất lượng' },
  { key: 'value', label: 'Giá trị' },
  { key: 'service', label: 'Phục vụ' },
]

const props = defineProps<{
  entityId: string
  entityName?: string
}>()

const { user, authHeaders } = useAuth()
const { confirmDialog } = useConfirm()
const isRemoteUrl = (url: string) => /^https?:\/\//.test(url)
const { openAuth } = useAuthModal()

async function toggleHelpful(r: any) {
  if (!user.value) { openAuth(() => toggleHelpful(r)); return }
  const flip = () => { r.user_liked = !r.user_liked; r.likes = (r.likes || 0) + (r.user_liked ? 1 : -1) }
  flip()
  try {
    await $fetch(`/api/posts/${r.id}/like`, { method: 'POST', headers: authHeaders() })
  } catch { flip() }
}

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

// Image attach state
const formImages = ref<string[]>([])
const uploadingImage = ref(false)
const uploadError = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

// Own-review actions
const deletingId = ref<string | number | null>(null)

const hasMore = computed(() => reviews.value.length < total.value)

const ratingDistribution = computed(() => {
  const counts = [0, 0, 0, 0, 0]
  for (const r of reviews.value) {
    const s = Math.round(r.rating || 0)
    if (s >= 1 && s <= 5) counts[s - 1]++
  }
  return counts
})
const maxDistCount = computed(() => Math.max(1, ...ratingDistribution.value))
function distCount(star: number) { return ratingDistribution.value[star - 1] || 0 }
function distPercent(star: number) { return (distCount(star) / maxDistCount.value) * 100 }

const selectedMentions = ref<string[]>([])
const STOP_WORDS = new Set(['và', 'là', 'của', 'cho', 'với', 'được', 'này', 'đã', 'có', 'không', 'rất', 'các', 'một', 'những', 'trong', 'ở', 'tại', 'cũng', 'nhưng', 'nên', 'thì', 'mà'])
const mentionChips = computed(() => {
  const freq = new Map<string, number>()
  for (const r of reviews.value) {
    const text = (r.content || '').toLowerCase()
    const words = text.split(/[\s,.!?;:()]+/).filter((w: string) => w.length >= 2 && !STOP_WORDS.has(w))
    const seen = new Set<string>()
    for (const w of words) {
      if (!seen.has(w)) { seen.add(w); freq.set(w, (freq.get(w) || 0) + 1) }
    }
  }
  return [...freq.entries()]
    .filter(([, c]) => c >= 2)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([word, count]) => ({ key: word, label: word, count }))
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

async function deleteReview(r: Review) {
  if (!isOwner(r)) return
  if (!await confirmDialog('Xóa đánh giá này?', { danger: true, confirmText: 'Xóa' })) return
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
    const res = await $fetch<ReviewFeedResponse>(`/api/entities/${props.entityId}/feed?page=${page.value}&limit=10`)
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
    submitError.value = extractErrorMessage(e, 'Gửi thất bại')
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
.review-sentinel { display: flex; justify-content: center; padding: var(--space-3) 0; min-height: 40px; }

/* Image attach */
.rf-photo-hint { margin: var(--space-2) 0 0; font-size: var(--text-sm); color: var(--ink-700); }
.ri-helpful { margin-top: var(--space-2); display: inline-flex; align-items: center; gap: .3rem; font-size: var(--text-sm); padding: .3rem .7rem; border: 1px solid var(--border); border-radius: 999px; background: var(--bg); color: var(--ink-700); cursor: pointer; min-height: 44px; }
.ri-helpful.active { background: color-mix(in srgb, var(--primary) 12%, var(--bg)); border-color: var(--primary); color: var(--primary-fg); }
.ri-helpful-count { font-weight: var(--weight-medium); }
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
  min-height: 44px; padding-inline: var(--space-3);
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
  min-height: 44px; padding-inline: var(--space-2);
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

/* Rating distribution */
.er-distribution {
  display: flex;
  flex-direction: column;
  gap: var(--space-1h, 6px);
  margin-bottom: var(--space-5);
  max-width: 320px;
}
.er-dist-row {
  display: grid;
  grid-template-columns: 28px 1fr 28px;
  align-items: center;
  gap: var(--space-2);
}
.er-dist-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium, 500);
  color: var(--muted);
  text-align: right;
}
.er-dist-track {
  height: 8px;
  border-radius: 4px;
  background: var(--bg-warm, var(--bg-alt));
  overflow: hidden;
}
.er-dist-fill {
  height: 100%;
  border-radius: 4px;
  background: var(--secondary);
  transition: width 400ms var(--ease-out, ease);
  min-width: 2px;
}
.er-dist-count {
  font-size: var(--text-xs);
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

/* Category breakdown */
.er-categories {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
  max-width: 400px;
}
.er-cat-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.er-cat-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium, 500);
  color: var(--ink);
}
.er-cat-track {
  height: 6px;
  border-radius: 3px;
  background: var(--bg-warm, var(--bg-alt));
  overflow: hidden;
}
.er-cat-fill {
  height: 100%;
  border-radius: 3px;
  background: var(--secondary);
}
.er-cat-placeholder { width: 0%; }
.er-cat-score {
  font-size: var(--text-xs);
  color: var(--muted);
}
.er-cat-hint {
  grid-column: 1 / -1;
  font-size: var(--text-xs);
  color: var(--muted);
  font-style: italic;
  margin: 0;
}

/* Mention chips */
.er-mentions {
  margin-bottom: var(--space-5);
}
.er-mentions-title {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold, 600);
  color: var(--ink);
  margin: 0 0 var(--space-2);
}
</style>

<!-- Chuyển từ detail.css: chỉ EntityReviews dùng .reviews-*/.review-*/.ri-*/.rf-* → nạp
     theo component (bỏ khỏi global entry.css). Non-scoped + giữ đúng thứ tự base→override
     để cascade không đổi (không file nào khác style các class này). -->
<style>
.reviews-section { margin-top: var(--space-8); }
.reviews-header { display: flex; align-items: baseline; gap: var(--space-3); flex-wrap: wrap; margin-bottom: var(--space-4); }
.reviews-header h2 { font-size: var(--text-lg); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); margin: 0; }
.reviews-summary { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-sm); }
.review-count { color: var(--muted); }

.review-form {
  background: linear-gradient(135deg, rgba(185, 219, 198, .04) 0%, rgba(232, 163, 61, .03) 100%);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: var(--space-5);
  margin-bottom: var(--space-5);
  box-shadow: 0 0 0 1px rgba(var(--secondary-rgb), .08);
}
.rf-rating { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-3); }
.rf-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--muted); }
.rf-error { color: var(--error); font-size: var(--text-sm); margin-top: var(--space-2); }
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
.ri-author strong { font-size: var(--text-sm); font-weight: var(--weight-semibold); }
.ri-avatar { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; }
.ri-avatar-placeholder { width: 32px; height: 32px; border-radius: 50%; background: var(--secondary); color: var(--text-on-dark, #fff); display: flex; align-items: center; justify-content: center; font-weight: var(--weight-bold); font-size: var(--text-sm); }
.ri-date { font-size: var(--text-xs); color: var(--muted); margin-inline-start: auto; }
.ri-content { margin: 0; font-size: var(--text-sm); line-height: var(--leading-relaxed); }
.ri-images { display: flex; gap: var(--space-2); margin-top: var(--space-2); overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: none; scroll-snap-type: x proximity; overscroll-behavior-x: contain; }
.ri-images::-webkit-scrollbar { display: none; }
.ri-images img { width: 120px; height: 90px; object-fit: cover; border-radius: var(--radius-sm); flex-shrink: 0; cursor: pointer; scroll-snap-align: start; transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out); }
.ri-images img:hover { transform: scale(1.05); box-shadow: var(--shadow-md); }
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
  background: linear-gradient(135deg, rgba(75, 169, 125, .04) 0%, rgba(240, 160, 80, .03) 100%);
  border-color: rgba(255, 255, 255, .06);
}
.dark .review-form:focus-within { box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .15); }
.dark .review-item:hover { background: rgba(255,255,255,.03); }
.dark .ri-avatar-placeholder { background: rgba(var(--primary-rgb), .3); }
</style>
