<template>
  <section class="page cp-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Tài khoản' }]" />

    <div v-if="!isLoggedIn" class="cp-guest card">
      <p class="dateline-eyebrow">HỒ SƠ HÀNH TRÌNH</p>
      <h1>Tài khoản</h1>
      <p>Đăng nhập để xem bảng điều khiển tài khoản.</p>
      <button type="button" class="btn btn-primary" @click="openAuth()">Đăng nhập</button>
    </div>

    <template v-else>
      <section class="cp-hero">
        <NuxtLink :to="profileUrl" class="cp-avatar-link" aria-label="Xem hồ sơ công khai">
          <img v-if="profileData.avatar_url" :src="profileData.avatar_url" alt="" class="cp-avatar" width="80" height="80" loading="lazy" />
          <span v-else class="cp-avatar-fallback"><AvatarPlaceholder :initial="initial" /></span>
        </NuxtLink>
        <div class="cp-identity">
          <p class="cp-kicker dateline-eyebrow">Trung tâm tài khoản</p>
          <h1 class="cp-name">{{ displayName }}</h1>
          <p v-if="user?.username" class="cp-username">@{{ user.username }}</p>
          <div class="cp-status-row">
            <span :class="['cp-pill', hasPassword ? 'ok' : 'warn']">{{ hasPassword ? 'Đã bảo vệ bằng mật khẩu' : 'Cần đặt mật khẩu' }}</span>
            <span class="cp-pill">Hồ sơ {{ profileCompletion }}%</span>
          </div>
          <div class="cp-hero-actions">
            <NuxtLink :to="primaryAction.to" class="btn btn-primary btn-sm">{{ primaryAction.label }}</NuxtLink>
            <NuxtLink to="/cai-dat" class="btn btn-ghost btn-sm">Cài đặt</NuxtLink>
          </div>
        </div>
        <div class="cp-score" aria-label="Điểm sẵn sàng tài khoản">
          <span class="cp-score-value">{{ accountScore }}</span>
          <span class="cp-score-label">{{ accountLevel }}</span>
        </div>
      </section>

      <div v-if="fetchIssue" class="cp-alert" role="status">
        <span>Chưa tải đủ dữ liệu tài khoản. Một vài chỉ số có thể đang tạm thời chưa chính xác.</span>
        <button type="button" class="btn btn-ghost btn-sm" :disabled="accountRefreshing" @click="loadAccountData">
          {{ accountRefreshing ? 'Đang thử lại...' : 'Thử lại' }}
        </button>
      </div>

      <!-- declutter-2 A7: rail đã bỏ — trùng panel "Việc nên làm tiếp" phía dưới. -->
      <section class="cp-summary-grid" aria-label="Tổng quan tài khoản">
        <article class="cp-panel">
          <div class="cp-panel-head">
            <span>
              <strong>Hoàn thiện hồ sơ</strong>
              <small>{{ completedProfileChecks }}/{{ profileChecks.length }} mục đã xong</small>
            </span>
            <NuxtLink to="/cai-dat#ho-so" class="cp-mini-link">Cập nhật</NuxtLink>
          </div>
          <div class="cp-progress" role="progressbar" aria-label="Tiến độ hoàn thiện hồ sơ" :aria-valuenow="profileCompletion" aria-valuemin="0" aria-valuemax="100"><span :style="{ width: profileCompletion + '%' }"></span></div>
          <div class="cp-checks">
            <NuxtLink v-for="item in profileChecks" :key="item.key" :to="item.to" :class="['cp-check', { done: item.done }]">
              <span aria-hidden="true">{{ item.done ? '✓' : '•' }}</span>{{ item.label }}
            </NuxtLink>
          </div>
        </article>

        <article class="cp-panel">
          <div class="cp-panel-head">
            <span>
              <strong>Sức khỏe bảo mật</strong>
              <small>{{ securitySummary }}</small>
            </span>
            <NuxtLink to="/cai-dat#bao-mat" class="cp-mini-link">Kiểm tra</NuxtLink>
          </div>
          <div class="cp-checks">
            <span v-for="item in securityChecks" :key="item.key" :class="['cp-check', { done: item.done }]">
              <span aria-hidden="true">{{ item.done ? '✓' : '•' }}</span>{{ item.label }}
            </span>
          </div>
        </article>

        <article class="cp-panel">
          <div class="cp-panel-head">
            <span>
              <strong>Việc nên làm tiếp</strong>
              <small>{{ nextActions.length }} gợi ý phù hợp</small>
            </span>
          </div>
          <div class="cp-action-list">
            <NuxtLink v-for="item in nextActions" :key="item.to + item.label" :to="item.to" class="cp-action-item">
              <span class="cp-action-icon" aria-hidden="true">{{ item.icon }}</span>
              <span>{{ item.label }}</span>
            </NuxtLink>
            <div v-if="!nextActions.length" class="cp-done-state">
              Hồ sơ đang ở trạng thái tốt. Bạn có thể tiếp tục khám phá và lưu thêm điểm đến.
            </div>
          </div>
        </article>
      </section>

      <!-- declutter-3 T5: cp-workspace 6 card đã bỏ — trùng side-panel "Dữ liệu của bạn"
           (count) + nav (đích đến); side-panel là nguồn count duy nhất (chốt spec-review). -->
      <section class="cp-main-grid">
        <article class="cp-section sediment-head">
          <div class="cp-section-head">
            <h2>Hoạt động gần đây</h2>
            <NuxtLink to="/cong-dong" class="cp-mini-link">Cộng đồng</NuxtLink>
          </div>
          <div v-if="activityLoading" class="cp-activity-loading">
            <div v-for="i in 4" :key="i" class="skeleton-box cp-activity-skel"></div>
          </div>
          <div v-else-if="activity.length" class="cp-activity-list">
            <template v-for="a in activity" :key="`${a.action}-${a.ref_id}-${a.created_at}`">
              <NuxtLink v-if="activityLink(a)" :to="activityLink(a)!" class="cp-activity-item cp-activity-link">
                <span class="cp-activity-icon" aria-hidden="true">{{ actionIcon(a.action) }}</span>
                <span class="cp-activity-body">
                  <span class="cp-activity-text">{{ actionLabel(a) }}</span>
                  <span class="cp-activity-time">{{ timeAgo(a.created_at) }}</span>
                </span>
              </NuxtLink>
              <div v-else class="cp-activity-item">
                <span class="cp-activity-icon" aria-hidden="true">{{ actionIcon(a.action) }}</span>
                <span class="cp-activity-body">
                  <span class="cp-activity-text">{{ actionLabel(a) }}</span>
                  <span class="cp-activity-time">{{ timeAgo(a.created_at) }}</span>
                </span>
              </div>
            </template>
            <button v-if="activityHasMore" type="button" class="btn btn-ghost btn-sm cp-load-more" :disabled="activityLoadingMore" @click="loadMoreActivity">
              {{ activityLoadingMore ? 'Đang tải...' : 'Xem thêm hoạt động' }}
            </button>
          </div>
          <div v-else class="cp-empty-state">
            <p>Chưa có hoạt động nào.</p>
            <div class="cp-empty-actions">
              <NuxtLink to="/cong-dong" class="btn btn-primary btn-sm">Viết bài đầu tiên</NuxtLink>
              <NuxtLink to="/dia-diem" class="btn btn-ghost btn-sm">Khám phá địa điểm</NuxtLink>
            </div>
          </div>
        </article>

        <aside class="cp-side-panel sediment-head" aria-label="Dữ liệu của bạn">
          <h2>Dữ liệu của bạn</h2>
          <div class="cp-data-list">
            <NuxtLink to="/da-luu" class="cp-data-row">
              <span>Địa điểm đã lưu</span>
              <strong>{{ counts.bookmarks ?? 0 }}</strong>
            </NuxtLink>
            <NuxtLink to="/thong-bao" class="cp-data-row">
              <span>Thông báo chưa đọc</span>
              <strong>{{ counts.unread_notifications ?? 0 }}</strong>
            </NuxtLink>
            <NuxtLink to="/cong-dong" class="cp-data-row">
              <span>Bản nháp</span>
              <strong>{{ counts.drafts ?? 0 }}</strong>
            </NuxtLink>
          </div>
          <NuxtLink to="/cai-dat#du-lieu" class="btn btn-secondary btn-sm cp-wide-btn">Xuất dữ liệu</NuxtLink>
        </aside>
      </section>

      <ClientOnly>
        <LazySmartRecommendations context="home" title="Gợi ý phù hợp với bạn" :limit="4" />
      </ClientOnly>
    </template>
  </section>
</template>

<script setup lang="ts">
import type { User } from '~/types'

type Counts = Partial<Record<'posts' | 'drafts' | 'bookmarks' | 'unread_notifications', number>>
type Stats = Partial<Record<'reviews' | 'followers' | 'following' | 'likes_received', number>>
type ActivityItem = { action: string; ref_id?: string; ref_type?: string; created_at: string; content?: string }

const { user, isLoggedIn, authHeaders, handleSessionExpired } = useAuth()
const { openAuth } = useAuthModal()
const { timeAgo } = useTimeAgo()

useHead({
  title: 'Tài khoản',
  meta: [{ name: 'robots', content: 'noindex, follow' }],
  link: [{ rel: 'canonical', href: canonicalUrl('/tai-khoan') }],
})

const counts = ref<Counts>({})
const stats = ref<Stats>({})
const activity = ref<ActivityItem[]>([])
const profileDetail = ref<Partial<User>>({})
const activityLoading = ref(true)
const activityHasMore = ref(false)
const activityLoadingMore = ref(false)
const accountRefreshing = ref(false)
const fetchIssue = ref(false)
const ACTIVITY_PAGE = 10

const profileData = computed(() => ({ ...(user.value || {}), ...profileDetail.value } as Partial<User>))
const displayName = computed(() => profileData.value.display_name || profileData.value.full_name || 'Người dùng')
const initial = computed(() => displayName.value.charAt(0).toUpperCase())
const profileUrl = computed(() => userPath(user.value?.username || user.value?.id))
const hasPassword = computed(() => user.value?.has_password === true)

const profileChecks = computed(() => {
  const u = profileData.value
  return [
    { key: 'name', label: 'Tên hiển thị', done: Boolean(u.display_name || u.full_name), to: '/cai-dat#ho-so' },
    { key: 'avatar', label: 'Ảnh đại diện', done: Boolean(u.avatar_url || u.avatar), to: '/cai-dat#ho-so' },
    { key: 'cover', label: 'Ảnh bìa', done: Boolean(u.cover_url), to: '/cai-dat#ho-so' },
    { key: 'bio', label: 'Giới thiệu', done: Boolean(u.bio), to: '/cai-dat#ho-so' },
    { key: 'contact', label: 'Liên hệ', done: Boolean(u.email || u.contact_info), to: '/cai-dat#ho-so' },
    { key: 'post', label: 'Bài viết đầu tiên', done: (counts.value.posts ?? 0) > 0, to: '/cong-dong' },
    { key: 'review', label: 'Đánh giá đầu tiên', done: (stats.value.reviews ?? 0) > 0, to: '/du-lich' },
  ]
})
const completedProfileChecks = computed(() => profileChecks.value.filter(i => i.done).length)
const profileCompletion = computed(() => Math.round((completedProfileChecks.value / profileChecks.value.length) * 100))

const securityChecks = computed(() => [
  { key: 'password', label: 'Mật khẩu', done: hasPassword.value },
  { key: 'sessions', label: 'Dữ liệu tài khoản tải ổn định', done: !fetchIssue.value },
])
const completedSecurityChecks = computed(() => securityChecks.value.filter(i => i.done).length)
const securitySummary = computed(() => `${completedSecurityChecks.value}/${securityChecks.value.length} lớp ổn định`)
const accountScore = computed(() => Math.round((profileCompletion.value * 0.65) + ((completedSecurityChecks.value / securityChecks.value.length) * 35)))
const accountLevel = computed(() => accountScore.value >= 85 ? 'sẵn sàng' : accountScore.value >= 60 ? 'đang tốt' : 'cần hoàn thiện')

const nextActions = computed(() => {
  const actions: Array<{ icon: string; label: string; to: string }> = []
  const u = profileData.value
  if (!hasPassword.value) actions.push({ icon: '🔒', label: 'Bảo vệ tài khoản bằng mật khẩu', to: '/cai-dat#bao-mat' })
  if (!(u.display_name || u.full_name)) actions.push({ icon: '✍️', label: 'Cập nhật tên hiển thị', to: '/cai-dat#ho-so' })
  if (!u.avatar_url) actions.push({ icon: '👤', label: 'Thêm ảnh đại diện', to: '/cai-dat#ho-so' })
  if (!u.cover_url) actions.push({ icon: '🖼️', label: 'Thêm ảnh bìa', to: '/cai-dat#ho-so' })
  if (!u.bio) actions.push({ icon: '✍️', label: 'Viết giới thiệu ngắn', to: '/cai-dat#ho-so' })
  if ((counts.value.posts ?? 0) === 0) actions.push({ icon: '📝', label: 'Chia sẻ bài đầu tiên', to: '/cong-dong' })
  if ((counts.value.bookmarks ?? 0) === 0) actions.push({ icon: '📍', label: 'Lưu địa điểm muốn đi', to: '/du-lich' })
  return actions.slice(0, 4)
})
const primaryAction = computed(() => nextActions.value[0] || { icon: '✓', label: 'Xem hồ sơ', to: profileUrl.value })
let accountLoadSeq = 0

function resetAccountData() {
  accountLoadSeq++
  counts.value = {}
  stats.value = {}
  activity.value = []
  profileDetail.value = {}
  activityHasMore.value = false
  activityLoading.value = false
  activityLoadingMore.value = false
  accountRefreshing.value = false
  fetchIssue.value = false
}

function resultStatusCode(result: PromiseSettledResult<unknown>) {
  return result.status === 'rejected' ? getStatusCode(result.reason) : null
}

if (import.meta.client) {
  watch(() => isLoggedIn.value ? user.value?.id : null, async (id) => {
    if (!id) { resetAccountData(); return }
    await loadAccountData()
  }, { immediate: true })
}

async function loadAccountData() {
  if (!isLoggedIn.value) { resetAccountData(); return }
  const seq = ++accountLoadSeq
  accountRefreshing.value = true
  if (!activity.value.length) activityLoading.value = true
  const headers = authHeaders()
  const profileKey = user.value?.username || user.value?.id
  try {
    const results = await Promise.allSettled([
      $fetch<Record<string, number>>('/api/me/counts', { headers }),
      $fetch<Record<string, number>>('/api/me/stats', { headers }),
      $fetch<{ items: ActivityItem[] }>(`/api/me/activity?limit=${ACTIVITY_PAGE}`, { headers }),
      profileKey ? $fetch<{ user?: Partial<User> } & Partial<User>>(`/api/users/${encodeURIComponent(profileKey)}`, { headers }) : Promise.resolve({}),
    ])
    if (seq !== accountLoadSeq) return
    if (results.some(result => resultStatusCode(result) === 401)) {
      handleSessionExpired()
      resetAccountData()
      return
    }
    const [c, s, a, p] = results
    fetchIssue.value = results.some(r => r.status === 'rejected')
    if (c.status === 'fulfilled') counts.value = c.value || {}
    if (s.status === 'fulfilled') stats.value = s.value || {}
    if (a.status === 'fulfilled') {
      const items = a.value.items || []
      activity.value = items
      activityHasMore.value = items.length >= ACTIVITY_PAGE
    }
    if (p.status === 'fulfilled') {
      const payload = p.value as ({ user?: Partial<User> } & Partial<User>)
      profileDetail.value = (payload.user || payload || {}) as Partial<User>
    }
  } finally {
    if (seq === accountLoadSeq) {
      activityLoading.value = false
      accountRefreshing.value = false
    }
  }
}

async function loadMoreActivity() {
  activityLoadingMore.value = true
  try {
    const res = await $fetch<{ items: ActivityItem[] }>(`/api/me/activity?limit=${ACTIVITY_PAGE}&offset=${activity.value.length}`, { headers: authHeaders() })
    const items = res.items || []
    activity.value.push(...items)
    activityHasMore.value = items.length >= ACTIVITY_PAGE
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    fetchIssue.value = true
  } finally {
    activityLoadingMore.value = false
  }
}

function actionIcon(action: string) {
  const icons: Record<string, string> = { post: '✍️', comment: '💬', like: '❤️', bookmark: '💾', review: '⭐', follow: '👤', mention: '📣', repost: '🔁' }
  return icons[action] || '📌'
}

function activityLink(a: ActivityItem): string | null {
  if (a.ref_type === 'post' && a.ref_id) return postPath(a.ref_id)
  if (a.ref_type === 'entity' && a.ref_id) return entityPath(a.ref_id)
  if (a.ref_type === 'user' && a.ref_id) return userPath(a.ref_id)
  return null
}

function actionLabel(a: ActivityItem) {
  const types: Record<string, string> = {
    post: 'Đã đăng bài viết',
    comment: 'Đã bình luận',
    like: 'Đã thích một bài viết',
    bookmark: a.ref_type === 'entity' ? 'Đã lưu một địa điểm' : 'Đã lưu một bài viết',
    review: 'Đã đánh giá',
    follow: 'Đã theo dõi',
    mention: 'Được nhắc đến',
    repost: 'Đã chia sẻ lại',
  }
  let label = types[a.action] || a.action
  if (a.content) {
    const preview = a.content.length > 60 ? `${a.content.slice(0, 60)}...` : a.content
    label += `: "${preview}"`
  }
  return label
}
</script>

<style scoped>
.cp-page { max-width: 1040px; margin: 0 auto; }
.cp-guest { padding: 2rem; text-align: center; }
.cp-guest h1 { margin: 0 0 1rem; font-family: var(--font-editorial); font-size: 1.5rem; font-weight: 600; }
.cp-guest p { color: var(--ink-700); margin-bottom: 1rem; }
.cp-guest .dateline-eyebrow { justify-content: center; }

/* Local page masthead eyebrow — small-caps dateline + hairline tick, matches
   the site's area/ward eyebrow pattern but scoped here (not promoted global). */
.dateline-eyebrow {
  display: flex; align-items: center; gap: .4rem;
  font-family: var(--font-sans); font-size: .78rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .06em; color: var(--ink-700);
}
.dateline-eyebrow::before { content: ""; width: 14px; height: 1.5px; background: var(--primary); flex-shrink: 0; }

.cp-hero {
  display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 1rem;
  align-items: center; margin-bottom: 1rem; padding: 1.25rem;
  border: 1px solid var(--line); border-radius: var(--radius-lg); background: var(--card);
}
.cp-avatar-link { width: 80px; height: 80px; border-radius: 50%; overflow: hidden; display: block; }
.cp-avatar, .cp-avatar-fallback { width: 80px; height: 80px; border-radius: 50%; object-fit: cover; display: block; }
.cp-kicker { margin: 0 0 .2rem; color: var(--ink-700); font-size: .82rem; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
.cp-name { margin: 0; font-family: var(--font-editorial); font-weight: 600; font-size: clamp(1.35rem, 2vw, 1.9rem); }
.cp-username { margin: .15rem 0 0; color: var(--ink-700); }
.cp-status-row { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .6rem; }
.cp-pill { display: inline-flex; align-items: center; min-height: 28px; padding: .2rem .65rem; border: 1px solid var(--line); border-radius: var(--radius-full); font-size: .78rem; color: var(--ink-700); background: var(--bg-alt); }
.cp-pill.ok { color: var(--accent); border-color: color-mix(in oklab, var(--accent) 35%, var(--line)); }
.cp-pill.warn { color: var(--danger); border-color: rgba(192,57,43,.25); }
.cp-hero-actions { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .85rem; }
.cp-score { width: 92px; height: 92px; border-radius: 50%; display: grid; place-content: center; text-align: center; border: 8px solid color-mix(in oklab, var(--accent) 55%, var(--line)); background: var(--bg-alt); }
.cp-score-value { font-size: 1.45rem; font-weight: 800; line-height: 1; }
.cp-score-label { font-size: .72rem; color: var(--ink-700); margin-top: .2rem; }
.cp-alert {
  display: flex; align-items: center; justify-content: space-between; gap: .75rem;
  margin-bottom: 1rem; padding: .75rem .9rem; border: 1px solid rgba(var(--danger-rgb, 217,79,61), .22);
  border-radius: var(--radius-md); background: color-mix(in oklab, var(--error-container) 70%, var(--card));
  color: var(--ink);
}
.cp-alert span { font-size: .86rem; line-height: 1.4; }

.cp-summary-grid, .cp-main-grid { display: grid; gap: 1rem; }
.cp-summary-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); margin-bottom: 1rem; }
.cp-panel, .cp-section, .cp-side-panel {
  border: 1px solid var(--line); border-radius: var(--radius-lg); background: var(--card);
}
.cp-panel { padding: 1rem; }
.cp-panel-head, .cp-section-head { display: flex; justify-content: space-between; gap: .75rem; align-items: flex-start; margin-bottom: .75rem; }
.cp-panel-head strong, .cp-section-head h2, .cp-side-panel h2 { display: block; margin: 0; font-size: 1rem; }
.cp-panel-head small { display: block; color: var(--ink-700); font-size: .78rem; margin-top: .15rem; }
.cp-mini-link { color: var(--accent); text-decoration: none; font-weight: 600; font-size: .82rem; white-space: nowrap; }
.cp-progress { height: 8px; border-radius: var(--radius-full); overflow: hidden; background: var(--bg-alt); margin-bottom: .75rem; }
.cp-progress span { display: block; height: 100%; border-radius: inherit; background: var(--accent); transition: width .35s var(--ease-out); }
.cp-checks, .cp-action-list, .cp-data-list { display: flex; flex-direction: column; gap: .45rem; }
.cp-check { display: flex; align-items: center; gap: .45rem; color: var(--ink-700); font-size: .84rem; text-decoration: none; border-radius: var(--radius-sm); }
.cp-check:hover { color: var(--ink); }
.cp-check:focus-visible, .cp-mini-link:focus-visible, .cp-action-item:focus-visible, .cp-data-row:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.cp-check.done { color: var(--ink); }
.cp-check.done span { color: var(--accent); font-weight: 800; }
.cp-action-item, .cp-data-row { display: flex; align-items: center; justify-content: space-between; gap: .65rem; padding: .55rem .65rem; border-radius: var(--radius-md); text-decoration: none; color: var(--ink); background: var(--bg-alt); }
.cp-action-item:hover, .cp-data-row:hover { background: color-mix(in oklab, var(--accent) 8%, var(--bg-alt)); }
.cp-action-icon { font-size: 1rem; }
.cp-done-state { padding: .75rem; border-radius: var(--radius-md); background: var(--bg-alt); color: var(--ink-700); font-size: .84rem; line-height: 1.45; }



.cp-main-grid { grid-template-columns: minmax(0, 1fr) 280px; align-items: start; }
.cp-section, .cp-side-panel { padding: 1rem; }
.cp-activity-list { display: flex; flex-direction: column; gap: .55rem; }
.cp-activity-item { display: flex; gap: .65rem; align-items: flex-start; padding: .7rem .8rem; border-radius: var(--radius-md); border: 1px solid var(--line); background: var(--bg-alt); color: inherit; text-decoration: none; }
.cp-activity-link:hover { border-color: var(--accent); background: color-mix(in oklab, var(--accent) 8%, var(--bg-alt)); }
.cp-activity-icon { font-size: 1.05rem; flex-shrink: 0; }
.cp-activity-body { min-width: 0; }
.cp-activity-text { display: block; font-size: .88rem; line-height: 1.4; }
.cp-activity-time { display: block; font-size: .76rem; color: var(--ink-700); margin-top: .1rem; }
.cp-activity-loading { display: flex; flex-direction: column; gap: .5rem; }
.cp-activity-skel { height: 50px; border-radius: var(--radius-md); }
.cp-load-more, .cp-wide-btn { width: 100%; margin-top: .75rem; }
.cp-empty-state { text-align: center; padding: 1.5rem .75rem; color: var(--ink-700); }
.cp-empty-actions { display: flex; flex-wrap: wrap; justify-content: center; gap: .5rem; margin-top: .75rem; }
.cp-data-row strong { font-variant-numeric: tabular-nums; }

.dark .cp-hero, .dark .cp-panel, .dark .cp-section, .dark .cp-side-panel { background: var(--bg-alt); border-color: var(--line); }
.dark .cp-action-item, .dark .cp-data-row, .dark .cp-activity-item, .dark .cp-score { background: var(--bg); }

@media (max-width: 860px) {
  .cp-summary-grid, .cp-main-grid { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .cp-hero { grid-template-columns: auto 1fr; }
  .cp-hero-actions .btn { flex: 1 1 130px; justify-content: center; }
  .cp-score { grid-column: 1 / -1; width: 100%; height: auto; border-radius: var(--radius-md); border-width: 1px; padding: .75rem; display: block; }
  .cp-alert { flex-direction: column; align-items: stretch; }
}
@media (prefers-reduced-motion: reduce) {
  .cp-progress span { transition: none; }
}
</style>
