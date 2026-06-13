<template>
  <section class="page">
    <NuxtLink class="back" to="/cong-dong">← Cộng đồng</NuxtLink>

    <div v-if="profile" class="user-profile">
      <div class="profile-cover">
        <UserCoverPlaceholder />
        <div class="profile-avatar-wrap">
          <span v-if="profile.avatar" class="avatar avatar-xl">
            <img :src="profile.avatar" :alt="profile.display_name" />
          </span>
          <span v-else class="avatar avatar-xl">{{ initial }}</span>
        </div>
      </div>

      <div class="profile-info">
        <h1>{{ profile.display_name || profile.phone || 'Người dùng' }}</h1>
        <p v-if="profile.bio" class="profile-bio">{{ profile.bio }}</p>
        <div class="profile-stats">
          <div class="stat-item">
            <strong>{{ profile.post_count || 0 }}</strong>
            <span>bài viết</span>
          </div>
          <div class="stat-item">
            <strong>{{ profile.review_count || 0 }}</strong>
            <span>đánh giá</span>
          </div>
          <div class="stat-item">
            <strong>{{ joinDate }}</strong>
            <span>tham gia</span>
          </div>
        </div>
      </div>

      <div class="profile-tabs">
        <button :class="['chip', { active: tab === 'posts' }]" @click="tab = 'posts'">Bài viết</button>
        <button :class="['chip', { active: tab === 'reviews' }]" @click="tab = 'reviews'">Đánh giá</button>
      </div>

      <div class="feed-main">
        <PostCard
          v-for="post in filteredPosts"
          :key="post.id"
          :post="post"
          @like="toggleLike"
          @comment="id => navigateTo(`/bai-viet/${id}`)"
          @bookmark="toggleBookmark"
          @report="reportPost"
        />
        <EmptyState v-if="!filteredPosts.length && !loading" :message="tab === 'reviews' ? 'Chưa có đánh giá nào.' : 'Chưa có bài viết nào.'" />
        <div v-if="loading" style="text-align: center; padding: 20px"><div class="spinner" style="margin: 0 auto"></div></div>
      </div>
    </div>

    <EmptyState v-else message="Không tìm thấy người dùng." />
  </section>
</template>

<script setup lang="ts">
const route = useRoute()
const userId = route.params.id as string
const { isLoggedIn, authHeaders } = useAuth()
const { show: showToast } = useToast()
const { reportPost } = useReport()

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl(`/nguoi-dung/${userId}`) }],
  meta: [{ name: 'robots', content: 'noindex,follow' }],
})

const tab = ref('posts')
const posts = ref<any[]>([])
const loading = ref(false)

const { data: profile } = await useAsyncData(`user-${userId}`, async () => {
  try {
    return await $fetch<any>(`/api/users/${userId}`, { headers: authHeaders() })
  } catch { return null }
})

const initial = computed(() => {
  const name = profile.value?.display_name || profile.value?.phone || '?'
  return name.charAt(0).toUpperCase()
})

const joinDate = computed(() => {
  if (!profile.value?.created_at) return ''
  return new Date(profile.value.created_at).toLocaleDateString('vi-VN')
})

const filteredPosts = computed(() => {
  if (tab.value === 'reviews') return posts.value.filter(p => p.post_type === 'review')
  return posts.value
})

async function fetchPosts() {
  loading.value = true
  try {
    const res = await $fetch<any>(`/api/users/${userId}/posts?limit=50`, { headers: authHeaders() })
    posts.value = res.posts || res || []
  } catch { showToast('Không thể tải bài viết', 'error') }
  loading.value = false
}

async function toggleLike(postId: string) {
  if (!isLoggedIn.value) return
  try {
    await $fetch(`/api/posts/${postId}/like`, { method: 'POST', headers: authHeaders() })
    const post = posts.value.find(p => p.id === postId)
    if (post) {
      post.user_liked = !post.user_liked
      post.likes = (post.likes || 0) + (post.user_liked ? 1 : -1)
    }
  } catch { /* ignore */ }
}

async function toggleBookmark(postId: string) {
  if (!isLoggedIn.value) return
  try {
    await $fetch(`/api/posts/${postId}/bookmark`, { method: 'POST', headers: authHeaders() })
    const post = posts.value.find(p => p.id === postId)
    if (post) post.user_bookmarked = !post.user_bookmarked
  } catch { /* ignore */ }
}

onMounted(() => fetchPosts())

if (profile.value) {
  const profileDesc = `Trang cá nhân của ${profile.value.display_name || 'thành viên'} trên cộng đồng vinhlong360.`
  useSeoMeta({
    title: `${profile.value.display_name || 'Người dùng'} — vinhlong360`,
    description: profileDesc,
    ogTitle: `${profile.value.display_name || 'Người dùng'} — vinhlong360`,
    ogDescription: profileDesc,
    ogImage: '/icons/icon-512.png',
    robots: 'noindex,follow',
  })
}
</script>
