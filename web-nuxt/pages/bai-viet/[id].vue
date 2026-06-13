<template>
  <section class="page">
    <NuxtLink class="back" to="/cong-dong">← Cộng đồng</NuxtLink>

    <div v-if="post" style="max-width: 720px">
      <PostCard :post="post" @like="toggleLike" @bookmark="toggleBookmark" @report="reportPost" />

      <!-- Comments -->
      <div class="comment-section">
        <h3 class="comment-title">💬 Bình luận ({{ comments.length }})</h3>

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

        <p v-if="!comments.length" class="empty" style="padding: 10px 0">Chưa có bình luận.</p>
      </div>
    </div>

    <p v-else class="empty">Không tìm thấy bài viết.</p>
  </section>
</template>

<script setup lang="ts">
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

async function fetchComments() {
  try {
    const res = await $fetch<any>(`/api/posts/${postId}/comments`)
    comments.value = res.comments || res || []
  } catch { /* ignore */ }
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
  } catch { /* ignore */ }
}

async function toggleLike(id: string) {
  if (!isLoggedIn.value || !post.value) return
  try {
    await $fetch(`/api/posts/${id}/like`, { method: 'POST', headers: authHeaders() })
    post.value.user_liked = !post.value.user_liked
    post.value.likes = (post.value.likes || 0) + (post.value.user_liked ? 1 : -1)
  } catch { /* ignore */ }
}

async function toggleBookmark(id: string) {
  if (!isLoggedIn.value || !post.value) return
  try {
    await $fetch(`/api/posts/${id}/bookmark`, { method: 'POST', headers: authHeaders() })
    post.value.user_bookmarked = !post.value.user_bookmarked
  } catch { /* ignore */ }
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
