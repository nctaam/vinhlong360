let pollTimer: ReturnType<typeof setInterval> | null = null

export function useNotifications() {
  const notifications = useState<any[]>('notifications', () => [])
  const unreadCount = useState('unread-count', () => 0)
  const loading = useState('notif-loading', () => true)
  const fetchError = useState('notif-fetch-error', () => false)
  const { isLoggedIn, authHeaders } = useAuth()

  async function fetchNotifications() {
    if (!isLoggedIn.value) return
    try {
      const res = await $fetch<{ notifications: Notification[]; unread_count?: number }>('/api/notifications?limit=20', { headers: authHeaders() })
      notifications.value = res.notifications || []
      unreadCount.value = res.unread_count || 0
      fetchError.value = false
    } catch { fetchError.value = true } finally { loading.value = false }
  }

  async function markAllRead() {
    if (!isLoggedIn.value) return
    try {
      await $fetch('/api/notifications/read-all', { method: 'POST', headers: authHeaders() })
      unreadCount.value = 0
      notifications.value.forEach(n => n.is_read = true)
    } catch { /* ignore */ }
  }

  async function markRead(id: string) {
    if (!isLoggedIn.value) return
    const n = notifications.value.find(x => x.id === id)
    if (!n || n.is_read) return
    // Optimistic — update UI immediately, fire request in background.
    n.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    try {
      await $fetch(`/api/notifications/${id}/read`, { method: 'POST', headers: authHeaders() })
    } catch { /* keep optimistic state; next poll reconciles */ }
  }

  function startPolling() {
    stopPolling()
    fetchNotifications()
    pollTimer = setInterval(fetchNotifications, 30_000)
    if (import.meta.client) {
      document.addEventListener('visibilitychange', _onVisibility)
    }
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
    if (import.meta.client) {
      document.removeEventListener('visibilitychange', _onVisibility)
    }
  }

  function _onVisibility() {
    if (document.hidden) {
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
    } else {
      fetchNotifications()
      pollTimer = setInterval(fetchNotifications, 30_000)
    }
  }

  return { notifications, unreadCount, loading, fetchError, fetchNotifications, markAllRead, markRead, startPolling, stopPolling }
}
