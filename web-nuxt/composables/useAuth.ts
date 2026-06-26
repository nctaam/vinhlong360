export interface User {
  id: string
  phone: string
  display_name: string | null
  avatar_url: string | null
  bio: string
  role: string
  created_at: string
  has_password?: boolean
}

export function useAuth() {
  const user = useState<User | null>('auth-user', () => null)
  const loading = useState('auth-loading', () => false)
  const token = useCookie('vl360_token', { maxAge: 60 * 60 * 24 * 30 })
  const isLoggedIn = computed(() => !!user.value)

  async function fetchMe() {
    if (!token.value) {
      user.value = null
      return
    }
    try {
      const res = await $fetch<{ user: User }>('/auth/me', {
        headers: { Authorization: `Bearer ${token.value}` },
      })
      user.value = res.user
    } catch {
      user.value = null
      token.value = null
    }
  }

  async function requestOtp(phone: string) {
    return await $fetch<{ success: boolean; message?: string }>('/auth/request-otp', {
      method: 'POST',
      body: { phone },
    })
  }

  async function verifyOtp(phone: string, code: string, consent?: boolean) {
    const res = await $fetch<{ token?: string; user?: User; has_password?: boolean; error?: string }>('/auth/verify-otp', {
      method: 'POST',
      body: { phone, code, consent: consent ?? false },
    })
    if (res.token) {
      token.value = res.token
      user.value = res.user || null
      if (!user.value) await fetchMe()
    }
    return res
  }

  async function checkPhone(phone: string) {
    return await $fetch<{ has_password: boolean }>('/auth/check-phone', {
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
      if (!user.value) await fetchMe()
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
      await $fetch('/auth/logout', {
        method: 'POST',
        headers: token.value ? { Authorization: `Bearer ${token.value}` } : {},
      })
    } catch { /* ignore */ }
    token.value = null
    user.value = null
  }

  function authHeaders(): Record<string, string> {
    return token.value ? { Authorization: `Bearer ${token.value}` } : {}
  }

  let sessionExpiredFired = false
  function handleSessionExpired() {
    if (!token.value && !sessionExpiredFired) return
    if (sessionExpiredFired) return
    sessionExpiredFired = true
    token.value = null
    user.value = null
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
    } catch (e: any) {
      if (e?.response?.status === 401 && token.value) {
        handleSessionExpired()
      }
      throw e
    }
  }

  return { user, isLoggedIn, loading, token, fetchMe, requestOtp, verifyOtp, checkPhone, login, setPassword, logout, authHeaders, authFetch, handleSessionExpired }
}
