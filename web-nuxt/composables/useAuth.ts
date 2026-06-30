import type { User } from '~/types'

export type { User }

export function useAuth() {
  const user = useState<User | null>('auth-user', () => null)
  const loading = useState('auth-loading', () => false)
  const token = useCookie('vl360_token', { maxAge: 60 * 60 * 24 * 30, secure: true, sameSite: 'lax' })
  const csrfToken = useState<string | null>('auth-csrf-token', () => null)
  const isLoggedIn = computed(() => !!user.value)

  async function fetchCsrf() {
    const currentToken = token.value
    if (!currentToken) {
      csrfToken.value = null
      return null
    }
    if (csrfToken.value) return csrfToken.value
    try {
      const url = import.meta.server
        ? `${useRuntimeConfig().public.apiBase}/auth/csrf`
        : '/auth/csrf'
      const res = await $fetch<{ csrf_token?: string }>(url, {
        headers: { Authorization: `Bearer ${currentToken}` },
      })
      csrfToken.value = res.csrf_token || null
      return csrfToken.value
    } catch (e: unknown) {
      csrfToken.value = null
      if (getStatusCode(e) === 401) {
        token.value = null
        user.value = null
      }
      return null
    }
  }

  async function fetchMe() {
    if (!token.value) {
      user.value = null
      csrfToken.value = null
      return
    }
    try {
      // SSR: wildcard proxy rule '/auth/**' doesn't resolve for internal $fetch
      // (same known issue as /api/**) — use absolute backend URL during SSR
      const url = import.meta.server
        ? `${useRuntimeConfig().public.apiBase}/auth/me`
        : '/auth/me'
      const res = await $fetch<{ user: User }>(url, {
        headers: { Authorization: `Bearer ${token.value}` },
      })
      user.value = res.user
      await fetchCsrf()
    } catch (e: unknown) {
      user.value = null
      csrfToken.value = null
      if (getStatusCode(e) === 401) {
        token.value = null
      }
    }
  }

  async function requestOtp(phone: string) {
    return await $fetch<{ success: boolean; message?: string }>('/auth/request-otp', {
      method: 'POST',
      body: { phone },
    })
  }

  async function verifyOtp(phone: string, code: string, consent?: boolean, registration?: {
    full_name?: string; username?: string; password?: string; date_of_birth?: string
  }) {
    const res = await $fetch<{ token?: string; user?: User; has_password?: boolean; error?: string }>('/auth/verify-otp', {
      method: 'POST',
      body: { phone, code, consent: consent ?? false, ...registration },
    })
    if (res.token) {
      token.value = res.token
      user.value = res.user || null
      if (!user.value || typeof user.value.has_password !== 'boolean') await fetchMe()
      else await fetchCsrf()
    }
    return res
  }

  async function checkPhone(phone: string) {
    return await $fetch<{ exists: boolean }>('/auth/check-phone', {
      method: 'POST',
      body: { phone },
    })
  }

  async function login(phone: string, password: string) {
    const res = await $fetch<{ token?: string; user?: User; error?: string }>('/auth/login', {
      method: 'POST',
      body: { phone, password },
    })
    if (res.token) {
      token.value = res.token
      user.value = res.user || null
      if (!user.value || typeof user.value.has_password !== 'boolean') await fetchMe()
      else await fetchCsrf()
    }
    return res
  }

  async function setPassword(password: string) {
    return await $fetch<{ success: boolean }>('/auth/set-password', {
      method: 'POST',
      headers: authHeaders(),
      body: { password },
    })
  }

  async function logout() {
    try {
      await fetchCsrf()
      await $fetch('/auth/logout', {
        method: 'POST',
        headers: authHeaders(),
      })
    } catch { /* ignore */ }
    token.value = null
    user.value = null
    csrfToken.value = null
  }

  function authHeaders(): Record<string, string> {
    const headers: Record<string, string> = {}
    if (token.value) headers.Authorization = `Bearer ${token.value}`
    if (csrfToken.value) {
      headers['X-CSRF-Token'] = csrfToken.value
    }
    return headers
  }

  let sessionExpiredFired = false
  function handleSessionExpired() {
    if (!token.value && !sessionExpiredFired) return
    if (sessionExpiredFired) return
    sessionExpiredFired = true
    token.value = null
    user.value = null
    csrfToken.value = null
    const { show } = useToast()
    show('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'warning', 5000)
    const { openAuth } = useAuthModal()
    openAuth()
    setTimeout(() => { sessionExpiredFired = false }, 2000)
  }

  async function authFetch<T>(url: string, opts: Parameters<typeof $fetch>[1] = {}): Promise<T> {
    try {
      return await $fetch<T>(url, {
        ...opts,
        headers: { ...authHeaders(), ...(opts.headers as Record<string, string> || {}) },
      })
    } catch (e: unknown) {
      if (getStatusCode(e) === 401 && token.value) {
        handleSessionExpired()
      }
      throw e
    }
  }

  return { user, isLoggedIn, loading, token, fetchMe, fetchCsrf, requestOtp, verifyOtp, checkPhone, login, setPassword, logout, authHeaders, authFetch, handleSessionExpired }
}
