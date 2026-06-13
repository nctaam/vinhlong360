<template>
  <div class="dropdown">
    <button class="auth-user" @click="open = !open" aria-haspopup="true" :aria-expanded="open">
      <span class="avatar avatar-sm">{{ initial }}</span>
      <span class="auth-user-name">{{ displayName }}</span>
    </button>
    <div :class="['dropdown-menu', { show: open }]">
      <NuxtLink v-if="user" :to="`/nguoi-dung/${user.id}`" class="dropdown-item" @click="open = false">
        👤 Trang cá nhân
      </NuxtLink>
      <div class="dropdown-divider"></div>
      <button class="dropdown-item" @click="doLogout">🚪 Đăng xuất</button>
      <button class="dropdown-item danger" @click="doDeleteAccount">🗑️ Xoá tài khoản</button>
    </div>
  </div>
</template>

<script setup lang="ts">
const { user, logout, authHeaders } = useAuth()
const open = ref(false)

async function doDeleteAccount() {
  // GĐ5.5: quyền xoá tài khoản & dữ liệu (PDPL).
  open.value = false
  if (!window.confirm('Xoá vĩnh viễn tài khoản và toàn bộ dữ liệu của bạn? Hành động này không thể hoàn tác.')) return
  try {
    await $fetch('/auth/account', { method: 'DELETE', headers: authHeaders() })
    await logout()
    await navigateTo('/')
  } catch (e) {
    window.alert('Không thể xoá tài khoản lúc này. Vui lòng thử lại hoặc liên hệ.')
  }
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

function onClickOutside(e: MouseEvent) {
  if (!(e.target as HTMLElement).closest('.dropdown')) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>
