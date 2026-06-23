<template>
  <div class="dropdown">
    <button type="button" ref="triggerRef" class="auth-user" @click="toggle" aria-haspopup="menu" :aria-expanded="open">
      <span class="avatar avatar-sm">{{ initial }}</span>
      <span class="auth-user-name">{{ displayName }}</span>
    </button>
    <Transition name="menu-pop">
    <div v-if="open" ref="menuRef" class="dropdown-menu show" role="menu" @keydown="onMenuKeydown">
      <NuxtLink v-if="user" :to="`/nguoi-dung/${user.id}`" class="dropdown-item" role="menuitem" @click="open = false">
        👤 Trang cá nhân
      </NuxtLink>
      <div class="dropdown-divider"></div>
      <button type="button" class="dropdown-item" role="menuitem" @click="doLogout">🚪 Đăng xuất</button>
      <button type="button" class="dropdown-item danger" role="menuitem" @click="doDeleteAccount">🗑️ Xoá tài khoản</button>
    </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
const { user, logout, authHeaders } = useAuth()
const { confirmDialog } = useConfirm()
const { show: showToast } = useToast()
const open = ref(false)
const triggerRef = ref<HTMLButtonElement>()
const menuRef = ref<HTMLElement>()

function toggle() {
  open.value = !open.value
  if (open.value) nextTick(() => menuRef.value?.querySelector<HTMLElement>('[role="menuitem"]')?.focus())
}

function onMenuKeydown(e: KeyboardEvent) {
  if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
  e.preventDefault()
  const items = menuRef.value ? Array.from(menuRef.value.querySelectorAll<HTMLElement>('[role="menuitem"]')) : []
  if (!items.length) return
  const cur = items.indexOf(document.activeElement as HTMLElement)
  const next = e.key === 'ArrowDown' ? (cur + 1) % items.length : (cur - 1 + items.length) % items.length
  items[next]?.focus()
}

async function doDeleteAccount() {
  // GĐ5.5: quyền xoá tài khoản & dữ liệu (PDPL).
  open.value = false
  if (!await confirmDialog('Xoá vĩnh viễn tài khoản và toàn bộ dữ liệu của bạn? Hành động này không thể hoàn tác.', { danger: true, confirmText: 'Xoá tài khoản', title: 'Xoá tài khoản' })) return
  try {
    await $fetch('/auth/account', { method: 'DELETE', headers: authHeaders() })
    await logout()
    await navigateTo('/')
  } catch (e) {
    showToast('Không thể xoá tài khoản lúc này. Vui lòng thử lại hoặc liên hệ.', 'error')
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
function onEsc(e: KeyboardEvent) {
  if (e.key === 'Escape' && open.value) { open.value = false; triggerRef.value?.focus() }
}

onMounted(() => { document.addEventListener('click', onClickOutside); document.addEventListener('keydown', onEsc) })
onUnmounted(() => { document.removeEventListener('click', onClickOutside); document.removeEventListener('keydown', onEsc) })
</script>
