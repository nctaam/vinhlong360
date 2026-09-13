<template>
  <component
    :is="interactive ? 'button' : 'span'"
    class="mekong-water-badge"
    :class="[
      `tide-${computedState.type}`,
      {
        'mekong-water-badge--compact': compact,
        'mekong-water-badge--interactive': interactive,
      },
    ]"
    :type="interactive ? 'button' : undefined"
    data-water-badge
    data-color-role="tide"
    :data-tide-state="computedState.type"
    :title="computedState.description"
    :aria-label="ariaLabelText"
    role="status"
    @click="onClick"
  >
    <span class="mwb-indicator" aria-hidden="true">
      <IconLine :name="computedState.icon" />
    </span>

    <span class="mwb-content">
      <span class="mwb-label">{{ computedState.label }}</span>
      <span v-if="formattedLunarDate" class="mwb-lunar">
        <span class="mwb-dot" aria-hidden="true">·</span>
        <span>{{ formattedLunarDate }}</span>
      </span>
    </span>

    <span v-if="showDescription && computedState.sublabel" class="mwb-sublabel">
      ({{ computedState.sublabel }})
    </span>
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { solarToLunar } from '~/composables/useLunar'

export interface MekongWaterBadgeProps {
  /** Explicit tidal cycle state ('rong' | 'kem' | 'lon' | 'rong-can' or Vietnamese title) */
  state?: 'rong' | 'kem' | 'lon' | 'rong-can' | 'chuyen' | string | null
  /** Lunar day (1-30) */
  lunarDay?: number | null
  /** Lunar month (1-12) */
  lunarMonth?: number | null
  /** Lunar year */
  lunarYear?: number | null
  /** Solar date (ISO string or Date object) for automatic lunar conversion */
  date?: string | Date | null
  /** Compact representation */
  compact?: boolean
  /** Whether the pill behaves as an interactive button */
  interactive?: boolean
  /** Whether to show descriptive sublabel inline */
  showDescription?: boolean
}

const props = withDefaults(defineProps<MekongWaterBadgeProps>(), {
  state: null,
  lunarDay: null,
  lunarMonth: null,
  lunarYear: null,
  date: null,
  compact: false,
  interactive: false,
  showDescription: false,
})

const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void
}>()

function onClick(e: MouseEvent) {
  if (props.interactive) {
    emit('click', e)
  }
}

/** Derived lunar calendar info */
const derivedLunar = computed(() => {
  if (props.lunarDay != null) {
    return {
      day: props.lunarDay,
      month: props.lunarMonth,
      year: props.lunarYear,
    }
  }

  if (props.date) {
    try {
      const d = typeof props.date === 'string' ? new Date(props.date) : props.date
      if (!isNaN(d.getTime())) {
        const l = solarToLunar(d.getDate(), d.getMonth() + 1, d.getFullYear())
        return {
          day: l.day,
          month: l.month,
          year: l.year,
        }
      }
    } catch {
      // Ignore conversion error
    }
  }

  return null
})

/** Formatted lunar date presentation */
const formattedLunarDate = computed(() => {
  const l = derivedLunar.value
  if (!l || !l.day) return ''

  const dayStr = l.day === 1 ? 'Mùng 1' : l.day === 15 ? 'Rằm (15)' : l.day <= 10 ? `Mùng ${l.day}` : `Ngày ${l.day}`
  if (l.month) {
    return `${dayStr} th.${l.month} ÂL`
  }
  return `${dayStr} ÂL`
})

interface TideMeta {
  type: string
  label: string
  sublabel: string
  description: string
  icon: string
}

/** Computed tidal state */
const computedState = computed<TideMeta>(() => {
  const rawState = (props.state || '').trim().toLowerCase()

  // 1. Explicit state checks
  if (rawState) {
    if (rawState === 'rong' || (rawState.includes('rong') && !rawState.includes('ròng'))) {
      return {
        type: 'rong',
        label: 'Con nước rong',
        sublabel: 'Triều cường',
        description: 'Triều cường dâng cao theo tuần trăng, nước tràn liếp vườn cù lao và kênh rạch',
        icon: 'droplet',
      }
    }
    if (rawState === 'kem' || rawState.includes('kém')) {
      return {
        type: 'kem',
        label: 'Con nước kém',
        sublabel: 'Sông êm',
        description: 'Mực nước tĩnh, biên độ nhỏ, thích hợp cào hến và giăng lưới',
        icon: 'compass',
      }
    }
    if (rawState === 'lon' || rawState.includes('lớn')) {
      return {
        type: 'lon',
        label: 'Nước lớn',
        sublabel: 'Triều dâng',
        description: 'Mực nước sông đang dâng cao theo chu kỳ bán nhật triều',
        icon: 'arrow-up',
      }
    }
    if (rawState === 'rong-can' || rawState === 'ròng' || rawState.includes('ròng') || rawState.includes('cạn')) {
      return {
        type: 'rong-can',
        label: 'Nước ròng',
        sublabel: 'Triều rút',
        description: 'Mực nước sông đang hạ cạn, để lộ bãi bồi phù sa',
        icon: 'arrow-down',
      }
    }
  }

  // 2. Infer from lunar day if available
  const lDay = derivedLunar.value?.day
  if (lDay != null) {
    // Con nước rong: Mùng 1 & Rằm (và các ngày triều cường lân cận: 29, 30, 1, 2, 3, 14, 15, 16, 17, 18)
    if ([29, 30, 1, 2, 3, 14, 15, 16, 17, 18].includes(lDay)) {
      return {
        type: 'rong',
        label: 'Con nước rong',
        sublabel: 'Triều cường',
        description: 'Triều cường dâng cao theo tuần trăng, nước tràn liếp vườn cù lao và kênh rạch',
        icon: 'droplet',
      }
    }

    // Con nước kém: Mùng 7-10 & 22-25 âm lịch
    if ([7, 8, 9, 10, 22, 23, 24, 25].includes(lDay)) {
      return {
        type: 'kem',
        label: 'Con nước kém',
        sublabel: 'Sông êm',
        description: 'Mực nước tĩnh, biên độ nhỏ, thích hợp cào hến và giăng lưới',
        icon: 'compass',
      }
    }

    // Intermediate days
    return {
      type: 'chuyen',
      label: 'Con nước thường',
      sublabel: 'Triều chuyển dòng',
      description: 'Dòng nước chảy điều hòa giữa hai kỳ nước rong và nước kém',
      icon: 'droplet',
    }
  }

  // 3. Fallback default: Con nước rong (signature Mekong rhythm)
  return {
    type: 'rong',
    label: 'Con nước rong',
    sublabel: 'Triều cường',
    description: 'Chu kỳ thủy triều sông Cổ Chiên và dòng Cửu Long',
    icon: 'droplet',
  }
})

const ariaLabelText = computed(() => {
  let text = `${computedState.value.label}: ${computedState.value.description}`
  if (formattedLunarDate.value) {
    text += ` (${formattedLunarDate.value})`
  }
  return text
})
</script>

<style scoped>
.mekong-water-badge {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-15, 6px);
  min-height: 44px;
  min-width: 44px;
  padding: var(--space-2, 8px) var(--space-3, 12px);
  font-family: var(--font-sans);
  font-size: var(--text-xs, 0.75rem);
  font-weight: var(--weight-medium, 500);
  line-height: var(--leading-normal, 1.5);
  border-radius: var(--radius-full, 9999px);
  border: 1px solid transparent;
  background: var(--card);
  color: var(--ink);
  box-shadow: 0 1px 2px rgba(var(--black-rgb), 0.05);
  text-decoration: none;
  cursor: default;
  touch-action: manipulation;
  user-select: none;
  transition: background-color 0.2s ease, border-color 0.2s ease, transform 0.15s ease;
}

/* WCAG 2.2 touch target expansion to ensure absolute >= 44x44px hitbox */
.mekong-water-badge::before {
  content: "";
  position: absolute;
  top: 50%;
  left: 50%;
  min-width: 44px;
  min-height: 44px;
  width: 100%;
  height: 100%;
  transform: translate(-50%, -50%);
  border-radius: var(--radius-full, 9999px);
  pointer-events: none;
}

.mekong-water-badge--interactive {
  cursor: pointer;
}

.mekong-water-badge--interactive:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 5px rgba(var(--black-rgb), 0.08);
}

.mekong-water-badge--interactive:active {
  transform: translateY(0);
}

.mekong-water-badge:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.mwb-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm, 0.875rem);
  flex-shrink: 0;
}

.mwb-content {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  white-space: nowrap;
}

.mwb-label {
  font-weight: var(--weight-semibold, 600);
}

.mwb-dot {
  opacity: 0.5;
  margin: 0 2px;
}

.mwb-lunar {
  font-variant-numeric: tabular-nums;
  opacity: 0.85;
}

.mwb-sublabel {
  font-size: var(--text-2xs, 0.6875rem);
  opacity: 0.75;
}

/* ── States: Mekong Terroir Palette ── */

/* 1. Con nước rong · Triều cường (River Blue / Deep Silt) */
.mekong-water-badge.tide-rong {
  background: color-mix(in srgb, var(--river-600) 12%, var(--card));
  color: var(--river-700);
  border-color: color-mix(in srgb, var(--river-600) 32%, transparent);
}
.mekong-water-badge.tide-rong .mwb-indicator {
  color: var(--river-600);
}

/* 2. Con nước kém · Sông êm (Clay / Alluvial Warmth) */
.mekong-water-badge.tide-kem {
  background: color-mix(in srgb, var(--clay-600) 10%, var(--card));
  color: var(--clay-700);
  border-color: color-mix(in srgb, var(--clay-600) 30%, transparent);
}
.mekong-water-badge.tide-kem .mwb-indicator {
  color: var(--clay-600);
}

/* 3. Nước lớn · Triều dâng (Orchard Green) */
.mekong-water-badge.tide-lon {
  background: color-mix(in srgb, var(--orchard-600) 10%, var(--card));
  color: var(--orchard-600);
  border-color: color-mix(in srgb, var(--orchard-600) 30%, transparent);
}
.mekong-water-badge.tide-lon .mwb-indicator {
  color: var(--orchard-600);
}

/* 4. Nước ròng · Triều rút (Amber Harvest Gold) */
.mekong-water-badge.tide-rong-can {
  background: color-mix(in srgb, var(--alluvial-gold) 12%, var(--card));
  color: var(--amber-700);
  border-color: color-mix(in srgb, var(--alluvial-gold) 32%, transparent);
}
.mekong-water-badge.tide-rong-can .mwb-indicator {
  color: var(--alluvial-gold);
}

/* 5. Con nước chuyển · Dòng điều hòa */
.mekong-water-badge.tide-chuyen {
  background: color-mix(in srgb, var(--river-600) 8%, var(--card));
  color: var(--ink);
  border-color: color-mix(in srgb, var(--line) 80%, transparent);
}

/* Dark mode adjustments */
.dark .mekong-water-badge.tide-rong {
  background: color-mix(in srgb, var(--river-legacy-dark) 18%, var(--card));
  color: var(--river-legacy-dark);
  border-color: color-mix(in srgb, var(--river-legacy-dark) 35%, transparent);
}
.dark .mekong-water-badge.tide-rong .mwb-indicator {
  color: var(--river-legacy-dark);
}

.dark .mekong-water-badge.tide-kem {
  background: color-mix(in srgb, var(--night-clay) 18%, var(--card));
  color: var(--night-clay);
  border-color: color-mix(in srgb, var(--night-clay) 35%, transparent);
}
.dark .mekong-water-badge.tide-kem .mwb-indicator {
  color: var(--night-clay);
}

.dark .mekong-water-badge.tide-lon {
  background: color-mix(in srgb, var(--night-leaf) 18%, var(--card));
  color: var(--night-leaf);
  border-color: color-mix(in srgb, var(--night-leaf) 35%, transparent);
}

.dark .mekong-water-badge.tide-rong-can {
  background: color-mix(in srgb, var(--night-amber) 18%, var(--card));
  color: var(--night-amber);
  border-color: color-mix(in srgb, var(--night-amber) 35%, transparent);
}

.dark .mekong-water-badge.tide-chuyen {
  background: color-mix(in srgb, var(--bg-alt) 80%, var(--card));
  color: var(--ink);
  border-color: var(--line);
}
</style>
