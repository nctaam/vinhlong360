<template>
  <div class="notif-bell" v-if="isLoggedIn">
    <button type="button" ref="triggerRef" class="notif-trigger" @click="toggle" :aria-label="unreadCount > 0 ? `${unreadCount} thông báo chưa đọc` : 'Thông báo'" :aria-expanded="open">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
      <span v-if="unreadCount > 0" class="notif-badge">{{ unreadCount > 9 ? '9+' : unreadCount }}</span>
    </button>

    <Transition name="notif-drop">
      <div v-if="open" class="notif-dropdown" role="region" aria-label="Thông báo" @keydown="onDropdownKeydown">
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
            <span class="notif-loading-text">Đang tải thông báo…</span>
          </div>
          <div v-else-if="fetchError && !notifications.length" class="notif-error" role="alert">
            <span class="notif-error-icon" aria-hidden="true">⚠️</span>
            <p>Không thể tải thông báo</p>
            <button type="button" class="notif-retry" :disabled="retrying" @click="retryFetch">{{ retrying ? 'Đang thử…' : 'Thử lại' }}</button>
          </div>
          <div v-else-if="!notifications.length" class="notif-empty">
            <span class="notif-empty-icon" aria-hidden="true">🔔</span>
            <p>Chưa có thông báo</p>
          </div>
        </div>
        <NuxtLink to="/thong-bao" class="notif-see-all" aria-label="Xem tất cả thông báo" @click="open = false">Xem tất cả</NuxtLink>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import type { Notification } from '~/types'
const { isLoggedIn } = useAuth()
const { notifications, unreadCount, loading, fetchError, fetchNotifications, markAllRead, markRead, startPolling, stopPolling } = useNotifications()

const open = ref(false)
const retrying = ref(false)
const triggerRef = ref<HTMLButtonElement>()
const { onMenuKeydown: onDropdownKeydown } = useDropdown(open, '.notif-bell', { itemSelector: '.notif-item', triggerRef })

function toggle() {
  open.value = !open.value
}

async function retryFetch() {
  retrying.value = true
  await fetchNotifications()
  setTimeout(() => { retrying.value = false }, 3000)
}

function doMarkRead() {
  markAllRead()
}

function notifIcon(n: Notification): string {
  if (n.type === 'like') return '❤️'
  if (n.type === 'comment') return '💬'
  if (n.type === 'follow') return '👤'
  if (n.type === 'mention') return '📣'
  if (n.type === 'repost') return '🔁'
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

onMounted(() => startPolling())
onUnmounted(() => stopPolling())
</script>

<style scoped>
.notif-see-all { display: block; text-align: center; padding: var(--space-3); border-top: .5px solid var(--line); font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--primary-fg); text-decoration: none; }
.notif-see-all:hover { background: var(--bg-alt); }
.notif-error { text-align: center; padding: var(--space-5); color: var(--muted); font-size: .88rem; display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.notif-error-icon { font-size: 1.5rem; }
.notif-error p { margin: 0; }
.notif-retry {
  min-height: 44px; padding: var(--space-2) var(--space-4);
  border: .5px solid var(--line); border-radius: var(--radius-full);
  background: var(--card); color: var(--ink); cursor: pointer;
  font-size: var(--text-sm); font-weight: var(--weight-semibold);
  transition: background .25s var(--ease-out), transform .25s var(--ease-spring-gentle), border-color .25s var(--ease-out);
}
.notif-retry:hover { background: var(--bg-alt); border-color: var(--ink); }
.notif-retry:active { transform: scale(.96); transition-duration: .08s; }
.notif-retry:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.notif-loading-text { font-size: var(--text-xs); color: var(--muted); margin-top: var(--space-1); }
/* dark overrides for .notif-retry in dark-overrides.css */
@media (max-width: 600px) {
  .notif-dropdown { max-height: 60vh; }
  .notif-list { max-height: calc(60vh - 80px); overflow-y: auto; }
}
@media (prefers-reduced-motion: reduce) {
  .notif-retry { transition: none; }
  .notif-retry:active { transform: none; }
}
@media (forced-colors: active) {
  .notif-retry { border: 1px solid ButtonText; background: Canvas; }
  .notif-see-all { border-top: 1px solid CanvasText; }
}
</style>
