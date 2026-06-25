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
          <div class="sf-avatar-preview" @click="($refs.avatarInput as HTMLInputElement)?.click()">
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
            <span v-if="!saving">Lưu thay đổi</span>
            <span v-else class="spinner spinner-sm" aria-label="Đang lưu"></span>
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
const route = useRoute()

useHead({
  title: 'Cài đặt',
  meta: [{ name: 'robots', content: 'noindex,nofollow' }],
  link: [{ rel: 'canonical', href: canonicalUrl('/cai-dat') }],
})

const TABS = [
  { key: 'ho-so', label: 'Hồ sơ', icon: '\u{1F464}' },
  { key: 'bao-mat', label: 'Bảo mật', icon: '\u{1F512}' },
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
  loadBlocked()
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
</style>
