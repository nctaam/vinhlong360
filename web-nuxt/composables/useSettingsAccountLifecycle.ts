import { ref } from 'vue'
import { getStatusCode, extractErrorMessage } from '~/composables/useFetchError'
import { consumeLifecycleClearInstruction } from '~/composables/useLifecycleClear'

export type ConsentHistoryItem = { id: string; version: string | null; created_at: string }
export type DeleteAccountResponse = { status: string; message: string; grace_days: number; browser_clear_instruction?: unknown }

export interface UseSettingsAccountLifecycleOptions {
  authHeaders?: () => Record<string, string>
  fetchMe?: () => Promise<unknown>
  handleSessionExpired?: () => void
  showToast?: (message: string, type?: 'info' | 'success' | 'warning' | 'error') => void
  confirm?: (message: string, options?: { title?: string; confirmText?: string; danger?: boolean }) => Promise<boolean>
  navigateTo?: (to: string) => Promise<unknown> | void
}

export function formatConsentDate(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return 'Không rõ thời điểm'
  return parsed.toLocaleDateString('vi-VN', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function useSettingsAccountLifecycle(options: UseSettingsAccountLifecycleOptions = {}) {
  const authHeaders = options.authHeaders ?? (() => ({}))
  const fetchMe = options.fetchMe ?? (() => Promise.resolve())
  const handleSessionExpired = options.handleSessionExpired ?? (() => {})
  const showToast = options.showToast ?? (() => {})
  const confirm = options.confirm ?? (() => Promise.resolve(true))
  const navigate = options.navigateTo ?? ((to: string) => { if (typeof navigateTo === 'function') navigateTo(to) })

  // ── Data & legal ──
  const exportLoading = ref(false)
  const consentHistory = ref<ConsentHistoryItem[]>([])
  const consentLoaded = ref(false)
  const deleteConfirmVisible = ref(false)
  const deleteBusy = ref(false)
  const accountStatus = ref('')

  async function exportData() {
    exportLoading.value = true
    try {
      const data = await $fetch<Record<string, any>>('/auth/export-data', { headers: authHeaders() })
      if (typeof document !== 'undefined') {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `vinhlong360-data-${new Date().toISOString().slice(0, 10)}.json`
        a.click()
        URL.revokeObjectURL(url)
      }
      showToast('Đã tải dữ liệu', 'success')
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast(extractErrorMessage(e, 'Không thể xuất dữ liệu'), 'error')
    } finally {
      exportLoading.value = false
    }
  }

  async function loadConsent() {
    try {
      const data = await $fetch<{ history: ConsentHistoryItem[] }>('/auth/consent-history', { headers: authHeaders() })
      consentHistory.value = data.history || []
      consentLoaded.value = true
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast(extractErrorMessage(e, 'Không thể tải lịch sử'), 'error')
      consentLoaded.value = true
    }
  }

  async function deactivate() {
    const ok = await confirm('Tài khoản sẽ bị khóa tạm thời. Đăng nhập lại bằng OTP để kích hoạt.', {
      title: 'Vô hiệu hóa tài khoản?',
      confirmText: 'Vô hiệu hóa',
      danger: true,
    })
    if (!ok) return
    try {
      await $fetch('/auth/deactivate', { method: 'POST', headers: authHeaders() })
      await fetchMe()
      showToast('Tài khoản đã bị vô hiệu hóa', 'success')
      navigate('/')
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast(extractErrorMessage(e, 'Lỗi'), 'error')
    }
  }

  async function deleteAccount() {
    if (deleteBusy.value) return
    deleteBusy.value = true
    accountStatus.value = ''
    try {
      const result = await $fetch<DeleteAccountResponse>('/auth/account', { method: 'DELETE', headers: authHeaders() })
      if (result.browser_clear_instruction) {
        try {
          if (typeof localStorage !== 'undefined') {
            localStorage.setItem('vl360_erasure_clear_instruction', JSON.stringify(result.browser_clear_instruction))
          }
        } catch { /* storage unavailable */ }
        consumeLifecycleClearInstruction(result.browser_clear_instruction)
      }
      const gracePhrase = `${result.grace_days} ngày`
      const messageIncludesGrace = result.message
        .toLocaleLowerCase('vi-VN')
        .replace(/\s+/g, ' ')
        .includes(gracePhrase.toLocaleLowerCase('vi-VN'))
      const graceCopy = Number.isFinite(result.grace_days) && result.grace_days > 0 && !messageIncludesGrace
        ? ` Thời gian chờ: ${gracePhrase}.`
        : ''
      accountStatus.value = `${result.message}${graceCopy}`.trim()
      deleteConfirmVisible.value = false
      showToast(result.message, result.status === 'scheduled' ? 'success' : 'info')
      await fetchMe()
      navigate('/')
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast(extractErrorMessage(e, 'Lỗi'), 'error')
    } finally {
      deleteBusy.value = false
    }
  }

  return {
    exportLoading,
    consentHistory,
    consentLoaded,
    deleteConfirmVisible,
    deleteBusy,
    accountStatus,
    exportData,
    loadConsent,
    formatConsentDate,
    deactivate,
    deleteAccount,
  }
}
