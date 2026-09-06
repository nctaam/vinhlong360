<template>
  <Teleport to="body">
    <Transition name="confirm-fade">
      <div v-if="state.open" class="confirm-overlay" role="presentation" @click.self="answer(false)">
        <div class="confirm-box" role="alertdialog" aria-modal="true" :aria-label="state.title" aria-describedby="confirm-msg" @keydown.esc="answer(false)" @keydown.tab="trapFocus">
          <h2 class="confirm-title">{{ state.title }}</h2>
          <p id="confirm-msg" class="confirm-message">{{ state.message }}</p>
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
const { state, answer: rawAnswer } = useConfirm()
const cancelBtn = ref<HTMLButtonElement | null>(null)
let previousFocus: HTMLElement | null = null

function answer(val: boolean) {
  rawAnswer(val)
  nextTick(() => { previousFocus?.focus(); previousFocus = null })
}

onUnmounted(() => {
  if (state.value.open) rawAnswer(false)
})

function trapFocus(e: KeyboardEvent) {
  const box = (e.currentTarget as HTMLElement)
  const focusable = Array.from(box.querySelectorAll<HTMLElement>('button:not([disabled]), [tabindex]:not([tabindex="-1"])'))
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (!first || !last) return
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
}

watch(() => state.value.open, async (open) => {
  if (!import.meta.client || !open) return
  previousFocus = document.activeElement as HTMLElement | null
  await nextTick()
  cancelBtn.value?.focus()
})
</script>

<style scoped>
.confirm-overlay {
  position: fixed; inset: 0; z-index: var(--z-modal-high); display: flex; align-items: center; justify-content: center;
  background: rgba(var(--ink-rgb), .45);
  padding: max(var(--space-4), env(safe-area-inset-top, 0px)) max(var(--space-4), env(safe-area-inset-right, 0px)) max(var(--space-4), env(safe-area-inset-bottom, 0px)) max(var(--space-4), env(safe-area-inset-left, 0px));
}
.confirm-box {
  background: var(--bg); color: var(--ink-900); border-radius: var(--radius-sheet);
  border: 1px solid var(--line);
  max-width: 400px; width: 100%; padding: var(--space-6); box-shadow: var(--shadow-lg, 0 10px 40px rgba(var(--ink-rgb),.25));
  transition: transform .25s var(--ease-out-expo);
}
.dark .confirm-box {
  background: var(--card);
  border-color: rgba(var(--white-rgb), .12);
  box-shadow: 0 18px 48px rgba(var(--black-rgb), .6);
}
.confirm-title { margin: 0 0 .5rem; font-size: 1.15rem; font-family: var(--font-editorial, inherit); font-weight: var(--weight-bold, 700); letter-spacing: -.01em; }
.confirm-message { margin: 0 0 1.25rem; color: var(--ink-700); line-height: 1.5; }
.confirm-actions { display: flex; gap: .75rem; justify-content: flex-end; }
.btn-danger { background: var(--danger); color: var(--text-on-dark, var(--white)); }
.confirm-fade-enter-active, .confirm-fade-leave-active { transition: opacity .2s var(--ease-out); }
.confirm-fade-enter-active .confirm-box, .confirm-fade-leave-active .confirm-box { transition: transform .25s var(--ease-out-expo); }
.confirm-fade-enter-from, .confirm-fade-leave-to { opacity: 0; }
.confirm-fade-enter-from .confirm-box, .confirm-fade-leave-to .confirm-box { transform: scale(.96) translateY(6px); }
@media (prefers-reduced-motion: reduce) {
  .confirm-fade-enter-active, .confirm-fade-leave-active { transition: none; }
  .confirm-fade-enter-active .confirm-box, .confirm-fade-leave-active .confirm-box { transition: none; transform: none; }
}
@media (forced-colors: active) {
  .confirm-overlay { background: rgba(var(--black-rgb),.7); }
  .confirm-box { border: 2px solid CanvasText; background: Canvas; }
  .btn-danger { border: 1px solid ButtonText; }
}
</style>
