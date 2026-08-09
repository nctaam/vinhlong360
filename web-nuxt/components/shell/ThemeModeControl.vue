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
// Hydration must match the Nocturne SSR fallback; persisted choices apply after mount.
const selectedMode = ref<Mode>('dark')
const semanticTheme = computed(() => selectedMode.value === 'light' ? 'parchment' : 'nocturne')

useHead({
  htmlAttrs: { 'data-theme': semanticTheme },
  script: [{
    key: 'vl360-semantic-theme-prepaint',
    innerHTML: "try{var d=document.documentElement,v=localStorage.getItem('vl360-color-mode');d.dataset.theme=v==='light'?'parchment':'nocturne'}catch(_){document.documentElement.dataset.theme='nocturne'}",
    tagPosition: 'head',
  }],
})

watch(() => colorMode.preference, (preference) => {
  if (isMode(preference)) {
    selectedMode.value = preference
    setDocumentTheme(preference)
  }
})

onMounted(() => {
  const initialMode = resolveMountedMode()
  if (colorMode.preference !== initialMode) colorMode.preference = initialMode
  selectedMode.value = initialMode
  setDocumentTheme(initialMode)
})

function isMode(value: unknown): value is Mode {
  return value === 'light' || value === 'dark'
}

function resolveMountedMode(): Mode {
  if (import.meta.client) {
    const bootstrap = (window as Window & {
      __NUXT_COLOR_MODE__?: { preference?: unknown; value?: unknown }
    }).__NUXT_COLOR_MODE__
    const bootstrapMode = isMode(bootstrap?.preference) ? bootstrap.preference :
      isMode(bootstrap?.value) ? bootstrap.value : null
    const prepaintedMode = document.documentElement.classList.contains('light') ? 'light' :
      document.documentElement.classList.contains('dark') ? 'dark' : null
    if (bootstrapMode) return bootstrapMode
    if (prepaintedMode) return prepaintedMode
  }

  if (isMode(colorMode.preference)) return colorMode.preference
  return isMode(colorMode.value) ? colorMode.value : 'dark'
}

function isActive(mode: Mode) {
  return selectedMode.value === mode
}

function selectMode(mode: Mode, event: MouseEvent) {
  selectedMode.value = mode
  colorMode.preference = mode
  setDocumentTheme(mode)
  ;(event.currentTarget as HTMLButtonElement).focus()
}

function setDocumentTheme(mode: Mode) {
  if (import.meta.client) document.documentElement.dataset.theme = mode === 'light' ? 'parchment' : 'nocturne'
}
</script>
