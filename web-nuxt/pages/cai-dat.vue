<template>
  <section class="page settings-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cài đặt' }]" />

    <div v-if="!isLoggedIn" class="settings-guest card">
      <h1>Cài đặt</h1>
      <p>Bạn cần đăng nhập để chỉnh sửa hồ sơ.</p>
      <button type="button" class="btn btn-primary" @click="openAuth">Đăng nhập</button>
    </div>

    <template v-else>
    <h1 class="settings-title">Cài đặt</h1>

    <!-- Tab navigation -->
    <nav class="settings-tabs" role="tablist" aria-label="Cài đặt">
      <button
        v-for="t in TABS" :key="t.key" type="button" role="tab"
        class="settings-tab" :class="{ active: activeTab === t.key }"
        :aria-selected="activeTab === t.key"
        @click="setTab(t.key)"
      >
        <span class="settings-tab-icon" aria-hidden="true">{{ t.icon }}</span>
        {{ t.label }}
      </button>
    </nav>

    <!-- Tab: Hồ sơ -->
    <div v-if="activeTab === 'ho-so'" class="settings-card card" role="tabpanel">
      <h2>Hồ sơ cá nhân</h2>
      <form class="settings-form" @submit.prevent="save">
        <div class="sf-avatar-section">
          <div class="sf-avatar-preview" role="button" tabindex="0" aria-label="Thay đổi ảnh đại diện" @click="($refs.avatarInput as HTMLInputElement)?.click()" @keydown.enter="($refs.avatarInput as HTMLInputElement)?.click()">
            <img v-if="avatarPreview || user?.avatar_url" :src="avatarPreview || user?.avatar_url!" alt="Avatar" class="sf-avatar-img" />
            <AvatarPlaceholder v-else :initial="user?.display_name?.[0]?.toUpperCase()" />
            <span class="sf-avatar-overlay">&#128247;</span>
          </div>
          <div class="sf-avatar-info">
            <span class="sf-label">Ảnh đại diện</span>
            <span class="sf-hint">JPEG, PNG hoặc WebP. Tối đa 12MB.</span>
            <button type="button" class="btn btn-ghost btn-sm" :disabled="uploadingAvatar" @click="($refs.avatarInput as HTMLInputElement)?.click()">
              {{ uploadingAvatar ? 'Đang tải...' : 'Đổi ảnh' }}
            </button>
          </div>
          <input ref="avatarInput" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="onAvatarChange" />
        </div>

        <div class="sf-cover-section">
          <div class="sf-cover-preview" role="button" tabindex="0" aria-label="Thay đổi ảnh bìa" @click="($refs.coverInput as HTMLInputElement)?.click()" @keydown.enter="($refs.coverInput as HTMLInputElement)?.click()">
            <img v-if="coverPreview || user?.cover_url" :src="coverPreview || user?.cover_url!" alt="Ảnh bìa" class="sf-cover-img" />
            <div v-else class="sf-cover-placeholder">
              <span>Thêm ảnh bìa</span>
            </div>
            <span class="sf-avatar-overlay">&#128247;</span>
          </div>
          <div class="sf-avatar-info">
            <span class="sf-label">Ảnh bìa</span>
            <span class="sf-hint">Ảnh ngang, tỉ lệ 3:1. Tối đa 12MB.</span>
            <button type="button" class="btn btn-ghost btn-sm" :disabled="uploadingCover" @click="($refs.coverInput as HTMLInputElement)?.click()">
              {{ uploadingCover ? 'Đang tải...' : 'Đổi ảnh bìa' }}
            </button>
          </div>
          <input ref="coverInput" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="onCoverChange" />
        </div>

        <label class="sf-field">
          <span class="sf-label">Tên hiển thị</span>
          <input
            v-model="displayName"
            type="text"
            class="sf-input"
            maxlength="50"
            required
            :aria-invalid="!!nameError"
            placeholder="Tên bạn muốn hiển thị"
          />
          <span v-if="nameError" class="sf-error" role="alert">{{ nameError }}</span>
        </label>

        <label class="sf-field">
          <span class="sf-label">Giới thiệu <span class="sf-hint">({{ bio.length }}/300)</span></span>
          <textarea
            v-model="bio"
            class="sf-input sf-textarea"
            maxlength="300"
            rows="4"
            placeholder="Đôi dòng về bạn (không bắt buộc)"
          ></textarea>
        </label>

        <div class="sf-actions">
          <button type="submit" class="btn btn-primary" :disabled="saving" :aria-busy="saving">
            <span v-if="saving" class="spinner spinner-sm" aria-hidden="true"></span>
            {{ saving ? 'Đang lưu…' : 'Lưu thay đổi' }}
          </button>
          <NuxtLink v-if="user" :to="`/nguoi-dung/${user.id}`" class="btn btn-ghost">Xem hồ sơ</NuxtLink>
        </div>
      </form>
    </div>

    <!-- Tab: Bảo mật -->
    <div v-if="activeTab === 'bao-mat'" role="tabpanel">
      <div class="settings-card card">
        <h2>Mật khẩu</h2>
        <p v-if="!user?.has_password" class="sf-hint">Bạn chưa đặt mật khẩu. Đặt mật khẩu để đăng nhập nhanh hơn.</p>
        <form class="settings-form" @submit.prevent="savePassword">
          <label v-if="user?.has_password" class="sf-field">
            <span class="sf-label">Mật khẩu hiện tại</span>
            <input v-model="currentPw" type="password" class="sf-input" autocomplete="current-password" required />
          </label>
          <label class="sf-field">
            <span class="sf-label">{{ user?.has_password ? 'Mật khẩu mới' : 'Đặt mật khẩu' }}</span>
            <input v-model="newPw" type="password" class="sf-input" minlength="6" autocomplete="new-password" required />
          </label>
          <div class="sf-actions">
            <button type="submit" class="btn btn-primary" :disabled="savingPw">
              {{ savingPw ? 'Đang lưu...' : (user?.has_password ? 'Đổi mật khẩu' : 'Đặt mật khẩu') }}
            </button>
          </div>
        </form>
      </div>

      <div class="settings-card card">
        <h2>Phiên đăng nhập</h2>
        <div v-if="sessionsLoading" class="sf-hint">Đang tải...</div>
        <div v-else-if="sessions.length" class="sessions-list">
          <div v-for="s in sessions" :key="s.id" :class="['session-item', { current: s.is_current }]">
            <div class="session-info">
              <span class="session-ua">{{ shortUA(s.user_agent) }}</span>
              <span class="sf-hint">{{ s.ip_address }} &middot; {{ timeAgo(s.created_at) }}</span>
            </div>
            <span v-if="s.is_current" class="session-badge">Hiện tại</span>
            <button v-else type="button" class="btn btn-ghost btn-sm btn-danger-text" @click="revokeSession(s.id)">Thu hồi</button>
          </div>
        </div>
        <p v-else class="sf-hint">Không có phiên nào.</p>
      </div>

      <div class="settings-card card">
        <h2>Lịch sử đăng nhập</h2>
        <div v-if="loginHistoryLoading" class="sf-hint">Đang tải...</div>
        <div v-else-if="loginHistory.length" class="sessions-list">
          <div v-for="h in loginHistory" :key="h.id" :class="['session-item', { 'login-fail': !h.success }]">
            <div class="session-info">
              <span class="session-ua">{{ h.method === 'otp' ? 'OTP' : 'Mật khẩu' }} — {{ h.success ? 'Thành công' : 'Thất bại' }}</span>
              <span class="sf-hint">{{ h.ip }} &middot; {{ timeAgo(h.created_at) }}</span>
            </div>
            <span :class="h.success ? 'login-ok' : 'login-bad'">{{ h.success ? '✓' : '✗' }}</span>
          </div>
        </div>
        <p v-else class="sf-hint">Chưa có lịch sử.</p>
      </div>
    </div>

    <!-- Tab: Thông báo -->
    <div v-if="activeTab === 'thong-bao'" class="settings-card card" role="tabpanel">
      <h2>Tùy chọn thông báo</h2>
      <p class="sf-hint" style="margin-bottom: 1rem;">Chọn loại thông báo bạn muốn nhận.</p>
      <div v-if="notifPrefsLoading" class="sf-hint">Đang tải...</div>
      <div v-else class="notif-prefs">
        <label v-for="np in NOTIF_TYPES" :key="np.key" class="notif-pref-item">
          <div class="notif-pref-info">
            <span class="notif-pref-icon" aria-hidden="true">{{ np.icon }}</span>
            <div>
              <strong>{{ np.label }}</strong>
              <span class="sf-hint">{{ np.desc }}</span>
            </div>
          </div>
          <input type="checkbox" :checked="notifPrefs[np.pref]" class="toggle" @change="toggleNotifPref(np.pref)" />
        </label>
      </div>
    </div>

    <!-- Tab: Giao diện -->
    <div v-if="activeTab === 'giao-dien'" class="settings-card card" role="tabpanel">
      <h2>Giao diện</h2>
      <div class="sf-field">
        <span class="sf-label">Chế độ màu</span>
        <div class="theme-options">
          <button type="button" :class="['theme-btn', { active: colorMode === 'light' }]" @click="setColorMode('light')">
            <span class="theme-icon">☀️</span> Sáng
          </button>
          <button type="button" :class="['theme-btn', { active: colorMode === 'dark' }]" @click="setColorMode('dark')">
            <span class="theme-icon">🌙</span> Tối
          </button>
          <button type="button" :class="['theme-btn', { active: colorMode === 'system' }]" @click="setColorMode('system')">
            <span class="theme-icon">💻</span> Hệ thống
          </button>
        </div>
        <span class="sf-hint">Chế độ "Hệ thống" tự động theo cài đặt thiết bị của bạn.</span>
      </div>
    </div>

    <!-- Tab: Quyền riêng tư -->
    <div v-if="activeTab === 'rieng-tu'" class="settings-card card" role="tabpanel">
      <h2>Quyền riêng tư</h2>
      <div v-if="privacyLoading" class="sf-hint">Đang tải...</div>
      <div v-else class="settings-form">
        <div class="sf-field">
          <span class="sf-label">Ai xem được hồ sơ?</span>
          <span class="sf-hint">Kiểm soát ai có thể xem bài viết, hoạt động và danh sách yêu thích.</span>
          <div class="theme-options">
            <button type="button" :class="['theme-btn', { active: privacy.profile_visibility === 'public' }]" @click="setPrivacy('profile_visibility', 'public')">
              Công khai
            </button>
            <button type="button" :class="['theme-btn', { active: privacy.profile_visibility === 'followers' }]" @click="setPrivacy('profile_visibility', 'followers')">
              Người theo dõi
            </button>
            <button type="button" :class="['theme-btn', { active: privacy.profile_visibility === 'private' }]" @click="setPrivacy('profile_visibility', 'private')">
              Riêng tư
            </button>
          </div>
        </div>
        <label class="notif-pref-item" @click.prevent="setPrivacy('show_activity', !privacy.show_activity)">
          <div class="notif-pref-info">
            <span class="notif-pref-icon">📊</span>
            <div>
              <strong>Hiển thị hoạt động</strong>
              <span class="sf-hint">Cho người khác xem bạn đã thích, bình luận gì gần đây.</span>
            </div>
          </div>
          <input type="checkbox" class="toggle" :checked="privacy.show_activity" />
        </label>
        <label class="notif-pref-item" @click.prevent="setPrivacy('show_saved', !privacy.show_saved)">
          <div class="notif-pref-info">
            <span class="notif-pref-icon">💾</span>
            <div>
              <strong>Hiển thị danh sách đã lưu</strong>
              <span class="sf-hint">Cho người khác xem địa điểm bạn đã lưu.</span>
            </div>
          </div>
          <input type="checkbox" class="toggle" :checked="privacy.show_saved" />
        </label>
      </div>
    </div>

    <!-- Tab: Người chặn -->
    <div v-if="activeTab === 'chan'" class="settings-card card" role="tabpanel">
      <h2>Người bị chặn</h2>
      <div v-if="blockedLoading" class="sf-hint">Đang tải...</div>
      <div v-else-if="blockedUsers.length" class="sessions-list">
        <div v-for="b in blockedUsers" :key="b.id" class="session-item">
          <div class="session-info">
            <NuxtLink :to="`/nguoi-dung/${b.id}`" class="session-ua">{{ b.display_name || 'Người dùng' }}</NuxtLink>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" @click="unblockUser(b.id, b.display_name)">Bỏ chặn</button>
        </div>
      </div>
      <p v-else class="sf-hint">Bạn chưa chặn ai.</p>
    </div>

    <!-- Tab: Nguy hiểm -->
    <div v-if="activeTab === 'nguy-hiem'" class="settings-card card settings-danger" role="tabpanel">
      <h2>Vùng nguy hiểm</h2>
      <div class="danger-actions">
        <div class="danger-item">
          <div>
            <strong>Vô hiệu hóa tài khoản</strong>
            <p class="sf-hint">Tạm khóa — đăng nhập lại bằng OTP để kích hoạt.</p>
          </div>
          <button type="button" class="btn btn-ghost btn-danger-text" @click="deactivate">Vô hiệu hóa</button>
        </div>
        <div class="danger-item">
          <div>
            <strong>Xóa tài khoản</strong>
            <p class="sf-hint">Xóa vĩnh viễn tài khoản và toàn bộ dữ liệu.</p>
          </div>
          <button type="button" class="btn btn-ghost btn-danger-text" @click="deleteAccount">Xóa tài khoản</button>
        </div>
      </div>
    </div>
    </template>
  </section>
</template>

<script setup lang="ts">
const { user, isLoggedIn, authHeaders, fetchMe } = useAuth()
const { openAuth } = useAuthModal()
const { show: showToast } = useToast()
const colorModeState = useColorMode()
const colorMode = computed(() => colorModeState.preference)
watch(isLoggedIn, (v) => { if (!v) navigateTo('/') })
function setColorMode(mode: 'light' | 'dark' | 'system') {
  colorModeState.preference = mode
}
const route = useRoute()

useHead({
  title: 'Cài đặt',
  meta: [{ name: 'robots', content: 'noindex,nofollow' }],
  link: [{ rel: 'canonical', href: canonicalUrl('/cai-dat') }],
})

const TABS = [
  { key: 'ho-so', label: 'Hồ sơ', icon: '\u{1F464}' },
  { key: 'bao-mat', label: 'Bảo mật', icon: '\u{1F512}' },
  { key: 'thong-bao', label: 'Thông báo', icon: '🔔' },
  { key: 'giao-dien', label: 'Giao diện', icon: '🎨' },
  { key: 'rieng-tu', label: 'Riêng tư', icon: '🔒' },
  { key: 'chan', label: 'Chặn', icon: '\u{1F6AB}' },
  { key: 'nguy-hiem', label: 'Nguy hiểm', icon: '⚠️' },
] as const
type TabKey = typeof TABS[number]['key']

const activeTab = ref<TabKey>((route.hash?.slice(1) as TabKey) || 'ho-so')

function setTab(key: TabKey) {
  activeTab.value = key
  if (import.meta.client) window.history.replaceState(null, '', `#${key}`)
}

const displayName = ref(user.value?.display_name || '')
const bio = ref('')
const saving = ref(false)
const nameError = ref('')
const uploadingAvatar = ref(false)
const avatarPreview = ref('')

async function onAvatarChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  avatarPreview.value = URL.createObjectURL(file)
  uploadingAvatar.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    const res = await $fetch<{ avatar_url: string }>('/auth/avatar', {
      method: 'POST',
      headers: authHeaders(),
      body: form,
    })
    if (res.avatar_url) {
      await fetchMe()
      showToast('Đã cập nhật ảnh đại diện', 'success')
    }
  } catch (err: any) {
    avatarPreview.value = ''
    showToast(err?.data?.detail || 'Không thể tải ảnh lên', 'error')
  } finally {
    uploadingAvatar.value = false
  }
}

// Prefill bio from the public profile (User type doesn't carry bio).
onMounted(async () => {
  if (!user.value) return
  try {
    const res = await $fetch<Record<string, any>>(`/api/users/${user.value.id}`, { headers: authHeaders() })
    const u = res?.user ?? res
    if (u?.bio) bio.value = u.bio
    if (!displayName.value && u?.display_name) displayName.value = u.display_name
  } catch { /* prefill is best-effort */ }
  loadSessions()
  loadLoginHistory()
  loadPrivacy()
  loadBlocked()
  loadNotifPrefs()
})

const currentPw = ref('')
const newPw = ref('')
const savingPw = ref(false)

async function savePassword() {
  savingPw.value = true
  try {
    const body: Record<string, string> = { password: newPw.value }
    if (currentPw.value) body.current_password = currentPw.value
    await $fetch('/auth/set-password', { method: 'POST', headers: authHeaders(), body })
    showToast('Đã cập nhật mật khẩu', 'success')
    currentPw.value = ''
    newPw.value = ''
    await fetchMe()
  } catch (e: any) {
    showToast(e?.data?.detail || 'Không thể đổi mật khẩu', 'error')
  } finally { savingPw.value = false }
}

const sessions = ref<any[]>([])
const sessionsLoading = ref(true)

async function loadSessions() {
  sessionsLoading.value = true
  try {
    const res = await $fetch<{ sessions: any[] }>('/auth/sessions', { headers: authHeaders() })
    sessions.value = res.sessions || []
  } catch { /* ignore */ }
  sessionsLoading.value = false
}

function shortUA(ua: string): string {
  if (!ua) return 'Không rõ'
  if (ua.includes('Mobile')) return 'Di động'
  if (ua.includes('Windows')) return 'Windows'
  if (ua.includes('Mac')) return 'macOS'
  if (ua.includes('Linux')) return 'Linux'
  return ua.slice(0, 30)
}

async function revokeSession(id: string) {
  try {
    await $fetch(`/auth/sessions/${id}`, { method: 'DELETE', headers: authHeaders() })
    sessions.value = sessions.value.filter(s => s.id !== id)
    showToast('Đã thu hồi phiên', 'success')
  } catch { showToast('Không thể thu hồi phiên', 'error') }
}

const uploadingCover = ref(false)
const coverPreview = ref('')

async function onCoverChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  coverPreview.value = URL.createObjectURL(file)
  uploadingCover.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    const res = await $fetch<{ cover_url: string }>('/auth/cover', {
      method: 'POST',
      headers: authHeaders(),
      body: form,
    })
    if (res.cover_url) {
      await fetchMe()
      showToast('Đã cập nhật ảnh bìa', 'success')
    }
  } catch (err: any) {
    coverPreview.value = ''
    showToast(err?.data?.detail || 'Không thể tải ảnh bìa lên', 'error')
  } finally {
    uploadingCover.value = false
  }
}

const loginHistory = ref<any[]>([])
const loginHistoryLoading = ref(true)

async function loadLoginHistory() {
  loginHistoryLoading.value = true
  try {
    const res = await $fetch<{ history: any[] }>('/auth/login-history', { headers: authHeaders() })
    loginHistory.value = res.history || []
  } catch { /* ignore */ }
  loginHistoryLoading.value = false
}

const privacy = ref({ profile_visibility: 'public', show_activity: true, show_saved: true })
const privacyLoading = ref(true)

async function loadPrivacy() {
  privacyLoading.value = true
  try {
    const res = await $fetch<Record<string, any>>('/auth/privacy', { headers: authHeaders() })
    privacy.value = { profile_visibility: res.profile_visibility || 'public', show_activity: res.show_activity !== false, show_saved: res.show_saved !== false }
  } catch { /* ignore */ }
  privacyLoading.value = false
}

async function setPrivacy(key: string, value: any) {
  const prev = { ...privacy.value }
  ;(privacy.value as any)[key] = value
  try {
    await $fetch('/auth/privacy', { method: 'PUT', headers: { ...authHeaders(), 'Content-Type': 'application/json' }, body: { [key]: value } })
    showToast('Đã cập nhật quyền riêng tư', 'success')
  } catch {
    privacy.value = prev
    showToast('Không thể cập nhật', 'error')
  }
}

const blockedUsers = ref<any[]>([])
const blockedLoading = ref(true)

async function loadBlocked() {
  blockedLoading.value = true
  try {
    const res = await $fetch<{ users: any[] }>('/api/blocked-users', { headers: authHeaders() })
    blockedUsers.value = res.users || []
  } catch { /* ignore */ }
  blockedLoading.value = false
}

async function unblockUser(id: string, name: string) {
  try {
    await $fetch(`/api/notifications/block/${id}`, { method: 'POST', headers: authHeaders() })
    blockedUsers.value = blockedUsers.value.filter(u => u.id !== id)
    showToast(`${name || 'Người dùng'} đã được bỏ chặn`, 'success')
  } catch { showToast('Không thể bỏ chặn', 'error') }
}

const NOTIF_TYPES = [
  { key: 'like', pref: 'pref_like', icon: '❤️', label: 'Lượt thích', desc: 'Khi ai đó thích bài viết của bạn' },
  { key: 'comment', pref: 'pref_comment', icon: '💬', label: 'Bình luận', desc: 'Khi ai đó bình luận bài viết của bạn' },
  { key: 'follow', pref: 'pref_follow', icon: '👤', label: 'Theo dõi', desc: 'Khi ai đó theo dõi bạn' },
  { key: 'mention', pref: 'pref_mention', icon: '📣', label: 'Nhắc đến', desc: 'Khi ai đó nhắc đến bạn' },
  { key: 'system', pref: 'pref_system', icon: '🔔', label: 'Hệ thống', desc: 'Thông báo từ hệ thống và quản trị' },
] as const

const notifPrefs = ref<Record<string, boolean>>({ pref_like: true, pref_comment: true, pref_follow: true, pref_mention: true, pref_system: true })
const notifPrefsLoading = ref(true)

async function loadNotifPrefs() {
  notifPrefsLoading.value = true
  try {
    const res = await $fetch<Record<string, boolean>>('/api/notification-preferences', { headers: authHeaders() })
    Object.assign(notifPrefs.value, res)
  } catch { /* defaults stay */ }
  notifPrefsLoading.value = false
}

async function toggleNotifPref(prefKey: string) {
  const prev = notifPrefs.value[prefKey]
  notifPrefs.value[prefKey] = !prev
  try {
    await $fetch('/api/notification-preferences', { method: 'PUT', headers: { ...authHeaders(), 'Content-Type': 'application/json' }, body: { [prefKey]: !prev } })
    showToast('Đã lưu tùy chọn thông báo', 'success')
  } catch {
    notifPrefs.value[prefKey] = prev
    showToast('Không thể cập nhật tùy chọn', 'error')
  }
}

const { confirm } = useConfirm()

async function deactivate() {
  const ok = await confirm({ title: 'Vô hiệu hóa tài khoản?', message: 'Tài khoản sẽ bị khóa tạm thời. Đăng nhập lại bằng OTP để kích hoạt.', confirmText: 'Vô hiệu hóa', danger: true })
  if (!ok) return
  try {
    await $fetch('/auth/deactivate', { method: 'POST', headers: authHeaders() })
    showToast('Tài khoản đã bị vô hiệu hóa', 'success')
    navigateTo('/')
  } catch (e: any) { showToast(e?.data?.detail || 'Lỗi', 'error') }
}

async function deleteAccount() {
  const ok = await confirm({ title: 'Xóa tài khoản vĩnh viễn?', message: 'Toàn bộ dữ liệu sẽ bị xóa và không thể khôi phục.', confirmText: 'Xóa tài khoản', danger: true })
  if (!ok) return
  try {
    await $fetch('/auth/account', { method: 'DELETE', headers: authHeaders() })
    showToast('Đã xóa tài khoản', 'success')
    navigateTo('/')
  } catch (e: any) { showToast(e?.data?.detail || 'Lỗi', 'error') }
}

const { timeAgo } = useTimeAgo()

async function save() {
  nameError.value = ''
  const name = displayName.value.trim()
  if (name.length < 2) {
    nameError.value = 'Tên hiển thị phải từ 2 ký tự trở lên'
    return
  }
  saving.value = true
  try {
    await $fetch('/auth/profile', {
      method: 'PUT',
      headers: authHeaders(),
      body: { display_name: name, bio: bio.value.trim() },
    })
    await fetchMe()
    showToast('Đã lưu hồ sơ', 'success')
  } catch (e: any) {
    showToast(e?.data?.detail || 'Không thể lưu hồ sơ', 'error')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.settings-page { max-width: 640px; margin: 0 auto; }
.settings-title { font-size: 1.5rem; margin: 0 0 1rem; }
.settings-card, .settings-guest { padding: 1.5rem; }
.settings-guest h1 { margin: 0 0 1.25rem; font-size: 1.5rem; }
.settings-guest p { color: var(--ink-700); margin-bottom: 1rem; }

/* ── Tabs ── */
.settings-tabs {
  display: flex; gap: var(--space-2); margin-bottom: var(--space-5);
  border-bottom: 1px solid var(--line); padding-bottom: 0;
  overflow-x: auto; -webkit-overflow-scrolling: touch;
}
.settings-tab {
  display: inline-flex; align-items: center; gap: 6px;
  padding: .6rem 1rem; border: none; background: none;
  font-size: .88rem; font-weight: 500; color: var(--muted);
  cursor: pointer; white-space: nowrap; position: relative;
  border-bottom: 2px solid transparent; margin-bottom: -1px;
  transition: color .2s, border-color .2s;
}
.settings-tab:hover { color: var(--ink); }
.settings-tab.active { color: var(--accent, var(--primary, #219653)); border-bottom-color: var(--accent, var(--primary, #219653)); font-weight: 600; }
.settings-tab:focus-visible { outline: 2px solid var(--accent, var(--primary)); outline-offset: -2px; border-radius: 4px; }
.settings-tab-icon { font-size: 1rem; }
.settings-form { display: flex; flex-direction: column; gap: 1.25rem; }
.sf-field { display: flex; flex-direction: column; gap: .4rem; }
.sf-label { font-weight: 600; font-size: .95rem; }
.sf-hint { font-weight: 400; color: var(--ink-700); font-size: .85rem; }
.sf-input {
  width: 100%; padding: .65rem .8rem; border: 1px solid var(--border-input);
  border-radius: var(--radius-md); background: var(--bg); color: var(--ink-900);
  font: inherit;
}
.sf-input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.sf-textarea { resize: vertical; min-height: 90px; }
.sf-error { color: var(--danger, #c0392b); font-size: .85rem; }
.sf-actions { display: flex; gap: .75rem; align-items: center; }
.sf-avatar-section { display: flex; align-items: center; gap: 1rem; }
.sf-avatar-preview {
  width: 80px; height: 80px; border-radius: 50%; overflow: hidden; cursor: pointer;
  position: relative; flex-shrink: 0; border: 2px solid var(--border-input);
}
.sf-avatar-preview:hover .sf-avatar-overlay { opacity: 1; }
.sf-avatar-img { width: 100%; height: 100%; object-fit: cover; }
.sf-avatar-overlay {
  position: absolute; inset: 0; background: rgba(0,0,0,.45); color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 1.5rem;
  opacity: 0; transition: opacity .2s;
}
.sf-avatar-info { display: flex; flex-direction: column; gap: .25rem; }
.sf-avatar-info .sf-hint { font-size: .8rem; }
.btn-sm { padding: .3rem .7rem; font-size: .85rem; }
.settings-card h2 { margin: 0 0 1rem; font-size: 1.2rem; }
.settings-card + .settings-card { margin-top: 1.25rem; }
.sessions-list { display: flex; flex-direction: column; gap: .5rem; }
.session-item { display: flex; align-items: center; gap: .75rem; padding: .6rem .8rem; border: 1px solid var(--border-input); border-radius: var(--radius-md); }
.session-item.current { border-color: var(--accent); background: color-mix(in oklab, var(--accent) 5%, transparent); }
.session-info { flex: 1; display: flex; flex-direction: column; gap: .15rem; }
.session-ua { font-weight: 600; font-size: .9rem; }
.session-badge { font-size: .75rem; font-weight: 600; color: var(--accent); background: color-mix(in oklab, var(--accent) 12%, transparent); padding: .15rem .5rem; border-radius: var(--radius-full); }
.settings-danger { border-color: rgba(192,57,43,.2); }
.danger-actions { display: flex; flex-direction: column; gap: .75rem; }
.danger-item { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.danger-item p { margin: 0; }
.btn-danger-text { color: var(--danger, #c0392b) !important; }
.blocked-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: .5rem; }
.notif-prefs { display: flex; flex-direction: column; gap: .5rem; }
.notif-pref-item { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: .75rem .8rem; border: 1px solid var(--border-input); border-radius: var(--radius-md); cursor: pointer; transition: background .2s; }
.notif-pref-item:hover { background: var(--bg-warm); }
.notif-pref-info { display: flex; align-items: center; gap: .75rem; }
.notif-pref-icon { font-size: 1.25rem; flex-shrink: 0; }
.notif-pref-info strong { display: block; font-size: .9rem; }
.notif-pref-info .sf-hint { display: block; margin-top: .1rem; }
.toggle { appearance: none; width: 40px; height: 22px; background: var(--muted); border-radius: 11px; position: relative; cursor: pointer; transition: background .2s; flex-shrink: 0; }
.toggle::after { content: ''; position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; background: #fff; border-radius: 50%; transition: transform .2s; }
.toggle:checked { background: var(--accent, var(--primary)); }
.toggle:checked::after { transform: translateX(18px); }
.toggle:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

/* ── Cover photo ── */
.sf-cover-section { display: flex; align-items: flex-start; gap: 1rem; }
.sf-cover-preview {
  width: 200px; height: 68px; border-radius: var(--radius-md); overflow: hidden; cursor: pointer;
  position: relative; flex-shrink: 0; border: 2px solid var(--border-input);
}
.sf-cover-preview:hover .sf-avatar-overlay { opacity: 1; }
.sf-cover-img { width: 100%; height: 100%; object-fit: cover; }
.sf-cover-placeholder {
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
  background: var(--bg-warm); color: var(--ink-700); font-size: .85rem;
}
.login-fail { border-color: rgba(192,57,43,.3) !important; }
.login-ok { color: var(--accent); font-weight: 600; font-size: 1.1rem; }
.login-bad { color: var(--danger, #c0392b); font-weight: 600; font-size: 1.1rem; }

/* ── Theme toggle ── */
.theme-options { display: flex; gap: .5rem; flex-wrap: wrap; }
.theme-btn {
  display: flex; align-items: center; gap: .4rem; padding: .6rem 1rem;
  border: 2px solid var(--border-input); border-radius: var(--radius-md);
  background: var(--bg); color: var(--ink-700); cursor: pointer; font-size: .9rem;
  transition: border-color .2s, background .2s;
}
.theme-btn:hover { border-color: var(--ink-500); }
.theme-btn.active { border-color: var(--accent, var(--primary)); background: color-mix(in oklab, var(--accent, var(--primary)) 8%, transparent); color: var(--ink); font-weight: 600; }
.theme-icon { font-size: 1.1rem; }

/* ── Dark mode ── */
.dark .sf-input { background: var(--bg-alt); border-color: var(--line); color: var(--ink); }
.dark .session-item { border-color: var(--line); background: var(--bg-alt); }
.dark .session-item.current { border-color: var(--accent); background: color-mix(in oklab, var(--accent) 8%, var(--bg-alt)); }
.dark .settings-danger { border-color: rgba(192,57,43,.3); }
.dark .sf-avatar-preview { border-color: var(--line); }
.dark .notif-pref-item { border-color: var(--line); }
.dark .notif-pref-item:hover { background: var(--bg-alt); }

/* ── Mobile ── */
@media (max-width: 600px) {
  .settings-page { padding: var(--space-4) var(--space-3); }
  .settings-card, .settings-guest { padding: var(--space-4); }
  .sf-avatar-section { flex-direction: column; align-items: flex-start; }
  .danger-item { flex-direction: column; align-items: flex-start; gap: .5rem; }
  .settings-tabs { gap: 0; }
  .settings-tab { padding: .5rem .65rem; font-size: .8rem; }
}
</style>
