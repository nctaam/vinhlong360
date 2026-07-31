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
const selectedMode = ref<Mode>('dark')
const hydrated = ref(false)

watch(() => colorMode.preference, (preference) => {
  if (hydrated.value && (preference === 'light' || preference === 'dark')) {
    selectedMode.value = preference
  }
})

onMounted(() => {
  const bootstrap = (window as Window & {
    __NUXT_COLOR_MODE__?: { preference?: unknown; value?: unknown }
  }).__NUXT_COLOR_MODE__
  const bootstrapMode: Mode | null = bootstrap?.preference === 'light' || bootstrap?.preference === 'dark'
    ? bootstrap.preference
    : null
  // The color-mode bootstrap can paint a stored choice before Nuxt hydrates.
  const prepaintedMode = document.documentElement.classList.contains('light') ? 'light' :
    document.documentElement.classList.contains('dark') ? 'dark' : null
  const initialMode: Mode = bootstrapMode ?? prepaintedMode ?? (colorMode.preference === 'light' ? 'light' : 'dark')
  if (colorMode.preference !== initialMode) colorMode.preference = initialMode
  selectedMode.value = initialMode
  hydrated.value = true
})

function isActive(mode: Mode) {
  return selectedMode.value === mode
}

function selectMode(mode: Mode, event: MouseEvent) {
  selectedMode.value = mode
  colorMode.preference = mode
  ;(event.currentTarget as HTMLButtonElement).focus()
}
</script>
