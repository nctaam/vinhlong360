let pollTimer: ReturnType<typeof setInterval> | null = null

export function useNotifications() {
  const notifications = useState<any[]>('notifications', () => [])
  const unreadCount = useState('unread-count', () => 0)
  const { isLoggedIn, authHeaders } = useAuth()

  async function fetchNotifications() {
    if (!isLoggedIn.value) return
    try {
      const res = await $fetch<any>('/api/notifications?limit=20', { headers: authHeaders() })
      notifications.value = res.notifications || []
      unreadCount.value = res.unread_count || 0
    } catch { /* ignore */ }
  }

  async function markAllRead() {
    if (!isLoggedIn.value) return
    try {
      await $fetch('/api/notifications/read-all', { method: 'POST', headers: authHeaders() })
      unreadCount.value = 0
      notifications.value.forEach(n => n.is_read = true)
    } catch { /* ignore */ }
  }

  function startPolling() {
    stopPolling()
    fetchNotifications()
    pollTimer = setInterval(fetchNotifications, 30_000)
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  }

  return { notifications, unreadCount, fetchNotifications, markAllRead, startPolling, stopPolling }
}
