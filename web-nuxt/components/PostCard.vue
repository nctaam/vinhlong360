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
        <button type="button" class="thread-more" aria-label="Tùy chọn bài viết" aria-haspopup="true" :aria-expanded="showMenu" @click="showMenu = !showMenu">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
        </button>
        <Transition name="menu-pop">
          <div v-if="showMenu" class="thread-menu" role="menu" aria-label="Tùy chọn bài viết" @keydown="onPostMenuKey">
            <button v-if="isOwner" type="button" role="menuitem" @click="$emit('edit', post.id); showMenu = false">Sửa bài</button>
            <button v-if="isOwner" type="button" role="menuitem" class="menu-danger" @click="confirmDelete">Xoá bài</button>
            <button v-if="!isOwner" type="button" role="menuitem" @click="$emit('report', post.id); showMenu = false">Báo cáo</button>
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

      <div v-if="post.content" class="thread-body">
        <p class="thread-content" :class="{ collapsed: isLong && !expanded }" v-html="contentHtml"></p>
        <button v-if="isLong" type="button" class="thread-expand" @click="expanded = !expanded">
          {{ expanded ? 'Thu gọn' : 'Xem thêm' }}
        </button>
      </div>

      <NuxtLink v-if="post.repost" :to="`/bai-viet/${post.repost.id}`" class="thread-repost-embed">
        <span class="tre-head">🔁 <strong>{{ post.repost.author || 'Người dùng' }}</strong></span>
        <span class="tre-content">{{ post.repost.content }}</span>
      </NuxtLink>

      <div v-if="post.images?.length" class="thread-images" :class="imgLayoutClass">
        <button type="button"
          v-for="(img, i) in displayImages"
          :key="i"
          class="thread-img-wrap"
          @click="openLightbox(i)"
        >
          <NuxtImg v-if="isRemoteUrl(img)" :src="img" :alt="`Ảnh ${i + 1}`" loading="lazy" decoding="async" width="400" height="300" sizes="sm:100vw md:50vw lg:400px" @error="onImgError" />
          <img v-else :src="img" :alt="`Ảnh ${i + 1}`" loading="lazy" decoding="async" width="400" height="300" @error="onImgError" />
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
        <div v-if="!post.repost" class="thread-repost-wrap">
          <button type="button" class="thread-act" @click="repostMenu = !repostMenu" :aria-expanded="repostMenu" aria-haspopup="true" aria-label="Đăng lại hoặc trích dẫn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
          </button>
          <div v-if="repostMenu" class="thread-repost-menu" role="menu" aria-label="Đăng lại hoặc trích dẫn" @keydown="onRepostMenuKey">
            <button type="button" role="menuitem" @click="$emit('repost', post.id); repostMenu = false">🔁 Đăng lại</button>
            <button type="button" role="menuitem" @click="$emit('quote', post.id); repostMenu = false">✍️ Trích dẫn</button>
          </div>
        </div>
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
      <div v-if="lbOpen" ref="lbEl" class="lightbox" role="dialog" aria-modal="true" aria-label="Xem ảnh" @click.self="closeLightbox">
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
  (e: 'repost', id: string): void
  (e: 'quote', id: string): void
  (e: 'edit', id: string): void
  (e: 'delete', id: string): void
}>()

const { user: _authUser } = useAuth()
const isRemoteUrl = (url: string) => /^https?:\/\//.test(url)
const isOwner = computed(() =>
  !!_authUser.value?.id && String(props.post?.user_id) === String(_authUser.value.id))

const showMenu = ref(false)
const repostMenu = ref(false)
const likePop = ref(false)
const expanded = ref(false)
const isLong = computed(() => (props.post.content || '').length > 280)

// @-mention: escape nội dung rồi linkify các mention (an toàn — content đã escape,
// href dựng từ id qua encodeURIComponent + type cố định).
const contentHtml = computed(() => {
  let html = escapeHtml(props.post.content || '')
  const mentions = props.post.mentions
  if (Array.isArray(mentions) && mentions.length) {
    const sorted = [...mentions].sort((a, b) => (b?.label?.length || 0) - (a?.label?.length || 0))
    for (const m of sorted) {
      if (!m?.label || !m?.id || (m.type !== 'user' && m.type !== 'entity')) continue
      const href = m.type === 'user'
        ? `/nguoi-dung/${encodeURIComponent(m.id)}`
        : `/dia-diem/${encodeURIComponent(m.id)}`
      const token = '@' + escapeHtml(m.label)
      html = html.split(token).join(`<a class="mention-link" href="${href}">${token}</a>`)
    }
  }
  // Hashtag #tag → link feed theo chủ-đề (content đã escape; tag chỉ \w nên an toàn)
  html = html.replace(/#(\w{1,30})/gu, (_m, tag) =>
    `<a class="hashtag-link" href="/cong-dong?tag=${encodeURIComponent(tag.toLowerCase())}">#${tag}</a>`)
  return html
})

const typeLabels: Record<string, string> = {
  review: '⭐ Đánh giá',
  question: '❓ Hỏi đáp',
  recommend: '👍 Gợi ý',
  share: '📸 Chia sẻ',
}
const typeLabel = computed(() => typeLabels[props.post?.post_type] || '')

function onPostMenuKey(e: KeyboardEvent) {
  if (e.key === 'Escape') { showMenu.value = false; return }
  if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
  e.preventDefault()
  const menu = (e.currentTarget as HTMLElement)
  const items = Array.from(menu.querySelectorAll<HTMLElement>('[role="menuitem"]'))
  if (!items.length) return
  const cur = items.indexOf(document.activeElement as HTMLElement)
  const next = e.key === 'ArrowDown' ? (cur + 1) % items.length : (cur - 1 + items.length) % items.length
  items[next]?.focus()
}

function onRepostMenuKey(e: KeyboardEvent) {
  if (e.key === 'Escape') { repostMenu.value = false; return }
  if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
  e.preventDefault()
  const menu = (e.currentTarget as HTMLElement)
  const items = Array.from(menu.querySelectorAll<HTMLElement>('[role="menuitem"]'))
  if (!items.length) return
  const cur = items.indexOf(document.activeElement as HTMLElement)
  const next = e.key === 'ArrowDown' ? (cur + 1) % items.length : (cur - 1 + items.length) % items.length
  items[next]?.focus()
}

function onLike() {
  emit('like', props.post.id)
  if (!props.post.user_liked) {
    likePop.value = true
    setTimeout(() => { likePop.value = false }, 400)
  }
}

function onImgError(e: Event) {
  const el = e.target as HTMLImageElement
  el.style.opacity = '.15'
  el.alt = 'Không tải được ảnh'
}

const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()

async function confirmDelete() {
  showMenu.value = false
  const ok = await confirmDialog('Xoá bài viết này? Hành động không thể hoàn tác.', { confirmText: 'Xoá', danger: true })
  if (ok) emit('delete', props.post.id)
}

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
const lbEl = ref<HTMLElement>()

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
watch(lbOpen, (v) => {
  if (import.meta.client) document.body.style.overflow = v ? 'hidden' : ''
})
onUnmounted(() => { if (import.meta.client) document.body.style.overflow = '' })
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
  else if (e.key === 'ArrowLeft') lbPrev()
  else if (e.key === 'ArrowRight') lbNext()
  else if (e.key === 'Tab') {
    const btns = lbEl.value ? Array.from(lbEl.value.querySelectorAll<HTMLElement>('button')) : []
    if (!btns.length) return
    const first = btns[0]!, last = btns[btns.length - 1]!
    const active = document.activeElement as HTMLElement
    if (e.shiftKey && active === first) { e.preventDefault(); last.focus() }
    else if (!e.shiftKey && active === last) { e.preventDefault(); first.focus() }
    else if (!btns.includes(active)) { e.preventDefault(); first.focus() }
  }
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

if (import.meta.client) {
  const onClick = (e: Event) => { if (showMenu.value) showMenu.value = false; if (repostMenu.value) repostMenu.value = false }
  onMounted(() => document.addEventListener('click', onClick, true))
  onUnmounted(() => document.removeEventListener('click', onClick, true))
}

const { timeAgo } = useTimeAgo()
</script>
