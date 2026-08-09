<template>
  <div class="theme-mode-control" data-theme-control role="group" aria-label="Chọn giao diện">
    <button
      v-for="mode in modes"
      :key="mode.value"
      type="button"
      :data-theme-mode="mode.value"
      :aria-pressed="isActive(mode.value)"
      :aria-label="mode.label"
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
const accessibility = useAccessibilityProfile({ colorMode, autoHydrate: false })
const selectedMode = computed<Mode>(() => accessibility.profile.value.theme === 'parchment' ? 'light' : 'dark')

watch(() => colorMode.preference, (preference) => {
  const nextTheme = preference === 'light' ? 'parchment' : 'nocturne'
  if (accessibility.profile.value.theme !== nextTheme) accessibility.setProfile({ theme: nextTheme })
})

onMounted(() => {
  accessibility.hydrate()
})

function isActive(mode: Mode) {
  return selectedMode.value === mode
}

function selectMode(mode: Mode, event: MouseEvent) {
  accessibility.setProfile({ theme: mode === 'light' ? 'parchment' : 'nocturne' })
  ;(event.currentTarget as HTMLButtonElement).focus()
}
</script>
