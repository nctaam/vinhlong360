<template>
  <article class="thread-post" :class="{ 'has-replies': hasReplies }">
    <div class="thread-left">
      <NuxtLink v-if="post.user_id" :to="`/nguoi-dung/${post.user_id}`" class="thread-avatar-link">
        <span v-if="post.avatar" class="avatar thread-avatar">
          <img :src="post.avatar" :alt="post.display_name" loading="lazy" decoding="async" width="40" height="40" @error="(e) => ((e.target as HTMLImageElement).style.display = 'none')" />
        </span>
        <span v-else class="avatar thread-avatar">{{ authorInitial }}</span>
      </NuxtLink>
      <span v-else class="avatar thread-avatar">{{ authorInitial }}</span>
      <div v-if="hasReplies" class="thread-line"></div>
    </div>

    <div class="thread-right">
      <div class="thread-head">
        <NuxtLink v-if="post.user_id" :to="`/nguoi-dung/${post.user_id}`" class="thread-author">
          {{ post.display_name || post.phone || 'Người dùng' }}
        </NuxtLink>
        <span v-else class="thread-author">{{ post.display_name || 'Người dùng' }}</span>
        <time class="thread-time" :datetime="post.created_at">{{ timeAgo(post.created_at) }}</time>
        <button type="button" class="thread-more" title="Tùy chọn" @click="showMenu = !showMenu">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
        </button>
        <Transition name="menu-pop">
          <div v-if="showMenu" class="thread-menu">
            <button type="button" @click="$emit('report', post.id); showMenu = false">Báo cáo</button>
          </div>
        </Transition>
      </div>

      <div class="thread-meta-row">
        <span v-if="post.post_type && post.post_type !== 'share'" :class="['thread-type-badge', `type-${post.post_type}`]">
          {{ typeLabel }}
        </span>
        <NuxtLink v-if="post.entity_id" :to="`/dia-diem/${post.entity_id}`" class="thread-entity">
          {{ post.entity_emoji || '📍' }} {{ post.entity_name || post.entity_id }}
        </NuxtLink>
      </div>

      <div v-if="post.rating" class="thread-rating" role="img" :aria-label="`${post.rating} trên 5 sao`">
        <span v-for="s in 5" :key="s" :class="['star', { active: s <= post.rating }]" aria-hidden="true">★</span>
      </div>

      <NuxtLink :to="`/bai-viet/${post.id}`" class="thread-body">
        <p class="thread-content">{{ post.content }}</p>
      </NuxtLink>

      <div v-if="post.images?.length" class="thread-images" :class="imgLayoutClass">
        <button type="button"
          v-for="(img, i) in displayImages"
          :key="i"
          class="thread-img-wrap"
          @click="openLightbox(i)"
        >
          <img :src="img" :alt="`Ảnh ${i + 1}`" loading="lazy" decoding="async" width="400" height="300" @error="(e) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
          <span v-if="i === 3 && extraCount > 0" class="thread-img-more">+{{ extraCount }}</span>
        </button>
      </div>

      <div class="thread-actions">
        <button type="button" :class="['thread-act', { active: post.user_liked, 'like-pop': likePop }]" @click="onLike" :aria-label="post.user_liked ? 'Bỏ thích' : 'Thích'">
          <svg v-if="!post.user_liked" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
          <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none" aria-hidden="true"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
          <span v-if="post.likes" class="act-count">{{ post.likes }}</span>
        </button>
        <button type="button" class="thread-act" @click="$emit('comment', post.id)" aria-label="Bình luận">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <span v-if="post.comments_count" class="act-count">{{ post.comments_count }}</span>
        </button>
        <button type="button" class="thread-act" aria-label="Chia sẻ" @click="sharePost">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>
        </button>
        <button type="button" :class="['thread-act thread-act-end', { active: post.user_bookmarked }]" @click="$emit('bookmark', post.id)" :aria-label="post.user_bookmarked ? 'Bỏ lưu' : 'Lưu'">
          <svg width="20" height="20" viewBox="0 0 24 24" :fill="post.user_bookmarked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
        </button>
      </div>

      <NuxtLink v-if="post.comments_count" :to="`/bai-viet/${post.id}`" class="thread-reply-hint">
        {{ post.comments_count }} bình luận
      </NuxtLink>
    </div>

    <Teleport to="body">
      <div v-if="lbOpen" class="lightbox" role="dialog" aria-modal="true" aria-label="Xem ảnh" @click.self="closeLightbox">
        <button type="button" class="lb-close" aria-label="Đóng" @click="closeLightbox">&times;</button>
        <button type="button" v-if="allImages.length > 1" class="lb-prev" aria-label="Ảnh trước" @click="lbPrev">&#8249;</button>
        <img
          :key="lbIdx"
          :src="allImages[lbIdx]"
          class="lb-img"
          :alt="`Ảnh ${lbIdx + 1} / ${allImages.length}`"
          :style="lbDragStyle"
          @touchstart.passive="onLbTouchStart"
          @touchmove.passive="onLbTouchMove"
          @touchend="onLbTouchEnd"
        />
        <button type="button" v-if="allImages.length > 1" class="lb-next" aria-label="Ảnh tiếp" @click="lbNext">&#8250;</button>
        <span class="lb-counter">{{ lbIdx + 1 }} / {{ allImages.length }}</span>
      </div>
    </Teleport>
  </article>
</template>

<script setup lang="ts">
const props = defineProps<{
  post: Record<string, any>
  hasReplies?: boolean
}>()
const emit = defineEmits<{
  (e: 'like', id: string): void
  (e: 'comment', id: string): void
  (e: 'bookmark', id: string): void
  (e: 'report', id: string): void
}>()

const showMenu = ref(false)
const likePop = ref(false)

const typeLabels: Record<string, string> = {
  review: '⭐ Đánh giá',
  question: '❓ Hỏi đáp',
  recommend: '👍 Gợi ý',
  share: '📸 Chia sẻ',
}
const typeLabel = computed(() => typeLabels[props.post?.post_type] || '')

function onLike() {
  emit('like', props.post.id)
  if (!props.post.user_liked) {
    likePop.value = true
    setTimeout(() => { likePop.value = false }, 400)
  }
}

const { show: showToast } = useToast()

async function sharePost() {
  const url = `${window.location.origin}/bai-viet/${props.post.id}`
  const text = props.post.content?.slice(0, 100) || 'Bài viết từ cộng đồng vinhlong360'
  if (navigator.share) {
    try { await navigator.share({ title: 'vinhlong360', text, url }) } catch {}
  } else {
    try {
      await navigator.clipboard.writeText(url)
      showToast('Đã sao chép liên kết', 'success')
    } catch {}
  }
}

const authorInitial = computed(() => {
  const name = props.post?.display_name || props.post?.phone || '?'
  return name.charAt(0).toUpperCase()
})

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

let lbTriggerEl: HTMLElement | null = null
function openLightbox(i: number) {
  lbTriggerEl = document.activeElement as HTMLElement
  lbIdx.value = i
  lbOpen.value = true
  nextTick(() => {
    const close = document.querySelector('.lb-close') as HTMLElement
    close?.focus()
  })
}
function closeLightbox() {
  lbOpen.value = false
  nextTick(() => lbTriggerEl?.focus())
}
function lbPrev() { lbIdx.value = (lbIdx.value - 1 + allImages.value.length) % allImages.value.length }
function lbNext() { lbIdx.value = (lbIdx.value + 1) % allImages.value.length }

const lbTouchX = ref(0)
const lbTouchDX = ref(0)
const lbSwiping = ref(false)

const lbDragStyle = computed(() => {
  if (!lbSwiping.value || !lbTouchDX.value) return {}
  const dx = lbTouchDX.value
  const opacity = Math.max(0.4, 1 - Math.abs(dx) / 400)
  return { transform: `translateX(${dx}px) scale(${opacity > 0.7 ? 1 : 0.95})`, opacity, transition: 'none' }
})

function onLbTouchStart(e: TouchEvent) {
  lbTouchX.value = e.touches[0].clientX
  lbTouchDX.value = 0
  lbSwiping.value = true
}
function onLbTouchMove(e: TouchEvent) {
  if (!lbSwiping.value) return
  lbTouchDX.value = e.touches[0].clientX - lbTouchX.value
}
function onLbTouchEnd() {
  if (Math.abs(lbTouchDX.value) > 60) {
    if (lbTouchDX.value < 0) lbNext()
    else lbPrev()
  }
  lbSwiping.value = false
  lbTouchDX.value = 0
}

function onKey(e: KeyboardEvent) {
  if (!lbOpen.value) return
  if (e.key === 'Escape') closeLightbox()
  if (e.key === 'ArrowLeft') lbPrev()
  if (e.key === 'ArrowRight') lbNext()
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

if (import.meta.client) {
  const onClick = (e: Event) => { if (showMenu.value) showMenu.value = false }
  onMounted(() => document.addEventListener('click', onClick, true))
  onUnmounted(() => document.removeEventListener('click', onClick, true))
}

const { timeAgo } = useTimeAgo()
</script>
