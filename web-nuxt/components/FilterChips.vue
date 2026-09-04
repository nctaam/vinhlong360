<script setup lang="ts">
interface FilterOption {
  key: string
  label: string
  icon?: string
  /** Tên biểu tượng IconLine — thay cho `icon` dạng emoji (B2: thêm đường mới). */
  iconName?: string
  count?: number
}

const props = withDefaults(defineProps<{
  filters: FilterOption[]
  modelValue: string[]
  singleSelect?: boolean
}>(), { singleSelect: false })

const emit = defineEmits<{ 'update:modelValue': [keys: string[]] }>()

function toggle(key: string) {
  if (props.singleSelect) {
    emit('update:modelValue', props.modelValue.includes(key) ? [] : [key])
    return
  }
  const next = props.modelValue.includes(key)
    ? props.modelValue.filter(k => k !== key)
    : [...props.modelValue, key]
  emit('update:modelValue', next)
}
</script>

<template>
  <div class="fc-row" role="group">
    <button
      v-for="f in filters"
      :key="f.key"
      type="button"
      :class="['fc-chip', { active: modelValue.includes(f.key) }]"
      :aria-pressed="modelValue.includes(f.key)"
      @click="toggle(f.key)"
    >
      <span v-if="f.iconName" class="fc-icon" aria-hidden="true"><IconLine :name="f.iconName" /></span>
      <span v-else-if="f.icon" class="fc-icon" aria-hidden="true">{{ f.icon }}</span>
      <span class="fc-label">{{ f.label }}</span>
      <span v-if="f.count != null" class="fc-count">{{ f.count }}</span>
    </button>
  </div>
</template>

<style scoped>
.fc-row {
  display: flex;
  gap: var(--chip-gap);
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  padding: var(--space-1) 0;
  -webkit-mask-image: linear-gradient(to right, black 0%, black calc(100% - 32px), transparent 100%);
  mask-image: linear-gradient(to right, black 0%, black calc(100% - 32px), transparent 100%);
}
.fc-row::-webkit-scrollbar { display: none; }
.fc-row:focus-within,
.fc-row:hover {
  -webkit-mask-image: none;
  mask-image: none;
}

.fc-chip {
  flex: 0 0 auto;
  scroll-snap-align: start;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  height: var(--chip-height);
  padding: 0 var(--space-4);
  border: var(--chip-border);
  border-radius: var(--chip-radius);
  background: transparent;
  color: var(--ink);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  letter-spacing: .01em;
  cursor: pointer;
  transition: background-color 150ms var(--ease-out), color 150ms var(--ease-out), border-color 150ms var(--ease-out), transform 200ms var(--ease-out-expo), box-shadow 200ms var(--ease-out-expo);
  white-space: nowrap;
  min-height: 44px;
}

.fc-chip:hover {
  background: rgba(var(--primary-rgb), 0.06);
  border-color: rgba(var(--primary-rgb), .3);
  transform: translateY(-1px);
}

.fc-chip:active {
  transform: scale(.96);
  transition-duration: .08s;
}

.fc-chip:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

/* active state = a hairline tri-province rule under the label instead of a heavier fill,
   so the selected chip reads as "marked" rather than as a flat app-UI toggle */
.fc-chip.active {
  background: var(--chip-active-bg);
  color: var(--chip-active-text);
  border-color: transparent;
  position: relative;
}
.fc-chip.active::after {
  content: "";
  position: absolute; left: var(--space-3); right: var(--space-3); bottom: 3px;
  height: 2px; border-radius: 2px;
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .fc-chip.active::after {
  background: linear-gradient(90deg, var(--river-legacy-dark) 0%, var(--amber-500) 52%, var(--clay-400) 100%);
}

.fc-icon { font-size: 1.1em; }
.fc-icon .line-icon { font-size: inherit; }

.fc-count {
  font-size: var(--text-xs);
  opacity: 0.75;
  font-weight: var(--weight-normal);
  font-variant-numeric: tabular-nums;
  padding: 0 6px;
  min-width: 18px;
  height: 18px;
  line-height: 18px;
  text-align: center;
  border-radius: var(--radius-full);
  background: var(--bg-alt);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.fc-chip.active .fc-count {
  opacity: 1;
  background: var(--color-brand-surface);
  color: var(--color-action);
  font-weight: var(--weight-semibold);
}
@media (prefers-reduced-motion: reduce) {
  .fc-chip { transition: none; transform: none; }
  .fc-chip:hover { transform: none; }
  .fc-chip:active { transform: none; }
}
@media (forced-colors: active) {
  .fc-row { mask-image: none; -webkit-mask-image: none; }
  .fc-chip { border: 1px solid ButtonText; }
  .fc-chip.active { border: 2px solid Highlight; }
}
</style>
