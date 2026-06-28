<template>
  <div class="review-item">
    <div class="ri-head">
      <NuxtLink :to="`/nguoi-dung/${review.username || review.user_id}`" class="ri-author">
        <img v-if="review.avatar_url" :src="review.avatar_url" class="ri-avatar" :alt="review.display_name" loading="lazy" decoding="async" width="32" height="32" @error="(e) => ((e.target as HTMLImageElement).style.display = 'none')" />
        <span v-else class="ri-avatar-placeholder">{{ (review.display_name || '?')[0] }}</span>
        <strong>{{ review.display_name || 'Ẩn danh' }}</strong>
      </NuxtLink>
      <span v-if="review.rating" class="star-rating-inline">
        <span v-for="s in 5" :key="s" class="star" :class="{ active: s <= review.rating }" aria-hidden="true">★</span>
      </span>
      <time class="ri-date" :datetime="review.created_at">{{ timeAgo(review.created_at) }}</time>
      <div v-if="owned" class="ri-actions">
        <button
          type="button"
          class="ri-action-btn ri-delete"
          :disabled="deleting"
          :aria-label="`Xóa đánh giá của bạn`"
          @click="$emit('delete', review)"
        >{{ deleting ? 'Đang xóa…' : 'Xóa' }}</button>
        <span v-if="deleteError" class="rf-error" role="alert">{{ deleteError }}</span>
      </div>
    </div>
    <p class="ri-content">{{ review.content }}</p>
    <div v-if="review.images?.length" class="ri-images">
      <template v-for="(img, i) in review.images" :key="i">
        <NuxtImg v-if="isRemoteUrl(img)" :src="img" :alt="`Ảnh đánh giá ${i + 1}`" loading="lazy" decoding="async" width="200" height="200" sizes="200px" @error="(e: Event) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
        <img v-else :src="img" :alt="`Ảnh đánh giá ${i + 1}`" loading="lazy" decoding="async" width="200" height="200" @error="(e) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
      </template>
    </div>
    <button type="button" :class="['ri-helpful', { active: review.user_liked }]" :aria-pressed="!!review.user_liked" @click="$emit('toggle-helpful', review)">
      👍 Hữu ích<span v-if="review.likes" class="ri-helpful-count">{{ review.likes }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import type { Review } from '~/types'

defineProps<{
  review: Review
  owned: boolean
  deleting: boolean
  deleteError: string
}>()

defineEmits<{
  delete: [review: Review]
  'toggle-helpful': [review: Review]
}>()

const { timeAgo } = useTimeAgo()
const isRemoteUrl = (url: string) => /^https?:\/\//.test(url)
</script>

<style scoped>
.ri-helpful { margin-top: var(--space-2); display: inline-flex; align-items: center; gap: .3rem; font-size: var(--text-sm); padding: .3rem .7rem; border: 1px solid var(--border); border-radius: 999px; background: var(--bg); color: var(--ink-700); cursor: pointer; min-height: 44px; }
.ri-helpful.active { background: color-mix(in srgb, var(--primary) 12%, var(--bg)); border-color: var(--primary); color: var(--primary-fg); }
.ri-helpful-count { font-weight: var(--weight-medium); }
.ri-actions { margin-inline-start: auto; display: inline-flex; gap: var(--space-2); }
.ri-action-btn {
  min-height: 44px; padding-inline: var(--space-2);
  border: .5px solid var(--line); border-radius: var(--radius-sm);
  background: transparent; font-size: var(--text-xs); color: var(--muted); cursor: pointer;
  transition: color .15s cubic-bezier(.2, 1, .4, 1), border-color .15s cubic-bezier(.2, 1, .4, 1);
}
.ri-action-btn:hover { color: var(--error, #D94F3D); border-color: var(--error, #D94F3D); }
.ri-action-btn:focus-visible { outline: 2px solid var(--error, currentColor); outline-offset: 1px; }
.ri-action-btn:disabled { opacity: .55; cursor: not-allowed; }
.rf-error { font-size: var(--text-sm); color: var(--error, #D94F3D); margin-top: var(--space-1); }
</style>
