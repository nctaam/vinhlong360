<template>
  <Teleport to="body">
    <Transition name="jb-slide">
      <div v-if="count > 0" class="journey-bar">
        <NuxtLink to="/lich-trinh" class="jb-summary">
          <svg class="jb-heart" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" fill="var(--save-red)" stroke="var(--save-red)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <strong :class="{ 'jb-count-pop': countPop }">{{ count }}</strong> đã lưu
        </NuxtLink>
        <div class="jb-actions">
          <NuxtLink to="/lich-trinh" class="btn btn-sm btn-ghost jb-link">Xem tất cả</NuxtLink>
          <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-sm btn-primary jb-link">Tạo lịch trình</NuxtLink>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
const { count } = useFavorites()
const countPop = ref(false)
const prevCount = ref(count.value)
let popTimer: ReturnType<typeof setTimeout> | null = null

watch(count, (n) => {
  if (n > prevCount.value) {
    if (popTimer) clearTimeout(popTimer)
    countPop.value = true
    popTimer = setTimeout(() => { countPop.value = false }, 400)
  }
  prevCount.value = n
})

onUnmounted(() => { if (popTimer) clearTimeout(popTimer) })
</script>

<style scoped>
.journey-bar {
  position: fixed; bottom: 0; left: 0; right: 0; z-index: 900;
  display: flex; align-items: center; justify-content: space-between; gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  background: var(--card); border-top: .5px solid var(--line);
  box-shadow: 0 -4px 20px rgba(0,0,0,.08);
}
.jb-summary {
  display: flex; align-items: center; gap: var(--space-2);
  font-size: var(--text-sm); font-weight: var(--weight-medium);
  color: var(--ink); text-decoration: none;
}
.jb-summary:hover { color: var(--primary-fg); }
.jb-heart { width: 20px; height: 20px; flex-shrink: 0; }
.jb-actions { display: flex; gap: var(--space-2); }

.jb-count-pop { animation: jbPop .4s var(--ease-spring-gentle); }
@keyframes jbPop { 0% { transform: scale(1); } 30% { transform: scale(1.3); } 100% { transform: scale(1); } }

.jb-slide-enter-active { transition: transform .35s var(--ease-spring-gentle), opacity .25s var(--ease-out); }
.jb-slide-leave-active { transition: transform .2s var(--ease-out), opacity .15s var(--ease-out); }
.jb-slide-enter-from { transform: translateY(100%); opacity: 0; }
.jb-slide-leave-to { transform: translateY(100%); opacity: 0; }

.dark .journey-bar { background: var(--card); box-shadow: 0 -4px 20px rgba(0,0,0,.25); }

@media (max-width: 480px) {
  .journey-bar { flex-wrap: wrap; padding: var(--space-2) var(--space-3); gap: var(--space-2); }
  .jb-actions { width: 100%; }
  .jb-actions .jb-link { flex: 1; justify-content: center; min-height: 44px; }
}

@media (prefers-reduced-motion: reduce) {
  .jb-count-pop { animation: none; }
  .jb-slide-enter-active, .jb-slide-leave-active { transition: none; }
}
</style>
