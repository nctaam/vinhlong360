export interface User {
  id: number
  phone: string
  display_name: string | null
  role: string
  created_at: string
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

  async function verifyOtp(phone: string, code: string) {
    const res = await $fetch<{ token?: string; user?: User; error?: string }>('/auth/verify-otp', {
      method: 'POST',
      body: { phone, code },
    })
    if (res.token) {
      token.value = res.token
      user.value = res.user || null
      if (!user.value) await fetchMe()
    }
    return res
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

  return { user, isLoggedIn, loading, token, fetchMe, requestOtp, verifyOtp, logout, authHeaders }
}
