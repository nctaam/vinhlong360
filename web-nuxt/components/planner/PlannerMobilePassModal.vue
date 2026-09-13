<template>
  <div
    v-if="open"
    class="planner-pass-modal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="pass-modal-title"
  >
    <div class="planner-pass-modal__backdrop" @click="close" />
    <div class="planner-pass-modal__sheet">
      <header class="planner-pass-modal__head">
        <div class="planner-pass-modal__brand">
          <div class="planner-pass-modal__badge-row">
            <span class="planner-pass-modal__pill">Thẻ hành trình thực địa</span>
            <span class="planner-pass-modal__offline-pill">
              <IconLine name="wifi" aria-hidden="true" />
              <span>Khả dụng ngoại tuyến</span>
            </span>
          </div>
          <h2 id="pass-modal-title" class="planner-pass-modal__title">{{ title || 'Lịch trình Vĩnh Long' }}</h2>
        </div>
        <button
          type="button"
          class="planner-pass-modal__close"
          aria-label="Đóng thẻ hành trình"
          @click="close"
        >
          <IconLine name="x" aria-hidden="true" />
        </button>
      </header>

      <div class="planner-pass-modal__card">
        <div class="planner-pass-modal__meta">
          <div>
            <span class="planner-pass-modal__label">Số điểm đến</span>
            <strong>{{ stops.length }} điểm</strong>
          </div>
          <div>
            <span class="planner-pass-modal__label">Phương thức</span>
            <strong>Đường bộ &amp; Đò sông</strong>
          </div>
        </div>

        <ol class="planner-pass-modal__timeline">
          <li v-for="(stop, i) in stops" :key="stop.id" class="planner-pass-modal__stop">
            <span class="planner-pass-modal__step-num">{{ i + 1 }}</span>
            <div class="planner-pass-modal__stop-info">
              <strong class="planner-pass-modal__stop-name">{{ stop.name }}</strong>
              <span v-if="stop.place_name" class="planner-pass-modal__stop-place">{{ stop.place_name }}</span>
            </div>
          </li>
        </ol>

        <div class="planner-pass-modal__notice">
          <p>
            <strong>Cứu hộ &amp; Hỗ trợ địa phương:</strong> Phà An Bình (24/7) · Hotline 0270 3822 188.
          </p>
        </div>
      </div>

      <footer class="planner-pass-modal__foot">
        <button type="button" class="planner-pass-modal__btn-print" @click="printPass">
          <IconLine name="printer" aria-hidden="true" />
          <span>In hoặc Lưu PDF</span>
        </button>
        <button type="button" class="planner-pass-modal__btn-done" @click="close">
          <span>Xong</span>
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  open: boolean
  title: string
  stops: Array<{ id: string; name: string; place_name?: string }>
}>()

const emit = defineEmits<{
  (e: 'update:open', val: boolean): void
}>()

function close() {
  emit('update:open', false)
}

function printPass() {
  if (typeof window !== 'undefined') {
    window.print()
  }
}
</script>

<style scoped>
.planner-pass-modal {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
}

.planner-pass-modal__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(var(--black-rgb), 0.6);
  backdrop-filter: blur(4px);
}

.planner-pass-modal__sheet {
  position: relative;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  overflow-y: auto;
  border-radius: var(--radius-sheet);
  background: var(--color-canvas);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-lg, 0 10px 25px -5px rgba(var(--black-rgb), 0.2));
  padding: var(--space-5);
}

.planner-pass-modal__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.planner-pass-modal__badge-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

.planner-pass-modal__pill {
  display: inline-block;
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--mangthit-500, var(--color-material-clay));
}

.planner-pass-modal__offline-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-2xs);
  font-weight: var(--weight-medium);
  color: var(--color-material-river);
  background: color-mix(in srgb, var(--color-material-river) 10%, transparent);
  border-radius: var(--radius-pill, 999px);
  padding: 0.125rem var(--space-2);
}

.planner-pass-modal__title {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: var(--text-lg);
  color: var(--color-text);
}

.planner-pass-modal__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-pill, 999px);
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: background .2s ease, color .2s ease;
}

.planner-pass-modal__close:hover {
  background: rgba(var(--black-rgb), 0.05);
  color: var(--color-text);
}

.dark .planner-pass-modal__close:hover {
  background: rgba(var(--white-rgb), 0.1);
}

.planner-pass-modal__close:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.planner-pass-modal__card {
  border-radius: var(--radius-surface, 12px);
  border: 1px solid var(--color-border);
  padding: var(--space-4);
  background: rgba(var(--black-rgb), 0.02);
  margin-bottom: var(--space-4);
}

.dark .planner-pass-modal__card {
  background: rgba(var(--white-rgb), 0.03);
}

.planner-pass-modal__meta {
  display: flex;
  justify-content: space-between;
  padding-bottom: var(--space-3);
  margin-bottom: var(--space-3);
  border-bottom: 1px dashed var(--color-border);
}

.planner-pass-modal__label {
  display: block;
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--color-text-muted);
}

.planner-pass-modal__timeline {
  margin: 0 0 var(--space-4);
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.planner-pass-modal__stop {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.planner-pass-modal__step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: var(--radius-pill, 999px);
  background: var(--mangthit-500, var(--color-material-clay));
  color: var(--white);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--mangthit-500) 25%, transparent);
  flex-shrink: 0;
}

.planner-pass-modal__stop-info {
  display: flex;
  flex-direction: column;
}

.planner-pass-modal__stop-name {
  font-size: var(--text-sm);
  color: var(--color-text);
}

.planner-pass-modal__stop-place {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.planner-pass-modal__notice {
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
  color: var(--color-text-muted);
  border-top: 1px dashed var(--color-border);
  padding-top: var(--space-3);
}

.planner-pass-modal__foot {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

.planner-pass-modal__btn-print {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  min-height: 44px;
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-control, 8px);
  border: 1px solid var(--color-border);
  background: var(--color-canvas);
  color: var(--color-text);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition: background .2s ease, border-color .2s ease;
}

.planner-pass-modal__btn-print:hover {
  background: rgba(var(--black-rgb), 0.04);
}

.dark .planner-pass-modal__btn-print:hover {
  background: rgba(var(--white-rgb), 0.08);
}

.planner-pass-modal__btn-print:focus-visible,
.planner-pass-modal__btn-done:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.planner-pass-modal__btn-done {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-control, 8px);
  border: none;
  background: var(--mangthit-500, var(--color-material-clay));
  color: var(--white);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition: opacity .2s ease;
}

.planner-pass-modal__btn-done:hover {
  opacity: 0.9;
}
</style>
