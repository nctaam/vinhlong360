<template>
  <div
    class="home-atmosphere-control"
    role="region"
    aria-label="Điều phối con nước và thời khắc thực địa Vĩnh Long"
  >
    <!-- Switcher bar: 3 thời khắc đặc trưng -->
    <div class="home-atmosphere-control__modes" role="tablist" aria-label="Chọn thời khắc sông nước">
      <button
        v-for="mode in MODES"
        :key="mode.id"
        type="button"
        role="tab"
        class="home-atmosphere-control__mode-btn"
        :class="{ 'is-active': activeMode === mode.id }"
        :aria-selected="activeMode === mode.id"
        :tabindex="activeMode === mode.id ? 0 : -1"
        @click="selectMode(mode.id)"
      >
        <span class="home-atmosphere-control__mode-dot" aria-hidden="true" />
        <span class="home-atmosphere-control__mode-time">{{ mode.timeRange }}</span>
        <span class="home-atmosphere-control__mode-title">{{ mode.shortTitle }}</span>
      </button>
    </div>

    <!-- Active dynamic cognitive pill -->
    <div class="home-atmosphere-control__capsule cinema-glass-plate" :data-current-mode="activeMode">
      <div class="home-atmosphere-control__segment home-atmosphere-control__segment--weather">
        <IconLine :name="currentConfig.icon" class="home-atmosphere-control__icon" aria-hidden="true" />
        <strong class="home-atmosphere-control__title">{{ currentConfig.weather }}</strong>
        <span class="home-atmosphere-control__sep" aria-hidden="true">·</span>
        <span class="home-atmosphere-control__desc">{{ currentConfig.temp }} {{ currentConfig.weatherDesc }}</span>
      </div>

      <div class="home-atmosphere-control__segment home-atmosphere-control__segment--tide">
        <IconLine name="droplet" class="home-atmosphere-control__icon" aria-hidden="true" />
        <strong class="home-atmosphere-control__title">Sông Cổ Chiên: {{ currentConfig.tideLabel }}</strong>
        <span class="home-atmosphere-control__sep" aria-hidden="true">·</span>
        <span class="home-atmosphere-control__desc">{{ currentConfig.tideDesc }}</span>
      </div>

      <div class="home-atmosphere-control__segment home-atmosphere-control__segment--curator">
        <IconLine name="compass" class="home-atmosphere-control__icon" aria-hidden="true" />
        <span class="home-atmosphere-control__curator-label">Thời khắc vàng:</span>
        <span class="home-atmosphere-control__desc">{{ currentConfig.advice }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import IconLine from '~/components/IconLine.vue'

export type AtmosphereMode = 'dawn' | 'noon' | 'dusk'

interface AtmosphereConfig {
  readonly id: AtmosphereMode
  readonly timeRange: string
  readonly shortTitle: string
  readonly weather: string
  readonly temp: string
  readonly weatherDesc: string
  readonly tideLabel: string
  readonly tideDesc: string
  readonly advice: string
  readonly icon: string
}

const MODES: readonly AtmosphereConfig[] = [
  {
    id: 'dawn',
    timeRange: '05:30 – 09:00',
    shortTitle: 'Bình minh Cù lao',
    weather: 'Sương mai thanh khiết',
    temp: '26°C',
    weatherDesc: 'Gió bến sông chớm dậy',
    tideLabel: 'Nước lớn đầy vành',
    tideDesc: 'Đò sớm êm sóng, chợ nổi nhộn nhịp',
    advice: 'Chợ nổi Trà Ôn & Vườn chôm chôm An Bình lúc đọng sương',
    icon: 'sun',
  },
  {
    id: 'noon',
    timeRange: '09:30 – 16:00',
    shortTitle: 'Trưa nắng Miệt vườn',
    weather: 'Trời êm nắng rực',
    temp: '31°C',
    weatherDesc: 'Bóng râm rợp mát vựa cây',
    tideLabel: 'Nước ròng phẳng lặng',
    tideDesc: 'Đò êm mái chèo, thuận đường xuồng rạch',
    advice: 'Vương quốc Gốm Mang Thít, Nhà cổ Cai Cường & Cá tai tượng chiên xù',
    icon: 'sun',
  },
  {
    id: 'dusk',
    timeRange: '16:30 – 21:30',
    shortTitle: 'Hoàng hôn & Dạ khúc',
    weather: 'Gió lộng chiều tà',
    temp: '28°C',
    weatherDesc: 'Nắng xiên rực đỏ vòm gốm',
    tideLabel: 'Nước lững soi bóng',
    tideDesc: 'Mặt nước dát vàng, đờn ca tài tử bến sông',
    advice: 'Sunset đò ngang sông Cổ Chiên & Đêm đờn ca tài tử Homestay Út Trinh',
    icon: 'moon',
  },
]

const props = withDefaults(
  defineProps<{
    modelValue?: AtmosphereMode
  }>(),
  {
    modelValue: undefined,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: AtmosphereMode): void
}>()

const localMode = ref<AtmosphereMode>('noon')

const activeMode = computed<AtmosphereMode>(() => {
  return props.modelValue ?? localMode.value
})

const currentConfig = computed(() => {
  return MODES.find(m => m.id === activeMode.value) ?? MODES[1]!
})

function detectInitialAtmosphere(): AtmosphereMode {
  const hour = new Date().getHours()
  if (hour >= 5 && hour < 10) return 'dawn'
  if (hour >= 10 && hour < 16) return 'noon'
  return 'dusk'
}

onMounted(() => {
  if (props.modelValue === undefined) {
    const detected = detectInitialAtmosphere()
    localMode.value = detected
    emit('update:modelValue', detected)
  }
})

function selectMode(id: AtmosphereMode) {
  localMode.value = id
  emit('update:modelValue', id)
}
</script>

<style scoped>
.home-atmosphere-control {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
}

.home-atmosphere-control__modes {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.home-atmosphere-control__mode-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 34px;
  padding: 4px 12px;
  border-radius: var(--radius-pill, 999px);
  background: color-mix(in srgb, var(--color-surface) 80%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  cursor: pointer;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1),
              background 0.2s ease,
              border-color 0.2s ease,
              color 0.2s ease,
              box-shadow 0.2s ease;
}

.home-atmosphere-control__mode-btn:hover {
  color: var(--color-text);
  border-color: color-mix(in srgb, var(--mangthit-600) 40%, transparent);
  background: color-mix(in srgb, var(--color-surface) 95%, transparent);
  transform: translateY(-1px);
}

.home-atmosphere-control__mode-btn:active {
  transform: scale(0.97);
}

.home-atmosphere-control__mode-btn:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.home-atmosphere-control__mode-btn.is-active {
  color: var(--color-text);
  font-weight: var(--weight-bold);
  background: color-mix(in srgb, var(--color-surface) 98%, transparent);
  border-color: color-mix(in srgb, var(--mangthit-600) 65%, var(--color-border));
  box-shadow: 0 4px 12px rgba(var(--black-rgb), 0.08),
              0 0 0 1px color-mix(in srgb, var(--mangthit-600) 25%, transparent);
}

.home-atmosphere-control__mode-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-text-muted);
  transition: background 0.2s ease, transform 0.2s ease;
}

.home-atmosphere-control__mode-btn.is-active .home-atmosphere-control__mode-dot {
  background: var(--mangthit-600);
  transform: scale(1.3);
  box-shadow: 0 0 6px var(--mangthit-500);
}

.home-atmosphere-control__mode-time {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  opacity: 0.75;
}

.home-atmosphere-control__mode-title {
  letter-spacing: -0.01em;
}

.home-atmosphere-control__capsule {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-surface, 16px);
  border: 1px solid color-mix(in srgb, var(--color-border) 80%, transparent);
  box-shadow: 0 8px 24px rgba(var(--black-rgb), 0.08);
  transition: border-color 0.3s ease, background 0.3s ease;
}

@media (min-width: 768px) {
  .home-atmosphere-control__capsule {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-4);
  }
}

.home-atmosphere-control__segment {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text);
  line-height: 1.4;
}

.home-atmosphere-control__icon {
  font-size: 14px;
  color: var(--mangthit-600);
  flex-shrink: 0;
}

.home-atmosphere-control__title {
  font-weight: var(--weight-bold);
  color: var(--color-text);
}

.home-atmosphere-control__curator-label {
  font-weight: var(--weight-bold);
  color: var(--mangthit-600);
  text-transform: uppercase;
  font-size: 10.5px;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}

.home-atmosphere-control__sep {
  color: var(--color-text-muted);
  opacity: 0.6;
}

.home-atmosphere-control__desc {
  color: var(--color-text-muted);
}

@media (prefers-reduced-motion: reduce) {
  .home-atmosphere-control__mode-btn,
  .home-atmosphere-control__mode-dot,
  .home-atmosphere-control__capsule {
    transition: none !important;
    transform: none !important;
  }
}
</style>
