<template>
  <div :class="['review-item', { 'review-featured': featured }]">
    <div class="ri-head">
      <NuxtLink :to="userPath(review.username || review.user_id)" class="ri-author">
        <span class="ri-avatar">
          <AvatarPlaceholder :src="review.avatar_url" :initial="(review.display_name || '?').charAt(0)?.toUpperCase()" :alt="review.display_name" />
        </span>
        <strong class="ri-byline">{{ review.display_name || 'Ẩn danh' }}</strong>
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
    <p class="ri-content" :class="{ 'ri-content-testimony': featured }">{{ review.content }}</p>
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
/* Byline reads like a masthead credit line, not a UI label — small-caps-ish tracking, no font swap (avatar row stays compact). */
.ri-byline { letter-spacing: .01em; }

.ri-content { text-wrap: pretty; }
/* Testimony treatment for the one most-helpful review per list (featured prop) — a light editorial quote frame, not a full pull-quote.
   Restraint: only the single featured review gets this so the list doesn't perform. */
.ri-content-testimony {
  font-family: var(--font-editorial);
  font-size: var(--text-base);
  font-weight: 500;
  line-height: var(--leading-relaxed);
  position: relative;
  padding-left: var(--space-5);
}
.ri-content-testimony::before {
  content: "\201C";
  position: absolute;
  left: 0;
  top: -.15em;
  font-family: var(--font-editorial);
  font-size: var(--text-2xl);
  line-height: 1;
  color: var(--river-600);
  opacity: .5;
}
.dark .ri-content-testimony::before { color: #74ABB5; opacity: .55; }

.ri-helpful { margin-top: var(--space-2); display: inline-flex; align-items: center; gap: .3rem; font-size: var(--text-sm); padding: .3rem .7rem; border: 1px solid var(--border); border-radius: 999px; background: var(--bg); color: var(--ink-700); cursor: pointer; min-height: 44px; }
.ri-helpful.active { background: color-mix(in srgb, var(--primary) 12%, var(--bg)); border-color: var(--primary); color: var(--primary-fg); }
.ri-helpful-count { font-weight: var(--weight-medium); font-variant-numeric: tabular-nums; }
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
/* Sediment accent replaces the generic --accent rail — river→amber→clay wash, echoing the section tick at card scale. */
.review-featured {
  border-left: 3px solid transparent;
  border-image: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 55%, var(--clay-600) 100%) 1;
  background: rgba(var(--accent-rgb), .04);
  border-radius: var(--radius-md);
}
.dark .review-featured {
  border-image: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 55%, var(--clay-400) 100%) 1;
}
/* background tint for .review-featured in dark stays in dark-overrides.css */
</style>
