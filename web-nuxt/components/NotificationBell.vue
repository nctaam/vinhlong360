<template>
  <div class="notif-bell" v-if="isLoggedIn">
    <button type="button" class="notif-trigger" @click="toggle" aria-label="Thông báo" :aria-expanded="open">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
      <span v-if="unreadCount > 0" class="notif-badge">{{ unreadCount > 9 ? '9+' : unreadCount }}</span>
    </button>

    <Transition name="notif-drop">
      <div v-if="open" class="notif-dropdown">
        <div class="notif-header">
          <strong>Thông báo</strong>
          <button type="button" v-if="unreadCount > 0" class="notif-mark-read" @click="doMarkRead">Đọc tất cả</button>
        </div>
        <div class="notif-list">
          <button type="button"
            v-for="n in notifications"
            :key="n.id"
            :class="['notif-item', { unread: !n.is_read }]"
            @click="goToNotif(n)"
          >
            <span class="notif-item-icon" aria-hidden="true">{{ notifIcon(n) }}</span>
            <div class="notif-item-content">
              <div class="notif-item-title">{{ n.title }}</div>
              <div v-if="n.body" class="notif-item-body">{{ n.body }}</div>
              <time class="notif-item-time" :datetime="n.created_at">{{ timeAgo(n.created_at) }}</time>
            </div>
            <span v-if="!n.is_read" class="notif-unread-dot"></span>
          </button>
          <div v-if="loading && !notifications.length" class="notif-loading" role="status" aria-label="Đang tải thông báo">
            <div class="spinner spinner-sm"></div>
          </div>
          <div v-else-if="!notifications.length" class="notif-empty">
            <span class="notif-empty-icon">🔔</span>
            <p>Chưa có thông báo</p>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
const { isLoggedIn } = useAuth()
const { notifications, unreadCount, loading, markAllRead, markRead, startPolling, stopPolling } = useNotifications()

const open = ref(false)

function toggle() {
  open.value = !open.value
}

function doMarkRead() {
  markAllRead()
}

function notifIcon(n: Notification): string {
  if (n.type === 'like') return '❤️'
  if (n.type === 'comment') return '💬'
  if (n.type === 'follow') return '👤'
  return '🔔'
}

function goToNotif(n: Notification) {
  open.value = false
  if (!n.is_read) markRead(n.id)
  if (n.ref_type === 'post' && n.ref_id) navigateTo(`/bai-viet/${n.ref_id}`)
  else if (n.ref_type === 'entity' && n.ref_id) navigateTo(`/dia-diem/${n.ref_id}`)
  else if (n.ref_type === 'user' && n.ref_id) navigateTo(`/nguoi-dung/${n.ref_id}`)
}

const { timeAgo } = useTimeAgo()

function onEsc(e: KeyboardEvent) {
  if (e.key === 'Escape' && open.value) open.value = false
}
function onClickOutside(e: MouseEvent) {
  if (!(e.target as HTMLElement).closest('.notif-bell')) open.value = false
}

onMounted(() => { startPolling(); document.addEventListener('keydown', onEsc); document.addEventListener('click', onClickOutside) })
onUnmounted(() => { stopPolling(); document.removeEventListener('keydown', onEsc); document.removeEventListener('click', onClickOutside) })
</script>
