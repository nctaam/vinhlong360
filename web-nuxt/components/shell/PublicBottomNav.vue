<template>
  <nav class="public-bottom-nav" aria-label="Điều hướng nhanh">
    <NuxtLink
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="public-bottom-nav-item"
      :class="{ active: isActive(item.to) }"
      :aria-current="isActive(item.to) ? 'page' : undefined"
    >
      <IconLine :name="item.icon" aria-hidden="true" />
      <span>{{ item.label }}</span>
    </NuxtLink>
  </nav>
</template>

<script setup lang="ts">
const route = useRoute()

const items = [
  { to: '/', label: 'Trang chủ', icon: 'home' },
  { to: '/du-lich', label: 'Khám phá', icon: 'compass' },
  { to: '/ban-do', label: 'Gần bạn', icon: 'locate' },
  { to: '/cong-dong', label: 'Cộng đồng', icon: 'message' },
  { to: '/tai-khoan', label: 'Cá nhân', icon: 'user' },
] as const

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(`${path}/`)
}
</script>
