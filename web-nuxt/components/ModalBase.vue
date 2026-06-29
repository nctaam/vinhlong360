<template>
  <Teleport to="body">
    <Transition :name="transitionName">
      <div v-if="open" class="modal-overlay" @click.self="$emit('close')">
        <div
          ref="sheetEl"
          class="modal-sheet"
          :class="[sizeClass]"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
        >
          <button type="button" class="modal-close" aria-label="Đóng" @click="$emit('close')">&times;</button>
          <div v-if="$slots.header" class="modal-header">
            <slot name="header" />
          </div>
          <div class="modal-body">
            <slot />
          </div>
          <div v-if="$slots.footer" class="modal-footer">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  open: boolean
  titleId?: string
  size?: 'sm' | 'md' | 'lg'
  transitionName?: string
}>(), {
  titleId: 'modal-title',
  size: 'md',
  transitionName: 'modal-fade',
})

const emit = defineEmits<{ close: [] }>()

const sheetEl = ref<HTMLElement | null>(null)
const isOpen = computed(() => props.open)

useModalA11y(isOpen, sheetEl, { onClose: () => emit('close') })

const sizeClass = computed(() => `modal-${props.size}`)
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; z-index: var(--z-modal, 1000);
  display: flex; align-items: center; justify-content: center;
  background: rgba(0, 0, 0, .45);
  backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
  padding: var(--space-4);
}
.modal-sheet {
  position: relative;
  background: var(--card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  max-height: 90vh;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.modal-sm { width: min(360px, 100%); }
.modal-md { width: min(480px, 100%); }
.modal-lg { width: min(640px, 100%); }
.modal-close {
  position: absolute; top: var(--space-3); right: var(--space-3);
  width: 44px; height: 44px;
  display: flex; align-items: center; justify-content: center;
  border: none; border-radius: var(--radius-full);
  background: transparent; color: var(--muted);
  font-size: 1.4rem; cursor: pointer;
  transition: background .2s, color .2s;
}
.modal-close:hover { background: var(--bg-alt); color: var(--ink); }
.modal-close:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.modal-header { padding: var(--space-5) var(--space-5) 0; }
.modal-body { padding: var(--space-5); }
.modal-footer { padding: 0 var(--space-5) var(--space-5); display: flex; gap: var(--space-3); justify-content: flex-end; }

.modal-fade-enter-active { transition: opacity .25s var(--ease-out); }
.modal-fade-enter-active .modal-sheet { transition: transform .3s var(--ease-spring-gentle), opacity .25s var(--ease-out); }
.modal-fade-leave-active { transition: opacity .2s var(--ease-out); }
.modal-fade-leave-active .modal-sheet { transition: transform .2s var(--ease-out), opacity .2s var(--ease-out); }
.modal-fade-enter-from { opacity: 0; }
.modal-fade-enter-from .modal-sheet { transform: translateY(12px) scale(.97); opacity: 0; }
.modal-fade-leave-to { opacity: 0; }
.modal-fade-leave-to .modal-sheet { transform: translateY(8px) scale(.98); opacity: 0; }

.dark .modal-sheet { border: .5px solid var(--line); }
@media (prefers-reduced-motion: reduce) {
  .modal-fade-enter-active, .modal-fade-leave-active,
  .modal-fade-enter-active .modal-sheet, .modal-fade-leave-active .modal-sheet { transition: none; }
  .modal-close { transition: none; }
}
@media (forced-colors: active) {
  .modal-sheet { border: 2px solid CanvasText; }
  .modal-close { border: 1px solid ButtonText; }
}
</style>
