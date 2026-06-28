<template>
  <Teleport to="body">
    <div class="toast-container" aria-label="Thông báo" role="region" aria-live="polite">
      <TransitionGroup name="toast">
        <div v-for="t in toasts" :key="t.id" :class="['toast', t.type]" :role="t.type === 'error' || t.type === 'warning' ? 'alert' : 'status'" :aria-live="t.type === 'error' || t.type === 'warning' ? 'assertive' : 'polite'">
          <span class="toast-icon" aria-hidden="true">{{ iconFor(t.type) }}</span>
          <span class="toast-msg">{{ t.message }}</span>
          <button type="button" class="toast-dismiss" aria-label="Đóng" @click="dismiss(t.id)">&times;</button>
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
    dismiss(toasts.value[toasts.value.length - 1].id)
  }
}
onMounted(() => document.addEventListener('keydown', onEscDismiss))
onUnmounted(() => document.removeEventListener('keydown', onEscDismiss))

function iconFor(type?: string) {
  if (type === 'success') return '✓'
  if (type === 'error') return '✕'
  if (type === 'warning') return '⚠'
  return 'ℹ'
}
</script>

<style scoped>
.toast-container {
  position: fixed; top: var(--space-4); right: var(--space-4); z-index: var(--z-toast);
  display: flex; flex-direction: column; gap: var(--space-2);
  max-width: 380px; width: calc(100% - var(--space-8));
  pointer-events: none;
}

.toast {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  padding-left: calc(var(--space-4) + 3px);
  border-radius: var(--radius-lg);
  background: var(--card);
  border: .5px solid var(--line);
  border-left: 3px solid var(--toast-accent, var(--line));
  box-shadow: var(--shadow-lg);
  backdrop-filter: var(--glass, blur(16px));
  -webkit-backdrop-filter: var(--glass, blur(16px));
  pointer-events: auto;
}
.toast.success { --toast-accent: var(--success, #16a34a); }
.toast.error { --toast-accent: var(--error, #dc3545); }
.toast.warning { --toast-accent: var(--accent-dark, #d4890f); }
.toast.info { --toast-accent: var(--primary); }

.toast-icon {
  flex-shrink: 0; width: 24px; height: 24px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--radius-full);
  font-size: var(--text-xs); font-weight: var(--weight-bold);
  animation: toastIconPop .35s var(--ease-spring-gentle, cubic-bezier(.2,1.2,.4,1)) .15s both;
}
@keyframes toastIconPop { from { transform: scale(0); opacity: 0; } to { transform: scale(1); opacity: 1; } }
.toast.success .toast-icon { background: rgba(var(--secondary-rgb, 46,125,91), .12); color: var(--secondary); }
.toast.error .toast-icon { background: rgba(var(--error-rgb, 220,53,69), .12); color: var(--error); }
.toast.warning .toast-icon { background: rgba(var(--accent-rgb, 245,166,35), .12); color: var(--accent-dark); }
.toast.info .toast-icon { background: rgba(var(--primary-rgb), .08); color: var(--primary-fg); }

.toast-msg { flex: 1; font-size: var(--text-sm); font-weight: var(--weight-medium); color: var(--ink); line-height: var(--leading-snug); }

.toast-dismiss {
  flex-shrink: 0; width: 44px; height: 44px; margin: -10px -10px -10px 0;
  display: flex; align-items: center; justify-content: center;
  background: none; border: none; border-radius: var(--radius-full);
  color: var(--muted); cursor: pointer; font-size: var(--text-base);
  transition: background .2s, color .2s;
}
.toast-dismiss:hover { background: var(--bg-alt); color: var(--ink); }

.toast-progress {
  position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  background: currentColor; opacity: .2;
  transform-origin: left;
  animation: toastCountdown linear forwards;
}
@keyframes toastCountdown { from { transform: scaleX(1); } to { transform: scaleX(0); } }

.toast { position: relative; overflow: hidden; }

/* ── Transitions ── */
.toast-enter-active { transition: transform .35s var(--ease-spring-gentle, cubic-bezier(.2,1.2,.4,1)), opacity .25s var(--ease-out, ease-out); will-change: transform, opacity; }
.toast-leave-active { transition: transform .2s var(--ease-out, ease-out), opacity .15s var(--ease-out, ease-out); will-change: transform, opacity; }
.toast-enter-from { transform: translateX(100%) scale(.95); opacity: 0; }
.toast-leave-to { transform: translateX(40px) scale(.95); opacity: 0; }
.toast-move { transition: transform .3s var(--ease-spring-gentle, cubic-bezier(.2,1.2,.4,1)); }

/* ── Dark ── */
.dark .toast { background: var(--card); border-color: rgba(var(--text-on-dark-rgb, 255,255,255),.1); box-shadow: 0 8px 32px rgba(0,0,0,.5); }

@media (max-width: 480px) {
  .toast-container { right: var(--space-2); left: var(--space-2); max-width: none; width: auto; }
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active,
  .toast-move { transition: none; }
  .toast-icon { animation: none; }
}
@media (forced-colors: active) {
  .toast { border: 1px solid CanvasText; background: Canvas; }
  .toast-dismiss { border: 1px solid ButtonText; }
  .toast-progress { background: Highlight; }
}
</style>
