<template>
  <article
    class="planner-friction-notice"
    :class="`planner-friction-notice--${severity}`"
    :data-friction-code="code"
    :data-friction-severity="severity"
    role="status"
  >
    <div class="planner-friction-notice__body">
      <span class="planner-friction-notice__label">{{ codeLabel }}</span>
      <p>{{ reason }}</p>
    </div>
    <button
      type="button"
      class="btn btn-sm btn-outline planner-friction-notice__recovery"
      data-friction-recovery
      @click="$emit('recover')"
    >
      {{ recoveryLabel }}
    </button>
  </article>
</template>

<script setup lang="ts">
import type {
  PlannerFrictionCode,
  PlannerFrictionRecovery,
  PlannerFrictionSeverity,
} from '~/composables/useItineraryOptimization'

const props = defineProps<{
  code: PlannerFrictionCode | string
  severity: PlannerFrictionSeverity
  reason: string
  recovery: PlannerFrictionRecovery | string
}>()

defineEmits<{ recover: [] }>()

const codeLabels: Record<string, string> = {
  'opening-hours-conflict': 'Giờ mở cửa',
  'travel-time-over-budget': 'Vượt ngân sách thời gian',
  'stale-stop-facts': 'Dữ kiện có thể đã cũ',
  'missing-coordinates': 'Thiếu tọa độ',
  'offline-draft': 'Bản nháp ngoại tuyến',
  'route-unavailable': 'Tuyến tạm thời không khả dụng',
}

const codeLabel = computed(() => codeLabels[props.code] || 'Lưu ý lịch trình')
const recoveryLabel = computed(() => (
  typeof props.recovery === 'string' ? props.recovery : props.recovery.label
))
</script>
