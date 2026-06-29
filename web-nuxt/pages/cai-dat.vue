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
        :id="`tab-${t.key}`"
        class="settings-tab" :class="{ active: activeTab === t.key }"
        :aria-selected="activeTab === t.key"
        :aria-controls="`panel-${t.key}`"
        @click="setTab(t.key)"
      >
        <span class="settings-tab-icon" aria-hidden="true">{{ t.icon }}</span>
        {{ t.label }}
      </button>
    </nav>

    <!-- Tab: Hồ sơ -->
    <div v-show="activeTab === 'ho-so'" :id="`panel-ho-so`" class="settings-card card" role="tabpanel" aria-labelledby="tab-ho-so">
      <h2>Hồ sơ cá nhân</h2>
      <form class="settings-form" @submit.prevent="save">
        <div class="sf-avatar-section">
          <button type="button" class="sf-avatar-preview" aria-label="Thay đổi ảnh đại diện" @click="($refs.avatarInput as HTMLInputElement)?.click()">
            <img v-if="avatarPreview || user?.avatar_url" :src="avatarPreview || user?.avatar_url!" alt="Avatar" class="sf-avatar-img" width="96" height="96" loading="lazy" decoding="async" @error="(e: Event) => ((e.target as HTMLImageElement).style.display = 'none')" />
            <AvatarPlaceholder v-else :initial="user?.display_name?.[0]?.toUpperCase()" />
            <span class="sf-avatar-overlay">&#128247;</span>
          </button>
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
          <button type="button" class="sf-cover-preview" aria-label="Thay đổi ảnh bìa" @click="($refs.coverInput as HTMLInputElement)?.click()">
            <img v-if="coverPreview || user?.cover_url" :src="coverPreview || user?.cover_url!" alt="Ảnh bìa" class="sf-cover-img" width="640" height="160" loading="lazy" decoding="async" @error="(e: Event) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
            <div v-else class="sf-cover-placeholder">
              <span>Thêm ảnh bìa</span>
            </div>
            <span class="sf-avatar-overlay">&#128247;</span>
          </button>
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
            enterkeyhint="done"
            maxlength="50"
            required
            :aria-invalid="!!nameError"
            placeholder="Tên bạn muốn hiển thị"
          />
          <span v-if="nameError" class="sf-error" role="alert">{{ nameError }}</span>
        </label>

        <label class="sf-field">
          <span class="sf-label">Username <span class="sf-hint">— dùng làm đường dẫn hồ sơ</span></span>
          <div class="sf-username-row">
            <span class="sf-username-prefix">vinhlong360.vn/nguoi-dung/</span>
            <input
              v-model="username"
              type="text"
              class="sf-input sf-username-input"
              maxlength="30"
              minlength="3"
              pattern="[a-z][a-z0-9._-]*"
              placeholder="ten-cua-ban"
              autocomplete="username"
              @input="onUsernameInput"
            />
          </div>
          <span v-if="usernameStatus === 'taken'" class="sf-error" role="alert">Username đã được sử dụng</span>
          <span v-else-if="usernameStatus === 'invalid'" class="sf-error" role="alert">{{ usernameError }}</span>
          <span v-else-if="usernameStatus === 'ok'" class="sf-success">Username khả dụng ✓</span>
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
          <NuxtLink v-if="user" :to="`/nguoi-dung/${savedUsername || user.id}`" class="btn btn-ghost">Xem hồ sơ</NuxtLink>
        </div>
      </form>
    </div>

    <!-- Tab: Bảo mật -->
    <div v-if="activeTab === 'bao-mat'" id="panel-bao-mat" role="tabpanel" aria-labelledby="tab-bao-mat">
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
          <label class="sf-field">
            <span class="sf-label">Xác nhận mật khẩu</span>
            <input v-model="confirmPw" type="password" class="sf-input" minlength="6" autocomplete="new-password" required />
            <span v-if="confirmPw && confirmPw !== newPw" class="sf-error" role="alert">Mật khẩu xác nhận không khớp</span>
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
        <div v-if="sessionsLoading" class="sf-loading"><div class="spinner spinner-sm"></div> Đang tải...</div>
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
        <div v-if="loginHistoryLoading" class="sf-loading"><div class="spinner spinner-sm"></div> Đang tải...</div>
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
    <div v-if="activeTab === 'thong-bao'" id="panel-thong-bao" class="settings-card card" role="tabpanel" aria-labelledby="tab-thong-bao">
      <h2>Tùy chọn thông báo</h2>
      <p class="sf-hint sf-hint-spaced">Chọn loại thông báo bạn muốn nhận.</p>
      <div v-if="notifPrefsLoading" class="sf-loading"><div class="spinner spinner-sm"></div> Đang tải...</div>
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
    <div v-if="activeTab === 'giao-dien'" id="panel-giao-dien" class="settings-card card" role="tabpanel" aria-labelledby="tab-giao-dien">
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
    <div v-if="activeTab === 'rieng-tu'" id="panel-rieng-tu" class="settings-card card" role="tabpanel" aria-labelledby="tab-rieng-tu">
      <h2>Quyền riêng tư</h2>
      <div v-if="privacyLoading" class="sf-loading"><div class="spinner spinner-sm"></div> Đang tải...</div>
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
    <div v-if="activeTab === 'chan'" id="panel-chan" class="settings-card card" role="tabpanel" aria-labelledby="tab-chan">
      <h2>Người bị chặn</h2>
      <div v-if="blockedLoading" class="sf-hint">Đang tải...</div>
      <div v-else-if="blockedUsers.length" class="sessions-list">
        <div v-for="b in blockedUsers" :key="b.id" class="session-item">
          <div class="session-info">
            <NuxtLink :to="`/nguoi-dung/${b.username || b.id}`" class="session-ua">{{ b.display_name || 'Người dùng' }}</NuxtLink>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" @click="unblockUser(b.id, b.display_name)">Bỏ chặn</button>
        </div>
      </div>
      <p v-else class="sf-hint">Bạn chưa chặn ai.</p>
    </div>

    <!-- Tab: Nguy hiểm -->
    <div v-if="activeTab === 'nguy-hiem'" id="panel-nguy-hiem" class="settings-card card settings-danger" role="tabpanel" aria-labelledby="tab-nguy-hiem">
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
const { user, isLoggedIn, authHeaders, fetchMe, handleSessionExpired } = useAuth()
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

const validKeys = new Set(TABS.map(t => t.key))
const hashKey = route.hash?.slice(1)
const activeTab = ref<TabKey>(validKeys.has(hashKey as TabKey) ? (hashKey as TabKey) : 'ho-so')

const tabLoaded = reactive(new Set<TabKey>())
function setTab(key: TabKey) {
  activeTab.value = key
  if (import.meta.client) window.history.replaceState(null, '', `#${key}`)
  lazyLoadTab(key)
}
function lazyLoadTab(key: TabKey) {
  if (tabLoaded.has(key)) return
  tabLoaded.add(key)
  if (key === 'bao-mat') { loadSessions(); loadLoginHistory() }
  else if (key === 'rieng-tu') loadPrivacy()
  else if (key === 'chan') loadBlocked()
  else if (key === 'thong-bao') loadNotifPrefs()
}

const displayName = ref(user.value?.display_name || '')
const bio = ref('')
const savedName = ref(displayName.value)
const savedBio = ref('')
const isDirty = computed(() => displayName.value !== savedName.value || bio.value !== savedBio.value || username.value !== savedUsername.value)
const saving = ref(false)
const nameError = ref('')
const username = ref(user.value?.username || '')
const savedUsername = ref(username.value)
const usernameStatus = ref<'' | 'ok' | 'taken' | 'invalid' | 'checking'>('')
const usernameError = ref('')
let usernameCheckTimer: ReturnType<typeof setTimeout> | null = null

function onUsernameInput() {
  const val = username.value.trim().toLowerCase()
  if (!val) { usernameStatus.value = ''; return }
  if (val.length < 3) { usernameStatus.value = 'invalid'; usernameError.value = 'Tối thiểu 3 ký tự'; return }
  if (!/^[a-z][a-z0-9._-]*$/.test(val)) { usernameStatus.value = 'invalid'; usernameError.value = 'Chỉ chữ cái, số, dấu chấm, gạch ngang'; return }
  usernameStatus.value = 'checking'
  if (usernameCheckTimer) clearTimeout(usernameCheckTimer)
  usernameCheckTimer = setTimeout(async () => {
    try {
      const res = await $fetch<{ available: boolean; reason?: string }>(`/auth/check-username/${encodeURIComponent(val)}`, { headers: authHeaders() })
      if (username.value.trim().toLowerCase() !== val) return
      if (res.available) { usernameStatus.value = 'ok' }
      else { usernameStatus.value = 'taken'; usernameError.value = res.reason || 'Đã được sử dụng' }
    } catch { usernameStatus.value = '' }
  }, 500)
}

const uploadingAvatar = ref(false)
const avatarPreview = ref('')

const ALLOWED_IMG = ['image/jpeg', 'image/png', 'image/webp']
const MAX_IMG_SIZE = 12 * 1024 * 1024

async function onAvatarChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!ALLOWED_IMG.includes(file.type)) { showToast('Chỉ hỗ trợ JPEG, PNG hoặc WebP', 'error'); return }
  if (file.size > MAX_IMG_SIZE) { showToast('Ảnh quá lớn (tối đa 12MB)', 'error'); return }
  if (avatarPreview.value?.startsWith('blob:')) URL.revokeObjectURL(avatarPreview.value)
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
  } catch (err: unknown) {
    avatarPreview.value = ''
    if (getStatusCode(err) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(err, 'Không thể tải ảnh lên'), 'error')
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
    if (u?.bio) { bio.value = u.bio; savedBio.value = u.bio }
    if (!displayName.value && u?.display_name) { displayName.value = u.display_name; savedName.value = u.display_name }
    if (u?.username) { username.value = u.username; savedUsername.value = u.username }
  } catch { /* prefill is best-effort */ }
  lazyLoadTab(activeTab.value)
})

const currentPw = ref('')
const newPw = ref('')
const confirmPw = ref('')
const savingPw = ref(false)

async function savePassword() {
  if (user.value?.has_password && !currentPw.value) {
    showToast('Vui lòng nhập mật khẩu hiện tại', 'error')
    return
  }
  if (!newPw.value || newPw.value.length < 6) {
    showToast('Mật khẩu mới phải từ 6 ký tự trở lên', 'error')
    return
  }
  if (newPw.value !== confirmPw.value) {
    showToast('Mật khẩu xác nhận không khớp', 'error')
    return
  }
  savingPw.value = true
  try {
    const body: Record<string, string> = { password: newPw.value }
    if (currentPw.value) body.current_password = currentPw.value
    await $fetch('/auth/set-password', { method: 'POST', headers: authHeaders(), body })
    showToast('Đã cập nhật mật khẩu', 'success')
    currentPw.value = ''
    newPw.value = ''
    confirmPw.value = ''
    await fetchMe()
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(e, 'Không thể đổi mật khẩu'), 'error')
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
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể thu hồi phiên', 'error')
  }
}

const uploadingCover = ref(false)
const coverPreview = ref('')

async function onCoverChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!ALLOWED_IMG.includes(file.type)) { showToast('Chỉ hỗ trợ JPEG, PNG hoặc WebP', 'error'); return }
  if (file.size > MAX_IMG_SIZE) { showToast('Ảnh quá lớn (tối đa 12MB)', 'error'); return }
  if (coverPreview.value?.startsWith('blob:')) URL.revokeObjectURL(coverPreview.value)
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
  } catch (err: unknown) {
    coverPreview.value = ''
    if (getStatusCode(err) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(err, 'Không thể tải ảnh bìa lên'), 'error')
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
  } catch (e: unknown) {
    privacy.value = prev
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể cập nhật', 'error')
  }
}

const blockedUsers = ref<any[]>([])
const blockedLoading = ref(true)

async function loadBlocked() {
  blockedLoading.value = true
  try {
    const res = await $fetch<{ blocked: any[] }>('/api/blocked-users', { headers: authHeaders() })
    blockedUsers.value = res.blocked || []
  } catch { /* ignore */ }
  blockedLoading.value = false
}

async function unblockUser(id: string, name: string) {
  try {
    await $fetch(`/api/notifications/block/${id}`, { method: 'POST', headers: authHeaders() })
    blockedUsers.value = blockedUsers.value.filter(u => u.id !== id)
    showToast(`${name || 'Người dùng'} đã được bỏ chặn`, 'success')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể bỏ chặn', 'error')
  }
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
  } catch (e: unknown) {
    notifPrefs.value[prefKey] = prev
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể cập nhật tùy chọn', 'error')
  }
}

const { confirm } = useConfirm()

async function deactivate() {
  const ok = await confirm({ title: 'Vô hiệu hóa tài khoản?', message: 'Tài khoản sẽ bị khóa tạm thời. Đăng nhập lại bằng OTP để kích hoạt.', confirmText: 'Vô hiệu hóa', danger: true })
  if (!ok) return
  try {
    await $fetch('/auth/deactivate', { method: 'POST', headers: authHeaders() })
    await fetchMe()
    showToast('Tài khoản đã bị vô hiệu hóa', 'success')
    navigateTo('/')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(e, 'Lỗi'), 'error')
  }
}

async function deleteAccount() {
  const ok = await confirm({ title: 'Xóa tài khoản vĩnh viễn?', message: 'Toàn bộ dữ liệu sẽ bị xóa và không thể khôi phục.', confirmText: 'Xóa tài khoản', danger: true })
  if (!ok) return
  try {
    await $fetch('/auth/account', { method: 'DELETE', headers: authHeaders() })
    await fetchMe()
    showToast('Đã xóa tài khoản', 'success')
    navigateTo('/')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(e, 'Lỗi'), 'error')
  }
}

const { timeAgo } = useTimeAgo()

async function save() {
  nameError.value = ''
  const name = displayName.value.trim()
  if (name.length < 2) {
    nameError.value = 'Tên hiển thị phải từ 2 ký tự trở lên'
    return
  }
  if (usernameStatus.value === 'taken' || usernameStatus.value === 'invalid') {
    showToast('Vui lòng kiểm tra lại username', 'error')
    return
  }
  saving.value = true
  try {
    const body: Record<string, any> = { display_name: name, bio: bio.value.trim() }
    const uname = username.value.trim().toLowerCase()
    if (uname !== savedUsername.value) body.username = uname || null
    await $fetch('/auth/profile', {
      method: 'PUT',
      headers: authHeaders(),
      body,
    })
    await fetchMe()
    savedName.value = displayName.value
    savedBio.value = bio.value
    savedUsername.value = username.value.trim().toLowerCase()
    usernameStatus.value = ''
    showToast('Đã lưu hồ sơ', 'success')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    if (getStatusCode(e) === 409) { usernameStatus.value = 'taken'; showToast('Username đã được sử dụng', 'error'); return }
    showToast(extractErrorMessage(e, 'Không thể lưu hồ sơ'), 'error')
  } finally {
    saving.value = false
  }
}

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (isDirty.value) e.preventDefault()
}
function onPopState() {
  const hash = window.location.hash.slice(1) as TabKey
  if (hash && TABS.some(t => t.key === hash)) activeTab.value = hash
}
onMounted(() => {
  if (import.meta.client) {
    window.addEventListener('beforeunload', onBeforeUnload)
    window.addEventListener('popstate', onPopState)
  }
})
onUnmounted(() => {
  if (import.meta.client) {
    window.removeEventListener('beforeunload', onBeforeUnload)
    window.removeEventListener('popstate', onPopState)
  }
  if (avatarPreview.value?.startsWith('blob:')) URL.revokeObjectURL(avatarPreview.value)
  if (coverPreview.value?.startsWith('blob:')) URL.revokeObjectURL(coverPreview.value)
  if (usernameCheckTimer) clearTimeout(usernameCheckTimer)
})
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
.settings-tab.active .settings-tab-icon { transform: scale(1.15); }
.settings-tab:focus-visible { outline: 2px solid var(--accent, var(--primary)); outline-offset: -2px; border-radius: 4px; }
.settings-tab-icon { font-size: 1rem; transition: transform .25s var(--ease-spring-gentle, cubic-bezier(.2,1,.4,1)); }
.settings-form { display: flex; flex-direction: column; gap: 1.25rem; }
.sf-field { display: flex; flex-direction: column; gap: .4rem; }
.sf-label { font-weight: 600; font-size: .95rem; }
.sf-hint { font-weight: 400; color: var(--ink-700); font-size: .85rem; }
.sf-input {
  width: 100%; padding: .65rem .8rem; border: 1px solid var(--border-input);
  border-radius: var(--radius-md); background: var(--bg); color: var(--ink-900);
  font: inherit; transition: border-color .25s var(--ease-out), box-shadow .25s var(--ease-out), background .25s var(--ease-out);
}
.sf-input:hover:not(:focus) { border-color: var(--ink-700); }
.sf-input:focus-visible { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(var(--accent-rgb, 33,150,83), .15); background: var(--card); }
.sf-textarea { resize: vertical; min-height: 90px; }
.sf-error { color: var(--danger, #c0392b); font-size: .85rem; }
.sf-success { color: var(--accent, #219653); font-size: .85rem; }
.sf-loading { display: flex; align-items: center; gap: var(--space-2); color: var(--ink-700); font-size: .85rem; padding: var(--space-4) 0; }
.sf-hint-spaced { margin-bottom: var(--space-4); }
.sf-username-row { display: flex; align-items: center; gap: 0; border: 1px solid var(--border-input); border-radius: var(--radius-md); overflow: hidden; }
.sf-username-prefix { padding: .65rem .6rem; background: var(--bg-warm, #f5f5f5); color: var(--ink-700); font-size: .85rem; white-space: nowrap; border-right: 1px solid var(--border-input); flex-shrink: 0; }
.sf-username-input { border: none !important; border-radius: 0 !important; flex: 1; min-width: 0; }
.sf-actions { display: flex; gap: .75rem; align-items: center; }
.sf-avatar-section { display: flex; align-items: center; gap: 1rem; }
.sf-avatar-preview {
  width: 80px; height: 80px; border-radius: 50%; overflow: hidden; cursor: pointer;
  position: relative; flex-shrink: 0; border: 2px solid var(--border-input);
  padding: 0; background: none; font: inherit; text-align: left;
}
.sf-avatar-preview:hover .sf-avatar-overlay { opacity: 1; }
.sf-avatar-img { width: 100%; height: 100%; object-fit: cover; }
.sf-avatar-overlay {
  position: absolute; inset: 0; background: rgba(0,0,0,.45); color: var(--text-on-dark, #fff);
  display: flex; align-items: center; justify-content: center; font-size: 1.5rem;
  opacity: 0; transition: opacity .2s;
}
.sf-avatar-info { display: flex; flex-direction: column; gap: .25rem; }
.sf-avatar-info .sf-hint { font-size: .8rem; }
.btn-sm { padding: .3rem .7rem; font-size: .85rem; }
.settings-card h2 { margin: 0 0 1rem; font-size: 1.2rem; padding-bottom: var(--space-3); border-bottom: 1px solid var(--line); }
.settings-card + .settings-card { margin-top: 1.25rem; }
.sessions-list { display: flex; flex-direction: column; gap: .5rem; }
.session-item { display: flex; align-items: center; gap: .75rem; padding: .6rem .8rem; border: 1px solid var(--border-input); border-radius: var(--radius-md); }
.session-item.current { border-color: var(--accent); background: color-mix(in oklab, var(--accent) 5%, transparent); }
.session-info { flex: 1; display: flex; flex-direction: column; gap: .15rem; }
.session-ua { font-weight: 600; font-size: .9rem; }
.session-badge { font-size: .75rem; font-weight: 600; color: var(--accent); background: color-mix(in oklab, var(--accent) 12%, transparent); padding: .15rem .5rem; border-radius: var(--radius-full); }
.settings-danger { border-color: rgba(192,57,43,.2); border-left: 3px solid var(--error, #c0392b); }
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
.toggle { appearance: none; width: 40px; height: 22px; background: var(--muted); border-radius: 11px; position: relative; cursor: pointer; transition: background .25s var(--ease-out, ease); flex-shrink: 0; min-height: 44px; padding: 11px 0; box-sizing: content-box; }
.toggle::after { content: ''; position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; background: var(--white, #fff); border-radius: 50%; transition: transform .3s var(--ease-spring-gentle, cubic-bezier(.2,1,.4,1)); box-shadow: 0 1px 3px rgba(0,0,0,.15); }
.toggle:checked { background: var(--accent, var(--primary)); }
.toggle:checked::after { transform: translateX(18px); }
.toggle:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.toggle:active::after { width: 22px; }

/* ── Cover photo ── */
.sf-cover-section { display: flex; align-items: flex-start; gap: 1rem; overflow: hidden; }
.sf-cover-preview {
  width: 200px; height: 68px; border-radius: var(--radius-md); overflow: hidden; cursor: pointer;
  position: relative; flex-shrink: 0; border: 2px solid var(--border-input);
  padding: 0; background: none; font: inherit; text-align: left;
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
.dark .sf-username-row { border-color: var(--line); }
.dark .sf-username-prefix { background: var(--bg-alt); border-color: var(--line); }
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
  .sf-input { font-size: 16px; }
  .sf-username-prefix { font-size: .75rem; padding: .65rem .4rem; }
}
</style>
