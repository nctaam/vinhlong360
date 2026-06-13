<template>
  <div v-if="weather" class="weather-bar">
    <span class="weather-icon">{{ weatherIcon }}</span>
    <span class="weather-temp">{{ weather.temp || weather.temperature || '—' }}°C</span>
    <span class="weather-desc">{{ weather.description || weather.condition || '' }}</span>
    <span class="weather-place">Vĩnh Long</span>
  </div>
</template>

<script setup lang="ts">
const weather = ref<any>(null)

const weatherIcon = computed(() => {
  const desc = (weather.value?.description || weather.value?.condition || '').toLowerCase()
  if (desc.includes('mưa') || desc.includes('rain')) return '🌧️'
  if (desc.includes('mây') || desc.includes('cloud')) return '⛅'
  if (desc.includes('nắng') || desc.includes('sun') || desc.includes('clear')) return '☀️'
  return '🌤️'
})

onMounted(async () => {
  try {
    const res = await $fetch<any>('/weather?area=vinh-long')
    if (res && !res.error) weather.value = res
  } catch { /* weather not available */ }
})
</script>
