import { ref } from 'vue'
import { getStatusCode } from '~/composables/useFetchError'

export const NOTIF_TYPES = [
  { key: 'like', pref: 'pref_like', icon: 'heart', label: 'Lượt thích', desc: 'Khi ai đó thích bài viết của bạn' },
  { key: 'comment', pref: 'pref_comment', icon: 'message', label: 'Bình luận', desc: 'Khi ai đó bình luận bài viết của bạn' },
  { key: 'follow', pref: 'pref_follow', icon: 'user', label: 'Theo dõi', desc: 'Khi ai đó theo dõi bạn' },
  { key: 'mention', pref: 'pref_mention', icon: 'megaphone', label: 'Nhắc đến', desc: 'Khi ai đó nhắc đến bạn' },
  { key: 'system', pref: 'pref_system', icon: 'bell', label: 'Hệ thống', desc: 'Thông báo từ hệ thống và quản trị' },
] as const

export interface UseSettingsModerationOptions {
  authHeaders?: () => Record<string, string>
  handleSessionExpired?: () => void
  showToast?: (message: string, type?: 'info' | 'success' | 'warning' | 'error') => void
}

export function useSettingsModeration(options: UseSettingsModerationOptions = {}) {
  const authHeaders = options.authHeaders ?? (() => ({}))
  const handleSessionExpired = options.handleSessionExpired ?? (() => {})
  const showToast = options.showToast ?? (() => {})

  // ── Privacy ──
  const privacy = ref({ profile_visibility: 'public', show_activity: true, show_saved: true })
  const privacyLoading = ref(true)

  async function loadPrivacy() {
    privacyLoading.value = true
    try {
      const res = await $fetch<Record<string, any>>('/auth/privacy', { headers: authHeaders() })
      privacy.value = {
        profile_visibility: res.profile_visibility || 'public',
        show_activity: res.show_activity !== false,
        show_saved: res.show_saved !== false,
      }
    } catch { /* ignore */ }
    privacyLoading.value = false
  }

  async function setPrivacy(key: string, value: any) {
    const prev = { ...privacy.value }
    ;(privacy.value as any)[key] = value
    try {
      await $fetch('/auth/privacy', {
        method: 'PUT',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: { [key]: value },
      })
      showToast('Đã cập nhật quyền riêng tư', 'success')
    } catch (e: unknown) {
      privacy.value = prev
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể cập nhật', 'error')
    }
  }

  // ── Blocked Users ──
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

  // ── Muted Users ──
  const mutedUsers = ref<any[]>([])
  const mutedLoading = ref(true)

  async function loadMutedUsers() {
    mutedLoading.value = true
    try {
      const res = await $fetch<{ muted: any[] }>('/api/muted-users', { headers: authHeaders() })
      mutedUsers.value = res.muted || []
    } catch { /* ignore */ }
    mutedLoading.value = false
  }

  async function unmuteUser(id: string, name: string) {
    try {
      await $fetch(`/api/mute/${encodeURIComponent(id)}`, { method: 'POST', headers: authHeaders() })
      mutedUsers.value = mutedUsers.value.filter(u => u.id !== id)
      showToast(`Đã bỏ tắt tiếng ${name || 'người dùng'}`, 'success')
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể bỏ tắt tiếng', 'error')
    }
  }

  // ── Notification Preferences ──
  const notifPrefs = ref<Record<string, boolean>>({
    pref_like: true,
    pref_comment: true,
    pref_follow: true,
    pref_mention: true,
    pref_system: true,
  })
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
    const prev = notifPrefs.value[prefKey] ?? false
    notifPrefs.value[prefKey] = !prev
    try {
      await $fetch('/api/notification-preferences', {
        method: 'PUT',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: { [prefKey]: !prev },
      })
      showToast('Đã lưu tùy chọn thông báo', 'success')
    } catch (e: unknown) {
      notifPrefs.value[prefKey] = prev
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể cập nhật tùy chọn', 'error')
    }
  }

  return {
    privacy,
    privacyLoading,
    loadPrivacy,
    setPrivacy,
    blockedUsers,
    blockedLoading,
    loadBlocked,
    unblockUser,
    mutedUsers,
    mutedLoading,
    loadMutedUsers,
    unmuteUser,
    NOTIF_TYPES,
    notifPrefs,
    notifPrefsLoading,
    loadNotifPrefs,
    toggleNotifPref,
  }
}
