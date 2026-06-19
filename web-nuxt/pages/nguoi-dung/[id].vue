<template>
  <section class="page user-profile-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cộng đồng', to: '/cong-dong' }, { label: profile?.display_name || 'Người dùng' }]" />

    <div v-if="profile" class="user-profile reveal">
      <div class="profile-cover">
        <UserCoverPlaceholder />
        <div class="profile-avatar-wrap">
          <span v-if="profile.avatar" class="avatar avatar-xl">
            <img :src="profile.avatar" :alt="profile.display_name" loading="lazy" decoding="async" width="96" height="96" />
          </span>
          <span v-else class="avatar avatar-xl">{{ initial }}</span>
        </div>
      </div>

      <div class="profile-info">
        <div class="profile-name-row">
          <h1>{{ profile.display_name || profile.phone || 'Người dùng' }}</h1>
          <button type="button"
            v-if="isLoggedIn && !isSelf"
            :class="['btn btn-sm', isFollowing ? 'btn-ghost' : 'btn-primary']"
            :disabled="followLoading"
            @click="toggleFollow"
          >
            {{ isFollowing ? 'Đang theo dõi' : 'Theo dõi' }}
          </button>
          <NuxtLink v-if="isSelf" to="/cai-dat" class="btn btn-ghost btn-sm">
            <svg class="icon-inline" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>Sửa hồ sơ
          </NuxtLink>
        </div>
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
            <strong>{{ followerCount }}</strong>
            <span>theo dõi</span>
          </div>
          <div class="stat-item">
            <time v-if="profile.created_at" :datetime="profile.created_at"><strong>{{ joinDate }}</strong></time>
            <strong v-else>{{ joinDate }}</strong>
            <span>tham gia</span>
          </div>
        </div>
      </div>

      <div class="profile-tabs">
        <button type="button" :class="['chip', { active: tab === 'posts' }]" @click="tab = 'posts'">Bài viết</button>
        <button type="button" :class="['chip', { active: tab === 'reviews' }]" @click="tab = 'reviews'">Đánh giá</button>
      </div>

      <div class="feed-main">
        <TransitionGroup name="post-list" tag="div">
          <PostCard
            v-for="post in filteredPosts"
            :key="post.id"
            :post="post"
            @like="toggleLike"
            @comment="id => navigateTo(`/bai-viet/${id}`)"
            @bookmark="toggleBookmark"
            @report="reportPost"
          />
        </TransitionGroup>
        <Transition name="fade">
          <EmptyState v-if="!filteredPosts.length && !loading" :message="tab === 'reviews' ? 'Chưa có đánh giá nào.' : 'Chưa có bài viết nào.'" />
        </Transition>
        <div v-if="loading" class="profile-loading" role="status" aria-label="Đang tải"><div class="spinner"></div></div>
      </div>
    </div>

    <EmptyState v-else-if="profileFetchFailed" icon="⚠️" title="Không thể tải trang" message="Lỗi kết nối. Vui lòng thử lại.">
      <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData(`user-${userId}`)">Thử lại</button>
    </EmptyState>
    <EmptyState v-else message="Không tìm thấy người dùng." />
  </section>
</template>

<script setup lang="ts">
useReveal()
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
const isFollowing = ref(false)
const followLoading = ref(false)
const followerCount = ref(0)
const isSelf = computed(() => {
  const { user } = useAuth()
  return user.value?.id === userId
})

const profileFetchFailed = ref(false)
const { data: profile } = await useAsyncData(`user-${userId}`, async () => {
  try {
    profileFetchFailed.value = false
    return await $fetch<any>(`/api/users/${userId}`, { headers: authHeaders() })
  } catch {
    profileFetchFailed.value = true
    return null
  }
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
  } catch { showToast('Không thể thích bài viết', 'error') }
}

async function toggleBookmark(postId: string) {
  if (!isLoggedIn.value) return
  try {
    await $fetch(`/api/posts/${postId}/bookmark`, { method: 'POST', headers: authHeaders() })
    const post = posts.value.find(p => p.id === postId)
    if (post) post.user_bookmarked = !post.user_bookmarked
  } catch { showToast('Không thể lưu bài viết', 'error') }
}

async function fetchFollowerCount() {
  try {
    const res = await $fetch<any>(`/api/followers/count/user/${userId}`)
    followerCount.value = res.count || 0
  } catch { /* non-critical */ }
}

async function checkFollowing() {
  if (!isLoggedIn.value) return
  try {
    const res = await $fetch<any>('/api/following?target_type=user', { headers: authHeaders() })
    const following = res.following || res || []
    isFollowing.value = following.some((f: any) => f.target_id === userId)
  } catch { /* non-critical */ }
}

async function toggleFollow() {
  if (!isLoggedIn.value) { showToast('Đăng nhập để theo dõi', 'info'); return }
  followLoading.value = true
  const was = isFollowing.value
  isFollowing.value = !was
  followerCount.value += was ? -1 : 1
  try {
    await $fetch(`/api/follow/user/${userId}`, { method: 'POST', headers: authHeaders() })
  } catch {
    isFollowing.value = was
    followerCount.value += was ? 1 : -1
    showToast('Không thể theo dõi', 'error')
  }
  followLoading.value = false
}

onMounted(() => {
  fetchPosts()
  fetchFollowerCount()
  checkFollowing()
})

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

<style scoped>
.profile-loading { text-align: center; padding: var(--space-5) 0; }
.profile-loading .spinner { margin: 0 auto; }

.profile-cover { position: relative; border-radius: var(--radius-xl, 20px); overflow: hidden; margin-bottom: calc(-1 * var(--space-8)); }
.profile-avatar-wrap { position: absolute; bottom: calc(-1 * var(--space-6)); left: var(--space-5); }
.profile-avatar-wrap .avatar { border: 3px solid var(--card); box-shadow: var(--shadow-md); transition: transform .35s var(--ease-spring-gentle); }
.profile-avatar-wrap .avatar:hover { transform: scale(1.05); }
.profile-avatar-wrap .avatar:active { transform: scale(.98); transition-duration: .08s; }

.profile-info { padding-top: var(--space-10); }
.user-profile-page { max-width: 680px; margin: 0 auto; }
.profile-name-row { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.profile-name-row h1 { flex: 1; min-width: 0; }
.profile-info h1 { font-size: clamp(1.25rem, 2.5vw, 1.75rem); font-weight: var(--weight-bold); letter-spacing: var(--tracking-tight); margin: 0; }
.profile-bio { color: var(--ink-secondary); font-size: var(--text-sm); line-height: var(--leading-relaxed); margin-top: var(--space-2); }

.profile-stats { display: flex; gap: var(--space-6); margin-top: var(--space-4); }
.stat-item { display: flex; flex-direction: column; align-items: center; gap: var(--space-1); padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); cursor: default; transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out); }
.stat-item:hover { background: var(--bg-alt); transform: translateY(-1px); box-shadow: var(--shadow-xs); }
.stat-item:active { transform: scale(.95); transition-duration: .08s; }
.stat-item strong { font-size: var(--text-lg); font-weight: var(--weight-bold); }
.stat-item span { font-size: var(--text-xs); color: var(--muted); }

.profile-tabs { display: flex; gap: var(--space-2); margin: var(--space-5) 0 var(--space-4); border-bottom: .5px solid var(--line); padding-bottom: var(--space-3); }
.profile-tabs .chip { min-height: 44px; transition: transform .35s var(--ease-spring-gentle), background .3s var(--ease-out), color .3s var(--ease-out), border-color .3s var(--ease-out); }
.profile-tabs .chip:active { transform: scale(.95); transition-duration: .08s; }

/* Post list transitions */
.post-list-enter-active { transition: opacity .35s var(--ease-out), transform .4s var(--ease-spring-gentle); }
.post-list-leave-active { transition: opacity .2s var(--ease-out), transform .2s var(--ease-out); }
.post-list-enter-from { opacity: 0; transform: translateY(8px); }
.post-list-leave-to { opacity: 0; transform: translateY(-4px); }
.post-list-move { transition: transform .35s var(--ease-spring-gentle); }

/* Fade */
.fade-enter-active { transition: opacity .3s var(--ease-out); }
.fade-leave-active { transition: opacity .15s var(--ease-out); }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* Follow button spring */
.profile-name-row .btn { transition: transform .35s var(--ease-spring-gentle), background .3s var(--ease-out), color .3s var(--ease-out), border-color .3s var(--ease-out); }
.profile-name-row .btn:active { transform: scale(.92); transition-duration: .08s; }

/* Dark mode */
.dark .profile-cover { border-color: var(--line); }
.dark .profile-avatar-wrap .avatar { border-color: var(--bg); }
.dark .stat-item:hover { background: rgba(255,255,255,.04); }
.dark .profile-tabs { border-bottom-color: var(--line); }

@media (prefers-reduced-motion: reduce) {
  .post-list-enter-active, .post-list-leave-active, .post-list-move { transition: none; }
  .profile-avatar-wrap .avatar:hover { transform: none; }
  .stat-item:hover { transform: none; }
  .profile-tabs .chip:active { transform: none; }
}
</style>
