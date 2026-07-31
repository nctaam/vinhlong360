<template>
  <div class="theme-mode-control" data-theme-control role="group" aria-label="Chọn giao diện">
    <button
      v-for="mode in modes"
      :key="mode.value"
      type="button"
      :data-theme-mode="mode.value"
      :aria-pressed="isActive(mode.value)"
      :aria-label="`${mode.label}: ${mode.description}`"
      :title="mode.description"
      @click="selectMode(mode.value, $event)"
    >
      <IconLine :name="mode.value === 'dark' ? 'moon' : 'sun'" aria-hidden="true" />
      <span class="theme-mode-label">{{ mode.label }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
const modes = [
  { value: 'dark', label: 'Nocturne', description: 'Nền tối mặc định' },
  { value: 'light', label: 'Nền sáng dễ đọc', description: 'Biến thể tăng khả năng đọc' },
] as const

type Mode = (typeof modes)[number]['value']
const colorMode = useColorMode()

function isActive(mode: Mode) {
  return mode === 'light' ? colorMode.value === 'light' : colorMode.value !== 'light'
}

function selectMode(mode: Mode, event: MouseEvent) {
  colorMode.preference = mode
  ;(event.currentTarget as HTMLButtonElement).focus()
}
</script>
