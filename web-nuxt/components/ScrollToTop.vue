<template>
  <Transition name="fade">
    <button type="button" v-show="visible" class="scroll-top" aria-label="Lên đầu trang" @click="scrollUp">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M18 15l-6-6-6 6"/>
      </svg>
    </button>
  </Transition>
</template>

<script setup lang="ts">
const visible = ref(false)

function onScroll() {
  visible.value = window.scrollY > 400
}

function scrollUp() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
  setTimeout(() => {
    document.getElementById('main-content')?.focus({ preventScroll: true })
  }, 500)
}

onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped>
.scroll-top {
  position: fixed;
  bottom: calc(90px + env(safe-area-inset-bottom));
  right: var(--space-5);
  z-index: var(--z-floating);
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: .5px solid var(--line);
  background: var(--glass-bg-heavy);
  backdrop-filter: var(--glass);
  -webkit-backdrop-filter: var(--glass);
  box-shadow: var(--shadow-sm);
  color: var(--primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo);
}
.scroll-top:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.scroll-top:active { transform: scale(.9); transition-duration: .08s; }
.scroll-top:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.fade-enter-active, .fade-leave-active { transition: opacity .3s var(--ease-out-expo), transform .3s var(--ease-spring-gentle); }
.fade-enter-from { opacity: 0; transform: translateY(8px) scale(.9); }
.fade-leave-to { opacity: 0; transform: translateY(4px) scale(.95); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .scroll-top:hover { transform: none; }
  .scroll-top:active { transform: none; }
  .fade-enter-active, .fade-leave-active { transition: opacity .15s; }
  .fade-enter-from, .fade-leave-to { transform: none; }
}
@media (forced-colors: active) {
  .scroll-top { border: 1px solid ButtonText; background: Canvas; }
}
</style>
