import { ref, computed, type Ref } from 'vue'
import { getStatusCode, extractErrorMessage } from '~/composables/useFetchError'

export const COMMON_PASSWORDS = new Set([
  '123456', 'password', '12345678', 'qwerty', 'abc123', 'monkey', 'master',
  '111111', '123123', 'letmein', 'dragon', 'baseball', 'iloveyou', 'trustno1',
  'sunshine', 'princess', 'football', 'shadow', 'superman', 'michael',
])

const RE_INTERNAL_UA = /(?:python|urllib|httpx|aiohttp|curl|wget|healthcheck|uptime|node|undici|node-fetch)/i
const RE_LOWER = /[a-z]/
const RE_UPPER = /[A-Z]/
const RE_DIGIT = /\d/
const RE_NON_ALNUM = /[^a-zA-Z0-9]/

const PW_STRENGTH_EMPTY = Object.freeze({ score: 0, label: '', color: '' })
const PW_STRENGTH_COMMON = Object.freeze({ score: 1, label: 'Rất yếu', color: 'var(--error)' })
const PW_STRENGTH_BY_LEVEL = Object.freeze([
  PW_STRENGTH_EMPTY,
  Object.freeze({ score: 1, label: 'Yếu', color: 'var(--error)' }),
  Object.freeze({ score: 2, label: 'Trung bình', color: 'var(--warning)' }),
  Object.freeze({ score: 3, label: 'Mạnh', color: 'var(--success)' }),
  Object.freeze({ score: 4, label: 'Rất mạnh', color: 'var(--color-brand)' }),
])

function isAbortError(err: unknown): boolean {
  return Boolean(err && typeof err === 'object' && ((err as any).name === 'AbortError' || (err as any).cause?.name === 'AbortError'))
}

export function isInternalUA(ua: string): boolean {
  return Boolean(ua) && RE_INTERNAL_UA.test(ua)
}

export function shortUA(ua: string): string {
  if (!ua) return 'Không rõ'
  if (isInternalUA(ua)) return 'Phiên hệ thống'
  if (ua.includes('Mobile')) return 'Di động'
  if (ua.includes('Windows')) return 'Windows'
  if (ua.includes('Mac')) return 'macOS'
  if (ua.includes('Linux')) return 'Linux'
  return ua.slice(0, 30)
}

export interface UseSettingsSecurityOptions {
  user?: Ref<any>
  authHeaders?: () => Record<string, string>
  fetchMe?: () => Promise<unknown>
  handleSessionExpired?: () => void
  showToast?: (message: string, type?: 'info' | 'success' | 'warning' | 'error') => void
}

export function useSettingsSecurity(options: UseSettingsSecurityOptions = {}) {
  const user = options.user ?? ref<any>(null)
  const authHeaders = options.authHeaders ?? (() => ({}))
  const fetchMe = options.fetchMe ?? (() => Promise.resolve())
  const handleSessionExpired = options.handleSessionExpired ?? (() => {})
  const showToast = options.showToast ?? (() => {})

  // Guard security-tab action buttons against double-submit while an async op runs.
  const securityBusy = ref(false)
  async function withBusy(fn: () => unknown) {
    if (securityBusy.value) return
    securityBusy.value = true
    try {
      await fn()
    } finally {
      securityBusy.value = false
    }
  }

  // ── Password Management ──
  const currentPw = ref('')
  const newPw = ref('')
  const confirmPw = ref('')
  const savingPw = ref(false)

  const pwStrength = computed(() => {
    const pw = newPw.value
    if (!pw) return PW_STRENGTH_EMPTY
    if (COMMON_PASSWORDS.has(pw.toLowerCase())) return PW_STRENGTH_COMMON
    let score = 0
    if (pw.length >= 8) score++
    if (pw.length >= 12) score++
    if (pw.length >= 16) score++
    if (RE_LOWER.test(pw) && RE_UPPER.test(pw)) score++
    if (RE_DIGIT.test(pw)) score++
    if (RE_NON_ALNUM.test(pw)) score++
    const level = score <= 2 ? 1 : score <= 3 ? 2 : score <= 4 ? 3 : 4
    return PW_STRENGTH_BY_LEVEL[level]!
  })

  const hasPassword = computed(() => user.value?.has_password === true)
  const hasPasswordKnown = computed(() => typeof user.value?.has_password === 'boolean')

  async function savePassword() {
    if (savingPw.value) return
    if (hasPassword.value && !currentPw.value) {
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
    } finally {
      savingPw.value = false
    }
  }

  // ── Sessions ──
  const sessions = ref<any[]>([])
  const sessionsLoading = ref(true)
  const hiddenSystemSessions = ref(0)
  let sessionsAbort: AbortController | null = null
  const revokingSessionIds = new Set<string>()

  async function loadSessions() {
    sessionsAbort?.abort()
    const controller = new AbortController()
    sessionsAbort = controller
    sessionsLoading.value = true
    try {
      const res = await $fetch<{ sessions: any[]; hidden_internal_count?: number }>('/auth/sessions', {
        headers: authHeaders(),
        signal: controller.signal,
      })
      if (sessionsAbort !== controller) return
      const visible: any[] = []
      let hidden = Number(res.hidden_internal_count || 0)
      for (const session of res.sessions || []) {
        if (!session.is_current && isInternalUA(session.user_agent)) hidden += 1
        else visible.push(session)
      }
      sessions.value = visible
      hiddenSystemSessions.value = hidden
    } catch (e: unknown) {
      if (isAbortError(e)) return
    } finally {
      if (sessionsAbort === controller) {
        sessionsLoading.value = false
        sessionsAbort = null
      }
    }
  }

  async function revokeSession(id: string) {
    if (!id || revokingSessionIds.has(id)) return
    revokingSessionIds.add(id)
    try {
      await $fetch(`/auth/sessions/${encodeURIComponent(id)}`, { method: 'DELETE', headers: authHeaders() })
      sessions.value = sessions.value.filter(s => s.id !== id)
      showToast('Đã thu hồi phiên', 'success')
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể thu hồi phiên', 'error')
    } finally {
      revokingSessionIds.delete(id)
    }
  }

  // ── Login History ──
  const loginHistory = ref<any[]>([])
  const loginHistoryLoading = ref(true)
  let loginHistoryAbort: AbortController | null = null

  async function loadLoginHistory() {
    loginHistoryAbort?.abort()
    const controller = new AbortController()
    loginHistoryAbort = controller
    loginHistoryLoading.value = true
    try {
      const res = await $fetch<{ history: any[] }>('/auth/login-history', {
        headers: authHeaders(),
        signal: controller.signal,
      })
      if (loginHistoryAbort !== controller) return
      loginHistory.value = res.history || []
    } catch (e: unknown) {
      if (isAbortError(e)) return
    } finally {
      if (loginHistoryAbort === controller) {
        loginHistoryLoading.value = false
        loginHistoryAbort = null
      }
    }
  }

  // ── 2FA ──
  const twoFA = ref<{ enabled: boolean; recovery_remaining: number }>({ enabled: false, recovery_remaining: 0 })
  const twoFALoading = ref(true)
  const setupData = ref<{ secret: string; otpauth_uri: string; qr: string } | null>(null)
  const setupCode = ref('')
  const recoveryCodes = ref<string[]>([])
  const disableCode = ref('')
  const trustedDevices = ref<any[]>([])
  let twoFAAbort: AbortController | null = null
  let trustedDevicesAbort: AbortController | null = null
  const removingDeviceIds = new Set<string>()

  async function load2FAStatus() {
    twoFAAbort?.abort()
    const controller = new AbortController()
    twoFAAbort = controller
    twoFALoading.value = true
    try {
      const res = await $fetch<{ enabled: boolean; recovery_remaining: number }>('/auth/2fa/status', {
        headers: authHeaders(),
        signal: controller.signal,
      })
      if (twoFAAbort !== controller) return
      twoFA.value = res
    } catch (e: unknown) {
      if (isAbortError(e)) return
    } finally {
      if (twoFAAbort === controller) {
        twoFALoading.value = false
        twoFAAbort = null
      }
    }
  }

  async function begin2FASetup() {
    try {
      setupData.value = await $fetch<{ secret: string; otpauth_uri: string; qr: string }>('/auth/2fa/setup', { method: 'POST', headers: authHeaders() })
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast(extractErrorMessage(e, 'Không thể bắt đầu thiết lập'), 'error')
    }
  }

  async function confirm2FASetup() {
    try {
      const res = await $fetch<{ recovery_codes: string[] }>('/auth/2fa/verify-setup', { method: 'POST', headers: authHeaders(), body: { code: setupCode.value } })
      recoveryCodes.value = res.recovery_codes || []
      setupData.value = null
      setupCode.value = ''
      showToast('Đã bật xác thực 2 bước', 'success')
      await load2FAStatus()
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast(extractErrorMessage(e, 'Mã không đúng'), 'error')
    }
  }

  async function disable2FA() {
    try {
      await $fetch('/auth/2fa/disable', { method: 'POST', headers: authHeaders(), body: { code: disableCode.value } })
      disableCode.value = ''
      recoveryCodes.value = []
      showToast('Đã tắt xác thực 2 bước', 'success')
      await Promise.all([load2FAStatus(), loadTrustedDevices()])
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast(extractErrorMessage(e, 'Mã không đúng'), 'error')
    }
  }

  async function loadTrustedDevices() {
    trustedDevicesAbort?.abort()
    const controller = new AbortController()
    trustedDevicesAbort = controller
    try {
      const r = await $fetch<{ devices: any[] }>('/auth/trusted-devices', {
        headers: authHeaders(),
        signal: controller.signal,
      })
      if (trustedDevicesAbort !== controller) return
      trustedDevices.value = r.devices || []
    } catch (e: unknown) {
      if (isAbortError(e)) return
    } finally {
      if (trustedDevicesAbort === controller) {
        trustedDevicesAbort = null
      }
    }
  }

  async function removeTrustedDevice(id: string) {
    if (!id || removingDeviceIds.has(id)) return
    removingDeviceIds.add(id)
    try {
      await $fetch(`/auth/trusted-devices/${encodeURIComponent(id)}`, { method: 'DELETE', headers: authHeaders() })
      trustedDevices.value = trustedDevices.value.filter(d => d.id !== id)
      showToast('Đã xoá thiết bị', 'success')
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể xoá thiết bị', 'error')
    } finally {
      removingDeviceIds.delete(id)
    }
  }

  function copyRecoveryCodes() {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(recoveryCodes.value.join('\n'))
        .then(() => showToast('Đã sao chép mã khôi phục', 'success'))
        .catch(() => showToast('Không thể sao chép', 'error'))
    }
  }

  function downloadRecoveryCodes() {
    if (typeof document === 'undefined') return
    const blob = new Blob([recoveryCodes.value.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'vinhlong360-recovery-codes.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  return {
    securityBusy,
    withBusy,
    currentPw,
    newPw,
    confirmPw,
    savingPw,
    pwStrength,
    hasPassword,
    hasPasswordKnown,
    savePassword,
    sessions,
    sessionsLoading,
    hiddenSystemSessions,
    loadSessions,
    revokeSession,
    loginHistory,
    loginHistoryLoading,
    loadLoginHistory,
    twoFA,
    twoFALoading,
    setupData,
    setupCode,
    recoveryCodes,
    disableCode,
    trustedDevices,
    load2FAStatus,
    begin2FASetup,
    confirm2FASetup,
    disable2FA,
    loadTrustedDevices,
    removeTrustedDevice,
    copyRecoveryCodes,
    downloadRecoveryCodes,
    isInternalUA,
    shortUA,
  }
}
