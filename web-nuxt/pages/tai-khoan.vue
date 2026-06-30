<template>
  <section class="page cp-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Tài khoản' }]" />

    <div v-if="!isLoggedIn" class="cp-guest card">
      <h1>Tài khoản</h1>
      <p>Đăng nhập để xem bảng điều khiển tài khoản.</p>
      <button type="button" class="btn btn-primary" @click="openAuth">Đăng nhập</button>
    </div>

    <template v-else>
      <!-- Header with avatar + name -->
      <div class="cp-header">
        <NuxtLink :to="`/nguoi-dung/${user?.username || user?.id}`" class="cp-avatar-link">
          <img v-if="user?.avatar_url" :src="user.avatar_url" alt="" class="cp-avatar" width="64" height="64" loading="lazy" />
          <span v-else class="cp-avatar-fallback"><AvatarPlaceholder :initial="user?.display_name?.[0]?.toUpperCase()" /></span>
        </NuxtLink>
        <div class="cp-header-info">
          <h1 class="cp-name">{{ user?.display_name || 'Người dùng' }}</h1>
          <p v-if="user?.username" class="cp-username">@{{ user.username }}</p>
        </div>
      </div>

      <!-- Stats row -->
      <div v-if="stats" class="cp-stats">
        <div class="cp-stat">
          <span class="cp-stat-val">{{ counts?.posts ?? 0 }}</span>
          <span class="cp-stat-label">Bài viết</span>
        </div>
        <div class="cp-stat">
          <span class="cp-stat-val">{{ stats?.reviews ?? 0 }}</span>
          <span class="cp-stat-label">Đánh giá</span>
        </div>
        <div class="cp-stat">
          <span class="cp-stat-val">{{ stats?.followers ?? 0 }}</span>
          <span class="cp-stat-label">Người theo dõi</span>
        </div>
        <div class="cp-stat">
          <span class="cp-stat-val">{{ stats?.following ?? 0 }}</span>
          <span class="cp-stat-label">Đang theo dõi</span>
        </div>
        <div class="cp-stat">
          <span class="cp-stat-val">{{ counts?.bookmarks ?? 0 }}</span>
          <span class="cp-stat-label">Đã lưu</span>
        </div>
        <div class="cp-stat">
          <span class="cp-stat-val">{{ stats?.likes_received ?? 0 }}</span>
          <span class="cp-stat-label">Lượt thích nhận</span>
        </div>
      </div>
      <div v-else class="cp-stats-skeleton">
        <div v-for="i in 6" :key="i" class="skeleton-box cp-stat-skel"></div>
      </div>

      <!-- Quick links grid -->
      <div class="cp-grid">
        <NuxtLink v-if="user" :to="`/nguoi-dung/${user.username || user.id}`" class="cp-card card">
          <span class="cp-card-icon">👤</span>
          <span class="cp-card-title">Trang cá nhân</span>
          <span class="cp-card-desc">Xem hồ sơ công khai</span>
        </NuxtLink>
        <NuxtLink to="/thong-bao" class="cp-card card">
          <span class="cp-card-icon">🔔</span>
          <span class="cp-card-title">Thông báo</span>
          <span v-if="counts?.unread_notifications" class="cp-card-badge">{{ counts.unread_notifications }}</span>
          <span class="cp-card-desc">{{ counts?.unread_notifications ? `${counts.unread_notifications} chưa đọc` : 'Không có mới' }}</span>
        </NuxtLink>
        <NuxtLink to="/da-luu" class="cp-card card">
          <span class="cp-card-icon">💾</span>
          <span class="cp-card-title">Đã lưu</span>
          <span class="cp-card-desc">{{ counts?.bookmarks ?? 0 }} địa điểm lưu</span>
        </NuxtLink>
        <NuxtLink to="/cong-dong" class="cp-card card">
          <span class="cp-card-icon">✍️</span>
          <span class="cp-card-title">Bài viết</span>
          <span class="cp-card-desc">{{ counts?.posts ?? 0 }} bài · {{ counts?.drafts ?? 0 }} nháp</span>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cp-card card">
          <span class="cp-card-icon">🗺️</span>
          <span class="cp-card-title">Lịch trình</span>
          <span class="cp-card-desc">Xem và tạo lịch trình</span>
        </NuxtLink>
        <NuxtLink to="/cai-dat" class="cp-card card">
          <span class="cp-card-icon">⚙️</span>
          <span class="cp-card-title">Cài đặt</span>
          <span class="cp-card-desc">Hồ sơ, bảo mật, giao diện</span>
        </NuxtLink>
      </div>

      <!-- Recent activity -->
      <div class="cp-section">
        <h2>Hoạt động gần đây</h2>
        <div v-if="activityLoading" class="cp-activity-loading">
          <div v-for="i in 4" :key="i" class="skeleton-box cp-activity-skel"></div>
        </div>
        <div v-else-if="activity.length" class="cp-activity-list">
          <div v-for="a in activity" :key="`${a.action}-${a.ref_id}`" class="cp-activity-item">
            <span class="cp-activity-icon">{{ actionIcon(a.action) }}</span>
            <div class="cp-activity-body">
              <span class="cp-activity-text">{{ actionLabel(a) }}</span>
              <span class="cp-activity-time">{{ timeAgo(a.created_at) }}</span>
            </div>
          </div>
        </div>
        <p v-else class="cp-empty-hint">Chưa có hoạt động nào.</p>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
const { user, isLoggedIn, authHeaders } = useAuth()
const { openAuth } = useAuthModal()
const { timeAgo } = useTimeAgo()

useHead({
  title: 'Tài khoản',
  meta: [{ name: 'robots', content: 'noindex,nofollow' }],
  link: [{ rel: 'canonical', href: canonicalUrl('/tai-khoan') }],
})

const counts = ref<Record<string, number> | null>(null)
const stats = ref<Record<string, number> | null>(null)
const activity = ref<any[]>([])
const activityLoading = ref(true)

onMounted(async () => {
  if (!isLoggedIn.value) return
  const headers = authHeaders()
  const [c, s, a] = await Promise.allSettled([
    $fetch<Record<string, number>>('/api/me/counts', { headers }),
    $fetch<Record<string, number>>('/api/me/stats', { headers }),
    $fetch<{ items: any[] }>('/api/me/activity?limit=10', { headers }),
  ])
  if (c.status === 'fulfilled') counts.value = c.value
  if (s.status === 'fulfilled') stats.value = s.value
  if (a.status === 'fulfilled') activity.value = (a.value as any).items || []
  activityLoading.value = false
})

function actionIcon(action: string) {
  const icons: Record<string, string> = { post: '✍️', comment: '💬', like: '❤️', bookmark: '💾', review: '⭐' }
  return icons[action] || '📌'
}

function actionLabel(a: any) {
  const types: Record<string, string> = {
    post: 'Đã đăng bài viết',
    comment: 'Đã bình luận',
    like: 'Đã thích một bài viết',
    bookmark: 'Đã lưu một bài viết',
    review: 'Đã đánh giá',
  }
  let label = types[a.action] || `${a.action}`
  if (a.content) {
    const preview = a.content.length > 60 ? a.content.slice(0, 60) + '…' : a.content
    label += `: "${preview}"`
  }
  return label
}
</script>

<style scoped>
.cp-page { max-width: 720px; margin: 0 auto; }
.cp-guest { padding: 2rem; text-align: center; }
.cp-guest h1 { margin: 0 0 1rem; font-size: 1.5rem; }
.cp-guest p { color: var(--ink-700); margin-bottom: 1rem; }

/* Header */
.cp-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem; }
.cp-avatar-link { flex-shrink: 0; }
.cp-avatar { width: 64px; height: 64px; border-radius: 50%; object-fit: cover; border: 2px solid var(--line); }
.cp-avatar-fallback { display: block; width: 64px; height: 64px; border-radius: 50%; overflow: hidden; }
.cp-name { margin: 0; font-size: 1.4rem; }
.cp-username { margin: .15rem 0 0; color: var(--ink-700); font-size: .9rem; }

/* Stats */
.cp-stats {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: var(--space-3); margin-bottom: 1.5rem;
  padding: 1rem; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius-lg);
}
.cp-stat { text-align: center; }
.cp-stat-val { display: block; font-size: 1.25rem; font-weight: 700; color: var(--ink); }
.cp-stat-label { font-size: .78rem; color: var(--ink-700); }
.cp-stats-skeleton { display: flex; gap: var(--space-3); margin-bottom: 1.5rem; }
.cp-stat-skel { height: 52px; flex: 1; border-radius: var(--radius-md); }

/* Quick links grid */
.cp-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--space-3); margin-bottom: 1.5rem;
}
.cp-card {
  display: flex; flex-direction: column; gap: .25rem;
  padding: 1rem; text-decoration: none; color: var(--ink);
  transition: transform .2s var(--ease-out), box-shadow .2s var(--ease-out);
  position: relative;
}
.cp-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.cp-card-icon { font-size: 1.5rem; }
.cp-card-title { font-weight: 600; font-size: .95rem; }
.cp-card-desc { font-size: .8rem; color: var(--ink-700); }
.cp-card-badge {
  position: absolute; top: .6rem; right: .6rem;
  background: var(--error, #e53e3e); color: #fff;
  font-size: .7rem; font-weight: 700; padding: 1px 6px;
  border-radius: var(--radius-full);
}

/* Activity */
.cp-section { margin-bottom: 2rem; }
.cp-section h2 { font-size: 1.1rem; margin: 0 0 .75rem; padding-bottom: .5rem; border-bottom: 1px solid var(--line); }
.cp-activity-list { display: flex; flex-direction: column; gap: .5rem; }
.cp-activity-item {
  display: flex; gap: .6rem; align-items: flex-start;
  padding: .6rem .75rem; border-radius: var(--radius-md);
  border: 1px solid var(--line); background: var(--card);
}
.cp-activity-icon { font-size: 1.1rem; flex-shrink: 0; margin-top: .1rem; }
.cp-activity-body { flex: 1; min-width: 0; }
.cp-activity-text { display: block; font-size: .88rem; color: var(--ink); line-height: 1.4; }
.cp-activity-time { font-size: .78rem; color: var(--ink-700); }
.cp-activity-loading { display: flex; flex-direction: column; gap: .5rem; }
.cp-activity-skel { height: 48px; border-radius: var(--radius-md); }
.cp-empty-hint { color: var(--ink-700); font-size: .9rem; }

/* Dark */
.dark .cp-stats { background: var(--bg-alt); border-color: var(--line); }
.dark .cp-activity-item { background: var(--bg-alt); border-color: var(--line); }

/* Mobile */
@media (max-width: 600px) {
  .cp-grid { grid-template-columns: repeat(2, 1fr); }
  .cp-stats { grid-template-columns: repeat(3, 1fr); }
  .cp-header { gap: .75rem; }
  .cp-name { font-size: 1.15rem; }
}
@media (prefers-reduced-motion: reduce) {
  .cp-card { transition: none; }
}
</style>
