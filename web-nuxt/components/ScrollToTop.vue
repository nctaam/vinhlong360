<template>
  <Transition name="fade">
    <button v-show="visible" class="scroll-top" aria-label="Lên đầu trang" @click="scrollUp">
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
}

onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped>
.scroll-top {
  position: fixed;
  bottom: 90px;
  right: var(--space-5);
  z-index: var(--z-dropdown);
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: var(--surface-translucent);
  backdrop-filter: saturate(180%) blur(16px);
  -webkit-backdrop-filter: saturate(180%) blur(16px);
  box-shadow: var(--shadow);
  color: var(--primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--duration-fast) var(--ease-spring), box-shadow var(--duration-fast);
}
.scroll-top:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.scroll-top:active { transform: scale(.92); transition-duration: .08s; }
.scroll-top:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.fade-enter-active, .fade-leave-active { transition: opacity var(--duration-normal) var(--ease-out); }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
