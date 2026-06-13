<template>
  <div class="notif-bell" v-if="isLoggedIn">
    <button class="notif-trigger" @click="open = !open" aria-label="Thông báo">
      🔔
      <span v-if="unreadCount > 0" class="notif-badge">{{ unreadCount > 9 ? '9+' : unreadCount }}</span>
    </button>

    <div v-if="open" class="notif-dropdown">
      <div class="notif-header">
        <strong>Thông báo</strong>
        <button v-if="unreadCount > 0" class="notif-mark-read" @click="doMarkRead">Đọc tất cả</button>
      </div>
      <div class="notif-list">
        <button
          v-for="n in notifications"
          :key="n.id"
          :class="['notif-item', { unread: !n.is_read }]"
          @click="goToNotif(n)"
        >
          <div class="notif-item-title">{{ n.title }}</div>
          <div v-if="n.body" class="notif-item-body">{{ n.body }}</div>
          <div class="notif-item-time">{{ timeAgo(n.created_at) }}</div>
        </button>
        <p v-if="!notifications.length" class="notif-empty">Chưa có thông báo.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const { isLoggedIn } = useAuth()
const { notifications, unreadCount, markAllRead, startPolling, stopPolling } = useNotifications()

const open = ref(false)

function doMarkRead() {
  markAllRead()
}

function goToNotif(n: any) {
  open.value = false
  if (n.ref_type === 'post' && n.ref_id) navigateTo(`/bai-viet/${n.ref_id}`)
  else if (n.ref_type === 'entity' && n.ref_id) navigateTo(`/dia-diem/${n.ref_id}`)
}

function timeAgo(dateStr: string): string {
  if (!dateStr) return ''
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
  if (diff < 60) return 'Vừa xong'
  if (diff < 3600) return `${Math.floor(diff / 60)}ph trước`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h trước`
  return `${Math.floor(diff / 86400)}d trước`
}

onMounted(() => startPolling())
onUnmounted(() => stopPolling())
</script>
