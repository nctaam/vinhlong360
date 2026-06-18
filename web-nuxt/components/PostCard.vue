<template>
  <div class="post-card">
    <div class="post-header">
      <NuxtLink v-if="post.user_id" :to="`/nguoi-dung/${post.user_id}`" class="avatar-link">
        <span v-if="post.avatar" class="avatar avatar-sm">
          <img :src="post.avatar" :alt="post.display_name" />
        </span>
        <span v-else class="avatar avatar-sm">{{ authorInitial }}</span>
      </NuxtLink>
      <span v-else class="avatar avatar-sm">{{ authorInitial }}</span>
      <div class="post-header-text">
        <div class="post-author">
          <NuxtLink v-if="post.user_id" :to="`/nguoi-dung/${post.user_id}`" class="post-author-link">
            {{ post.display_name || post.phone || 'Người dùng' }}
          </NuxtLink>
          <span v-if="postTypeBadge" :class="['post-type-badge', `ptb-${post.post_type}`]">{{ postTypeBadge }}</span>
        </div>
        <div class="post-meta">
          <span>{{ timeAgo(post.created_at) }}</span>
        </div>
      </div>
    </div>

    <NuxtLink v-if="post.entity_id" :to="`/dia-diem/${post.entity_id}`" class="post-entity-link">
      {{ post.entity_emoji || '📍' }} {{ post.entity_name || post.entity_id }}
      <span class="tag-muted">{{ post.entity_type_label || '' }}</span>
    </NuxtLink>

    <div v-if="post.rating" class="post-rating">
      <span class="star-rating-inline">
        <span v-for="s in 5" :key="s" :class="['star', { active: s <= post.rating }]">★</span>
      </span>
    </div>

    <div class="post-content">{{ post.content }}</div>

    <div v-if="post.images?.length" class="post-images" :class="imgLayoutClass">
      <button
        v-for="(img, i) in displayImages"
        :key="i"
        class="post-img-wrap"
        @click="openLightbox(i)"
      >
        <img :src="img" :alt="`Ảnh ${i + 1}`" loading="lazy" />
        <span v-if="i === 3 && extraCount > 0" class="post-img-more">+{{ extraCount }}</span>
      </button>
    </div>

    <div class="post-actions">
      <button :class="['post-action', { active: post.user_liked }]" @click="$emit('like', post.id)">
        {{ post.user_liked ? '❤️' : '🤍' }} {{ post.likes || 0 }}
      </button>
      <button class="post-action" @click="$emit('comment', post.id)">
        💬 {{ post.comments_count || 0 }}
      </button>
      <button :class="['post-action', { active: post.user_bookmarked }]" @click="$emit('bookmark', post.id)">
        {{ post.user_bookmarked ? '🔖' : '📑' }}
      </button>
      <button class="post-action" title="Báo cáo nội dung vi phạm" @click="$emit('report', post.id)">
        🚩
      </button>
    </div>

    <Teleport to="body">
      <div v-if="lbOpen" class="lightbox" @click.self="lbOpen = false">
        <button class="lb-close" @click="lbOpen = false">&times;</button>
        <button v-if="allImages.length > 1" class="lb-prev" @click="lbPrev">&#8249;</button>
        <img :src="allImages[lbIdx]" class="lb-img" :alt="`Ảnh ${lbIdx + 1} / ${allImages.length}`" />
        <button v-if="allImages.length > 1" class="lb-next" @click="lbNext">&#8250;</button>
        <span class="lb-counter">{{ lbIdx + 1 }} / {{ allImages.length }}</span>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ post: Record<string, any> }>()
defineEmits<{
  (e: 'like', id: string): void
  (e: 'comment', id: string): void
  (e: 'bookmark', id: string): void
  (e: 'report', id: string): void
}>()

const POST_TYPE_LABELS: Record<string, string> = {
  review: 'Đánh giá',
  share: 'Chia sẻ',
  recommend: 'Gợi ý',
  question: 'Hỏi đáp',
}

const authorInitial = computed(() => {
  const name = props.post?.display_name || props.post?.phone || '?'
  return name.charAt(0).toUpperCase()
})

const postTypeBadge = computed(() => POST_TYPE_LABELS[props.post?.post_type] || null)

const allImages = computed(() => props.post?.images || [])
const displayImages = computed(() => allImages.value.slice(0, 4))
const extraCount = computed(() => Math.max(0, allImages.value.length - 4))

const imgLayoutClass = computed(() => {
  const len = allImages.value.length
  if (len === 1) return 'img-grid-1'
  if (len === 2) return 'img-grid-2'
  if (len === 3) return 'img-grid-3'
  return 'img-grid-4'
})

const lbOpen = ref(false)
const lbIdx = ref(0)

function openLightbox(i: number) {
  lbIdx.value = i
  lbOpen.value = true
}
function lbPrev() { lbIdx.value = (lbIdx.value - 1 + allImages.value.length) % allImages.value.length }
function lbNext() { lbIdx.value = (lbIdx.value + 1) % allImages.value.length }

function onKey(e: KeyboardEvent) {
  if (!lbOpen.value) return
  if (e.key === 'Escape') lbOpen.value = false
  if (e.key === 'ArrowLeft') lbPrev()
  if (e.key === 'ArrowRight') lbNext()
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

function timeAgo(dateStr: string): string {
  if (!dateStr) return ''
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = Math.floor((now - then) / 1000)
  if (diff < 60) return 'Vừa xong'
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`
  if (diff < 604800) return `${Math.floor(diff / 86400)} ngày trước`
  return new Date(dateStr).toLocaleDateString('vi-VN')
}
</script>

<style scoped>
.post-author-link { font-weight: 600; transition: color .3s var(--ease-out); }
.post-author-link:hover { color: var(--primary-fg); }
.avatar-link { transition: transform .35s var(--ease-spring-gentle); display: inline-block; }
.avatar-link:hover { transform: scale(1.1); }
.post-type-badge { transition: transform .3s var(--ease-spring-gentle); }
.post-type-badge:hover { transform: scale(1.06); }
.star { transition: transform .3s var(--ease-spring-gentle); display: inline-block; }
.star.active { color: var(--accent); }
.star:hover { transform: scale(1.2); }
.post-entity-link { transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out); }
.post-entity-link:hover { box-shadow: var(--shadow-xs); }
.avatar-link:active { transform: scale(.95); transition-duration: .08s; }
.star:active { transform: scale(.9); transition-duration: .08s; }
.post-type-badge:active { transform: scale(.95); transition-duration: .08s; }
</style>
