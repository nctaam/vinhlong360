<template>
  <section class="page">
    <NuxtLink class="back" to="/cong-dong">← Cộng đồng</NuxtLink>

    <div v-if="post" class="post-detail-wrap reveal">
      <PostCard :post="post" @like="toggleLike" @bookmark="toggleBookmark" @report="reportPost" />

      <div class="comment-section">
        <h3 class="comment-title">Bình luận ({{ comments.length }})</h3>

        <div v-if="isLoggedIn" class="comment-form">
          <input
            v-model="commentText"
            class="input"
            placeholder="Viết bình luận…"
            @keyup.enter="submitComment"
          />
          <button class="btn btn-primary btn-sm" :disabled="!commentText.trim()" @click="submitComment">Gửi</button>
        </div>

        <div v-for="c in comments" :key="c.id" class="comment-item">
          <span class="avatar avatar-sm">{{ (c.display_name || c.phone || '?').charAt(0).toUpperCase() }}</span>
          <div>
            <strong>{{ c.display_name || c.phone || 'Người dùng' }}</strong>
            <span class="comment-time"> · {{ timeAgo(c.created_at) }}</span>
            <p class="comment-text">{{ c.content }}</p>
          </div>
        </div>

        <p v-if="!comments.length" class="comment-empty">Chưa có bình luận nào. Hãy là người đầu tiên!</p>
      </div>
    </div>

    <p v-else class="empty">Không tìm thấy bài viết.</p>
  </section>
</template>

<script setup lang="ts">
useReveal()
const route = useRoute()
const postId = route.params.id as string
const { isLoggedIn, authHeaders } = useAuth()
const { reportPost } = useReport()

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl(`/bai-viet/${postId}`) }],
  meta: [{ name: 'robots', content: 'noindex,follow' }],
})

const commentText = ref('')
const comments = ref<any[]>([])

const { data: post } = await useAsyncData(`post-${postId}`, async () => {
  try {
    return await $fetch<any>(`/api/posts/${postId}`, { headers: authHeaders() })
  } catch { return null }
})

const { show: showToast } = useToast()

async function fetchComments() {
  try {
    const res = await $fetch<any>(`/api/posts/${postId}/comments`)
    comments.value = res.comments || res || []
  } catch { /* silent — comments are non-critical */ }
}

async function submitComment() {
  if (!commentText.value.trim()) return
  try {
    await $fetch(`/api/posts/${postId}/comments`, {
      method: 'POST',
      headers: authHeaders(),
      body: { content: commentText.value.trim() },
    })
    commentText.value = ''
    await fetchComments()
  } catch { showToast('Gửi bình luận thất bại', 'error') }
}

async function toggleLike(id: string) {
  if (!isLoggedIn.value || !post.value) return
  try {
    await $fetch(`/api/posts/${id}/like`, { method: 'POST', headers: authHeaders() })
    post.value.user_liked = !post.value.user_liked
    post.value.likes = (post.value.likes || 0) + (post.value.user_liked ? 1 : -1)
  } catch { showToast('Không thể thích bài viết', 'error') }
}

async function toggleBookmark(id: string) {
  if (!isLoggedIn.value || !post.value) return
  try {
    await $fetch(`/api/posts/${id}/bookmark`, { method: 'POST', headers: authHeaders() })
    post.value.user_bookmarked = !post.value.user_bookmarked
  } catch { showToast('Không thể lưu bài viết', 'error') }
}

function timeAgo(dateStr: string): string {
  if (!dateStr) return ''
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
  if (diff < 60) return 'Vừa xong'
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`
  if (diff < 604800) return `${Math.floor(diff / 86400)} ngày trước`
  return new Date(dateStr).toLocaleDateString('vi-VN')
}

onMounted(() => fetchComments())

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
    robots: 'noindex,follow',
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
.post-detail-wrap { max-width: 720px; }

.comment-section { margin-top: var(--space-5); }
.comment-title { font-size: var(--text-lg); font-weight: var(--weight-semibold); margin-bottom: var(--space-4); }

.comment-form { display: flex; gap: var(--space-2); margin-bottom: var(--space-5); padding: var(--space-3); border: .5px solid var(--line); border-radius: var(--radius-lg); background: var(--bg-alt); transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo); }
.comment-form:focus-within { border-color: var(--primary-fg); box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .1), var(--shadow-xs); }
.comment-form .input { flex: 1; border: none; background: transparent; outline: none; font-size: var(--text-sm); min-height: 44px; }
.comment-form .btn { transition: transform .35s var(--ease-spring-gentle), opacity .3s var(--ease-out); }
.comment-form .btn:active { transform: scale(.95); }

.comment-item { display: flex; gap: var(--space-3); padding: var(--space-3) 0; border-bottom: .5px solid var(--line); transition: background .3s var(--ease-out); }
.comment-item:last-child { border-bottom: none; }
.comment-item:hover { background: var(--bg-alt); }
.comment-time { color: var(--muted); font-size: var(--text-xs); }
.comment-text { margin-top: var(--space-1); font-size: var(--text-sm); line-height: var(--leading-relaxed); }

.comment-empty { color: var(--muted); font-size: var(--text-sm); padding: var(--space-6) 0; text-align: center; }

</style>
