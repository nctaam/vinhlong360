<template>
  <section class="page user-profile-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cộng đồng', to: '/cong-dong' }, { label: profile?.display_name || 'Người dùng' }]" />

    <div v-if="profile" class="user-profile reveal">
      <div class="profile-cover">
        <img v-if="profile.cover_url" :src="profile.cover_url" :alt="`Ảnh bìa ${profile.display_name}`" class="cover-img" loading="eager" decoding="async" />
        <UserCoverPlaceholder v-else />
        <div class="cover-scrim" aria-hidden="true"></div>
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
            :aria-busy="followLoading"
            @click="toggleFollow"
          >
            <span v-if="!followLoading">{{ isFollowing ? 'Đang theo dõi' : 'Theo dõi' }}</span>
            <span v-else class="spinner spinner-sm" aria-label="Đang xử lý"></span>
          </button>
          <div v-if="isLoggedIn && !isSelf" class="profile-more-wrap">
            <button type="button" class="btn btn-ghost btn-sm btn-icon" aria-label="Thêm" @click="showMoreMenu = !showMoreMenu">&#8226;&#8226;&#8226;</button>
            <div v-if="showMoreMenu" class="profile-more-menu" @click="showMoreMenu = false">
              <button type="button" class="pm-item" @click="toggleBlock">{{ isBlocked ? 'Bỏ chặn' : 'Chặn người này' }}</button>
              <button type="button" class="pm-item pm-danger" @click="reportUser">Báo cáo</button>
            </div>
          </div>
          <NuxtLink v-if="isSelf" to="/cai-dat" class="btn btn-ghost btn-sm">
            <svg class="icon-inline" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>Sửa hồ sơ
          </NuxtLink>
        </div>
        <p v-if="profile.bio" class="profile-bio">{{ profile.bio }}</p>
        <div v-if="profile.reputation" class="profile-reputation">
          <NuxtLink to="/huong-dan-thanh-vien" class="rep-level" :data-level="profile.reputation.level" title="Xem hướng dẫn cấp bậc">
            {{ levelIcon(profile.reputation.level) }} {{ profile.reputation.level_label }}
          </NuxtLink>
          <span v-for="b in profile.reputation.badges" :key="b.id" class="rep-badge" :title="b.label">
            {{ b.icon }} {{ b.label }}
          </span>
        </div>
        <div class="profile-stats">
          <div class="stat-item">
            <strong>{{ profile.post_count || 0 }}</strong>
            <span>bài viết</span>
          </div>
          <div class="stat-item">
            <strong>{{ profile.review_count || 0 }}</strong>
            <span>đánh giá</span>
          </div>
          <button type="button" class="stat-item stat-clickable" @click="openFollowModal('followers')">
            <strong>{{ followerCount }}</strong>
            <span>người theo dõi</span>
          </button>
          <button type="button" class="stat-item stat-clickable" @click="openFollowModal('following')">
            <strong>{{ profile.following_count || 0 }}</strong>
            <span>đang theo dõi</span>
          </button>
          <div class="stat-item">
            <time v-if="profile.created_at" :datetime="profile.created_at"><strong>{{ joinDate }}</strong></time>
            <strong v-else>{{ joinDate }}</strong>
            <span>tham gia</span>
          </div>
        </div>
      </div>

      <div v-if="isSelf && profileCompletion < 100" class="profile-completion">
        <div class="pc-row">
          <span class="pc-label">Hồ sơ hoàn thiện {{ profileCompletion }}%</span>
          <NuxtLink to="/cai-dat" class="pc-link">Hoàn thiện</NuxtLink>
        </div>
        <div class="pc-bar"><div class="pc-fill" :style="{ width: profileCompletion + '%' }"></div></div>
        <div class="pc-hints">
          <span v-if="!profile.display_name" class="pc-hint">Thêm tên hiển thị</span>
          <span v-if="!profile.avatar" class="pc-hint">Thêm ảnh đại diện</span>
          <span v-if="!profile.bio" class="pc-hint">Viết giới thiệu</span>
          <span v-if="(profile.post_count || 0) === 0" class="pc-hint">Đăng bài đầu tiên</span>
          <span v-if="(profile.review_count || 0) === 0" class="pc-hint">Viết đánh giá</span>
        </div>
      </div>

      <div v-if="profile.is_private" class="profile-private-notice">
        <p>🔒 Hồ sơ riêng tư — theo dõi để xem nội dung.</p>
      </div>

      <div v-else class="profile-tabs">
        <button type="button" :class="['chip', { active: tab === 'posts' }]" :aria-pressed="tab === 'posts'" @click="tab = 'posts'">Bài viết</button>
        <button type="button" :class="['chip', { active: tab === 'reviews' }]" :aria-pressed="tab === 'reviews'" @click="tab = 'reviews'">Đánh giá</button>
        <button type="button" v-if="isSelf" :class="['chip', { active: tab === 'saved' }]" :aria-pressed="tab === 'saved'" @click="tab = 'saved'">
          Đã lưu<ClientOnly><span v-if="savedCount > 0" class="tab-count">{{ savedCount }}</span></ClientOnly>
        </button>
      </div>

      <div v-if="!profile.is_private" class="feed-main">
        <!-- Đã lưu (self only, client-only — từ localStorage) -->
        <ClientOnly v-if="tab === 'saved'">
          <div v-if="favorites.length" class="saved-grid">
            <NuxtLink v-for="fav in favorites" :key="fav.id" :to="`/dia-diem/${fav.id}`" class="card saved-card">
              <div v-if="fav.image" class="cover cover-img">
                <img :src="fav.image" :alt="fav.name" loading="lazy" decoding="async" width="400" height="160" />
              </div>
              <div class="card-b">
                <span class="card-type">{{ getSavedTypeMeta(fav.type).label }}</span>
                <h3>{{ fav.name }}</h3>
                <p v-if="fav.place_name" class="place">{{ fav.place_name }}</p>
              </div>
            </NuxtLink>
          </div>
          <div v-if="favorites.length" class="saved-cta">
            <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-primary btn-sm">📋 Tạo lịch trình từ danh sách đã lưu</NuxtLink>
          </div>
          <EmptyState
            v-else
            icon="❤️"
            title="Chưa lưu địa điểm nào"
            message="Lưu địa điểm yêu thích để xem lại nhanh và ghép vào lịch trình."
            hint="Nhấn nút lưu ở bất kỳ địa điểm nào để bắt đầu."
          >
            <NuxtLink to="/du-lich" class="btn btn-primary btn-sm">Khám phá địa điểm</NuxtLink>
          </EmptyState>
        </ClientOnly>

        <template v-else>
          <TransitionGroup name="post-list" tag="div">
            <PostCard
              v-for="post in filteredPosts"
              :key="post.id"
              :post="post"
              @like="toggleLike"
              @comment="id => navigateTo(`/bai-viet/${id}`)"
              @bookmark="toggleBookmark"
              @report="reportPost"
              @repost="repost"
              @quote="quote"
              @edit="(id) => navigateTo(`/bai-viet/${id}?edit=1`)"
              @delete="deletePost"
            />
          </TransitionGroup>
          <Transition name="fade">
            <EmptyState
              v-if="!filteredPosts.length && !loading"
              :icon="tab === 'reviews' ? '⭐' : '✍️'"
              :title="tab === 'reviews' ? 'Chưa có đánh giá' : 'Chưa có bài viết'"
              :message="tab === 'reviews' ? 'Chưa có đánh giá nào.' : 'Chưa có bài viết nào.'"
              :hint="emptyHint"
            >
              <NuxtLink v-if="isSelf" to="/cong-dong" class="btn btn-primary btn-sm">
                {{ tab === 'reviews' ? 'Viết đánh giá đầu tiên' : 'Viết bài viết đầu tiên' }}
              </NuxtLink>
            </EmptyState>
          </Transition>
          <SkeletonList v-if="loading && !posts.length" :count="3" class="profile-skeleton" />
          <div v-else-if="loading" class="profile-loading" role="status" aria-label="Đang tải"><div class="spinner"></div></div>
        </template>
      </div>
    </div>

    <EmptyState v-else-if="profileFetchFailed" icon="⚠️" tone="error" title="Không thể tải trang" message="Lỗi kết nối. Vui lòng thử lại.">
      <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData(`user-${userId}`)">Thử lại</button>
    </EmptyState>
    <EmptyState v-else message="Không tìm thấy người dùng." />

    <!-- Modal danh sách theo dõi -->
    <Teleport to="body">
      <div v-if="followModalOpen" class="fm-overlay" @click.self="followModalOpen = false">
        <div class="fm-dialog" role="dialog" aria-modal="true" aria-label="Danh sách theo dõi">
          <header class="fm-head">
            <div class="fm-tabs">
              <button type="button" :class="['fm-tab', { active: followModalTab === 'followers' }]" @click="followModalTab = 'followers'">Người theo dõi</button>
              <button type="button" :class="['fm-tab', { active: followModalTab === 'following' }]" @click="followModalTab = 'following'">Đang theo dõi</button>
            </div>
            <button type="button" class="fm-close" aria-label="Đóng" @click="followModalOpen = false">&times;</button>
          </header>
          <div class="fm-body">
            <div v-if="followLoadingList" class="fm-loading"><div class="spinner spinner-sm"></div></div>
            <template v-else>
              <ul v-if="followModalList.length" class="fm-list">
                <li v-for="u in followModalList" :key="u.id">
                  <NuxtLink :to="`/nguoi-dung/${u.id}`" class="fm-user" @click="followModalOpen = false">
                    <span class="avatar fm-avatar">{{ (u.display_name || '?').charAt(0).toUpperCase() }}</span>
                    <span class="fm-name">{{ u.display_name }}</span>
                  </NuxtLink>
                </li>
              </ul>
              <p v-else class="fm-empty">{{ followModalTab === 'followers' ? 'Chưa có người theo dõi.' : 'Chưa theo dõi ai.' }}</p>
            </template>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { TYPE_META } from '~/composables/useConstants'
useReveal()
const route = useRoute()
const userId = route.params.id as string
const { isLoggedIn, authHeaders } = useAuth()
const { show: showToast } = useToast()
const { reportPost } = useReport()
const { repost, quote } = useRepost()

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl(`/nguoi-dung/${userId}`) }],
  meta: [{ name: 'robots', content: 'noindex,follow' }],
})

const tab = ref('posts')
const posts = ref<Entity[]>([])
const { favorites, count: savedCount } = useFavorites()
const loading = ref(true)
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
    // BE trả {user:{display_name, avatar_url, bio, created_at, stats:{posts,reviews}}}
    // → unwrap + map về flat keys mà template đọc (P0-11).
    const res = await apiFetch<Record<string, any>>(`/api/users/${userId}`, { headers: authHeaders() })
    const u = (res?.user ?? res) as Record<string, any> | null
    if (!u) return null
    const mapped = {
      ...u,
      avatar: u.avatar_url ?? u.avatar ?? null,
      post_count: u.stats?.posts ?? u.post_count ?? 0,
      review_count: u.stats?.reviews ?? u.review_count ?? 0,
      follower_count: u.stats?.followers ?? 0,
      following_count: u.stats?.following ?? 0,
    }
    followerCount.value = mapped.follower_count
    return mapped
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

const profileCompletion = computed(() => {
  if (!profile.value) return 0
  const p = profile.value
  let score = 0
  if (p.display_name) score += 20
  if (p.avatar) score += 20
  if (p.bio) score += 20
  if ((p.post_count || 0) > 0) score += 20
  if ((p.review_count || 0) > 0) score += 20
  return score
})

const filteredPosts = computed(() => {
  if (tab.value === 'reviews') return posts.value.filter(p => p.post_type === 'review')
  return posts.value
})

function getSavedTypeMeta(type: string) {
  return TYPE_META[type] || { emoji: '📍', label: type, cat: 'place' }
}

function levelIcon(level: number) {
  return (['', '🌱', '🤝', '🌟', '👑'][level]) || '🌱'  // 1→4
}

const displayName = computed(() => profile.value?.display_name || profile.value?.phone || 'Người dùng')
const emptyHint = computed(() => {
  if (isSelf.value) return 'Chia sẻ trải nghiệm của bạn với cộng đồng.'
  return `Theo dõi ${displayName.value} để nhận cập nhật mới.`
})

async function fetchPosts() {
  loading.value = true
  try {
    const res = await $fetch<Record<string, unknown>>(`/api/users/${userId}/posts?limit=50`, { headers: authHeaders() })
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

async function deletePost(postId: string) {
  try {
    await $fetch(`/api/posts/${postId}`, { method: 'DELETE', headers: authHeaders() })
    posts.value = posts.value.filter(p => p.id !== postId)
    showToast('Đã xoá bài viết', 'success')
  } catch { showToast('Không thể xoá bài viết', 'error') }
}

async function toggleBookmark(postId: string) {
  if (!isLoggedIn.value) return
  try {
    await $fetch(`/api/posts/${postId}/bookmark`, { method: 'POST', headers: authHeaders() })
    const post = posts.value.find(p => p.id === postId)
    if (post) post.user_bookmarked = !post.user_bookmarked
  } catch { showToast('Không thể lưu bài viết', 'error') }
}


// ── Modal danh sách follower/following ──
const followModalOpen = ref(false)
const followModalTab = ref<'followers' | 'following'>('followers')
const followLists = ref<{ followers: any[] | null; following: any[] | null }>({ followers: null, following: null })
const followLoadingList = ref(false)
const followModalList = computed(() => followLists.value[followModalTab.value] || [])
async function loadFollowList(which: 'followers' | 'following') {
  if (followLists.value[which]) return  // đã tải (cache)
  followLoadingList.value = true
  try {
    const res = await $fetch<any>(`/api/users/${userId}/${which}`)
    followLists.value[which] = res.users || []
  } catch { followLists.value[which] = [] }
  followLoadingList.value = false
}
function openFollowModal(tab: 'followers' | 'following') {
  followModalTab.value = tab
  followModalOpen.value = true
  loadFollowList(tab)
}
watch(followModalTab, (t) => loadFollowList(t))

async function checkFollowing() {
  if (!isLoggedIn.value) return
  try {
    const res = await $fetch<Record<string, unknown>[]>('/api/following?target_type=user', { headers: authHeaders() })
    const following = res.following || res || []
    isFollowing.value = following.some((f: Entity) => f.target_id === userId)
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

// ── Block / Report ──
const showMoreMenu = ref(false)
const isBlocked = ref(false)
const { confirm } = useConfirm()

function onClickOutsideMore(e: MouseEvent) {
  const wrap = (e.target as HTMLElement)?.closest('.profile-more-wrap')
  if (!wrap) showMoreMenu.value = false
}
watch(showMoreMenu, (v) => {
  if (import.meta.client) {
    if (v) setTimeout(() => document.addEventListener('click', onClickOutsideMore), 0)
    else document.removeEventListener('click', onClickOutsideMore)
  }
})

async function checkBlocked() {
  if (!isLoggedIn.value || isSelf.value) return
  try {
    const res = await $fetch<{ users: any[] }>('/api/blocked-users', { headers: authHeaders() })
    isBlocked.value = (res.users || []).some(u => u.id === userId)
  } catch { /* non-critical */ }
}

async function toggleBlock() {
  if (isBlocked.value) {
    await $fetch(`/api/block/${userId}`, { method: 'POST', headers: authHeaders() })
    isBlocked.value = false
    showToast('Đã bỏ chặn', 'success')
    return
  }
  const ok = await confirm({
    title: `Chặn ${profile.value?.display_name || 'người dùng này'}?`,
    message: 'Họ sẽ không thấy bài viết, bình luận và hoạt động của bạn. Bạn cũng sẽ không thấy nội dung của họ.',
    confirmText: 'Chặn',
    danger: true,
  })
  if (!ok) return
  try {
    await $fetch(`/api/block/${userId}`, { method: 'POST', headers: authHeaders() })
    isBlocked.value = true
    if (isFollowing.value) { isFollowing.value = false; followerCount.value-- }
    showToast('Đã chặn người dùng', 'success')
  } catch { showToast('Không thể chặn', 'error') }
}

function reportUser() {
  showToast('Cảm ơn bạn đã báo cáo. Chúng tôi sẽ xem xét.', 'info')
}

onMounted(() => {
  fetchPosts()
  checkFollowing()
  checkBlocked()
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
.profile-reputation { display: flex; flex-wrap: wrap; gap: .4rem; margin: .25rem 0 .75rem; }
.rep-level { font-weight: var(--weight-semibold); font-size: var(--text-sm); padding: .2rem .6rem; border-radius: 999px; background: color-mix(in srgb, var(--accent) 16%, var(--bg-alt)); color: var(--accent-text, var(--ink)); text-decoration: none; transition: filter .2s; }
.rep-level:hover { filter: brightness(1.1); }
.rep-level[data-level="4"] { background: color-mix(in srgb, gold 28%, var(--bg-alt)); }
.rep-badge { font-size: var(--text-xs); padding: .2rem .55rem; border-radius: 999px; background: var(--bg-alt); border: 1px solid var(--border); color: var(--ink-700); }
.profile-loading { text-align: center; padding: var(--space-5) 0; }
.profile-loading .spinner { margin: 0 auto; }

.profile-cover { position: relative; border-radius: var(--radius-xl, 20px); overflow: hidden; margin-bottom: calc(-1 * var(--space-8)); box-shadow: var(--shadow-lg, var(--shadow-md)); }
.cover-img { width: 100%; height: 200px; object-fit: cover; display: block; }
.profile-private-notice { text-align: center; padding: var(--space-8) var(--space-4); color: var(--ink-700); font-size: .95rem; }
.cover-scrim { position: absolute; inset: 0; pointer-events: none; background: linear-gradient(to bottom, transparent 40%, rgba(0,0,0,.18)); }
.profile-avatar-wrap { position: absolute; bottom: calc(-1 * var(--space-6)); left: var(--space-5); z-index: 1; }
.profile-avatar-wrap .avatar { border: 6px solid var(--card); box-shadow: 0 0 0 2px var(--line), 0 8px 28px rgba(0,0,0,.12); transition: transform .35s var(--ease-spring-gentle); }
.profile-avatar-wrap .avatar:hover { transform: scale(1.05); }
.profile-avatar-wrap .avatar:active { transform: scale(.98); transition-duration: .08s; }

.profile-info { padding-top: var(--space-10); }
.user-profile-page { max-width: 680px; margin: 0 auto; }
.profile-name-row { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.profile-name-row h1 { flex: 1; min-width: 0; }
.profile-more-wrap { position: relative; }
.btn-icon { min-width: 32px; padding: .3rem .5rem; letter-spacing: 2px; font-weight: 700; }
.profile-more-menu { position: absolute; right: 0; top: 100%; margin-top: 4px; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius-md); box-shadow: var(--shadow-md); z-index: 50; min-width: 160px; overflow: hidden; }
.pm-item { display: block; width: 100%; text-align: left; padding: .6rem 1rem; border: none; background: none; font: inherit; font-size: var(--text-sm); color: var(--ink); cursor: pointer; transition: background .15s; }
.pm-item:hover { background: var(--bg-alt); }
.pm-danger { color: var(--danger, #c0392b); }
.pm-danger:hover { background: rgba(192,57,43,.06); }
.profile-info h1 { font-size: clamp(1.25rem, 2.5vw, 1.75rem); font-weight: var(--weight-bold); letter-spacing: var(--tracking-tight); margin: 0; text-wrap: balance; overflow-wrap: break-word; }
.profile-bio { color: var(--ink-secondary); font-size: var(--text-sm); line-height: var(--leading-relaxed); margin-top: var(--space-2); max-width: 640px; overflow-wrap: break-word; word-break: break-word; }

.profile-stats { display: flex; gap: var(--space-6); margin-top: var(--space-4); }
.stat-item { display: flex; flex-direction: column; align-items: center; gap: var(--space-1); padding: var(--space-2) var(--space-3); background: var(--bg-warm); border: .5px solid var(--line); border-radius: var(--radius-md); transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out), border-color .3s var(--ease-out); }
.stat-item:hover { background: var(--card); transform: translateY(-1px); box-shadow: var(--shadow-sm); border-color: var(--border, var(--line)); }
.stat-item:active { transform: scale(.95); transition-duration: .08s; }
.stat-item:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.stat-item strong { font-size: var(--text-lg); font-weight: var(--weight-bold); user-select: all; }
.stat-item span { font-size: var(--text-xs); color: var(--muted); }
.stat-clickable { cursor: pointer; font: inherit; }

/* Modal follower/following */
.fm-overlay { position: fixed; inset: 0; z-index: 1000; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; padding: var(--space-4); }
.fm-dialog { background: var(--card); border-radius: var(--radius-lg); width: 100%; max-width: 420px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: var(--shadow-lg); overflow: hidden; }
.fm-head { display: flex; align-items: center; justify-content: space-between; border-bottom: .5px solid var(--line); padding-right: var(--space-2); }
.fm-tabs { display: flex; }
.fm-tab { flex: 1; padding: var(--space-3) var(--space-4); border: none; background: none; cursor: pointer; font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--muted); border-bottom: 2px solid transparent; }
.fm-tab.active { color: var(--ink); border-bottom-color: var(--primary); }
.fm-close { border: none; background: none; font-size: 1.5rem; line-height: 1; cursor: pointer; color: var(--muted); padding: var(--space-2); }
.fm-body { overflow-y: auto; padding: var(--space-2); }
.fm-loading { display: flex; justify-content: center; padding: var(--space-5); }
.fm-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; }
.fm-user { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); text-decoration: none; color: var(--ink); }
.fm-user:hover { background: var(--bg-alt); }
.fm-avatar { width: 38px; height: 38px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary); color: var(--primary-fg, #fff); font-weight: var(--weight-semibold); flex-shrink: 0; }
.fm-name { font-size: var(--text-sm); font-weight: var(--weight-medium); }
.fm-empty { text-align: center; color: var(--muted); padding: var(--space-5); font-size: var(--text-sm); }

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
.profile-name-row .btn[aria-busy="true"] { pointer-events: none; }
/* Spinner contrast inside filled primary follow button */
.profile-name-row .btn-primary .spinner-sm { border-color: rgba(255,255,255,.45); border-top-color: #fff; }

.profile-skeleton { margin-top: var(--space-2); }

/* Saved tab (self profile) */
.tab-count {
  margin-left: var(--space-2); padding: 0 var(--space-2);
  border-radius: var(--radius-full); background: rgba(var(--accent-rgb), .16);
  color: var(--accent-dark); font-size: var(--text-xs); font-weight: var(--weight-bold);
  font-variant-numeric: tabular-nums; line-height: 1.6;
}
.saved-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-4); margin-top: var(--space-2); }
.saved-cta { text-align: center; margin-top: var(--space-5); }
.saved-cta .btn:active { transform: scale(.97); transition-duration: .08s; }
.dark .tab-count { background: rgba(232,163,61,.2); color: var(--accent); }

/* Dark mode */
.dark .profile-cover { border-color: var(--line); }
.dark .profile-avatar-wrap .avatar { border-color: var(--bg-warm); }
.dark .stat-item:hover { background: var(--card); box-shadow: var(--shadow-sm); }
.dark .profile-tabs { border-bottom-color: var(--line); }

/* Mobile: stack follow/edit button below name */
@media (max-width: 480px) {
  .profile-name-row { flex-direction: column; align-items: flex-start; }
  .profile-name-row .btn { width: 100%; justify-content: center; }
  .profile-stats { gap: var(--space-3); flex-wrap: wrap; }
}

@media (prefers-reduced-motion: reduce) {
  .post-list-enter-active, .post-list-leave-active, .post-list-move { transition: none; }
  .profile-avatar-wrap .avatar:hover { transform: none; }
  .stat-item:hover { transform: none; }
  .profile-tabs .chip:active { transform: none; }
  .saved-cta .btn:active { transform: none; }
}
.profile-completion { padding: 0 var(--space-4); margin-bottom: var(--space-3); }
.pc-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-1); }
.pc-label { font-size: var(--text-sm); font-weight: 600; color: var(--muted); }
.pc-link { font-size: var(--text-sm); color: var(--primary); text-decoration: none; }
.pc-bar { height: 6px; background: var(--bg-alt); border-radius: var(--radius-full); overflow: hidden; }
.pc-fill { height: 100%; background: var(--accent); border-radius: var(--radius-full); transition: width .4s var(--ease-out); }
.pc-hints { display: flex; flex-wrap: wrap; gap: var(--space-1); margin-top: var(--space-2); }
.pc-hint { font-size: .72rem; color: var(--muted); padding: 2px 8px; border: 1px solid var(--border-input); border-radius: var(--radius-full); }
</style>
