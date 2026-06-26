<template>
  <section class="page thread-detail-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cộng đồng', to: '/cong-dong' }, { label: 'Bài viết' }]" />
    <h1 class="sr-only">{{ post?.display_name ? `Bài viết của ${post.display_name}` : 'Bài viết' }}</h1>

    <div v-if="post" class="thread-detail reveal">
      <div v-if="editing" class="post-edit-form">
        <h2 class="pef-title">Sửa bài viết</h2>
        <textarea v-model="editContent" class="textarea" maxlength="5000" rows="6" aria-label="Nội dung bài viết"></textarea>
        <div class="pef-actions">
          <span class="pef-count">{{ editContent.length }}/5000</span>
          <button type="button" class="btn btn-ghost btn-sm" @click="cancelEdit">Huỷ</button>
          <button type="button" class="btn btn-primary btn-sm" :disabled="editSaving || editContent.trim().length < 10" @click="saveEdit">{{ editSaving ? 'Đang lưu…' : 'Lưu' }}</button>
        </div>
      </div>
      <PostCard v-else :post="post" :has-replies="comments.length > 0" @like="toggleLike" @comment="scrollToCompose" @bookmark="toggleBookmark" @report="reportPost" @repost="repost" @quote="quote" @edit="startEdit" @delete="deletePost" />

      <!-- Comment thread -->
      <div class="thread-comments">
        <div class="replies-header">
          <svg class="replies-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
          <span class="replies-label">Trả lời</span>
          <span v-if="comments.length" class="replies-count" :class="{ 'replies-count--active': comments.length > 0 }">{{ comments.length }}</span>
        </div>

        <!-- Comment form (Threads style) -->
        <div v-if="isLoggedIn" ref="composeRef" class="thread-comment-compose" role="form" aria-label="Viết bình luận">
          <div class="compose-left">
            <span class="avatar thread-avatar avatar-sm">{{ userInitial }}</span>
          </div>
          <div class="compose-right">
            <div v-if="replyingTo" class="reply-context">
              <span>Đang trả lời <strong>@{{ replyingTo.author?.display_name || 'Người dùng' }}</strong></span>
              <button type="button" class="reply-context-x" aria-label="Huỷ trả lời" @click="cancelReply">&times;</button>
            </div>
            <div class="comment-mention-wrap">
              <input
                ref="commentInputEl"
                v-model="commentText"
                class="compose-input-sm"
                maxlength="500"
                :placeholder="replyingTo ? `Trả lời @${replyingTo.author?.display_name || 'Người dùng'}…` : `Trả lời ${post.display_name || 'bài viết'}…`"
                aria-label="Nội dung bình luận (gõ @ để nhắc người dùng hoặc địa điểm)"
                @input="onMentionInput"
                @keydown="onCommentKeydown"
              />
              <ul v-if="mentionOpen && mentionResults.length" class="mention-menu" role="listbox" aria-label="Gợi ý @nhắc">
                <li
                  v-for="(m, mi) in mentionResults"
                  :key="m.type + m.id"
                  :class="['mention-item', { active: mi === mentionActive }]"
                  role="option"
                  :aria-selected="mi === mentionActive"
                  @mousedown.prevent="pickMention(m)"
                >
                  <span class="mention-ic" aria-hidden="true">{{ m.type === 'user' ? '👤' : '📍' }}</span>
                  <span class="mention-label">{{ m.label }}</span>
                  <span class="mention-sub">{{ m.sub }}</span>
                </li>
              </ul>
            </div>
            <button type="button" class="btn btn-primary btn-sm compose-send" :disabled="!commentText.trim() || submitting" @click="submitComment">
              <svg v-if="!submitting" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M22 2 11 13"/><path d="m22 2-7 20-4-9-9-4z"/></svg>
              <span v-else class="spinner spinner-sm"></span>
            </button>
          </div>
        </div>
        <div v-else class="thread-comment-guest">
          <button type="button" class="guest-reply-link" @click="openAuth">Đăng nhập để trả lời</button>
        </div>

        <!-- Comment items as thread replies -->
        <div v-for="(c, idx) in comments" :key="c.id" class="thread-reply">
          <div class="thread-left">
            <NuxtLink v-if="c.author?.id" :to="`/nguoi-dung/${c.author?.username || c.author?.id}`" class="thread-avatar-link">
              <span class="avatar thread-avatar avatar-sm">{{ (c.author?.display_name || '?').charAt(0).toUpperCase() }}</span>
            </NuxtLink>
            <span v-else class="avatar thread-avatar avatar-sm">{{ (c.author?.display_name || '?').charAt(0).toUpperCase() }}</span>
            <div v-if="idx < comments.length - 1 || (c.replies && c.replies.length)" class="thread-line"></div>
          </div>
          <div class="thread-right">
            <div class="thread-head">
              <NuxtLink v-if="c.author?.id" :to="`/nguoi-dung/${c.author?.username || c.author?.id}`" class="thread-author">
                {{ c.author?.display_name || 'Người dùng' }}
              </NuxtLink>
              <span v-else class="thread-author">{{ c.author?.display_name || 'Người dùng' }}</span>
              <time class="thread-time" :datetime="c.created_at">{{ timeAgo(c.created_at) }}</time>
            </div>
            <p class="thread-content reply-text" v-html="renderComment(c)"></p>
            <div class="comment-actions">
              <button v-if="isLoggedIn" type="button" class="comment-reply-btn" @click="startReply(c)">Trả lời</button>
              <span v-if="isQuestion && c.id === bestAnswerId" class="qa-badge">✓ Câu trả lời hay</span>
              <button v-else-if="isQuestion && isQuestionAuthor" type="button" class="qa-pick" @click="setBestAnswer(c.id)">Chọn là câu trả lời hay</button>
            </div>

            <!-- Replies lồng (threaded, 1 cấp) -->
            <div v-for="r in (c.replies || [])" :key="r.id" class="thread-subreply">
              <NuxtLink v-if="r.author?.id" :to="`/nguoi-dung/${r.author?.username || r.author?.id}`" class="thread-avatar-link">
                <span class="avatar thread-avatar avatar-xs">{{ (r.author?.display_name || '?').charAt(0).toUpperCase() }}</span>
              </NuxtLink>
              <span v-else class="avatar thread-avatar avatar-xs">{{ (r.author?.display_name || '?').charAt(0).toUpperCase() }}</span>
              <div class="subreply-body">
                <div class="thread-head">
                  <NuxtLink v-if="r.author?.id" :to="`/nguoi-dung/${r.author?.username || r.author?.id}`" class="thread-author">{{ r.author?.display_name || 'Người dùng' }}</NuxtLink>
                  <span v-else class="thread-author">{{ r.author?.display_name || 'Người dùng' }}</span>
                  <time class="thread-time" :datetime="r.created_at">{{ timeAgo(r.created_at) }}</time>
                </div>
                <p class="thread-content reply-text" v-html="renderComment(r)"></p>
                <button v-if="isLoggedIn" type="button" class="comment-reply-btn" @click="startReply(r)">Trả lời</button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="commentError && !loading" class="comment-empty">
          <span class="comment-empty-halo"><span class="comment-empty-icon">⚠️</span></span>
          <p>Không thể tải bình luận.</p>
          <button type="button" class="btn btn-outline btn-sm" @click="fetchComments()">Thử lại</button>
        </div>
        <div v-else-if="!comments.length && !loading" class="comment-empty">
          <span class="comment-empty-halo"><span class="comment-empty-icon">💬</span></span>
          <p>Chưa có bình luận nào.</p>
          <p class="comment-empty-hint">{{ isLoggedIn ? 'Hãy là người đầu tiên trả lời!' : 'Đăng nhập để bình luận.' }}</p>
        </div>
        <div v-if="loading" class="feed-loading" role="status" aria-label="Đang tải bình luận"><div class="spinner"></div></div>
      </div>

      <!-- Related posts -->
      <ClientOnly>
        <div v-if="relatedPosts.length" class="related-section">
          <h3 class="related-title">Bài viết liên quan</h3>
          <div class="related-grid">
            <NuxtLink v-for="rp in relatedPosts" :key="rp.id" :to="`/bai-viet/${rp.id}`" class="related-card">
              <img v-if="rp.images?.[0]" :src="rp.images[0]" :alt="rp.display_name || 'Bài viết liên quan'" class="related-thumb" loading="lazy" decoding="async" width="400" height="100" />
              <div class="related-body">
                <span class="related-author">{{ rp.display_name }}</span>
                <p class="related-text">{{ (rp.content || '').slice(0, 80) }}{{ (rp.content || '').length > 80 ? '…' : '' }}</p>
                <span class="related-meta">{{ rp.like_count || 0 }} thích</span>
              </div>
            </NuxtLink>
          </div>
        </div>
      </ClientOnly>
    </div>

    <div v-else-if="pending" class="thread-detail-skeleton" role="status" aria-label="Đang tải bài viết">
      <SkeletonList :count="1" />
      <div class="thread-detail-skeleton-comments">
        <SkeletonList :count="2" />
      </div>
    </div>

    <div v-else class="empty-state-wrap">
      <EmptyState v-if="postFetchFailed" icon="⚠️" title="Không thể tải bài viết" message="Lỗi kết nối. Vui lòng thử lại.">
        <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData(`post-${postId}`)">Thử lại</button>
      </EmptyState>
      <EmptyState v-else icon="🔍" title="Không tìm thấy bài viết" message="Bài viết có thể đã bị xoá hoặc đường dẫn không đúng.">
        <NuxtLink to="/cong-dong" class="btn btn-outline btn-sm">Về Cộng đồng</NuxtLink>
      </EmptyState>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Post, Entity} from '~/types'
useReveal()
const route = useRoute()
const postId = computed(() => route.params.id as string)
const { isLoggedIn, authHeaders, user, handleSessionExpired } = useAuth()
const { openAuth } = useAuthModal()
const { confirmDialog } = useConfirm()
const { repost, quote } = useRepost()

// Linkify @-mention + #hashtag trong bình luận (content escape trước → an toàn v-html)
function renderComment(c: any): string {
  let html = escapeHtml(c?.content || '')
  const mentions = Array.isArray(c?.mentions) ? [...c.mentions].sort((a, b) => (b?.label?.length || 0) - (a?.label?.length || 0)) : []
  for (const m of mentions) {
    if (!m?.label || !m?.id || (m.type !== 'user' && m.type !== 'entity')) continue
    const href = m.type === 'user' ? `/nguoi-dung/${encodeURIComponent(m.id)}` : `/dia-diem/${encodeURIComponent(m.id)}`
    const token = '@' + escapeHtml(m.label)
    html = html.split(token).join(`<a class="mention-link" href="${href}">${token}</a>`)
  }
  html = html.replace(/#(\w{1,30})/gu, (_m, tag) => `<a class="hashtag-link" href="/cong-dong?tag=${encodeURIComponent(tag.toLowerCase())}">#${tag}</a>`)
  return html
}
const { reportPost } = useReport()
const { show: showToast } = useToast()

const commentText = ref('')
const comments = ref<Entity[]>([])
const submitting = ref(false)
const loading = ref(true)
const commentError = ref(false)
const replyingTo = ref<any | null>(null)

// @-mention trong ô bình luận (dùng composable chung)
const commentInputEl = ref<HTMLInputElement | null>(null)
const {
  mentionResults, mentionOpen, mentionActive,
  onInput: onMentionInput, pick: pickMention,
  onKeydown: onMentionKeydown, closeMention: closeMentionComment, reset: resetMention, activeMentions,
} = useMentionAutocomplete(commentText, commentInputEl)

function onCommentKeydown(e: KeyboardEvent) {
  const consumed = onMentionKeydown(e)
  if (consumed) return
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); submitComment(); return }
  if (e.key === 'Enter') submitComment()
}

// ── Q&A: câu trả lời hay (chủ bài hỏi chọn) ──
const bestAnswerId = ref<string | null>(null)
const isQuestion = computed(() => (post.value as any)?.post_type === 'question')
const isQuestionAuthor = computed(() =>
  isQuestion.value && isLoggedIn.value && String((post.value as any)?.user_id) === String(user.value?.id))
async function setBestAnswer(commentId: string) {
  const prev = bestAnswerId.value
  bestAnswerId.value = commentId
  try {
    await $fetch(`/api/posts/${postId.value}/best-answer`, { method: 'POST', headers: authHeaders(), body: { comment_id: commentId } })
    showToast('Đã chọn câu trả lời hay', 'success')
  } catch (e: any) {
    bestAnswerId.value = prev
    if (e?.response?.status === 401) { handleSessionExpired(); return }
    showToast('Không thể chọn, thử lại', 'error')
  }
}
async function deletePost() {
  const ok = await confirmDialog('Bạn có chắc muốn xoá bài viết này? Hành động không thể hoàn tác.', { confirmText: 'Xoá', danger: true })
  if (!ok) return
  try {
    await $fetch(`/api/posts/${postId.value}`, { method: 'DELETE', headers: authHeaders() })
    showToast('Đã xoá bài viết', 'success')
    navigateTo('/cong-dong')
  } catch (e: any) {
    if (e?.response?.status === 401) { handleSessionExpired(); return }
    showToast('Không thể xoá bài viết', 'error')
  }
}

const composeRef = ref<HTMLElement>()

function scrollToCompose() {
  composeRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  nextTick(() => {
    const input = composeRef.value?.querySelector('input')
    input?.focus()
  })
}

// ── Sửa bài viết (chủ bài) ──
const editing = ref(false)
const editContent = ref('')
const editSaving = ref(false)
function startEdit() {
  if (!post.value) return
  editContent.value = post.value.content || ''
  editing.value = true
}
function cancelEdit() { editing.value = false }
async function saveEdit() {
  if (editContent.value.trim().length < 10 || editSaving.value) return
  editSaving.value = true
  try {
    const res = await $fetch<any>(`/api/posts/${postId.value}`, {
      method: 'PATCH', headers: authHeaders(), body: { content: editContent.value.trim() },
    })
    if (post.value && res.post) {
      post.value.content = res.post.content
      post.value.hashtags = res.post.hashtags
      post.value.mentions = res.post.mentions
    }
    editing.value = false
    showToast(res.moderation_status === 'pending' ? 'Đã lưu — đang chờ duyệt lại' : 'Đã cập nhật bài viết', 'success')
  } catch (e: any) {
    if (e?.response?.status === 401) { handleSessionExpired(); return }
    showToast(e?.data?.detail || 'Không thể lưu bài viết', 'error')
  }
  editSaving.value = false
}

// ── Threaded reply ──
function startReply(c: any) {
  if (!isLoggedIn.value) { openAuth(() => startReply(c)); return }
  replyingTo.value = c
  scrollToCompose()
}
function cancelReply() { replyingTo.value = null }

const userInitial = computed(() => {
  const name = user.value?.display_name || user.value?.phone || '?'
  return name.charAt(0).toUpperCase()
})

const postFetchFailed = ref(false)
const { data: post, pending } = await useAsyncData(() => `post-${postId.value}`, async () => {
  try {
    postFetchFailed.value = false
    const res = await apiFetch<Post>(`/api/posts/${postId.value}`, { headers: authHeaders() })
    return res?.post || res
  } catch {
    postFetchFailed.value = true
    return null
  }
})
if (import.meta.server && !post.value && !postFetchFailed.value) {
  throw createError({ statusCode: 404, statusMessage: 'Không tìm thấy bài viết' })
}
bestAnswerId.value = (post.value as any)?.best_answer_id ?? null

async function fetchComments() {
  loading.value = true
  commentError.value = false
  try {
    const res = await $fetch<Post>(`/api/posts/${postId.value}/comments`)
    comments.value = res.comments || res || []
  } catch {
    commentError.value = true
  }
  loading.value = false
}

async function submitComment() {
  if (!commentText.value.trim() || submitting.value) return
  submitting.value = true
  try {
    const body: Record<string, any> = { content: commentText.value.trim() }
    const t = replyingTo.value
    const mentions: any[] = [...activeMentions()]   // @-mention người dùng tự gõ
    if (t) {
      // Threading 1 cấp: gắn vào bình-luận-gốc (cha của reply, hoặc chính nó nếu là top-level)
      body.parent_id = t.parent_id || t.id
      // Trả lời 1 reply → @mention tác-giả để giữ ngữ cảnh trong nhánh phẳng
      if (t.parent_id && t.author?.id && t.author?.display_name) {
        const label = t.author.display_name
        if (!body.content.includes(`@${label}`)) body.content = `@${label} ${body.content}`
        if (!mentions.some(x => x.type === 'user' && x.id === t.author.id)) {
          mentions.push({ type: 'user', id: t.author.id, label })
        }
      }
    }
    if (mentions.length) body.mentions = mentions
    await $fetch(`/api/posts/${postId.value}/comments`, {
      method: 'POST',
      headers: authHeaders(),
      body,
    })
    commentText.value = ''
    replyingTo.value = null
    resetMention()
    showToast(t ? 'Đã gửi trả lời' : 'Đã gửi bình luận', 'success')
    if (post.value) post.value.comments_count = (post.value.comments_count || 0) + 1
    await fetchComments()
  } catch (e: any) {
    if (e?.response?.status === 401) { handleSessionExpired(); return }
    const detail = e?.data?.detail
    showToast(detail || 'Gửi bình luận thất bại — vui lòng thử lại', 'error')
  }
  submitting.value = false
}

const pendingActions = reactive(new Set<string>())

async function toggleLike(id: string) {
  if (!isLoggedIn.value) { showToast('Đăng nhập để thích bài viết', 'info'); return }
  if (!post.value || pendingActions.has('like')) return
  pendingActions.add('like')
  post.value.user_liked = !post.value.user_liked
  post.value.likes = (post.value.likes || 0) + (post.value.user_liked ? 1 : -1)
  try {
    await $fetch(`/api/posts/${id}/like`, { method: 'POST', headers: authHeaders() })
  } catch (e: any) {
    post.value.user_liked = !post.value.user_liked
    post.value.likes = (post.value.likes || 0) + (post.value.user_liked ? 1 : -1)
    if (e?.response?.status === 401) { handleSessionExpired(); return }
    showToast('Không thể thích bài viết', 'error')
  } finally { pendingActions.delete('like') }
}

async function toggleBookmark(id: string) {
  if (!isLoggedIn.value) { showToast('Đăng nhập để lưu bài viết', 'info'); return }
  if (!post.value || pendingActions.has('bookmark')) return
  pendingActions.add('bookmark')
  post.value.user_bookmarked = !post.value.user_bookmarked
  try {
    await $fetch(`/api/posts/${id}/bookmark`, { method: 'POST', headers: authHeaders() })
  } catch (e: any) {
    post.value.user_bookmarked = !post.value.user_bookmarked
    if (e?.response?.status === 401) { handleSessionExpired(); return }
    showToast('Không thể lưu bài viết', 'error')
  } finally { pendingActions.delete('bookmark') }
}

const { timeAgo } = useTimeAgo()

const relatedPosts = ref<any[]>([])
async function fetchRelated() {
  try {
    const res = await $fetch<any>(`/api/posts/${postId.value}/related?limit=4`)
    relatedPosts.value = res.posts || []
  } catch { /* non-critical */ }
}

function onClickOutsideMention(e: MouseEvent) {
  if (mentionOpen.value && !(e.target as HTMLElement)?.closest('.comment-mention-wrap')) {
    closeMentionComment()
  }
}

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (editing.value && editContent.value !== (post.value?.content || '')) {
    e.preventDefault()
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutsideMention)
  if (import.meta.client) window.addEventListener('beforeunload', onBeforeUnload)
  fetchComments()
  fetchRelated()
  // mở editor khi điều hướng từ trang khác: /bai-viet/{id}?edit=1 (chủ bài)
  if (route.query.edit === '1' && isLoggedIn.value && post.value
      && String((post.value as any).user_id) === String(user.value?.id)) {
    startEdit()
  }
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutsideMention)
  if (import.meta.client) window.removeEventListener('beforeunload', onBeforeUnload)
})

watch(postId, () => {
  comments.value = []
  relatedPosts.value = []
  loading.value = true
  editing.value = false
  replyingTo.value = null
  commentText.value = ''
  bestAnswerId.value = null
  fetchComments()
  fetchRelated()
})

useHead({
  link: computed(() => [{ rel: 'canonical', href: canonicalUrl(`/bai-viet/${postId.value}`) }]),
  meta: [{ name: 'robots', content: 'noindex,follow' }],
})

useSeoMeta({
  title: () => `${post.value?.display_name || 'Bài viết'} — vinhlong360`,
  description: () => (post.value?.content || '').substring(0, 160),
  ogTitle: () => `${post.value?.display_name || 'Bài viết'} — vinhlong360`,
  ogDescription: () => (post.value?.content || '').substring(0, 160),
  ogImage: () => post.value?.images?.[0] || '/icons/icon-512.png',
})

useHead({
  script: computed(() => {
    if (!post.value) return []
    const p = post.value
    const postTitle = p.display_name || 'Bài viết'
    const postDesc = (p.content || '').substring(0, 160)
    const articleLd: Record<string, any> = {
      '@context': 'https://schema.org',
      '@type': p.post_type === 'review' ? 'Review' : 'Article',
      headline: postTitle, description: postDesc,
      url: `https://vinhlong360.vn/bai-viet/${postId.value}`,
      datePublished: p.created_at,
      dateModified: p.updated_at || p.created_at,
      author: {
        '@type': 'Person', name: p.display_name || 'Người dùng',
        ...(p.user_id ? { url: `https://vinhlong360.vn/nguoi-dung/${p.user_id}` } : {}),
      },
      publisher: { '@type': 'Organization', name: 'vinhlong360', url: 'https://vinhlong360.vn' },
    }
    if (p.images?.length) articleLd.image = p.images
    if (p.post_type === 'review' && p.rating) {
      articleLd.reviewRating = { '@type': 'Rating', ratingValue: p.rating, bestRating: 5 }
    }
    const breadcrumb = {
      '@context': 'https://schema.org', '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
        { '@type': 'ListItem', position: 2, name: 'Cộng đồng', item: 'https://vinhlong360.vn/cong-dong' },
        { '@type': 'ListItem', position: 3, name: postTitle },
      ],
    }
    return [
      { type: 'application/ld+json', innerHTML: JSON.stringify(articleLd) },
      { type: 'application/ld+json', innerHTML: JSON.stringify(breadcrumb) },
    ]
  }),
})
</script>

<style scoped>
.post-edit-form { background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-lg); padding: var(--space-4); margin-bottom: var(--space-3); }
.pef-title { font-size: var(--text-base); margin: 0 0 var(--space-3); }
.post-edit-form .textarea { width: 100%; resize: vertical; }
.pef-actions { display: flex; align-items: center; justify-content: flex-end; gap: var(--space-3); margin-top: var(--space-3); }
.pef-count { margin-right: auto; font-size: var(--text-xs); color: var(--muted); }
.qa-row { margin-top: .4rem; }
.qa-badge { display: inline-flex; align-items: center; gap: .25rem; font-size: var(--text-xs); font-weight: var(--weight-semibold); padding: .2rem .55rem; border-radius: 999px; background: color-mix(in srgb, var(--leaf, green) 18%, var(--bg-alt)); color: var(--leaf-fg, green); }
.qa-pick { font-size: var(--text-xs); padding: .2rem .55rem; border: 1px solid var(--border); border-radius: 999px; background: var(--bg); color: var(--ink-700); cursor: pointer; }
.qa-pick:hover { border-color: var(--primary); color: var(--primary-fg); }

/* ── Comment actions + threaded replies ── */
.comment-actions { display: flex; align-items: center; gap: var(--space-3); margin-top: .35rem; flex-wrap: wrap; }
.comment-reply-btn { font-size: var(--text-xs); font-weight: var(--weight-semibold); padding: .15rem .1rem; border: none; background: none; color: var(--muted); cursor: pointer; min-height: 44px; min-width: 44px; display: inline-flex; align-items: center; justify-content: center; }
.comment-reply-btn:hover { color: var(--primary-fg); }
.thread-subreply { display: flex; gap: var(--space-2); margin-top: var(--space-3); padding-left: var(--space-2); border-left: 2px solid var(--line); }
.subreply-body { flex: 1; min-width: 0; }
.subreply-body .comment-reply-btn { margin-top: .25rem; }
.avatar-xs { width: 26px; height: 26px; font-size: 11px; }
.reply-context { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); font-size: var(--text-xs); color: var(--ink-700); background: var(--bg-alt); border-radius: var(--radius-sm); padding: .3rem .6rem; margin-bottom: var(--space-2); }
.reply-context-x { background: none; border: none; color: var(--muted); font-size: 1.1rem; line-height: 1; cursor: pointer; }
.reply-context-x:hover { color: var(--ink); }
.thread-detail-page { max-width: 680px; margin: 0 auto; }
.thread-detail { display: flex; flex-direction: column; }

/* ── Section rhythm: clear break between post & comments ── */
.thread-comments { margin-top: var(--space-6); padding-top: var(--space-5); border-top: .5px solid var(--line); }

/* ── Replies header ── */
.replies-header {
  display: flex; align-items: center; gap: var(--space-2);
  padding: 0 0 var(--space-4);
}
.replies-icon { color: var(--primary-fg); flex-shrink: 0; }
.replies-label { font-size: var(--text-base); font-weight: var(--weight-semibold); color: var(--ink); letter-spacing: .01em; }
.replies-count {
  font-size: var(--text-xs); font-weight: var(--weight-semibold);
  background: var(--bg-alt); color: var(--muted); border-radius: var(--radius-full);
  padding: 2px 9px; min-width: 22px; text-align: center; line-height: 1.6;
}
.replies-count--active {
  background: rgba(var(--primary-rgb), .12); color: var(--primary-fg);
}

/* ── Comment compose (Threads style) ── */
.thread-comment-compose {
  display: flex; gap: var(--space-3); padding: var(--space-3) 0 var(--space-4);
  border-bottom: .5px solid var(--line);
  transition: border-color .2s;
}
.thread-comment-compose:focus-within { border-bottom-color: var(--ink); }
.thread-comment-compose .compose-left { width: 32px; flex-shrink: 0; display: flex; justify-content: center; }
.thread-comment-compose .compose-right { flex: 1; display: flex; gap: var(--space-2); align-items: center; }
.compose-input-sm {
  flex: 1; border: none; border-bottom: 2px solid transparent; background: transparent; color: var(--ink);
  font-size: var(--text-sm); line-height: var(--leading-relaxed);
  outline: none; font-family: inherit; min-height: 44px; padding: 0;
  transition: border-color .2s var(--ease-out);
}
.compose-input-sm::placeholder { color: var(--ink-tertiary, var(--muted)); }
.compose-input-sm:focus { border-bottom-color: var(--primary-fg); box-shadow: none; }
.compose-send {
  width: 44px; height: 44px; min-height: 44px; padding: 0;
  display: inline-flex; align-items: center; justify-content: center; border-radius: var(--radius-full);
  transition: transform .2s var(--ease-out), box-shadow .2s var(--ease-out), background .2s var(--ease-out);
}
.compose-send:hover:not(:disabled) { transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.compose-send .spinner-sm { width: 14px; height: 14px; color: var(--primary-fg); }

.thread-comment-guest { padding: var(--space-3) 0 var(--space-4); border-bottom: .5px solid var(--line); }
.guest-reply-link { font-size: var(--text-sm); color: var(--primary-fg); text-decoration: none; font-weight: var(--weight-medium); border-radius: var(--radius-sm); }
.guest-reply-link:hover { text-decoration: underline; }
.guest-reply-link:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

/* ── Thread replies ── */
.thread-comments { display: flex; flex-direction: column; }
/* (section rhythm spacing for .thread-comments defined above) */

.thread-reply {
  display: flex; gap: var(--space-3); padding: var(--space-3) var(--space-2);
  border-bottom: .5px solid var(--line);
  animation: replyIn .3s var(--ease-out) both;
  border-radius: var(--radius-sm); margin: 0 calc(var(--space-2) * -1);
  transition: background .3s var(--ease-out);
}
.thread-reply:hover { background: var(--overlay-subtle); }
.thread-reply:last-child { border-bottom: none; }

.thread-reply .thread-left { width: 32px; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.thread-reply .thread-line { flex: 1; width: 2px; background: var(--line); border-radius: 1px; min-height: 16px; transition: background .3s var(--ease-out); }
.thread-reply:hover .thread-line { background: var(--primary-fg); }
.thread-reply .thread-right { flex: 1; min-width: 0; }

.reply-text { margin: var(--space-1) 0 0; font-size: var(--text-sm); line-height: var(--leading-relaxed); color: var(--ink); }

@keyframes replyIn { from { opacity: 0; transform: translateY(4px); } }

.comment-empty {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-8) var(--space-4); text-align: center;
  background: var(--bg-warm); border-radius: var(--radius-lg);
}
.comment-empty-halo {
  display: inline-flex; align-items: center; justify-content: center;
  width: 64px; height: 64px; border-radius: var(--radius-full);
  background: rgba(var(--accent-rgb), .08); margin-bottom: var(--space-1);
}
.comment-empty-icon { font-size: var(--text-2xl, 1.75rem); opacity: .8; }
.comment-empty p { margin: 0; color: var(--ink); font-size: var(--text-sm); font-weight: var(--weight-medium); }
.comment-empty-hint { color: var(--muted); font-size: var(--text-xs); font-weight: var(--weight-normal); }
.empty-state-wrap { padding: var(--space-8) 0; text-align: center; }
.dark .comment-empty { background: rgba(255,255,255,.03); }

.feed-loading { text-align: center; padding: var(--space-5); }
.feed-loading .spinner { margin: 0 auto; }

/* ── Post-detail loading skeleton (reduces CLS vs blank) ── */
.thread-detail-skeleton-comments { margin-top: var(--space-6); padding-top: var(--space-5); border-top: .5px solid var(--line); }

.avatar-sm { width: 32px; height: 32px; font-size: var(--text-xs); }

/* ── Reading experience: full content on detail page (no line-clamp) ── */
.thread-detail-page :deep(.thread-content) {
  -webkit-line-clamp: unset; line-clamp: unset; display: block;
  font-size: var(--text-base); line-height: var(--leading-relaxed, 1.65);
  max-width: 65ch; overflow: visible;
}
.thread-detail-page :deep(.thread-body) { cursor: default; }

/* ── Focus-visible & keyboard nav in replies ── */
.thread-reply .thread-author:focus-visible,
.thread-reply .thread-avatar-link:focus-visible {
  outline: 2px solid var(--primary); outline-offset: 2px; border-radius: var(--radius-sm);
}

/* ── Related posts ── */
.related-section { margin-top: var(--space-6); padding-top: var(--space-5); border-top: .5px solid var(--line); }
.related-title { font-size: var(--text-lg); font-weight: var(--weight-bold); margin: 0 0 var(--space-3); }
.related-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-3); }
.related-card {
  display: flex; flex-direction: column; background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-lg); overflow: hidden; text-decoration: none; color: var(--ink);
  transition: border-color .2s, transform .2s var(--ease-spring-gentle);
}
.related-card:hover { border-color: var(--primary-fg); transform: translateY(-1px); }
.related-thumb { width: 100%; height: 100px; object-fit: cover; }
.related-body { padding: var(--space-2) var(--space-3); display: flex; flex-direction: column; gap: .2rem; }
.related-author { font-size: var(--text-xs); font-weight: var(--weight-semibold); }
.related-text { margin: 0; font-size: var(--text-xs); color: var(--ink-secondary, var(--ink)); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.related-meta { font-size: var(--text-xs); color: var(--muted); }
@media (max-width: 480px) { .related-grid { grid-template-columns: 1fr; } }

@media (prefers-reduced-motion: reduce) {
  .thread-reply { animation: none; }
  .compose-input-sm, .compose-send { transition: none; }
  .compose-send:hover:not(:disabled) { transform: none; }
}
</style>
