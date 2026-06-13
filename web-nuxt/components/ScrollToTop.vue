<template>
  <Transition name="fade">
    <button v-show="visible" class="scroll-top" aria-label="Lên đầu trang" @click="scrollUp">
      ↑
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
  right: 20px;
  z-index: 30;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: rgba(255,255,255,.95);
  backdrop-filter: blur(6px);
  box-shadow: var(--shadow);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform .15s ease, opacity .2s ease;
}
.scroll-top:hover { transform: translateY(-2px); }
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
