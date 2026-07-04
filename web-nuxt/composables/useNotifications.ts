import type { Notification } from '~/types'

let pollTimer: ReturnType<typeof setTimeout> | null = null
let eventSource: EventSource | null = null
let pollInterval = 30_000
let sseDebounce: ReturnType<typeof setTimeout> | null = null
let sseReconnectTimer: ReturnType<typeof setTimeout> | null = null
let sseRetryDelay = 1_000
let activeSubscribers = 0
let visibilityListenerAttached = false

export function useNotifications() {
  const notifications = useState<Notification[]>('notifications', () => [])
  const unreadCount = useState('unread-count', () => 0)
  const loading = useState('notif-loading', () => true)
  const fetchError = useState('notif-fetch-error', () => false)
  const { isLoggedIn, authHeaders, handleSessionExpired } = useAuth()

  function resetNotificationState() {
    notifications.value = []
    unreadCount.value = 0
    fetchError.value = false
    loading.value = false
  }

  async function fetchNotifications() {
    if (!isLoggedIn.value) {
      resetNotificationState()
      return
    }
    loading.value = true
    try {
      const params = new URLSearchParams({ limit: '20' })
      const res = await $fetch<{ notifications: Notification[]; unread_count?: number }>(`/api/notifications?${params}`, { headers: authHeaders() })
      notifications.value = res.notifications || []
      unreadCount.value = res.unread_count ?? 0
      fetchError.value = false
      pollInterval = 30_000
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) {
        handleSessionExpired()
        resetNotificationState()
        return
      }
      fetchError.value = true
      pollInterval = Math.min(pollInterval * 2, 300_000)
    } finally { loading.value = false }
  }

  async function markAllRead() {
    if (!isLoggedIn.value) return
    const previous = notifications.value.map(n => ({ n, is_read: (n as any).is_read }))
    const previousUnread = unreadCount.value
    try {
      await $fetch('/api/notifications/read-all', { method: 'POST', headers: authHeaders() })
      unreadCount.value = 0
      notifications.value.forEach(n => (n as any).is_read = true)
    } catch (e: unknown) {
      previous.forEach(p => { (p.n as any).is_read = p.is_read })
      unreadCount.value = previousUnread
      if (getStatusCode(e) === 401) handleSessionExpired()
    }
  }

  async function markRead(id: string) {
    if (!isLoggedIn.value) return
    const n = notifications.value.find(x => x.id === id)
    if (!n || (n as any).is_read) return
    const previousRead = (n as any).is_read
    const previousUnread = unreadCount.value
    ;(n as any).is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    try {
      await $fetch(`/api/notifications/${encodePathId(id)}/read`, { method: 'POST', headers: authHeaders() })
    } catch (e: unknown) {
      ;(n as any).is_read = previousRead
      unreadCount.value = previousUnread
      if (getStatusCode(e) === 401) handleSessionExpired()
    }
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

  function _clearReconnectTimer() {
    if (sseReconnectTimer) { clearTimeout(sseReconnectTimer); sseReconnectTimer = null }
  }

  function _isDocumentHidden() {
    return import.meta.client && typeof document !== 'undefined' && document.hidden
  }

  function _connectSSE() {
    if (!import.meta.client || !isLoggedIn.value || _isDocumentHidden()) return
    if (eventSource && eventSource.readyState !== EventSource.CLOSED) return
    _clearReconnectTimer()
    _closeSSE()
    const es = new EventSource('/api/notifications/stream', { withCredentials: true })
    es.onopen = () => {
      sseRetryDelay = 1_000
      fetchError.value = false
      _clearPollTimer()
    }
    es.onmessage = () => {
      if (sseDebounce) clearTimeout(sseDebounce)
      sseDebounce = setTimeout(() => fetchNotifications(), 2000)
    }
    es.onerror = () => {
      _closeSSE()
      if (!isLoggedIn.value) return
      _schedulePoll()
      _scheduleReconnect()
    }
    eventSource = es
  }

  function _closeSSE() {
    if (sseDebounce) { clearTimeout(sseDebounce); sseDebounce = null }
    if (eventSource) { eventSource.close(); eventSource = null }
  }

  function _scheduleReconnect() {
    if (!import.meta.client || !isLoggedIn.value || activeSubscribers <= 0 || _isDocumentHidden()) return
    _clearReconnectTimer()
    const delay = sseRetryDelay
    sseRetryDelay = Math.min(sseRetryDelay * 2, 30_000)
    sseReconnectTimer = setTimeout(() => _connectSSE(), delay)
  }

  function startPolling() {
    activeSubscribers += 1
    if (activeSubscribers > 1) return
    pollInterval = 30_000
    sseRetryDelay = 1_000
    fetchNotifications()
    _connectSSE()
    if (import.meta.client && !visibilityListenerAttached) {
      document.addEventListener('visibilitychange', _onVisibility)
      visibilityListenerAttached = true
    }
  }

  function stopPolling() {
    activeSubscribers = Math.max(0, activeSubscribers - 1)
    if (activeSubscribers > 0) return
    _clearPollTimer()
    _clearReconnectTimer()
    _closeSSE()
    if (import.meta.client && visibilityListenerAttached) {
      document.removeEventListener('visibilitychange', _onVisibility)
      visibilityListenerAttached = false
    }
  }

  function _onVisibility() {
    if (document.hidden) {
      _clearPollTimer()
      _clearReconnectTimer()
      _closeSSE()
    } else {
      pollInterval = 30_000
      sseRetryDelay = 1_000
      fetchNotifications()
      _connectSSE()
    }
  }

  return { notifications, unreadCount, loading, fetchError, fetchNotifications, markAllRead, markRead, startPolling, stopPolling }
}
