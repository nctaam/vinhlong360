<template>
  <section class="page thread-detail-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cộng đồng', to: '/cong-dong' }, { label: 'Bài viết' }]" />
    <h1 class="sr-only">{{ post?.display_name ? `Bài viết của ${post.display_name}` : 'Bài viết' }}</h1>

    <div v-if="post" class="thread-detail reveal">
      <PostCard :post="post" :has-replies="comments.length > 0" @like="toggleLike" @comment="scrollToCompose" @bookmark="toggleBookmark" @report="reportPost" />

      <!-- Comment thread -->
      <div class="thread-comments">
        <div class="replies-header">
          <svg class="replies-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
          <span class="replies-label">Trả lời</span>
          <span v-if="comments.length" class="replies-count" :class="{ 'replies-count--active': comments.length > 0 }">{{ comments.length }}</span>
        </div>

        <!-- Comment form (Threads style) -->
        <div v-if="isLoggedIn" ref="composeRef" class="thread-comment-compose">
          <div class="compose-left">
            <span class="avatar thread-avatar avatar-sm">{{ userInitial }}</span>
          </div>
          <div class="compose-right">
            <input
              v-model="commentText"
              class="compose-input-sm"
              maxlength="500"
              :placeholder="`Trả lời ${post.display_name || 'bài viết'}…`"
              @keyup.enter="submitComment"
            />
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
            <NuxtLink v-if="c.author?.id" :to="`/nguoi-dung/${c.author?.id}`" class="thread-avatar-link">
              <span class="avatar thread-avatar avatar-sm">{{ (c.author?.display_name || '?').charAt(0).toUpperCase() }}</span>
            </NuxtLink>
            <span v-else class="avatar thread-avatar avatar-sm">{{ (c.author?.display_name || '?').charAt(0).toUpperCase() }}</span>
            <div v-if="idx < comments.length - 1" class="thread-line"></div>
          </div>
          <div class="thread-right">
            <div class="thread-head">
              <NuxtLink v-if="c.author?.id" :to="`/nguoi-dung/${c.author?.id}`" class="thread-author">
                {{ c.author?.display_name || 'Người dùng' }}
              </NuxtLink>
              <span v-else class="thread-author">{{ c.author?.display_name || 'Người dùng' }}</span>
              <time class="thread-time" :datetime="c.created_at">{{ timeAgo(c.created_at) }}</time>
            </div>
            <p class="thread-content reply-text">{{ c.content }}</p>
          </div>
        </div>

        <div v-if="!comments.length && !loading" class="comment-empty">
          <span class="comment-empty-halo"><span class="comment-empty-icon">💬</span></span>
          <p>Chưa có bình luận nào.</p>
          <p class="comment-empty-hint">{{ isLoggedIn ? 'Hãy là người đầu tiên trả lời!' : 'Đăng nhập để bình luận.' }}</p>
        </div>
        <div v-if="loading" class="feed-loading" role="status" aria-label="Đang tải bình luận"><div class="spinner"></div></div>
      </div>
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
const postId = route.params.id as string
const { isLoggedIn, authHeaders, user } = useAuth()
const { openAuth } = useAuthModal()
const { reportPost } = useReport()
const { show: showToast } = useToast()

const commentText = ref('')
const comments = ref<Entity[]>([])
const submitting = ref(false)
const loading = ref(true)
const composeRef = ref<HTMLElement>()

function scrollToCompose() {
  composeRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  nextTick(() => {
    const input = composeRef.value?.querySelector('input')
    input?.focus()
  })
}

const userInitial = computed(() => {
  const name = user.value?.display_name || user.value?.phone || '?'
  return name.charAt(0).toUpperCase()
})

const postFetchFailed = ref(false)
const { data: post, pending } = await useAsyncData(`post-${postId}`, async () => {
  try {
    postFetchFailed.value = false
    const res = await $fetch<Post>(`/api/posts/${postId}`, { headers: authHeaders() })
    return res?.post || res
  } catch {
    postFetchFailed.value = true
    return null
  }
})

async function fetchComments() {
  loading.value = true
  try {
    const res = await $fetch<Post>(`/api/posts/${postId}/comments`)
    comments.value = res.comments || res || []
  } catch { /* comments are non-critical */ }
  loading.value = false
}

async function submitComment() {
  if (!commentText.value.trim() || submitting.value) return
  submitting.value = true
  try {
    await $fetch(`/api/posts/${postId}/comments`, {
      method: 'POST',
      headers: authHeaders(),
      body: { content: commentText.value.trim() },
    })
    commentText.value = ''
    showToast('Đã gửi bình luận', 'success')
    if (post.value) post.value.comments_count = (post.value.comments_count || 0) + 1
    await fetchComments()
  } catch { showToast('Gửi bình luận thất bại', 'error') }
  submitting.value = false
}

async function toggleLike(id: string) {
  if (!isLoggedIn.value) { showToast('Đăng nhập để thích bài viết', 'info'); return }
  if (!post.value) return
  post.value.user_liked = !post.value.user_liked
  post.value.likes = (post.value.likes || 0) + (post.value.user_liked ? 1 : -1)
  try {
    await $fetch(`/api/posts/${id}/like`, { method: 'POST', headers: authHeaders() })
  } catch {
    post.value.user_liked = !post.value.user_liked
    post.value.likes = (post.value.likes || 0) + (post.value.user_liked ? 1 : -1)
    showToast('Không thể thích bài viết', 'error')
  }
}

async function toggleBookmark(id: string) {
  if (!isLoggedIn.value) { showToast('Đăng nhập để lưu bài viết', 'info'); return }
  if (!post.value) return
  post.value.user_bookmarked = !post.value.user_bookmarked
  try {
    await $fetch(`/api/posts/${id}/bookmark`, { method: 'POST', headers: authHeaders() })
  } catch {
    post.value.user_bookmarked = !post.value.user_bookmarked
    showToast('Không thể lưu bài viết', 'error')
  }
}

const { timeAgo } = useTimeAgo()

onMounted(() => fetchComments())

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl(`/bai-viet/${postId}`) }],
  meta: [{ name: 'robots', content: 'noindex,follow' }],
})

if (post.value) {
  const p = post.value
  const postDesc = (p.content || '').substring(0, 160)
  const postTitle = p.display_name || 'Bài viết'
  useSeoMeta({
    title: `${postTitle} — vinhlong360`,
    description: postDesc,
    ogTitle: `${postTitle} — vinhlong360`,
    ogDescription: postDesc,
    ogImage: p.images?.[0] || '/icons/icon-512.png',
    // SEO-04: robots đã set ở useHead (vô-điều-kiện) → bỏ ở đây tránh thẻ trùng
  })

  const articleLd: Record<string, any> = {
    '@context': 'https://schema.org',
    '@type': p.post_type === 'review' ? 'Review' : 'Article',
    headline: postTitle,
    description: postDesc,
    url: `https://vinhlong360.vn/bai-viet/${postId}`,
    datePublished: p.created_at,
    dateModified: p.updated_at || p.created_at,
    author: {
      '@type': 'Person',
      name: p.display_name || 'Người dùng',
      ...(p.user_id ? { url: `https://vinhlong360.vn/nguoi-dung/${p.user_id}` } : {}),
    },
    publisher: { '@type': 'Organization', name: 'vinhlong360', url: 'https://vinhlong360.vn' },
  }
  if (p.images?.length) articleLd.image = p.images
  if (p.post_type === 'review' && p.rating) {
    articleLd.reviewRating = { '@type': 'Rating', ratingValue: p.rating, bestRating: 5 }
  }

  const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
      { '@type': 'ListItem', position: 2, name: 'Cộng đồng', item: 'https://vinhlong360.vn/cong-dong' },
      { '@type': 'ListItem', position: 3, name: postTitle },
    ],
  }

  useHead({
    script: [
      { type: 'application/ld+json', innerHTML: JSON.stringify(articleLd) },
      { type: 'application/ld+json', innerHTML: JSON.stringify(breadcrumb) },
    ],
  })
}
</script>

<style scoped>
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

@media (prefers-reduced-motion: reduce) {
  .thread-reply { animation: none; }
  .compose-input-sm, .compose-send { transition: none; }
  .compose-send:hover:not(:disabled) { transform: none; }
}
</style>
