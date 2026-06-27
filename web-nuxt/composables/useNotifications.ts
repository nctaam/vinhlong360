import type { Notification } from '~/types'

let pollTimer: ReturnType<typeof setTimeout> | null = null
let eventSource: EventSource | null = null
let pollInterval = 30_000
let sseDebounce: ReturnType<typeof setTimeout> | null = null
let isActive = false

export function useNotifications() {
  const notifications = useState<Notification[]>('notifications', () => [])
  const unreadCount = useState('unread-count', () => 0)
  const loading = useState('notif-loading', () => true)
  const fetchError = useState('notif-fetch-error', () => false)
  const { isLoggedIn, authHeaders } = useAuth()

  async function fetchNotifications() {
    if (!isLoggedIn.value) return
    try {
      const res = await $fetch<{ notifications: Notification[]; unread_count?: number }>('/api/notifications?limit=20', { headers: authHeaders() })
      notifications.value = res.notifications || []
      unreadCount.value = res.unread_count ?? 0
      fetchError.value = false
      pollInterval = 30_000
    } catch {
      fetchError.value = true
      pollInterval = Math.min(pollInterval * 2, 300_000)
    } finally { loading.value = false }
  }

  async function markAllRead() {
    if (!isLoggedIn.value) return
    try {
      await $fetch('/api/notifications/read-all', { method: 'POST', headers: authHeaders() })
      unreadCount.value = 0
      notifications.value.forEach(n => (n as any).is_read = true)
    } catch { /* ignore */ }
  }

  async function markRead(id: string) {
    if (!isLoggedIn.value) return
    const n = notifications.value.find(x => x.id === id)
    if (!n || (n as any).is_read) return
    ;(n as any).is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    try {
      await $fetch(`/api/notifications/${id}/read`, { method: 'POST', headers: authHeaders() })
    } catch { /* keep optimistic state; next poll reconciles */ }
  }

  function _schedulePoll() {
    _clearPollTimer()
    pollTimer = setTimeout(async () => {
      await fetchNotifications()
      if (!eventSource) _schedulePoll()
    }, pollInterval)
  }

  function _clearPollTimer() {
    if (pollTimer) { clearTimeout(pollTimer); pollTimer = null }
  }

  function _connectSSE() {
    if (!import.meta.client || !isLoggedIn.value) return
    _closeSSE()
    const headers = authHeaders()
    const token = (headers as any)?.Authorization?.replace('Bearer ', '')
    if (!token) { _schedulePoll(); return }
    const es = new EventSource(`/api/notifications/stream?token=${encodeURIComponent(token)}`)
    es.onmessage = () => {
      if (sseDebounce) clearTimeout(sseDebounce)
      sseDebounce = setTimeout(() => fetchNotifications(), 2000)
    }
    es.onerror = () => {
      _closeSSE()
      if (!isLoggedIn.value) return
      _schedulePoll()
    }
    eventSource = es
  }

  function _closeSSE() {
    if (sseDebounce) { clearTimeout(sseDebounce); sseDebounce = null }
    if (eventSource) { eventSource.close(); eventSource = null }
  }

  function startPolling() {
    if (isActive) return
    isActive = true
    pollInterval = 30_000
    fetchNotifications()
    _connectSSE()
    if (import.meta.client) {
      document.addEventListener('visibilitychange', _onVisibility)
    }
  }

  function stopPolling() {
    isActive = false
    _clearPollTimer()
    _closeSSE()
    if (import.meta.client) {
      document.removeEventListener('visibilitychange', _onVisibility)
    }
  }

  function _onVisibility() {
    if (document.hidden) {
      _clearPollTimer()
      _closeSSE()
    } else {
      pollInterval = 30_000
      fetchNotifications()
      _connectSSE()
    }
  }

  return { notifications, unreadCount, loading, fetchError, fetchNotifications, markAllRead, markRead, startPolling, stopPolling }
}
