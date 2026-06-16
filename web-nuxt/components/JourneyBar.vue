<template>
  <Teleport to="body">
    <div v-if="count > 0" class="journey-bar">
      <NuxtLink to="/hanh-trinh" class="jb-summary">
        <svg class="jb-heart" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" fill="#dc2626" stroke="#dc2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
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
