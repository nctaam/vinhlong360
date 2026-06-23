<template>
  <Teleport to="body">
    <Transition name="confirm-fade">
      <div v-if="state.open" class="confirm-overlay" role="presentation" @click.self="answer(false)">
        <div class="confirm-box" role="alertdialog" aria-modal="true" :aria-label="state.title" @keydown.esc="answer(false)">
          <h2 class="confirm-title">{{ state.title }}</h2>
          <p class="confirm-message">{{ state.message }}</p>
          <div class="confirm-actions">
            <button ref="cancelBtn" type="button" class="btn btn-ghost" @click="answer(false)">{{ state.cancelText }}</button>
            <button type="button" :class="['btn', state.danger ? 'btn-danger' : 'btn-primary']" @click="answer(true)">{{ state.confirmText }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
const { state, answer } = useConfirm()
const cancelBtn = ref<HTMLButtonElement | null>(null)

// Focus nút Hủy khi mở (an toàn — tránh bấm nhầm xác nhận)
watch(() => state.value.open, async (open) => {
  if (open) {
    await nextTick()
    cancelBtn.value?.focus()
  }
})
</script>

<style scoped>
.confirm-overlay {
  position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center;
  background: rgba(0, 0, 0, .45); padding: var(--space-4);
}
.confirm-box {
  background: var(--bg); color: var(--ink-900); border-radius: var(--radius-lg);
  max-width: 400px; width: 100%; padding: 1.5rem; box-shadow: var(--shadow-lg, 0 10px 40px rgba(0,0,0,.25));
}
.confirm-title { margin: 0 0 .5rem; font-size: 1.15rem; }
.confirm-message { margin: 0 0 1.25rem; color: var(--ink-700); line-height: 1.5; }
.confirm-actions { display: flex; gap: .75rem; justify-content: flex-end; }
.btn-danger { background: var(--danger, #c0392b); color: #fff; }
.confirm-fade-enter-active, .confirm-fade-leave-active { transition: opacity .2s var(--ease-out); }
.confirm-fade-enter-from, .confirm-fade-leave-to { opacity: 0; }
@media (prefers-reduced-motion: reduce) { .confirm-fade-enter-active, .confirm-fade-leave-active { transition: none; } }
</style>
