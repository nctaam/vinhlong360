<template>
  <section class="system-state" :class="`system-state-${kind}`" role="alert" aria-live="polite">
    <div class="system-state-signal" aria-hidden="true">
      <span class="system-state-node"></span>
    </div>
    <div class="system-state-icon" aria-hidden="true">
      <IconLine :name="iconName" />
    </div>
    <div class="system-state-copy">
      <p class="system-state-label">{{ stateLabel }}</p>
      <h1>{{ title }}</h1>
      <p class="system-state-description">{{ description }}</p>
      <p v-if="details" class="system-state-details">{{ details }}</p>
      <p v-if="retryAfter" class="system-state-retry">Có thể thử lại lúc {{ retryAfter }}</p>
      <div v-if="primaryLabel || secondaryLabel" class="system-state-actions">
        <button v-if="primaryLabel" type="button" class="btn btn-primary" @click="$emit('primary')">
          {{ primaryLabel }}
        </button>
        <button v-if="secondaryLabel" type="button" class="btn btn-ghost" @click="$emit('secondary')">
          {{ secondaryLabel }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
export type SystemStateKind =
  | 'permission-denied'
  | 'session-expired'
  | 'partial'
  | 'conflict'
  | 'rate-limited'
  | 'offline'
  | 'read-only'
  | 'error'

const props = defineProps<{
  kind: SystemStateKind
  title: string
  description: string
  primaryLabel?: string
  secondaryLabel?: string
  details?: string
  retryAfter?: string
}>()

defineEmits<{
  primary: []
  secondary: []
}>()

const STATE_META: Record<SystemStateKind, { label: string; icon: string }> = {
  'permission-denied': { label: 'Quyền truy cập', icon: 'alert-triangle' },
  'session-expired': { label: 'Phiên đăng nhập', icon: 'clock' },
  partial: { label: 'Dữ liệu một phần', icon: 'database' },
  conflict: { label: 'Dữ liệu đã thay đổi', icon: 'repeat' },
  'rate-limited': { label: 'Giới hạn thao tác', icon: 'clock' },
  offline: { label: 'Kết nối', icon: 'globe' },
  'read-only': { label: 'Chỉ đọc', icon: 'file-text' },
  error: { label: 'Sự cố hệ thống', icon: 'alert-triangle' },
}

const stateLabel = computed(() => STATE_META[props.kind].label)
const iconName = computed(() => STATE_META[props.kind].icon)
</script>

<style scoped>
.system-state {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-5);
  width: min(100%, 720px);
  padding: clamp(var(--space-6), 5vw, var(--space-10));
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--card);
}

.system-state-signal {
  position: absolute;
  inset: 0 auto 0 0;
  width: 5px;
  background: var(--primary);
}

.system-state-node {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 11px;
  height: 11px;
  border: 2px solid var(--card);
  border-radius: 50%;
  background: var(--primary);
  transform: translate(-50%, -50%);
}

.system-state-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  color: var(--primary);
  background: var(--bg-alt);
  font-size: 1.5rem;
}

.system-state-copy { min-width: 0; }
.system-state-label {
  margin: 0 0 var(--space-2);
  color: var(--muted);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.system-state h1 {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: clamp(1.5rem, 4vw, 2.25rem);
  line-height: 1.2;
}

.system-state-description,
.system-state-details,
.system-state-retry {
  max-width: 60ch;
  margin: var(--space-3) 0 0;
  color: var(--muted);
  line-height: 1.65;
}

.system-state-details,
.system-state-retry { font-size: var(--text-sm); }
.system-state-retry { color: var(--warning); font-weight: 600; }

.system-state-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-6);
}

.system-state-permission-denied .system-state-signal,
.system-state-error .system-state-signal,
.system-state-permission-denied .system-state-node,
.system-state-error .system-state-node { background: var(--error); }

.system-state-permission-denied .system-state-icon,
.system-state-error .system-state-icon { color: var(--error); }

.system-state-rate-limited .system-state-signal,
.system-state-rate-limited .system-state-node { background: var(--warning); }
.system-state-rate-limited .system-state-icon { color: var(--warning); }

@media (max-width: 560px) {
  .system-state { grid-template-columns: 1fr; }
  .system-state-actions { align-items: stretch; flex-direction: column; }
  .system-state-actions .btn { width: 100%; }
}
</style>
