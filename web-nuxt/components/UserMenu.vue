<template>
  <div class="dropdown">
    <button type="button" ref="triggerRef" class="auth-user" @click="toggle" aria-haspopup="menu" :aria-expanded="open">
      <span class="avatar avatar-sm">{{ initial }}</span>
      <span class="auth-user-name">{{ displayName }}</span>
    </button>
    <Transition name="menu-pop">
    <div v-if="open" ref="menuRef" class="dropdown-menu show menu-editorial" role="menu" @keydown="onMenuKeydown">
      <span class="menu-eyebrow">Sổ tay của bạn</span>
      <NuxtLink to="/tai-khoan" class="dropdown-item" role="menuitem" @click="open = false">
        <IconLine name="user" class="menu-icon" /> Tài khoản
      </NuxtLink>
      <NuxtLink v-if="user" :to="userPath(user.username || user.id)" class="dropdown-item" role="menuitem" @click="open = false">
        <IconLine name="user" class="menu-icon" /> Trang cá nhân
      </NuxtLink>
      <NuxtLink to="/thong-bao" class="dropdown-item" role="menuitem" @click="open = false">
        <IconLine name="bell" class="menu-icon" /> Thông báo
        <span v-if="unreadCount" class="menu-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
      </NuxtLink>
      <NuxtLink to="/da-luu" class="dropdown-item" role="menuitem" @click="open = false">
        <IconLine name="bookmark" class="menu-icon" /> Đã lưu
      </NuxtLink>
      <NuxtLink to="/cai-dat" class="dropdown-item" role="menuitem" @click="open = false">
        <IconLine name="sliders" class="menu-icon" /> Cài đặt
      </NuxtLink>
      <span class="menu-rule" aria-hidden="true"></span>
      <button type="button" class="dropdown-item" role="menuitem" @click="doLogout"><IconLine name="logout" class="menu-icon" /> Đăng xuất</button>
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
  color: var(--white);
  font-size: .7rem;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--radius-full, 9999px);
  margin-left: auto;
  line-height: 1.3;
}
/* ── Editorial reskin — masthead eyebrow + quiet icon rail + tri-province rule ── */
.menu-editorial { padding-top: var(--space-1); }
.menu-eyebrow {
  display: block;
  padding: var(--space-2) 14px var(--space-1);
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase; color: var(--muted);
}
/* emoji restrained into a quiet fixed-width rail, not "loose emoji next to text" */
.menu-icon { display: inline-flex; width: 1.25em; justify-content: center; opacity: .85; }
.menu-rule {
  display: block; height: 2px; border-radius: 2px;
  margin: var(--space-1) 14px;
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .menu-rule { background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }
</style>
