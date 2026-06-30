<template>
  <div class="dropdown">
    <button type="button" ref="triggerRef" class="auth-user" @click="toggle" aria-haspopup="menu" :aria-expanded="open">
      <span class="avatar avatar-sm">{{ initial }}</span>
      <span class="auth-user-name">{{ displayName }}</span>
    </button>
    <Transition name="menu-pop">
    <div v-if="open" ref="menuRef" class="dropdown-menu show" role="menu" @keydown="onMenuKeydown">
      <NuxtLink to="/tai-khoan" class="dropdown-item" role="menuitem" @click="open = false">
        📊 Tài khoản
      </NuxtLink>
      <NuxtLink v-if="user" :to="`/nguoi-dung/${user.username || user.id}`" class="dropdown-item" role="menuitem" @click="open = false">
        👤 Trang cá nhân
      </NuxtLink>
      <NuxtLink to="/thong-bao" class="dropdown-item" role="menuitem" @click="open = false">
        🔔 Thông báo
        <span v-if="unreadCount" class="menu-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
      </NuxtLink>
      <NuxtLink to="/da-luu" class="dropdown-item" role="menuitem" @click="open = false">
        💾 Đã lưu
      </NuxtLink>
      <NuxtLink to="/cai-dat" class="dropdown-item" role="menuitem" @click="open = false">
        ⚙️ Cài đặt
      </NuxtLink>
      <div class="dropdown-divider"></div>
      <button type="button" class="dropdown-item" role="menuitem" @click="doLogout">🚪 Đăng xuất</button>
    </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
const { user, logout, authHeaders } = useAuth()
const { show: showToast } = useToast()
const { unreadCount } = useNotifications()
const open = ref(false)
const triggerRef = ref<HTMLButtonElement>()
const menuRef = ref<HTMLElement>()
const { onMenuKeydown } = useDropdown(open, '.dropdown', { triggerRef })

function toggle() {
  open.value = !open.value
  if (open.value) nextTick(() => menuRef.value?.querySelector<HTMLElement>('[role="menuitem"]')?.focus())
}

const displayName = computed(() => user.value?.display_name || user.value?.phone || '')
const initial = computed(() => {
  const name = displayName.value
  return name ? name.charAt(0).toUpperCase() : '?'
})

async function doLogout() {
  open.value = false
  await logout()
}

</script>

<style scoped>
.menu-badge {
  background: var(--error, #e53e3e);
  color: #fff;
  font-size: .7rem;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--radius-full, 9999px);
  margin-left: auto;
  line-height: 1.3;
}
</style>
