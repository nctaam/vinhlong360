<template>
  <Teleport to="body">
    <div v-if="count > 0" class="journey-bar">
      <NuxtLink to="/hanh-trinh" class="jb-summary">
        <span class="jb-heart">❤️</span>
        <strong>{{ count }}</strong> đã lưu
      </NuxtLink>
      <div class="jb-actions">
        <NuxtLink to="/hanh-trinh" class="btn btn-sm btn-ghost jb-link">Xem tất cả</NuxtLink>
    <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-sm btn-primary jb-link">Tạo lịch trình</NuxtLink>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const { count } = useFavorites()
</script>
