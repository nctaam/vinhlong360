<template>
  <div v-if="weather" class="weather-bar">
    <div class="weather-inner">
      <span class="weather-icon">{{ weatherIcon }}</span>
      <span v-if="tempC != null" class="weather-temp">{{ tempC }}°C</span>
      <span class="weather-desc">{{ desc }}</span>
      <span class="weather-place">📍 {{ areaName }}</span>
      <span v-if="weather.suggestion" class="weather-tip">{{ weather.suggestion }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
const weather = ref<Record<string, any> | null>(null)
let timer: ReturnType<typeof setInterval> | null = null

const tempC = computed(() => weather.value?.temp_c ?? weather.value?.temp ?? weather.value?.temperature ?? null)
const desc = computed(() => (weather.value?.description || weather.value?.condition || '') as string)
const areaName = computed(() => weather.value?.area_name || 'Vĩnh Long')

const weatherIcon = computed(() => {
  const d = desc.value.toLowerCase()
  if (d.includes('mưa') || d.includes('rain')) return '🌧️'
  if (d.includes('mây') || d.includes('cloud')) return '⛅'
  if (d.includes('nắng') || d.includes('sun') || d.includes('clear')) return '☀️'
  return '🌤️'
})

async function fetchWeather(retries = 1) {
  try {
    const res = await $fetch<Record<string, any>>('/weather?area=vinh-long')
    if (res && !res.error) weather.value = res
  } catch {
    if (retries > 0) setTimeout(() => fetchWeather(retries - 1), 5000)
  }
}

onMounted(() => {
  fetchWeather()
  timer = setInterval(fetchWeather, 30 * 60 * 1000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.weather-temp { font-weight: 800; color: var(--accent-dark); }
.weather-desc { color: var(--ink); text-transform: capitalize; }
.weather-place { color: var(--muted); font-weight: 600; }
.weather-tip { color: var(--muted); font-size: .82rem; }
@media (max-width: 640px) { .weather-tip { display: none; } }
</style>
