<template>
  <aside class="planner-summary" data-planner-summary aria-label="Tóm tắt lịch trình">
    <div class="planner-summary__heading">
      <span class="planner-summary__eyebrow">Nhìn nhanh</span>
      <h2>Tóm tắt lịch trình</h2>
    </div>
    <dl class="planner-summary__stats">
      <div>
        <dt>Điểm dừng</dt>
        <dd data-summary-stop-count>{{ stopCount }}</dd>
      </div>
      <div>
        <dt>Tổng thời gian</dt>
        <dd data-summary-total-duration>{{ displayDuration(totalDuration, totalDurationPartial) }}</dd>
      </div>
      <div>
        <dt>Di chuyển</dt>
        <dd data-summary-travel-duration>{{ displayDuration(travelDuration) }}</dd>
      </div>
    </dl>
    <div v-if="warnings.length" class="planner-summary__warnings" data-summary-warnings>
      <h3>Lưu ý cần xem</h3>
      <ul>
        <li v-for="(warning, index) in warnings" :key="warningKey(warning, index)">
          {{ warningText(warning) }}
        </li>
      </ul>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { formatDuration } from '~/composables/useRouting'
import type { PlannerFrictionNotice } from '~/composables/useItineraryOptimization'

const props = defineProps<{
  stopCount: number
  totalDuration: number | string | null
  totalDurationPartial?: boolean
  travelDuration: number | string | null
  warnings: Array<string | PlannerFrictionNotice>
}>()

function displayDuration(value: number | string | null, partial = false): string {
  if (value === null) return 'Chưa xác định'
  if (typeof value === 'string') return value
  const duration = value === 0 ? '0 phút' : formatDuration(value)
  return partial ? `${duration} đã biết · chưa gồm di chuyển` : duration
}

function warningText(value: string | PlannerFrictionNotice): string {
  return typeof value === 'string' ? value : value.reason
}

function warningKey(value: string | PlannerFrictionNotice, index: number): string {
  return `${typeof value === 'string' ? value : value.code}-${index}`
}
</script>
