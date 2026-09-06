<template>
  <div class="schedule-option">
    <label class="schedule-toggle">
      <input
        type="checkbox"
        :checked="modelValue"
        class="cd-toggle"
        @change="$emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
      />
      <span>Lên lịch đăng bài</span>
    </label>
    <div v-if="modelValue" class="schedule-picker">
      <input
        type="datetime-local"
        :value="scheduledAt"
        :min="minScheduleDate"
        class="cd-input"
        aria-label="Chọn thời gian đăng bài"
        @input="$emit('update:scheduledAt', ($event.target as HTMLInputElement).value)"
      />
      <span class="cd-hint">Bài sẽ được đăng tự động vào thời gian đã chọn</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: boolean
  scheduledAt: string
  minScheduleDate: string
}>()

defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'update:scheduledAt', val: string): void
}>()
</script>

<style scoped>
.schedule-option { margin-top: var(--space-1); }
.schedule-toggle { display: flex; align-items: center; gap: var(--space-2); cursor: pointer; font-size: var(--text-sm); color: var(--ink); width: fit-content; }
.schedule-picker { margin-top: var(--space-2); display: flex; flex-direction: column; gap: var(--space-1); align-items: flex-start; }
.cd-toggle { appearance: none; width: 40px; height: 22px; background: var(--muted); border-radius: 11px; position: relative; cursor: pointer; transition: background .25s var(--ease-out); flex-shrink: 0; min-height: 44px; padding: 11px 0; box-sizing: content-box; margin: 0; }
.cd-toggle::after { content: ''; position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; background: var(--white, var(--white)); border-radius: 50%; transition: transform .25s var(--ease-out-expo); box-shadow: 0 1px 3px rgba(var(--black-rgb),.15); }
.cd-toggle:checked { background: var(--color-action); }
.cd-toggle:checked::after { transform: translateX(18px); }
.cd-toggle:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.cd-input {
  padding: var(--space-2) var(--space-3); border: 1px solid var(--line); border-radius: var(--radius-surface);
  background: var(--bg-alt); color: var(--ink); font-size: var(--text-sm); font-family: inherit; min-height: 44px;
}
.cd-input:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 1px; border-color: var(--color-focus); box-shadow: 0 0 0 3px rgba(var(--accent-rgb), .15); }
.cd-hint { font-size: var(--text-xs); color: var(--muted); }

@media (max-width: 820px) {
  .cd-input { font-size: var(--text-base, 16px); }
}

@media (prefers-reduced-motion: reduce) {
  .cd-toggle, .cd-toggle::after { transition: none; }
}
</style>
