<template>
  <Teleport to="body">
    <div class="toast-container" aria-label="Thông báo" role="region" aria-live="polite">
      <TransitionGroup name="toast">
        <div v-for="t in toasts" :key="t.id" :class="['toast', t.type]" :role="t.type === 'error' || t.type === 'warning' ? 'alert' : 'status'" :aria-live="t.type === 'error' || t.type === 'warning' ? 'assertive' : 'polite'">
          <span class="toast-icon" aria-hidden="true">
            <IconLine :name="iconNameFor(t.type)" />
          </span>
          <span class="toast-msg">{{ t.message }}</span>
          <button type="button" class="toast-dismiss" aria-label="Đóng" @click="dismiss(t.id)">
            <IconLine name="x" aria-hidden="true" />
          </button>
          <span v-if="(t.duration ?? 3000) > 0" class="toast-progress" aria-hidden="true" :style="{ animationDuration: (t.duration ?? 3000) / 1000 + 's' }" />
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const { toasts, dismiss } = useToast()

function onEscDismiss(e: KeyboardEvent) {
  if (e.key === 'Escape' && toasts.value.length) {
    const last = toasts.value[toasts.value.length - 1]
    if (last) dismiss(last.id)
  }
}
onMounted(() => document.addEventListener('keydown', onEscDismiss))
onUnmounted(() => document.removeEventListener('keydown', onEscDismiss))

function iconNameFor(type?: string) {
  if (type === 'success') return 'check'
  if (type === 'error') return 'x'
  if (type === 'warning') return 'alert-triangle'
  return 'info'
}
</script>

<style scoped>
.toast-container {
  position: fixed; top: max(var(--space-4), env(safe-area-inset-top, 0px)); right: max(var(--space-4), env(safe-area-inset-right, 0px)); z-index: var(--z-toast);
  display: flex; flex-direction: column; gap: var(--space-2);
  max-width: 380px; width: calc(100% - var(--space-8));
  pointer-events: none;
}

.toast {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-sheet);
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-lg);
  backdrop-filter: var(--glass);
  -webkit-backdrop-filter: var(--glass);
  pointer-events: auto;
}
.toast.success { --toast-accent: var(--secondary); }
.toast.error { --toast-accent: var(--error); }
.toast.warning { --toast-accent: var(--accent-dark); }
.toast.info { --toast-accent: var(--color-action); }

.toast-icon {
  flex-shrink: 0; width: 24px; height: 24px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--radius-full);
  font-size: var(--text-xs); font-weight: var(--weight-bold);
  animation: toastIconPop .35s var(--ease-out-expo) .1s both;
}
.toast-icon .line-icon {
  font-size: 14px;
}
@keyframes toastIconPop { from { transform: scale(0); opacity: 0; } to { transform: scale(1); opacity: 1; } }
.toast.success .toast-icon { background: rgba(var(--secondary-rgb), .12); color: var(--secondary); }
.toast.error .toast-icon { background: rgba(var(--color-error-rgb), .12); color: var(--error); }
.toast.warning .toast-icon { background: rgba(var(--accent-rgb), .12); color: var(--accent-dark); }
.toast.info .toast-icon { background: rgba(var(--color-action-rgb), .1); color: var(--color-action); }

.toast-msg { flex: 1; font-size: var(--text-sm); font-weight: var(--weight-medium); color: var(--ink); line-height: var(--leading-snug); }

.toast-dismiss {
  flex-shrink: 0; width: 44px; height: 44px; margin: -10px -10px -10px 0;
  display: flex; align-items: center; justify-content: center;
  background: none; border: none; border-radius: var(--radius-full);
  color: var(--muted); cursor: pointer; font-size: var(--text-base);
  transition: background .2s, color .2s;
}
.toast-dismiss .line-icon {
  font-size: 16px;
  transition: transform .2s var(--ease-out-expo);
}
.toast-dismiss:hover { background: var(--bg-alt); color: var(--ink); }
.toast-dismiss:hover .line-icon { transform: scale(1.15); }
.toast-dismiss:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }

.toast-progress {
  position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
  border-radius: 0 0 var(--radius-sheet) var(--radius-sheet);
  background: currentColor; opacity: .2;
  transform-origin: left;
  animation: toastCountdown linear forwards;
}
@keyframes toastCountdown { from { transform: scaleX(1); } to { transform: scaleX(0); } }

.toast { position: relative; overflow: hidden; }

/* ── Transitions ── */
.toast-enter-active { transition: transform .35s var(--ease-out-expo), opacity .25s var(--ease-out); will-change: transform, opacity; }
.toast-leave-active { transition: transform .2s var(--ease-out), opacity .15s var(--ease-out); will-change: transform, opacity; }
.toast-enter-from { transform: translateX(100%) scale(.95); opacity: 0; }
.toast-leave-to { transform: translateX(40px) scale(.95); opacity: 0; }
.toast-move { transition: transform .3s var(--ease-out-expo); }

/* ── Dark ── */
.dark .toast { background: var(--card); border-color: rgba(var(--text-on-dark-rgb),.1); box-shadow: 0 8px 32px rgba(var(--black-rgb),.5); }

@media (max-width: 480px) {
  .toast-container {
    top: max(var(--space-2), env(safe-area-inset-top, 0px));
    right: max(var(--space-2), env(safe-area-inset-right, 0px));
    left: max(var(--space-2), env(safe-area-inset-left, 0px));
    max-width: none;
    width: auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active,
  .toast-move { transition: none; }
  .toast-icon { animation: none; }
  .toast-progress { animation: none; }
}
@media (forced-colors: active) {
  .toast { border: 1px solid CanvasText; background: Canvas; }
  .toast-dismiss { border: 1px solid ButtonText; }
  .toast-progress { background: Highlight; }
}
</style>
