<template>
  <article
    class="thread-post"
    :class="{ 'has-replies': hasReplies }"
    data-image-surface="post-grid"
    data-source-class="user-uploaded"
    data-entity-image-policy="no-image-invariant"
  >
    <div class="thread-left">
      <NuxtLink v-if="post.user_id" :to="userPath(post.username || post.user_id)" class="thread-avatar-link">
        <span class="avatar thread-avatar">
          <AvatarPlaceholder :src="post.avatar" :initial="authorInitial" :alt="post.display_name" />
        </span>
      </NuxtLink>
      <span v-else class="avatar thread-avatar">
        <AvatarPlaceholder :initial="authorInitial" />
      </span>
      <div v-if="hasReplies" class="thread-line"></div>
    </div>

    <div
      class="thread-right"
      data-image-surface="post-lightbox"
      data-source-class="user-uploaded"
      data-entity-image-policy="no-image-invariant"
    >
      <div class="thread-head">
        <NuxtLink v-if="post.user_id" :to="userPath(post.username || post.user_id)" class="thread-author">
          {{ post.display_name || post.phone || 'Người dùng' }}
        </NuxtLink>
        <span v-else class="thread-author">{{ post.display_name || 'Người dùng' }}</span>
        <time class="thread-time thread-dateline" :datetime="post.created_at">{{ timeAgo(post.created_at) }}</time>
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

      <div v-if="(post.post_type && post.post_type !== 'share') || post.entity_id" class="thread-meta-row">
        <span v-if="post.post_type && post.post_type !== 'share'" :class="['thread-type-badge', `type-${post.post_type}`]">
          {{ typeLabel }}
        </span>
        <NuxtLink v-if="post.entity_id" :to="entityPath(post.entity_id)" class="thread-entity">
          {{ post.entity_name || post.entity_id }}
        </NuxtLink>
      </div>
      <span v-if="(post.post_type && post.post_type !== 'share') || post.entity_id" class="thread-rule" aria-hidden="true"></span>

      <div v-if="post.rating" class="thread-rating" role="img" :aria-label="`${post.rating} trên 5 sao`">
        <span v-for="s in 5" :key="s" :class="['star', { active: s <= post.rating }]" aria-hidden="true">★</span>
      </div>

      <div v-if="post.content" class="thread-body">
        <p class="thread-content" :class="{ collapsed: isLong && !expanded }" v-html="contentHtml"></p>
        <button v-if="isLong" type="button" class="thread-expand" @click="expanded = !expanded">
          {{ expanded ? 'Thu gọn' : 'Xem thêm' }}
        </button>
      </div>

      <NuxtLink v-if="post.repost" :to="postPath(post.repost.id)" class="thread-repost-embed">
        <template v-if="post.repost.content">
          <span class="tre-head"><span class="emoji-chip" aria-hidden="true">🔁</span> <strong>{{ post.repost.author || 'Người dùng' }}</strong></span>
          <span class="tre-content">{{ post.repost.content }}</span>
        </template>
        <span v-else class="tre-deleted"><span class="emoji-chip" aria-hidden="true">🔁</span> Bài viết gốc đã bị xoá</span>
      </NuxtLink>

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
            <button type="button" role="menuitem" @click="$emit('repost', post.id); repostMenu = false"><span class="emoji-chip" aria-hidden="true">🔁</span> Đăng lại</button>
            <button type="button" role="menuitem" @click="$emit('quote', post.id); repostMenu = false"><span class="emoji-chip" aria-hidden="true">✍️</span> Trích dẫn</button>
          </div>
        </div>
        <button type="button" class="thread-act" aria-label="Chia sẻ" @click="sharePost">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>
        </button>
        <button type="button" :class="['thread-act thread-act-end', { active: post.user_bookmarked }]" @click="$emit('bookmark', post.id)" :aria-label="post.user_bookmarked ? 'Bỏ lưu' : 'Lưu'">
          <svg width="20" height="20" viewBox="0 0 24 24" :fill="post.user_bookmarked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
        </button>
      </div>

      <NuxtLink v-if="post.comments_count" :to="postPath(post.id)" class="thread-reply-hint">
        {{ post.comments_count }} bình luận
      </NuxtLink>
    </div>

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
const isOwner = computed(() =>
  !!_authUser.value?.id && String(props.post?.user_id) === String(_authUser.value.id))

const showMenu = ref(false)
const repostMenu = ref(false)
const likePop = ref(false)
const expanded = ref(false)
const isLong = computed(() => (props.post.content || '').length > 280)

const contentHtml = computed(() => linkifyContent(props.post.content || '', props.post.mentions))

const typeLabels: Record<string, string> = {
  review: 'Đánh giá',
  question: 'Hỏi đáp',
  recommend: 'Gợi ý',
  share: 'Chia sẻ',
}
const typeLabel = computed(() => typeLabels[props.post?.post_type] || '')

function menuKeyHandler(closeRef: Ref<boolean>) {
  return (e: KeyboardEvent) => {
    if (e.key === 'Escape') { closeRef.value = false; return }
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
    e.preventDefault()
    const items = Array.from((e.currentTarget as HTMLElement).querySelectorAll<HTMLElement>('[role="menuitem"]'))
    if (!items.length) return
    const cur = items.indexOf(document.activeElement as HTMLElement)
    const next = e.key === 'ArrowDown' ? (cur + 1) % items.length : (cur - 1 + items.length) % items.length
    items[next]?.focus()
  }
}
const onPostMenuKey = menuKeyHandler(showMenu)
const onRepostMenuKey = menuKeyHandler(repostMenu)

let likePopTimer: ReturnType<typeof setTimeout> | undefined
function onLike() {
  emit('like', props.post.id)
  if (!props.post.user_liked) {
    if (likePopTimer) clearTimeout(likePopTimer)
    likePop.value = true
    likePopTimer = setTimeout(() => { likePop.value = false }, 400)
  }
}

const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()

async function confirmDelete() {
  showMenu.value = false
  const ok = await confirmDialog('Xoá bài viết này? Hành động không thể hoàn tác.', { confirmText: 'Xoá', danger: true })
  if (ok) emit('delete', props.post.id)
}

async function sharePost() {
  const url = `${window.location.origin}${postPath(props.post.id)}`
  const text = props.post.content?.slice(0, 100) || 'Bài viết từ cộng đồng vinhlong360'
  if (navigator.share) {
    try { await navigator.share({ title: 'vinhlong360', text, url }) } catch {}
  } else {
    try {
      await navigator.clipboard.writeText(url)
      showToast('Đã sao chép liên kết', 'success')
    } catch {
      showToast('Không thể sao chép liên kết', 'error')
    }
  }
}

const authorInitial = computed(() => {
  const name = props.post?.display_name || props.post?.phone || '?'
  return name.charAt(0).toUpperCase()
})

if (import.meta.client) {
  const onClick = (e: Event) => { showMenu.value = false; repostMenu.value = false }
  watch(() => showMenu.value || repostMenu.value, (open) => {
    if (open) document.addEventListener('click', onClick, true)
    else document.removeEventListener('click', onClick, true)
  })
  onUnmounted(() => document.removeEventListener('click', onClick, true))
}

onUnmounted(() => {
  if (likePopTimer) clearTimeout(likePopTimer)
})

const { timeAgo } = useTimeAgo()
</script>

<style scoped>
.tre-deleted { font-size: var(--text-sm); color: var(--muted); font-style: italic; }

/* ── Editorial reskin (visual/typographic only — no logic touched) ──
   Mirrors the shipped Story Card vocabulary (EntityCard.vue: card-dateline /
   card-rule / font-editorial) so a community post reads as the same
   publication, not a bolt-on app widget. Restraint: only the author name
   gets display serif — the body stays plain and scannable. */

/* Author name as quiet display type — a name, not a masthead */
.thread-author {
  font-family: var(--font-editorial);
  font-weight: 600;
  letter-spacing: -.005em;
}

/* Dateline — small-caps-ish quiet timestamp, museum-label register */
.thread-dateline {
  font-variant-numeric: tabular-nums;
  letter-spacing: .02em;
}

/* Tri-province sediment rule — card-scale hairline echo of the site-wide
   river→amber→clay thread. Only renders when the meta-row above it has
   content (type badge or linked entity), so plain posts stay clean. */
.thread-rule {
  display: block;
  width: 26px;
  height: 2px;
  border-radius: 2px;
  margin: var(--space-1) 0 var(--space-05);
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .thread-rule {
  background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%);
}

/* Type badge — hairline top-border eyebrow (museum spec-tag) instead of a
   solid app-badge pill; small-caps wide tracking per narrative-system §2.2. */
.thread-type-badge {
  background: none;
  border-top: 2px solid currentColor;
  border-radius: 0;
  padding: var(--space-1) 0 0;
  font-size: var(--text-2xs);
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--muted);
}
.thread-type-badge.type-review { color: var(--accent-text); }
.thread-type-badge.type-question { color: var(--primary-fg); }
.thread-type-badge.type-recommend { color: var(--secondary); }
.thread-type-badge.type-share { color: var(--tertiary-fg); }

/* Emoji-in-chip — never a bare emoji floating next to text; a small
   rounded token keeps it decorative rather than reading as a stray glyph.
   --bg-alt already remaps under .dark (variables.css), so this needs no
   separate dark override to stay legible. */
.emoji-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.4em;
  padding: 0 .15em;
  border-radius: var(--radius-xs);
  background: var(--bg-alt);
  font-size: .9em;
  line-height: 1.4;
}
</style>
