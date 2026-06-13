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
      <button class="dropdown-item danger" @click="doLogout">🚪 Đăng xuất</button>
    </div>
  </div>
</template>

<script setup lang="ts">
const { user, logout } = useAuth()
const open = ref(false)

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
