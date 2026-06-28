<script setup lang="ts">
interface FilterOption {
  key: string
  label: string
  icon?: string
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
      <span v-if="f.icon" class="fc-icon" aria-hidden="true">{{ f.icon }}</span>
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
}
.fc-row::-webkit-scrollbar { display: none; }

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
  font-weight: var(--weight-medium, 500);
  cursor: pointer;
  transition: background-color 150ms, color 150ms, border-color 150ms;
  white-space: nowrap;
  min-height: 44px;
}

.fc-chip:hover {
  background: rgba(var(--primary-rgb), 0.06);
}

.fc-chip:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.fc-chip.active {
  background: var(--chip-active-bg);
  color: var(--chip-active-text);
  border-color: transparent;
}

.fc-icon { font-size: 1.1em; }

.fc-count {
  font-size: var(--text-xs);
  opacity: 0.7;
  font-weight: var(--weight-normal, 400);
}
.fc-chip.active .fc-count { opacity: 0.85; }
</style>
