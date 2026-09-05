<template>
  <div v-if="practicalTips.length || bestTimeText" class="detail-practical-tips-wrapper">
    <!-- Lưu ý thực tế — Scenarios 2,3,6,9: practical tips for food/family/OCOP/delegation -->
    <div v-if="practicalTips.length" class="practical-tips reveal">
      <h2 class="section-subtitle sediment-head">
        <IconLine name="clipboard-list" aria-hidden="true" />
        {{ tipsHeading || 'Lưu ý thực tế' }}
      </h2>
      <ul class="pt-list">
        <li v-for="tip in practicalTips" :key="tip.icon" class="pt-item">
          <IconLine class="pt-icon" :name="tip.icon" aria-hidden="true" />
          <div class="pt-content">
            <strong>{{ tip.label }}</strong>
            <span>{{ tip.value }}</span>
          </div>
        </li>
      </ul>
    </div>

    <!-- Best time callout -->
    <!-- declutter-1 T6: best_time chỉ render 1 chỗ (callout này); đã bỏ khỏi practicalTips
         nên guard chống-trùng cũ không cần nữa. -->
    <div v-if="bestTimeText" class="best-time-callout reveal">
      <IconLine class="btc-icon" name="clock" aria-hidden="true" />
      <div class="btc-body">
        <strong>Thời điểm lý tưởng</strong>
        <span>{{ bestTimeText }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'

interface Props {
  entity: Entity
  tipsHeading?: string
}

const props = defineProps<Props>()

const practicalTips = computed(() => {
  const a = props.entity?.attributes
  if (!a) return []
  const tips: { icon: string; label: string; value: string }[] = []
  if (a.highlight) tips.push({ icon: 'sparkles', label: 'Điểm nhấn', value: String(a.highlight) })
  if (a.booking_note) tips.push({ icon: 'clipboard-list', label: 'Đặt trước', value: String(a.booking_note) })
  if (a.transport) tips.push({ icon: 'car', label: 'Di chuyển', value: String(a.transport) })
  if (a.fee) tips.push({ icon: 'tag', label: 'Phí vào cửa', value: String(a.fee) })
  // declutter-3 T17 (A8 thu-scope D5): amenities 1 nguồn duy nhất = facts-card "Tiện ích"
  // (bảng tham chiếu) — bỏ dòng lặp trong practical-tips.
  if (a.family_friendly || (Array.isArray(a.suitable_for) && a.suitable_for.includes('family')))
    tips.push({ icon: 'users', label: 'Gia đình', value: 'Phù hợp cho gia đình có trẻ em' })
  if (a.parking) tips.push({ icon: 'pin', label: 'Đậu xe', value: String(a.parking) })
  if (a.vehicle_access) tips.push({ icon: 'car', label: 'Tiếp cận xe', value: String(a.vehicle_access) })
  if (Array.isArray(a.travel_tips)) {
    for (const t of a.travel_tips.slice(0, 3)) {
      if (t) tips.push({ icon: 'bulb', label: 'Mẹo', value: String(t) })
    }
  }
  return tips
})

const bestTimeText = computed(() => (props.entity?.attributes?.best_time as string) || '')
</script>
