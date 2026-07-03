<template>
  <div :class="['review-item', { 'review-featured': featured }]">
    <div class="ri-head">
      <NuxtLink :to="userPath(review.username || review.user_id)" class="ri-author">
        <span class="ri-avatar">
          <AvatarPlaceholder :src="review.avatar_url" :initial="(review.display_name || '?').charAt(0)?.toUpperCase()" :alt="review.display_name" />
        </span>
        <strong>{{ review.display_name || 'Ẩn danh' }}</strong>
      </NuxtLink>
      <span v-if="review.rating" class="star-rating-inline">
        <span v-for="s in 5" :key="s" class="star" :class="{ active: s <= review.rating }" aria-hidden="true">★</span>
      </span>
      <time v-if="review.created_at" class="ri-date" :datetime="review.created_at">{{ timeAgo(review.created_at) }}</time>
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
        <NuxtImg v-if="isRemoteUrl(img)" :src="img" :alt="`Ảnh đánh giá ${i + 1}`" loading="lazy" decoding="async" width="200" height="200" sizes="200px" @error="dimImage" />
        <img v-else :src="img" :alt="`Ảnh đánh giá ${i + 1}`" loading="lazy" decoding="async" width="200" height="200" @error="dimImage" />
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
  featured?: boolean
}>()

defineEmits<{
  delete: [review: Review]
  'toggle-helpful': [review: Review]
}>()

const { timeAgo } = useTimeAgo()

function imageFromPayload(payload: Event | string): HTMLImageElement | null {
  if (typeof payload === 'string') return null
  return payload.target instanceof HTMLImageElement ? payload.target : null
}

function dimImage(payload: Event | string) {
  const img = imageFromPayload(payload)
  if (img) img.style.opacity = '.15'
}
</script>

<style scoped>
.ri-avatar { width: 32px; height: 32px; border-radius: 50%; overflow: hidden; flex-shrink: 0; display: block; }
.ri-helpful { margin-top: var(--space-2); display: inline-flex; align-items: center; gap: .3rem; font-size: var(--text-sm); padding: .3rem .7rem; border: 1px solid var(--border); border-radius: 999px; background: var(--bg); color: var(--ink-700); cursor: pointer; min-height: 44px; }
.ri-helpful.active { background: color-mix(in srgb, var(--primary) 12%, var(--bg)); border-color: var(--primary); color: var(--primary-fg); }
.ri-helpful-count { font-weight: var(--weight-medium); }
.ri-actions { margin-inline-start: auto; display: inline-flex; gap: var(--space-2); }
.ri-action-btn {
  min-height: 44px; padding-inline: var(--space-2);
  border: .5px solid var(--line); border-radius: var(--radius-sm);
  background: transparent; font-size: var(--text-xs); color: var(--muted); cursor: pointer;
  transition: color .15s var(--ease-soft), border-color .15s var(--ease-soft);
}
.ri-action-btn:hover { color: var(--error, #D94F3D); border-color: var(--error, #D94F3D); }
.ri-action-btn:focus-visible { outline: 2px solid var(--error, currentColor); outline-offset: 1px; }
.ri-action-btn:disabled { opacity: .55; cursor: not-allowed; }
.rf-error { font-size: var(--text-sm); color: var(--error, #D94F3D); margin-top: var(--space-1); }
.review-featured { border-left: 3px solid var(--accent); background: rgba(var(--accent-rgb), .04); border-radius: var(--radius-md); }
/* dark override for .review-featured in dark-overrides.css */
</style>
